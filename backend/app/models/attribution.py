from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PerformanceAttribution(Base):
    __tablename__ = "performance_attribution"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("strategy_run.id"))
    attribution_date: Mapped[date] = mapped_column(Date, nullable=False)
    period_type: Mapped[str] = mapped_column(String(30), nullable=False)
    dimension: Mapped[str] = mapped_column(String(50), nullable=False)
    symbol: Mapped[str | None] = mapped_column(String(32))
    asset_class: Mapped[str | None] = mapped_column(String(30))
    contribution_return: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    contribution_amount: Mapped[Decimal | None] = mapped_column(Numeric(24, 4))
    explanation: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

