from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class NewsArticle(Base):
    __tablename__ = "news_article"
    __table_args__ = (UniqueConstraint("source", "external_id", name="uq_news_article_source_external_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(160), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    source_name: Mapped[str | None] = mapped_column(String(120))
    url: Mapped[str | None] = mapped_column(String(1000))
    image_url: Mapped[str | None] = mapped_column(String(1000))
    publish_time: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    summary: Mapped[str | None] = mapped_column(Text)
    content: Mapped[str | None] = mapped_column(Text)
    keywords: Mapped[list[str]] = mapped_column(JSON, default=list)
    related_symbols: Mapped[list[str]] = mapped_column(JSON, default=list)
    related_asset_class: Mapped[list[str]] = mapped_column(JSON, default=list)
    related_region: Mapped[list[str]] = mapped_column(JSON, default=list)
    sentiment_score: Mapped[float | None] = mapped_column(Float)
    impact_level: Mapped[str | None] = mapped_column(String(40))
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
