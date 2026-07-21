from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.auth_api import require_researcher_user
from app.core.database import get_db
from app.schemas.risk_schema import RebalanceGenerateRequest, RebalanceGenerateResponse, RebalanceOrderRead
from app.services.risk_service import generate_rebalance_orders, list_rebalance_orders

router = APIRouter(prefix="/rebalance", tags=["rebalance"])


@router.post("/generate", response_model=RebalanceGenerateResponse)
def generate_rebalance(
    request: RebalanceGenerateRequest,
    _: str = Depends(require_researcher_user),
    db: Session = Depends(get_db),
) -> RebalanceGenerateResponse:
    return generate_rebalance_orders(db, run_id=request.run_id, portfolio_value=request.portfolio_value)


@router.get("/orders", response_model=list[RebalanceOrderRead])
def get_rebalance_orders(
    run_id: int | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> list[RebalanceOrderRead]:
    return list_rebalance_orders(db, run_id=run_id, limit=limit)
