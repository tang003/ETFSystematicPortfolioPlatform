from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class FactorCalculateRequest(BaseModel):
    symbols: list[str] | None = Field(default=None, description="ETF symbols; empty means all enabled ETFs")
    start_date: date | None = None
    end_date: date | None = None


class SymbolFactorResult(BaseModel):
    symbol: str
    factor_rows: int
    status: str
    message: str | None = None


class FactorCalculateResponse(BaseModel):
    total_symbols: int
    success_count: int
    failed_count: int
    total_factor_rows: int
    results: list[SymbolFactorResult]


class FactorRead(BaseModel):
    symbol: str
    trade_date: date
    ma20: Decimal | None
    ma60: Decimal | None
    ma120: Decimal | None
    ma200: Decimal | None
    ret_20d: Decimal | None
    ret_60d: Decimal | None
    ret_120d: Decimal | None
    ret_250d: Decimal | None
    volatility_60d: Decimal | None
    volatility_120d: Decimal | None
    drawdown_120d: Decimal | None
    drawdown_250d: Decimal | None
    liquidity_20d: Decimal | None
    premium_rate: Decimal | None
    trend_score: Decimal | None
    momentum_score: Decimal | None
    volatility_score: Decimal | None
    drawdown_score: Decimal | None
    liquidity_score: Decimal | None
    premium_score: Decimal | None
    alpha_score: Decimal | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FactorResearchRequest(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    forward_days: int = Field(default=20, ge=1, le=250)
    quantiles: int = Field(default=3, ge=2, le=10)


class FactorIcMetric(BaseModel):
    factor_name: str
    observations: int
    mean_ic: Decimal | None
    mean_rank_ic: Decimal | None
    positive_ic_ratio: Decimal | None
    effective: bool


class FactorCorrelationMetric(BaseModel):
    factor_x: str
    factor_y: str
    correlation: Decimal | None


class FactorQuantileReturnMetric(BaseModel):
    factor_name: str
    quantile: int
    mean_forward_return: Decimal | None
    observations: int


class FactorResearchResponse(BaseModel):
    start_date: date | None
    end_date: date | None
    forward_days: int
    quantiles: int
    factor_count: int
    sample_count: int
    ic_metrics: list[FactorIcMetric]
    correlations: list[FactorCorrelationMetric]
    quantile_returns: list[FactorQuantileReturnMetric]
