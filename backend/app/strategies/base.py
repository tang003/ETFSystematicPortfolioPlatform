from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol

from app.models.asset import AssetMaster
from app.models.factor import FactorDaily
from app.models.portfolio import TargetPortfolio
from app.models.strategy import AlphaSignal


@dataclass(frozen=True)
class StrategyRunContext:
    run_id: int
    run_date: date
    ranking: list[FactorDaily]
    asset_map: dict[str, AssetMaster]
    tradability_map: dict[str, dict[str, Any]]
    config: dict[str, Any]


class StrategyEngine(Protocol):
    engine_code: str

    def normalize_config(self, config: dict[str, Any]) -> dict[str, Any]:
        """Normalize and validate user-facing strategy configuration."""

    def build_signals(self, context: StrategyRunContext) -> list[AlphaSignal]:
        """Build strategy signals for persistence."""

    def build_targets(self, context: StrategyRunContext) -> list[TargetPortfolio]:
        """Build target portfolio rows for persistence."""

