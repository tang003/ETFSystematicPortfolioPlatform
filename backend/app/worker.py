from __future__ import annotations

import signal
import time
from datetime import datetime

import redis
from loguru import logger

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.logging import setup_logging
from app.core.scheduler import create_scheduler
from app.services.daily_maintenance_service import parse_daily_maintenance_time, run_daily_maintenance_from_settings
from app.services.workflow_service import (
    claim_next_workflow_task,
    recover_interrupted_workflow_tasks,
    run_workflow_task,
)

HEARTBEAT_KEY = "workflow_worker:heartbeat"
_shutdown_requested = False


def request_shutdown(signum: int, _frame: object) -> None:
    global _shutdown_requested
    _shutdown_requested = True
    logger.info("workflow worker received signal {}", signum)


def record_heartbeat(client: redis.Redis, ttl_seconds: int) -> None:
    client.set(HEARTBEAT_KEY, datetime.utcnow().isoformat(), ex=ttl_seconds)


def main() -> int:
    setup_logging()
    settings = get_settings()
    signal.signal(signal.SIGTERM, request_shutdown)
    signal.signal(signal.SIGINT, request_shutdown)

    redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    scheduler = create_scheduler()
    if settings.daily_maintenance_enabled:
        hour, minute = parse_daily_maintenance_time(settings.daily_maintenance_time)
        scheduler.add_job(
            run_daily_maintenance_from_settings,
            "cron",
            hour=hour,
            minute=minute,
            args=[settings, redis_client],
            id="daily_maintenance",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        scheduler.start()
        logger.info("daily maintenance scheduled at {:02d}:{:02d} Asia/Shanghai", hour, minute)
    else:
        logger.info("daily maintenance scheduler disabled")
    logger.info("workflow worker starting with poll interval {}s", settings.workflow_worker_poll_seconds)

    db = SessionLocal()
    try:
        recovered = recover_interrupted_workflow_tasks(db)
        if recovered:
            logger.warning("recovered {} interrupted workflow task(s)", recovered)
    finally:
        db.close()

    while not _shutdown_requested:
        record_heartbeat(redis_client, settings.workflow_worker_heartbeat_ttl_seconds)
        db = SessionLocal()
        try:
            task = claim_next_workflow_task(db)
        finally:
            db.close()

        if task is None:
            time.sleep(settings.workflow_worker_poll_seconds)
            continue

        logger.info("workflow worker claimed task {}", task.id)
        run_workflow_task(task.id)

    if scheduler.running:
        scheduler.shutdown(wait=False)
    logger.info("workflow worker stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
