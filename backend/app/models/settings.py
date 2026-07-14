from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DataSourceConfig(Base):
    __tablename__ = "data_source_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider_code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    provider_name: Mapped[str] = mapped_column(String(120), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(40), default="market")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    base_url: Mapped[str | None] = mapped_column(String(500))
    auth_type: Mapped[str] = mapped_column(String(40), default="token")
    secret_value: Mapped[str | None] = mapped_column(Text)
    request_interval_seconds: Mapped[float | None] = mapped_column(Float)
    quota_per_minute: Mapped[int | None] = mapped_column(Integer)
    quota_per_day: Mapped[int | None] = mapped_column(Integer)
    supported_usages: Mapped[list[str]] = mapped_column(JSON, default=list)
    adapter_status: Mapped[str] = mapped_column(String(40), default="metadata_only")
    notes: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

