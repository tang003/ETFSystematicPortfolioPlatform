from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class CalendarSyncRequest(BaseModel):
    start_date: date
    end_date: date
    market: str = Field(default="CN")
    source: str = Field(default="akshare")


class CalendarSyncResponse(BaseModel):
    start_date: date
    end_date: date
    market: str
    source: str
    open_days: int


class TradingCalendarRead(BaseModel):
    trade_date: date
    market: str
    is_open: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
