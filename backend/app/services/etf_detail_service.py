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
    alternatives = build_same_index_alternatives(
        db,
        asset=asset,
        current_metric=metric,
        start_date=resolved_start,
        end_date=resolved_end,
    )
    return {
        "symbol": symbol,
        "asset": asset,
        "metric": metric,
        "decision": build_decision_summary(asset=asset, metric=metric, alternatives=alternatives),
        "latest_factor": latest_factor,
        "alternatives": alternatives,
        "curve": build_detail_curve(bars),
        "recent_bars": [market_bar_dict(row) for row in reversed(bars[-30:])],
    }


def build_decision_summary(
    *,
    asset: AssetMaster | None,
    metric: dict,
    alternatives: list[dict],
) -> dict:
    score = int(metric.get("buy_score") or 0)
    level = str(metric.get("buy_level") or "暂无结论")
    bars = int(metric.get("bars") or 0)
    tradability = int(metric.get("tradability_score") or 0)
    drawdown = metric.get("max_drawdown")
    volatility = metric.get("annualized_volatility")
    annualized_return = metric.get("annualized_return")
    sharpe = metric.get("sharpe_ratio")

    if bars < 60:
        action = "先补数据，不建议直接买入"
        confidence = "低"
        position_hint = "建议仓位 0%，等行情样本补齐后再评估。"
    elif score >= 75:
        action = "可以作为优先候选"
        confidence = "中高"
        position_hint = "可考虑分批建仓，单只 ETF 初始仓位建议不超过目标组合的 20%。"
    elif score >= 60:
        action = "可以观察，小额分批"
        confidence = "中"
        position_hint = "适合先用计划资金的 20%-40% 分批试探，后续结合回撤和趋势再加仓。"
    elif score >= 45:
        action = "谨慎观察，暂不重仓"
        confidence = "中低"
        position_hint = "适合观察或很小比例定投，暂不建议一次性重仓。"
    else:
        action = "暂不优先买入"
        confidence = "低"
        position_hint = "建议暂缓买入，优先比较同类 ETF 或等待风险收益改善。"

    entry_plan = build_entry_plan(score=score, bars=bars, drawdown=drawdown, annualized_return=annualized_return)
    stop_loss_hint = build_stop_loss_hint(drawdown=drawdown, volatility=volatility)
    data_quality = build_data_quality_text(bars=bars, tradability=tradability)
    reasons = build_decision_reasons(metric=metric, asset=asset)
    risks = build_decision_risks(metric=metric, asset=asset)
    next_steps = build_next_steps(metric=metric, alternatives=alternatives)

    return {
        "action": action,
        "score": score,
        "level": level,
        "confidence": confidence,
        "position_hint": position_hint,
        "entry_plan": entry_plan,
        "stop_loss_hint": stop_loss_hint,
        "data_quality": data_quality,
        "reasons": reasons,
        "risks": risks,
        "next_steps": next_steps,
    }


def build_entry_plan(
    *,
    score: int,
    bars: int,
    drawdown: Decimal | None,
    annualized_return: Decimal | None,
) -> str:
    if bars < 60:
        return "先同步至少 120 个交易日行情，再做 6 个月和 1 年两个窗口的对比。"
    if score >= 75:
        return "可按 3-5 次分批买入；若回撤接近历史最大回撤的一半，可暂停加仓并复核。"
    if score >= 60:
        return "建议按月或按周定投，先投入计划资金的 20%-40%，等待趋势和成交额确认。"
    if annualized_return is not None and annualized_return < 0:
        return "区间收益为负，先观察是否止跌，不建议追高或一次性买入。"
    if drawdown is not None and drawdown < Decimal("-0.15"):
        return "回撤压力偏大，可等待回撤收敛或均线趋势修复后再考虑。"
    return "当前更适合加入观察池，等评分提升到 60 以上再进入定投或建仓计划。"


def build_stop_loss_hint(*, drawdown: Decimal | None, volatility: Decimal | None) -> str:
    if drawdown is None:
        return "缺少回撤样本，暂时无法给出有效风险阈值。"
    if drawdown <= Decimal("-0.25"):
        return "历史回撤较深，建议设置组合级止损或减仓线，避免单一 ETF 拖累整体组合。"
    if volatility is not None and volatility >= Decimal("0.30"):
        return "波动较高，建议用更长分批周期，并控制单次投入金额。"
    return "可用历史最大回撤作为压力参考，若新的回撤明显超过历史区间，应暂停加仓并复核。"


def build_data_quality_text(*, bars: int, tradability: int) -> str:
    if bars < 60:
        return "数据不足：样本少于 60 个交易日，结论只能作为占位参考。"
    if bars < 120:
        return "数据偏少：适合短期观察，但不适合直接形成重仓结论。"
    if tradability < 60:
        return "交易性偏弱：需要重点关注成交额、滑点和买卖价差。"
    return "数据可用：当前样本和交易性可以支持基础买入评估。"


def build_decision_reasons(*, metric: dict, asset: AssetMaster | None) -> list[str]:
    reasons: list[str] = []
    if metric.get("annualized_return") is not None:
        reasons.append(f"区间年化收益约 {Decimal(metric['annualized_return']) * Decimal('100'):.2f}%")
    if metric.get("sharpe_ratio") is not None:
        reasons.append(f"夏普比率约 {Decimal(metric['sharpe_ratio']):.2f}")
    if metric.get("tradability_score") is not None:
        reasons.append(f"可交易性评分 {metric['tradability_score']}，{metric.get('tradability_level') or '暂无等级'}")
    if asset and asset.fund_size:
        reasons.append(f"基金规模约 {Decimal(asset.fund_size) / Decimal('100000000'):.2f} 亿")
    return reasons or ["当前核心指标不足，建议先补齐行情和 ETF 主资料。"]


def build_decision_risks(*, metric: dict, asset: AssetMaster | None) -> list[str]:
    risks: list[str] = []
    if metric.get("max_drawdown") is not None:
        risks.append(f"区间最大回撤约 {Decimal(metric['max_drawdown']) * Decimal('100'):.2f}%")
    if metric.get("annualized_volatility") is not None:
        risks.append(f"年化波动约 {Decimal(metric['annualized_volatility']) * Decimal('100'):.2f}%")
    if asset and asset.is_cross_border:
        risks.append("跨境/QDII ETF 还需要关注汇率、额度、溢价率和海外市场交易时差。")
    if metric.get("estimated_gap_ratio") is not None and Decimal(metric["estimated_gap_ratio"]) > Decimal("0.05"):
        risks.append("行情缺口偏多，需先补齐数据再做正式结论。")
    risks.extend(metric.get("buy_notes") or [])
    return list(dict.fromkeys(risks))[:6] or ["暂未识别到明确风险，但仍需结合组合仓位控制。"]


def build_next_steps(*, metric: dict, alternatives: list[dict]) -> list[str]:
    steps = ["用最近 6 个月和最近 1 年两个周期各跑一次，对比结论是否一致。"]
    if int(metric.get("bars") or 0) < 120:
        steps.insert(0, "先同步本 ETF 最近 1 年行情，补齐样本后再评估。")
    if alternatives:
        best = alternatives[0]
        steps.append(f"和同指数候选 {best['symbol']} {best['name']} 比较费率、规模和成交额。")
    steps.append("若准备买入，建议先写入定投计划或目标组合，再让持仓模块持续跟踪加减仓。")
    return steps[:4]


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
