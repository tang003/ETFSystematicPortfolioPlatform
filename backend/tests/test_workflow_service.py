from datetime import date, datetime
from decimal import Decimal

import pytest

from app.schemas.workflow_schema import HistoricalMarketInitRequest
from app.services.asset_service import CURATED_ETF_SYMBOLS
from app.services.workflow_service import (
    HISTORICAL_MARKET_INIT_STEPS,
    WORKFLOW_STEPS,
    WorkflowStepValidationError,
    historical_init_dates,
    json_ready,
    require_run_id,
    resolve_historical_init_symbols,
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


def test_historical_init_dates_defaults_to_requested_year_window() -> None:
    request = HistoricalMarketInitRequest(end_date=date(2026, 7, 13), years=10)

    start_date, end_date = historical_init_dates(request)

    assert end_date == date(2026, 7, 13)
    assert start_date == date(2016, 7, 5)


def test_resolve_historical_init_symbols_uses_curated_pool() -> None:
    request = HistoricalMarketInitRequest(scope="curated", max_symbols=3)

    assert resolve_historical_init_symbols(None, request) == CURATED_ETF_SYMBOLS[:3]


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
