from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from app.services import market_service


def test_eastmoney_secid_uses_exchange_prefix() -> None:
    assert market_service.eastmoney_secid("510300") == "1.510300"
    assert market_service.eastmoney_secid("159915") == "0.159915"


def test_eastmoney_scaled_price_handles_scaled_quote() -> None:
    assert market_service.eastmoney_scaled_price("1092") == Decimal("1.092000")
    assert market_service.eastmoney_scaled_price("1.092") == Decimal("1.092000")
    assert market_service.eastmoney_scaled_price("-") is None


def test_limit_symbols_returns_selected_and_skipped_count() -> None:
    selected, skipped = market_service.limit_symbols(["510300", "510500", "159915"], 2)
    assert selected == ["510300", "510500"]
    assert skipped == 1


def test_limit_symbols_rejects_invalid_limit() -> None:
    with pytest.raises(ValueError, match="max_symbols"):
        market_service.limit_symbols(["510300"], 0)


def test_merge_symbol_groups_dedupes_by_priority() -> None:
    assert market_service.merge_symbol_groups(
        ["513050", "510300"],
        ["510300", "159915"],
        ["513050", "511010"],
    ) == ["513050", "510300", "159915", "511010"]


def test_resolve_scoped_symbols_core_merges_priority_groups(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(market_service, "latest_position_symbols", lambda db: ["513050", "510300"])
    monkeypatch.setattr(market_service, "latest_target_symbols", lambda db: ["510300", "159915"])
    monkeypatch.setattr(market_service, "plan_suggestion_symbols", lambda db: ["511010"])
    monkeypatch.setattr(market_service, "enabled_asset_symbols", lambda db: ["510300", "588000"])

    assert market_service.resolve_scoped_symbols(db=None, sync_scope="core") == [
        "513050",
        "510300",
        "159915",
        "511010",
        "588000",
    ]


def test_normalize_market_bars_from_english_columns() -> None:
    frame = pd.DataFrame(
        [
            {
                "date": "2026-07-01",
                "open": "5.009",
                "high": "5.054",
                "low": "4.957",
                "close": "4.998",
                "volume": "9626190",
                "amount": "4820926453",
            }
        ]
    )

    rows = market_service.normalize_market_bars("510300", frame)

    assert rows[0]["symbol"] == "510300"
    assert rows[0]["trade_date"] == date(2026, 7, 1)
    assert rows[0]["close"] == Decimal("4.998")
    assert rows[0]["amount"] == Decimal("4820926453")


def test_fetch_etf_daily_bars_falls_back_to_eastmoney(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_akshare(symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
        raise RuntimeError("akshare down")

    def ok_eastmoney(symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
        return pd.DataFrame([{"date": "2026-07-01", "open": "1", "high": "1", "low": "1", "close": "1"}])

    monkeypatch.setattr(market_service, "fetch_akshare_daily_bars", fail_akshare)
    monkeypatch.setattr(market_service, "fetch_eastmoney_daily_bars", ok_eastmoney)

    frame, source = market_service.fetch_etf_daily_bars("510300", date(2026, 7, 1), date(2026, 7, 2))

    assert source == "eastmoney"
    assert len(frame) == 1


def test_resolve_market_sync_window_uses_incremental_gap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(market_service, "latest_market_trade_date", lambda db, symbol: date(2026, 7, 3))

    sync_start, sync_end, up_to_date = market_service.resolve_market_sync_window(
        db=None,
        symbol="510300",
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 8),
        incremental=True,
    )

    assert sync_start == date(2026, 7, 4)
    assert sync_end == date(2026, 7, 8)
    assert up_to_date is False


def test_resolve_market_sync_window_marks_up_to_date(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(market_service, "latest_market_trade_date", lambda db, symbol: date(2026, 7, 8))

    sync_start, sync_end, up_to_date = market_service.resolve_market_sync_window(
        db=None,
        symbol="510300",
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 8),
        incremental=True,
    )

    assert sync_start == date(2026, 7, 1)
    assert sync_end == date(2026, 7, 8)
    assert up_to_date is True
