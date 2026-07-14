from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.models.asset import AssetMaster
from app.models.factor import FactorDaily
from app.models.portfolio import TargetPortfolio
from app.models.strategy import AlphaSignal
from app.strategies.base import StrategyRunContext

ENGINE_CODE = "factor_rotation"
TRADABILITY_EXCLUDE_THRESHOLD = 40
TRADABILITY_REDUCE_THRESHOLD = 60
TRADABILITY_REDUCED_MULTIPLIER = Decimal("0.50")
DEFAULT_TARGET_WEIGHTS = {
    "equity_primary": "0.40",
    "equity_secondary": "0.25",
    "defense": "0.25",
    "cash": "0.10",
}


class FactorRotationEngine:
    engine_code = ENGINE_CODE

    def normalize_config(self, config: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(config)
        normalized.setdefault("engine", self.engine_code)
        normalized.setdefault("target_weights", DEFAULT_TARGET_WEIGHTS)
        resolve_target_weights(normalized)
        return normalized

    def build_signals(self, context: StrategyRunContext) -> list[AlphaSignal]:
        return build_alpha_signals(context.run_id, context.run_date, context.ranking)

    def build_targets(self, context: StrategyRunContext) -> list[TargetPortfolio]:
        return build_target_portfolio(
            context.run_id,
            context.run_date,
            context.ranking,
            context.asset_map,
            context.tradability_map,
            context.config,
        )


def build_alpha_signals(run_id: int, signal_date, ranking: list[FactorDaily]) -> list[AlphaSignal]:
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
    portfolio_date,
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

