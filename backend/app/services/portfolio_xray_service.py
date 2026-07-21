from collections import defaultdict
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.asset import AssetMaster
from app.models.factor import FactorDaily
from app.models.market_data import MarketDataClean
from app.models.portfolio import PortfolioPosition, TargetPortfolio
from app.schemas.portfolio_schema import PortfolioExposureRead, PortfolioReadinessRead, PortfolioXrayRead
from app.services.holding_service import latest_position_date
from app.services.strategy_service import latest_target_portfolio


def build_portfolio_xray(
    db: Session,
    *,
    owner_username: str | None = None,
    include_legacy: bool = False,
) -> PortfolioXrayRead:
    assets = {asset.symbol: asset for asset in db.scalars(select(AssetMaster)).all()}
    positions = latest_positions(db, owner_username=owner_username, include_legacy=include_legacy)
    targets = latest_target_portfolio(db)
    current_weights = {item.symbol: Decimal(item.weight or 0) for item in positions}
    target_weights = {
        item.symbol: Decimal(item.final_target_weight or item.raw_target_weight or 0)
        for item in targets
        if Decimal(item.final_target_weight or item.raw_target_weight or 0) > 0
    }
    exposures = build_exposures(assets, current_weights, target_weights)
    readiness = build_readiness(db, assets, positions, targets, target_weights)
    return PortfolioXrayRead(exposures=exposures, readiness=readiness)


def latest_positions(
    db: Session,
    *,
    owner_username: str | None = None,
    include_legacy: bool = False,
) -> list[PortfolioPosition]:
    from app.services.holding_service import user_owned_clause

    position_date = latest_position_date(db, owner_username=owner_username, include_legacy=include_legacy)
    if position_date is None:
        return []
    return list(
        db.scalars(
            select(PortfolioPosition).where(
                PortfolioPosition.position_date == position_date,
                user_owned_clause(PortfolioPosition, owner_username, include_legacy=include_legacy),
            )
        ).all()
    )


def build_exposures(
    assets: dict[str, AssetMaster],
    current_weights: dict[str, Decimal],
    target_weights: dict[str, Decimal],
) -> list[PortfolioExposureRead]:
    rows: list[PortfolioExposureRead] = []
    for dimension, resolver in {
        "asset_class": lambda asset: asset.asset_class if asset else "unknown",
        "asset_region": lambda asset: asset.asset_region if asset and asset.asset_region else "unknown",
        "risk_level": lambda asset: f"R{asset.risk_level}" if asset else "unknown",
    }.items():
        current_bucket: dict[str, Decimal] = defaultdict(Decimal)
        target_bucket: dict[str, Decimal] = defaultdict(Decimal)
        for symbol, weight in current_weights.items():
            current_bucket[resolver(assets.get(symbol))] += weight
        for symbol, weight in target_weights.items():
            target_bucket[resolver(assets.get(symbol))] += weight
        for name in sorted(set(current_bucket) | set(target_bucket)):
            current = current_bucket.get(name, Decimal("0"))
            target = target_bucket.get(name, Decimal("0"))
            rows.append(
                PortfolioExposureRead(
                    dimension=dimension,
                    name=name,
                    current_weight=current.quantize(Decimal("0.000001")),
                    target_weight=target.quantize(Decimal("0.000001")),
                    diff_weight=(target - current).quantize(Decimal("0.000001")),
                )
            )
    return rows


def build_readiness(
    db: Session,
    assets: dict[str, AssetMaster],
    positions: list[PortfolioPosition],
    targets: list[TargetPortfolio],
    target_weights: dict[str, Decimal],
) -> PortfolioReadinessRead:
    enabled_symbols = [symbol for symbol, asset in assets.items() if asset.enabled]
    latest_market_date = db.scalar(select(func.max(MarketDataClean.trade_date)))
    latest_factor_date = db.scalar(select(func.max(FactorDaily.trade_date)))
    market_symbols = set(db.scalars(select(MarketDataClean.symbol).distinct()).all())
    missing_market_count = len([symbol for symbol in enabled_symbols if symbol not in market_symbols])
    high_risk_target_weight = sum(
        (weight for symbol, weight in target_weights.items() if (assets.get(symbol).risk_level if assets.get(symbol) else 0) >= 5),
        Decimal("0"),
    )
    cross_border_target_weight = sum(
        (weight for symbol, weight in target_weights.items() if assets.get(symbol) and assets[symbol].is_cross_border),
        Decimal("0"),
    )
    max_single_target_weight = max(target_weights.values(), default=Decimal("0"))
    messages = []
    if not enabled_symbols:
        messages.append("ETF 池没有启用研究对象")
    if not targets:
        messages.append("尚未生成目标组合")
    if not positions:
        messages.append("尚未保存当前持仓")
    if missing_market_count:
        messages.append(f"{missing_market_count} 只启用 ETF 缺少行情")
    if high_risk_target_weight > Decimal("0.5"):
        messages.append("目标组合中高风险 ETF 权重超过 50%")
    if cross_border_target_weight > Decimal("0.5"):
        messages.append("目标组合中跨境 ETF 权重超过 50%，需关注汇率和海外市场风险")

    status = "ready" if not messages else ("warning" if targets or positions else "missing_data")
    return PortfolioReadinessRead(
        enabled_etf_count=len(enabled_symbols),
        position_count=len(positions),
        target_count=len(targets),
        latest_market_date=latest_market_date,
        latest_factor_date=latest_factor_date,
        missing_market_count=missing_market_count,
        high_risk_target_weight=high_risk_target_weight.quantize(Decimal("0.000001")),
        cross_border_target_weight=cross_border_target_weight.quantize(Decimal("0.000001")),
        max_single_target_weight=max_single_target_weight.quantize(Decimal("0.000001")),
        status=status,
        messages=messages or ["策略前检查通过，可以继续运行或生成建议"],
    )
