from datetime import date

import pandas as pd

from app.services.calendar_service import parse_akshare_calendar, weekday_calendar


def test_weekday_calendar_excludes_weekends() -> None:
    days = weekday_calendar(date(2026, 7, 1), date(2026, 7, 8))

    assert days == [
        date(2026, 7, 1),
        date(2026, 7, 2),
        date(2026, 7, 3),
        date(2026, 7, 6),
        date(2026, 7, 7),
        date(2026, 7, 8),
    ]


def test_parse_akshare_calendar_filters_range() -> None:
    frame = pd.DataFrame({"trade_date": ["2026-06-30", "2026-07-01", "2026-07-02", "2026-07-09"]})

    days = parse_akshare_calendar(frame, date(2026, 7, 1), date(2026, 7, 8))

    assert days == [date(2026, 7, 1), date(2026, 7, 2)]

