from datetime import date, timedelta
from decimal import Decimal
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.agent_analysis import AgentAnalysisLog
from app.models.factor import FactorDaily
from app.models.portfolio import HoldingAnalysisResult, PortfolioPosition, TargetPortfolio
from app.services.deepseek_service import DeepSeekClientError, complete_json, deepseek_configured
from app.services.etf_detail_service import get_etf_detail
from app.services.holding_service import ensure_position_market_data


def analyze_etf_with_agents(
    db: Session,
    *,
    symbol: str,
    start_date: date | None = None,
    end_date: date | None = None,
    use_llm: bool = True,
    auto_sync: bool = False,
    save_result: bool = True,
) -> dict:
    cleaned_symbol = symbol.strip().upper().split(".", 1)[0]
    resolved_end = end_date or date.today()
    resolved_start = start_date or (resolved_end - timedelta(days=365))
    warnings: list[str] = []

    if auto_sync:
        try:
            ensure_position_market_data(db, cleaned_symbol)
        except Exception as exc:  # noqa: BLE001 - analysis can still continue with existing local data.
            warnings.append(f"自动补全 ETF 基础信息/行情失败，已使用本地现有数据分析：{exc}")

    detail = get_etf_detail(db, symbol=cleaned_symbol, start_date=resolved_start, end_date=resolved_end)
    factor = detail["latest_factor"]
    position = latest_position(db, cleaned_symbol)
    target = latest_target(db, cleaned_symbol)
    holding = latest_holding_analysis(db, cleaned_symbol)
    context = {
        "detail": detail,
        "factor": factor,
        "position": position,
        "target": target,
        "holding": holding,
    }
    agents = [
        market_environment_agent(context),
        technical_trend_agent(context),
        liquidity_agent(context),
        portfolio_agent(context),
        risk_control_agent(context),
    ]
    manager = manager_agent(agents, detail)
    agents.append(manager)
    warnings.extend(build_warnings(detail, position, target))

    llm_used = False
    manager_commentary = manager["summary"]
    final_summary = manager["summary"]
    if use_llm and deepseek_configured():
        try:
            llm_result = complete_json(
                system_prompt=manager_system_prompt(),
                user_prompt=json.dumps(build_llm_payload(detail, agents, warnings), ensure_ascii=False, default=str),
            )
            final_summary = str(llm_result.get("final_summary") or final_summary)
            manager_commentary = str(llm_result.get("manager_commentary") or manager_commentary)
            manager["summary"] = manager_commentary
            if llm_result.get("final_action"):
                manager["suggestion"] = str(llm_result["final_action"])
            llm_used = True
        except DeepSeekClientError as exc:
            warnings.append(f"DeepSeek 调用失败，已使用规则总结：{exc}")

    result = {
        "symbol": cleaned_symbol,
        "name": detail["asset"].name if detail["asset"] else None,
        "start_date": resolved_start,
        "end_date": resolved_end,
        "data_status": "ready" if detail["curve"] else "missing_market_data",
        "llm_enabled": deepseek_configured(),
        "llm_used": llm_used,
        "llm_model": get_settings().deepseek_model if deepseek_configured() else None,
        "final_action": manager["suggestion"],
        "final_score": manager["score"],
        "final_summary": final_summary,
        "manager_commentary": manager_commentary,
        "agents": agents,
        "warnings": warnings,
    }
    if save_result:
        save_agent_analysis(db, result)
    return result


def latest_position(db: Session, symbol: str) -> PortfolioPosition | None:
    return db.scalar(
        select(PortfolioPosition)
        .where(PortfolioPosition.symbol == symbol)
        .order_by(PortfolioPosition.position_date.desc(), PortfolioPosition.created_at.desc())
        .limit(1)
    )


def latest_target(db: Session, symbol: str) -> TargetPortfolio | None:
    return db.scalar(
        select(TargetPortfolio)
        .where(TargetPortfolio.symbol == symbol)
        .order_by(TargetPortfolio.portfolio_date.desc(), TargetPortfolio.created_at.desc())
        .limit(1)
    )


def latest_holding_analysis(db: Session, symbol: str) -> HoldingAnalysisResult | None:
    return db.scalar(
        select(HoldingAnalysisResult)
        .where(HoldingAnalysisResult.symbol == symbol)
        .order_by(HoldingAnalysisResult.analysis_date.desc(), HoldingAnalysisResult.created_at.desc())
        .limit(1)
    )


def market_environment_agent(context: dict) -> dict:
    metric = context["detail"]["metric"]
    total_return = metric["total_return"]
    drawdown = metric["max_drawdown"]
    score = 50
    evidence: list[str] = []
    risks: list[str] = []
    if total_return is not None:
        score += 15 if total_return > 0 else -10
        evidence.append(f"区间收益 {format_percent(total_return)}")
    if drawdown is not None:
        if drawdown <= Decimal("-0.15"):
            score -= 12
            risks.append(f"最大回撤 {format_percent(drawdown)}，波动压力较高")
        else:
            evidence.append(f"最大回撤 {format_percent(drawdown)}")
    return opinion("market", "市场环境 Agent", score, evidence, risks, "根据区间收益和回撤判断 ETF 所处市场环境。")


