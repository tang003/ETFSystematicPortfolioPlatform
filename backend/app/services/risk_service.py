from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.portfolio import TargetPortfolio
from app.models.rebalance import RebalanceOrder
from app.models.risk import RiskCheckResult, RiskRule
from app.services.holding_service import current_weight_map

MIN_REBALANCE_DIFF = Decimal("0.05")


def run_risk_check(db: Session, *, run_id: int) -> dict[str, Any]:
    targets = load_targets(db, run_id)
    if not targets:
        raise ValueError(f"No target portfolio found for run_id={run_id}")

    rules = load_rule_thresholds(db)
    before = {item.symbol: Decimal(item.final_target_weight or item.raw_target_weight or 0) for item in targets}
    adjusted = dict(before)
    logs: list[RiskCheckResult] = []
    check_date = targets[0].portfolio_date

    apply_max_single_weight(adjusted, logs, run_id, check_date, rules.get("max_single_weight", Decimal("0.50")))
    apply_max_asset_class_weight(
        adjusted,
        targets,
        logs,
        run_id,
        check_date,
        asset_class="equity",
        rule_code="max_equity_weight",
        threshold=rules.get("max_equity_weight", Decimal("0.80")),
    )
    apply_min_asset_class_weight(
        adjusted,
        targets,
        logs,
        run_id,
        check_date,
        asset_classes={"bond", "gold"},
        rule_code="min_defense_weight",
        threshold=rules.get("min_defense_weight", Decimal("0.20")),
    )
    apply_min_asset_class_weight(
        adjusted,
        targets,
        logs,
        run_id,
        check_date,
        asset_classes={"cash"},
        rule_code="min_cash_weight",
        threshold=rules.get("min_cash_weight", Decimal("0.05")),
    )
    normalize_weights(adjusted)

    for item in targets:
        item.final_target_weight = adjusted[item.symbol].quantize(Decimal("0.000001"))
        if item.final_target_weight != item.raw_target_weight:
            item.reason = f"{item.reason or ''}; risk_adjusted={item.final_target_weight}".strip("; ")

    if not logs:
        logs.append(
            RiskCheckResult(
                run_id=run_id,
                check_date=check_date,
                rule_code="all_rules",
                status="passed",
                message="No risk adjustment required",
                before_value=sum(before.values(), Decimal("0")),
                after_value=sum(adjusted.values(), Decimal("0")),
            )
        )

    db.add_all(logs)
    db.commit()
    return {
        "run_id": run_id,
        "check_date": check_date,
        "result_count": len(logs),
        "adjusted_count": sum(1 for item in targets if item.final_target_weight != item.raw_target_weight),
        "status": "success",
    }


def load_targets(db: Session, run_id: int) -> list[TargetPortfolio]:
    return list(
        db.scalars(
            select(TargetPortfolio)
            .where(TargetPortfolio.run_id == run_id)
            .order_by(TargetPortfolio.final_target_weight.desc().nullslast())
        ).all()
    )


def load_rule_thresholds(db: Session) -> dict[str, Decimal]:
    rules = db.scalars(select(RiskRule).where(RiskRule.enabled.is_(True))).all()
    return {rule.rule_code: Decimal(rule.threshold) for rule in rules if rule.threshold is not None}


def apply_max_single_weight(
    weights: dict[str, Decimal],
    logs: list[RiskCheckResult],
    run_id: int,
    check_date: date,
    threshold: Decimal,
) -> None:
    excess = Decimal("0")
    for symbol, weight in list(weights.items()):
        if weight > threshold:
            weights[symbol] = threshold
            excess += weight - threshold
            logs.append(
                RiskCheckResult(
                    run_id=run_id,
                    check_date=check_date,
                    rule_code="max_single_weight",
                    status="adjusted",
                    message=f"{symbol} capped at {threshold}",
                    before_value=weight,
                    after_value=threshold,
                )
            )
    add_excess_to_cash(weights, excess)


def apply_max_asset_class_weight(
    weights: dict[str, Decimal],
    targets: list[TargetPortfolio],
    logs: list[RiskCheckResult],
    run_id: int,
    check_date: date,
    *,
    asset_class: str,
    rule_code: str,
    threshold: Decimal,
) -> None:
    symbols = [item.symbol for item in targets if item.asset_class == asset_class]
    current = sum(weights.get(symbol, Decimal("0")) for symbol in symbols)
    if current <= threshold or current == 0:
        return
    scale = threshold / current
    excess = Decimal("0")
    for symbol in symbols:
        before = weights[symbol]
        weights[symbol] = before * scale
        excess += before - weights[symbol]
    add_excess_to_cash(weights, excess)
    logs.append(
        RiskCheckResult(
            run_id=run_id,
            check_date=check_date,
            rule_code=rule_code,
            status="adjusted",
            message=f"{asset_class} exposure reduced to {threshold}",
            before_value=current,
            after_value=threshold,
        )
    )


