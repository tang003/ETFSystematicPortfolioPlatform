from datetime import date
from decimal import Decimal

import pandas as pd

from app.services.backtest_service import calculate_backtest_metrics, simulate_equal_weight_buy_and_hold


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

