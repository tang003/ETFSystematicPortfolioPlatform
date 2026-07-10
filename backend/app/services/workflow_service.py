from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import Base, SessionLocal, engine
from app.models.market_data import MarketDataClean, TradingCalendar
from app.models.workflow import WorkflowTask, WorkflowTaskStep
from app.schemas.workflow_schema import WorkflowRunRequest
from app.services.calendar_service import sync_trading_calendar
from app.services.data_quality_service import check_clean_bars
from app.services.factor_service import calculate_factors
from app.services.market_service import limit_symbols, resolve_symbols, sync_market_data
from app.services.report_service import generate_monthly_report
from app.services.risk_service import generate_rebalance_orders, run_risk_check
from app.services.strategy_service import run_strategy

WORKFLOW_STEPS = [
    ("calendar", "同步交易日历"),
    ("market", "同步 ETF 行情"),
    ("quality", "检查数据质量"),
    ("factors", "计算因子"),
    ("strategy", "运行策略"),
    ("risk", "执行风控"),
    ("rebalance", "生成调仓单"),
    ("report", "生成月度报告"),
]

TERMINAL_STATUSES = {"success", "failed", "cancelled", "partial_success"}


def ensure_workflow_tables() -> None:
    Base.metadata.create_all(bind=engine, tables=[WorkflowTask.__table__, WorkflowTaskStep.__table__])


def create_workflow_task(db: Session, request: WorkflowRunRequest) -> WorkflowTask:
    ensure_workflow_tables()
    task = WorkflowTask(
        task_type="full_rebalance",
        status="pending",
        request_payload=json_ready(request.model_dump()),
    )
    db.add(task)
    db.flush()
    db.add_all(
        [
            WorkflowTaskStep(
                task_id=task.id,
                step_key=step_key,
                step_name=step_name,
                sort_order=index,
                status="pending",
            )
            for index, (step_key, step_name) in enumerate(WORKFLOW_STEPS, start=1)
        ]
    )
    db.commit()
    db.refresh(task)
    return task


def get_workflow_task(db: Session, task_id: int) -> tuple[WorkflowTask | None, list[WorkflowTaskStep]]:
    ensure_workflow_tables()
    task = db.get(WorkflowTask, task_id)
    if task is None:
        return None, []
    steps = list(
        db.scalars(
            select(WorkflowTaskStep)
            .where(WorkflowTaskStep.task_id == task_id)
            .order_by(WorkflowTaskStep.sort_order)
        ).all()
    )
    return task, steps


def list_workflow_tasks(db: Session, limit: int = 20) -> list[WorkflowTask]:
    ensure_workflow_tables()
    return list(db.scalars(select(WorkflowTask).order_by(WorkflowTask.created_at.desc()).limit(limit)).all())


def cancel_workflow_task(db: Session, task_id: int) -> WorkflowTask:
    task, steps = get_workflow_task(db, task_id)
    if task is None:
        raise ValueError(f"Workflow task not found: {task_id}")
    if task.status in TERMINAL_STATUSES:
        return task
    task.status = "cancelled"
    task.error_message = "任务已取消"
    task.finished_at = datetime.utcnow()
    for step in steps:
        if step.status == "running":
            step.status = "cancelled"
            step.message = "任务取消时该步骤正在执行"
            step.finished_at = datetime.utcnow()
        elif step.status == "pending":
            step.status = "skipped"
            step.message = "任务已取消，跳过未执行步骤"
            step.finished_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    return task


def reset_failed_steps_for_retry(db: Session, task_id: int) -> WorkflowTask:
    task, steps = get_workflow_task(db, task_id)
    if task is None:
        raise ValueError(f"Workflow task not found: {task_id}")
    failed_seen = False
    for step in steps:
        if step.status == "failed":
            failed_seen = True
        if failed_seen and step.status in {"failed", "pending", "skipped"}:
            step.status = "pending"
            step.message = None
            step.result_payload = None
            step.started_at = None
            step.finished_at = None
    if not failed_seen:
        raise ValueError("No failed step found for retry")
    task.status = "pending"
    task.current_step = None
    task.error_message = None
    task.finished_at = None
    db.commit()
    db.refresh(task)
    return task


def claim_next_workflow_task(db: Session) -> WorkflowTask | None:
    ensure_workflow_tables()
    task = db.scalar(
        select(WorkflowTask)
        .where(WorkflowTask.status == "pending")
        .order_by(WorkflowTask.created_at.asc(), WorkflowTask.id.asc())
        .with_for_update(skip_locked=True)
    )
    if task is None:
        db.rollback()
        return None
    task.status = "running"
    task.started_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    return task


