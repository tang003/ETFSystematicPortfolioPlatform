from datetime import date
from decimal import Decimal
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.asset import AssetMaster
from app.models.factor import FactorDaily
from app.models.market_data import MarketDataClean

FACTOR_WEIGHTS = {
    "trend_score": Decimal("0.35"),
    "momentum_score": Decimal("0.30"),
    "volatility_score": Decimal("0.15"),
    "drawdown_score": Decimal("0.10"),
    "liquidity_score": Decimal("0.05"),
    "premium_score": Decimal("0.05"),
}


def calculate_factors(
    db: Session,
    *,
    symbols: list[str] | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, Any]:
    resolved_symbols = resolve_factor_symbols(db, symbols)
    results: list[dict[str, Any]] = []
    for symbol in resolved_symbols:
        bars = load_clean_bars(db, symbol=symbol, start_date=start_date, end_date=end_date)
        try:
            rows = build_factor_rows(symbol, bars)
            upsert_factor_rows(db, rows)
            db.commit()
            results.append({"symbol": symbol, "factor_rows": len(rows), "status": "success", "message": None})
        except Exception as exc:  # noqa: BLE001 - per-symbol failure keeps batch calculation resilient.
            db.rollback()
            results.append({"symbol": symbol, "factor_rows": 0, "status": "failed", "message": str(exc)})

    return {
        "total_symbols": len(resolved_symbols),
        "success_count": sum(1 for item in results if item["status"] == "success"),
        "failed_count": sum(1 for item in results if item["status"] == "failed"),
        "total_factor_rows": sum(item["factor_rows"] for item in results),
        "results": results,
    }


def resolve_factor_symbols(db: Session, symbols: list[str] | None) -> list[str]:
    if symbols:
        return [symbol.strip() for symbol in symbols if symbol.strip()]
    return list(
        db.scalars(
            select(AssetMaster.symbol).where(AssetMaster.enabled.is_(True)).order_by(AssetMaster.symbol)
        ).all()
    )


