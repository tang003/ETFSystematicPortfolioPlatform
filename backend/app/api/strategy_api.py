from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.strategy_schema import (
    AlphaSignalRead,
    StrategyConfigCreate,
    StrategyConfigRead,
    StrategyConfigUpdate,
    StrategyRunRequest,
    StrategyRunResponse,
)
from app.services.strategy_service import (
    create_strategy_config,
    latest_signals,
    list_strategy_configs,
    run_strategy,
    update_strategy_config,
)

router = APIRouter(prefix="/strategies", tags=["strategies"])


@router.get("", response_model=list[StrategyConfigRead])
def get_strategies(db: Session = Depends(get_db)) -> list[StrategyConfigRead]:
    return list_strategy_configs(db)


@router.post("", response_model=StrategyConfigRead)
def create_strategy_endpoint(request: StrategyConfigCreate, db: Session = Depends(get_db)) -> StrategyConfigRead:
    try:
        return create_strategy_config(db, request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/{strategy_code}", response_model=StrategyConfigRead)
def update_strategy_endpoint(
    strategy_code: str,
    request: StrategyConfigUpdate,
    db: Session = Depends(get_db),
) -> StrategyConfigRead:
    try:
        return update_strategy_config(db, strategy_code, request.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=404 if "not found" in str(exc).lower() else 400, detail=str(exc)) from exc


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

