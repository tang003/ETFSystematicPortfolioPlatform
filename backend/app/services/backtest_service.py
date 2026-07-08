from datetime import date
from decimal import Decimal
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.asset import AssetMaster
from app.models.backtest import BacktestEquityCurve, BacktestMetrics, BacktestRun, BacktestTrade
from app.models.market_data import MarketDataClean


def run_backtest(
    db: Session,
    *,
    strategy_code: str,
    name: str | None,
    symbols: list[str] | None,
    start_date: date,
    end_date: date,
    initial_cash: Decimal,
    monthly_contribution: Decimal,
    fee_rate: Decimal,
    slippage_rate: Decimal,
) -> dict[str, Any]:
    resolved_symbols = resolve_backtest_symbols(db, symbols)
    price_frame = load_price_frame(db, resolved_symbols, start_date, end_date)
    if price_frame.empty:
        raise ValueError("No clean market data available for backtest")

    backtest_run = BacktestRun(
        strategy_code=strategy_code,
        strategy_version="0.1.0",
        name=name or f"{strategy_code}-{start_date}-{end_date}",
        start_date=start_date,
        end_date=end_date,
        initial_cash=initial_cash,
        monthly_contribution=monthly_contribution,
        fee_rate=fee_rate,
        slippage_rate=slippage_rate,
        config={"symbols": resolved_symbols, "mode": "equal_weight_buy_and_hold"},
        status="success",
    )
    db.add(backtest_run)
    db.flush()

    equity_rows, trade_rows, metrics = simulate_equal_weight_buy_and_hold(
        backtest_id=backtest_run.id,
        price_frame=price_frame,
        initial_cash=initial_cash,
        monthly_contribution=monthly_contribution,
        fee_rate=fee_rate,
        slippage_rate=slippage_rate,
    )
    db.add_all(equity_rows)
    db.add_all(trade_rows)
    db.add_all(build_metric_rows(backtest_run.id, metrics))
    db.commit()

    return {
        "backtest_id": backtest_run.id,
        "strategy_code": strategy_code,
        "start_date": start_date,
        "end_date": end_date,
        "symbols": resolved_symbols,
        "equity_points": len(equity_rows),
        "trade_count": len(trade_rows),
        "metrics": metrics,
        "status": "success",
    }


def resolve_backtest_symbols(db: Session, symbols: list[str] | None) -> list[str]:
    if symbols:
        return [symbol.strip() for symbol in symbols if symbol.strip()]
    return list(
        db.scalars(
            select(AssetMaster.symbol)
            .where(AssetMaster.enabled.is_(True))
            .where(AssetMaster.asset_class == "equity")
            .order_by(AssetMaster.symbol)
            .limit(2)
        ).all()
    )


def load_price_frame(db: Session, symbols: list[str], start_date: date, end_date: date) -> pd.DataFrame:
    bars = db.scalars(
        select(MarketDataClean)
        .where(MarketDataClean.symbol.in_(symbols))
        .where(MarketDataClean.trade_date >= start_date)
        .where(MarketDataClean.trade_date <= end_date)
        .order_by(MarketDataClean.trade_date)
    ).all()
    frame = pd.DataFrame(
        [{"trade_date": bar.trade_date, "symbol": bar.symbol, "close": float(bar.close)} for bar in bars if bar.close]
    )
    if frame.empty:
        return frame
    return frame.pivot(index="trade_date", columns="symbol", values="close").dropna(how="any")


