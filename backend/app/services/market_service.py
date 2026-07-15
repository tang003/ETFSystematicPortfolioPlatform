import time
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

import akshare as ak
import pandas as pd
import requests
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.asset import AssetMaster
from app.models.market_data import MarketDataClean, MarketDataRaw, TradingCalendar
from app.models.portfolio import InvestmentPlanSuggestion, PortfolioPosition, TargetPortfolio
from app.services.data_quality_service import add_quality_log, check_clean_bars
from app.services.tushare_service import fetch_fund_daily, to_tushare_code

EASTMONEY_KLINE_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
EASTMONEY_QUOTE_URL = "https://push2.eastmoney.com/api/qt/stock/get"


def default_sync_dates(start_date: date | None, end_date: date | None) -> tuple[date, date]:
    resolved_end = end_date or date.today()
    resolved_start = start_date or (resolved_end - timedelta(days=365))
    if resolved_start > resolved_end:
        raise ValueError("start_date must not be later than end_date")
    return resolved_start, resolved_end


SYNC_SCOPES = {"enabled", "core", "positions", "target", "plans", "all"}


def resolve_symbols(db: Session, symbols: list[str] | None, sync_scope: str = "enabled") -> list[str]:
    if symbols:
        return dedupe_symbols(symbols)
    return resolve_scoped_symbols(db, sync_scope)


def dedupe_symbols(symbols: list[str]) -> list[str]:
    seen: set[str] = set()
    resolved: list[str] = []
    for symbol in symbols:
        cleaned = symbol.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        resolved.append(cleaned)
    return resolved


def resolve_scoped_symbols(db: Session, sync_scope: str = "enabled") -> list[str]:
    normalized_scope = (sync_scope or "enabled").strip().lower()
    if normalized_scope not in SYNC_SCOPES:
        raise ValueError("sync_scope must be one of: enabled, core, positions, target, plans, all")
    if normalized_scope == "positions":
        return latest_position_symbols(db)
    if normalized_scope == "target":
        return latest_target_symbols(db)
    if normalized_scope == "plans":
        return plan_suggestion_symbols(db)
    if normalized_scope == "all":
        return all_asset_symbols(db)
    if normalized_scope == "core":
        return merge_symbol_groups(
            latest_position_symbols(db),
            latest_target_symbols(db),
            plan_suggestion_symbols(db),
            enabled_asset_symbols(db),
        )
    return enabled_asset_symbols(db)


def enabled_asset_symbols(db: Session) -> list[str]:
    return list(
        db.scalars(
            select(AssetMaster.symbol).where(AssetMaster.enabled.is_(True)).order_by(AssetMaster.symbol)
        ).all()
    )


def all_asset_symbols(db: Session) -> list[str]:
    return list(db.scalars(select(AssetMaster.symbol).order_by(AssetMaster.symbol)).all())


def latest_position_symbols(db: Session) -> list[str]:
    latest_date = db.scalar(select(func.max(PortfolioPosition.position_date)))
    if latest_date is None:
        return []
    return list(
        db.scalars(
            select(PortfolioPosition.symbol)
            .where(PortfolioPosition.position_date == latest_date)
            .order_by(PortfolioPosition.weight.desc().nullslast(), PortfolioPosition.symbol)
        ).all()
    )


def latest_target_symbols(db: Session) -> list[str]:
    latest_date = db.scalar(select(func.max(TargetPortfolio.portfolio_date)))
    if latest_date is None:
        return []
    return list(
        db.scalars(
            select(TargetPortfolio.symbol)
            .where(TargetPortfolio.portfolio_date == latest_date)
            .order_by(TargetPortfolio.final_target_weight.desc().nullslast(), TargetPortfolio.symbol)
        ).all()
    )


def plan_suggestion_symbols(db: Session) -> list[str]:
    return list(
        db.scalars(
            select(InvestmentPlanSuggestion.symbol)
            .distinct()
            .order_by(InvestmentPlanSuggestion.symbol)
        ).all()
    )


def merge_symbol_groups(*groups: list[str]) -> list[str]:
    merged: list[str] = []
    for group in groups:
        merged.extend(group)
    return dedupe_symbols(merged)


