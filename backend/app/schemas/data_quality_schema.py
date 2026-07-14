from datetime import date, datetime

from pydantic import BaseModel, ConfigDict
from pydantic import Field


class DataQualityCheckRequest(BaseModel):
    symbols: list[str] = Field(description="需要检查的 ETF 代码列表")
    start_date: date
    end_date: date


class DataQualityCheckResult(BaseModel):
    symbol: str
    quality_logs: int
    status: str
    message: str | None = None


class DataQualityLogRead(BaseModel):
    symbol: str | None
    trade_date: date | None
    check_type: str
    status: str
    message: str | None
    severity: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DataQualityStatus(BaseModel):
    total_logs: int
    error_logs: int
    warning_logs: int
    latest_created_at: datetime | None
    status: str
    history_total_logs: int = 0
    history_error_logs: int = 0
    history_warning_logs: int = 0
