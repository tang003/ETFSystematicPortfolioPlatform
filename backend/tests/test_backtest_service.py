from datetime import date
from decimal import Decimal

import pandas as pd

from app.services.backtest_service import calculate_backtest_metrics, simulate_equal_weight_buy_and_hold, simulate_monthly_strategy_rotation


class Asset:
    def __init__(self, asset_class: str, risk_level: int = 3, enabled: bool = True) -> None:
        self.asset_class = asset_class
        self.risk_level = risk_level
        self.enabled = enabled


def test_simulate_equal_weight_buy_and_hold_generates_curve_and_trades() -> None:
    price_frame = pd.DataFrame(
        {"510300": [1.0, 1.1, 1.2], "510500": [2.0, 2.0, 2.2]},
        index=[date(2026, 7, 1), date(2026, 7, 2), date(2026, 7, 3)],
    )

    curve, trades, metrics = simulate_equal_weight_buy_and_hold(
        backtest_id=1,
        price_frame=price_frame,
        initial_cash=Decimal("10000"),
        monthly_contribution=Decimal("0"),
        fee_rate=Decimal("0"),
        slippage_rate=Decimal("0"),
    )

    assert len(curve) == 3
    assert len(trades) == 2
    assert curve[-1].total_equity == Decimal("11500.0000")
    assert metrics["cumulative_return"] == Decimal("0.15000000")
    assert metrics["trade_count"] == Decimal("2")


def test_calculate_backtest_metrics_handles_empty_curve() -> None:
    assert calculate_backtest_metrics([], [], Decimal("10000")) == {}


def test_simulate_monthly_strategy_rotation_rebalances_from_factor_ranking() -> None:
    price_frame = pd.DataFrame(
        {
            "510300": [1.0, 1.1, 1.2, 1.3],
            "510500": [2.0, 2.1, 2.0, 2.2],
            "511010": [1.0, 1.0, 1.0, 1.0],
            "511880": [1.0, 1.0, 1.0, 1.0],
        },
        index=[date(2026, 1, 2), date(2026, 1, 31), date(2026, 2, 2), date(2026, 2, 28)],
    )

    curve, trades, metrics = simulate_monthly_strategy_rotation(
        backtest_id=1,
        price_frame=price_frame,
        initial_cash=Decimal("10000"),
        monthly_contribution=Decimal("1000"),
        fee_rate=Decimal("0"),
        slippage_rate=Decimal("0"),
        asset_map={
            "510300": Asset("equity"),
            "510500": Asset("equity"),
            "511010": Asset("bond", risk_level=1),
            "511880": Asset("cash", risk_level=1),
        },
        ranking_by_date={
            date(2026, 1, 2): ["510300", "510500", "511010", "511880"],
            date(2026, 2, 2): ["510500", "510300", "511010", "511880"],
        },
    )

    assert len(curve) == 4
    assert len(trades) > 4
    assert any(trade.trade_date == date(2026, 2, 2) for trade in trades)
    assert metrics["trade_count"] == Decimal(len(trades))
    assert curve[-1].total_equity > Decimal("10000")


def test_calculate_backtest_metrics_uses_invested_capital_when_provided() -> None:
    price_frame = pd.DataFrame(
        {"510300": [1.0, 1.0]},
        index=[date(2026, 1, 2), date(2026, 1, 3)],
    )
    curve, trades, _ = simulate_equal_weight_buy_and_hold(
        backtest_id=1,
        price_frame=price_frame,
        initial_cash=Decimal("10000"),
        monthly_contribution=Decimal("0"),
        fee_rate=Decimal("0"),
        slippage_rate=Decimal("0"),
    )

    metrics = calculate_backtest_metrics(curve, trades, Decimal("10000"), invested_capital=Decimal("12000"))

    assert metrics["cumulative_return"] == Decimal("-0.16666667")
