from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.audit import AuditLog
from app.schemas.audit_schema import AuditLogRead

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


@router.get("", response_model=list[AuditLogRead])
def list_audit_logs(
    limit: int = Query(default=100, ge=1, le=500),
    actor_username: str | None = Query(default=None),
    action: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[AuditLogRead]:
    query = select(AuditLog)
    if actor_username:
        query = query.where(AuditLog.actor_username == actor_username)
    if action:
        query = query.where(AuditLog.action == action)
    rows = db.scalars(query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(limit)).all()
    return [AuditLogRead.model_validate(row) for row in rows]
