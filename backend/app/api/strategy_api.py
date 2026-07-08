from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.strategy_schema import AlphaSignalRead, StrategyConfigRead, StrategyRunRequest, StrategyRunResponse
from app.services.strategy_service import latest_signals, list_strategy_configs, run_strategy

router = APIRouter(prefix="/strategies", tags=["strategies"])


@router.get("", response_model=list[StrategyConfigRead])
def get_strategies(db: Session = Depends(get_db)) -> list[StrategyConfigRead]:
    return list_strategy_configs(db)


@router.post("/run", response_model=StrategyRunResponse)
def run_strategy_endpoint(request: StrategyRunRequest, db: Session = Depends(get_db)) -> StrategyRunResponse:
    return run_strategy(
        db,
        strategy_code=request.strategy_code,
        run_date=request.run_date,
        run_type=request.run_type,
    )


@router.get("/latest-signals", response_model=list[AlphaSignalRead])
def get_latest_signals(
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> list[AlphaSignalRead]:
    return latest_signals(db, limit=limit)