def recover_interrupted_workflow_tasks(db: Session) -> int:
    ensure_workflow_tables()
    tasks = list(db.scalars(select(WorkflowTask).where(WorkflowTask.status == "running")).all())
    recovered = 0
    for task in tasks:
        task.status = "pending"
        task.current_step = None
        task.error_message = "Worker restarted before task finished; task was returned to pending."
        steps = list(
            db.scalars(
                select(WorkflowTaskStep)
                .where(WorkflowTaskStep.task_id == task.id)
                .where(WorkflowTaskStep.status == "running")
            ).all()
        )
        for step in steps:
            step.status = "pending"
            step.message = "Worker restarted; this step will be retried."
            step.started_at = None
            step.finished_at = None
        recovered += 1
    db.commit()
    return recovered


def run_workflow_task(task_id: int) -> None:
    ensure_workflow_tables()
    db = SessionLocal()
    try:
        task = db.get(WorkflowTask, task_id)
        if task is None or task.status == "cancelled":
            return
        request = WorkflowRunRequest.model_validate(task.request_payload)
        mark_task_running(db, task)
        results: dict[str, Any] = dict(task.result_payload.get("steps", {}) if task.result_payload else {})
        workflow_symbols = resolve_workflow_symbols(db, request.symbols, request.max_symbols)

        run_id = existing_run_id(task)
        for step_key, _ in WORKFLOW_STEPS:
            if is_step_done(db, task.id, step_key):
                continue
            check_cancelled(db, task.id)
            if step_key == "calendar":
                execute_step(
                    db,
                    task,
                    step_key,
                    lambda: sync_trading_calendar(
                        db,
                        request.start_date,
                        request.end_date,
                        "CN",
                        request.calendar_source,
                        request.incremental_sync,
                    ),
                    results,
                )
            elif step_key == "market":
                execute_step(
                    db,
                    task,
                    step_key,
                    lambda: run_market_step(
                        db,
                        symbols=workflow_symbols,
                        start_date=request.start_date,
                        end_date=request.end_date,
                        source=request.market_source,
                        incremental=request.incremental_sync,
                        request_interval_seconds=request.request_interval_seconds,
                        strict=request.strict_data_validation,
                        minimum_history_bars=request.minimum_history_bars,
                    ),
                    results,
                )
            elif step_key == "quality":
                if workflow_symbols:
                    execute_step(db, task, step_key, lambda: run_quality_checks(db, workflow_symbols, request.start_date, request.end_date), results)
                else:
                    raise ValueError("研究范围中没有可用的 ETF，请先在 ETF 池中启用研究对象。")
            elif step_key == "factors":
                execute_step(
                    db,
                    task,
                    step_key,
                    lambda: run_factor_step(
                        db,
                        symbols=workflow_symbols,
                        start_date=request.start_date,
                        end_date=request.end_date,
                        strict=request.strict_data_validation,
                    ),
                    results,
                )
            elif step_key == "strategy":
                strategy_result = execute_step(
                    db,
                    task,
                    step_key,
                    lambda: run_strategy(db, strategy_code=request.strategy_code, run_date=request.end_date, run_type="workflow"),
                    results,
                )
                run_id = int(strategy_result["run_id"])
                task.result_payload = json_ready({"run_id": run_id, "steps": results})
                db.commit()
            elif step_key == "risk":
                run_id = require_run_id(run_id)
                execute_step(db, task, step_key, lambda: run_risk_check(db, run_id=run_id), results)
            elif step_key == "rebalance":
                run_id = require_run_id(run_id)
                execute_step(db, task, step_key, lambda: generate_rebalance_orders(db, run_id=run_id, portfolio_value=request.portfolio_value), results)
            elif step_key == "report":
                run_id = require_run_id(run_id)
                if request.generate_report:
                    execute_step(db, task, step_key, lambda: generate_monthly_report(db, run_id=run_id, report_date=request.end_date), results)
                else:
                    skip_step(db, task, step_key, "本次任务未选择生成报告。")

        task.status = final_status_for_steps(db, task.id)
        task.current_step = None
        task.result_payload = json_ready({"run_id": run_id, "steps": results})
        task.finished_at = datetime.utcnow()
        db.commit()
    except WorkflowCancelled:
        db.rollback()
    except Exception as exc:  # noqa: BLE001 - persist task failure for UI polling.
        db.rollback()
        fail_task(db, task_id, str(exc))
    finally:
        db.close()


class WorkflowCancelled(Exception):
    pass


