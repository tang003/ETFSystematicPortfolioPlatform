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
        "alternatives": build_same_index_alternatives(
            db,
            asset=asset,
            current_metric=metric,
            start_date=resolved_start,
            end_date=resolved_end,
        ),
        "curve": build_detail_curve(bars),
        "recent_bars": [market_bar_dict(row) for row in reversed(bars[-30:])],
    }


def build_same_index_alternatives(
    db: Session,
    *,
    asset: AssetMaster | None,
    current_metric: dict,
    start_date: date,
    end_date: date,
    limit: int = 8,
) -> list[dict]:
    if asset is None or not asset.tracking_index:
        return []
    candidates = list(
        db.scalars(
            select(AssetMaster)
            .where(
                AssetMaster.tracking_index == asset.tracking_index,
                AssetMaster.symbol != asset.symbol,
            )
            .order_by(AssetMaster.enabled.desc(), AssetMaster.fund_size.desc().nullslast(), AssetMaster.symbol)
            .limit(30)
        ).all()
    )
    rows: list[dict] = []
    current_score = recommendation_score(asset, current_metric)
    for candidate in candidates:
        bars = list(
            db.scalars(
                select(MarketDataClean)
                .where(
                    MarketDataClean.symbol == candidate.symbol,
                    MarketDataClean.trade_date >= start_date,
                    MarketDataClean.trade_date <= end_date,
                    MarketDataClean.close.is_not(None),
                )
                .order_by(MarketDataClean.trade_date)
            ).all()
        )
        metric = build_compare_metric(candidate.symbol, bars, candidate)
        score = recommendation_score(candidate, metric)
        level = recommendation_level(score, current_score)
        rows.append(
            {
                "symbol": candidate.symbol,
                "name": candidate.name,
                "fund_company": candidate.fund_company,
                "tracking_index": candidate.tracking_index,
                "fund_size": candidate.fund_size,
                "expense_ratio": candidate.expense_ratio or total_fee(candidate),
                "average_amount": metric.get("average_amount"),
                "tradability_score": metric.get("tradability_score", 0),
                "recommendation_score": score,
                "recommendation_level": level,
                "reasons": recommendation_reasons(candidate, metric, score, current_score),
            }
        )
    return sorted(rows, key=lambda item: item["recommendation_score"], reverse=True)[:limit]


def recommendation_score(asset: AssetMaster, metric: dict) -> int:
    tradability = int(metric.get("tradability_score") or 0)
    size_score = 0
    if asset.fund_size:
        size_yi = Decimal(asset.fund_size) / Decimal("100000000")
        if size_yi >= 100:
            size_score = 20
        elif size_yi >= 50:
            size_score = 16
        elif size_yi >= 20:
            size_score = 12
        elif size_yi >= 5:
            size_score = 8
        else:
            size_score = 4
    fee = asset.expense_ratio or total_fee(asset)
    fee_score = 10
    if fee is not None:
        fee_value = Decimal(fee)
        if fee_value <= Decimal("0.002"):
            fee_score = 15
        elif fee_value <= Decimal("0.006"):
            fee_score = 12
        elif fee_value <= Decimal("0.010"):
            fee_score = 8
        else:
            fee_score = 4
    return max(0, min(100, round(tradability * 0.65 + size_score + fee_score)))


def recommendation_level(score: int, current_score: int) -> str:
    if score >= max(80, current_score + 5):
        return "首选关注"
    if score >= current_score - 10:
        return "可替代"
    return "谨慎"


def recommendation_reasons(asset: AssetMaster, metric: dict, score: int, current_score: int) -> list[str]:
    reasons: list[str] = []
    if score > current_score:
        reasons.append("综合评分高于当前 ETF")
    if asset.fund_size:
        reasons.append(f"基金规模约 {Decimal(asset.fund_size) / Decimal('100000000'):.2f} 亿")
    fee = asset.expense_ratio or total_fee(asset)
    if fee is not None:
        reasons.append(f"综合费率约 {Decimal(fee) * Decimal('100'):.3f}%")
    average_amount = metric.get("average_amount")
    if average_amount:
        reasons.append(f"区间日均成交额约 {Decimal(average_amount) / Decimal('100000000'):.2f} 亿")
    if not reasons:
        reasons.append("同指数 ETF，可作为备选观察")
    return reasons[:4]


def total_fee(asset: AssetMaster) -> Decimal | None:
    management = Decimal(asset.management_fee or 0)
    custody = Decimal(asset.custody_fee or 0)
    if not management and not custody:
        return None
    return management + custody


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