def resolve_symbol_meta(db: Session, symbols: list[str]) -> dict[str, AssetMaster]:
    if not symbols:
        return {}
    rows = db.scalars(select(AssetMaster).where(AssetMaster.symbol.in_(symbols))).all()
    return {row.symbol: row for row in rows}


def limit_symbols(symbols: list[str], max_symbols: int | None) -> tuple[list[str], int]:
    if max_symbols is None:
        return symbols, 0
    if max_symbols < 1:
        raise ValueError("max_symbols must be greater than 0")
    return symbols[:max_symbols], max(0, len(symbols) - max_symbols)


def fetch_etf_daily_bars(
    symbol: str,
    start_date: date,
    end_date: date,
    source: str = "tushare",
    exchange: str | None = None,
) -> tuple[pd.DataFrame, str]:
    if source in {"akshare", "eastmoney"}:
        raise ValueError("ETF 行情同步已切换为 Tushare-only，AKShare/东方财富暂时停用")
    if source == "tushare":
        return fetch_tushare_daily_bars(symbol, start_date, end_date, exchange), "tushare"
    raise ValueError("source must be tushare")


def fetch_akshare_daily_bars(symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
    return ak.fund_etf_hist_em(
        symbol=symbol,
        period="daily",
        start_date=start_date.strftime("%Y%m%d"),
        end_date=end_date.strftime("%Y%m%d"),
        adjust="",
    )


def fetch_eastmoney_daily_bars(symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
    response = requests.get(
        EASTMONEY_KLINE_URL,
        params={
            "secid": eastmoney_secid(symbol),
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57",
            "klt": "101",
            "fqt": "0",
            "beg": start_date.strftime("%Y%m%d"),
            "end": end_date.strftime("%Y%m%d"),
        },
        timeout=15,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    response.raise_for_status()
    payload = response.json()
    klines = (payload.get("data") or {}).get("klines") or []
    if not klines:
        raise ValueError(f"{symbol} eastmoney returned no kline rows")

    rows: list[dict[str, Any]] = []
    for line in klines:
        values = line.split(",")
        if len(values) < 7:
            continue
        rows.append(
            {
                "date": values[0],
                "open": values[1],
                "close": values[2],
                "high": values[3],
                "low": values[4],
                "volume": values[5],
                "amount": values[6],
            }
        )
    return pd.DataFrame(rows)


def fetch_tushare_daily_bars(symbol: str, start_date: date, end_date: date, exchange: str | None = None) -> pd.DataFrame:
    ts_code = to_tushare_code(symbol, exchange)
    frame = fetch_fund_daily(ts_code, start_date, end_date)
    if frame is None or frame.empty:
        raise ValueError(f"{symbol} tushare returned no fund_daily rows")
    return frame


def eastmoney_secid(symbol: str) -> str:
    if symbol.startswith(("5", "6", "9")):
        return f"1.{symbol}"
    return f"0.{symbol}"


def fetch_eastmoney_spot_quote(symbol: str) -> dict[str, Any]:
    response = requests.get(
        EASTMONEY_QUOTE_URL,
        params={
            "secid": eastmoney_secid(symbol),
            "fields": "f43,f44,f45,f46,f47,f48,f57,f58",
        },
        timeout=15,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    response.raise_for_status()
    data = (response.json().get("data") or {})
    price = eastmoney_scaled_price(data.get("f43"))
    if price is None or price <= 0:
        raise ValueError(f"{symbol} eastmoney spot returned no valid price")
    return {
        "symbol": symbol,
        "name": data.get("f58"),
        "trade_date": date.today(),
        "open": eastmoney_scaled_price(data.get("f46")) or price,
        "high": eastmoney_scaled_price(data.get("f44")) or price,
        "low": eastmoney_scaled_price(data.get("f45")) or price,
        "close": price,
        "volume": _to_decimal(data.get("f47")),
        "amount": _to_decimal(data.get("f48")),
        "raw_payload": data,
    }


def sync_eastmoney_spot_quote(db: Session, symbol: str) -> dict[str, Any]:
    quote = fetch_eastmoney_spot_quote(symbol)
    row = {
        "symbol": symbol,
        "trade_date": quote["trade_date"],
        "open": quote["open"],
        "high": quote["high"],
        "low": quote["low"],
        "close": quote["close"],
        "volume": quote["volume"],
        "amount": quote["amount"],
        "raw_payload": quote["raw_payload"],
    }
    upsert_raw_bars(db, [row], "eastmoney_spot")
    upsert_clean_bars(db, [row])
    db.commit()
    return quote


def eastmoney_scaled_price(value: Any) -> Decimal | None:
    price = _to_decimal(value)
    if price is None:
        return None
    if price > 100:
        price = price / Decimal("1000")
    return price.quantize(Decimal("0.000001"))


def sync_market_data(
    db: Session,
    *,
    symbols: list[str] | None,
    start_date: date | None,
    end_date: date | None,
    source: str = "tushare",
    sync_scope: str = "enabled",
    incremental: bool = False,
    clean_after_sync: bool = True,
    max_symbols: int | None = None,
    request_interval_seconds: float = 0,
) -> dict[str, Any]:
    resolved_start, resolved_end = default_sync_dates(start_date, end_date)
    all_symbols = resolve_symbols(db, symbols, sync_scope=sync_scope)
    resolved_symbols, skipped_symbols = limit_symbols(all_symbols, max_symbols)
    symbol_meta = resolve_symbol_meta(db, resolved_symbols)
    results: list[dict[str, Any]] = []
    up_to_date_symbols = 0
    effective_interval = request_interval_seconds
    if source == "tushare" and effective_interval == 0:
        effective_interval = get_settings().tushare_request_interval_seconds

    for index, symbol in enumerate(resolved_symbols):
        try:
            sync_start, sync_end, up_to_date = resolve_market_sync_window(
                db,
                symbol=symbol,
                start_date=resolved_start,
                end_date=resolved_end,
                incremental=incremental,
            )
            if up_to_date:
                up_to_date_symbols += 1
                results.append(
                    {
                        "symbol": symbol,
                        "raw_rows": 0,
                        "clean_rows": 0,
                        "quality_logs": 0,
                        "status": "success",
                        "message": "up_to_date",
                    }
                )
                continue
            raw_frame, actual_source = fetch_etf_daily_bars(
                symbol,
                sync_start,
                sync_end,
                source,
                symbol_meta.get(symbol).exchange if symbol in symbol_meta else None,
            )
            normalized_rows = normalize_market_bars(symbol, raw_frame)
            raw_rows = upsert_raw_bars(db, normalized_rows, actual_source)
            clean_rows = upsert_clean_bars(db, normalized_rows) if clean_after_sync else 0
            quality_logs = check_clean_bars(db, symbol, sync_start, sync_end) if clean_after_sync else 0
            db.commit()
            results.append(
                {
                    "symbol": symbol,
                    "raw_rows": raw_rows,
                    "clean_rows": clean_rows,
                    "quality_logs": quality_logs,
                    "status": "success",
                    "message": f"source={actual_source}; synced={sync_start.isoformat()}~{sync_end.isoformat()}",
                }
            )
        except Exception as exc:  # noqa: BLE001 - API needs per-symbol failure details.
            db.rollback()
            if is_incremental_tushare_empty_gap(
                db,
                symbol=symbol,
                source=source,
                incremental=incremental,
                error=exc,
            ):
                up_to_date_symbols += 1
                results.append(
                    {
                        "symbol": symbol,
                        "raw_rows": 0,
                        "clean_rows": 0,
                        "quality_logs": 0,
                        "status": "success",
                        "message": "up_to_date_no_new_tushare_daily",
                    }
                )
                continue
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
        if effective_interval > 0 and index < len(resolved_symbols) - 1:
            time.sleep(effective_interval)

    success_count = sum(1 for item in results if item["status"] == "success")
    failed_count = sum(1 for item in results if item["status"] == "failed")
    return {
        "start_date": resolved_start,
        "end_date": resolved_end,
        "source": source,
        "sync_scope": "custom" if symbols else sync_scope,
        "incremental": incremental,
        "request_interval_seconds": effective_interval,
        "total_symbols": len(resolved_symbols),
        "requested_symbols": len(all_symbols),
        "skipped_symbols": skipped_symbols,
        "up_to_date_symbols": up_to_date_symbols,
        "success_count": success_count,
        "failed_count": failed_count,
        "total_raw_rows": sum(item["raw_rows"] for item in results),
        "total_clean_rows": sum(item["clean_rows"] for item in results),
        "total_quality_logs": sum(item["quality_logs"] for item in results),
        "results": results,
    }


def build_market_sync_plan(
    db: Session,
    sync_scope: str = "core",
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    min_bars: int = 120,
) -> dict[str, Any]:
    symbols = resolve_scoped_symbols(db, sync_scope)
    symbol_meta = resolve_symbol_meta(db, symbols)
    latest_dates = latest_clean_trade_dates(db, symbols)
    coverage = clean_bar_coverage(db, symbols, start_date=start_date, end_date=end_date)
    categories = symbol_categories(db, symbols)
    expected_bars = expected_market_bars(db, start_date=start_date, end_date=end_date)
    rows = [
        {
            "symbol": symbol,
            "name": symbol_meta[symbol].name if symbol in symbol_meta else None,
            "categories": categories.get(symbol, []),
            "latest_trade_date": latest_dates.get(symbol),
            "has_clean_price": latest_dates.get(symbol) is not None,
            "range_bar_count": coverage.get(symbol, {}).get("bar_count", 0),
            "range_latest_trade_date": coverage.get(symbol, {}).get("latest_trade_date"),
            "expected_bar_count": expected_bars,
            "missing_bar_count": missing_bar_count(expected_bars, coverage.get(symbol, {}).get("bar_count", 0)),
            "coverage_ratio": coverage_ratio(coverage.get(symbol, {}).get("bar_count", 0), expected_bars),
            "sample_status": sample_status(coverage.get(symbol, {}).get("bar_count", 0), min_bars),
            "sample_message": sample_message(coverage.get(symbol, {}).get("bar_count", 0), min_bars, expected_bars),
        }
        for symbol in symbols
    ]
    recommended_sync_symbols = [
        row["symbol"]
        for row in rows
        if row["sample_status"] in {"empty", "insufficient"}
    ]
    return {
        "sync_scope": sync_scope,
        "total_symbols": len(rows),
        "missing_price_count": sum(1 for row in rows if not row["has_clean_price"]),
        "ready_count": sum(1 for row in rows if row["sample_status"] == "ready"),
        "insufficient_count": sum(1 for row in rows if row["sample_status"] == "insufficient"),
        "empty_count": sum(1 for row in rows if row["sample_status"] == "empty"),
        "recommended_sync_symbols": recommended_sync_symbols,
        "expected_bar_count": expected_bars,
        "min_bars": min_bars,
        "symbols": rows,
    }


def latest_clean_trade_dates(db: Session, symbols: list[str]) -> dict[str, date]:
    if not symbols:
        return {}
    rows = db.execute(
        select(MarketDataClean.symbol, func.max(MarketDataClean.trade_date))
        .where(MarketDataClean.symbol.in_(symbols))
        .group_by(MarketDataClean.symbol)
    ).all()
    return {symbol: trade_date for symbol, trade_date in rows if trade_date is not None}


def clean_bar_coverage(
    db: Session,
    symbols: list[str],
    *,
    start_date: date | None,
    end_date: date | None,
) -> dict[str, dict[str, Any]]:
    if not symbols:
        return {}
    query = (
        select(MarketDataClean.symbol, func.count(MarketDataClean.trade_date), func.max(MarketDataClean.trade_date))
        .where(MarketDataClean.symbol.in_(symbols))
        .group_by(MarketDataClean.symbol)
    )
    if start_date:
        query = query.where(MarketDataClean.trade_date >= start_date)
    if end_date:
        query = query.where(MarketDataClean.trade_date <= end_date)
    rows = db.execute(query).all()
    return {
        symbol: {"bar_count": int(bar_count or 0), "latest_trade_date": latest_trade_date}
        for symbol, bar_count, latest_trade_date in rows
    }


def expected_market_bars(db: Session, *, start_date: date | None, end_date: date | None) -> int | None:
    if start_date is None or end_date is None:
        return None
    return int(
        db.scalar(
            select(func.count())
            .select_from(TradingCalendar)
            .where(TradingCalendar.trade_date >= start_date)
            .where(TradingCalendar.trade_date <= end_date)
            .where(TradingCalendar.is_open.is_(True))
        )
        or 0
    )


def missing_bar_count(expected_bars: int | None, bar_count: int) -> int | None:
    if expected_bars is None:
        return None
    return max(0, expected_bars - bar_count)


def coverage_ratio(bar_count: int, expected_bars: int | None) -> float | None:
    if not expected_bars:
        return None
    return round(min(1.0, bar_count / expected_bars), 4)


def sample_status(bar_count: int, min_bars: int) -> str:
    if bar_count <= 0:
        return "empty"
    if bar_count < min_bars:
        return "insufficient"
    return "ready"


def sample_message(bar_count: int, min_bars: int, expected_bars: int | None) -> str:
    if bar_count <= 0:
        return "没有本区间清洗行情，需先同步行情"
    if bar_count < min_bars:
        return f"样本 {bar_count} 根，低于策略建议门槛 {min_bars} 根"
    if expected_bars is not None and bar_count < expected_bars:
        return f"样本满足策略门槛，但区间内仍缺 {expected_bars - bar_count} 个交易日"
    return "样本满足策略和回测基础门槛"


def symbol_categories(db: Session, symbols: list[str]) -> dict[str, list[str]]:
    category_sets = {symbol: set() for symbol in symbols}
    for symbol in latest_position_symbols(db):
        if symbol in category_sets:
            category_sets[symbol].add("position")
    for symbol in latest_target_symbols(db):
        if symbol in category_sets:
            category_sets[symbol].add("target")
    for symbol in plan_suggestion_symbols(db):
        if symbol in category_sets:
            category_sets[symbol].add("plan")
    enabled = set(enabled_asset_symbols(db))
    for symbol in symbols:
        if symbol in enabled:
            category_sets[symbol].add("enabled")
    return {symbol: sorted(values) for symbol, values in category_sets.items()}


def latest_market_trade_date(db: Session, symbol: str) -> date | None:
    clean_date = db.scalar(
        select(MarketDataClean.trade_date)
        .where(MarketDataClean.symbol == symbol)
        .order_by(MarketDataClean.trade_date.desc())
        .limit(1)
    )
    if clean_date is not None:
        return clean_date
    return db.scalar(
        select(MarketDataRaw.trade_date)
        .where(MarketDataRaw.symbol == symbol)
        .order_by(MarketDataRaw.trade_date.desc())
        .limit(1)
    )


def resolve_market_sync_window(
    db: Session,
    *,
    symbol: str,
    start_date: date,
    end_date: date,
    incremental: bool = False,
) -> tuple[date, date, bool]:
    if not incremental:
        return start_date, end_date, False
    latest_trade_date = latest_market_trade_date(db, symbol)
    if latest_trade_date is None:
        return start_date, end_date, False
    effective_start = max(start_date, latest_trade_date + timedelta(days=1))
    if effective_start > end_date:
        return start_date, end_date, True
    return effective_start, end_date, False


def is_incremental_tushare_empty_gap(
    db: Session,
    *,
    symbol: str,
    source: str,
    incremental: bool,
    error: Exception,
) -> bool:
    if not incremental or source != "tushare":
        return False
    if "tushare returned no fund_daily rows" not in str(error):
        return False
    return latest_market_trade_date(db, symbol) is not None


def normalize_market_bars(symbol: str, frame: pd.DataFrame) -> list[dict[str, Any]]:
    if frame is None or frame.empty:
        raise ValueError(f"{symbol} returned no market data")

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
                "volume": _to_decimal(_first_value(raw_row, "成交量", "volume", "vol")),
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
        raise ValueError("market data is missing trade_date")
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
