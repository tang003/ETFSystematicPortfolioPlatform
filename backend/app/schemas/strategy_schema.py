from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class StrategyConfigRead(BaseModel):
    strategy_code: str
    strategy_name: str
    version: str
    rebalance_frequency: str
    config: dict
    enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StrategyRunRequest(BaseModel):
    strategy_code: str = Field(default="core_etf_rotation")
    run_date: date | None = None
    run_type: str = Field(default="manual")


class StrategyRunResponse(BaseModel):
    run_id: int
    strategy_code: str
    strategy_version: str
    run_date: date
    signal_count: int
    target_count: int
    status: str


class AlphaSignalRead(BaseModel):
    run_id: int | None
    symbol: str
    signal_date: date
    alpha_score: Decimal | None
    rank_no: int | None
    confidence: Decimal | None
    signal_reason: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

