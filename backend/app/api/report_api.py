from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.report_schema import MonthlyReportRequest, ReportRead, ReportSummary
from app.services.report_service import generate_monthly_report, get_report, list_reports

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/monthly", response_model=ReportSummary)
def create_monthly_report(request: MonthlyReportRequest, db: Session = Depends(get_db)) -> ReportSummary:
    return generate_monthly_report(db, run_id=request.run_id, report_date=request.report_date)


@router.get("", response_model=list[ReportRead])
def get_reports(
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> list[ReportRead]:
    return list_reports(db, limit=limit)


@router.get("/{report_id}", response_model=ReportRead)
def get_report_by_id(report_id: int, db: Session = Depends(get_db)) -> ReportRead:
    report = get_report(db, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report

