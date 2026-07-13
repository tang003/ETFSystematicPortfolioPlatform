from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import time
from typing import Any

import akshare as ak
import requests
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.asset import AssetMaster
from app.models.asset_sync_log import AssetSyncLog
from app.schemas.asset_schema import AssetUpdateRequest, AssetUpsertItem

UPSERT_FIELDS = [
    "name",
    "exchange",
    "asset_class",
    "asset_region",
    "currency",
    "is_cross_border",
    "is_leveraged",
    "is_inverse",
    "enabled",
    "risk_level",
    "fund_company",
    "tracking_index",
    "listing_date",
    "fund_size",
    "management_fee",
    "custody_fee",
    "expense_ratio",
    "tracking_error",
    "latest_premium_rate",
    "description",
]

MARKET_SYNC_PRESERVE_FIELDS = {
    "enabled": AssetMaster.enabled,
    "fund_company": AssetMaster.fund_company,
    "tracking_index": AssetMaster.tracking_index,
    "listing_date": AssetMaster.listing_date,
    "fund_size": AssetMaster.fund_size,
    "management_fee": AssetMaster.management_fee,
    "custody_fee": AssetMaster.custody_fee,
    "expense_ratio": AssetMaster.expense_ratio,
    "tracking_error": AssetMaster.tracking_error,
    "latest_premium_rate": AssetMaster.latest_premium_rate,
}


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
            set_={field: getattr(statement.excluded, field) for field in UPSERT_FIELDS},
        )
    )
    db.commit()
    return len(payload)


def sync_etf_universe(db: Session, *, source: str = "auto", limit: int | None = None) -> dict[str, int | str]:
    if source not in {"auto", "akshare", "eastmoney"}:
        raise ValueError("ETF 基础池同步当前支持 source=auto、akshare、eastmoney")
    try:
        items, actual_source = fetch_etf_universe(source=source, limit=limit)
        inserted = upsert_market_assets_preserve_enabled(db, items)
        result = {
            "source": actual_source,
            "total": len(items),
            "inserted_or_updated": inserted,
        }
        safe_write_asset_sync_log(
            db,
            sync_type="universe",
            result={"source": actual_source, "total": len(items), "updated": inserted, "skipped": 0, "failed": 0, "results": []},
            message="ETF 基础池同步完成",
        )
        return result
    except Exception as exc:
        safe_write_asset_sync_log(
            db,
            sync_type="universe",
            result={"source": source, "total": 1, "updated": 0, "skipped": 0, "failed": 1, "results": [{"message": friendly_external_error(exc)}]},
            message="ETF 基础池同步失败，已保留本地已有 ETF 池",
        )
        raise RuntimeError(friendly_external_error(exc)) from exc


def sync_etf_profiles(
    db: Session,
    *,
    source: str = "akshare",
    symbols: list[str] | None = None,
    limit: int | None = 100,
    preserve_existing: bool = True,
) -> dict[str, Any]:
    if source != "akshare":
        raise ValueError("ETF 资料补全当前仅支持 source=akshare")
    normalized_symbols = [symbol for symbol in (normalize_symbol(item) for item in symbols or []) if symbol]
    assets = resolve_profile_assets(db, normalized_symbols, limit=limit)
    if not assets:
        result = {"source": source, "total": 0, "updated": 0, "skipped": 0, "failed": 0, "results": []}
        safe_write_asset_sync_log(db, sync_type="profile", result=result, message="没有匹配到需要补全的 ETF")
        return result

    market_rows = fetch_akshare_etf_spot_rows()
    results: list[dict[str, Any]] = []
    updated_count = 0
    skipped_count = 0
    failed_count = 0
    for asset in assets:
        try:
            row = market_rows.get(asset.symbol, {})
            profile = build_profile_patch(asset.symbol, asset.name, row)
            updated_fields = apply_profile_patch(asset, profile, preserve_existing=preserve_existing)
            if updated_fields:
                updated_count += 1
                status = "updated"
                message = "已补全 ETF 主资料"
            else:
                skipped_count += 1
                status = "skipped"
                message = "没有可补充的新字段"
            results.append(
                {
                    "symbol": asset.symbol,
                    "status": status,
                    "updated_fields": updated_fields,
                    "message": message,
                }
            )
        except Exception as exc:  # noqa: BLE001 - one symbol failing should not stop the batch.
            failed_count += 1
            results.append(
                {
                    "symbol": asset.symbol,
                    "status": "failed",
                    "updated_fields": [],
                    "message": str(exc),
                }
            )
    result = {
        "source": source,
        "total": len(assets),
        "updated": updated_count,
        "skipped": skipped_count,
        "failed": failed_count,
        "results": results,
    }
    db.commit()
    safe_write_asset_sync_log(db, sync_type="profile", result=result, message="ETF 主资料补全完成")
    return result


