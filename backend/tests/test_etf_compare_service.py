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


def test_screen_etfs_filters_and_sorts_candidates(monkeypatch) -> None:
    monkeypatch.setattr(etf_compare_service, "resolve_screen_symbols", lambda db, scope, symbols: ["510300", "159915"])
    monkeypatch.setattr(etf_compare_service, "load_asset_meta", lambda db, symbols: {"510300": Asset(), "159915": Asset()})
    monkeypatch.setattr(
        etf_compare_service,
        "load_clean_bars_for_symbols",
        lambda db, symbols, start_date, end_date: {"510300": [], "159915": []},
    )

    def fake_metric(symbol, rows, asset):
        base = {
            "symbol": symbol,
            "asset_class": "equity",
            "asset_region": "CN",
            "bars": 250,
            "tradability_score": 80,
            "buy_score": 60,
            "sharpe_ratio": Decimal("0.5"),
            "annualized_return": Decimal("0.08"),
        }
        if symbol == "159915":
            base["buy_score"] = 82
            base["sharpe_ratio"] = Decimal("1.2")
        return base

    monkeypatch.setattr(etf_compare_service, "build_compare_metric", fake_metric)

    result = etf_compare_service.screen_etfs(db=None, scope="enabled", limit=10, min_buy_score=70)

    assert result["total_candidates"] == 2
    assert result["returned"] == 1
    assert [item["symbol"] for item in result["metrics"]] == ["159915"]


def test_auto_sync_missing_bars_syncs_limited_missing_symbols(monkeypatch) -> None:
    calls = []

    def fake_sync(db, **kwargs):
        calls.append(kwargs)
        return {"success_count": len(kwargs["symbols"])}

    def fake_load(db, symbols, start_date, end_date):
        return {symbol: [Bar(date(2026, 1, 1), "1.00")] for symbol in symbols}

    monkeypatch.setattr(etf_compare_service, "sync_market_data", fake_sync)
    monkeypatch.setattr(etf_compare_service, "load_clean_bars_for_symbols", fake_load)

    result = etf_compare_service.auto_sync_missing_bars(
        None,
        symbols=["513500", "159612", "510300"],
        bars_by_symbol={"510300": [Bar(date(2026, 1, 1), "1.00")] * 30},
        start_date=date(2026, 1, 1),
        end_date=date(2026, 7, 1),
        min_bars=20,
        max_symbols=1,
    )

    assert calls[0]["symbols"] == ["513500"]
    assert calls[0]["source"] == "tushare"
    assert len(result["513500"]) == 1
    assert "159612" not in result
