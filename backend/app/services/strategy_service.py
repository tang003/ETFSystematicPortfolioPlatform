from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.asset import AssetMaster
from app.models.factor import FactorDaily
from app.models.portfolio import TargetPortfolio
from app.models.strategy import AlphaSignal, StrategyConfig, StrategyRun
from app.services.etf_compare_service import score_etf_tradability
from app.strategies.base import StrategyRunContext
from app.strategies.factor_rotation import (
    DEFAULT_TARGET_WEIGHTS,
    build_target_portfolio,
    construct_target_weights,
    construct_target_weights_with_tradability,
    score_confidence,
)
from app.strategies.registry import get_strategy_engine

DEFAULT_STRATEGY_CODE = "core_etf_rotation"
DEFAULT_ENGINE_CODE = "factor_rotation"
BUILTIN_STRATEGIES: list[dict[str, Any]] = [
    {
        "strategy_code": "core_etf_rotation",
        "strategy_name": "核心 ETF 轮动策略",
        "version": "0.2.0",
        "rebalance_frequency": "monthly",
        "enabled": True,
        "config": {
            "engine": DEFAULT_ENGINE_CODE,
            "risk_profile": "balanced",
            "target_weights": DEFAULT_TARGET_WEIGHTS,
            "description": "以 Alpha 因子排名选择两只权益 ETF，搭配防守资产和现金缓冲。",
        },
    },
    {
        "strategy_code": "aggressive_equity_rotation",
        "strategy_name": "进取权益轮动策略",
        "version": "0.1.0",
        "rebalance_frequency": "monthly",
        "enabled": True,
        "config": {
            "engine": DEFAULT_ENGINE_CODE,
            "risk_profile": "aggressive",
            "target_weights": {
                "equity_primary": "0.50",
                "equity_secondary": "0.30",
                "defense": "0.10",
                "cash": "0.10",
            },
            "description": "提高权益 ETF 权重，适合风险承受能力较高、希望捕捉趋势的组合。",
        },
    },
    {
        "strategy_code": "defensive_all_weather",
        "strategy_name": "防守全天候配置策略",
        "version": "0.1.0",
        "rebalance_frequency": "monthly",
        "enabled": True,
        "config": {
            "engine": DEFAULT_ENGINE_CODE,
            "risk_profile": "defensive",
            "target_weights": {
                "equity_primary": "0.25",
                "equity_secondary": "0.15",
                "defense": "0.45",
                "cash": "0.15",
            },
            "description": "降低权益暴露，提高债券、黄金和现金缓冲，优先控制回撤。",
        },
    },
    {
        "strategy_code": "global_qdii_rotation",
        "strategy_name": "QDII 全球 ETF 轮动策略",
        "version": "0.1.0",
        "rebalance_frequency": "monthly",
        "enabled": True,
        "config": {
            "engine": DEFAULT_ENGINE_CODE,
            "risk_profile": "global",
            "preferred_regions": ["US", "GLOBAL", "JP", "DE", "CN_HK_US"],
            "target_weights": {
                "equity_primary": "0.35",
                "equity_secondary": "0.25",
                "defense": "0.25",
                "cash": "0.15",
            },
            "description": "优先在跨境和全球 ETF 中筛选，适合海外资产配置观察。",
        },
    },
]


def list_strategy_configs(db: Session) -> list[StrategyConfig]:
    ensure_builtin_strategy_configs(db)
    return list(db.scalars(select(StrategyConfig).order_by(StrategyConfig.strategy_code)).all())


def ensure_builtin_strategy_configs(db: Session) -> None:
    changed = False
    for item in BUILTIN_STRATEGIES:
        exists = db.scalar(select(StrategyConfig).where(StrategyConfig.strategy_code == item["strategy_code"]))
        if exists is not None:
            continue
        db.add(StrategyConfig(**item))
        changed = True
    if changed:
        db.commit()


def create_strategy_config(db: Session, payload: dict[str, Any]) -> StrategyConfig:
    strategy_code = normalize_strategy_code(payload["strategy_code"])
    exists = db.scalar(select(StrategyConfig).where(StrategyConfig.strategy_code == strategy_code))
    if exists is not None:
        raise ValueError(f"Strategy already exists: {strategy_code}")
    strategy = StrategyConfig(
        strategy_code=strategy_code,
        strategy_name=payload["strategy_name"],
        version=payload.get("version") or "0.1.0",
        rebalance_frequency=payload.get("rebalance_frequency") or "monthly",
        config=normalize_strategy_config(payload.get("config") or {}),
        enabled=bool(payload.get("enabled", True)),
    )
    db.add(strategy)
    db.commit()
    db.refresh(strategy)
    return strategy


