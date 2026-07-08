from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class BacktestRun(Base):
    __tablename__ = "backtest_run"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    strategy_code: Mapped[str] = mapped_column(String(100), nullable=False)
    strategy_version: Mapped[str | None] = mapped_column(String(30))
    name: Mapped[str | None] = mapped_column(String(100))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    initial_cash: Mapped[Decimal | None] = mapped_column(Numeric(24, 4))
    monthly_contribution: Mapped[Decimal | None] = mapped_column(Numeric(24, 4))
    fee_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 8))
    slippage_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 8))
    config: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(30), default="success")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class BacktestEquityCurve(Base):
    __tablename__ = "backtest_equity_curve"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    backtest_id: Mapped[int | None] = mapped_column(ForeignKey("backtest_run.id"))
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_equity: Mapped[Decimal | None] = mapped_column(Numeric(24, 4))
    cash: Mapped[Decimal | None] = mapped_column(Numeric(24, 4))
    drawdown: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    daily_return: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class BacktestTrade(Base):
    __tablename__ = "backtest_trade"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    backtest_id: Mapped[int | None] = mapped_column(ForeignKey("backtest_run.id"))
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    price: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(24, 6))
    amount: Mapped[Decimal | None] = mapped_column(Numeric(24, 4))
    fee: Mapped[Decimal | None] = mapped_column(Numeric(24, 4))
    slippage: Mapped[Decimal | None] = mapped_column(Numeric(24, 4))
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class BacktestMetrics(Base):
    __tablename__ = "backtest_metrics"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    backtest_id: Mapped[int | None] = mapped_column(ForeignKey("backtest_run.id"))
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_value: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    metric_unit: Mapped[str | None] = mapped_column(String(20))
    sort_order: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

