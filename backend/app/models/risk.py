from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RiskRule(Base):
    __tablename__ = "risk_rule"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    rule_name: Mapped[str] = mapped_column(String(100), nullable=False)
    rule_type: Mapped[str | None] = mapped_column(String(50))
    threshold: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    config: Mapped[dict | None] = mapped_column(JSON)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    severity: Mapped[str] = mapped_column(String(20), default="warning")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class RiskCheckResult(Base):
    __tablename__ = "risk_check_result"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("strategy_run.id"))
    check_date: Mapped[date] = mapped_column(Date, nullable=False)
    rule_code: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    message: Mapped[str | None] = mapped_column(Text)
    before_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    after_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

