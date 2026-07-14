from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.settings_schema import DataSourceProviderRead, DataSourceSettingsRead

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/data-sources", response_model=DataSourceSettingsRead)
def get_data_sources() -> DataSourceSettingsRead:
    settings = get_settings()
    return DataSourceSettingsRead(
        default_calendar_source="tushare",
        default_market_source="tushare",
        default_profile_source="tushare",
        default_ai_provider="deepseek",
        providers=[
            DataSourceProviderRead(
                provider_code="tushare",
                provider_name="Tushare Pro",
                enabled=True,
                configured=bool(settings.tushare_token),
                base_url=settings.tushare_api_url,
                token_masked=mask_secret(settings.tushare_token),
                request_interval_seconds=settings.tushare_request_interval_seconds,
                max_requests_per_minute=requests_per_minute(settings.tushare_request_interval_seconds),
                status="ready" if settings.tushare_token else "missing_token",
                used_by=["交易日历", "ETF 基础池", "ETF 主资料", "日线行情", "数据健康", "全流程"],
                notes=[
                    "正式行情和基金资料当前只使用 Tushare，避免多数据源口径混用。",
                    "Token 只保存在后端环境变量中，前端不会获取明文。",
                ],
            ),
            DataSourceProviderRead(
                provider_code="deepseek",
                provider_name="DeepSeek",
                enabled=True,
                configured=bool(settings.deepseek_api_key),
                base_url=settings.deepseek_base_url,
                token_masked=mask_secret(settings.deepseek_api_key),
                request_interval_seconds=None,
                max_requests_per_minute=None,
                status="ready" if settings.deepseek_api_key else "missing_token",
                used_by=["AI 投研委员会", "ETF 详情解释", "报告增强"],
                notes=[
                    f"当前模型：{settings.deepseek_model}",
                    "AI 结论只作为投研解释层，不直接代替量化信号和风控门禁。",
                ],
            ),
        ],
    )


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

