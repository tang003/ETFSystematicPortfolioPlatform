from datetime import date
from decimal import Decimal

from app.services.etf_detail_service import build_detail_curve


class Bar:
    def __init__(self, trade_date: date, close: str, amount: str = "10000000") -> None:
        self.trade_date = trade_date
        self.close = Decimal(close)
        self.amount = Decimal(amount)


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
