import pytest

from app.core.config import Settings
from app.services import daily_maintenance_service
from app.services.daily_maintenance_service import (
    DAILY_MAINTENANCE_LAST_RUN_KEY,
    get_daily_maintenance_status,
    next_maintenance_preview,
    parse_daily_maintenance_time,
    record_daily_maintenance_result,
)


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self.store.get(key)

    def set(self, key: str, value: str, ex: int | None = None, nx: bool = False) -> bool:
        if nx and key in self.store:
            return False
        self.store[key] = value
        return True


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


def test_daily_maintenance_status_includes_last_run(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeRedis()
    record_daily_maintenance_result(fake, {"status": "success", "run_date": "2026-07-14"})
    assert fake.get(DAILY_MAINTENANCE_LAST_RUN_KEY)
    monkeypatch.setattr(daily_maintenance_service.redis.Redis, "from_url", lambda *args, **kwargs: fake)

    status = get_daily_maintenance_status(Settings(daily_maintenance_enabled=True))

    assert status["enabled"] is True
    assert status["lock_active"] is False
    assert status["last_run"] == {"status": "success", "run_date": "2026-07-14"}
