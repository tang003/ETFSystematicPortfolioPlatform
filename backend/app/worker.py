from __future__ import annotations

import signal
import time
from datetime import datetime

import redis
from loguru import logger

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.logging import setup_logging
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

    logger.info("workflow worker stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