def update_strategy_config(db: Session, strategy_code: str, payload: dict[str, Any]) -> StrategyConfig:
    strategy = db.scalar(select(StrategyConfig).where(StrategyConfig.strategy_code == strategy_code))
    if strategy is None:
        raise ValueError(f"Strategy not found: {strategy_code}")
    for field in ("strategy_name", "version", "rebalance_frequency", "enabled"):
        if field in payload and payload[field] is not None:
            setattr(strategy, field, payload[field])
    if "config" in payload and payload["config"] is not None:
        strategy.config = normalize_strategy_config(payload["config"])
    db.commit()
    db.refresh(strategy)
    return strategy


def normalize_strategy_code(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    if not normalized.replace("_", "").isalnum():
        raise ValueError("strategy_code can only contain letters, numbers and underscores")
    return normalized


def normalize_strategy_config(config: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(config)
    normalized.setdefault("engine", DEFAULT_ENGINE_CODE)
    engine = get_strategy_engine(normalized["engine"])
    return engine.normalize_config(normalized)


def run_strategy(
    db: Session,
    *,
    strategy_code: str = DEFAULT_STRATEGY_CODE,
    run_date: date | None = None,
    run_type: str = "manual",
) -> dict[str, Any]:
    strategy = get_enabled_strategy(db, strategy_code)
    resolved_run_date = run_date or latest_factor_date(db)
    if resolved_run_date is None:
        raise ValueError("No factor data available for strategy run")

    ranking = load_factor_ranking(db, resolved_run_date)
    if not ranking:
        raise ValueError(f"No factor ranking found for {resolved_run_date}")

    engine_code = (strategy.config or {}).get("engine") or DEFAULT_ENGINE_CODE
    engine = get_strategy_engine(engine_code)
    strategy_config = engine.normalize_config(strategy.config or {})

    strategy_run = StrategyRun(
        strategy_code=strategy.strategy_code,
        strategy_version=strategy.version,
        run_date=resolved_run_date,
        run_type=run_type,
        status="success",
        message=f"Generated {len(ranking)} alpha signals with engine={engine.engine_code}",
    )
    db.add(strategy_run)
    db.flush()

    asset_map = load_asset_map(db)
    tradability_map = {
        item["symbol"]: item
        for item in score_etf_tradability(db, symbols=[item.symbol for item in ranking], end_date=resolved_run_date)
    }
    context = StrategyRunContext(
        run_id=strategy_run.id,
        run_date=resolved_run_date,
        ranking=ranking,
        asset_map=asset_map,
        tradability_map=tradability_map,
        config=strategy_config,
    )
    signals = engine.build_signals(context)
    targets = engine.build_targets(context)
    db.add_all(signals)
    db.add_all(targets)
    db.commit()

    return {
        "run_id": strategy_run.id,
        "strategy_code": strategy.strategy_code,
        "strategy_version": strategy.version,
        "run_date": resolved_run_date,
        "signal_count": len(signals),
        "target_count": len(targets),
        "status": "success",
    }


def get_enabled_strategy(db: Session, strategy_code: str) -> StrategyConfig:
    ensure_builtin_strategy_configs(db)
    strategy = db.scalar(
        select(StrategyConfig)
        .where(StrategyConfig.strategy_code == strategy_code)
        .where(StrategyConfig.enabled.is_(True))
    )
    if strategy is None:
        raise ValueError(f"Strategy not found or disabled: {strategy_code}")
    return strategy


def latest_factor_date(db: Session) -> date | None:
    return db.scalar(select(FactorDaily.trade_date).order_by(FactorDaily.trade_date.desc()).limit(1))


def load_factor_ranking(db: Session, run_date: date) -> list[FactorDaily]:
    return list(
        db.scalars(
            select(FactorDaily)
            .where(FactorDaily.trade_date == run_date)
            .order_by(FactorDaily.alpha_score.desc().nullslast())
        ).all()
    )


def load_asset_map(db: Session) -> dict[str, AssetMaster]:
    assets = db.scalars(select(AssetMaster).where(AssetMaster.enabled.is_(True))).all()
    return {asset.symbol: asset for asset in assets}


def latest_signals(db: Session, limit: int = 100) -> list[AlphaSignal]:
    latest_run_id = db.scalar(select(StrategyRun.id).order_by(StrategyRun.created_at.desc()).limit(1))
    if latest_run_id is None:
        return []
    return list(
        db.scalars(
            select(AlphaSignal)
            .where(AlphaSignal.run_id == latest_run_id)
            .order_by(AlphaSignal.rank_no)
            .limit(limit)
        ).all()
    )


def latest_target_portfolio(db: Session) -> list[TargetPortfolio]:
    latest_run_id = db.scalar(select(TargetPortfolio.run_id).order_by(TargetPortfolio.created_at.desc()).limit(1))
    if latest_run_id is None:
        return []
    return list(
        db.scalars(
            select(TargetPortfolio)
            .where(TargetPortfolio.run_id == latest_run_id)
            .order_by(TargetPortfolio.final_target_weight.desc().nullslast())
        ).all()
    )
