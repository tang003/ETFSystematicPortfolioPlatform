from datetime import date

from app.services.market_service import coverage_ratio, missing_bar_count, sample_message, sample_status
from app.services.data_quality_service import list_expected_trade_dates


class ScalarResult:
    def __init__(self, values: list[date]) -> None:
        self.values = values

    def all(self) -> list[date]:
        return self.values


class FakeSession:
    def __init__(self, values: list[date]) -> None:
        self.values = values

    def scalars(self, query):  # noqa: ANN001
        return ScalarResult(self.values)


def test_list_expected_trade_dates_reads_scalar_dates() -> None:
    expected = [date(2026, 7, 1), date(2026, 7, 2)]
    db = FakeSession(expected)

    assert list_expected_trade_dates(db, date(2026, 7, 1), date(2026, 7, 8)) == expected


def test_market_sample_status_helpers() -> None:
    assert sample_status(0, 120) == "empty"
    assert sample_status(60, 120) == "insufficient"
    assert sample_status(120, 120) == "ready"
    assert missing_bar_count(240, 200) == 40
    assert coverage_ratio(200, 240) == 0.8333
    assert "低于策略建议门槛" in sample_message(60, 120, 240)
