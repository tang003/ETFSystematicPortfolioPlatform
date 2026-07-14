from pydantic import BaseModel


class DataSourceProviderRead(BaseModel):
    id: int | None = None
    provider_code: str
    provider_name: str
    provider_type: str = "market"
    enabled: bool
    configured: bool
    base_url: str | None = None
    auth_type: str = "token"
    token_masked: str | None = None
    request_interval_seconds: float | None = None
    max_requests_per_minute: int | None = None
    quota_per_minute: int | None = None
    quota_per_day: int | None = None
    status: str
    adapter_status: str = "metadata_only"
    used_by: list[str]
    supported_usages: list[str] = []
    notes: list[str]


class DataSourceSettingsRead(BaseModel):
    default_calendar_source: str
    default_market_source: str
    default_profile_source: str
    default_ai_provider: str
    providers: list[DataSourceProviderRead]


class DataSourceConfigCreate(BaseModel):
    provider_code: str
    provider_name: str
    provider_type: str = "market"
    enabled: bool = True
    base_url: str | None = None
    auth_type: str = "token"
    secret_value: str | None = None
    request_interval_seconds: float | None = None
    quota_per_minute: int | None = None
    quota_per_day: int | None = None
    supported_usages: list[str] = []
    adapter_status: str = "metadata_only"
    notes: list[str] = []


class DataSourceConfigUpdate(BaseModel):
    provider_name: str | None = None
    provider_type: str | None = None
    enabled: bool | None = None
    base_url: str | None = None
    auth_type: str | None = None
    secret_value: str | None = None
    clear_secret: bool = False
    request_interval_seconds: float | None = None
    quota_per_minute: int | None = None
    quota_per_day: int | None = None
    supported_usages: list[str] | None = None
    adapter_status: str | None = None
    notes: list[str] | None = None
