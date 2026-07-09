from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class TargetPortfolioRead(BaseModel):
    run_id: int | None
    portfolio_date: date
    symbol: str
    raw_target_weight: Decimal | None
    final_target_weight: Decimal | None
    asset_class: str | None
    reason: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PortfolioPositionUpsert(BaseModel):
    symbol: str
    quantity: Decimal | None = None
    market_value: Decimal
    cost_basis: Decimal | None = None


class PortfolioSnapshotRequest(BaseModel):
    position_date: date
    positions: list[PortfolioPositionUpsert]


class PortfolioPositionRead(BaseModel):
    position_date: date
    symbol: str
    quantity: Decimal | None
    market_value: Decimal | None
    weight: Decimal | None
    cost_basis: Decimal | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HoldingAnalysisRequest(BaseModel):
    run_id: int | None = None
    analysis_date: date | None = None


class HoldingAnalysisRead(BaseModel):
    run_id: int | None
    analysis_date: date
    symbol: str
    current_weight: Decimal | None
    target_weight: Decimal | None
    weight_diff: Decimal | None
    action_suggestion: str
    alpha_score: Decimal | None
    reason: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
