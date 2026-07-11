from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.etf_detail_schema import EtfDetailResponse
from app.services.etf_detail_service import get_etf_detail

router = APIRouter(prefix="/etf-detail", tags=["etf-detail"])


@router.get("/{symbol}", response_model=EtfDetailResponse)
def get_etf_detail_endpoint(
    symbol: str,
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> EtfDetailResponse:
    return EtfDetailResponse(**get_etf_detail(db, symbol=symbol, start_date=start_date, end_date=end_date))
