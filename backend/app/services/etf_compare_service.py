from datetime import date, timedelta
from decimal import Decimal
from math import sqrt
from statistics import mean, stdev

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.asset import AssetMaster
from app.models.market_data import MarketDataClean
from app.services.market_service import resolve_symbols


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
    bars_by_symbol = load_clean_bars_for_symbols(
        db,
        symbols=cleaned_symbols,
        start_date=resolved_start,
        end_date=resolved_end,
    )
    return [
        build_compare_metric(
            symbol,
            bars_by_symbol.get(symbol, []),
            asset_meta.get(symbol),
        )
        for symbol in cleaned_symbols
    ]


def screen_etfs(
    db: Session,
    *,
    scope: str = "enabled",
    symbols: list[str] | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 50,
    min_bars: int = 120,
    min_tradability_score: int = 40,
    min_buy_score: int = 0,
    asset_class: str | None = None,
    asset_region: str | None = None,
) -> dict:
    resolved_end = end_date or date.today()
    resolved_start = start_date or (resolved_end - timedelta(days=365))
    resolved_symbols = resolve_screen_symbols(db, scope=scope, symbols=symbols)
    asset_meta = load_asset_meta(db, resolved_symbols)
    bars_by_symbol = load_clean_bars_for_symbols(
        db,
        symbols=resolved_symbols,
        start_date=resolved_start,
        end_date=resolved_end,
    )
    metrics = [
        build_compare_metric(symbol, bars_by_symbol.get(symbol, []), asset_meta.get(symbol))
        for symbol in resolved_symbols
    ]
    filtered = [
        item
        for item in metrics
        if item["bars"] >= min_bars
        and item["tradability_score"] >= min_tradability_score
        and item["buy_score"] >= min_buy_score
        and (asset_class is None or item["asset_class"] == asset_class)
        and (asset_region is None or item["asset_region"] == asset_region)
    ]
    filtered.sort(
        key=lambda item: (
            item["buy_score"],
            item["tradability_score"],
            decimal_sort_value(item["sharpe_ratio"]),
            decimal_sort_value(item["annualized_return"]),
        ),
        reverse=True,
    )
    return {
        "start_date": resolved_start,
        "end_date": resolved_end,
        "scope": scope,
        "total_candidates": len(metrics),
        "returned": min(len(filtered), limit),
        "metrics": filtered[:limit],
    }


def dedupe_symbols(symbols: list[str]) -> list[str]:
    resolved: list[str] = []
    seen: set[str] = set()
    for symbol in symbols:
        cleaned = symbol.strip()
        if cleaned and cleaned not in seen:
            resolved.append(cleaned)
            seen.add(cleaned)
    return resolved


def resolve_screen_symbols(db: Session, *, scope: str, symbols: list[str] | None) -> list[str]:
    normalized_scope = (scope or "enabled").strip().lower()
    if normalized_scope == "custom":
        return dedupe_symbols(symbols or [])
    return resolve_symbols(db, dedupe_symbols(symbols or []) or None, sync_scope=normalized_scope)


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


def load_clean_bars_for_symbols(
    db: Session,
    *,
    symbols: list[str],
    start_date: date,
    end_date: date,
) -> dict[str, list[MarketDataClean]]:
    if not symbols:
        return {}
    rows = list(
        db.scalars(
            select(MarketDataClean)
            .where(
                MarketDataClean.symbol.in_(symbols),
                MarketDataClean.trade_date >= start_date,
                MarketDataClean.trade_date <= end_date,
                MarketDataClean.close.is_not(None),
            )
            .order_by(MarketDataClean.symbol, MarketDataClean.trade_date)
        ).all()
    )
    grouped = {symbol: [] for symbol in symbols}
    for row in rows:
        grouped.setdefault(row.symbol, []).append(row)
    return grouped


def build_compare_metric(symbol: str, rows: list[MarketDataClean], asset: AssetMaster | None) -> dict:
    closes = [Decimal(row.close) for row in rows if row.close and row.close > 0]
    returns = daily_returns(closes)
    avg_amount = average_decimal([row.amount for row in rows if row.amount is not None])
    total_return = (closes[-1] / closes[0] - Decimal("1")) if len(closes) >= 2 else None
    days = max((rows[-1].trade_date - rows[0].trade_date).days, 1) if len(rows) >= 2 else 1
    annualized_return = annualize_return(total_return, days) if total_return is not None else None
    annualized_volatility = Decimal(str(stdev(returns) * sqrt(252))) if len(returns) >= 2 else None
    downside_volatility = downside_annualized_volatility(returns)
    drawdown = max_drawdown(closes) if closes else None
    score, level, notes = tradability_score(rows, avg_amount)
    sharpe = risk_adjusted_ratio(annualized_return, annualized_volatility)
    sortino = risk_adjusted_ratio(annualized_return, downside_volatility)
    calmar = calmar_ratio(annualized_return, drawdown)
    hit_rate = positive_return_rate(returns)
    gap_ratio = estimated_gap_ratio(rows, days)
    buy_score, buy_level, buy_notes = buy_decision_score(
        bars=len(rows),
        annualized_return=annualized_return,
        annualized_volatility=annualized_volatility,
        max_drawdown_value=drawdown,
        sharpe=sharpe,
        tradability_score_value=score,
        risk_level=asset.risk_level if asset else None,
        gap_ratio=gap_ratio,
    )
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
        "downside_volatility": quantize_rate(downside_volatility),
        "max_drawdown": quantize_rate(drawdown),
        "sharpe_ratio": quantize_number(sharpe),
        "sortino_ratio": quantize_number(sortino),
        "calmar_ratio": quantize_number(calmar),
        "positive_day_rate": quantize_rate(hit_rate),
        "estimated_gap_ratio": quantize_rate(gap_ratio),
        "average_amount": avg_amount.quantize(Decimal("0.01")) if avg_amount is not None else None,
        "tradability_score": score,
        "tradability_level": level,
        "tradability_notes": notes,
        "buy_score": buy_score,
        "buy_level": buy_level,
        "buy_notes": buy_notes,
    }


