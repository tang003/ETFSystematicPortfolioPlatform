from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.backtest import BacktestMetrics, BacktestRun
from app.models.portfolio import TargetPortfolio
from app.models.rebalance import RebalanceOrder
from app.models.report import ReportLog
from app.models.risk import RiskCheckResult
from app.models.strategy import AlphaSignal, StrategyRun


def generate_monthly_report(
    db: Session,
    *,
    run_id: int | None = None,
    report_date: date | None = None,
) -> dict[str, Any]:
    strategy_run = resolve_strategy_run(db, run_id)
    if strategy_run is None:
        raise ValueError("No strategy run found for monthly report")
    resolved_report_date = report_date or strategy_run.run_date

    signals = load_signals(db, strategy_run.id)
    targets = load_targets(db, strategy_run.id)
    risk_results = load_risk_results(db, strategy_run.id)
    rebalance_orders = load_rebalance_orders(db, strategy_run.id)
    latest_backtest = load_latest_backtest(db)
    backtest_metrics = load_backtest_metrics(db, latest_backtest.id) if latest_backtest else []

    markdown = build_monthly_report_markdown(
        strategy_run=strategy_run,
        report_date=resolved_report_date,
        signals=signals,
        targets=targets,
        risk_results=risk_results,
        rebalance_orders=rebalance_orders,
        backtest=latest_backtest,
        backtest_metrics=backtest_metrics,
    )

    report = ReportLog(
        run_id=strategy_run.id,
        report_date=resolved_report_date,
        report_type="monthly_rebalance",
        title=f"ETF 月度调仓报告 (Monthly Rebalance Report) - {resolved_report_date}",
        file_path=None,
        content_markdown=markdown,
        status="generated",
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return {
        "id": report.id,
        "run_id": strategy_run.id,
        "report_date": resolved_report_date,
        "report_type": report.report_type,
        "title": report.title,
        "status": report.status,
    }


def resolve_strategy_run(db: Session, run_id: int | None) -> StrategyRun | None:
    if run_id is not None:
        return db.get(StrategyRun, run_id)
    return db.scalar(select(StrategyRun).order_by(StrategyRun.created_at.desc()).limit(1))


def load_signals(db: Session, run_id: int) -> list[AlphaSignal]:
    return list(db.scalars(select(AlphaSignal).where(AlphaSignal.run_id == run_id).order_by(AlphaSignal.rank_no)).all())


def load_targets(db: Session, run_id: int) -> list[TargetPortfolio]:
    return list(
        db.scalars(
            select(TargetPortfolio)
            .where(TargetPortfolio.run_id == run_id)
            .order_by(TargetPortfolio.final_target_weight.desc().nullslast())
        ).all()
    )


def load_risk_results(db: Session, run_id: int) -> list[RiskCheckResult]:
    return list(
        db.scalars(
            select(RiskCheckResult).where(RiskCheckResult.run_id == run_id).order_by(RiskCheckResult.created_at)
        ).all()
    )


def load_rebalance_orders(db: Session, run_id: int) -> list[RebalanceOrder]:
    return list(
        db.scalars(
            select(RebalanceOrder).where(RebalanceOrder.run_id == run_id).order_by(RebalanceOrder.symbol)
        ).all()
    )


def load_latest_backtest(db: Session) -> BacktestRun | None:
    return db.scalar(select(BacktestRun).order_by(BacktestRun.created_at.desc()).limit(1))


def load_backtest_metrics(db: Session, backtest_id: int) -> list[BacktestMetrics]:
    return list(
        db.scalars(
            select(BacktestMetrics)
            .where(BacktestMetrics.backtest_id == backtest_id)
            .order_by(BacktestMetrics.sort_order)
        ).all()
    )


def build_monthly_report_markdown(
    *,
    strategy_run: StrategyRun,
    report_date: date,
    signals: list[AlphaSignal],
    targets: list[TargetPortfolio],
    risk_results: list[RiskCheckResult],
    rebalance_orders: list[RebalanceOrder],
    backtest: BacktestRun | None,
    backtest_metrics: list[BacktestMetrics],
) -> str:
    lines = [
        f"# ETF 月度调仓报告 (Monthly Rebalance Report) - {report_date}",
        "",
        "## 策略运行概览 (Strategy Run)",
        "",
        f"- run_id: {strategy_run.id}",
        f"- strategy_code: {strategy_run.strategy_code}",
        f"- strategy_version: {strategy_run.strategy_version}",
        f"- run_date: {strategy_run.run_date}",
        f"- status: {strategy_run.status}",
        "",
        "## Alpha 排名 (Alpha Ranking)",
        "",
    ]
    lines.extend(markdown_table(["排名 Rank", "代码 Symbol", "Alpha 分数", "置信度 Confidence"], signal_rows(signals)))
    lines.extend(["", "## 目标组合 (Target Portfolio)", ""])
    lines.extend(markdown_table(["代码 Symbol", "资产类别 Asset Class", "原始权重 Raw Weight", "最终权重 Final Weight", "说明 Reason"], target_rows(targets)))
    lines.extend(["", "## 风控检查 (Risk Check)", ""])
    lines.extend(markdown_table(["规则 Rule", "状态 Status", "调整前 Before", "调整后 After", "说明 Message"], risk_rows(risk_results)))
    lines.extend(["", "## 调仓建议单 (Rebalance Orders)", ""])
    lines.extend(markdown_table(["代码 Symbol", "方向 Action", "当前权重 Current", "目标权重 Target", "差异 Diff", "估算金额 Amount"], rebalance_rows(rebalance_orders)))
    lines.extend(["", "## 回测摘要 (Backtest Snapshot)", ""])
    if backtest:
        lines.extend([f"- backtest_id: {backtest.id}", f"- name: {backtest.name}", f"- period: {backtest.start_date} to {backtest.end_date}", ""])
        lines.extend(markdown_table(["指标 Metric", "数值 Value", "单位 Unit"], metric_rows(backtest_metrics)))
    else:
        lines.append("- 暂无可用回测结果 (No backtest result available).")
    lines.extend(
        [
            "",
            "## 系统说明 (System Notes)",
            "",
            "- 本报告用于个人 ETF 投研和复盘 (personal ETF research and review)。",
            "- 本报告不是投资建议 (not investment advice)，也不会触发真实交易。",
            "- 调仓单为建议订单 (suggested rebalance orders)，执行前需要人工确认。",
        ]
    )
    return "\n".join(lines)


def markdown_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    if not rows:
        rows = [["-" for _ in headers]]
    return [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
        *["| " + " | ".join(row) + " |" for row in rows],
    ]


def signal_rows(signals: list[AlphaSignal]) -> list[list[str]]:
    return [
        [str(item.rank_no), item.symbol, fmt_decimal(item.alpha_score), fmt_decimal(item.confidence)]
        for item in signals
    ]


def target_rows(targets: list[TargetPortfolio]) -> list[list[str]]:
    return [
        [
            item.symbol,
            item.asset_class or "",
            fmt_percent(item.raw_target_weight),
            fmt_percent(item.final_target_weight),
            item.reason or "",
        ]
        for item in targets
    ]


def risk_rows(results: list[RiskCheckResult]) -> list[list[str]]:
    return [
        [
            item.rule_code,
            item.status,
            fmt_decimal(item.before_value),
            fmt_decimal(item.after_value),
            item.message or "",
        ]
        for item in results
    ]


def rebalance_rows(orders: list[RebalanceOrder]) -> list[list[str]]:
    return [
        [
            item.symbol,
            item.action,
            fmt_percent(item.current_weight),
            fmt_percent(item.target_weight),
            fmt_percent(item.weight_diff),
            fmt_decimal(item.estimated_amount),
        ]
        for item in orders
    ]


def metric_rows(metrics: list[BacktestMetrics]) -> list[list[str]]:
    return [[item.metric_name, fmt_decimal(item.metric_value), item.metric_unit or ""] for item in metrics]


def fmt_decimal(value: Decimal | None) -> str:
    if value is None:
        return ""
    return str(value)


def fmt_percent(value: Decimal | None) -> str:
    if value is None:
        return ""
    return f"{(Decimal(value) * Decimal('100')).quantize(Decimal('0.01'))}%"


def list_reports(db: Session, limit: int = 100) -> list[ReportLog]:
    return list(db.scalars(select(ReportLog).order_by(ReportLog.created_at.desc()).limit(limit)).all())


def get_report(db: Session, report_id: int) -> ReportLog | None:
    return db.get(ReportLog, report_id)
