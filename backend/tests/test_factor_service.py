from datetime import date
from decimal import Decimal

from app.services.factor_service import (
    build_factor_rows,
    score_drawdown,
    score_return,
    score_trend,
    score_volatility,
    weighted_alpha_score,
)


class CleanBar:
    def __init__(self, trade_date: date, close: Decimal, amount: Decimal) -> None:
        self.trade_date = trade_date
        self.close = close
        self.amount = amount


def test_score_return_is_explainable_bucket() -> None:
    assert score_return(0.12) == Decimal("100")
    assert score_return(0.04) == Decimal("80")
    assert score_return(-0.02) == Decimal("40")
    assert score_return(-0.08) == Decimal("20")


def test_risk_scores_reward_lower_risk() -> None:
    assert score_volatility(0.10) == Decimal("100")
    assert score_volatility(0.55) == Decimal("20")
    assert score_drawdown(-0.03) == Decimal("100")
    assert score_drawdown(-0.25) == Decimal("20")


def test_score_trend_counts_price_above_moving_averages() -> None:
    row = {"close": 10, "ma20": 9, "ma60": 9.5, "ma120": 10.5, "ma200": 11}
    assert score_trend(row) == Decimal("50")


def test_weighted_alpha_score_uses_default_weights() -> None:
    score = weighted_alpha_score(
        trend_score=Decimal("100"),
        momentum_score=Decimal("80"),
        volatility_score=Decimal("60"),
        drawdown_score=Decimal("40"),
        liquidity_score=Decimal("20"),
        premium_score=Decimal("80"),
    )
    assert score == Decimal("77.0000")


def test_build_factor_rows_generates_rows_for_small_sample() -> None:
    bars = [
        CleanBar(date(2026, 7, 1), Decimal("1.00"), Decimal("1000")),
        CleanBar(date(2026, 7, 2), Decimal("1.02"), Decimal("1100")),
        CleanBar(date(2026, 7, 3), Decimal("1.05"), Decimal("1200")),
    ]

    rows = build_factor_rows("510300", bars)

    assert len(rows) == 3
    assert rows[-1]["symbol"] == "510300"
    assert rows[-1]["ma20"] == Decimal("1.023333")
    assert rows[-1]["trend_score"] == Decimal("100")
    assert rows[-1]["alpha_score"] is not None

