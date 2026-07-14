from pydantic import BaseModel


class DataSourceProviderRead(BaseModel):
    provider_code: str
    provider_name: str
    enabled: bool
    configured: bool
    base_url: str | None = None
    token_masked: str | None = None
    request_interval_seconds: float | None = None
    max_requests_per_minute: int | None = None
    status: str
    used_by: list[str]
    notes: list[str]


class DataSourceSettingsRead(BaseModel):
    default_calendar_source: str
    default_market_source: str
    default_profile_source: str
    default_ai_provider: str
    providers: list[DataSourceProviderRead]