def technical_trend_agent(context: dict) -> dict:
    factor: FactorDaily | None = context["factor"]
    metric = context["detail"]["metric"]
    score = 50
    evidence: list[str] = []
    risks: list[str] = []
    if factor and factor.trend_score is not None:
        trend = Decimal(factor.trend_score)
        score += int((trend - Decimal("50")) / Decimal("2"))
        evidence.append(f"趋势评分 {trend}")
    if factor and factor.momentum_score is not None:
        momentum = Decimal(factor.momentum_score)
        score += int((momentum - Decimal("50")) / Decimal("3"))
        evidence.append(f"动量评分 {momentum}")
    if metric["bars"] < 60:
        score -= 15
        risks.append("历史样本不足 60 个交易日，技术判断可靠性较弱")
    return opinion("technical", "技术趋势 Agent", score, evidence, risks, "根据趋势、动量和样本数量判断价格结构。")


def liquidity_agent(context: dict) -> dict:
    metric = context["detail"]["metric"]
    score = int(metric["tradability_score"])
    evidence = [f"可交易性评分 {metric['tradability_score']} {metric['tradability_level']}"]
    if metric["average_amount"] is not None:
        evidence.append(f"日均成交额约 {format_money(metric['average_amount'])}")
    risks = list(metric["tradability_notes"])
    return opinion("liquidity", "流动性 Agent", score, evidence, risks, "根据成交额、样本数量和可交易性评分判断交易便利度。")


def portfolio_agent(context: dict) -> dict:
    position: PortfolioPosition | None = context["position"]
    target: TargetPortfolio | None = context["target"]
    holding: HoldingAnalysisResult | None = context["holding"]
    score = 55
    evidence: list[str] = []
    risks: list[str] = []
    if position:
        evidence.append(f"当前持仓权重 {format_percent(position.weight)}，浮盈亏 {format_money(position.unrealized_pnl)}")
        if position.unrealized_pnl_rate is not None and position.unrealized_pnl_rate < Decimal("-0.08"):
            risks.append(f"当前持仓亏损率 {format_percent(position.unrealized_pnl_rate)}")
            score -= 8
    else:
        risks.append("当前未录入该 ETF 持仓")
        score -= 3
    if target:
        evidence.append(f"最新目标权重 {format_percent(target.final_target_weight)}")
    if holding:
        evidence.append(f"持仓分析建议：{translate_action(holding.action_suggestion)}")
        if holding.action_suggestion in {"ADD", "HOLD", "加仓", "持有"}:
            score += 8
        if holding.action_suggestion in {"REDUCE", "REDUCE_OR_EXIT", "减仓", "退出"}:
            score -= 12
    return opinion("portfolio", "组合持仓 Agent", score, evidence, risks, "结合当前持仓、目标组合和持仓分析判断组合动作。")


def risk_control_agent(context: dict) -> dict:
    asset = context["detail"]["asset"]
    metric = context["detail"]["metric"]
    score = 70
    evidence: list[str] = []
    risks: list[str] = []
    if asset:
        evidence.append(f"风险等级 R{asset.risk_level}")
        if asset.risk_level >= 4:
            score -= 15
            risks.append("该 ETF 风险等级较高，需要控制仓位")
        if asset.is_cross_border:
            score -= 8
            risks.append("跨境 ETF 可能受汇率、海外市场和交易时差影响")
    if metric["max_drawdown"] is not None and metric["max_drawdown"] <= Decimal("-0.2"):
        score -= 12
        risks.append(f"区间最大回撤达到 {format_percent(metric['max_drawdown'])}")
    return opinion("risk", "风险控制 Agent", score, evidence, risks, "根据风险等级、跨境属性和回撤控制仓位风险。")


def manager_agent(agents: list[dict], detail: dict) -> dict:
    scores = [agent["score"] for agent in agents]
    score = int(sum(scores) / len(scores)) if scores else 50
    weak_roles = [agent["title"] for agent in agents if agent["score"] < 45]
    evidence = [f"综合评分 {score}", f"本地行情样本 {detail['metric']['bars']} 条"]
    risks = [f"{role} 给出偏谨慎结论" for role in weak_roles]
    if detail["metric"]["bars"] == 0:
        score = min(score, 35)
        risks.append("缺少本地清洗行情，不能生成可靠投资判断")
    return opinion("manager", "复合经理 Agent", score, evidence, risks, "汇总多角色观点，给出最终 ETF 操作建议。")


def opinion(role: str, title: str, score: int, evidence: list[str], risks: list[str], summary: str) -> dict:
    bounded_score = max(0, min(100, score))
    return {
        "role": role,
        "title": title,
        "stance": stance_from_score(bounded_score),
        "score": bounded_score,
        "summary": summary,
        "evidence": evidence or ["暂无充分证据"],
        "risks": risks or ["未发现突出风险"],
        "suggestion": action_from_score(bounded_score),
    }


