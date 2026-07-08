from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class TargetPortfolioRead(BaseModel):
    run_id: int | None
    portfolio_date: date
    symbol: str
    raw_target_weight: Decimal | None
    final_target_weight: Decimal | None
    asset_class: str | None
    reason: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

