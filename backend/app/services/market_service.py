from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

import akshare as ak
import pandas as pd
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.asset import AssetMaster
from app.models.market_data import MarketDataClean, MarketDataRaw
from app.services.data_quality_service import add_quality_log, check_clean_bars


def default_sync_dates(start_date: date | None, end_date: date | None) -> tuple[date, date]:
    resolved_end = end_date or date.today()
    resolved_start = start_date or (resolved_end - timedelta(days=365))
    if resolved_start > resolved_end:
        raise ValueError("start_date 不能晚于 end_date")
    return resolved_start, resolved_end


def resolve_symbols(db: Session, symbols: list[str] | None) -> list[str]:
    if symbols:
        return [symbol.strip() for symbol in symbols if symbol.strip()]
    return list(
        db.scalars(
            select(AssetMaster.symbol).where(AssetMaster.enabled.is_(True)).order_by(AssetMaster.symbol)
        ).all()
    )


def fetch_etf_daily_bars(symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
    return ak.fund_etf_hist_em(
        symbol=symbol,
        period="daily",
        start_date=start_date.strftime("%Y%m%d"),
        end_date=end_date.strftime("%Y%m%d"),
        adjust="",
    )


def sync_market_data(
    db: Session,
    *,
    symbols: list[str] | None,
    start_date: date | None,
    end_date: date | None,
    source: str = "akshare",
    clean_after_sync: bool = True,
) -> dict[str, Any]:
    resolved_start, resolved_end = default_sync_dates(start_date, end_date)
    resolved_symbols = resolve_symbols(db, symbols)
    results: list[dict[str, Any]] = []

    for symbol in resolved_symbols:
        try:
            raw_frame = fetch_etf_daily_bars(symbol, resolved_start, resolved_end)
            normalized_rows = normalize_akshare_bars(symbol, raw_frame)
            raw_rows = upsert_raw_bars(db, normalized_rows, source)
            clean_rows = upsert_clean_bars(db, normalized_rows) if clean_after_sync else 0
            quality_logs = check_clean_bars(db, symbol, resolved_start, resolved_end) if clean_after_sync else 0
            db.commit()
            results.append(
                {
                    "symbol": symbol,
                    "raw_rows": raw_rows,
                    "clean_rows": clean_rows,
                    "quality_logs": quality_logs,
                    "status": "success",
                    "message": None,
                }
            )
        except Exception as exc:  # noqa: BLE001 - API needs per-symbol failure details.
            db.rollback()
            add_quality_log(
                db,
                symbol=symbol,
                trade_date=None,
                check_type="market_sync_failed",
                status="failed",
                message=str(exc),
                severity="error",
            )
            db.commit()
            results.append(
                {
                    "symbol": symbol,
                    "raw_rows": 0,
                    "clean_rows": 0,
                    "quality_logs": 1,
                    "status": "failed",
                    "message": str(exc),
                }
            )

    return {
        "start_date": resolved_start,
        "end_date": resolved_end,
        "source": source,
        "total_symbols": len(resolved_symbols),
        "total_raw_rows": sum(item["raw_rows"] for item in results),
        "total_clean_rows": sum(item["clean_rows"] for item in results),
        "total_quality_logs": sum(item["quality_logs"] for item in results),
        "results": results,
    }


def normalize_akshare_bars(symbol: str, frame: pd.DataFrame) -> list[dict[str, Any]]:
    if frame is None or frame.empty:
        raise ValueError(f"{symbol} 没有获取到行情数据")

    rows: list[dict[str, Any]] = []
    for raw_row in frame.to_dict("records"):
        trade_date = _to_date(_first_value(raw_row, "日期", "date", "trade_date"))
        rows.append(
            {
                "symbol": symbol,
                "trade_date": trade_date,
                "open": _to_decimal(_first_value(raw_row, "开盘", "open")),
                "high": _to_decimal(_first_value(raw_row, "最高", "high")),
                "low": _to_decimal(_first_value(raw_row, "最低", "low")),
                "close": _to_decimal(_first_value(raw_row, "收盘", "close")),
                "volume": _to_decimal(_first_value(raw_row, "成交量", "volume")),
                "amount": _to_decimal(_first_value(raw_row, "成交额", "amount")),
                "raw_payload": _json_safe(raw_row),
            }
        )
    return rows


def upsert_raw_bars(db: Session, rows: list[dict[str, Any]], source: str) -> int:
    if not rows:
        return 0
    payload = [{**row, "source": source} for row in rows]
    statement = insert(MarketDataRaw).values(payload)
    update_columns = {
        "open": statement.excluded.open,
        "high": statement.excluded.high,
        "low": statement.excluded.low,
        "close": statement.excluded.close,
        "volume": statement.excluded.volume,
        "amount": statement.excluded.amount,
        "raw_payload": statement.excluded.raw_payload,
    }
    db.execute(statement.on_conflict_do_update(index_elements=["symbol", "trade_date", "source"], set_=update_columns))
    return len(rows)


def upsert_clean_bars(db: Session, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    clean_rows = [
        {
            "symbol": row["symbol"],
            "trade_date": row["trade_date"],
            "open": row["open"],
            "high": row["high"],
            "low": row["low"],
            "close": row["close"],
            "volume": row["volume"],
            "amount": row["amount"],
            "is_adjusted": False,
            "data_status": "normal",
        }
        for row in rows
    ]
    statement = insert(MarketDataClean).values(clean_rows)
    update_columns = {
        "open": statement.excluded.open,
        "high": statement.excluded.high,
        "low": statement.excluded.low,
        "close": statement.excluded.close,
        "volume": statement.excluded.volume,
        "amount": statement.excluded.amount,
        "is_adjusted": statement.excluded.is_adjusted,
        "data_status": statement.excluded.data_status,
    }
    db.execute(statement.on_conflict_do_update(index_elements=["symbol", "trade_date"], set_=update_columns))
    return len(rows)


def list_clean_bars(db: Session, symbol: str, start_date: date | None, end_date: date | None) -> list[MarketDataClean]:
    query = select(MarketDataClean).where(MarketDataClean.symbol == symbol).order_by(MarketDataClean.trade_date)
    if start_date:
        query = query.where(MarketDataClean.trade_date >= start_date)
    if end_date:
        query = query.where(MarketDataClean.trade_date <= end_date)
    return list(db.scalars(query).all())


def list_raw_bars(db: Session, symbol: str | None, limit: int = 100) -> list[MarketDataRaw]:
    query = select(MarketDataRaw).order_by(MarketDataRaw.trade_date.desc()).limit(limit)
    if symbol:
        query = query.where(MarketDataRaw.symbol == symbol)
    return list(db.scalars(query).all())


def _first_value(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in row:
            return row[key]
    return None


def _to_date(value: Any) -> date:
    if value is None or pd.isna(value):
        raise ValueError("行情数据缺少交易日期字段")
    if isinstance(value, date):
        return value
    return pd.to_datetime(value).date()


def _to_decimal(value: Any) -> Decimal | None:
    if value is None or pd.isna(value):
        return None
    try:
        return Decimal(str(value).replace(",", ""))
    except (InvalidOperation, ValueError):
        return None


def _json_safe(row: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in row.items():
        if pd.isna(value):
            safe[key] = None
        elif isinstance(value, (date, pd.Timestamp)):
            safe[key] = str(value)
        elif isinstance(value, Decimal):
            safe[key] = str(value)
        else:
            safe[key] = value
    return safe
