from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ReportLog(Base):
    __tablename__ = "report_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("strategy_run.id"))
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str | None] = mapped_column(String(200))
    file_path: Mapped[str | None] = mapped_column(String(500))
    content_markdown: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="generated")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