def list_asset_sync_logs(db: Session, *, sync_type: str | None = None, limit: int = 20) -> list[AssetSyncLog]:
    query = select(AssetSyncLog)
    if sync_type:
        query = query.where(AssetSyncLog.sync_type == sync_type)
    query = query.order_by(AssetSyncLog.created_at.desc(), AssetSyncLog.id.desc()).limit(limit)
    return list(db.scalars(query).all())


def write_asset_sync_log(db: Session, *, sync_type: str, result: dict[str, Any], message: str | None = None) -> None:
    failed = int(result.get("failed") or 0)
    status = "failed" if failed and failed >= int(result.get("total") or 0) else "partial" if failed else "success"
    db.add(
        AssetSyncLog(
            sync_type=sync_type,
            source=str(result.get("source") or "unknown"),
            status=status,
            total=int(result.get("total") or 0),
            updated=int(result.get("updated") or 0),
            skipped=int(result.get("skipped") or 0),
            failed=failed,
            message=message,
            details={"results": result.get("results", [])[:200]},
        )
    )


def safe_write_asset_sync_log(db: Session, *, sync_type: str, result: dict[str, Any], message: str | None = None) -> None:
    try:
        write_asset_sync_log(db, sync_type=sync_type, result=result, message=message)
        db.commit()
    except SQLAlchemyError:
        db.rollback()


def fetch_etf_universe(*, source: str = "auto", limit: int | None = None) -> tuple[list[AssetUpsertItem], str]:
    errors: list[Exception] = []
    if source in {"auto", "akshare"}:
        try:
            return fetch_akshare_etf_universe(limit=limit), "akshare"
        except Exception as exc:  # noqa: BLE001 - fallback source is intentionally attempted.
            errors.append(exc)
            if source == "akshare":
                raise
    if source in {"auto", "eastmoney"}:
        try:
            return fetch_eastmoney_etf_universe(limit=limit), "eastmoney"
        except Exception as exc:  # noqa: BLE001 - caller receives a friendly combined error.
            errors.append(exc)
    if errors:
        raise RuntimeError("；".join(friendly_external_error(error) for error in errors))
    raise ValueError("没有可用 ETF 基础池数据源")


def fetch_akshare_etf_universe(limit: int | None = None, *, retries: int = 3, retry_interval_seconds: float = 1.2) -> list[AssetUpsertItem]:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            frame = ak.fund_etf_spot_em()
            break
        except Exception as exc:  # noqa: BLE001 - external provider retry.
            last_error = exc
            if attempt < retries:
                time.sleep(retry_interval_seconds * attempt)
    else:
        raise RuntimeError(f"AKShare/东方财富 ETF 列表接口连续 {retries} 次不可用：{last_error}") from last_error
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


