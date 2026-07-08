from datetime import date

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

