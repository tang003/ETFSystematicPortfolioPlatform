from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ETF Systematic Portfolio Platform"
    app_env: str = "local"
    api_prefix: str = "/api"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "quant_etf"
    postgres_user: str = "quant_etf"
    postgres_password: str = "quant_etf_password"

    redis_host: str = "localhost"
    redis_port: int = 6379

    log_level: str = Field(default="INFO")

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()

