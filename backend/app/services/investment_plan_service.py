from datetime import date
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.database import Base, engine
from app.models.portfolio import InvestmentPlan, InvestmentPlanSuggestion, TargetPortfolio
from app.schemas.portfolio_schema import InvestmentPlanCreate
from app.services.holding_service import current_weight_map
from app.services.strategy_service import latest_target_portfolio


MIN_MONTHS = 1
MAX_MONTHS = 360


def ensure_investment_plan_tables() -> None:
    Base.metadata.create_all(bind=engine, tables=[InvestmentPlan.__table__, InvestmentPlanSuggestion.__table__])


def create_investment_plan(db: Session, request: InvestmentPlanCreate) -> InvestmentPlan:
    ensure_investment_plan_tables()
    if request.months < MIN_MONTHS or request.months > MAX_MONTHS:
        raise ValueError("Months must be between 1 and 360")
    if request.monthly_amount <= 0:
        raise ValueError("Monthly amount must be greater than 0")

    plan = InvestmentPlan(
        plan_name=request.plan_name.strip() or "定投计划",
        run_id=request.run_id,
        start_date=request.start_date,
        months=request.months,
        monthly_amount=request.monthly_amount,
        total_budget=(request.monthly_amount * request.months).quantize(Decimal("0.0001")),
        status="active",
        note=request.note,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def list_investment_plans(db: Session, limit: int = 50) -> list[InvestmentPlan]:
    ensure_investment_plan_tables()
    return list(db.scalars(select(InvestmentPlan).order_by(InvestmentPlan.created_at.desc()).limit(limit)).all())


def analyze_investment_plan(
    db: Session,
    *,
    plan_id: int,
    period_no: int = 1,
    suggestion_date: date | None = None,
) -> list[InvestmentPlanSuggestion]:
    ensure_investment_plan_tables()
    plan = db.get(InvestmentPlan, plan_id)
    if plan is None:
        raise ValueError("Investment plan not found")
    if period_no < 1 or period_no > plan.months:
        raise ValueError("Period number must be within the plan months")

    targets = resolve_plan_targets(db, plan.run_id)
    if not targets:
        raise ValueError("No target portfolio available for investment plan")

    resolved_run_id = plan.run_id or targets[0].run_id
    resolved_date = suggestion_date or date.today()
    current_weights = current_weight_map(db)
    rows = build_investment_suggestions(
        plan_id=plan.id,
        run_id=resolved_run_id,
        suggestion_date=resolved_date,
        period_no=period_no,
        monthly_amount=Decimal(plan.monthly_amount),
        targets=targets,
        current_weights=current_weights,
    )

    db.execute(
        delete(InvestmentPlanSuggestion).where(
            InvestmentPlanSuggestion.plan_id == plan.id,
            InvestmentPlanSuggestion.period_no == period_no,
        )
    )
    db.add_all(rows)
    db.commit()
    return list_investment_suggestions(db, plan_id=plan.id, period_no=period_no)


def list_investment_suggestions(
    db: Session,
    *,
    plan_id: int | None = None,
    period_no: int | None = None,
    limit: int = 100,
) -> list[InvestmentPlanSuggestion]:
    ensure_investment_plan_tables()
    query = select(InvestmentPlanSuggestion)
    if plan_id is not None:
        query = query.where(InvestmentPlanSuggestion.plan_id == plan_id)
    if period_no is not None:
        query = query.where(InvestmentPlanSuggestion.period_no == period_no)
    query = query.order_by(InvestmentPlanSuggestion.suggested_amount.desc()).limit(limit)
    return list(db.scalars(query).all())


def resolve_plan_targets(db: Session, run_id: int | None) -> list[TargetPortfolio]:
    if run_id is None:
        return latest_target_portfolio(db)
    return list(
        db.scalars(
            select(TargetPortfolio)
            .where(TargetPortfolio.run_id == run_id)
            .order_by(TargetPortfolio.final_target_weight.desc().nullslast())
        ).all()
    )


def build_investment_suggestions(
    *,
    plan_id: int,
    run_id: int | None,
    suggestion_date: date,
    period_no: int,
    monthly_amount: Decimal,
    targets: list[TargetPortfolio],
    current_weights: dict[str, Decimal],
) -> list[InvestmentPlanSuggestion]:
    target_weights = {
        item.symbol: Decimal(item.final_target_weight or item.raw_target_weight or 0)
        for item in targets
        if Decimal(item.final_target_weight or item.raw_target_weight or 0) > 0
    }
    positive_gaps = {
        symbol: (target - current_weights.get(symbol, Decimal("0")))
        for symbol, target in target_weights.items()
        if (target - current_weights.get(symbol, Decimal("0"))) > 0
    }
    allocation_base = sum(positive_gaps.values(), Decimal("0"))

    if allocation_base <= 0:
        allocation_base = sum(target_weights.values(), Decimal("0"))
        positive_gaps = dict(target_weights)

    rows: list[InvestmentPlanSuggestion] = []
    remaining = monthly_amount.quantize(Decimal("0.0001"))
    symbols = list(positive_gaps.keys())
    for index, symbol in enumerate(symbols):
        gap = positive_gaps[symbol]
        if index == len(symbols) - 1:
            amount = remaining
        else:
            amount = (monthly_amount * gap / allocation_base).quantize(Decimal("0.0001"))
            remaining -= amount
        target = target_weights[symbol]
        current = current_weights.get(symbol, Decimal("0"))
        rows.append(
            InvestmentPlanSuggestion(
                plan_id=plan_id,
                run_id=run_id,
                suggestion_date=suggestion_date,
                period_no=period_no,
                symbol=symbol,
                target_weight=target.quantize(Decimal("0.000001")),
                current_weight=current.quantize(Decimal("0.000001")),
                gap_weight=(target - current).quantize(Decimal("0.000001")),
                suggested_amount=amount,
                action_suggestion="INVEST",
                reason=build_investment_reason(symbol, current, target, amount),
            )
        )
    return rows


def build_investment_reason(symbol: str, current: Decimal, target: Decimal, amount: Decimal) -> str:
    if target > current:
        return f"{symbol} 当前权重低于目标权重，优先分配本期定投资金 {amount} 元。"
    return f"{symbol} 当前权重未低于目标权重，按目标权重分配本期定投资金 {amount} 元。"
