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
    assert metric["sharpe_ratio"] is not None
    assert metric["positive_day_rate"] == Decimal("0.500000")
    assert metric["buy_score"] >= 0
    assert metric["buy_level"] in {"优先候选", "可观察", "谨慎观察", "暂不优先"}


def test_correlation_uses_overlapping_return_dates() -> None:
    left = {date(2026, 1, 2): 0.01, date(2026, 1, 3): 0.02, date(2026, 1, 4): 0.03}
    right = {date(2026, 1, 2): 0.02, date(2026, 1, 3): 0.04, date(2026, 1, 4): 0.06}

    assert etf_compare_service.quantize_rate(etf_compare_service.correlation(left, right)) == Decimal("1.000000")


def test_score_etf_tradability_keeps_symbols_without_bars(monkeypatch) -> None:
    monkeypatch.setattr(etf_compare_service, "load_asset_meta", lambda db, symbols: {})
    monkeypatch.setattr(
        etf_compare_service,
        "load_clean_bars_for_symbols",
        lambda db, symbols, start_date, end_date: {"510300": [Bar(date(2026, 1, 1), "1.00")]},
    )

    rows = etf_compare_service.score_etf_tradability(
        db=None,
        symbols=["510300", "159915"],
        end_date=date(2026, 1, 2),
    )

    assert [item["symbol"] for item in rows] == ["510300", "159915"]
    assert rows[1]["bars"] == 0
