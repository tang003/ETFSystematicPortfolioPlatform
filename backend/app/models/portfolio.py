from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint, func
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
    __table_args__ = (UniqueConstraint("position_date", "symbol", name="uq_portfolio_position_date_symbol"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    position_date: Mapped[date] = mapped_column(Date, nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(24, 6))
    market_value: Mapped[Decimal | None] = mapped_column(Numeric(24, 4))
    weight: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    cost_basis: Mapped[Decimal | None] = mapped_column(Numeric(24, 4))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class HoldingAnalysisResult(Base):
    __tablename__ = "holding_analysis_result"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
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
