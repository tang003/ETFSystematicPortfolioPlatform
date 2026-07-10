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
    position_name: str | None = None
    asset_type: str | None = None
    quantity: Decimal | None = None
    current_price: Decimal | None = None
    cost_price: Decimal | None = None
    market_value: Decimal | None = None
    cost_basis: Decimal | None = None


class PortfolioSnapshotRequest(BaseModel):
    position_date: date
    positions: list[PortfolioPositionUpsert]


class PortfolioPositionRead(BaseModel):
    position_date: date
    symbol: str
    position_name: str | None
    asset_type: str | None
    quantity: Decimal | None
    current_price: Decimal | None
    cost_price: Decimal | None
    market_value: Decimal | None
    weight: Decimal | None
    cost_basis: Decimal | None
    unrealized_pnl: Decimal | None
    unrealized_pnl_rate: Decimal | None
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


class InvestmentPlanCreate(BaseModel):
    plan_name: str
    run_id: int | None = None
    start_date: date
    months: int
    monthly_amount: Decimal
    note: str | None = None


class InvestmentPlanAnalyzeRequest(BaseModel):
    period_no: int = 1
    suggestion_date: date | None = None


class InvestmentPlanRead(BaseModel):
    id: int
    plan_name: str
    run_id: int | None
    start_date: date
    months: int
    monthly_amount: Decimal
    total_budget: Decimal
    status: str
    note: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvestmentPlanSuggestionRead(BaseModel):
    plan_id: int
    run_id: int | None
    suggestion_date: date
    period_no: int
    symbol: str
    target_weight: Decimal | None
    current_weight: Decimal | None
    gap_weight: Decimal | None
    suggested_amount: Decimal
    action_suggestion: str
    reason: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
