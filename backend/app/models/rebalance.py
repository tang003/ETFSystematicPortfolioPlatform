from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RebalanceOrder(Base):
    __tablename__ = "rebalance_order"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("strategy_run.id"))
    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    current_weight: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    target_weight: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    weight_diff: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    estimated_amount: Mapped[Decimal | None] = mapped_column(Numeric(24, 4))
    reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

