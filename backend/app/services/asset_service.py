from typing import Any

import akshare as ak
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.asset import AssetMaster
from app.schemas.asset_schema import AssetUpsertItem


def list_assets(db: Session, enabled: bool | None = None) -> list[AssetMaster]:
    query = select(AssetMaster).order_by(AssetMaster.asset_class, AssetMaster.symbol)
    if enabled is not None:
        query = query.where(AssetMaster.enabled.is_(enabled))
    return list(db.scalars(query).all())


def batch_upsert_assets(db: Session, items: list[AssetUpsertItem]) -> int:
    if not items:
        return 0
    payload = [item.model_dump() for item in items]
    statement = insert(AssetMaster).values(payload)
    db.execute(
        statement.on_conflict_do_update(
            index_elements=["symbol"],
            set_={
                "name": statement.excluded.name,
                "exchange": statement.excluded.exchange,
                "asset_class": statement.excluded.asset_class,
                "asset_region": statement.excluded.asset_region,
                "currency": statement.excluded.currency,
                "is_cross_border": statement.excluded.is_cross_border,
                "is_leveraged": statement.excluded.is_leveraged,
                "is_inverse": statement.excluded.is_inverse,
                "enabled": statement.excluded.enabled,
                "risk_level": AssetMaster.risk_level,
                "description": AssetMaster.description,
            },
        )
    )
    db.commit()
    return len(payload)


def sync_etf_universe(db: Session, *, source: str = "akshare", limit: int | None = None) -> dict[str, int | str]:
    if source != "akshare":
        raise ValueError("ETF 全市场同步当前仅支持 source=akshare")
    items = fetch_akshare_etf_universe(limit=limit)
    return {
        "source": source,
        "total": len(items),
        "inserted_or_updated": upsert_market_assets_preserve_enabled(db, items),
    }


def fetch_akshare_etf_universe(limit: int | None = None) -> list[AssetUpsertItem]:
    frame = ak.fund_etf_spot_em()
    items: list[AssetUpsertItem] = []
    for row in frame.to_dict("records"):
        item = build_asset_item_from_market_row(row)
        if item is None:
            continue
        items.append(item)
        if limit is not None and len(items) >= limit:
            break
    if not items:
        raise ValueError("AKShare 未返回可识别的 ETF 基础列表")
    return items


def build_asset_item_from_market_row(row: dict[str, Any]) -> AssetUpsertItem | None:
    symbol = normalize_symbol(first_value(row, "代码", "基金代码", "symbol", "code"))
    name = str(first_value(row, "名称", "基金简称", "name") or "").strip()
    if not symbol or not name:
        return None
    meta = classify_etf_asset(symbol, name)
    return AssetUpsertItem(
        symbol=symbol,
        name=name,
        exchange=infer_exchange(symbol),
        currency="CNY",
        enabled=False,
        description="全市场 ETF 基础池自动同步；默认不启用研究，启用后才进入行情、因子、策略和回测流程。",
        **meta,
    )


def upsert_market_assets_preserve_enabled(db: Session, items: list[AssetUpsertItem]) -> int:
    if not items:
        return 0
    payload = [item.model_dump() for item in items]
    statement = insert(AssetMaster).values(payload)
    db.execute(
        statement.on_conflict_do_update(
            index_elements=["symbol"],
            set_={
                "name": statement.excluded.name,
                "exchange": statement.excluded.exchange,
                "asset_class": statement.excluded.asset_class,
                "asset_region": statement.excluded.asset_region,
                "currency": statement.excluded.currency,
                "is_cross_border": statement.excluded.is_cross_border,
                "is_leveraged": statement.excluded.is_leveraged,
                "is_inverse": statement.excluded.is_inverse,
                "enabled": AssetMaster.enabled,
                "risk_level": statement.excluded.risk_level,
                "description": statement.excluded.description,
            },
        )
    )
    db.commit()
    return len(payload)


def first_value(row: dict[str, Any], *keys: str) -> Any:
    lowered = {str(key).lower(): value for key, value in row.items()}
    for key in keys:
        if key in row:
            return row[key]
        lowered_value = lowered.get(key.lower())
        if lowered_value is not None:
            return lowered_value
    return None


def normalize_symbol(value: Any) -> str | None:
    if value is None:
        return None
    symbol = str(value).strip()
    if symbol.endswith(".0"):
        symbol = symbol[:-2]
    symbol = symbol.zfill(6) if symbol.isdigit() and len(symbol) < 6 else symbol
    if len(symbol) != 6 or not symbol.isdigit():
        return None
    return symbol


def infer_exchange(symbol: str) -> str:
    if symbol.startswith(("5", "6", "9")):
        return "SH"
    return "SZ"


def classify_etf_asset(symbol: str, name: str) -> dict[str, Any]:
    normalized_name = name.upper()
    is_cross_border = any(
        keyword in normalized_name
        for keyword in ["QDII", "恒生", "港股", "中概", "纳指", "纳斯达克", "标普", "德国", "日经", "印度", "法国", "海外", "美国", "全球"]
    )
    if any(keyword in normalized_name for keyword in ["货币", "现金", "添富快线", "日利"]):
        asset_class = "cash"
        region = "CN"
        risk_level = 1
    elif any(keyword in normalized_name for keyword in ["债", "国债", "政金债", "可转债"]):
        asset_class = "bond"
        region = "CN"
        risk_level = 2
    elif any(keyword in normalized_name for keyword in ["黄金", "商品", "有色", "能源", "豆粕"]):
        asset_class = "gold" if "黄金" in normalized_name else "commodity"
        region = "CN"
        risk_level = 3
    elif is_cross_border:
        asset_class = "qdii"
        region = infer_cross_border_region(normalized_name)
        risk_level = 5 if any(keyword in normalized_name for keyword in ["科技", "互联网", "纳指", "纳斯达克", "中概"]) else 4
    else:
        asset_class = "equity"
        region = "CN"
        risk_level = 5 if any(keyword in normalized_name for keyword in ["芯片", "半导体", "科创", "创业", "军工", "新能源", "光伏"]) else 4
    return {
        "asset_class": asset_class,
        "asset_region": region,
        "is_cross_border": is_cross_border,
        "is_leveraged": any(keyword in normalized_name for keyword in ["杠杆", "2X", "两倍"]),
        "is_inverse": any(keyword in normalized_name for keyword in ["反向", "做空", "SHORT"]),
        "risk_level": risk_level,
    }


def infer_cross_border_region(name: str) -> str:
    if any(keyword in name for keyword in ["中概", "中国互联网", "中证海外中国"]):
        return "CN_HK_US"
    if any(keyword in name for keyword in ["恒生", "港股", "香港", "H股"]):
        return "HK"
    if any(keyword in name for keyword in ["纳指", "纳斯达克", "标普", "美国"]):
        return "US"
    if any(keyword in name for keyword in ["日经", "日本"]):
        return "JP"
    if any(keyword in name for keyword in ["德国"]):
        return "DE"
    return "GLOBAL"


def update_asset(
    db: Session,
    symbol: str,
    *,
    enabled: bool | None = None,
    risk_level: int | None = None,
    description: str | None = None,
) -> AssetMaster | None:
    asset = db.scalar(select(AssetMaster).where(AssetMaster.symbol == symbol))
    if asset is None:
        return None
    if enabled is not None:
        asset.enabled = enabled
    if risk_level is not None:
        asset.risk_level = risk_level
    if description is not None:
        asset.description = description
    db.commit()
    db.refresh(asset)
    return asset
