from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.asset_schema import AssetRead
from app.schemas.etf_compare_schema import EtfCompareMetric
from app.schemas.factor_schema import FactorRead
from app.schemas.market_schema import MarketBarRead


class EtfDetailCurvePoint(BaseModel):
    trade_date: date
    close: Decimal
    normalized_value: Decimal
    drawdown: Decimal
    amount: Decimal | None = None


class EtfDetailResponse(BaseModel):
    symbol: str
    asset: AssetRead | None = None
    metric: EtfCompareMetric
    latest_factor: FactorRead | None = None
    curve: list[EtfDetailCurvePoint]
    recent_bars: list[MarketBarRead]
