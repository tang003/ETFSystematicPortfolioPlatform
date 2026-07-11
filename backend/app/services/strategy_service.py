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


def list_strategy_configs(db: Session) -> list[StrategyConfig]:
    return list(db.scalars(select(StrategyConfig).order_by(StrategyConfig.strategy_code)).all())


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
    targets = build_target_portfolio(strategy_run.id, resolved_run_date, ranking, asset_map, tradability_map)
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
) -> list[TargetPortfolio]:
    tradability_map = tradability_map or {}
    weights = construct_target_weights([item.symbol for item in ranking], asset_map)
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
                reason=target_reason(symbol, weight, ranking, asset_map, tradability_map),
            )
        )
    return targets


def construct_target_weights(ranked_symbols: list[str], asset_map: dict[str, AssetMaster]) -> dict[str, Decimal]:
    equity_symbols = [symbol for symbol in ranked_symbols if asset_map.get(symbol) and asset_map[symbol].asset_class == "equity"]
    defense_symbols = [
        symbol for symbol, asset in asset_map.items() if asset.asset_class in {"bond", "gold"} and asset.enabled
    ]
    cash_symbols = [symbol for symbol, asset in asset_map.items() if asset.asset_class == "cash" and asset.enabled]

    weights: dict[str, Decimal] = {}
    cash_weight = Decimal("0.10")

    if equity_symbols:
        weights[equity_symbols[0]] = Decimal("0.40")
    else:
        cash_weight += Decimal("0.40")

    if len(equity_symbols) >= 2:
        weights[equity_symbols[1]] = Decimal("0.25")
    else:
        cash_weight += Decimal("0.25")

    if defense_symbols:
        defense_symbol = sorted(defense_symbols, key=lambda symbol: (asset_map[symbol].risk_level, symbol))[0]
        weights[defense_symbol] = weights.get(defense_symbol, Decimal("0")) + Decimal("0.25")
    else:
        cash_weight += Decimal("0.25")

    if cash_symbols:
        cash_symbol = sorted(cash_symbols)[0]
        weights[cash_symbol] = weights.get(cash_symbol, Decimal("0")) + cash_weight

    total_weight = sum(weights.values(), Decimal("0"))
    if total_weight != Decimal("1.00") and weights:
        first_symbol = next(iter(weights))
        weights[first_symbol] += Decimal("1.00") - total_weight
    return {symbol: weight.quantize(Decimal("0.000001")) for symbol, weight in weights.items() if weight > 0}


def target_reason(
    symbol: str,
    weight: Decimal,
    ranking: list[FactorDaily],
    asset_map: dict[str, AssetMaster],
    tradability_map: dict[str, dict[str, Any]] | None = None,
) -> str:
    rank_lookup = {item.symbol: index for index, item in enumerate(ranking, start=1)}
    asset = asset_map.get(symbol)
    tradability_note = build_tradability_note(symbol, tradability_map or {})
    if asset and asset.asset_class == "equity":
        return f"Equity ETF selected by alpha ranking; rank={rank_lookup.get(symbol)}; target_weight={weight}; {tradability_note}"
    if asset and asset.asset_class in {"bond", "gold"}:
        return f"Defense asset allocation; target_weight={weight}; {tradability_note}"
    if asset and asset.asset_class == "cash":
        return f"Cash buffer and unused risk budget; target_weight={weight}; {tradability_note}"
    return f"Target allocation; target_weight={weight}; {tradability_note}"


def build_tradability_note(symbol: str, tradability_map: dict[str, dict[str, Any]]) -> str:
    metric = tradability_map.get(symbol)
    if not metric:
        return "tradability_score=unknown"
    notes = " / ".join(metric.get("tradability_notes") or [])
    return f"tradability_score={metric['tradability_score']}({metric['tradability_level']}); {notes}"


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