def fetch_eastmoney_etf_universe(limit: int | None = None) -> list[AssetUpsertItem]:
    rows = fetch_eastmoney_etf_rows(limit=limit)
    items: list[AssetUpsertItem] = []
    for row in rows:
        item = build_asset_item_from_market_row(row)
        if item is None:
            continue
        items.append(item)
        if limit is not None and len(items) >= limit:
            break
    if not items:
        raise ValueError("东方财富备用接口未返回可识别的 ETF 基础列表")
    return items


def fetch_eastmoney_etf_rows(limit: int | None = None, *, retries: int = 3, retry_interval_seconds: float = 1.2) -> list[dict[str, Any]]:
    page_size = min(max(limit or 5000, 1), 5000)
    params = {
        "pn": "1",
        "pz": str(page_size),
        "po": "1",
        "np": "1",
        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
        "fltt": "2",
        "invt": "2",
        "wbp2u": "|0|0|0|web",
        "fid": "f12",
        "fs": "b:MK0021,b:MK0022,b:MK0023,b:MK0024,b:MK0827",
        "fields": "f12,f13,f14,f20,f21,f38,f402,f297",
    }
    hosts = ["88.push2.eastmoney.com", "push2.eastmoney.com", "21.push2.eastmoney.com"]
    last_error: Exception | None = None
    response: requests.Response | None = None
    for attempt in range(1, retries + 1):
        for host in hosts:
            try:
                response = requests.get(
                    f"https://{host}/api/qt/clist/get",
                    params=params,
                    headers={"User-Agent": "Mozilla/5.0"},
                    timeout=15,
                )
                response.raise_for_status()
                break
            except requests.RequestException as exc:
                last_error = exc
                response = None
        if response is not None:
            break
        if attempt < retries:
            time.sleep(retry_interval_seconds * attempt)
    if response is None:
        raise RuntimeError(f"东方财富备用接口连续 {retries} 次不可用：{last_error}") from last_error
    payload = response.json()
    if payload.get("rc") != 0:
        raise RuntimeError(f"东方财富备用接口返回异常 rc={payload.get('rc')}")
    rows = payload.get("data", {}).get("diff") or []
    normalized_rows: list[dict[str, Any]] = []
    for row in rows:
        normalized_rows.append(
            {
                "代码": row.get("f12"),
                "名称": row.get("f14"),
                "总市值": row.get("f20"),
                "流通市值": row.get("f21"),
                "最新份额": row.get("f38"),
                "基金折价率": row.get("f402"),
                "数据日期": row.get("f297"),
            }
        )
    return normalized_rows


def friendly_external_error(error: Exception) -> str:
    text = str(error)
    if "RemoteDisconnected" in text or "Connection aborted" in text:
        return "外部 ETF 列表接口主动断开连接，通常是数据源限流或临时不稳定；本地已有 ETF 池已保留，请稍后重试"
    if "Read timed out" in text or "timeout" in text.lower():
        return "外部 ETF 列表接口响应超时；本地已有 ETF 池已保留，请稍后重试"
    if "8000" in text and "积分" in text:
        return "当前 Tushare 权限不足，ETF 基础信息接口通常需要更高积分；请改用 auto/akshare/eastmoney"
    return f"外部 ETF 列表接口暂不可用：{text}"


def fetch_akshare_etf_spot_rows() -> dict[str, dict[str, Any]]:
    try:
        frame = ak.fund_etf_spot_em()
    except Exception:
        return {}
    rows: dict[str, dict[str, Any]] = {}
    for row in frame.to_dict("records"):
        symbol = normalize_symbol(first_value(row, "代码", "基金代码", "symbol", "code"))
        if symbol:
            rows[symbol] = row
    return rows


def resolve_profile_assets(db: Session, symbols: list[str], *, limit: int | None) -> list[AssetMaster]:
    query = select(AssetMaster).order_by(AssetMaster.enabled.desc(), AssetMaster.symbol)
    if symbols:
        query = query.where(AssetMaster.symbol.in_(symbols))
    if limit is not None:
        query = query.limit(limit)
    return list(db.scalars(query).all())


