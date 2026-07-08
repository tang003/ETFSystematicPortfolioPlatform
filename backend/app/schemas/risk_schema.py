from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class RiskCheckRequest(BaseModel):
    run_id: int


class RiskCheckResponse(BaseModel):
    run_id: int
    check_date: date
    result_count: int
    adjusted_count: int
    status: str


class RiskCheckResultRead(BaseModel):
    run_id: int | None
    check_date: date
    rule_code: str
    status: str
    message: str | None
    before_value: Decimal | None
    after_value: Decimal | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RebalanceGenerateRequest(BaseModel):
    run_id: int
    portfolio_value: Decimal = Field(default=Decimal("100000"), gt=0)


class RebalanceGenerateResponse(BaseModel):
    run_id: int
    order_date: date
    order_count: int
    status: str


class RebalanceOrderRead(BaseModel):
    run_id: int | None
    order_date: date
    symbol: str
    action: str
    current_weight: Decimal | None
    target_weight: Decimal | None
    weight_diff: Decimal | None
    estimated_amount: Decimal | None
    reason: str | None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

