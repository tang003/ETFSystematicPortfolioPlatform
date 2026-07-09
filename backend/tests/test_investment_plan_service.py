from datetime import date
from decimal import Decimal

from app.services.investment_plan_service import build_investment_suggestions


class Target:
    def __init__(self, symbol: str, weight: str) -> None:
        self.symbol = symbol
        self.final_target_weight = Decimal(weight)
        self.raw_target_weight = Decimal(weight)


def test_build_investment_suggestions_prioritizes_underweight_assets() -> None:
    rows = build_investment_suggestions(
        plan_id=1,
        run_id=2,
        suggestion_date=date(2026, 7, 9),
        period_no=1,
        monthly_amount=Decimal("3000"),
        targets=[Target("510300", "0.40"), Target("511010", "0.25"), Target("511880", "0.35")],
        current_weights={"510300": Decimal("0.60"), "511880": Decimal("0.40")},
    )

    assert len(rows) == 1
    assert rows[0].symbol == "511010"
    assert rows[0].suggested_amount == Decimal("3000.0000")
    assert rows[0].action_suggestion == "INVEST"


def test_build_investment_suggestions_falls_back_to_target_weights_when_no_gap() -> None:
    rows = build_investment_suggestions(
        plan_id=1,
        run_id=2,
        suggestion_date=date(2026, 7, 9),
        period_no=1,
        monthly_amount=Decimal("1000"),
        targets=[Target("510300", "0.40"), Target("511880", "0.60")],
        current_weights={"510300": Decimal("0.50"), "511880": Decimal("0.70")},
    )

    assert [row.symbol for row in rows] == ["510300", "511880"]
    assert sum((row.suggested_amount for row in rows), Decimal("0")) == Decimal("1000.0000")