def stance_from_score(score: int) -> str:
    if score >= 75:
        return "偏多"
    if score >= 55:
        return "中性偏多"
    if score >= 40:
        return "中性偏谨慎"
    return "偏空/谨慎"


def action_from_score(score: int) -> str:
    if score >= 80:
        return "可关注加仓"
    if score >= 65:
        return "持有观察"
    if score >= 45:
        return "谨慎观察"
    return "暂不操作/考虑降权"


def build_warnings(detail: dict, position: PortfolioPosition | None, target: TargetPortfolio | None) -> list[str]:
    warnings: list[str] = []
    if not detail["asset"]:
        warnings.append("资产主数据缺失，请先同步或登记 ETF 主数据")
    if not detail["curve"]:
        warnings.append("本地清洗行情缺失，请先在 ETF 详情页或数据健康页同步行情")
    if not position:
        warnings.append("当前未录入该 ETF 持仓，组合持仓 Agent 只能给出观察建议")
    if not target:
        warnings.append("最新目标组合中未发现该 ETF，建议先运行策略或确认是否纳入研究池")
    return warnings


def build_llm_payload(detail: dict, agents: list[dict], warnings: list[str]) -> dict:
    metric = detail["metric"]
    asset = detail["asset"]
    return {
        "symbol": detail["symbol"],
        "name": asset.name if asset else None,
        "asset_class": asset.asset_class if asset else None,
        "risk_level": asset.risk_level if asset else None,
        "metric": {
            "latest_close": metric["latest_close"],
            "bars": metric["bars"],
            "total_return": metric["total_return"],
            "annualized_volatility": metric["annualized_volatility"],
            "max_drawdown": metric["max_drawdown"],
            "average_amount": metric["average_amount"],
            "tradability_score": metric["tradability_score"],
            "tradability_level": metric["tradability_level"],
        },
        "agent_opinions": agents,
        "warnings": warnings,
    }


def manager_system_prompt() -> str:
    return (
        "你是 ETF 系统化资产配置平台的复合经理。请基于多个 Agent 观点生成中文 ETF 投研结论。"
        "只输出 JSON，字段为 final_action、final_summary、manager_commentary。"
        "必须强调这不是投资承诺，当前系统不自动下单。结论要适合中长期 ETF 配置，不要给短线荐股口吻。"
        "不得编造用户没有提供、系统没有给出的行情、公告或新闻。"
    )


def save_agent_analysis(db: Session, result: dict) -> AgentAnalysisLog | None:
    if not hasattr(db, "add"):
        return None
    row = AgentAnalysisLog(
        symbol=result["symbol"],
        name=result["name"],
        start_date=result["start_date"],
        end_date=result["end_date"],
        data_status=result["data_status"],
        llm_used=result["llm_used"],
        llm_model=result["llm_model"],
        final_action=result["final_action"],
        final_score=result["final_score"],
        final_summary=result["final_summary"],
        manager_commentary=result["manager_commentary"],
        agents_payload=json_safe(result["agents"]),
        warnings_payload=json_safe(result["warnings"]),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_agent_analysis_logs(db: Session, *, symbol: str | None = None, limit: int = 20) -> list[dict]:
    query = select(AgentAnalysisLog).order_by(AgentAnalysisLog.created_at.desc(), AgentAnalysisLog.id.desc())
    if symbol:
        query = query.where(AgentAnalysisLog.symbol == symbol.strip().upper().split(".", 1)[0])
    rows = db.scalars(query.limit(max(1, min(limit, 100)))).all()
    return [agent_log_to_dict(row) for row in rows]


def agent_log_to_dict(row: AgentAnalysisLog) -> dict:
    return {
        "id": row.id,
        "symbol": row.symbol,
        "name": row.name,
        "start_date": row.start_date,
        "end_date": row.end_date,
        "data_status": row.data_status,
        "llm_used": row.llm_used,
        "llm_model": row.llm_model,
        "final_action": row.final_action,
        "final_score": row.final_score,
        "final_summary": row.final_summary,
        "manager_commentary": row.manager_commentary,
        "agents": row.agents_payload or [],
        "warnings": row.warnings_payload or [],
        "created_at": row.created_at,
    }


def json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def translate_action(action: str | None) -> str:
    mapping = {
        "ADD": "加仓",
        "HOLD": "持有",
        "REDUCE": "减仓",
        "REDUCE_OR_EXIT": "减仓或退出",
    }
    return mapping.get(action or "", action or "-")


def format_percent(value: Decimal | None) -> str:
    if value is None:
        return "-"
    return f"{(Decimal(value) * Decimal('100')).quantize(Decimal('0.01'))}%"


def format_money(value: Decimal | None) -> str:
    if value is None:
        return "-"
    amount = Decimal(value)
    if abs(amount) >= Decimal("100000000"):
        return f"{(amount / Decimal('100000000')).quantize(Decimal('0.01'))} 亿"
    if abs(amount) >= Decimal("10000"):
        return f"{(amount / Decimal('10000')).quantize(Decimal('0.01'))} 万"
    return str(amount.quantize(Decimal("0.01")))
