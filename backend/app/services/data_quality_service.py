from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.data_quality import DataQualityLog
from app.models.market_data import MarketDataClean


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
            message="指定区间没有 clean 行情数据",
            severity="error",
        )
        return 1

    log_count = 0
    previous_close: Decimal | None = None
    for bar in bars:
        issues: list[tuple[str, str, str]] = []
        if bar.close is None or bar.close <= 0:
            issues.append(("zero_price", "failed", "收盘价为空或小于等于 0"))
        if bar.open is not None and bar.open <= 0:
            issues.append(("zero_price", "failed", "开盘价小于等于 0"))
        if bar.high is not None and bar.low is not None and bar.high < bar.low:
            issues.append(("abnormal_price", "failed", "最高价低于最低价"))
        if bar.volume is not None and bar.volume <= 0:
            issues.append(("zero_volume", "warning", "成交量为空或小于等于 0"))
        if previous_close and bar.close:
            daily_return = (bar.close / previous_close) - Decimal("1")
            if abs(daily_return) > Decimal("0.15"):
                issues.append(("abnormal_return", "warning", f"单日涨跌幅异常：{daily_return:.4%}"))

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
        message=f"完成 clean 行情质量检查，共检查 {len(bars)} 条",
        severity="info",
    )
    return log_count + 1


def list_quality_logs(db: Session, limit: int = 100, symbol: str | None = None) -> list[DataQualityLog]:
    query = select(DataQualityLog).order_by(DataQualityLog.created_at.desc()).limit(limit)
    if symbol:
        query = query.where(DataQualityLog.symbol == symbol)
    return list(db.scalars(query).all())


def get_quality_status(db: Session) -> dict:
    total_logs = db.scalar(select(func.count()).select_from(DataQualityLog)) or 0
    error_logs = db.scalar(select(func.count()).select_from(DataQualityLog).where(DataQualityLog.severity == "error")) or 0
    warning_logs = (
        db.scalar(select(func.count()).select_from(DataQualityLog).where(DataQualityLog.severity == "warning")) or 0
    )
    latest_created_at = db.scalar(select(func.max(DataQualityLog.created_at)))
    status = "error" if error_logs else "warning" if warning_logs else "ok"
    return {
        "total_logs": total_logs,
        "error_logs": error_logs,
        "warning_logs": warning_logs,
        "latest_created_at": latest_created_at,
        "status": status,
    }

