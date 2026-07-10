from datetime import date
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.database import Base, engine
from app.models.factor import FactorDaily
from app.models.portfolio import HoldingAnalysisResult, PortfolioPosition, TargetPortfolio
from app.schemas.portfolio_schema import PortfolioSnapshotRequest
from app.services.strategy_service import latest_target_portfolio

MIN_ACTION_DIFF = Decimal("0.03")


def ensure_holding_tables() -> None:
    Base.metadata.create_all(bind=engine, tables=[HoldingAnalysisResult.__table__])


def upsert_position_snapshot(db: Session, request: PortfolioSnapshotRequest) -> list[PortfolioPosition]:
    db.execute(delete(PortfolioPosition).where(PortfolioPosition.position_date == request.position_date))
    normalized = [normalize_position_input(item) for item in request.positions if item.symbol.strip()]
    total_value = sum((item["market_value"] for item in normalized), Decimal("0"))
    if total_value <= 0:
        raise ValueError("Total market value must be greater than 0")

    rows = [
        PortfolioPosition(
            position_date=request.position_date,
            symbol=item["symbol"],
            position_name=item["position_name"],
            asset_type=item["asset_type"],
            quantity=item["quantity"],
            current_price=item["current_price"],
            cost_price=item["cost_price"],
            market_value=item["market_value"],
            weight=(item["market_value"] / total_value).quantize(Decimal("0.000001")),
            cost_basis=item["cost_basis"],
            unrealized_pnl=item["unrealized_pnl"],
            unrealized_pnl_rate=item["unrealized_pnl_rate"],
        )
        for item in normalized
    ]
    db.add_all(rows)
    db.commit()
    return list_positions(db, position_date=request.position_date)


def normalize_position_input(item) -> dict:
    quantity = item.quantity or Decimal("0")
    current_price = item.current_price
    cost_price = item.cost_price
    market_value = item.market_value
    cost_basis = item.cost_basis

    if market_value is None and quantity > 0 and current_price is not None:
        market_value = (quantity * current_price).quantize(Decimal("0.0001"))
    if cost_basis is None and quantity > 0 and cost_price is not None:
        cost_basis = (quantity * cost_price).quantize(Decimal("0.0001"))
    if current_price is None and quantity > 0 and market_value is not None:
        current_price = (market_value / quantity).quantize(Decimal("0.000001"))
    if cost_price is None and quantity > 0 and cost_basis is not None:
        cost_price = (cost_basis / quantity).quantize(Decimal("0.000001"))
    if market_value is None or market_value <= 0:
        raise ValueError(f"Position {item.symbol} must provide market_value or quantity/current_price")

    unrealized_pnl = None
    unrealized_pnl_rate = None
    if cost_basis is not None and cost_basis > 0:
        unrealized_pnl = (market_value - cost_basis).quantize(Decimal("0.0001"))
        unrealized_pnl_rate = (unrealized_pnl / cost_basis).quantize(Decimal("0.000001"))

    return {
        "symbol": item.symbol.strip(),
        "position_name": item.position_name.strip() if item.position_name else None,
        "asset_type": (item.asset_type or "etf").strip().lower(),
        "quantity": quantity,
        "current_price": current_price,
        "cost_price": cost_price,
        "market_value": market_value,
        "cost_basis": cost_basis,
        "unrealized_pnl": unrealized_pnl,
        "unrealized_pnl_rate": unrealized_pnl_rate,
    }


def latest_position_date(db: Session) -> date | None:
    return db.scalar(select(func.max(PortfolioPosition.position_date)))


def list_positions(db: Session, position_date: date | None = None) -> list[PortfolioPosition]:
    resolved_date = position_date or latest_position_date(db)
    if resolved_date is None:
        return []
    return list(
        db.scalars(
            select(PortfolioPosition)
            .where(PortfolioPosition.position_date == resolved_date)
            .order_by(PortfolioPosition.weight.desc().nullslast())
        ).all()
    )


def current_weight_map(db: Session, position_date: date | None = None) -> dict[str, Decimal]:
    return {item.symbol: Decimal(item.weight or 0) for item in list_positions(db, position_date=position_date)}


