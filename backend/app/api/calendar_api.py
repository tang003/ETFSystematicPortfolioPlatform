from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.calendar_schema import CalendarSyncRequest, CalendarSyncResponse, TradingCalendarRead
from app.services.calendar_service import list_trading_calendar, sync_trading_calendar

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.post("/sync", response_model=CalendarSyncResponse)
def sync_calendar(request: CalendarSyncRequest, db: Session = Depends(get_db)) -> CalendarSyncResponse:
    return sync_trading_calendar(db, start_date=request.start_date, end_date=request.end_date, market=request.market)


@router.get("/trading-days", response_model=list[TradingCalendarRead])
def get_trading_days(
    start_date: date = Query(),
    end_date: date = Query(),
    market: str = Query(default="CN"),
    db: Session = Depends(get_db),
) -> list[TradingCalendarRead]:
    return list_trading_calendar(db, start_date=start_date, end_date=end_date, market=market)

