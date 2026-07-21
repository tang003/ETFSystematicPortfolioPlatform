from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.auth_api import ADMIN_ROLE, AuthenticatedUser, get_authenticated_user, require_researcher_user
from app.core.database import get_db
from app.schemas.portfolio_schema import (
    HoldingAnalysisRead,
    HoldingAnalysisRequest,
    InvestmentPlanAnalyzeRequest,
    InvestmentPlanCreate,
    InvestmentPlanRead,
    InvestmentPlanSuggestionRead,
    PortfolioPositionRead,
    PortfolioSnapshotRequest,
    PortfolioXrayRead,
    PositionResolveRead,
    PositionResolveRequest,
    TargetPortfolioRead,
)
from app.services.holding_service import (
    analyze_holdings,
    enrich_holding_analysis_with_alternatives,
    list_holding_analysis,
    list_positions,
    resolve_position_details,
    upsert_position_snapshot,
)
from app.services.investment_plan_service import (
    analyze_investment_plan,
    create_investment_plan,
    list_investment_plans,
    list_investment_suggestions,
)
from app.services.portfolio_xray_service import build_portfolio_xray
from app.services.strategy_service import latest_target_portfolio

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


def include_legacy_rows(user: AuthenticatedUser) -> bool:
    return user.role == ADMIN_ROLE


@router.get("/target", response_model=list[TargetPortfolioRead])
def get_latest_target_portfolio(db: Session = Depends(get_db)) -> list[TargetPortfolioRead]:
    return latest_target_portfolio(db)


@router.post("/positions", response_model=list[PortfolioPositionRead])
def save_position_snapshot(
    request: PortfolioSnapshotRequest,
    _: str = Depends(require_researcher_user),
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> list[PortfolioPositionRead]:
    try:
        return upsert_position_snapshot(
            db,
            request,
            owner_username=user.username,
            include_legacy=include_legacy_rows(user),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/positions", response_model=list[PortfolioPositionRead])
def get_positions(
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> list[PortfolioPositionRead]:
    return list_positions(db, owner_username=user.username, include_legacy=include_legacy_rows(user))


@router.get("/xray", response_model=PortfolioXrayRead)
def get_portfolio_xray(
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> PortfolioXrayRead:
    return build_portfolio_xray(db, owner_username=user.username, include_legacy=include_legacy_rows(user))


@router.post("/positions/resolve", response_model=list[PositionResolveRead])
def resolve_positions(
    request: PositionResolveRequest,
    _: str = Depends(require_researcher_user),
    db: Session = Depends(get_db),
) -> list[PositionResolveRead]:
    return resolve_position_details(db, request.symbols, auto_sync=request.auto_sync, source=request.source)


@router.post("/holdings/analyze", response_model=list[HoldingAnalysisRead])
def run_holding_analysis(
    request: HoldingAnalysisRequest,
    _: str = Depends(require_researcher_user),
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> list[HoldingAnalysisRead]:
    try:
        rows = analyze_holdings(
            db,
            run_id=request.run_id,
            analysis_date=request.analysis_date,
            owner_username=user.username,
            include_legacy=include_legacy_rows(user),
        )
        return enrich_holding_analysis_with_alternatives(db, rows)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/holdings/analysis", response_model=list[HoldingAnalysisRead])
def get_holding_analysis(
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> list[HoldingAnalysisRead]:
    rows = list_holding_analysis(db, owner_username=user.username, include_legacy=include_legacy_rows(user))
    return enrich_holding_analysis_with_alternatives(db, rows)


@router.post("/investment-plans", response_model=InvestmentPlanRead)
def create_plan(
    request: InvestmentPlanCreate,
    _: str = Depends(require_researcher_user),
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> InvestmentPlanRead:
    try:
        return create_investment_plan(db, request, owner_username=user.username)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/investment-plans", response_model=list[InvestmentPlanRead])
def get_plans(
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> list[InvestmentPlanRead]:
    return list_investment_plans(db, owner_username=user.username, include_legacy=include_legacy_rows(user))


@router.post("/investment-plans/{plan_id}/analyze", response_model=list[InvestmentPlanSuggestionRead])
def run_investment_plan_analysis(
    plan_id: int,
    request: InvestmentPlanAnalyzeRequest,
    _: str = Depends(require_researcher_user),
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> list[InvestmentPlanSuggestionRead]:
    try:
        return analyze_investment_plan(
            db,
            plan_id=plan_id,
            period_no=request.period_no,
            suggestion_date=request.suggestion_date,
            owner_username=user.username,
            include_legacy=include_legacy_rows(user),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/investment-plans/{plan_id}/suggestions", response_model=list[InvestmentPlanSuggestionRead])
def get_investment_plan_suggestions(
    plan_id: int,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> list[InvestmentPlanSuggestionRead]:
    return list_investment_suggestions(
        db,
        plan_id=plan_id,
        owner_username=user.username,
        include_legacy=include_legacy_rows(user),
    )
