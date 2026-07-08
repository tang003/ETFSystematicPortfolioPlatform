from datetime import date
from decimal import Decimal

from app.services.risk_service import (
    apply_max_asset_class_weight,
    apply_max_single_weight,
    apply_min_asset_class_weight,
    normalize_weights,
    rebalance_action,
)


class Target:
    def __init__(self, symbol: str, asset_class: str, portfolio_date: date = date(2026, 7, 8)) -> None:
        self.symbol = symbol
        self.asset_class = asset_class
        self.portfolio_date = portfolio_date


def test_apply_max_single_weight_moves_excess_to_cash() -> None:
    weights = {"510300": Decimal("0.70"), "511880": Decimal("0.30")}
    logs = []

    apply_max_single_weight(weights, logs, 1, date(2026, 7, 8), Decimal("0.50"))

    assert weights["510300"] == Decimal("0.50")
    assert weights["511880"] == Decimal("0.50")
    assert logs[0].rule_code == "max_single_weight"


def test_apply_max_asset_class_weight_scales_equity() -> None:
    weights = {"510300": Decimal("0.50"), "510500": Decimal("0.40"), "511880": Decimal("0.10")}
    targets = [Target("510300", "equity"), Target("510500", "equity"), Target("511880", "cash")]
    logs = []

    apply_max_asset_class_weight(
        weights,
        targets,
        logs,
        1,
        date(2026, 7, 8),
        asset_class="equity",
        rule_code="max_equity_weight",
        threshold=Decimal("0.80"),
    )

    assert (weights["510300"] + weights["510500"]).quantize(Decimal("0.000001")) == Decimal("0.800000")
    assert weights["511880"].quantize(Decimal("0.000001")) == Decimal("0.200000")
    assert logs[0].rule_code == "max_equity_weight"


def test_apply_min_asset_class_weight_raises_defense() -> None:
    weights = {"510300": Decimal("0.80"), "511010": Decimal("0.10"), "511880": Decimal("0.10")}
    targets = [Target("510300", "equity"), Target("511010", "bond"), Target("511880", "cash")]
    logs = []

    apply_min_asset_class_weight(
        weights,
        targets,
        logs,
        1,
        date(2026, 7, 8),
        asset_classes={"bond", "gold"},
        rule_code="min_defense_weight",
        threshold=Decimal("0.20"),
    )
    normalize_weights(weights)

    assert weights["511010"].quantize(Decimal("0.000001")) == Decimal("0.200000")
    assert sum(weights.values()).quantize(Decimal("0.000001")) == Decimal("1.000000")


def test_rebalance_action_uses_minimum_diff() -> None:
    assert rebalance_action(Decimal("0.049")) == "HOLD"
    assert rebalance_action(Decimal("0.050")) == "BUY"
    assert rebalance_action(Decimal("-0.050")) == "SELL"

