from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class MarketSyncRequest(BaseModel):
    symbols: list[str] | None = Field(default=None, description="ETF 代码列表；为空时同步全部启用 ETF")
    start_date: date | None = Field(default=None, description="开始日期，默认近一年")
    end_date: date | None = Field(default=None, description="结束日期，默认今天")
    source: str = Field(default="akshare", description="行情来源")
    clean_after_sync: bool = Field(default=True, description="同步 raw 后是否写入 clean 表")


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
    total_symbols: int
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

