from fastapi import APIRouter, Depends, HTTPException
import redis
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.worker import HEARTBEAT_KEY

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    settings = get_settings()
    return {"status": "ok", "service": settings.app_name, "environment": settings.app_env}


@router.get("/health/live")
def liveness_check() -> dict[str, str]:
    settings = get_settings()
    return {"status": "ok", "service": settings.app_name, "environment": settings.app_env}


@router.get("/health/ready")
def readiness_check(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    settings = get_settings()
    if settings.workflow_execution_mode == "worker":
        try:
            client = redis.Redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=2)
            heartbeat = client.get(HEARTBEAT_KEY)
        except redis.RedisError as exc:
            raise HTTPException(status_code=503, detail="Redis is not ready") from exc
        if not heartbeat:
            raise HTTPException(status_code=503, detail="Workflow worker heartbeat is missing")
    return {
        "status": "ready",
        "service": settings.app_name,
        "environment": settings.app_env,
        "workflow_execution_mode": settings.workflow_execution_mode,
    }