def execute_step(
    db: Session,
    task: WorkflowTask,
    step_key: str,
    action: Callable[[], dict[str, Any]],
    results: dict[str, Any],
) -> dict[str, Any]:
    step = load_step(db, task.id, step_key)
    now = datetime.utcnow()
    task.status = "running"
    task.current_step = step_key
    step.status = "running"
    step.started_at = now
    step.finished_at = None
    step.message = "开始执行"
    db.commit()

    try:
        result = action()
    except WorkflowStepValidationError as exc:
        step.result_payload = json_ready(exc.result)
        results[step_key] = json_ready(exc.result)
        task.result_payload = json_ready({"run_id": existing_run_id(task), "steps": results})
        db.commit()
        raise
    db.refresh(task)
    if task.status == "cancelled":
        raise WorkflowCancelled()
    step.status = "success"
    step.result_payload = json_ready(result)
    step.message = summarize_result(result)
    step.finished_at = datetime.utcnow()
    results[step_key] = json_ready(result)
    task.result_payload = json_ready({"run_id": existing_run_id(task), "steps": results})
    db.commit()
    return result


def skip_step(db: Session, task: WorkflowTask, step_key: str, message: str) -> None:
    step = load_step(db, task.id, step_key)
    step.status = "skipped"
    step.message = message
    step.finished_at = datetime.utcnow()
    db.commit()


def run_quality_checks(db: Session, symbols: list[str], start_date: date, end_date: date) -> dict[str, Any]:
    results = []
    for symbol in symbols:
        log_count = check_clean_bars(db, symbol, start_date, end_date)
        db.commit()
        results.append({"symbol": symbol, "quality_logs": log_count, "status": "success"})
    return {"status": "success", "results": results, "total_logs": sum(item["quality_logs"] for item in results)}


class WorkflowStepValidationError(ValueError):
    def __init__(self, message: str, result: dict[str, Any]) -> None:
        super().__init__(message)
        self.result = result


def resolve_workflow_symbols(db: Session, symbols: list[str] | None, max_symbols: int | None) -> list[str]:
    resolved, _ = limit_symbols(resolve_symbols(db, symbols), max_symbols)
    if not resolved:
        raise ValueError("研究范围中没有可用的 ETF，请先在 ETF 池中启用研究对象。")
    return resolved


def run_market_step(
    db: Session,
    *,
    symbols: list[str],
    start_date: date,
    end_date: date,
    source: str,
    incremental: bool,
    request_interval_seconds: float,
    strict: bool,
    minimum_history_bars: int,
) -> dict[str, Any]:
    result = sync_market_data(
        db,
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        source=source,
        incremental=incremental,
        max_symbols=None,
        clean_after_sync=True,
        request_interval_seconds=request_interval_seconds,
    )
    validate_batch_result("行情同步", result, strict=strict)
    readiness = inspect_market_readiness(
        db,
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        minimum_history_bars=minimum_history_bars,
    )
    result["readiness"] = readiness
    if readiness["ready_count"] == 0:
        raise WorkflowStepValidationError("没有 ETF 通过数据新鲜度和历史样本门禁，流程已停止。", result)
    if strict and readiness["not_ready_count"] > 0:
        failed_symbols = "、".join(item["symbol"] for item in readiness["not_ready"])
        raise WorkflowStepValidationError(f"ETF 数据未通过严格门禁：{failed_symbols}。", result)
    return result


def run_factor_step(
    db: Session,
    *,
    symbols: list[str],
    start_date: date,
    end_date: date,
    strict: bool,
) -> dict[str, Any]:
    result = calculate_factors(db, symbols=symbols, start_date=start_date, end_date=end_date)
    validate_batch_result("因子计算", result, strict=strict)
    return result


def validate_batch_result(step_name: str, result: dict[str, Any], *, strict: bool) -> None:
    total = int(result.get("total_symbols", 0))
    success_count = int(result.get("success_count", 0))
    failed_count = int(result.get("failed_count", 0))
    if total == 0:
        raise WorkflowStepValidationError(f"{step_name}没有可处理的 ETF，流程已停止。", result)
    if success_count == 0:
        raise WorkflowStepValidationError(f"{step_name}全部失败，流程已停止。", result)
    if strict and failed_count > 0:
        raise WorkflowStepValidationError(
            f"{step_name}有 {failed_count}/{total} 只 ETF 失败，严格数据门禁已停止后续建议生成。",
            result,
        )