def build_normalized_series(rows: list[MarketDataClean]) -> list[dict]:
    closes = [(row.trade_date, Decimal(row.close)) for row in rows if row.close and row.close > 0]
    if not closes:
        return []
    base = closes[0][1]
    return [{"trade_date": trade_date, "value": (close / base * Decimal("100")).quantize(Decimal("0.0001"))} for trade_date, close in closes]


def daily_returns(closes: list[Decimal]) -> list[float]:
    return [float(closes[index] / closes[index - 1] - Decimal("1")) for index in range(1, len(closes))]


def downside_annualized_volatility(returns: list[float]) -> Decimal | None:
    downside = [value for value in returns if value < 0]
    if len(downside) < 2:
        return None
    return Decimal(str(stdev(downside) * sqrt(252)))


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


def risk_adjusted_ratio(annualized_return: Decimal | None, annualized_volatility: Decimal | None) -> Decimal | None:
    if annualized_return is None or annualized_volatility is None or annualized_volatility <= 0:
        return None
    risk_free_rate = Decimal("0.02")
    return (annualized_return - risk_free_rate) / annualized_volatility


def calmar_ratio(annualized_return: Decimal | None, drawdown: Decimal | None) -> Decimal | None:
    if annualized_return is None or drawdown is None or drawdown >= 0:
        return None
    return annualized_return / abs(drawdown)


def positive_return_rate(returns: list[float]) -> Decimal | None:
    if not returns:
        return None
    return Decimal(sum(1 for value in returns if value > 0)) / Decimal(len(returns))


def estimated_gap_ratio(rows: list[MarketDataClean], days: int) -> Decimal | None:
    if not rows or days <= 0:
        return None
    expected_trading_days = max(int(days * 244 / 365), 1)
    missing = max(expected_trading_days - len(rows), 0)
    return Decimal(missing) / Decimal(expected_trading_days)


def buy_decision_score(
    *,
    bars: int,
    annualized_return: Decimal | None,
    annualized_volatility: Decimal | None,
    max_drawdown_value: Decimal | None,
    sharpe: Decimal | None,
    tradability_score_value: int,
    risk_level: int | None,
    gap_ratio: Decimal | None,
) -> tuple[int, str, list[str]]:
    score = 50
    notes: list[str] = []

    score += score_annualized_return(annualized_return)
    score += score_sharpe(sharpe)
    score += score_drawdown_risk(max_drawdown_value)
    score += score_volatility_risk(annualized_volatility)
    score += int((tradability_score_value - 60) * 0.25)

    if bars < 120:
        score -= 20
        notes.append("样本少于 120 个交易日，结论不稳定")
    elif bars < 250:
        score -= 8
        notes.append("样本不足 1 年，适合观察不适合重仓")

    if risk_level is not None and risk_level >= 5:
        score -= 8
        notes.append("风险等级较高，需控制仓位")
    elif risk_level is not None and risk_level <= 2:
        score += 4

    if gap_ratio is not None and gap_ratio > Decimal("0.05"):
        score -= 10
        notes.append("估算行情缺口较多，先补数据再决策")

    if tradability_score_value < 60:
        notes.append("可交易性偏弱，不适合频繁调仓")

    score = max(0, min(100, score))
    if score >= 75:
        return score, "优先候选", notes or ["收益、风险和交易性综合表现较好"]
    if score >= 60:
        return score, "可观察", notes or ["综合表现可用，建议结合持仓和估值分批观察"]
    if score >= 45:
        return score, "谨慎观察", notes or ["存在风险或交易性短板，不建议直接重仓"]
    return score, "暂不优先", notes or ["当前风险收益比不足或数据质量不足"]


def score_annualized_return(value: Decimal | None) -> int:
    if value is None:
        return -10
    if value >= Decimal("0.15"):
        return 18
    if value >= Decimal("0.08"):
        return 12
    if value >= Decimal("0.03"):
        return 5
    if value >= Decimal("0"):
        return 0
    return -12


def score_sharpe(value: Decimal | None) -> int:
    if value is None:
        return -8
    if value >= Decimal("1.2"):
        return 18
    if value >= Decimal("0.8"):
        return 12
    if value >= Decimal("0.4"):
        return 5
    if value >= Decimal("0"):
        return 0
    return -10


def score_drawdown_risk(value: Decimal | None) -> int:
    if value is None:
        return -8
    if value >= Decimal("-0.08"):
        return 12
    if value >= Decimal("-0.15"):
        return 6
    if value >= Decimal("-0.25"):
        return 0
    if value >= Decimal("-0.35"):
        return -8
    return -16


def score_volatility_risk(value: Decimal | None) -> int:
    if value is None:
        return -5
    if value <= Decimal("0.15"):
        return 10
    if value <= Decimal("0.25"):
        return 5
    if value <= Decimal("0.35"):
        return 0
    if value <= Decimal("0.50"):
        return -8
    return -14


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


def quantize_number(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return value.quantize(Decimal("0.0001"))


def decimal_sort_value(value: Decimal | None) -> Decimal:
    return value if value is not None else Decimal("-999")
