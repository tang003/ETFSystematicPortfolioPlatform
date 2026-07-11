from decimal import Decimal

from app.schemas.portfolio_schema import PortfolioPositionUpsert
from app.schemas.portfolio_schema import PositionResolveRead
from app.services.holding_service import infer_asset_type, normalize_position_input, normalize_symbol, suggest_action


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


def test_normalize_position_input_uses_resolved_detail() -> None:
    item = PortfolioPositionUpsert(symbol="513050", quantity=Decimal("1700"), cost_price=Decimal("1.151"))
    detail = PositionResolveRead(
        symbol="513050",
        position_name="中概互联",
        asset_type="etf",
        current_price=Decimal("1.092"),
        price_date=None,
        resolved=True,
    )

    result = normalize_position_input(item, detail)

    assert result["position_name"] == "中概互联"
    assert result["asset_type"] == "etf"
    assert result["current_price"] == Decimal("1.092")
    assert result["market_value"] == Decimal("1856.4000")


def test_infer_asset_type_defaults_platform_assets_to_etf() -> None:
    assert infer_asset_type("stock") == "etf"
    assert infer_asset_type("equity") == "etf"
    assert infer_asset_type("cash") == "cash"
    assert infer_asset_type("cross_border") == "etf"
    assert infer_asset_type(None) == "etf"


def test_normalize_symbol_accepts_exchange_suffix() -> None:
    assert normalize_symbol("159928") == "159928"
    assert normalize_symbol("513050.SH") == "513050"
    assert normalize_symbol(" 159928.sz ") == "159928"
