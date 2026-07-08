from decimal import Decimal

from app.services.strategy_service import construct_target_weights, score_confidence


class Asset:
    def __init__(self, asset_class: str, risk_level: int = 3, enabled: bool = True) -> None:
        self.asset_class = asset_class
        self.risk_level = risk_level
        self.enabled = enabled


def test_construct_target_weights_normal_two_equity_case() -> None:
    asset_map = {
        "510300": Asset("equity", 4),
        "510500": Asset("equity", 4),
        "511010": Asset("bond", 1),
        "511880": Asset("cash", 1),
    }

    weights = construct_target_weights(["510300", "510500"], asset_map)

    assert weights == {
        "510300": Decimal("0.400000"),
        "510500": Decimal("0.250000"),
        "511010": Decimal("0.250000"),
        "511880": Decimal("0.100000"),
    }
    assert sum(weights.values()) == Decimal("1.000000")


def test_construct_target_weights_moves_missing_second_equity_to_cash() -> None:
    asset_map = {
        "510300": Asset("equity", 4),
        "511010": Asset("bond", 1),
        "511880": Asset("cash", 1),
    }

    weights = construct_target_weights(["510300"], asset_map)

    assert weights["510300"] == Decimal("0.400000")
    assert weights["511010"] == Decimal("0.250000")
    assert weights["511880"] == Decimal("0.350000")
    assert sum(weights.values()) == Decimal("1.000000")


def test_score_confidence_is_bounded() -> None:
    assert score_confidence(None) == Decimal("0.5000")
    assert score_confidence(Decimal("10")) == Decimal("0.3000")
    assert score_confidence(Decimal("120")) == Decimal("0.9500")
    assert score_confidence(Decimal("72.3456")) == Decimal("0.7235")

