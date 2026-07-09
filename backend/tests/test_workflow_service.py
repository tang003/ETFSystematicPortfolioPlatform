from datetime import date, datetime
from decimal import Decimal

from app.services.workflow_service import WORKFLOW_STEPS, json_ready, summarize_result


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
