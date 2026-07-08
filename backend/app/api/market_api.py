from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.market_schema import MarketBarRead, MarketSyncRequest, MarketSyncResponse
from app.services.market_service import list_clean_bars, list_raw_bars, sync_market_data

router = APIRouter(prefix="/market", tags=["market"])


@router.post("/sync", response_model=MarketSyncResponse)
def sync_market(request: MarketSyncRequest, db: Session = Depends(get_db)) -> MarketSyncResponse:
    return sync_market_data(
        db,
        symbols=request.symbols,
        start_date=request.start_date,
        end_date=request.end_date,
        source=request.source,
        clean_after_sync=request.clean_after_sync,
    )


@router.get("/raw", response_model=list[MarketBarRead])
def get_raw_market_bars(
    symbol: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> list[MarketBarRead]:
    rows = list_raw_bars(db, symbol=symbol, limit=limit)
    return [
        MarketBarRead(
            symbol=row.symbol,
            trade_date=row.trade_date,
            open=row.open,
            high=row.high,
            low=row.low,
            close=row.close,
            volume=row.volume,
            amount=row.amount,
            source=row.source,
            data_status=None,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.get("/clean", response_model=list[MarketBarRead])
def get_clean_market_bars(
    symbol: str,
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[MarketBarRead]:
    rows = list_clean_bars(db, symbol=symbol, start_date=start_date, end_date=end_date)
    return [
        MarketBarRead(
            symbol=row.symbol,
            trade_date=row.trade_date,
            open=row.open,
            high=row.high,
            low=row.low,
            close=row.close,
            volume=row.volume,
            amount=row.amount,
            source=None,
            data_status=row.data_status,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.get("/bars/{symbol}", response_model=list[MarketBarRead])
def get_symbol_bars(
    symbol: str,
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[MarketBarRead]:
    rows = list_clean_bars(db, symbol=symbol, start_date=start_date, end_date=end_date)
    return [
        MarketBarRead(
            symbol=row.symbol,
            trade_date=row.trade_date,
            open=row.open,
            high=row.high,
            low=row.low,
            close=row.close,
            volume=row.volume,
            amount=row.amount,
            source=None,
            data_status=row.data_status,
            created_at=row.created_at,
        )
        for row in rows
    ]

