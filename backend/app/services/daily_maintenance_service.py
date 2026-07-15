from __future__ import annotations

import json
from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

import redis
from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.database import SessionLocal
from app.models.factor import FactorDaily
from app.services.calendar_service import sync_trading_calendar
from app.services.factor_service import calculate_factors, latest_factor_ranking
from app.services.market_service import sync_market_data
from app.services.report_service import generate_monthly_report
from app.services.risk_service import generate_rebalance_orders, run_risk_check
from app.services.strategy_service import run_strategy

DAILY_MAINTENANCE_LOCK_KEY = "daily_maintenance:lock"
DAILY_MAINTENANCE_LAST_RUN_KEY = "daily_maintenance:last_run"


def parse_daily_maintenance_time(value: str) -> tuple[int, int]:
    parts = value.strip().split(":")
    if len(parts) != 2:
        raise ValueError("DAILY_MAINTENANCE_TIME must use HH:MM format")
    hour = int(parts[0])
    minute = int(parts[1])
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise ValueError("DAILY_MAINTENANCE_TIME must be a valid 24-hour time")
    return hour, minute


def run_daily_maintenance_from_settings(settings: Settings, redis_client: redis.Redis | None = None) -> dict[str, Any]:
    client = redis_client or redis.Redis.from_url(settings.redis_url, decode_responses=True)
    acquired = client.set(DAILY_MAINTENANCE_LOCK_KEY, "running", nx=True, ex=60 * 60)
    if not acquired:
        logger.info("daily maintenance skipped because another run is active")
        return {"status": "skipped", "reason": "already_running"}

    db = SessionLocal()
    try:
        result = run_daily_maintenance(db, settings=settings)
        record_daily_maintenance_result(client, result)
        return result
    except Exception as exc:
        failed = {"status": "failed", "error": str(exc), "run_date": date.today().isoformat()}
        record_daily_maintenance_result(client, failed)
        raise
    finally:
        db.close()
        client.delete(DAILY_MAINTENANCE_LOCK_KEY)


def run_daily_maintenance(db: Session, *, settings: Settings) -> dict[str, Any]:
    today = date.today()
    start_date = today - timedelta(days=settings.daily_maintenance_lookback_days)
    logger.info("daily maintenance started: {} to {}", start_date, today)

    calendar_result = sync_trading_calendar(
        db,
        start_date=start_date,
        end_date=today,
        source="tushare",
        incremental=True,
    )
    market_result = sync_market_data(
        db,
        symbols=None,
        sync_scope=settings.daily_maintenance_scope,
        start_date=start_date,
        end_date=today,
        source="tushare",
        incremental=True,
        clean_after_sync=True,
        max_symbols=settings.daily_maintenance_max_symbols,
        request_interval_seconds=settings.daily_maintenance_request_interval_seconds,
    )
    factor_result = calculate_factors(db, symbols=None, start_date=None, end_date=None)
    run_date = latest_available_factor_date(db)
    strategy_result: dict[str, Any] | None = None
    risk_result: dict[str, Any] | None = None
    rebalance_result: dict[str, Any] | None = None
    report_result: dict[str, Any] | None = None

    if run_date is not None and factor_result["success_count"] > 0:
        strategy_result = run_strategy(
            db,
            strategy_code=settings.daily_maintenance_strategy_code,
            run_date=run_date,
            run_type="daily_maintenance",
        )
        run_id = strategy_result["run_id"]
        risk_result = run_risk_check(db, run_id=run_id)
        rebalance_result = generate_rebalance_orders(
            db,
            run_id=run_id,
            portfolio_value=Decimal(settings.daily_maintenance_portfolio_value),
        )
        if settings.daily_maintenance_generate_report:
            report_result = generate_monthly_report(db, run_id=run_id, report_date=run_date)

    summary = {
        "status": "success",
        "run_date": run_date,
        "calendar": calendar_result,
        "market": summarize_market_result(market_result),
        "factors": {
            "total_symbols": factor_result["total_symbols"],
            "success_count": factor_result["success_count"],
            "failed_count": factor_result["failed_count"],
            "total_factor_rows": factor_result["total_factor_rows"],
        },
        "strategy": strategy_result,
        "risk": risk_result,
        "rebalance": rebalance_result,
        "report": report_result,
    }
    logger.info("daily maintenance completed: {}", summary)
    return summary


def record_daily_maintenance_result(client: redis.Redis, result: dict[str, Any]) -> None:
    client.set(DAILY_MAINTENANCE_LAST_RUN_KEY, json.dumps(result, default=str, ensure_ascii=False), ex=60 * 60 * 24 * 30)


def get_daily_maintenance_status(settings: Settings) -> dict[str, Any]:
    client = redis.Redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=2)
    last_run_raw = client.get(DAILY_MAINTENANCE_LAST_RUN_KEY)
    lock_active = bool(client.get(DAILY_MAINTENANCE_LOCK_KEY))
    last_run: dict[str, Any] | None = None
    if last_run_raw:
        try:
            last_run = json.loads(last_run_raw)
        except json.JSONDecodeError:
            last_run = {"status": "unknown", "raw": last_run_raw}
    return {
        **next_maintenance_preview(settings),
        "lock_active": lock_active,
        "last_run": last_run,
    }


def latest_available_factor_date(db: Session) -> date | None:
    ranking = latest_factor_ranking(db, limit=1)
    if ranking:
        return ranking[0].trade_date
    return db.scalar(select(FactorDaily.trade_date).order_by(FactorDaily.trade_date.desc()).limit(1))


def summarize_market_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "start_date": result.get("start_date"),
        "end_date": result.get("end_date"),
        "source": result.get("source"),
        "sync_scope": result.get("sync_scope"),
        "requested_symbols": result.get("requested_symbols"),
        "up_to_date_symbols": result.get("up_to_date_symbols"),
        "success_count": result.get("success_count"),
        "failed_count": result.get("failed_count"),
        "total_raw_rows": result.get("total_raw_rows"),
        "total_clean_rows": result.get("total_clean_rows"),
        "total_quality_logs": result.get("total_quality_logs"),
    }


def next_maintenance_preview(settings: Settings) -> dict[str, Any]:
    hour, minute = parse_daily_maintenance_time(settings.daily_maintenance_time)
    return {
        "enabled": settings.daily_maintenance_enabled,
        "timezone": "Asia/Shanghai",
        "hour": hour,
        "minute": minute,
        "scope": settings.daily_maintenance_scope,
        "lookback_days": settings.daily_maintenance_lookback_days,
        "max_symbols": settings.daily_maintenance_max_symbols,
        "request_interval_seconds": settings.daily_maintenance_request_interval_seconds,
        "strategy_code": settings.daily_maintenance_strategy_code,
        "generate_report": settings.daily_maintenance_generate_report,
        "now": date.today().isoformat(),
        "tz": ZoneInfo("Asia/Shanghai").key,
    }
