from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.settings import DataSourceConfig
from app.schemas.settings_schema import DataSourceProviderRead, DataSourceSettingsRead


ENV_PROVIDER_DEFAULTS = {
    "tushare": {
        "provider_name": "Tushare Pro",
        "provider_type": "market",
        "base_url_attr": "tushare_api_url",
        "secret_attr": "tushare_token",
        "request_interval_attr": "tushare_request_interval_seconds",
        "supported_usages": ["calendar", "market_daily", "asset_universe", "asset_profile"],
        "adapter_status": "runtime_supported",
        "used_by": ["交易日历", "ETF 基础池", "ETF 主资料", "日线行情", "数据健康", "全流程"],
        "notes": [
            "正式行情和基金资料当前只使用 Tushare，避免多数据源口径混用。",
            "Token 可由服务器环境变量或数据源配置提供，前端不会获取明文。",
        ],
    },
    "deepseek": {
        "provider_name": "DeepSeek",
        "provider_type": "ai",
        "base_url_attr": "deepseek_base_url",
        "secret_attr": "deepseek_api_key",
        "request_interval_attr": None,
        "supported_usages": ["ai_research", "report_enhancement"],
        "adapter_status": "runtime_supported",
        "used_by": ["AI 投研委员会", "ETF 详情解释", "报告增强"],
        "notes": ["AI 结论只作为投研解释层，不直接代替量化信号和风控门禁。"],
    },
    "juhe_finance_news": {
        "provider_name": "聚合数据财经新闻",
        "provider_type": "news",
        "base_url_attr": None,
        "secret_attr": None,
        "request_interval_attr": None,
        "supported_usages": ["news"],
        "adapter_status": "runtime_supported",
        "used_by": ["新闻资讯", "ETF 关键词关联", "AI 投研事件输入"],
        "notes": [
            "财经新闻源，第一版用于低频同步和 ETF 关键词关联。",
            "免费/低配额度通常较低，建议后端批量同步，不让前端直接请求外部接口。",
        ],
        "base_url": "https://apis.juhe.cn/fapigx/caijing/query",
        "request_interval_seconds": 7200,
        "quota_per_day": 50,
    },
}


def list_data_source_settings(db: Session) -> DataSourceSettingsRead:
    ensure_default_data_sources(db)
    rows = list(db.scalars(select(DataSourceConfig).order_by(DataSourceConfig.provider_code)).all())
    return DataSourceSettingsRead(
        default_calendar_source="tushare",
        default_market_source="tushare",
        default_profile_source="tushare",
        default_ai_provider="deepseek",
        providers=[build_provider_read(row) for row in rows],
    )


