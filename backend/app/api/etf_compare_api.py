from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.etf_compare_schema import EtfCompareRequest, EtfCompareResponse
from app.services.etf_compare_service import compare_etfs

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
