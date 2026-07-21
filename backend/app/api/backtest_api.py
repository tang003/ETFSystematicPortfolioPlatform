from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.auth_api import require_researcher_user
from app.core.database import get_db
from app.schemas.backtest_schema import (
    BacktestEquityCurveRead,
    BacktestMetricRead,
    BacktestRunRead,
    BacktestRunRequest,
    BacktestRunResponse,
    BacktestTradeRead,
)
from app.services.backtest_service import (
    get_backtest_run,
    list_backtest_metrics,
    list_backtest_runs,
    list_backtest_trades,
    list_equity_curve,
    run_backtest,
)

router = APIRouter(prefix="/backtest", tags=["backtest"])


@router.post("/run", response_model=BacktestRunResponse)
def run_backtest_endpoint(
    request: BacktestRunRequest,
    _: str = Depends(require_researcher_user),
    db: Session = Depends(get_db),
) -> BacktestRunResponse:
    return run_backtest(
        db,
        strategy_code=request.strategy_code,
        name=request.name,
        symbols=request.symbols,
        start_date=request.start_date,
        end_date=request.end_date,
        initial_cash=request.initial_cash,
        monthly_contribution=request.monthly_contribution,
        fee_rate=request.fee_rate,
        slippage_rate=request.slippage_rate,
    )


@router.get("/runs", response_model=list[BacktestRunRead])
def get_backtest_runs(
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> list[BacktestRunRead]:
    return list_backtest_runs(db, limit=limit)


@router.get("/{backtest_id}", response_model=BacktestRunRead)
def get_backtest(backtest_id: int, db: Session = Depends(get_db)) -> BacktestRunRead:
    run = get_backtest_run(db, backtest_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Backtest not found")
    return run


@router.get("/{backtest_id}/equity-curve", response_model=list[BacktestEquityCurveRead])
def get_equity_curve(backtest_id: int, db: Session = Depends(get_db)) -> list[BacktestEquityCurveRead]:
    return list_equity_curve(db, backtest_id)


@router.get("/{backtest_id}/trades", response_model=list[BacktestTradeRead])
def get_trades(backtest_id: int, db: Session = Depends(get_db)) -> list[BacktestTradeRead]:
    return list_backtest_trades(db, backtest_id)


@router.get("/{backtest_id}/metrics", response_model=list[BacktestMetricRead])
def get_metrics(backtest_id: int, db: Session = Depends(get_db)) -> list[BacktestMetricRead]:
    return list_backtest_metrics(db, backtest_id)
