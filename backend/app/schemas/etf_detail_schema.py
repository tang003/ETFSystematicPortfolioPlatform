from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.asset_schema import AssetRead
from app.schemas.etf_compare_schema import EtfCompareMetric
from app.schemas.factor_schema import FactorRead
from app.schemas.market_schema import MarketBarRead


class EtfDetailCurvePoint(BaseModel):
    trade_date: date
    close: Decimal
    normalized_value: Decimal
    drawdown: Decimal
    amount: Decimal | None = None


class EtfAlternativeCandidate(BaseModel):
    symbol: str
    name: str
    fund_company: str | None = None
    tracking_index: str | None = None
    fund_size: Decimal | None = None
    expense_ratio: Decimal | None = None
    average_amount: Decimal | None = None
    tradability_score: int
    recommendation_score: int
    recommendation_level: str
    reasons: list[str]


class EtfDecisionSummary(BaseModel):
    action: str
    score: int
    level: str
    confidence: str
    position_hint: str
    entry_plan: str
    stop_loss_hint: str
    data_quality: str
    reasons: list[str]
    risks: list[str]
    next_steps: list[str]


class EtfDetailResponse(BaseModel):
    symbol: str
    asset: AssetRead | None = None
    metric: EtfCompareMetric
    decision: EtfDecisionSummary
    latest_factor: FactorRead | None = None
    alternatives: list[EtfAlternativeCandidate]
    curve: list[EtfDetailCurvePoint]
    recent_bars: list[MarketBarRead]