def apply_min_asset_class_weight(
    weights: dict[str, Decimal],
    targets: list[TargetPortfolio],
    logs: list[RiskCheckResult],
    run_id: int,
    check_date: date,
    *,
    asset_classes: set[str],
    rule_code: str,
    threshold: Decimal,
) -> None:
    symbols = [item.symbol for item in targets if item.asset_class in asset_classes]
    current = sum(weights.get(symbol, Decimal("0")) for symbol in symbols)
    if current >= threshold or not symbols:
        return
    deficit = threshold - current
    reduce_non_required(weights, targets, asset_classes, deficit)
    receiver = symbols[0]
    weights[receiver] = weights.get(receiver, Decimal("0")) + deficit
    logs.append(
        RiskCheckResult(
            run_id=run_id,
            check_date=check_date,
            rule_code=rule_code,
            status="adjusted",
            message=f"{','.join(sorted(asset_classes))} raised to {threshold}",
            before_value=current,
            after_value=threshold,
        )
    )


def reduce_non_required(
    weights: dict[str, Decimal],
    targets: list[TargetPortfolio],
    protected_classes: set[str],
    amount: Decimal,
) -> None:
    candidates = [item.symbol for item in targets if item.asset_class not in protected_classes and weights.get(item.symbol, 0) > 0]
    total = sum(weights.get(symbol, Decimal("0")) for symbol in candidates)
    if total <= 0:
        return
    for symbol in candidates:
        reduction = amount * (weights[symbol] / total)
        weights[symbol] = max(Decimal("0"), weights[symbol] - reduction)


def add_excess_to_cash(weights: dict[str, Decimal], excess: Decimal) -> None:
    if excess <= 0:
        return
    cash_symbol = next((symbol for symbol in weights if symbol in {"511880"}), None)
    if cash_symbol is None and weights:
        cash_symbol = next(iter(weights))
    if cash_symbol:
        weights[cash_symbol] = weights.get(cash_symbol, Decimal("0")) + excess


def normalize_weights(weights: dict[str, Decimal]) -> None:
    total = sum(weights.values(), Decimal("0"))
    if total == 0:
        return
    for symbol in list(weights):
        weights[symbol] = weights[symbol] / total


def list_risk_results(db: Session, run_id: int | None = None, limit: int = 100) -> list[RiskCheckResult]:
    query = select(RiskCheckResult).order_by(RiskCheckResult.created_at.desc()).limit(limit)
    if run_id is not None:
        query = query.where(RiskCheckResult.run_id == run_id)
    return list(db.scalars(query).all())


def generate_rebalance_orders(db: Session, *, run_id: int, portfolio_value: Decimal = Decimal("100000")) -> dict[str, Any]:
    targets = load_targets(db, run_id)
    if not targets:
        raise ValueError(f"No target portfolio found for run_id={run_id}")
    order_date = targets[0].portfolio_date
    existing_orders = db.scalars(select(RebalanceOrder).where(RebalanceOrder.run_id == run_id)).all()
    for order in existing_orders:
        db.delete(order)
    db.flush()

    orders: list[RebalanceOrder] = []
    current_weights = current_weight_map(db, position_date=order_date) or current_weight_map(db)
    for target in targets:
        current_weight = current_weights.get(target.symbol, Decimal("0"))
        target_weight = Decimal(target.final_target_weight or 0)
        diff = target_weight - current_weight
        action = rebalance_action(diff)
        if action == "HOLD" and abs(diff) < MIN_REBALANCE_DIFF:
            continue
        orders.append(
            RebalanceOrder(
                run_id=run_id,
                order_date=order_date,
                symbol=target.symbol,
                action=action,
                current_weight=current_weight.quantize(Decimal("0.000001")),
                target_weight=target_weight.quantize(Decimal("0.000001")),
                weight_diff=diff.quantize(Decimal("0.000001")),
                estimated_amount=(portfolio_value * diff).quantize(Decimal("0.0001")),
                reason=f"从当前权重 current_weight={current_weight} 调整到目标权重 target_weight={target_weight}",
                status="pending",
            )
        )
    db.add_all(orders)
    db.commit()
    return {"run_id": run_id, "order_date": order_date, "order_count": len(orders), "status": "success"}


def rebalance_action(diff: Decimal) -> str:
    if abs(diff) < MIN_REBALANCE_DIFF:
        return "HOLD"
    if diff > 0:
        return "BUY"
    return "SELL"


def list_rebalance_orders(db: Session, run_id: int | None = None, limit: int = 100) -> list[RebalanceOrder]:
    query = select(RebalanceOrder).order_by(RebalanceOrder.created_at.desc()).limit(limit)
    if run_id is not None:
        query = query.where(RebalanceOrder.run_id == run_id)
    return list(db.scalars(query).all())
