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
        title=f"ETF Monthly Rebalance Report - {resolved_report_date}",
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
        f"# ETF Monthly Rebalance Report - {report_date}",
        "",
        "## Strategy Run",
        "",
        f"- run_id: {strategy_run.id}",
        f"- strategy_code: {strategy_run.strategy_code}",
        f"- strategy_version: {strategy_run.strategy_version}",
        f"- run_date: {strategy_run.run_date}",
        f"- status: {strategy_run.status}",
        "",
        "## Alpha Ranking",
        "",
    ]
    lines.extend(markdown_table(["Rank", "Symbol", "Alpha Score", "Confidence"], signal_rows(signals)))
    lines.extend(["", "## Target Portfolio", ""])
    lines.extend(markdown_table(["Symbol", "Asset Class", "Raw Weight", "Final Weight", "Reason"], target_rows(targets)))
    lines.extend(["", "## Risk Check", ""])
    lines.extend(markdown_table(["Rule", "Status", "Before", "After", "Message"], risk_rows(risk_results)))
    lines.extend(["", "## Rebalance Orders", ""])
    lines.extend(markdown_table(["Symbol", "Action", "Current", "Target", "Diff", "Amount"], rebalance_rows(rebalance_orders)))
    lines.extend(["", "## Backtest Snapshot", ""])
    if backtest:
        lines.extend([f"- backtest_id: {backtest.id}", f"- name: {backtest.name}", f"- period: {backtest.start_date} to {backtest.end_date}", ""])
        lines.extend(markdown_table(["Metric", "Value", "Unit"], metric_rows(backtest_metrics)))
    else:
        lines.append("- No backtest result available.")
    lines.extend(
        [
            "",
            "## System Notes",
            "",
            "- This report is generated for personal ETF research and review.",
            "- It is not investment advice and does not trigger real trades.",
            "- Rebalance orders are suggestions and require manual confirmation.",
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

