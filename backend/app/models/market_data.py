from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Integer, JSON, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MarketDataRaw(Base):
    __tablename__ = "market_data_raw"
    __table_args__ = (UniqueConstraint("symbol", "trade_date", "source", name="uq_market_data_raw_symbol_date_source"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    open: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    high: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    low: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    close: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    volume: Mapped[Decimal | None] = mapped_column(Numeric(24, 4))
    amount: Mapped[Decimal | None] = mapped_column(Numeric(24, 4))
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    raw_payload: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class MarketDataClean(Base):
    __tablename__ = "market_data_clean"
    __table_args__ = (UniqueConstraint("symbol", "trade_date", name="uq_market_data_clean_symbol_date"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    open: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    high: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    low: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    close: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    volume: Mapped[Decimal | None] = mapped_column(Numeric(24, 4))
    amount: Mapped[Decimal | None] = mapped_column(Numeric(24, 4))
    is_adjusted: Mapped[bool] = mapped_column(Boolean, default=False)
    data_status: Mapped[str] = mapped_column(String(30), default="normal")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class EtfNavPremium(Base):
    __tablename__ = "etf_nav_premium"
    __table_args__ = (UniqueConstraint("symbol", "trade_date", name="uq_etf_nav_premium_symbol_date"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    nav: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    market_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    premium_rate: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    source: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class TradingCalendar(Base):
    __tablename__ = "trading_calendar"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, unique=True, nullable=False)
    market: Mapped[str] = mapped_column(String(20), default="CN")
    is_open: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