def analyze_holdings(
    db: Session,
    *,
    run_id: int | None = None,
    analysis_date: date | None = None,
) -> list[HoldingAnalysisResult]:
    ensure_holding_tables()
    targets = resolve_targets(db, run_id)
    if not targets:
        raise ValueError("No target portfolio available for holding analysis")
    resolved_run_id = targets[0].run_id
    resolved_date = analysis_date or targets[0].portfolio_date
    current_weights = current_weight_map(db)
    target_weights = {item.symbol: Decimal(item.final_target_weight or item.raw_target_weight or 0) for item in targets}
    symbols = sorted(set(current_weights) | set(target_weights))
    alpha_scores = latest_alpha_scores(db)

    db.execute(delete(HoldingAnalysisResult).where(HoldingAnalysisResult.run_id == resolved_run_id))
    rows = []
    for symbol in symbols:
        current = current_weights.get(symbol, Decimal("0"))
        target = target_weights.get(symbol, Decimal("0"))
        diff = target - current
        rows.append(
            HoldingAnalysisResult(
                run_id=resolved_run_id,
                analysis_date=resolved_date,
                symbol=symbol,
                current_weight=current.quantize(Decimal("0.000001")),
                target_weight=target.quantize(Decimal("0.000001")),
                weight_diff=diff.quantize(Decimal("0.000001")),
                action_suggestion=suggest_action(current, target),
                alpha_score=alpha_scores.get(symbol),
                reason=build_reason(symbol, current, target, diff, alpha_scores.get(symbol)),
            )
        )
    db.add_all(rows)
    db.commit()
    return list_holding_analysis(db, run_id=resolved_run_id)


def list_holding_analysis(db: Session, run_id: int | None = None, limit: int = 100) -> list[HoldingAnalysisResult]:
    ensure_holding_tables()
    resolved_run_id = run_id or db.scalar(select(HoldingAnalysisResult.run_id).order_by(HoldingAnalysisResult.created_at.desc()).limit(1))
    if resolved_run_id is None:
        return []
    return list(
        db.scalars(
            select(HoldingAnalysisResult)
            .where(HoldingAnalysisResult.run_id == resolved_run_id)
            .order_by(HoldingAnalysisResult.weight_diff.desc().nullslast())
            .limit(limit)
        ).all()
    )


def resolve_targets(db: Session, run_id: int | None) -> list[TargetPortfolio]:
    if run_id is None:
        return latest_target_portfolio(db)
    return list(
        db.scalars(
            select(TargetPortfolio)
            .where(TargetPortfolio.run_id == run_id)
            .order_by(TargetPortfolio.final_target_weight.desc().nullslast())
        ).all()
    )


def latest_alpha_scores(db: Session) -> dict[str, Decimal]:
    latest_date = db.scalar(select(FactorDaily.trade_date).order_by(FactorDaily.trade_date.desc()).limit(1))
    if latest_date is None:
        return {}
    rows = db.scalars(select(FactorDaily).where(FactorDaily.trade_date == latest_date)).all()
    return {row.symbol: row.alpha_score for row in rows if row.alpha_score is not None}


def suggest_action(current: Decimal, target: Decimal) -> str:
    diff = target - current
    if target == 0 and current > 0:
        return "REDUCE_OR_EXIT"
    if diff >= MIN_ACTION_DIFF:
        return "ADD"
    if diff <= -MIN_ACTION_DIFF:
        return "REDUCE"
    return "HOLD"


def build_reason(symbol: str, current: Decimal, target: Decimal, diff: Decimal, alpha_score: Decimal | None) -> str:
    alpha_text = f"alpha_score={alpha_score}" if alpha_score is not None else "暂无 alpha_score"
    if target == 0 and current > 0:
        return f"{symbol} 不在目标组合中，当前仍有持仓，建议考虑减仓或退出；{alpha_text}"
    if diff >= MIN_ACTION_DIFF:
        return f"当前权重低于目标权重 {diff:.2%}，建议考虑加仓；{alpha_text}"
    if diff <= -MIN_ACTION_DIFF:
        return f"当前权重高于目标权重 {abs(diff):.2%}，建议考虑减仓；{alpha_text}"
    return f"当前权重接近目标权重，建议继续持有；{alpha_text}"
