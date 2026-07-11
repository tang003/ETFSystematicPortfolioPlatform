from decimal import Decimal

from app.services.strategy_service import construct_target_weights, construct_target_weights_with_tradability, score_confidence


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


def test_construct_target_weights_excludes_low_tradability_equity() -> None:
    asset_map = {
        "510300": Asset("equity", 4),
        "510500": Asset("equity", 4),
        "159915": Asset("equity", 5),
        "511880": Asset("cash", 1),
    }
    tradability = {
        "510300": {"tradability_score": 30},
        "510500": {"tradability_score": 85},
        "159915": {"tradability_score": 90},
    }

    weights, adjustments = construct_target_weights_with_tradability(["510300", "510500", "159915"], asset_map, tradability)

    assert "510300" not in weights
    assert weights["510500"] == Decimal("0.400000")
    assert weights["159915"] == Decimal("0.250000")
    assert adjustments["510300"] == "excluded_by_tradability_score<40"


def test_construct_target_weights_reduces_weak_tradability_equity_to_cash() -> None:
    asset_map = {
        "510300": Asset("equity", 4),
        "510500": Asset("equity", 4),
        "511880": Asset("cash", 1),
    }
    tradability = {
        "510300": {"tradability_score": 50},
        "510500": {"tradability_score": 90},
    }

    weights, adjustments = construct_target_weights_with_tradability(["510300", "510500"], asset_map, tradability)

    assert weights["510300"] == Decimal("0.200000")
    assert weights["511880"] == Decimal("0.550000")
    assert adjustments["510300"] == "reduced_by_tradability_score<60"


def test_score_confidence_is_bounded() -> None:
    assert score_confidence(None) == Decimal("0.5000")
    assert score_confidence(Decimal("10")) == Decimal("0.3000")
    assert score_confidence(Decimal("120")) == Decimal("0.9500")
    assert score_confidence(Decimal("72.3456")) == Decimal("0.7235")
