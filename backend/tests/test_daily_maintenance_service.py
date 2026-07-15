import pytest

from app.core.config import Settings
from app.services.daily_maintenance_service import next_maintenance_preview, parse_daily_maintenance_time


def test_parse_daily_maintenance_time_accepts_hh_mm() -> None:
    assert parse_daily_maintenance_time("18:30") == (18, 30)
    assert parse_daily_maintenance_time("09:05") == (9, 5)


@pytest.mark.parametrize("value", ["1830", "24:00", "12:60", "aa:bb"])
def test_parse_daily_maintenance_time_rejects_invalid_values(value: str) -> None:
    with pytest.raises(ValueError):
        parse_daily_maintenance_time(value)


def test_daily_maintenance_defaults_are_disabled() -> None:
    settings = Settings()

    assert settings.daily_maintenance_enabled is False
    assert settings.daily_maintenance_scope == "enabled"
    assert settings.daily_maintenance_strategy_code == "core_etf_rotation"


def test_next_maintenance_preview_masks_runtime_details() -> None:
    settings = Settings(daily_maintenance_enabled=True, daily_maintenance_time="19:15")

    preview = next_maintenance_preview(settings)

    assert preview["enabled"] is True
    assert preview["timezone"] == "Asia/Shanghai"
    assert preview["hour"] == 19
    assert preview["minute"] == 15
    assert preview["strategy_code"] == "core_etf_rotation"
