import pytest

from app.core.config import Settings, validate_runtime_configuration


def production_settings(**overrides) -> Settings:
    values = {
        "app_env": "production",
        "app_allowed_hosts": "localhost,etf.example.com",
        "trust_proxy_headers": True,
        "postgres_password": "a-long-production-database-password",
        "auth_enabled": True,
        "auth_admin_password_hash": "pbkdf2_sha256$600000$salt$digest",
        "auth_session_secret": "s" * 48,
        "auth_cookie_secure": True,
    }
    values.update(overrides)
    return Settings(**values)


def test_valid_production_configuration_passes() -> None:
    validate_runtime_configuration(production_settings())


@pytest.mark.parametrize(
    ("overrides", "expected_message"),
    [
        ({"auth_enabled": False}, "AUTH_ENABLED"),
        ({"auth_cookie_secure": False}, "AUTH_COOKIE_SECURE"),
        ({"postgres_password": "quant_etf_password"}, "POSTGRES_PASSWORD"),
        ({"app_allowed_hosts": "*"}, "APP_ALLOWED_HOSTS"),
        ({"trust_proxy_headers": False}, "TRUST_PROXY_HEADERS"),
    ],
)
def test_invalid_production_configuration_fails(overrides, expected_message: str) -> None:
    with pytest.raises(RuntimeError, match=expected_message):
        validate_runtime_configuration(production_settings(**overrides))
