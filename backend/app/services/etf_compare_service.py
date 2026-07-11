from datetime import date, timedelta
from decimal import Decimal
from math import sqrt
from statistics import mean, stdev

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.asset import AssetMaster
from app.models.market_data import MarketDataClean


def compare_etfs(
    db: Session,
    *,
    symbols: list[str],
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict:
    resolved_end = end_date or date.today()
    resolved_start = start_date or (resolved_end - timedelta(days=365))
    cleaned_symbols = dedupe_symbols(symbols)
    asset_meta = load_asset_meta(db, cleaned_symbols)
    bars_by_symbol = {
        symbol: load_clean_bars(db, symbol=symbol, start_date=resolved_start, end_date=resolved_end)
        for symbol in cleaned_symbols
    }
    normalized_series = {symbol: build_normalized_series(rows) for symbol, rows in bars_by_symbol.items()}
    return {
        "start_date": resolved_start,
        "end_date": resolved_end,
        "metrics": [
            build_compare_metric(symbol, bars_by_symbol[symbol], asset_meta.get(symbol))
            for symbol in cleaned_symbols
        ],
        "normalized_series": normalized_series,
        "correlations": build_correlations(bars_by_symbol),
    }


def score_etf_tradability(
    db: Session,
    *,
    symbols: list[str],
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict]:
    resolved_end = end_date or date.today()
    resolved_start = start_date or (resolved_end - timedelta(days=365))
    cleaned_symbols = dedupe_symbols(symbols)
    asset_meta = load_asset_meta(db, cleaned_symbols)
    return [
        build_compare_metric(
            symbol,
            load_clean_bars(db, symbol=symbol, start_date=resolved_start, end_date=resolved_end),
            asset_meta.get(symbol),
        )
        for symbol in cleaned_symbols
    ]


def dedupe_symbols(symbols: list[str]) -> list[str]:
    resolved: list[str] = []
    seen: set[str] = set()
    for symbol in symbols:
        cleaned = symbol.strip()
        if cleaned and cleaned not in seen:
            resolved.append(cleaned)
            seen.add(cleaned)
    return resolved


def load_asset_meta(db: Session, symbols: list[str]) -> dict[str, AssetMaster]:
    if not symbols:
        return {}
    rows = db.scalars(select(AssetMaster).where(AssetMaster.symbol.in_(symbols))).all()
    return {row.symbol: row for row in rows}


def load_clean_bars(db: Session, *, symbol: str, start_date: date, end_date: date) -> list[MarketDataClean]:
    return list(
        db.scalars(
            select(MarketDataClean)
            .where(
                MarketDataClean.symbol == symbol,
                MarketDataClean.trade_date >= start_date,
                MarketDataClean.trade_date <= end_date,
                MarketDataClean.close.is_not(None),
            )
            .order_by(MarketDataClean.trade_date)
        ).all()
    )


def build_compare_metric(symbol: str, rows: list[MarketDataClean], asset: AssetMaster | None) -> dict:
    closes = [Decimal(row.close) for row in rows if row.close and row.close > 0]
    returns = daily_returns(closes)
    avg_amount = average_decimal([row.amount for row in rows if row.amount is not None])
    total_return = (closes[-1] / closes[0] - Decimal("1")) if len(closes) >= 2 else None
    days = max((rows[-1].trade_date - rows[0].trade_date).days, 1) if len(rows) >= 2 else 1
    annualized_return = annualize_return(total_return, days) if total_return is not None else None
    annualized_volatility = Decimal(str(stdev(returns) * sqrt(252))) if len(returns) >= 2 else None
    drawdown = max_drawdown(closes) if closes else None
    score, level, notes = tradability_score(rows, avg_amount)
    return {
        "symbol": symbol,
        "name": asset.name if asset else None,
        "asset_class": asset.asset_class if asset else None,
        "asset_region": asset.asset_region if asset else None,
        "risk_level": asset.risk_level if asset else None,
        "first_trade_date": rows[0].trade_date if rows else None,
        "latest_trade_date": rows[-1].trade_date if rows else None,
        "latest_close": closes[-1] if closes else None,
        "bars": len(rows),
        "total_return": quantize_rate(total_return),
        "annualized_return": quantize_rate(annualized_return),
        "annualized_volatility": quantize_rate(annualized_volatility),
        "max_drawdown": quantize_rate(drawdown),
        "average_amount": avg_amount.quantize(Decimal("0.01")) if avg_amount is not None else None,
        "tradability_score": score,
        "tradability_level": level,
        "tradability_notes": notes,
    }


def build_normalized_series(rows: list[MarketDataClean]) -> list[dict]:
    closes = [(row.trade_date, Decimal(row.close)) for row in rows if row.close and row.close > 0]
    if not closes:
        return []
    base = closes[0][1]
    return [{"trade_date": trade_date, "value": (close / base * Decimal("100")).quantize(Decimal("0.0001"))} for trade_date, close in closes]


def daily_returns(closes: list[Decimal]) -> list[float]:
    return [float(closes[index] / closes[index - 1] - Decimal("1")) for index in range(1, len(closes))]


def annualize_return(total_return: Decimal, days: int) -> Decimal:
    return Decimal(str((1 + float(total_return)) ** (365 / days) - 1))


def max_drawdown(closes: list[Decimal]) -> Decimal:
    peak = closes[0]
    worst = Decimal("0")
    for close in closes:
        peak = max(peak, close)
        if peak > 0:
            worst = min(worst, close / peak - Decimal("1"))
    return worst


def average_decimal(values: list[Decimal | None]) -> Decimal | None:
    cleaned = [Decimal(value) for value in values if value is not None]
    if not cleaned:
        return None
    return sum(cleaned) / Decimal(len(cleaned))


def tradability_score(rows: list[MarketDataClean], average_amount: Decimal | None) -> tuple[int, str, list[str]]:
    score = 100
    notes: list[str] = []
    if len(rows) < 60:
        score -= 25
        notes.append("历史样本少于 60 个交易日")
    elif len(rows) < 120:
        score -= 10
        notes.append("历史样本少于 120 个交易日")
    if average_amount is None:
        score -= 35
        notes.append("缺少成交额数据")
    elif average_amount < Decimal("10000000"):
        score -= 35
        notes.append("近似日均成交额低于 1000 万")
    elif average_amount < Decimal("50000000"):
        score -= 15
        notes.append("近似日均成交额低于 5000 万")
    zero_volume_days = sum(1 for row in rows if row.volume is not None and row.volume <= 0)
    if rows and zero_volume_days / len(rows) > 0.05:
        score -= 20
        notes.append("存在较多零成交量日期")
    score = max(0, min(100, score))
    if score >= 80:
        return score, "优秀", notes or ["成交活跃度和历史样本较好"]
    if score >= 60:
        return score, "可用", notes or ["可交易性基本可用"]
    if score >= 40:
        return score, "谨慎", notes
    return score, "较弱", notes


def build_correlations(bars_by_symbol: dict[str, list[MarketDataClean]]) -> list[dict]:
    returns_by_symbol = {symbol: returns_by_date(rows) for symbol, rows in bars_by_symbol.items()}
    symbols = list(bars_by_symbol)
    cells: list[dict] = []
    for symbol_x in symbols:
        for symbol_y in symbols:
            cells.append(
                {
                    "symbol_x": symbol_x,
                    "symbol_y": symbol_y,
                    "correlation": quantize_rate(correlation(returns_by_symbol[symbol_x], returns_by_symbol[symbol_y])),
                }
            )
    return cells


def returns_by_date(rows: list[MarketDataClean]) -> dict[date, float]:
    values: dict[date, float] = {}
    previous: Decimal | None = None
    for row in rows:
        if row.close is None or row.close <= 0:
            continue
        close = Decimal(row.close)
        if previous is not None and previous > 0:
            values[row.trade_date] = float(close / previous - Decimal("1"))
        previous = close
    return values


def correlation(left: dict[date, float], right: dict[date, float]) -> Decimal | None:
    common_dates = sorted(set(left).intersection(right))
    if len(common_dates) < 3:
        return None
    xs = [left[item] for item in common_dates]
    ys = [right[item] for item in common_dates]
    mean_x = mean(xs)
    mean_y = mean(ys)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
    denominator_x = sum((x - mean_x) ** 2 for x in xs)
    denominator_y = sum((y - mean_y) ** 2 for y in ys)
    if denominator_x <= 0 or denominator_y <= 0:
        return None
    return Decimal(str(numerator / sqrt(denominator_x * denominator_y)))


def quantize_rate(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return value.quantize(Decimal("0.000001"))