def load_clean_bars(
    db: Session,
    *,
    symbol: str,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[MarketDataClean]:
    query = select(MarketDataClean).where(MarketDataClean.symbol == symbol).order_by(MarketDataClean.trade_date)
    if start_date:
        query = query.where(MarketDataClean.trade_date >= start_date)
    if end_date:
        query = query.where(MarketDataClean.trade_date <= end_date)
    return list(db.scalars(query).all())


def build_factor_rows(symbol: str, bars: list[MarketDataClean]) -> list[dict[str, Any]]:
    if not bars:
        raise ValueError(f"{symbol} has no clean bars")

    frame = pd.DataFrame(
        [
            {
                "trade_date": bar.trade_date,
                "close": float(bar.close) if bar.close is not None else None,
                "amount": float(bar.amount) if bar.amount is not None else None,
            }
            for bar in bars
        ]
    ).sort_values("trade_date")

    frame["ma20"] = frame["close"].rolling(20, min_periods=1).mean()
    frame["ma60"] = frame["close"].rolling(60, min_periods=1).mean()
    frame["ma120"] = frame["close"].rolling(120, min_periods=1).mean()
    frame["ma200"] = frame["close"].rolling(200, min_periods=1).mean()
    for window in (20, 60, 120, 250):
        frame[f"ret_{window}d"] = frame["close"] / frame["close"].shift(window) - 1
    daily_return = frame["close"].pct_change()
    frame["volatility_60d"] = daily_return.rolling(60, min_periods=2).std() * (252 ** 0.5)
    frame["volatility_120d"] = daily_return.rolling(120, min_periods=2).std() * (252 ** 0.5)
    frame["drawdown_120d"] = frame["close"] / frame["close"].rolling(120, min_periods=1).max() - 1
    frame["drawdown_250d"] = frame["close"] / frame["close"].rolling(250, min_periods=1).max() - 1
    frame["liquidity_20d"] = frame["amount"].rolling(20, min_periods=1).mean()

    max_liquidity = frame["liquidity_20d"].max()
    rows: list[dict[str, Any]] = []
    for item in frame.to_dict("records"):
        trend_score = score_trend(item)
        momentum_score = score_momentum(item)
        volatility_score = score_volatility(item.get("volatility_60d"))
        drawdown_score = score_drawdown(item.get("drawdown_120d"))
        liquidity_score = score_liquidity(item.get("liquidity_20d"), max_liquidity)
        premium_score = Decimal("80")
        alpha_score = weighted_alpha_score(
            trend_score=trend_score,
            momentum_score=momentum_score,
            volatility_score=volatility_score,
            drawdown_score=drawdown_score,
            liquidity_score=liquidity_score,
            premium_score=premium_score,
        )
        rows.append(
            {
                "symbol": symbol,
                "trade_date": item["trade_date"],
                "ma20": to_decimal(item.get("ma20"), 6),
                "ma60": to_decimal(item.get("ma60"), 6),
                "ma120": to_decimal(item.get("ma120"), 6),
                "ma200": to_decimal(item.get("ma200"), 6),
                "ret_20d": to_decimal(item.get("ret_20d"), 8),
                "ret_60d": to_decimal(item.get("ret_60d"), 8),
                "ret_120d": to_decimal(item.get("ret_120d"), 8),
                "ret_250d": to_decimal(item.get("ret_250d"), 8),
                "volatility_60d": to_decimal(item.get("volatility_60d"), 8),
                "volatility_120d": to_decimal(item.get("volatility_120d"), 8),
                "drawdown_120d": to_decimal(item.get("drawdown_120d"), 8),
                "drawdown_250d": to_decimal(item.get("drawdown_250d"), 8),
                "liquidity_20d": to_decimal(item.get("liquidity_20d"), 4),
                "premium_rate": None,
                "trend_score": trend_score,
                "momentum_score": momentum_score,
                "volatility_score": volatility_score,
                "drawdown_score": drawdown_score,
                "liquidity_score": liquidity_score,
                "premium_score": premium_score,
                "alpha_score": alpha_score,
            }
        )
    return rows


def upsert_factor_rows(db: Session, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    statement = insert(FactorDaily).values(rows)
    update_columns = {column: getattr(statement.excluded, column) for column in rows[0] if column not in {"symbol", "trade_date"}}
    db.execute(statement.on_conflict_do_update(index_elements=["symbol", "trade_date"], set_=update_columns))
    return len(rows)


def list_factors(db: Session, symbol: str, limit: int = 100) -> list[FactorDaily]:
    return list(
        db.scalars(
            select(FactorDaily)
            .where(FactorDaily.symbol == symbol)
            .order_by(FactorDaily.trade_date.desc())
            .limit(limit)
        ).all()
    )


def latest_factor_ranking(db: Session, trade_date: date | None = None, limit: int = 50) -> list[FactorDaily]:
    resolved_date = trade_date or db.scalar(select(FactorDaily.trade_date).order_by(FactorDaily.trade_date.desc()).limit(1))
    if resolved_date is None:
        return []
    return list(
        db.scalars(
            select(FactorDaily)
            .where(FactorDaily.trade_date == resolved_date)
            .order_by(FactorDaily.alpha_score.desc().nullslast())
            .limit(limit)
        ).all()
    )


def score_trend(row: dict[str, Any]) -> Decimal:
    close = row.get("close")
    if pd.isna(close):
        return Decimal("0")
    score = Decimal("0")
    for ma_key, points in (("ma20", 25), ("ma60", 25), ("ma120", 25), ("ma200", 25)):
        ma_value = row.get(ma_key)
        if not pd.isna(ma_value) and close >= ma_value:
            score += Decimal(points)
    return score


def score_momentum(row: dict[str, Any]) -> Decimal:
    scores = [score_return(row.get(key)) for key in ("ret_20d", "ret_60d", "ret_120d", "ret_250d")]
    return sum(scores, Decimal("0")) / Decimal(len(scores))


def score_return(value: Any) -> Decimal:
    if value is None or pd.isna(value):
        return Decimal("50")
    value_decimal = Decimal(str(value))
    if value_decimal >= Decimal("0.10"):
        return Decimal("100")
    if value_decimal >= Decimal("0.03"):
        return Decimal("80")
    if value_decimal >= Decimal("0"):
        return Decimal("60")
    if value_decimal >= Decimal("-0.05"):
        return Decimal("40")
    return Decimal("20")


def score_volatility(value: Any) -> Decimal:
    if value is None or pd.isna(value):
        return Decimal("50")
    value_decimal = Decimal(str(value))
    if value_decimal <= Decimal("0.15"):
        return Decimal("100")
    if value_decimal <= Decimal("0.25"):
        return Decimal("80")
    if value_decimal <= Decimal("0.35"):
        return Decimal("60")
    if value_decimal <= Decimal("0.50"):
        return Decimal("40")
    return Decimal("20")


def score_drawdown(value: Any) -> Decimal:
    if value is None or pd.isna(value):
        return Decimal("50")
    value_decimal = Decimal(str(value))
    if value_decimal >= Decimal("-0.05"):
        return Decimal("100")
    if value_decimal >= Decimal("-0.10"):
        return Decimal("80")
    if value_decimal >= Decimal("-0.20"):
        return Decimal("60")
    return Decimal("20")


def score_liquidity(value: Any, max_liquidity: Any) -> Decimal:
    if value is None or max_liquidity is None or pd.isna(value) or pd.isna(max_liquidity) or max_liquidity <= 0:
        return Decimal("50")
    ratio = Decimal(str(value)) / Decimal(str(max_liquidity))
    return min(Decimal("100"), max(Decimal("20"), (ratio * Decimal("100")).quantize(Decimal("0.0001"))))


def weighted_alpha_score(**scores: Decimal) -> Decimal:
    total = sum(scores[key] * weight for key, weight in FACTOR_WEIGHTS.items())
    return total.quantize(Decimal("0.0001"))


def to_decimal(value: Any, places: int) -> Decimal | None:
    if value is None or pd.isna(value):
        return None
    quant = Decimal("1").scaleb(-places)
    return Decimal(str(value)).quantize(quant)

