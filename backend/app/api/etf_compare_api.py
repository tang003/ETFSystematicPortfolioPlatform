from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.etf_compare_schema import (
    EtfCompareMetric,
    EtfCompareRequest,
    EtfCompareResponse,
    EtfScreenerRequest,
    EtfScreenerResponse,
    EtfTradabilityRequest,
)
from app.services.etf_compare_service import compare_etfs, score_etf_tradability, screen_etfs

router = APIRouter(prefix="/etf-compare", tags=["etf-compare"])


@router.post("", response_model=EtfCompareResponse)
def compare_etf_metrics(request: EtfCompareRequest, db: Session = Depends(get_db)) -> EtfCompareResponse:
    try:
        result = compare_etfs(
            db,
            symbols=request.symbols,
            start_date=request.start_date,
            end_date=request.end_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return EtfCompareResponse(**result)


@router.post("/tradability", response_model=list[EtfCompareMetric])
def score_etf_tradability_endpoint(
    request: EtfTradabilityRequest,
    db: Session = Depends(get_db),
) -> list[EtfCompareMetric]:
    return score_etf_tradability(
        db,
        symbols=request.symbols,
        start_date=request.start_date,
        end_date=request.end_date,
    )


@router.post("/screener", response_model=EtfScreenerResponse)
def screen_etf_candidates(
    request: EtfScreenerRequest,
    db: Session = Depends(get_db),
) -> EtfScreenerResponse:
    try:
        result = screen_etfs(
            db,
            scope=request.scope,
            symbols=request.symbols,
            start_date=request.start_date,
            end_date=request.end_date,
            limit=request.limit,
            min_bars=request.min_bars,
            min_tradability_score=request.min_tradability_score,
            min_buy_score=request.min_buy_score,
            asset_class=request.asset_class,
            asset_region=request.asset_region,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return EtfScreenerResponse(**result)
