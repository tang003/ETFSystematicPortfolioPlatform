from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DataQualityLog(Base):
    __tablename__ = "data_quality_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    symbol: Mapped[str | None] = mapped_column(String(32), index=True)
    trade_date: Mapped[date | None] = mapped_column(Date, index=True)
    check_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    message: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(20), default="info")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

