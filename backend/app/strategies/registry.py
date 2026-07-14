from __future__ import annotations

from app.strategies.base import StrategyEngine
from app.strategies.factor_rotation import ENGINE_CODE, FactorRotationEngine

_ENGINES: dict[str, StrategyEngine] = {
    ENGINE_CODE: FactorRotationEngine(),
}


def get_strategy_engine(engine_code: str | None) -> StrategyEngine:
    code = (engine_code or ENGINE_CODE).strip().lower()
    engine = _ENGINES.get(code)
    if engine is None:
        raise ValueError(f"Unsupported strategy engine: {code}")
    return engine


def list_strategy_engines() -> list[str]:
    return sorted(_ENGINES)

