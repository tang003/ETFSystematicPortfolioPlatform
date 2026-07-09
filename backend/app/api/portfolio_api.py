from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.portfolio_schema import (
    HoldingAnalysisRead,
    HoldingAnalysisRequest,
    PortfolioPositionRead,
    PortfolioSnapshotRequest,
    TargetPortfolioRead,
)
from app.services.holding_service import analyze_holdings, list_holding_analysis, list_positions, upsert_position_snapshot
from app.services.strategy_service import latest_target_portfolio

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/target", response_model=list[TargetPortfolioRead])
def get_latest_target_portfolio(db: Session = Depends(get_db)) -> list[TargetPortfolioRead]:
    return latest_target_portfolio(db)


@router.post("/positions", response_model=list[PortfolioPositionRead])
def save_position_snapshot(
    request: PortfolioSnapshotRequest,
    db: Session = Depends(get_db),
) -> list[PortfolioPositionRead]:
    return upsert_position_snapshot(db, request)


@router.get("/positions", response_model=list[PortfolioPositionRead])
def get_positions(db: Session = Depends(get_db)) -> list[PortfolioPositionRead]:
    return list_positions(db)


@router.post("/holdings/analyze", response_model=list[HoldingAnalysisRead])
def run_holding_analysis(
    request: HoldingAnalysisRequest,
    db: Session = Depends(get_db),
) -> list[HoldingAnalysisRead]:
    return analyze_holdings(db, run_id=request.run_id, analysis_date=request.analysis_date)


@router.get("/holdings/analysis", response_model=list[HoldingAnalysisRead])
def get_holding_analysis(db: Session = Depends(get_db)) -> list[HoldingAnalysisRead]:
    return list_holding_analysis(db)
