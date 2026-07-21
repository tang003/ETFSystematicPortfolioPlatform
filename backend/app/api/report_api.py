from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.auth_api import ADMIN_ROLE, AuthenticatedUser, get_authenticated_user, require_researcher_user
from app.core.database import get_db
from app.schemas.report_schema import MonthlyReportRequest, ReportRead, ReportSummary
from app.services.report_service import generate_monthly_report, get_report, list_reports

router = APIRouter(prefix="/reports", tags=["reports"])


def include_legacy_rows(user: AuthenticatedUser) -> bool:
    return user.role == ADMIN_ROLE


@router.post("/monthly", response_model=ReportSummary)
def create_monthly_report(
    request: MonthlyReportRequest,
    _: str = Depends(require_researcher_user),
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> ReportSummary:
    return generate_monthly_report(
        db,
        run_id=request.run_id,
        report_date=request.report_date,
        owner_username=user.username,
        include_legacy=include_legacy_rows(user),
    )


@router.get("", response_model=list[ReportRead])
def get_reports(
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> list[ReportRead]:
    return list_reports(db, limit=limit, owner_username=user.username, include_legacy=include_legacy_rows(user))


@router.get("/{report_id}", response_model=ReportRead)
def get_report_by_id(
    report_id: int,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> ReportRead:
    report = get_report(db, report_id, owner_username=user.username, include_legacy=include_legacy_rows(user))
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report
