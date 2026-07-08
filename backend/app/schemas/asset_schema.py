from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AssetRead(BaseModel):
    symbol: str
    name: str
    exchange: str | None
    asset_class: str
    asset_region: str | None
    currency: str
    is_cross_border: bool
    is_leveraged: bool
    is_inverse: bool
    enabled: bool
    risk_level: int
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

