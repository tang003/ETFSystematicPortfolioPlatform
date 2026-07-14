from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from math import sqrt
from statistics import stdev
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.asset import AssetMaster
from app.models.market_data import MarketDataClean
from app.services.tushare_service import fetch_index_daily

INDEX_SYMBOL_PREFIX = "IDX:"

INDEX_CODE_ALIASES: dict[str, str] = {
    "上证50": "000016.SH",
    "沪深300": "000300.SH",
    "中证500": "000905.SH",
    "中证800": "000906.SH",
    "中证1000": "000852.SH",
    "中证2000": "932000.CSI",
    "中证A500": "000510.SH",
    "创业板指": "399006.SZ",
    "创业板50": "399673.SZ",
    "科创50": "000688.SH",
    "科创创业50": "931643.CSI",
    "上证红利": "000015.SH",
    "中证红利": "000922.CSI",
    "中证全指证券公司": "399975.SZ",
    "证券公司指数": "399975.SZ",
    "中证银行": "399986.SZ",
    "银行指数": "399986.SZ",
    "中证主要消费": "000932.SH",
    "消费主题指数": "000932.SH",
    "中证酒": "399987.SZ",
    "中证新能源": "399808.SZ",
    "中证新能源汽车": "399976.SZ",
    "中证光伏产业": "931151.CSI",
    "光伏产业指数": "931151.CSI",
    "国证芯片": "980017.CNI",
    "芯片产业指数": "980017.CNI",
    "中证军工": "399967.SZ",
    "军工指数": "399967.SZ",
    "中证传媒": "399971.SZ",
    "中证中药": "930641.CSI",
    "中证绿色电力": "931897.CSI",
}


def build_tracking_quality_patch(
    db: Session,
    asset: AssetMaster,
    *,
    tracking_index: str | None = None,
    lookback_days: int = 400,
) -> dict[str, Decimal]:
    index_code = resolve_index_code(tracking_index or asset.tracking_index)
    if not index_code:
        return {}
    end_date = latest_etf_date(db, asset.symbol) or date.today()
    start_date = end_date - timedelta(days=lookback_days)
    sync_index_daily(db, index_code=index_code, start_date=start_date, end_date=end_date)
    tracking_error = calculate_tracking_error(
        db,
        etf_symbol=asset.symbol,
        index_code=index_code,
        start_date=start_date,
        end_date=end_date,
    )
    return {"tracking_error": tracking_error} if tracking_error is not None else {}


def should_fetch_tracking_error(asset: AssetMaster, *, preserve_existing: bool) -> bool:
    if not preserve_existing:
        return True
    return asset.tracking_error is None


def resolve_index_code(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = normalize_index_name(value)
    if cleaned in INDEX_CODE_ALIASES:
        return INDEX_CODE_ALIASES[cleaned]
    for name, code in INDEX_CODE_ALIASES.items():
        if name in cleaned or cleaned in name:
            return code
    return None


def normalize_index_name(value: str) -> str:
    cleaned = (
        value.strip()
        .replace("收益率", "")
        .replace("全收益", "")
        .replace("净收益", "")
        .replace("价格", "")
        .replace("指数", "")
        .replace("（", "(")
        .replace("）", ")")
    )
    cleaned = cleaned.split("×", 1)[0].split("*", 1)[0]
    cleaned = cleaned.replace(" ", "").replace("-", "")
    if cleaned.upper() in {"A500", "中证A500"}:
        return "中证A500"
    return cleaned


def index_market_symbol(index_code: str) -> str:
    return f"{INDEX_SYMBOL_PREFIX}{index_code}"


def sync_index_daily(db: Session, *, index_code: str, start_date: date, end_date: date) -> int:
    frame = fetch_index_daily(index_code, start_date, end_date)
    rows = [build_index_bar_payload(index_code, row) for row in frame.to_dict(orient="records")]
    rows = [row for row in rows if row is not None]
    if not rows:
        return 0
    statement = insert(MarketDataClean).values(rows)
    update_columns = {column: getattr(statement.excluded, column) for column in rows[0] if column not in {"symbol", "trade_date"}}
    db.execute(statement.on_conflict_do_update(index_elements=["symbol", "trade_date"], set_=update_columns))
    db.commit()
    return len(rows)


def build_index_bar_payload(index_code: str, row: dict[str, Any]) -> dict[str, Any] | None:
    trade_date = parse_tushare_date(row.get("trade_date"))
    close = to_decimal(row.get("close"))
    if trade_date is None or close is None:
        return None
    return {
        "symbol": index_market_symbol(index_code),
        "trade_date": trade_date,
        "open": to_decimal(row.get("open")),
        "high": to_decimal(row.get("high")),
        "low": to_decimal(row.get("low")),
        "close": close,
        "volume": to_decimal(row.get("vol")),
        "amount": to_decimal(row.get("amount")),
        "is_adjusted": False,
        "data_status": "index",
    }


def calculate_tracking_error(
    db: Session,
    *,
    etf_symbol: str,
    index_code: str,
    start_date: date,
    end_date: date,
) -> Decimal | None:
    etf_returns = load_returns_by_date(db, symbol=etf_symbol, start_date=start_date, end_date=end_date)
    index_returns = load_returns_by_date(db, symbol=index_market_symbol(index_code), start_date=start_date, end_date=end_date)
    excess_returns = [etf_returns[item] - index_returns[item] for item in sorted(etf_returns.keys() & index_returns.keys())]
    if len(excess_returns) < 60:
        return None
    return Decimal(str(stdev(excess_returns) * sqrt(252))).quantize(Decimal("0.000001"))


def load_returns_by_date(db: Session, *, symbol: str, start_date: date, end_date: date) -> dict[date, float]:
    rows = list(
        db.scalars(
            select(MarketDataClean)
            .where(
                MarketDataClean.symbol == symbol,
                MarketDataClean.trade_date >= start_date,
                MarketDataClean.trade_date <= end_date,
                MarketDataClean.close.is_not(None),
            )
            .order_by(MarketDataClean.trade_date)
        ).all()
    )
    result: dict[date, float] = {}
    previous_close: Decimal | None = None
    for row in rows:
        close = Decimal(row.close)
        if previous_close is not None and previous_close > 0:
            result[row.trade_date] = float(close / previous_close - Decimal("1"))
        previous_close = close
    return result


def latest_etf_date(db: Session, symbol: str) -> date | None:
    return db.scalar(
        select(MarketDataClean.trade_date)
        .where(MarketDataClean.symbol == symbol, MarketDataClean.close.is_not(None))
        .order_by(MarketDataClean.trade_date.desc())
        .limit(1)
    )


def parse_tushare_date(value: Any) -> date | None:
    if value is None:
        return None
    text = str(value).strip()
    if len(text) != 8 or not text.isdigit():
        return None
    return date(int(text[:4]), int(text[4:6]), int(text[6:8]))


def to_decimal(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
