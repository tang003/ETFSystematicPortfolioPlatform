from datetime import date
from decimal import Decimal

from app.services import etf_compare_service


class Bar:
    def __init__(self, trade_date: date, close: str, amount: str = "80000000", volume: str = "1000000") -> None:
        self.trade_date = trade_date
        self.close = Decimal(close)
        self.amount = Decimal(amount)
        self.volume = Decimal(volume)


class Asset:
    name = "沪深300ETF"
    asset_class = "equity"
    asset_region = "CN"
    risk_level = 4


def test_build_compare_metric_calculates_return_and_drawdown() -> None:
    rows = [
        Bar(date(2026, 1, 1), "1.00"),
        Bar(date(2026, 1, 2), "1.10"),
        Bar(date(2026, 1, 3), "1.05"),
    ]

    metric = etf_compare_service.build_compare_metric("510300", rows, Asset())

    assert metric["symbol"] == "510300"
    assert metric["total_return"] == Decimal("0.050000")
    assert metric["max_drawdown"] == Decimal("-0.045455")
    assert metric["tradability_score"] == 75


def test_correlation_uses_overlapping_return_dates() -> None:
    left = {date(2026, 1, 2): 0.01, date(2026, 1, 3): 0.02, date(2026, 1, 4): 0.03}
    right = {date(2026, 1, 2): 0.02, date(2026, 1, 3): 0.04, date(2026, 1, 4): 0.06}

    assert etf_compare_service.quantize_rate(etf_compare_service.correlation(left, right)) == Decimal("1.000000")
