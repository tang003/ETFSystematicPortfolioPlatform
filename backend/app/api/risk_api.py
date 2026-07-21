from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.auth_api import require_researcher_user
from app.core.database import get_db
from app.schemas.risk_schema import RiskCheckRequest, RiskCheckResponse, RiskCheckResultRead
from app.services.risk_service import list_risk_results, run_risk_check

router = APIRouter(prefix="/risk", tags=["risk"])


@router.post("/check", response_model=RiskCheckResponse)
def check_risk(
    request: RiskCheckRequest,
    _: str = Depends(require_researcher_user),
    db: Session = Depends(get_db),
) -> RiskCheckResponse:
    return run_risk_check(db, run_id=request.run_id)


@router.get("/results", response_model=list[RiskCheckResultRead])
def get_risk_results(
    run_id: int | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> list[RiskCheckResultRead]:
    return list_risk_results(db, run_id=run_id, limit=limit)
