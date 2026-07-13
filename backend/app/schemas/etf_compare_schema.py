from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class EtfCompareRequest(BaseModel):
    symbols: list[str] = Field(min_length=1, max_length=8)
    start_date: date | None = None
    end_date: date | None = None


class EtfTradabilityRequest(BaseModel):
    symbols: list[str] = Field(min_length=1, max_length=3000)
    start_date: date | None = None
    end_date: date | None = None


class EtfScreenerRequest(BaseModel):
    scope: str = Field(default="enabled", description="enabled, core, positions, target, plans, all, or custom")
    symbols: list[str] | None = Field(default=None, max_length=3000)
    start_date: date | None = None
    end_date: date | None = None
    limit: int = Field(default=50, ge=1, le=500)
    min_bars: int = Field(default=120, ge=1, le=3000)
    min_tradability_score: int = Field(default=40, ge=0, le=100)
    min_buy_score: int = Field(default=0, ge=0, le=100)
    asset_class: str | None = None
    asset_region: str | None = None


class EtfCompareSeriesPoint(BaseModel):
    trade_date: date
    value: Decimal


class EtfCompareMetric(BaseModel):
    symbol: str
    name: str | None = None
    asset_class: str | None = None
    asset_region: str | None = None
    risk_level: int | None = None
    first_trade_date: date | None = None
    latest_trade_date: date | None = None
    latest_close: Decimal | None = None
    bars: int
    total_return: Decimal | None = None
    annualized_return: Decimal | None = None
    annualized_volatility: Decimal | None = None
    downside_volatility: Decimal | None = None
    max_drawdown: Decimal | None = None
    sharpe_ratio: Decimal | None = None
    sortino_ratio: Decimal | None = None
    calmar_ratio: Decimal | None = None
    positive_day_rate: Decimal | None = None
    estimated_gap_ratio: Decimal | None = None
    average_amount: Decimal | None = None
    tradability_score: int
    tradability_level: str
    tradability_notes: list[str]
    buy_score: int
    buy_level: str
    buy_notes: list[str]


class EtfCorrelationCell(BaseModel):
    symbol_x: str
    symbol_y: str
    correlation: Decimal | None


class EtfCompareResponse(BaseModel):
    start_date: date | None
    end_date: date | None
    metrics: list[EtfCompareMetric]
    normalized_series: dict[str, list[EtfCompareSeriesPoint]]
    correlations: list[EtfCorrelationCell]


class EtfScreenerResponse(BaseModel):
    start_date: date | None
    end_date: date | None
    scope: str
    total_candidates: int
    returned: int
    metrics: list[EtfCompareMetric]
