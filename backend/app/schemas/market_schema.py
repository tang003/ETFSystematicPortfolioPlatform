from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class MarketSyncRequest(BaseModel):
    symbols: list[str] | None = Field(default=None, description="ETF symbols; empty means all enabled ETFs")
    sync_scope: str = Field(default="enabled", description="enabled, core, positions, target, plans, or all")
    start_date: date | None = Field(default=None, description="Start date; default is one year before end_date")
    end_date: date | None = Field(default=None, description="End date; default is today")
    source: str = Field(default="tushare", description="Tushare-only ETF daily bars")
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
    sync_scope: str
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


class MarketSyncPlanItem(BaseModel):
    symbol: str
    name: str | None = None
    categories: list[str]
    latest_trade_date: date | None = None
    has_clean_price: bool
    range_bar_count: int = 0
    range_latest_trade_date: date | None = None
    expected_bar_count: int | None = None
    missing_bar_count: int | None = None
    coverage_ratio: float | None = None
    sample_status: str = "empty"
    sample_message: str | None = None


class MarketSyncPlanResponse(BaseModel):
    sync_scope: str
    total_symbols: int
    missing_price_count: int
    ready_count: int = 0
    insufficient_count: int = 0
    empty_count: int = 0
    recommended_sync_symbols: list[str] = Field(
        default_factory=list,
        description="Symbols that are empty or below the minimum bar threshold in the selected analysis range",
    )
    expected_bar_count: int | None = None
    min_bars: int = 120
    symbols: list[MarketSyncPlanItem]


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
