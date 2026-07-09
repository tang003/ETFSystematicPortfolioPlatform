from decimal import Decimal

from app.services.holding_service import suggest_action


def test_suggest_action_add_reduce_hold_and_exit() -> None:
    assert suggest_action(Decimal("0.10"), Decimal("0.20")) == "ADD"
    assert suggest_action(Decimal("0.30"), Decimal("0.20")) == "REDUCE"
    assert suggest_action(Decimal("0.205"), Decimal("0.20")) == "HOLD"
    assert suggest_action(Decimal("0.10"), Decimal("0")) == "REDUCE_OR_EXIT"
