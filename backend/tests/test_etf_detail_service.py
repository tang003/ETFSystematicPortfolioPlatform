from datetime import date
from decimal import Decimal

from app.services.etf_detail_service import build_detail_curve, recommendation_level, recommendation_score


class Bar:
    def __init__(self, trade_date: date, close: str, amount: str = "10000000") -> None:
        self.trade_date = trade_date
        self.close = Decimal(close)
        self.amount = Decimal(amount)


class Asset:
    fund_size = Decimal("12000000000")
    expense_ratio = Decimal("0.005")
    management_fee = None
    custody_fee = None


def test_build_detail_curve_normalizes_and_tracks_drawdown() -> None:
    rows = [
        Bar(date(2026, 1, 1), "1.00"),
        Bar(date(2026, 1, 2), "1.20"),
        Bar(date(2026, 1, 3), "1.08"),
    ]

    curve = build_detail_curve(rows)

    assert curve[0]["normalized_value"] == Decimal("100.0000")
    assert curve[1]["normalized_value"] == Decimal("120.0000")
    assert curve[2]["drawdown"] == Decimal("-0.100000")


def test_recommendation_score_uses_tradability_size_and_fee() -> None:
    score = recommendation_score(Asset(), {"tradability_score": 80})

    assert score >= 80
    assert recommendation_level(score, current_score=70) == "首选关注"
