from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditLogRead(BaseModel):
    id: int
    actor_username: str | None
    actor_role: str | None
    method: str
    path: str
    action: str
    status_code: int | None
    duration_ms: int | None
    client_ip: str | None
    request_id: str | None
    detail: dict | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
