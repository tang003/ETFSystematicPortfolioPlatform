from datetime import date
from decimal import Decimal

from app.core.config import get_settings
from app.services import agent_analysis_service
from app.services.agent_analysis_service import analyze_etf_with_agents


class Db:
    def scalar(self, _statement):
        return None


class Asset:
    name = "沪深300ETF"
    asset_class = "equity"
    asset_region = "CN"
    risk_level = 3
    is_cross_border = False


def fake_detail():
    return {
        "symbol": "510300",
        "asset": Asset(),
        "metric": {
            "symbol": "510300",
            "name": "沪深300ETF",
            "asset_class": "equity",
            "asset_region": "CN",
            "risk_level": 3,
            "first_trade_date": date(2026, 1, 1),
            "latest_trade_date": date(2026, 7, 1),
            "latest_close": Decimal("4.12"),
            "bars": 120,
            "total_return": Decimal("0.08"),
            "annualized_return": Decimal("0.16"),
            "annualized_volatility": Decimal("0.18"),
            "max_drawdown": Decimal("-0.09"),
            "average_amount": Decimal("80000000"),
            "tradability_score": 85,
            "tradability_level": "优秀",
            "tradability_notes": ["成交活跃度和历史样本较好"],
        },
        "latest_factor": None,
        "curve": [{"trade_date": date(2026, 1, 1), "close": Decimal("4.0")}],
        "recent_bars": [],
    }


def test_agent_analysis_falls_back_to_rule_summary_without_deepseek(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")
    get_settings.cache_clear()
    monkeypatch.setattr(agent_analysis_service, "get_etf_detail", lambda *args, **kwargs: fake_detail())
    try:
        result = analyze_etf_with_agents(Db(), symbol="510300", start_date=date(2026, 1, 1), end_date=date(2026, 7, 1))
    finally:
        get_settings.cache_clear()

    assert result["llm_enabled"] is False
    assert result["llm_used"] is False
    assert result["final_action"]
    assert len(result["agents"]) == 6


def test_agent_analysis_uses_deepseek_when_configured(monkeypatch) -> None:
    monkeypatch.setattr(agent_analysis_service, "get_etf_detail", lambda *args, **kwargs: fake_detail())
    monkeypatch.setattr(agent_analysis_service, "deepseek_configured", lambda: True)
    monkeypatch.setattr(
        agent_analysis_service,
        "complete_json",
        lambda **_: {
            "final_action": "持有观察",
            "final_summary": "DeepSeek 综合认为该 ETF 适合持有观察。",
            "manager_commentary": "多角色观点整体偏稳健。",
        },
    )

    result = analyze_etf_with_agents(Db(), symbol="510300", start_date=date(2026, 1, 1), end_date=date(2026, 7, 1))

    assert result["llm_used"] is True
    assert result["final_action"] == "持有观察"
    assert "DeepSeek" in result["final_summary"]
