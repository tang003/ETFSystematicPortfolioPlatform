from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AssetMaster(Base):
    __tablename__ = "asset_master"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    exchange: Mapped[str | None] = mapped_column(String(20))
    asset_class: Mapped[str] = mapped_column(String(30), nullable=False)
    asset_region: Mapped[str | None] = mapped_column(String(30))
    currency: Mapped[str] = mapped_column(String(10), default="CNY")
    is_cross_border: Mapped[bool] = mapped_column(Boolean, default=False)
    is_leveraged: Mapped[bool] = mapped_column(Boolean, default=False)
    is_inverse: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    risk_level: Mapped[int] = mapped_column(Integer, default=3)
    fund_company: Mapped[str | None] = mapped_column(String(100))
    tracking_index: Mapped[str | None] = mapped_column(String(100))
    listing_date: Mapped[date | None] = mapped_column(Date)
    fund_size: Mapped[Decimal | None] = mapped_column(Numeric(24, 4))
    management_fee: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    custody_fee: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    expense_ratio: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    tracking_error: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    latest_premium_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
