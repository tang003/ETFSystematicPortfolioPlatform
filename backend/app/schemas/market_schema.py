from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class MarketSyncRequest(BaseModel):
    symbols: list[str] | None = Field(default=None, description="ETF symbols; empty means all enabled ETFs")
    start_date: date | None = Field(default=None, description="Start date; default is one year before end_date")
    end_date: date | None = Field(default=None, description="End date; default is today")
    source: str = Field(default="akshare", description="akshare falls back to eastmoney when possible")
    incremental: bool = Field(default=False, description="Only fetch missing dates after the latest stored bar")
    clean_after_sync: bool = Field(default=True, description="Whether to write clean bars after raw sync")
    max_symbols: int | None = Field(default=None, ge=1, description="Maximum symbols to sync in this request")
    request_interval_seconds: float = Field(default=0, ge=0, le=10, description="Delay between symbols")


class SymbolSyncResult(BaseModel):
    symbol: str
    raw_rows: int = 0
    clean_rows: int = 0
    quality_logs: int = 0
    status: str
    message: str | None = None


class MarketSyncResponse(BaseModel):
    start_date: date
    end_date: date
    source: str
    incremental: bool
    request_interval_seconds: float
    total_symbols: int
    requested_symbols: int
    skipped_symbols: int
    up_to_date_symbols: int
    success_count: int
    failed_count: int
    total_raw_rows: int
    total_clean_rows: int
    total_quality_logs: int
    results: list[SymbolSyncResult]


class MarketBarRead(BaseModel):
    symbol: str
    trade_date: date
    open: Decimal | None
    high: Decimal | None
    low: Decimal | None
    close: Decimal | None
    volume: Decimal | None
    amount: Decimal | None
    source: str | None = None
    data_status: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