def inspect_market_readiness(
    db: Session,
    *,
    symbols: list[str],
    start_date: date,
    end_date: date,
    minimum_history_bars: int,
) -> dict[str, Any]:
    required_trade_date = db.scalar(
        select(func.max(TradingCalendar.trade_date))
        .where(TradingCalendar.market == "CN")
        .where(TradingCalendar.is_open.is_(True))
        .where(TradingCalendar.trade_date >= start_date)
        .where(TradingCalendar.trade_date <= end_date)
    )
    if required_trade_date is None:
        return {
            "required_trade_date": None,
            "minimum_history_bars": minimum_history_bars,
            "ready_count": 0,
            "not_ready_count": len(symbols),
            "ready": [],
            "not_ready": [{"symbol": symbol, "reasons": ["missing_trading_calendar"]} for symbol in symbols],
        }

    rows = db.execute(
        select(
            MarketDataClean.symbol,
            func.max(MarketDataClean.trade_date).label("latest_trade_date"),
            func.count(MarketDataClean.id).label("bar_count"),
        )
        .where(MarketDataClean.symbol.in_(symbols))
        .where(MarketDataClean.trade_date >= start_date)
        .where(MarketDataClean.trade_date <= end_date)
        .group_by(MarketDataClean.symbol)
    ).all()
    stats = {row.symbol: row for row in rows}
    ready: list[dict[str, Any]] = []
    not_ready: list[dict[str, Any]] = []
    for symbol in symbols:
        row = stats.get(symbol)
        latest_trade_date = row.latest_trade_date if row else None
        bar_count = int(row.bar_count) if row else 0
        reasons = []
        if latest_trade_date is None or latest_trade_date < required_trade_date:
            reasons.append("stale_market_data")
        if bar_count < minimum_history_bars:
            reasons.append("insufficient_history")
        item = {
            "symbol": symbol,
            "latest_trade_date": latest_trade_date,
            "bar_count": bar_count,
            "reasons": reasons,
        }
        (not_ready if reasons else ready).append(item)

    return {
        "required_trade_date": required_trade_date,
        "minimum_history_bars": minimum_history_bars,
        "ready_count": len(ready),
        "not_ready_count": len(not_ready),
        "ready": ready,
        "not_ready": not_ready,
    }


def mark_task_running(db: Session, task: WorkflowTask) -> None:
    task.status = "running"
    task.started_at = datetime.utcnow()
    task.finished_at = None
    task.error_message = None
    db.commit()


def fail_task(db: Session, task_id: int, message: str) -> None:
    task = db.get(WorkflowTask, task_id)
    if task is None:
        return
    if task.current_step:
        step = load_step(db, task.id, task.current_step)
        step.status = "failed"
        step.message = message
        step.finished_at = datetime.utcnow()
    task.status = "failed"
    task.error_message = message
    task.finished_at = datetime.utcnow()
    db.commit()


def load_step(db: Session, task_id: int, step_key: str) -> WorkflowTaskStep:
    step = db.scalar(
        select(WorkflowTaskStep)
        .where(WorkflowTaskStep.task_id == task_id)
        .where(WorkflowTaskStep.step_key == step_key)
    )
    if step is None:
        raise ValueError(f"Workflow step not found: {step_key}")
    return step


def is_step_done(db: Session, task_id: int, step_key: str) -> bool:
    step = load_step(db, task_id, step_key)
    return step.status in {"success", "skipped"}


def check_cancelled(db: Session, task_id: int) -> None:
    task = db.get(WorkflowTask, task_id)
    if task and task.status == "cancelled":
        raise WorkflowCancelled()


def existing_run_id(task: WorkflowTask) -> int | None:
    if not task.result_payload:
        return None
    value = task.result_payload.get("run_id")
    return int(value) if value is not None else None


def require_run_id(run_id: int | None) -> int:
    if run_id is None:
        raise ValueError("Missing run_id from strategy step")
    return run_id


def final_status_for_steps(db: Session, task_id: int) -> str:
    steps = list(db.scalars(select(WorkflowTaskStep).where(WorkflowTaskStep.task_id == task_id)).all())
    if any(step.status == "failed" for step in steps):
        return "failed"
    if any(step.status == "skipped" for step in steps):
        return "partial_success"
    return "success"


def summarize_result(result: dict[str, Any]) -> str:
    keys = ["status", "success_count", "failed_count", "total_clean_rows", "total_factor_rows", "run_id", "target_count", "result_count", "order_count", "id"]
    parts = [f"{key}={result[key]}" for key in keys if key in result]
    return "，".join(parts) if parts else "执行成功"


def json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_ready(item) for item in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value
