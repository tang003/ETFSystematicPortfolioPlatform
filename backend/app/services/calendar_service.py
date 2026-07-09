from datetime import date, timedelta
from typing import Any

import akshare as ak
import pandas as pd
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.market_data import TradingCalendar
from app.services.tushare_service import fetch_trade_calendar


def sync_trading_calendar(
    db: Session,
    start_date: date,
    end_date: date,
    market: str = "CN",
    source: str = "akshare",
    incremental: bool = False,
) -> dict[str, Any]:
    if start_date > end_date:
        raise ValueError("start_date must not be later than end_date")
    effective_start, effective_end, up_to_date = resolve_calendar_sync_window(
        db,
        start_date=start_date,
        end_date=end_date,
        market=market,
        incremental=incremental,
    )
    if up_to_date:
        return {
            "start_date": start_date,
            "end_date": end_date,
            "market": market,
            "source": source,
            "incremental": incremental,
            "open_days": 0,
            "stored_days": 0,
        }

    rows, actual_source = fetch_calendar_rows(effective_start, effective_end, source=source)
    payload = [{"trade_date": item, "market": market, "is_open": True} for item in rows]
    if payload:
        statement = insert(TradingCalendar).values(payload)
        db.execute(
            statement.on_conflict_do_update(
                index_elements=["trade_date"],
                set_={"market": statement.excluded.market, "is_open": statement.excluded.is_open},
            )
        )
    db.commit()
    return {
        "start_date": effective_start,
        "end_date": effective_end,
        "market": market,
        "source": actual_source,
        "incremental": incremental,
        "open_days": len(rows),
        "stored_days": len(rows),
    }


def latest_calendar_trade_date(db: Session, market: str = "CN") -> date | None:
    return db.scalar(
        select(TradingCalendar.trade_date)
        .where(TradingCalendar.market == market)
        .order_by(TradingCalendar.trade_date.desc())
        .limit(1)
    )


def resolve_calendar_sync_window(
    db: Session,
    *,
    start_date: date,
    end_date: date,
    market: str = "CN",
    incremental: bool = False,
) -> tuple[date, date, bool]:
    if not incremental:
        return start_date, end_date, False
    latest_trade_date = latest_calendar_trade_date(db, market=market)
    if latest_trade_date is None:
        return start_date, end_date, False
    effective_start = max(start_date, latest_trade_date + timedelta(days=1))
    if effective_start > end_date:
        return start_date, end_date, True
    return effective_start, end_date, False


def fetch_calendar_rows(start_date: date, end_date: date, source: str = "akshare") -> tuple[list[date], str]:
    if source == "tushare":
        frame = fetch_trade_calendar(start_date, end_date)
        dates = parse_tushare_calendar(frame, start_date, end_date)
        return dates, "tushare_trade_cal"

    if source == "akshare":
        try:
            frame = ak.tool_trade_date_hist_sina()
            dates = parse_akshare_calendar(frame, start_date, end_date)
            if dates:
                return dates, "akshare_sina"
        except Exception:  # noqa: BLE001 - weekday fallback keeps local development usable.
            pass
        return weekday_calendar(start_date, end_date), "weekday_fallback"

    if source == "weekday":
        return weekday_calendar(start_date, end_date), "weekday_fallback"

    raise ValueError("source must be one of: akshare, tushare, weekday")


def parse_akshare_calendar(frame: pd.DataFrame, start_date: date, end_date: date) -> list[date]:
    if frame is None or frame.empty:
        return []
    first_column = frame.columns[0]
    dates = [pd.to_datetime(value).date() for value in frame[first_column].dropna().tolist()]
    return sorted(item for item in dates if start_date <= item <= end_date)


def parse_tushare_calendar(frame: pd.DataFrame, start_date: date, end_date: date) -> list[date]:
    if frame is None or frame.empty:
        return []
    open_frame = frame[frame["is_open"].astype(str) == "1"]
    dates = [pd.to_datetime(value).date() for value in open_frame["cal_date"].dropna().tolist()]
    return sorted(item for item in dates if start_date <= item <= end_date)


def weekday_calendar(start_date: date, end_date: date) -> list[date]:
    days: list[date] = []
    current = start_date
    while current <= end_date:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days


def list_trading_calendar(db: Session, start_date: date, end_date: date, market: str = "CN") -> list[TradingCalendar]:
    return list(
        db.scalars(
            select(TradingCalendar)
            .where(TradingCalendar.market == market)
            .where(TradingCalendar.trade_date >= start_date)
            .where(TradingCalendar.trade_date <= end_date)
            .order_by(TradingCalendar.trade_date)
        ).all()
    )
