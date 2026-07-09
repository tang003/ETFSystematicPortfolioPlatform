from datetime import date
from decimal import Decimal
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.factor import FactorDaily
from app.models.market_data import MarketDataClean

RESEARCH_FACTORS = [
    "trend_score",
    "momentum_score",
    "volatility_score",
    "drawdown_score",
    "liquidity_score",
    "premium_score",
    "alpha_score",
]


def analyze_factor_research(
    db: Session,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    forward_days: int = 20,
    quantiles: int = 3,
) -> dict[str, Any]:
    factor_frame = load_factor_frame(db, start_date=start_date, end_date=end_date)
    price_frame = load_price_frame(db, start_date=start_date, end_date=end_date)
    sample = build_factor_forward_return_sample(factor_frame, price_frame, forward_days=forward_days)

    ic_metrics = build_ic_metrics(sample)
    correlations = build_factor_correlations(sample)
    quantile_returns = build_quantile_returns(sample, quantiles=quantiles)

    return {
        "start_date": start_date,
        "end_date": end_date,
        "forward_days": forward_days,
        "quantiles": quantiles,
        "factor_count": len(RESEARCH_FACTORS),
        "sample_count": int(len(sample)),
        "ic_metrics": ic_metrics,
        "correlations": correlations,
        "quantile_returns": quantile_returns,
    }


def load_factor_frame(db: Session, *, start_date: date | None, end_date: date | None) -> pd.DataFrame:
    query = select(FactorDaily).order_by(FactorDaily.trade_date, FactorDaily.symbol)
    if start_date:
        query = query.where(FactorDaily.trade_date >= start_date)
    if end_date:
        query = query.where(FactorDaily.trade_date <= end_date)
    rows = db.scalars(query).all()
    frame = pd.DataFrame(
        [
            {
                "trade_date": row.trade_date,
                "symbol": row.symbol,
                **{factor: float(getattr(row, factor)) if getattr(row, factor) is not None else None for factor in RESEARCH_FACTORS},
            }
            for row in rows
        ]
    )
    return frame


def load_price_frame(db: Session, *, start_date: date | None, end_date: date | None) -> pd.DataFrame:
    query = select(MarketDataClean).order_by(MarketDataClean.symbol, MarketDataClean.trade_date)
    if start_date:
        query = query.where(MarketDataClean.trade_date >= start_date)
    if end_date:
        query = query.where(MarketDataClean.trade_date <= end_date)
    rows = db.scalars(query).all()
    return pd.DataFrame(
        [
            {"trade_date": row.trade_date, "symbol": row.symbol, "close": float(row.close)}
            for row in rows
            if row.close is not None
        ]
    )


def build_factor_forward_return_sample(
    factor_frame: pd.DataFrame,
    price_frame: pd.DataFrame,
    *,
    forward_days: int,
) -> pd.DataFrame:
    if factor_frame.empty or price_frame.empty:
        return pd.DataFrame()
    prices = price_frame.sort_values(["symbol", "trade_date"]).copy()
    prices["future_close"] = prices.groupby("symbol")["close"].shift(-forward_days)
    prices["forward_return"] = prices["future_close"] / prices["close"] - 1
    sample = factor_frame.merge(prices[["symbol", "trade_date", "forward_return"]], on=["symbol", "trade_date"], how="inner")
    return sample.dropna(subset=["forward_return"])


def build_ic_metrics(sample: pd.DataFrame) -> list[dict[str, Any]]:
    if sample.empty:
        return [empty_ic_metric(factor) for factor in RESEARCH_FACTORS]
    rows: list[dict[str, Any]] = []
    for factor in RESEARCH_FACTORS:
        daily = []
        for _, group in sample[["trade_date", factor, "forward_return"]].dropna().groupby("trade_date"):
            if len(group) < 2:
                continue
            if group[factor].nunique() < 2 or group["forward_return"].nunique() < 2:
                continue
            ic = group[factor].corr(group["forward_return"], method="pearson")
            rank_ic = group[factor].rank(method="average").corr(group["forward_return"].rank(method="average"), method="pearson")
            if pd.notna(ic) and pd.notna(rank_ic):
                daily.append({"ic": ic, "rank_ic": rank_ic})
        if not daily:
            rows.append(empty_ic_metric(factor))
            continue
        daily_frame = pd.DataFrame(daily)
        mean_ic = float(daily_frame["ic"].mean())
        mean_rank_ic = float(daily_frame["rank_ic"].mean())
        positive_ratio = float((daily_frame["ic"] > 0).mean())
        rows.append(
            {
                "factor_name": factor,
                "observations": int(len(daily_frame)),
                "mean_ic": to_decimal(mean_ic, 8),
                "mean_rank_ic": to_decimal(mean_rank_ic, 8),
                "positive_ic_ratio": to_decimal(positive_ratio, 8),
                "effective": abs(mean_ic) >= 0.03 or abs(mean_rank_ic) >= 0.03,
            }
        )
    return rows


def build_factor_correlations(sample: pd.DataFrame) -> list[dict[str, Any]]:
    if sample.empty:
        return []
    corr = sample[RESEARCH_FACTORS].corr(method="pearson")
    rows: list[dict[str, Any]] = []
    for factor_x in RESEARCH_FACTORS:
        for factor_y in RESEARCH_FACTORS:
            value = corr.loc[factor_x, factor_y]
            rows.append(
                {
                    "factor_x": factor_x,
                    "factor_y": factor_y,
                    "correlation": to_decimal(float(value), 8) if pd.notna(value) else None,
                }
            )
    return rows


def build_quantile_returns(sample: pd.DataFrame, *, quantiles: int) -> list[dict[str, Any]]:
    if sample.empty:
        return []
    rows: list[dict[str, Any]] = []
    for factor in RESEARCH_FACTORS:
        factor_sample = sample[["trade_date", factor, "forward_return"]].dropna().copy()
        if factor_sample.empty:
            continue
        quantile_frames = []
        for _, group in factor_sample.groupby("trade_date"):
            if len(group) < quantiles:
                continue
            try:
                group = group.copy()
                group["quantile"] = pd.qcut(group[factor].rank(method="first"), quantiles, labels=False) + 1
                quantile_frames.append(group)
            except ValueError:
                continue
        if not quantile_frames:
            continue
        quantile_sample = pd.concat(quantile_frames)
        grouped = quantile_sample.groupby("quantile")["forward_return"]
        for quantile, values in grouped:
            rows.append(
                {
                    "factor_name": factor,
                    "quantile": int(quantile),
                    "mean_forward_return": to_decimal(float(values.mean()), 8),
                    "observations": int(values.count()),
                }
            )
    return rows


def empty_ic_metric(factor_name: str) -> dict[str, Any]:
    return {
        "factor_name": factor_name,
        "observations": 0,
        "mean_ic": None,
        "mean_rank_ic": None,
        "positive_ic_ratio": None,
        "effective": False,
    }


def to_decimal(value: float, places: int) -> Decimal | None:
    if pd.isna(value):
        return None
    quant = Decimal("1").scaleb(-places)
    return Decimal(str(value)).quantize(quant)
