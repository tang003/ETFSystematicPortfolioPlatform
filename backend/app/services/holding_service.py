from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.database import Base, engine
from app.models.asset import AssetMaster
from app.models.factor import FactorDaily
from app.models.market_data import MarketDataClean
from app.models.portfolio import HoldingAnalysisResult, PortfolioPosition, TargetPortfolio
from app.schemas.portfolio_schema import PortfolioSnapshotRequest, PositionResolveRead
from app.services.strategy_service import latest_target_portfolio

MIN_ACTION_DIFF = Decimal("0.03")


def ensure_holding_tables() -> None:
    Base.metadata.create_all(bind=engine, tables=[HoldingAnalysisResult.__table__])


def upsert_position_snapshot(db: Session, request: PortfolioSnapshotRequest) -> list[PortfolioPosition]:
    db.execute(delete(PortfolioPosition).where(PortfolioPosition.position_date == request.position_date))
    prepared_details = prepare_position_assets(db, request)
    normalized = [
        normalize_position_input(item, prepared_details.get(normalize_symbol(item.symbol)) or resolve_position_detail(db, item.symbol))
        for item in request.positions
        if item.symbol.strip()
    ]
    total_value = sum((item["market_value"] for item in normalized), Decimal("0"))
    if total_value <= 0:
        raise ValueError("持仓总市值必须大于 0")

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


def prepare_position_assets(
    db: Session,
    request: PortfolioSnapshotRequest,
    *,
    source: str = "tushare",
) -> dict[str, PositionResolveRead]:
    details: dict[str, PositionResolveRead] = {}
    for item in request.positions:
        symbol = normalize_symbol(item.symbol)
        if not symbol:
            continue
        detail = ensure_position_asset_and_market(db, symbol, source=source)
        details[symbol] = detail
    return details


def normalize_position_input(item, detail: PositionResolveRead | None = None) -> dict:
    quantity = item.quantity or Decimal("0")
    current_price = item.current_price if item.current_price is not None else (detail.current_price if detail else None)
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
        raise ValueError(f"{item.symbol} 缺少最新价格，无法计算市值。请先刷新该代码行情，或临时补充现价。")

    unrealized_pnl = None
    unrealized_pnl_rate = None
    if cost_basis is not None and cost_basis > 0:
        unrealized_pnl = (market_value - cost_basis).quantize(Decimal("0.0001"))
        unrealized_pnl_rate = (unrealized_pnl / cost_basis).quantize(Decimal("0.000001"))

    return {
        "symbol": normalize_symbol(item.symbol),
        "position_name": item.position_name.strip() if item.position_name else (detail.position_name if detail else None),
        "asset_type": (item.asset_type or (detail.asset_type if detail else None) or "etf").strip().lower(),
        "quantity": quantity,
        "current_price": current_price,
        "cost_price": cost_price,
        "market_value": market_value,
        "cost_basis": cost_basis,
        "unrealized_pnl": unrealized_pnl,
        "unrealized_pnl_rate": unrealized_pnl_rate,
    }


def resolve_position_details(
    db: Session,
    symbols: list[str],
    *,
    auto_sync: bool = False,
    source: str = "tushare",
) -> list[PositionResolveRead]:
    seen: set[str] = set()
    resolved = []
    for symbol in symbols:
        cleaned = normalize_symbol(symbol)
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        if auto_sync:
            ensure_position_market_data(db, cleaned, source=source)
        resolved.append(resolve_position_detail(db, cleaned))
    return resolved


def resolve_position_detail(db: Session, symbol: str) -> PositionResolveRead:
    cleaned = normalize_symbol(symbol)
    asset = db.scalar(select(AssetMaster).where(AssetMaster.symbol == cleaned))
    latest_bar = db.scalar(
        select(MarketDataClean)
        .where(MarketDataClean.symbol == cleaned)
        .where(MarketDataClean.close.is_not(None))
        .order_by(MarketDataClean.trade_date.desc())
        .limit(1)
    )

    name = asset.name if asset else None
    asset_type = infer_asset_type(asset.asset_class if asset else None)
    current_price = latest_bar.close if latest_bar else None
    price_date = latest_bar.trade_date if latest_bar else None
    messages = []
    if asset is None:
        messages.append("资产主表未找到该代码")
    if latest_bar is None:
        messages.append("未找到已清洗行情价格")

    return PositionResolveRead(
        symbol=cleaned,
        position_name=name,
        asset_type=asset_type,
        current_price=current_price,
        price_date=price_date,
        resolved=asset is not None and current_price is not None,
        message="；".join(messages) if messages else None,
    )


