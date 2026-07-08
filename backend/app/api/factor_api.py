from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.factor_schema import FactorCalculateRequest, FactorCalculateResponse, FactorRead
from app.services.factor_service import calculate_factors, latest_factor_ranking, list_factors

router = APIRouter(prefix="/factors", tags=["factors"])


@router.post("/calculate", response_model=FactorCalculateResponse)
def calculate_factor_values(
    request: FactorCalculateRequest,
    db: Session = Depends(get_db),
) -> FactorCalculateResponse:
    return calculate_factors(db, symbols=request.symbols, start_date=request.start_date, end_date=request.end_date)


@router.get("/ranking", response_model=list[FactorRead])
def get_factor_ranking(
    trade_date: date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[FactorRead]:
    return latest_factor_ranking(db, trade_date=trade_date, limit=limit)


@router.get("/{symbol}", response_model=list[FactorRead])
def get_symbol_factors(
    symbol: str,
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> list[FactorRead]:
    return list_factors(db, symbol=symbol, limit=limit)

