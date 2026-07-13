from datetime import date
from decimal import Decimal

from app.services.report_service import build_monthly_report_markdown, markdown_table


class StrategyRun:
    id = 1
    strategy_code = "core_etf_rotation"
    strategy_version = "0.1.0"
    run_date = date(2026, 7, 8)
    status = "success"


class Signal:
    rank_no = 1
    symbol = "510300"
    alpha_score = Decimal("44.4887")
    confidence = Decimal("0.4449")


class Target:
    symbol = "510300"
    asset_class = "equity"
    raw_target_weight = Decimal("0.400000")
    final_target_weight = Decimal("0.400000")
    reason = "Equity ETF selected by alpha ranking"


class Risk:
    rule_code = "all_rules"
    status = "passed"
    before_value = Decimal("1.00000000")
    after_value = Decimal("1.00000000")
    message = "No risk adjustment required"


class Order:
    symbol = "510300"
    action = "BUY"
    current_weight = Decimal("0")
    target_weight = Decimal("0.400000")
    weight_diff = Decimal("0.400000")
    estimated_amount = Decimal("40000.0000")


class Backtest:
    id = 1
    name = "baseline"
    start_date = date(2026, 7, 1)
    end_date = date(2026, 7, 8)


class Metric:
    metric_name = "cumulative_return"
    metric_value = Decimal("0.01000000")
    metric_unit = "ratio"


def test_markdown_table_adds_empty_row_when_no_data() -> None:
    rows = markdown_table(["A", "B"], [])
    assert rows[-1] == "| - | - |"


def test_build_monthly_report_markdown_contains_core_sections() -> None:
    markdown = build_monthly_report_markdown(
        strategy_run=StrategyRun(),
        report_date=date(2026, 7, 8),
        signals=[Signal()],
        targets=[Target()],
        risk_results=[Risk()],
        rebalance_orders=[Order()],
        backtest=Backtest(),
        backtest_metrics=[Metric()],
    )

    assert "# ETF 月度调仓报告 (Monthly Rebalance Report) - 2026-07-08" in markdown
    assert "## Alpha 排名 (Alpha Ranking)" in markdown
    assert "## 目标组合 (Target Portfolio)" in markdown
    assert "## 风控检查 (Risk Check)" in markdown
    assert "## 持仓替代观察 (Same-Index Alternatives)" in markdown
    assert "## 调仓建议单 (Rebalance Orders)" in markdown
    assert "## 回测摘要 (Backtest Snapshot)" in markdown
    assert "510300" in markdown