def build_profile_patch(symbol: str, name: str, row: dict[str, Any] | None = None) -> dict[str, Any]:
    row = row or {}
    market_name = str(first_value(row, "名称", "基金简称", "name") or "").strip()
    effective_name = market_name or name
    management_fee = to_ratio_decimal(first_value(row, "管理费率", "管理费", "management_fee"))
    custody_fee = to_ratio_decimal(first_value(row, "托管费率", "托管费", "custody_fee"))
    expense_ratio = to_ratio_decimal(first_value(row, "综合费率", "费率", "expense_ratio"))
    if expense_ratio is None and (management_fee is not None or custody_fee is not None):
        expense_ratio = (management_fee or Decimal("0")) + (custody_fee or Decimal("0"))
    return {
        "name": effective_name,
        "exchange": infer_exchange(symbol),
        "fund_company": infer_fund_company(effective_name),
        "tracking_index": infer_tracking_index(effective_name),
        "listing_date": to_date(first_value(row, "上市日期", "成立日期", "日期", "listing_date")),
        "fund_size": to_money_decimal(first_value(row, "基金规模", "最新规模", "规模", "总市值", "流通市值", "总份额")),
        "management_fee": management_fee,
        "custody_fee": custody_fee,
        "expense_ratio": expense_ratio,
        "tracking_error": to_ratio_decimal(first_value(row, "跟踪误差", "年化跟踪误差", "tracking_error")),
        "latest_premium_rate": to_ratio_decimal(first_value(row, "溢价率", "折溢价率", "premium_rate")),
        "description": build_profile_description(symbol, effective_name),
        **classify_etf_asset(symbol, effective_name),
    }


