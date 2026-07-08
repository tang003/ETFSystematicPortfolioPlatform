from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.data_quality_schema import DataQualityCheckRequest, DataQualityCheckResult, DataQualityLogRead, DataQualityStatus
from app.services.data_quality_service import check_clean_bars, get_quality_status, list_quality_logs

router = APIRouter(prefix="/data-quality", tags=["data-quality"])


@router.post("/check", response_model=list[DataQualityCheckResult])
def check_data_quality(
    request: DataQualityCheckRequest,
    db: Session = Depends(get_db),
) -> list[DataQualityCheckResult]:
    results: list[DataQualityCheckResult] = []
    for symbol in request.symbols:
        try:
            log_count = check_clean_bars(db, symbol=symbol, start_date=request.start_date, end_date=request.end_date)
            db.commit()
            results.append(DataQualityCheckResult(symbol=symbol, quality_logs=log_count, status="success"))
        except Exception as exc:  # noqa: BLE001 - keep per-symbol failure visible to API callers.
            db.rollback()
            results.append(DataQualityCheckResult(symbol=symbol, quality_logs=0, status="failed", message=str(exc)))
    return results


@router.get("/logs", response_model=list[DataQualityLogRead])
def get_data_quality_logs(
    symbol: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> list[DataQualityLogRead]:
    return list_quality_logs(db, limit=limit, symbol=symbol)


@router.get("/status", response_model=DataQualityStatus)
def get_data_quality_status(db: Session = Depends(get_db)) -> DataQualityStatus:
    return get_quality_status(db)
