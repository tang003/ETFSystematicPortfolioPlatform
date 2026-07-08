from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class MonthlyReportRequest(BaseModel):
    run_id: int | None = None
    report_date: date | None = None


class ReportSummary(BaseModel):
    id: int
    run_id: int | None
    report_date: date
    report_type: str
    title: str | None
    status: str


class ReportRead(BaseModel):
    id: int
    run_id: int | None
    report_date: date
    report_type: str
    title: str | None
    file_path: str | None
    content_markdown: str | None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

