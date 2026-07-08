from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class StrategyConfig(Base):
    __tablename__ = "strategy_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    strategy_name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(30), nullable=False)
    rebalance_frequency: Mapped[str] = mapped_column(String(30), default="monthly")
    config: Mapped[dict] = mapped_column(JSON, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class StrategyRun(Base):
    __tablename__ = "strategy_run"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    strategy_code: Mapped[str] = mapped_column(String(100), nullable=False)
    strategy_version: Mapped[str | None] = mapped_column(String(30))
    run_date: Mapped[date] = mapped_column(Date, nullable=False)
    run_type: Mapped[str] = mapped_column(String(30), default="scheduled")
    status: Mapped[str] = mapped_column(String(30), default="success")
    message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AlphaSignal(Base):
    __tablename__ = "alpha_signal"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("strategy_run.id"))
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    signal_date: Mapped[date] = mapped_column(Date, nullable=False)
    alpha_score: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    rank_no: Mapped[int | None] = mapped_column(Integer)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    signal_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

