from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.asset import AssetMaster
from app.models.factor import FactorDaily
from app.models.market_data import MarketDataClean
from app.services.etf_compare_service import build_compare_metric


def get_etf_detail(
    db: Session,
    *,
    symbol: str,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict:
    resolved_end = end_date or date.today()
    resolved_start = start_date or (resolved_end - timedelta(days=365))
    asset = db.scalar(select(AssetMaster).where(AssetMaster.symbol == symbol))
    bars = list(
        db.scalars(
            select(MarketDataClean)
            .where(
                MarketDataClean.symbol == symbol,
                MarketDataClean.trade_date >= resolved_start,
                MarketDataClean.trade_date <= resolved_end,
                MarketDataClean.close.is_not(None),
            )
            .order_by(MarketDataClean.trade_date)
        ).all()
    )
    latest_factor = db.scalar(
        select(FactorDaily)
        .where(FactorDaily.symbol == symbol)
        .order_by(FactorDaily.trade_date.desc())
        .limit(1)
    )
    metric = build_compare_metric(symbol, bars, asset)
    return {
        "symbol": symbol,
        "asset": asset,
        "metric": metric,
        "latest_factor": latest_factor,
        "curve": build_detail_curve(bars),
        "recent_bars": [market_bar_dict(row) for row in reversed(bars[-30:])],
    }


def build_detail_curve(rows: list[MarketDataClean]) -> list[dict]:
    closes = [(row, Decimal(row.close)) for row in rows if row.close and row.close > 0]
    if not closes:
        return []
    base = closes[0][1]
    peak = closes[0][1]
    curve: list[dict] = []
    for row, close in closes:
        peak = max(peak, close)
        curve.append(
            {
                "trade_date": row.trade_date,
                "close": close,
                "normalized_value": (close / base * Decimal("100")).quantize(Decimal("0.0001")),
                "drawdown": (close / peak - Decimal("1")).quantize(Decimal("0.000001")),
                "amount": row.amount,
            }
        )
    return curve


def market_bar_dict(row: MarketDataClean) -> dict:
    return {
        "symbol": row.symbol,
        "trade_date": row.trade_date,
        "open": row.open,
        "high": row.high,
        "low": row.low,
        "close": row.close,
        "volume": row.volume,
        "amount": row.amount,
        "source": None,
        "data_status": row.data_status,
        "created_at": row.created_at,
    }
