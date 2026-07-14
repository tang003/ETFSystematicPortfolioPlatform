from datetime import date, timedelta
from decimal import Decimal

from app.services import tracking_service


def test_resolve_index_code_handles_common_cn_indices() -> None:
    assert tracking_service.resolve_index_code("沪深300指数收益率×100%") == "000300.SH"
    assert tracking_service.resolve_index_code("中证A500指数收益率") == "000510.SH"
    assert tracking_service.resolve_index_code("创业板指") == "399006.SZ"


def test_build_index_bar_payload_uses_prefixed_symbol() -> None:
    row = tracking_service.build_index_bar_payload(
        "000300.SH",
        {
            "trade_date": "20260713",
            "open": "4745.43",
            "high": "4775.23",
            "low": "4670.24",
            "close": "4695.38",
            "vol": "278634853",
            "amount": "907944700",
        },
    )

    assert row is not None
    assert row["symbol"] == "IDX:000300.SH"
    assert row["trade_date"] == date(2026, 7, 13)
    assert row["close"] == Decimal("4695.38")
    assert row["data_status"] == "index"


def test_calculate_tracking_error_from_overlapping_returns(monkeypatch) -> None:
    start = date(2026, 1, 1)
    etf_returns = {start + timedelta(days=index): 0.01 + index * 0.00001 for index in range(80)}
    index_returns = {start + timedelta(days=index): 0.009 + index * 0.000008 for index in range(80)}

    def fake_returns(db, *, symbol, start_date, end_date):
        return etf_returns if symbol == "510300" else index_returns

    monkeypatch.setattr(tracking_service, "load_returns_by_date", fake_returns)

    result = tracking_service.calculate_tracking_error(
        None,
        etf_symbol="510300",
        index_code="000300.SH",
        start_date=start,
        end_date=start + timedelta(days=100),
    )

    assert result is not None
    assert result > Decimal("0")
