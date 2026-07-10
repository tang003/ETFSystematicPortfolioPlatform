from decimal import Decimal

from app.services.portfolio_xray_service import build_exposures


class Asset:
    def __init__(self, asset_class: str, asset_region: str, risk_level: int) -> None:
        self.asset_class = asset_class
        self.asset_region = asset_region
        self.risk_level = risk_level


def test_build_exposures_groups_current_and_target_weights() -> None:
    assets = {
        "510300": Asset("equity", "CN", 4),
        "511010": Asset("bond", "CN", 2),
        "513100": Asset("qdii", "US", 5),
    }

    rows = build_exposures(
        assets,
        current_weights={"510300": Decimal("0.60"), "511010": Decimal("0.40")},
        target_weights={"510300": Decimal("0.40"), "511010": Decimal("0.30"), "513100": Decimal("0.30")},
    )

    by_key = {(row.dimension, row.name): row for row in rows}
    assert by_key[("asset_class", "equity")].current_weight == Decimal("0.600000")
    assert by_key[("asset_class", "equity")].target_weight == Decimal("0.400000")
    assert by_key[("asset_class", "qdii")].target_weight == Decimal("0.300000")
    assert by_key[("asset_region", "US")].diff_weight == Decimal("0.300000")
    assert by_key[("risk_level", "R5")].target_weight == Decimal("0.300000")
