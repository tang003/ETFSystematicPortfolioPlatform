from datetime import date, datetime
from decimal import Decimal

import pytest

from app.schemas.workflow_schema import HistoricalMarketInitRequest, MarketRepairRequest, WorkflowRunRequest
from app.services.asset_service import CURATED_ETF_SYMBOLS
from app.services.workflow_service import (
    HISTORICAL_MARKET_INIT_STEPS,
    MARKET_REPAIR_STEPS,
    WORKFLOW_STEPS,
    WorkflowStepValidationError,
    default_workflow_end_date,
    historical_init_dates,
    json_ready,
    require_run_id,
    resolve_historical_init_symbols,
    resolve_market_repair_symbols,
    resolve_workflow_dates,
    resolve_workflow_symbols,
    summarize_result,
    validate_batch_result,
)


def test_json_ready_serializes_dates_and_decimals() -> None:
    payload = {
        "trade_date": date(2026, 7, 9),
        "created_at": datetime(2026, 7, 9, 10, 30),
        "weight": Decimal("0.123456"),
        "items": [{"amount": Decimal("1000.00")}],
    }

    assert json_ready(payload) == {
        "trade_date": "2026-07-09",
        "created_at": "2026-07-09T10:30:00",
        "weight": "0.123456",
        "items": [{"amount": "1000.00"}],
    }


def test_summarize_result_picks_key_fields() -> None:
    summary = summarize_result({"status": "success", "run_id": 12, "target_count": 4, "ignored": "x"})

    assert summary == "status=success，run_id=12，target_count=4"


def test_workflow_steps_keep_expected_order() -> None:
    assert [step[0] for step in WORKFLOW_STEPS] == [
        "calendar",
        "market",
        "quality",
        "factors",
        "strategy",
        "risk",
        "rebalance",
        "report",
    ]


def test_historical_market_init_steps_keep_expected_order() -> None:
    assert [step[0] for step in HISTORICAL_MARKET_INIT_STEPS] == ["calendar", "market", "quality"]


def test_market_repair_steps_keep_expected_order() -> None:
    assert [step[0] for step in MARKET_REPAIR_STEPS] == ["calendar", "market", "quality"]


def test_historical_init_dates_defaults_to_requested_year_window() -> None:
    request = HistoricalMarketInitRequest(end_date=date(2026, 7, 13), years=10)

    start_date, end_date = historical_init_dates(request)

    assert end_date == date(2026, 7, 13)
    assert start_date == date(2016, 7, 5)


def test_resolve_historical_init_symbols_uses_curated_pool() -> None:
    request = HistoricalMarketInitRequest(scope="curated", max_symbols=3)

    assert resolve_historical_init_symbols(None, request) == CURATED_ETF_SYMBOLS[:3]


def test_resolve_market_repair_symbols_respects_limit() -> None:
    request = MarketRepairRequest(
        symbols=["510300", "513500", "159915"],
        start_date=date(2026, 1, 1),
        end_date=date(2026, 7, 13),
        max_symbols=2,
    )

    assert resolve_market_repair_symbols(request) == ["510300", "513500"]


def test_resolve_workflow_symbols_uses_scope_when_symbols_are_blank(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.workflow_service.resolve_symbols", lambda db, symbols, sync_scope="enabled": ["510300", "159915", "513500"])

    assert resolve_workflow_symbols(None, None, 2, "core") == ["510300", "159915"]


def test_resolve_workflow_symbols_prefers_custom_symbols(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = {}

    def fake_resolve_symbols(db, symbols, sync_scope="enabled"):
        captured["symbols"] = symbols
        captured["sync_scope"] = sync_scope
        return symbols

    monkeypatch.setattr("app.services.workflow_service.resolve_symbols", fake_resolve_symbols)

    assert resolve_workflow_symbols(None, ["513500", "513100"], 10, "custom") == ["513500", "513100"]
    assert captured == {"symbols": ["513500", "513100"], "sync_scope": "enabled"}


def test_resolve_workflow_dates_uses_fixed_preset() -> None:
    request = WorkflowRunRequest(date_preset="6m", end_date=date(2026, 7, 13))

    start_date, end_date = resolve_workflow_dates(None, request, ["510300"])

    assert start_date == date(2026, 1, 11)
    assert end_date == date(2026, 7, 13)


def test_resolve_workflow_dates_requires_custom_start_date() -> None:
    request = WorkflowRunRequest(date_preset="custom", end_date=date(2026, 7, 13))

    with pytest.raises(ValueError, match="开始日期"):
        resolve_workflow_dates(None, request, ["510300"])


def test_resolve_workflow_dates_uses_inception_date(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.workflow_service.earliest_asset_start_date", lambda db, symbols: date(2012, 5, 28))
    request = WorkflowRunRequest(date_preset="inception", end_date=date(2026, 7, 13))

    start_date, end_date = resolve_workflow_dates(None, request, ["510300"])

    assert start_date == date(2012, 5, 28)
    assert end_date == date(2026, 7, 13)


def test_default_workflow_end_date_prefers_completed_trade_date() -> None:
    class FakeDb:
        def scalar(self, statement):
            return date(2026, 7, 13)

    assert default_workflow_end_date(FakeDb()) == date(2026, 7, 13)


def test_require_run_id_rejects_missing_value() -> None:
    try:
        require_run_id(None)
    except ValueError as exc:
        assert "run_id" in str(exc)
    else:
        raise AssertionError("require_run_id should fail when run_id is missing")


def test_validate_batch_result_rejects_total_failure() -> None:
    result = {"total_symbols": 2, "success_count": 0, "failed_count": 2}

    with pytest.raises(WorkflowStepValidationError, match="全部失败") as exc_info:
        validate_batch_result("行情同步", result, strict=True)

    assert exc_info.value.result == result


def test_validate_batch_result_rejects_partial_failure_in_strict_mode() -> None:
    result = {"total_symbols": 3, "success_count": 2, "failed_count": 1}

    with pytest.raises(WorkflowStepValidationError, match="严格数据门禁"):
        validate_batch_result("因子计算", result, strict=True)


def test_validate_batch_result_allows_partial_failure_when_not_strict() -> None:
    validate_batch_result(
        "行情同步",
        {"total_symbols": 3, "success_count": 2, "failed_count": 1},
        strict=False,
    )