def simulate_equal_weight_buy_and_hold(
    *,
    backtest_id: int,
    price_frame: pd.DataFrame,
    initial_cash: Decimal,
    monthly_contribution: Decimal,
    fee_rate: Decimal,
    slippage_rate: Decimal,
) -> tuple[list[BacktestEquityCurve], list[BacktestTrade], dict[str, Decimal]]:
    symbols = list(price_frame.columns)
    first_date = price_frame.index[0]
    first_prices = price_frame.loc[first_date]
    investable_cash = initial_cash
    per_symbol_cash = investable_cash / Decimal(len(symbols))
    positions: dict[str, Decimal] = {}
    cash = Decimal("0")
    trades: list[BacktestTrade] = []

    for symbol in symbols:
        price = Decimal(str(first_prices[symbol]))
        cost_rate = Decimal("1") + fee_rate + slippage_rate
        quantity = (per_symbol_cash / (price * cost_rate)).quantize(Decimal("0.000001"))
        amount = (quantity * price).quantize(Decimal("0.0001"))
        fee = (amount * fee_rate).quantize(Decimal("0.0001"))
        slippage = (amount * slippage_rate).quantize(Decimal("0.0001"))
        positions[symbol] = quantity
        cash += per_symbol_cash - amount - fee - slippage
        trades.append(
            BacktestTrade(
                backtest_id=backtest_id,
                trade_date=first_date,
                symbol=symbol,
                action="BUY",
                price=price,
                quantity=quantity,
                amount=amount,
                fee=fee,
                slippage=slippage,
                reason="Initial equal weight allocation",
            )
        )

    equity_rows: list[BacktestEquityCurve] = []
    previous_equity: Decimal | None = None
    high_watermark = Decimal("0")
    last_month = first_date.month
    for trade_date, row in price_frame.iterrows():
        if trade_date.month != last_month and monthly_contribution > 0:
            cash += monthly_contribution
            last_month = trade_date.month

        position_value = sum(positions[symbol] * Decimal(str(row[symbol])) for symbol in symbols)
        total_equity = (position_value + cash).quantize(Decimal("0.0001"))
        high_watermark = max(high_watermark, total_equity)
        drawdown = Decimal("0") if high_watermark == 0 else (total_equity / high_watermark - Decimal("1"))
        daily_return = Decimal("0") if previous_equity in (None, Decimal("0")) else (total_equity / previous_equity - Decimal("1"))
        equity_rows.append(
            BacktestEquityCurve(
                backtest_id=backtest_id,
                trade_date=trade_date,
                total_equity=total_equity,
                cash=cash.quantize(Decimal("0.0001")),
                drawdown=drawdown.quantize(Decimal("0.00000001")),
                daily_return=daily_return.quantize(Decimal("0.00000001")),
            )
        )
        previous_equity = total_equity

    metrics = calculate_backtest_metrics(equity_rows, trades, initial_cash)
    return equity_rows, trades, metrics


def calculate_backtest_metrics(
    equity_rows: list[BacktestEquityCurve],
    trades: list[BacktestTrade],
    initial_cash: Decimal,
) -> dict[str, Decimal]:
    if not equity_rows:
        return {}
    first = Decimal(equity_rows[0].total_equity)
    last = Decimal(equity_rows[-1].total_equity)
    cumulative_return = last / initial_cash - Decimal("1")
    days = max(1, (equity_rows[-1].trade_date - equity_rows[0].trade_date).days)
    annualized_return = Decimal(str((float(last / first) ** (365 / days)) - 1))
    max_drawdown = min(Decimal(row.drawdown) for row in equity_rows)
    returns = [float(row.daily_return or 0) for row in equity_rows[1:]]
    volatility = Decimal(str(pd.Series(returns).std() * (252 ** 0.5))) if returns else Decimal("0")
    sharpe = Decimal("0") if volatility == 0 else annualized_return / volatility
    return {
        "cumulative_return": cumulative_return.quantize(Decimal("0.00000001")),
        "annualized_return": annualized_return.quantize(Decimal("0.00000001")),
        "max_drawdown": max_drawdown.quantize(Decimal("0.00000001")),
        "volatility": volatility.quantize(Decimal("0.00000001")),
        "sharpe_ratio": sharpe.quantize(Decimal("0.00000001")),
        "trade_count": Decimal(len(trades)),
    }


def build_metric_rows(backtest_id: int, metrics: dict[str, Decimal]) -> list[BacktestMetrics]:
    rows: list[BacktestMetrics] = []
    for index, (name, value) in enumerate(metrics.items(), start=1):
        rows.append(
            BacktestMetrics(
                backtest_id=backtest_id,
                metric_name=name,
                metric_value=value,
                metric_unit="count" if name == "trade_count" else "ratio",
                sort_order=index,
            )
        )
    return rows


def list_backtest_runs(db: Session, limit: int = 100) -> list[BacktestRun]:
    return list(db.scalars(select(BacktestRun).order_by(BacktestRun.created_at.desc()).limit(limit)).all())


def get_backtest_run(db: Session, backtest_id: int) -> BacktestRun | None:
    return db.get(BacktestRun, backtest_id)


def list_equity_curve(db: Session, backtest_id: int) -> list[BacktestEquityCurve]:
    return list(
        db.scalars(
            select(BacktestEquityCurve)
            .where(BacktestEquityCurve.backtest_id == backtest_id)
            .order_by(BacktestEquityCurve.trade_date)
        ).all()
    )


def list_backtest_trades(db: Session, backtest_id: int) -> list[BacktestTrade]:
    return list(
        db.scalars(
            select(BacktestTrade).where(BacktestTrade.backtest_id == backtest_id).order_by(BacktestTrade.trade_date)
        ).all()
    )


def list_backtest_metrics(db: Session, backtest_id: int) -> list[BacktestMetrics]:
    return list(
        db.scalars(
            select(BacktestMetrics)
            .where(BacktestMetrics.backtest_id == backtest_id)
            .order_by(BacktestMetrics.sort_order)
        ).all()
    )