def ensure_position_market_data(db: Session, symbol: str, *, source: str = "tushare") -> None:
    ensure_position_asset(db, symbol, enabled=True)
    if latest_clean_bar(db, symbol) is not None:
        return

    from app.services.market_service import sync_market_data

    end_date = date.today()
    start_date = end_date - timedelta(days=45)
    sync_market_data(
        db,
        symbols=[symbol],
        sync_scope="custom",
        start_date=start_date,
        end_date=end_date,
        source=source,
        incremental=True,
        clean_after_sync=True,
        max_symbols=1,
        request_interval_seconds=0,
    )


def ensure_position_asset_and_market(db: Session, symbol: str, *, source: str = "tushare") -> PositionResolveRead:
    ensure_position_asset(db, symbol, enabled=True)
    ensure_position_market_data(db, symbol, source=source)
    return resolve_position_detail(db, symbol)


def ensure_position_asset(db: Session, symbol: str, *, enabled: bool = True) -> AssetMaster:
    asset = db.scalar(select(AssetMaster).where(AssetMaster.symbol == symbol))
    if asset is not None:
        changed = False
        if enabled and not asset.enabled:
            asset.enabled = True
            changed = True
        if changed:
            db.commit()
            db.refresh(asset)
        return asset

    asset = AssetMaster(
        symbol=symbol,
        name=infer_placeholder_name(symbol),
        exchange=infer_exchange(symbol),
        asset_class="equity",
        asset_region="CN",
        currency="CNY",
        is_cross_border=symbol.startswith("513"),
        is_leveraged=False,
        is_inverse=False,
        enabled=True,
        risk_level=4 if symbol.startswith("513") else 3,
        description="由当前持仓自动登记，后续可在 ETF 池补全基金公司、跟踪指数、费率等主数据。",
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def update_asset_from_quote(db: Session, symbol: str, name: str | None) -> None:
    if not name:
        return
    asset = db.scalar(select(AssetMaster).where(AssetMaster.symbol == symbol))
    if asset is None:
        return
    if asset.name == infer_placeholder_name(symbol):
        asset.name = name
        db.commit()


def latest_clean_bar(db: Session, symbol: str) -> MarketDataClean | None:
    return db.scalar(
        select(MarketDataClean)
        .where(MarketDataClean.symbol == symbol)
        .where(MarketDataClean.close.is_not(None))
        .order_by(MarketDataClean.trade_date.desc())
        .limit(1)
    )


def normalize_symbol(symbol: str) -> str:
    cleaned = symbol.strip().upper()
    if "." in cleaned:
        return cleaned.split(".", 1)[0]
    return cleaned


def infer_exchange(symbol: str) -> str:
    if symbol.startswith(("5", "6", "9")):
        return "SH"
    return "SZ"


def infer_placeholder_name(symbol: str) -> str:
    return f"{symbol} ETF"


def infer_asset_type(asset_class: str | None) -> str:
    normalized = (asset_class or "").lower()
    if normalized == "cash":
        return "cash"
    if normalized in {"stock", "equity", "bond", "commodity", "money_market", "qdii", "index", "cross_border"}:
        return "etf"
    return "etf"


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
        raise ValueError("没有可用的目标组合。请先在“目标组合”页面运行策略，或在“全流程”页面生成目标组合后再运行持仓分析。")
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


def enrich_holding_analysis_with_alternatives(db: Session, rows: list[HoldingAnalysisResult], *, max_alternatives: int = 3) -> list[dict]:
    from app.services.etf_detail_service import get_etf_detail

    end_date = date.today()
    start_date = end_date - timedelta(days=365)
    enriched: list[dict] = []
    for row in rows:
        alternatives = []
        try:
            detail = get_etf_detail(db, symbol=row.symbol, start_date=start_date, end_date=end_date)
            alternatives = detail.get("alternatives", [])[:max_alternatives]
        except Exception:
            alternatives = []
        enriched.append(
            {
                "run_id": row.run_id,
                "analysis_date": row.analysis_date,
                "symbol": row.symbol,
                "current_weight": row.current_weight,
                "target_weight": row.target_weight,
                "weight_diff": row.weight_diff,
                "action_suggestion": row.action_suggestion,
                "alpha_score": row.alpha_score,
                "reason": row.reason,
                "alternatives": alternatives,
                "created_at": row.created_at,
            }
        )
    return enriched


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
