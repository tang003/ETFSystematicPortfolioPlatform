from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AgentAnalysisLog(Base):
    __tablename__ = "agent_analysis_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    owner_username: Mapped[str | None] = mapped_column(String(100), index=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(100))
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    data_status: Mapped[str] = mapped_column(String(40), nullable=False)
    llm_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    llm_model: Mapped[str | None] = mapped_column(String(80))
    final_action: Mapped[str] = mapped_column(String(80), nullable=False)
    final_score: Mapped[int] = mapped_column(Integer, nullable=False)
    final_summary: Mapped[str] = mapped_column(Text, nullable=False)
    manager_commentary: Mapped[str] = mapped_column(Text, nullable=False)
    agents_payload: Mapped[list] = mapped_column(JSON, nullable=False)
    warnings_payload: Mapped[list] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
