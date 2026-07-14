from datetime import date
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.data_quality import DataQualityLog
from app.models.market_data import MarketDataClean, TradingCalendar


def add_quality_log(
    db: Session,
    *,
    symbol: str | None,
    trade_date: date | None,
    check_type: str,
    status: str,
    message: str,
    severity: str = "info",
) -> DataQualityLog:
    log = DataQualityLog(
        symbol=symbol,
        trade_date=trade_date,
        check_type=check_type,
        status=status,
        message=message,
        severity=severity,
    )
    db.add(log)
    return log


def check_clean_bars(db: Session, symbol: str, start_date: date, end_date: date) -> int:
    clear_existing_quality_logs(db, symbol=symbol, start_date=start_date, end_date=end_date)
    bars = list(
        db.scalars(
            select(MarketDataClean)
            .where(MarketDataClean.symbol == symbol)
            .where(MarketDataClean.trade_date >= start_date)
            .where(MarketDataClean.trade_date <= end_date)
            .order_by(MarketDataClean.trade_date)
        )
    )

    if not bars:
        add_quality_log(
            db,
            symbol=symbol,
            trade_date=None,
            check_type="missing_data",
            status="failed",
            message="No clean market data in requested date range",
            severity="error",
        )
        return 1

    log_count = 0
    existing_trade_dates = {bar.trade_date for bar in bars}
    expected_trade_dates = list_expected_trade_dates(db, start_date, end_date)
    missing_dates = [trade_date for trade_date in expected_trade_dates if trade_date not in existing_trade_dates]
    for missing_date in missing_dates:
        add_quality_log(
            db,
            symbol=symbol,
            trade_date=missing_date,
            check_type="missing_data",
            status="warning",
            message="Missing clean market data for open trading day",
            severity="warning",
        )
        log_count += 1

    previous_close: Decimal | None = None
    for bar in bars:
        issues: list[tuple[str, str, str]] = []
        if bar.close is None or bar.close <= 0:
            issues.append(("zero_price", "error", "Close price is empty or <= 0"))
        if bar.open is not None and bar.open <= 0:
            issues.append(("zero_price", "error", "Open price is <= 0"))
        if bar.high is not None and bar.low is not None and bar.high < bar.low:
            issues.append(("abnormal_price", "error", "High price is lower than low price"))
        if bar.volume is not None and bar.volume <= 0:
            issues.append(("zero_volume", "warning", "Volume is empty or <= 0"))
        if previous_close and bar.close:
            daily_return = (bar.close / previous_close) - Decimal("1")
            if abs(daily_return) > Decimal("0.15"):
                issues.append(("abnormal_return", "warning", f"Abnormal daily return: {daily_return:.4%}"))

        if issues:
            bar.data_status = "warning"
            for check_type, severity, message in issues:
                add_quality_log(
                    db,
                    symbol=symbol,
                    trade_date=bar.trade_date,
                    check_type=check_type,
                    status="failed" if severity == "error" else "warning",
                    message=message,
                    severity=severity,
                )
                log_count += 1
        else:
            bar.data_status = "normal"

        if bar.close and bar.close > 0:
            previous_close = bar.close

    add_quality_log(
        db,
        symbol=symbol,
        trade_date=end_date,
        check_type="cleaning_success",
        status="success",
        message=f"Checked {len(bars)} clean bars; missing_open_days={len(missing_dates)}",
        severity="info",
    )
    return log_count + 1


def clear_existing_quality_logs(db: Session, *, symbol: str, start_date: date, end_date: date) -> None:
    db.execute(
        delete(DataQualityLog).where(
            DataQualityLog.symbol == symbol,
            DataQualityLog.trade_date.is_not(None),
            DataQualityLog.trade_date >= start_date,
            DataQualityLog.trade_date <= end_date,
        )
    )
    db.execute(
        delete(DataQualityLog).where(
            DataQualityLog.symbol == symbol,
            DataQualityLog.trade_date.is_(None),
            DataQualityLog.check_type == "missing_data",
        )
    )


def list_expected_trade_dates(db: Session, start_date: date, end_date: date) -> list[date]:
    return list(
        db.scalars(
            select(TradingCalendar.trade_date)
            .where(TradingCalendar.trade_date >= start_date)
            .where(TradingCalendar.trade_date <= end_date)
            .where(TradingCalendar.is_open.is_(True))
            .order_by(TradingCalendar.trade_date)
        ).all()
    )


def list_quality_logs(db: Session, limit: int = 100, symbol: str | None = None) -> list[DataQualityLog]:
    query = select(DataQualityLog).order_by(DataQualityLog.created_at.desc()).limit(limit)
    if symbol:
        query = query.where(DataQualityLog.symbol == symbol)
    return list(db.scalars(query).all())


def get_quality_status(db: Session) -> dict:
    history_total_logs = db.scalar(select(func.count()).select_from(DataQualityLog)) or 0
    history_error_logs = db.scalar(select(func.count()).select_from(DataQualityLog).where(DataQualityLog.severity == "error")) or 0
    history_warning_logs = (
        db.scalar(select(func.count()).select_from(DataQualityLog).where(DataQualityLog.severity == "warning")) or 0
    )
    latest_created_at = db.scalar(select(func.max(DataQualityLog.created_at)))
    if latest_created_at is None:
        total_logs = 0
        error_logs = 0
        warning_logs = 0
    else:
        total_logs = (
            db.scalar(select(func.count()).select_from(DataQualityLog).where(DataQualityLog.created_at == latest_created_at))
            or 0
        )
        error_logs = (
            db.scalar(
                select(func.count())
                .select_from(DataQualityLog)
                .where(DataQualityLog.created_at == latest_created_at, DataQualityLog.severity == "error")
            )
            or 0
        )
        warning_logs = (
            db.scalar(
                select(func.count())
                .select_from(DataQualityLog)
                .where(DataQualityLog.created_at == latest_created_at, DataQualityLog.severity == "warning")
            )
            or 0
        )
    status = "error" if error_logs else "warning" if warning_logs else "ok"
    return {
        "total_logs": total_logs,
        "error_logs": error_logs,
        "warning_logs": warning_logs,
        "latest_created_at": latest_created_at,
        "status": status,
        "history_total_logs": history_total_logs,
        "history_error_logs": history_error_logs,
        "history_warning_logs": history_warning_logs,
    }
