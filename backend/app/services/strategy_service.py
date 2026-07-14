from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.asset import AssetMaster
from app.models.factor import FactorDaily
from app.models.portfolio import TargetPortfolio
from app.models.strategy import AlphaSignal, StrategyConfig, StrategyRun
from app.services.etf_compare_service import score_etf_tradability

DEFAULT_STRATEGY_CODE = "core_etf_rotation"
TRADABILITY_EXCLUDE_THRESHOLD = 40
TRADABILITY_REDUCE_THRESHOLD = 60
TRADABILITY_REDUCED_MULTIPLIER = Decimal("0.50")
DEFAULT_TARGET_WEIGHTS = {
    "equity_primary": "0.40",
    "equity_secondary": "0.25",
    "defense": "0.25",
    "cash": "0.10",
}
BUILTIN_STRATEGIES: list[dict[str, Any]] = [
    {
        "strategy_code": "core_etf_rotation",
        "strategy_name": "核心 ETF 轮动策略",
        "version": "0.2.0",
        "rebalance_frequency": "monthly",
        "enabled": True,
        "config": {
            "engine": "factor_rotation",
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
            "engine": "factor_rotation",
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
            "engine": "factor_rotation",
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
            "engine": "factor_rotation",
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
    normalized.setdefault("engine", "factor_rotation")
    normalized.setdefault("target_weights", DEFAULT_TARGET_WEIGHTS)
    return normalized


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

    strategy_run = StrategyRun(
        strategy_code=strategy.strategy_code,
        strategy_version=strategy.version,
        run_date=resolved_run_date,
        run_type=run_type,
        status="success",
        message=f"Generated {len(ranking)} alpha signals",
    )
    db.add(strategy_run)
    db.flush()

    asset_map = load_asset_map(db)
    signals = build_alpha_signals(strategy_run.id, resolved_run_date, ranking)
    tradability_map = {
        item["symbol"]: item
        for item in score_etf_tradability(db, symbols=[item.symbol for item in ranking], end_date=resolved_run_date)
    }
    targets = build_target_portfolio(strategy_run.id, resolved_run_date, ranking, asset_map, tradability_map, strategy.config)
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


def build_alpha_signals(run_id: int, signal_date: date, ranking: list[FactorDaily]) -> list[AlphaSignal]:
    signals: list[AlphaSignal] = []
    for index, item in enumerate(ranking, start=1):
        signals.append(
            AlphaSignal(
                run_id=run_id,
                symbol=item.symbol,
                signal_date=signal_date,
                alpha_score=item.alpha_score,
                rank_no=index,
                confidence=score_confidence(item.alpha_score),
                signal_reason=f"rank={index}; alpha_score={item.alpha_score}",
            )
        )
    return signals


def build_target_portfolio(
    run_id: int,
    portfolio_date: date,
    ranking: list[FactorDaily],
    asset_map: dict[str, AssetMaster],
    tradability_map: dict[str, dict[str, Any]] | None = None,
    strategy_config: dict[str, Any] | None = None,
) -> list[TargetPortfolio]:
    tradability_map = tradability_map or {}
    weights, adjustments = construct_target_weights_with_tradability(
        [item.symbol for item in ranking],
        asset_map,
        tradability_map,
        strategy_config=strategy_config,
    )
    targets: list[TargetPortfolio] = []
    for symbol, weight in weights.items():
        asset = asset_map.get(symbol)
        targets.append(
            TargetPortfolio(
                run_id=run_id,
                portfolio_date=portfolio_date,
                symbol=symbol,
                raw_target_weight=weight,
                final_target_weight=weight,
                asset_class=asset.asset_class if asset else None,
                reason=target_reason(symbol, weight, ranking, asset_map, tradability_map, adjustments),
            )
        )
    return targets


def construct_target_weights(ranked_symbols: list[str], asset_map: dict[str, AssetMaster]) -> dict[str, Decimal]:
    weights, _ = construct_target_weights_with_tradability(ranked_symbols, asset_map, tradability_map={})
    return weights


def construct_target_weights_with_tradability(
    ranked_symbols: list[str],
    asset_map: dict[str, AssetMaster],
    tradability_map: dict[str, dict[str, Any]],
    strategy_config: dict[str, Any] | None = None,
) -> tuple[dict[str, Decimal], dict[str, str]]:
    strategy_config = strategy_config or {}
    target_weights = resolve_target_weights(strategy_config)
    equity_symbols, adjustments = tradable_equity_symbols(ranked_symbols, asset_map, tradability_map, strategy_config)
    defense_symbols = [
        symbol for symbol, asset in asset_map.items() if asset.asset_class in {"bond", "gold"} and asset.enabled
    ]
    cash_symbols = [symbol for symbol, asset in asset_map.items() if asset.asset_class == "cash" and asset.enabled]

    weights: dict[str, Decimal] = {}
    cash_weight = target_weights["cash"]

    if equity_symbols:
        weights[equity_symbols[0]] = target_weights["equity_primary"]
    else:
        cash_weight += target_weights["equity_primary"]

    if len(equity_symbols) >= 2:
        weights[equity_symbols[1]] = target_weights["equity_secondary"]
    else:
        cash_weight += target_weights["equity_secondary"]

    if defense_symbols:
        defense_symbol = sorted(defense_symbols, key=lambda symbol: (asset_map[symbol].risk_level, symbol))[0]
        weights[defense_symbol] = weights.get(defense_symbol, Decimal("0")) + target_weights["defense"]
    else:
        cash_weight += target_weights["defense"]

    if cash_symbols:
        cash_symbol = sorted(cash_symbols)[0]
        weights[cash_symbol] = weights.get(cash_symbol, Decimal("0")) + cash_weight

    weights = apply_tradability_adjustments(weights, adjustments, asset_map)
    total_weight = sum(weights.values(), Decimal("0"))
    if total_weight != Decimal("1.00") and weights:
        first_symbol = next(iter(weights))
        weights[first_symbol] += Decimal("1.00") - total_weight
    return {symbol: weight.quantize(Decimal("0.000001")) for symbol, weight in weights.items() if weight > 0}, adjustments


def tradable_equity_symbols(
    ranked_symbols: list[str],
    asset_map: dict[str, AssetMaster],
    tradability_map: dict[str, dict[str, Any]],
    strategy_config: dict[str, Any] | None = None,
) -> tuple[list[str], dict[str, str]]:
    selected: list[str] = []
    adjustments: dict[str, str] = {}
    preferred_regions = set((strategy_config or {}).get("preferred_regions") or [])
    for symbol in ranked_symbols:
        asset = asset_map.get(symbol)
        if not asset or asset.asset_class != "equity":
            continue
        if preferred_regions and asset.asset_region not in preferred_regions:
            adjustments[symbol] = "excluded_by_preferred_regions"
            continue
        score = tradability_score(symbol, tradability_map)
        if score is not None and score < TRADABILITY_EXCLUDE_THRESHOLD:
            adjustments[symbol] = f"excluded_by_tradability_score<{TRADABILITY_EXCLUDE_THRESHOLD}"
            continue
        selected.append(symbol)
        if score is not None and score < TRADABILITY_REDUCE_THRESHOLD:
            adjustments[symbol] = f"reduced_by_tradability_score<{TRADABILITY_REDUCE_THRESHOLD}"
    return selected, adjustments


def resolve_target_weights(strategy_config: dict[str, Any]) -> dict[str, Decimal]:
    raw_weights = strategy_config.get("target_weights") or DEFAULT_TARGET_WEIGHTS
    weights = {
        key: Decimal(str(raw_weights.get(key, DEFAULT_TARGET_WEIGHTS[key])))
        for key in ("equity_primary", "equity_secondary", "defense", "cash")
    }
    total = sum(weights.values(), Decimal("0"))
    if total <= 0:
        return {key: Decimal(value) for key, value in DEFAULT_TARGET_WEIGHTS.items()}
    if total != Decimal("1.00"):
        weights = {key: (value / total).quantize(Decimal("0.000001")) for key, value in weights.items()}
    return weights


def apply_tradability_adjustments(
    weights: dict[str, Decimal],
    adjustments: dict[str, str],
    asset_map: dict[str, AssetMaster],
) -> dict[str, Decimal]:
    cash_symbols = [symbol for symbol, asset in asset_map.items() if asset.asset_class == "cash" and asset.enabled]
    if not cash_symbols:
        return weights
    cash_symbol = sorted(cash_symbols)[0]
    released = Decimal("0")
    for symbol, reason in adjustments.items():
        if symbol not in weights or not reason.startswith("reduced_by"):
            continue
        reduced_weight = (weights[symbol] * TRADABILITY_REDUCED_MULTIPLIER).quantize(Decimal("0.000001"))
        released += weights[symbol] - reduced_weight
        weights[symbol] = reduced_weight
    if released > 0:
        weights[cash_symbol] = weights.get(cash_symbol, Decimal("0")) + released
    return weights


def target_reason(
    symbol: str,
    weight: Decimal,
    ranking: list[FactorDaily],
    asset_map: dict[str, AssetMaster],
    tradability_map: dict[str, dict[str, Any]] | None = None,
    adjustments: dict[str, str] | None = None,
) -> str:
    rank_lookup = {item.symbol: index for index, item in enumerate(ranking, start=1)}
    asset = asset_map.get(symbol)
    tradability_note = build_tradability_note(symbol, tradability_map or {})
    adjustment_note = build_tradability_adjustment_note(symbol, adjustments or {})
    if asset and asset.asset_class == "equity":
        return f"Equity ETF selected by alpha ranking; rank={rank_lookup.get(symbol)}; target_weight={weight}; {tradability_note}; {adjustment_note}"
    if asset and asset.asset_class in {"bond", "gold"}:
        return f"Defense asset allocation; target_weight={weight}; {tradability_note}; {adjustment_note}"
    if asset and asset.asset_class == "cash":
        return f"Cash buffer and unused risk budget; target_weight={weight}; {tradability_note}; {adjustment_note}"
    return f"Target allocation; target_weight={weight}; {tradability_note}; {adjustment_note}"


def build_tradability_note(symbol: str, tradability_map: dict[str, dict[str, Any]]) -> str:
    metric = tradability_map.get(symbol)
    if not metric:
        return "tradability_score=unknown"
    notes = " / ".join(metric.get("tradability_notes") or [])
    return f"tradability_score={metric['tradability_score']}({metric['tradability_level']}); {notes}"


def build_tradability_adjustment_note(symbol: str, adjustments: dict[str, str]) -> str:
    reason = adjustments.get(symbol)
    if not reason:
        return "tradability_adjustment=none"
    return f"tradability_adjustment={reason}"


def tradability_score(symbol: str, tradability_map: dict[str, dict[str, Any]]) -> int | None:
    metric = tradability_map.get(symbol)
    if metric is None:
        return None
    value = metric.get("tradability_score")
    return int(value) if value is not None else None


def score_confidence(alpha_score: Decimal | None) -> Decimal:
    if alpha_score is None:
        return Decimal("0.5000")
    confidence = max(Decimal("0.3000"), min(Decimal("0.9500"), Decimal(alpha_score) / Decimal("100")))
    return confidence.quantize(Decimal("0.0001"))


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