def create_data_source_config(db: Session, payload: dict[str, Any]) -> DataSourceConfig:
    provider_code = normalize_provider_code(payload["provider_code"])
    exists = db.scalar(select(DataSourceConfig).where(DataSourceConfig.provider_code == provider_code))
    if exists is not None:
        raise ValueError(f"Data source already exists: {provider_code}")
    row = DataSourceConfig(
        provider_code=provider_code,
        provider_name=payload["provider_name"],
        provider_type=payload.get("provider_type") or "market",
        enabled=bool(payload.get("enabled", True)),
        base_url=payload.get("base_url"),
        auth_type=payload.get("auth_type") or "token",
        secret_value=empty_to_none(payload.get("secret_value")),
        request_interval_seconds=payload.get("request_interval_seconds"),
        quota_per_minute=payload.get("quota_per_minute"),
        quota_per_day=payload.get("quota_per_day"),
        supported_usages=payload.get("supported_usages") or [],
        adapter_status=payload.get("adapter_status") or "metadata_only",
        notes=payload.get("notes") or [],
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_data_source_config(db: Session, provider_code: str, payload: dict[str, Any]) -> DataSourceConfig:
    row = db.scalar(select(DataSourceConfig).where(DataSourceConfig.provider_code == provider_code))
    if row is None:
        raise ValueError(f"Data source not found: {provider_code}")
    for field in (
        "provider_name",
        "provider_type",
        "enabled",
        "base_url",
        "auth_type",
        "request_interval_seconds",
        "quota_per_minute",
        "quota_per_day",
        "supported_usages",
        "adapter_status",
        "notes",
    ):
        if field in payload and payload[field] is not None:
            setattr(row, field, payload[field])
    if payload.get("clear_secret"):
        row.secret_value = None
    elif payload.get("secret_value"):
        row.secret_value = payload["secret_value"]
    db.commit()
    db.refresh(row)
    return row


def ensure_default_data_sources(db: Session) -> None:
    settings = get_settings()
    changed = False
    for provider_code, defaults in ENV_PROVIDER_DEFAULTS.items():
        row = db.scalar(select(DataSourceConfig).where(DataSourceConfig.provider_code == provider_code))
        if row is not None:
            continue
        row = DataSourceConfig(
            provider_code=provider_code,
            provider_name=defaults["provider_name"],
            provider_type=defaults["provider_type"],
            enabled=True,
            base_url=(
                getattr(settings, defaults["base_url_attr"])
                if defaults.get("base_url_attr")
                else defaults.get("base_url")
            ),
            auth_type="bearer" if provider_code == "deepseek" else "token",
            secret_value=None,
            request_interval_seconds=(
                getattr(settings, defaults["request_interval_attr"])
                if defaults.get("request_interval_attr")
                else defaults.get("request_interval_seconds")
            ),
            quota_per_day=defaults.get("quota_per_day"),
            supported_usages=defaults["supported_usages"],
            adapter_status=defaults["adapter_status"],
            notes=defaults["notes"],
        )
        db.add(row)
        changed = True
    if changed:
        db.commit()


def build_provider_read(row: DataSourceConfig) -> DataSourceProviderRead:
    settings = get_settings()
    defaults = ENV_PROVIDER_DEFAULTS.get(row.provider_code, {})
    env_secret = getattr(settings, defaults.get("secret_attr", ""), None) if defaults.get("secret_attr") else None
    env_base_url = (
        getattr(settings, defaults.get("base_url_attr"), None)
        if defaults.get("base_url_attr")
        else defaults.get("base_url")
    )
    env_interval = (
        getattr(settings, defaults.get("request_interval_attr"), None)
        if defaults.get("request_interval_attr")
        else None
    )
    effective_secret = row.secret_value or env_secret
    effective_interval = row.request_interval_seconds if row.request_interval_seconds is not None else env_interval
    status = resolve_status(row, effective_secret)
    supported_usages = row.supported_usages or defaults.get("supported_usages", [])
    return DataSourceProviderRead(
        id=row.id,
        provider_code=row.provider_code,
        provider_name=row.provider_name,
        provider_type=row.provider_type,
        enabled=row.enabled,
        configured=bool(effective_secret),
        base_url=row.base_url or env_base_url,
        auth_type=row.auth_type,
        token_masked=mask_secret(effective_secret),
        request_interval_seconds=effective_interval,
        max_requests_per_minute=requests_per_minute(effective_interval),
        quota_per_minute=row.quota_per_minute,
        quota_per_day=row.quota_per_day,
        status=status,
        adapter_status=row.adapter_status,
        used_by=usage_labels(supported_usages, defaults.get("used_by", [])),
        supported_usages=supported_usages,
        notes=row.notes or defaults.get("notes", []),
    )


def resolve_status(row: DataSourceConfig, effective_secret: str | None) -> str:
    if not row.enabled:
        return "disabled"
    if row.auth_type != "none" and not effective_secret:
        return "missing_token"
    if row.adapter_status != "runtime_supported":
        return "metadata_only"
    return "ready"


def normalize_provider_code(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    if not normalized.replace("_", "").isalnum():
        raise ValueError("provider_code can only contain letters, numbers and underscores")
    return normalized


def empty_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def mask_secret(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 12:
        return "*" * len(value)
    return f"{value[:4]}...{value[-6:]}"


def requests_per_minute(interval_seconds: float | None) -> int | None:
    if not interval_seconds or interval_seconds <= 0:
        return None
    return int(60 / interval_seconds)


def usage_labels(usages: list[str], fallback: list[str]) -> list[str]:
    if fallback:
        return fallback
    labels = {
        "calendar": "交易日历",
        "market_daily": "ETF 日线行情",
        "asset_universe": "ETF 基础池",
        "asset_profile": "ETF 主资料",
        "ai_research": "AI 投研",
        "report_enhancement": "报告增强",
    }
    return [labels.get(item, item) for item in usages]