def apply_profile_patch(asset: AssetMaster, profile: dict[str, Any], *, preserve_existing: bool) -> list[str]:
    updated_fields: list[str] = []
    for field, value in profile.items():
        if value is None or value == "":
            continue
        current_value = getattr(asset, field)
        if preserve_existing and current_value not in (None, ""):
            continue
        if current_value == value:
            continue
        setattr(asset, field, value)
        updated_fields.append(field)
    return updated_fields


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
    update_fields = {field: getattr(statement.excluded, field) for field in UPSERT_FIELDS}
    update_fields.update(MARKET_SYNC_PRESERVE_FIELDS)
    db.execute(
        statement.on_conflict_do_update(
            index_elements=["symbol"],
            set_=update_fields,
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
    if any(keyword in normalized_name for keyword in ["货币", "现金", "添富快线", "日利", "保证金"]):
        asset_class = "cash"
        region = "CN"
        risk_level = 1
    elif any(keyword in normalized_name for keyword in ["债", "国债", "政金债", "可转债"]):
        asset_class = "bond"
        region = "CN"
        risk_level = 2
    elif any(keyword in normalized_name for keyword in ["黄金", "商品", "有色", "能源", "豆粕", "原油"]):
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
    if any(keyword in name for keyword in ["中概", "中国互联网", "海外中国"]):
        return "CN_HK_US"
    if any(keyword in name for keyword in ["恒生", "港股", "香港", "H股"]):
        return "HK"
    if any(keyword in name for keyword in ["纳指", "纳斯达克", "标普", "美国"]):
        return "US"
    if any(keyword in name for keyword in ["日经", "日本"]):
        return "JP"
    if "德国" in name:
        return "DE"
    return "GLOBAL"


def infer_fund_company(name: str) -> str | None:
    company_prefixes = {
        "华夏": "华夏基金",
        "华泰柏瑞": "华泰柏瑞基金",
        "易方达": "易方达基金",
        "嘉实": "嘉实基金",
        "南方": "南方基金",
        "广发": "广发基金",
        "国泰": "国泰基金",
        "富国": "富国基金",
        "博时": "博时基金",
        "鹏华": "鹏华基金",
        "银华": "银华基金",
        "华安": "华安基金",
        "天弘": "天弘基金",
        "招商": "招商基金",
        "工银": "工银瑞信基金",
        "景顺长城": "景顺长城基金",
        "汇添富": "汇添富基金",
        "建信": "建信基金",
        "平安": "平安基金",
        "中欧": "中欧基金",
        "华宝": "华宝基金",
        "国联安": "国联安基金",
        "海富通": "海富通基金",
        "大成": "大成基金",
    }
    compact_name = name.replace(" ", "")
    for prefix, company in company_prefixes.items():
        if compact_name.startswith(prefix):
            return company
    return None


def infer_tracking_index(name: str) -> str | None:
    index_keywords = [
        ("沪深300", "沪深300"),
        ("中证A500", "中证A500"),
        ("A500", "中证A500"),
        ("中证500", "中证500"),
        ("中证1000", "中证1000"),
        ("上证50", "上证50"),
        ("科创50", "科创50"),
        ("创业板50", "创业板50"),
        ("创业板", "创业板指"),
        ("恒生科技", "恒生科技"),
        ("恒生互联网", "恒生互联网科技业"),
        ("恒生", "恒生指数"),
        ("纳斯达克100", "纳斯达克100"),
        ("纳指", "纳斯达克100"),
        ("标普500", "标普500"),
        ("日经225", "日经225"),
        ("德国", "德国DAX"),
        ("中证红利", "中证红利"),
        ("红利低波", "红利低波"),
        ("国债", "债券指数"),
        ("黄金", "上海黄金交易所黄金现货"),
        ("证券", "证券公司指数"),
        ("银行", "银行指数"),
        ("消费", "消费主题指数"),
        ("医药", "医药卫生指数"),
        ("芯片", "芯片产业指数"),
        ("半导体", "半导体指数"),
        ("新能源", "新能源指数"),
        ("光伏", "光伏产业指数"),
        ("军工", "军工指数"),
        ("畜牧", "畜牧养殖指数"),
        ("绿色电力", "绿色电力指数"),
    ]
    compact_name = name.upper().replace(" ", "")
    for keyword, index_name in index_keywords:
        if keyword.upper() in compact_name:
            return index_name
    return None


def build_profile_description(symbol: str, name: str) -> str:
    meta = classify_etf_asset(symbol, name)
    labels = {
        "equity": "权益 ETF",
        "bond": "债券 ETF",
        "gold": "黄金 ETF",
        "commodity": "商品 ETF",
        "cash": "货币现金 ETF",
        "qdii": "跨境 QDII ETF",
    }
    return f"系统根据全市场 ETF 列表和名称规则自动补全；类型识别为{labels.get(meta['asset_class'], 'ETF')}。"


def to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    text = str(value).strip().replace(",", "")
    if not text or text in {"-", "--", "nan", "None"}:
        return None
    for suffix in ["亿元", "亿", "%", "元", "份"]:
        text = text.replace(suffix, "")
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def to_ratio_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    text = str(value).strip()
    number = to_decimal(text)
    if number is None:
        return None
    if "%" in text or abs(number) > Decimal("1"):
        return number / Decimal("100")
    return number


def to_money_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    text = str(value).strip()
    number = to_decimal(text)
    if number is None:
        return None
    if "亿" in text:
        return number * Decimal("100000000")
    return number


def to_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text or text in {"-", "--", "nan", "None"}:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.strptime(text[:10] if fmt != "%Y%m%d" else text[:8], fmt).date()
        except ValueError:
            continue
    return None


def update_asset(
    db: Session,
    symbol: str,
    *,
    enabled: bool | None = None,
    risk_level: int | None = None,
    description: str | None = None,
    profile: AssetUpdateRequest | None = None,
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
    if profile is not None:
        for field, value in profile.model_dump(exclude_unset=True).items():
            if field in {"enabled", "risk_level", "description"}:
                continue
            setattr(asset, field, value)
    db.commit()
    db.refresh(asset)
    return asset
