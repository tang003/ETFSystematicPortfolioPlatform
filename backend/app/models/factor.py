from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Date, DateTime, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FactorDaily(Base):
    __tablename__ = "factor_daily"
    __table_args__ = (UniqueConstraint("symbol", "trade_date", name="uq_factor_daily_symbol_date"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    ma20: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    ma60: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    ma120: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    ma200: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    ret_20d: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    ret_60d: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    ret_120d: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    ret_250d: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    volatility_60d: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    volatility_120d: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    drawdown_120d: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    drawdown_250d: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    liquidity_20d: Mapped[Decimal | None] = mapped_column(Numeric(24, 4))
    premium_rate: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    trend_score: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    momentum_score: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    volatility_score: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    drawdown_score: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    liquidity_score: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    premium_score: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    alpha_score: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

