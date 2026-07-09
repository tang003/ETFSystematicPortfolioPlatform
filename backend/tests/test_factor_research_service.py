from datetime import date, timedelta

import pandas as pd

from app.services.factor_research_service import (
    build_factor_forward_return_sample,
    build_ic_metrics,
    build_quantile_returns,
)


def test_build_factor_research_sample_and_ic_metrics() -> None:
    dates = [date(2026, 1, 1) + timedelta(days=i) for i in range(4)]
    factor_frame = pd.DataFrame(
        [
            {"trade_date": dates[0], "symbol": "A", "trend_score": 90, "momentum_score": 80, "volatility_score": 50, "drawdown_score": 50, "liquidity_score": 50, "premium_score": 80, "alpha_score": 90},
            {"trade_date": dates[0], "symbol": "B", "trend_score": 20, "momentum_score": 30, "volatility_score": 50, "drawdown_score": 50, "liquidity_score": 50, "premium_score": 80, "alpha_score": 20},
            {"trade_date": dates[1], "symbol": "A", "trend_score": 95, "momentum_score": 85, "volatility_score": 50, "drawdown_score": 50, "liquidity_score": 50, "premium_score": 80, "alpha_score": 95},
            {"trade_date": dates[1], "symbol": "B", "trend_score": 10, "momentum_score": 20, "volatility_score": 50, "drawdown_score": 50, "liquidity_score": 50, "premium_score": 80, "alpha_score": 10},
        ]
    )
    price_frame = pd.DataFrame(
        [
            {"trade_date": dates[0], "symbol": "A", "close": 10},
            {"trade_date": dates[1], "symbol": "A", "close": 11},
            {"trade_date": dates[2], "symbol": "A", "close": 12},
            {"trade_date": dates[0], "symbol": "B", "close": 10},
            {"trade_date": dates[1], "symbol": "B", "close": 9},
            {"trade_date": dates[2], "symbol": "B", "close": 8},
        ]
    )

    sample = build_factor_forward_return_sample(factor_frame, price_frame, forward_days=1)
    metrics = build_ic_metrics(sample)

    alpha_metric = next(item for item in metrics if item["factor_name"] == "alpha_score")
    assert len(sample) == 4
    assert alpha_metric["observations"] == 2
    assert alpha_metric["mean_ic"] > 0
    assert alpha_metric["effective"] is True


def test_build_quantile_returns_groups_forward_returns() -> None:
    sample = pd.DataFrame(
        [
            {"trade_date": date(2026, 1, 1), "alpha_score": 10, "trend_score": 10, "momentum_score": 10, "volatility_score": 10, "drawdown_score": 10, "liquidity_score": 10, "premium_score": 10, "forward_return": -0.02},
            {"trade_date": date(2026, 1, 1), "alpha_score": 50, "trend_score": 50, "momentum_score": 50, "volatility_score": 50, "drawdown_score": 50, "liquidity_score": 50, "premium_score": 50, "forward_return": 0.01},
            {"trade_date": date(2026, 1, 1), "alpha_score": 90, "trend_score": 90, "momentum_score": 90, "volatility_score": 90, "drawdown_score": 90, "liquidity_score": 90, "premium_score": 90, "forward_return": 0.05},
        ]
    )

    rows = build_quantile_returns(sample, quantiles=3)
    alpha_rows = [item for item in rows if item["factor_name"] == "alpha_score"]

    assert len(alpha_rows) == 3
    assert alpha_rows[-1]["mean_forward_return"] > alpha_rows[0]["mean_forward_return"]
