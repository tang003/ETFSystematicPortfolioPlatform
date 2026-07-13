from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


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
    fund_company: str | None = None
    tracking_index: str | None = None
    listing_date: date | None = None
    fund_size: Decimal | None = None
    management_fee: Decimal | None = None
    custody_fee: Decimal | None = None
    expense_ratio: Decimal | None = None
    tracking_error: Decimal | None = None
    latest_premium_rate: Decimal | None = None
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AssetUpsertItem(BaseModel):
    symbol: str = Field(min_length=6, max_length=32)
    name: str = Field(min_length=1, max_length=100)
    exchange: str | None = None
    asset_class: str = Field(default="equity")
    asset_region: str | None = Field(default="CN")
    currency: str = Field(default="CNY")
    is_cross_border: bool = False
    is_leveraged: bool = False
    is_inverse: bool = False
    enabled: bool = True
    risk_level: int = Field(default=3, ge=1, le=5)
    fund_company: str | None = None
    tracking_index: str | None = None
    listing_date: date | None = None
    fund_size: Decimal | None = None
    management_fee: Decimal | None = None
    custody_fee: Decimal | None = None
    expense_ratio: Decimal | None = None
    tracking_error: Decimal | None = None
    latest_premium_rate: Decimal | None = None
    description: str | None = None


class AssetBatchUpsertRequest(BaseModel):
    items: list[AssetUpsertItem]


class AssetBatchUpsertResponse(BaseModel):
    total: int
    inserted_or_updated: int


class AssetUniverseSyncRequest(BaseModel):
    source: str = Field(default="akshare")
    limit: int | None = Field(default=None, ge=1, le=3000)


class AssetUniverseSyncResponse(BaseModel):
    source: str
    total: int
    inserted_or_updated: int


class AssetUpdateRequest(BaseModel):
    enabled: bool | None = None
    risk_level: int | None = Field(default=None, ge=1, le=5)
    fund_company: str | None = None
    tracking_index: str | None = None
    listing_date: date | None = None
    fund_size: Decimal | None = None
    management_fee: Decimal | None = None
    custody_fee: Decimal | None = None
    expense_ratio: Decimal | None = None
    tracking_error: Decimal | None = None
    latest_premium_rate: Decimal | None = None
    description: str | None = None
