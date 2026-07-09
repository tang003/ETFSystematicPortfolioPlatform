from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import Base, SessionLocal, engine
from app.models.workflow import WorkflowTask, WorkflowTaskStep
from app.schemas.workflow_schema import WorkflowRunRequest
from app.services.calendar_service import sync_trading_calendar
from app.services.data_quality_service import check_clean_bars
from app.services.factor_service import calculate_factors
from app.services.market_service import sync_market_data
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


def run_workflow_task(task_id: int) -> None:
    ensure_workflow_tables()
    db = SessionLocal()
    try:
        task = db.get(WorkflowTask, task_id)
        if task is None:
            return
        request = WorkflowRunRequest.model_validate(task.request_payload)
        mark_task_running(db, task)
        results: dict[str, Any] = {}

        execute_step(db, task, "calendar", lambda: sync_trading_calendar(db, request.start_date, request.end_date, "CN"), results)
        execute_step(
            db,
            task,
            "market",
            lambda: sync_market_data(
                db,
                symbols=request.symbols,
                start_date=request.start_date,
                end_date=request.end_date,
                max_symbols=request.max_symbols,
                clean_after_sync=True,
                request_interval_seconds=0,
            ),
            results,
        )
        if request.symbols:
            execute_step(db, task, "quality", lambda: run_quality_checks(db, request.symbols or [], request.start_date, request.end_date), results)
        else:
            skip_step(db, task, "quality", "未指定 ETF 代码，跳过前端指定范围的数据质量检查。")
        execute_step(
            db,
            task,
            "factors",
            lambda: calculate_factors(db, symbols=request.symbols, start_date=request.start_date, end_date=request.end_date),
            results,
        )
        strategy_result = execute_step(
            db,
            task,
            "strategy",
            lambda: run_strategy(db, strategy_code=request.strategy_code, run_date=request.end_date, run_type="workflow"),
            results,
        )
        run_id = int(strategy_result["run_id"])
        execute_step(db, task, "risk", lambda: run_risk_check(db, run_id=run_id), results)
        execute_step(db, task, "rebalance", lambda: generate_rebalance_orders(db, run_id=run_id, portfolio_value=request.portfolio_value), results)
        if request.generate_report:
            execute_step(db, task, "report", lambda: generate_monthly_report(db, run_id=run_id, report_date=request.end_date), results)
        else:
            skip_step(db, task, "report", "本次任务未选择生成报告。")

        task.status = "success"
        task.current_step = None
        task.result_payload = json_ready({"run_id": run_id, "steps": results})
        task.finished_at = datetime.utcnow()
        db.commit()
    except Exception as exc:  # noqa: BLE001 - persist task failure for UI polling.
        db.rollback()
        fail_task(db, task_id, str(exc))
    finally:
        db.close()


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
    step.message = "开始执行"
    db.commit()

    result = action()
    step.status = "success"
    step.result_payload = json_ready(result)
    step.message = summarize_result(result)
    step.finished_at = datetime.utcnow()
    results[step_key] = json_ready(result)
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


def mark_task_running(db: Session, task: WorkflowTask) -> None:
    task.status = "running"
    task.started_at = datetime.utcnow()
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
