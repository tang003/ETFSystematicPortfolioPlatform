from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class EtfCompareRequest(BaseModel):
    symbols: list[str] = Field(min_length=1, max_length=8)
    start_date: date | None = None
    end_date: date | None = None


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
    max_drawdown: Decimal | None = None
    average_amount: Decimal | None = None
    tradability_score: int
    tradability_level: str
    tradability_notes: list[str]


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
