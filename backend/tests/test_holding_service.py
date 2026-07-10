from decimal import Decimal

from app.schemas.portfolio_schema import PortfolioPositionUpsert
from app.services.holding_service import normalize_position_input, suggest_action


def test_suggest_action_add_reduce_hold_and_exit() -> None:
    assert suggest_action(Decimal("0.10"), Decimal("0.20")) == "ADD"
    assert suggest_action(Decimal("0.30"), Decimal("0.20")) == "REDUCE"
    assert suggest_action(Decimal("0.205"), Decimal("0.20")) == "HOLD"
    assert suggest_action(Decimal("0.10"), Decimal("0")) == "REDUCE_OR_EXIT"


def test_normalize_position_input_calculates_broker_fields() -> None:
    item = PortfolioPositionUpsert(
        symbol="513050",
        position_name="中概互联",
        asset_type="etf",
        quantity=Decimal("1700"),
        current_price=Decimal("1.092"),
        cost_price=Decimal("1.151"),
    )

    result = normalize_position_input(item)

    assert result["market_value"] == Decimal("1856.4000")
    assert result["cost_basis"] == Decimal("1956.7000")
    assert result["unrealized_pnl"] == Decimal("-100.3000")
    assert result["unrealized_pnl_rate"] == Decimal("-0.051260")
