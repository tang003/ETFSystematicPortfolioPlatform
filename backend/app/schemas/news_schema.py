from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class NewsArticleRead(BaseModel):
    id: int
    source: str
    external_id: str
    title: str
    source_name: str | None = None
    url: str | None = None
    image_url: str | None = None
    publish_time: datetime | None = None
    summary: str | None = None
    keywords: list[str] = []
    related_symbols: list[str] = []
    related_asset_class: list[str] = []
    related_region: list[str] = []
    sentiment_score: float | None = None
    impact_level: str | None = None
    raw_payload: dict[str, Any] = {}
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NewsSyncRequest(BaseModel):
    source: str = Field(default="juhe_finance_news")
    num: int = Field(default=50, ge=1, le=50)
    page: int = Field(default=1, ge=1, le=50)


class NewsSyncResponse(BaseModel):
    source: str
    fetched: int
    inserted: int
    updated: int
    skipped: int

