from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class WorkflowRunRequest(BaseModel):
    symbols: list[str] | None = None
    start_date: date
    end_date: date
    max_symbols: int | None = Field(default=10, ge=1)
    calendar_source: str = Field(default="akshare")
    market_source: str = Field(default="akshare")
    incremental_sync: bool = Field(default=True)
    request_interval_seconds: float = Field(default=0, ge=0, le=10)
    strict_data_validation: bool = Field(default=True)
    minimum_history_bars: int = Field(default=200, ge=20, le=1000)
    strategy_code: str = Field(default="core_etf_rotation")
    portfolio_value: Decimal = Field(default=Decimal("100000"), gt=0)
    generate_report: bool = True


class HistoricalMarketInitRequest(BaseModel):
    scope: str = Field(default="curated", description="curated, enabled, core, positions, or custom")
    symbols: list[str] | None = None
    years: int = Field(default=10, ge=1, le=15)
    start_date: date | None = None
    end_date: date | None = None
    source: str = Field(default="tushare")
    calendar_source: str = Field(default="tushare")
    incremental_sync: bool = True
    clean_after_sync: bool = True
    request_interval_seconds: float = Field(default=0.2, ge=0, le=10)
    max_symbols: int | None = Field(default=None, ge=1)


class WorkflowTaskCreateResponse(BaseModel):
    task_id: int
    status: str


class WorkflowTaskStepRead(BaseModel):
    id: int
    task_id: int
    step_key: str
    step_name: str
    sort_order: int
    status: str
    message: str | None
    result_payload: dict | None
    started_at: datetime | None
    finished_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class WorkflowTaskRead(BaseModel):
    id: int
    task_type: str
    status: str
    current_step: str | None
    request_payload: dict
    result_payload: dict | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    steps: list[WorkflowTaskStepRead]

    model_config = ConfigDict(from_attributes=True)
