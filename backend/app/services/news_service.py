from __future__ import annotations

from datetime import datetime
from typing import Any

import requests
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.asset import AssetMaster
from app.models.news import NewsArticle
from app.models.settings import DataSourceConfig

JUHE_FINANCE_NEWS = "juhe_finance_news"

KEYWORD_RULES = [
    (["沪深300", "中证500", "中证1000", "中证a500", "a股", "上证", "深证"], "equity", "CN"),
    (["港股", "恒生", "恒指"], "equity", "HK"),
    (["美股", "标普", "纳指", "纳斯达克", "道指"], "equity", "US"),
    (["德国", "dax"], "equity", "DE"),
    (["日本", "日经"], "equity", "JP"),
    (["黄金", "金价", "贵金属"], "gold", "GLOBAL"),
    (["债券", "国债", "利率", "降息", "央行"], "bond", "CN"),
    (["原油", "商品", "能源"], "commodity", "GLOBAL"),
    (["消费", "白酒"], "equity", "CN"),
    (["半导体", "芯片", "科技", "人工智能", "ai"], "equity", "CN"),
    (["新能源", "光伏", "电池", "电力"], "equity", "CN"),
]


def sync_news(db: Session, *, source: str = JUHE_FINANCE_NEWS, num: int = 50, page: int = 1) -> dict[str, Any]:
    if source != JUHE_FINANCE_NEWS:
        raise ValueError("当前新闻适配器仅支持 juhe_finance_news")
    provider = get_enabled_provider(db, source)
    rows = fetch_juhe_finance_news(provider, num=num, page=page)
    assets = load_assets(db)
    inserted = 0
    updated = 0
    skipped = 0
    for row in rows:
        item = normalize_juhe_row(row, assets)
        if not item["external_id"] or not item["title"]:
            skipped += 1
            continue
        existing = db.scalar(
            select(NewsArticle)
            .where(NewsArticle.source == source)
            .where(NewsArticle.external_id == item["external_id"])
        )
        if existing is None:
            db.add(NewsArticle(source=source, **item))
            inserted += 1
        else:
            for key, value in item.items():
                setattr(existing, key, value)
            updated += 1
    db.commit()
    return {"source": source, "fetched": len(rows), "inserted": inserted, "updated": updated, "skipped": skipped}


def list_news(
    db: Session,
    *,
    symbol: str | None = None,
    q: str | None = None,
    limit: int = 50,
) -> list[NewsArticle]:
    statement = select(NewsArticle).order_by(NewsArticle.publish_time.desc().nullslast(), NewsArticle.created_at.desc())
    if q:
        like = f"%{q.strip()}%"
        statement = statement.where(or_(NewsArticle.title.ilike(like), NewsArticle.summary.ilike(like)))
    rows = list(db.scalars(statement.limit(min(limit * 4, 500))).all())
    if symbol:
        normalized = symbol.strip()
        rows = [row for row in rows if normalized in (row.related_symbols or [])]
    return rows[:limit]


def get_enabled_provider(db: Session, provider_code: str) -> DataSourceConfig:
    provider = db.scalar(select(DataSourceConfig).where(DataSourceConfig.provider_code == provider_code))
    if provider is None:
        raise ValueError(f"数据源未配置：{provider_code}")
    if not provider.enabled:
        raise ValueError(f"数据源已停用：{provider_code}")
    if not provider.secret_value:
        raise ValueError(f"数据源缺少 key：{provider_code}")
    return provider


def fetch_juhe_finance_news(provider: DataSourceConfig, *, num: int, page: int) -> list[dict[str, Any]]:
    response = requests.get(
        provider.base_url or "https://apis.juhe.cn/fapigx/caijing/query",
        params={"key": provider.secret_value, "num": num, "page": page},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    code = str(payload.get("error_code", "0"))
    if code not in {"0", ""}:
        raise RuntimeError(f"聚合数据财经新闻请求失败：{payload.get('reason') or code}")
    result = payload.get("result") or {}
    newslist = result.get("newslist") or []
    if not isinstance(newslist, list):
        return []
    return [item for item in newslist if isinstance(item, dict)]


def normalize_juhe_row(row: dict[str, Any], assets: list[AssetMaster]) -> dict[str, Any]:
    title = str(row.get("title") or "").strip()
    external_id = str(row.get("id") or row.get("url") or title).strip()
    keywords, asset_classes, regions = classify_title(title)
    related_symbols = match_assets(title, assets)
    return {
        "external_id": external_id[:160],
        "title": title[:500],
        "source_name": str(row.get("source") or "聚合数据").strip()[:120],
        "url": empty_to_none(row.get("url")),
        "image_url": empty_to_none(row.get("picUrl")),
        "publish_time": parse_publish_time(row.get("ctime")),
        "summary": None,
        "content": None,
        "keywords": keywords,
        "related_symbols": related_symbols,
        "related_asset_class": asset_classes,
        "related_region": regions,
        "sentiment_score": None,
        "impact_level": "normal" if keywords or related_symbols else "low",
        "raw_payload": row,
    }


def classify_title(title: str) -> tuple[list[str], list[str], list[str]]:
    lowered = title.lower()
    keywords: list[str] = []
    asset_classes: list[str] = []
    regions: list[str] = []
    for words, asset_class, region in KEYWORD_RULES:
        matched = [word for word in words if word.lower() in lowered]
        if not matched:
            continue
        keywords.extend(matched)
        asset_classes.append(asset_class)
        regions.append(region)
    return unique(keywords), unique(asset_classes), unique(regions)


def match_assets(title: str, assets: list[AssetMaster]) -> list[str]:
    matched: list[str] = []
    lowered = title.lower()
    for asset in assets:
        fields = [asset.symbol, asset.name, asset.tracking_index or ""]
        if any(field and field.lower() in lowered for field in fields):
            matched.append(asset.symbol)
    return unique(matched)


def load_assets(db: Session) -> list[AssetMaster]:
    return list(db.scalars(select(AssetMaster).where(AssetMaster.enabled.is_(True))).all())


def parse_publish_time(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    for pattern in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(text, pattern)
        except ValueError:
            continue
    return None


def empty_to_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result

