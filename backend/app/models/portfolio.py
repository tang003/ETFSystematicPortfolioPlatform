from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TargetPortfolio(Base):
    __tablename__ = "target_portfolio"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("strategy_run.id"))
    portfolio_date: Mapped[date] = mapped_column(Date, nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    raw_target_weight: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    final_target_weight: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    asset_class: Mapped[str | None] = mapped_column(String(30))
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class PortfolioPosition(Base):
    __tablename__ = "portfolio_position"
    __table_args__ = (UniqueConstraint("owner_username", "position_date", "symbol", name="uq_portfolio_position_owner_date_symbol"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    owner_username: Mapped[str | None] = mapped_column(String(100), index=True)
    position_date: Mapped[date] = mapped_column(Date, nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    position_name: Mapped[str | None] = mapped_column(String(100))
    asset_type: Mapped[str | None] = mapped_column(String(30))
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(24, 6))
    current_price: Mapped[Decimal | None] = mapped_column(Numeric(24, 6))
    cost_price: Mapped[Decimal | None] = mapped_column(Numeric(24, 6))
    market_value: Mapped[Decimal | None] = mapped_column(Numeric(24, 4))
    weight: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    cost_basis: Mapped[Decimal | None] = mapped_column(Numeric(24, 4))
    unrealized_pnl: Mapped[Decimal | None] = mapped_column(Numeric(24, 4))
    unrealized_pnl_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class HoldingAnalysisResult(Base):
    __tablename__ = "holding_analysis_result"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    owner_username: Mapped[str | None] = mapped_column(String(100), index=True)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("strategy_run.id"))
    analysis_date: Mapped[date] = mapped_column(Date, nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    current_weight: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    target_weight: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    weight_diff: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    action_suggestion: Mapped[str] = mapped_column(String(30), nullable=False)
    alpha_score: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class InvestmentPlan(Base):
    __tablename__ = "investment_plan"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    owner_username: Mapped[str | None] = mapped_column(String(100), index=True)
    plan_name: Mapped[str] = mapped_column(String(100), nullable=False)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("strategy_run.id"))
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    months: Mapped[int] = mapped_column(Integer, nullable=False)
    monthly_amount: Mapped[Decimal] = mapped_column(Numeric(24, 4), nullable=False)
    total_budget: Mapped[Decimal] = mapped_column(Numeric(24, 4), nullable=False)
    target_annual_return: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    investment_mode: Mapped[str] = mapped_column(String(30), nullable=False, default="scheduled_dca")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class InvestmentPlanSuggestion(Base):
    __tablename__ = "investment_plan_suggestion"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    owner_username: Mapped[str | None] = mapped_column(String(100), index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("investment_plan.id"), nullable=False)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("strategy_run.id"))
    suggestion_date: Mapped[date] = mapped_column(Date, nullable=False)
    period_no: Mapped[int] = mapped_column(Integer, nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    target_weight: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    current_weight: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    gap_weight: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    suggested_amount: Mapped[Decimal] = mapped_column(Numeric(24, 4), nullable=False)
    action_suggestion: Mapped[str] = mapped_column(String(30), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
