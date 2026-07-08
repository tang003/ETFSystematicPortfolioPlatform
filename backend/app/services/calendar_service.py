from datetime import date, timedelta
from typing import Any

import akshare as ak
import pandas as pd
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.market_data import TradingCalendar


def sync_trading_calendar(db: Session, start_date: date, end_date: date, market: str = "CN") -> dict[str, Any]:
    if start_date > end_date:
        raise ValueError("start_date must not be later than end_date")
    rows, source = fetch_calendar_rows(start_date, end_date)
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
    return {"start_date": start_date, "end_date": end_date, "market": market, "source": source, "open_days": len(rows)}


def fetch_calendar_rows(start_date: date, end_date: date) -> tuple[list[date], str]:
    try:
        frame = ak.tool_trade_date_hist_sina()
        dates = parse_akshare_calendar(frame, start_date, end_date)
        if dates:
            return dates, "akshare_sina"
    except Exception:  # noqa: BLE001 - weekday fallback keeps local development usable.
        pass
    return weekday_calendar(start_date, end_date), "weekday_fallback"


def parse_akshare_calendar(frame: pd.DataFrame, start_date: date, end_date: date) -> list[date]:
    if frame is None or frame.empty:
        return []
    first_column = frame.columns[0]
    dates = [pd.to_datetime(value).date() for value in frame[first_column].dropna().tolist()]
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
