from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class BacktestRunRequest(BaseModel):
    strategy_code: str = Field(default="equal_weight_buy_and_hold")
    name: str | None = None
    symbols: list[str] | None = None
    start_date: date
    end_date: date
    initial_cash: Decimal = Field(default=Decimal("10000"), gt=0)
    monthly_contribution: Decimal = Field(default=Decimal("0"), ge=0)
    fee_rate: Decimal = Field(default=Decimal("0.001"), ge=0)
    slippage_rate: Decimal = Field(default=Decimal("0.001"), ge=0)


class BacktestRunResponse(BaseModel):
    backtest_id: int
    strategy_code: str
    start_date: date
    end_date: date
    symbols: list[str]
    equity_points: int
    trade_count: int
    metrics: dict[str, Decimal]
    status: str


class BacktestRunRead(BaseModel):
    id: int
    strategy_code: str
    strategy_version: str | None
    name: str | None
    start_date: date | None
    end_date: date | None
    initial_cash: Decimal | None
    monthly_contribution: Decimal | None
    fee_rate: Decimal | None
    slippage_rate: Decimal | None
    config: dict | None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BacktestEquityCurveRead(BaseModel):
    backtest_id: int | None
    trade_date: date
    total_equity: Decimal | None
    cash: Decimal | None
    drawdown: Decimal | None
    daily_return: Decimal | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BacktestTradeRead(BaseModel):
    backtest_id: int | None
    trade_date: date
    symbol: str
    action: str
    price: Decimal | None
    quantity: Decimal | None
    amount: Decimal | None
    fee: Decimal | None
    slippage: Decimal | None
    reason: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BacktestMetricRead(BaseModel):
    backtest_id: int | None
    metric_name: str
    metric_value: Decimal | None
    metric_unit: str | None
    sort_order: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

