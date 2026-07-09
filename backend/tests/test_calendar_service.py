from datetime import date

import pandas as pd

from app.services import calendar_service
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


def test_resolve_calendar_sync_window_uses_incremental_gap(monkeypatch) -> None:
    monkeypatch.setattr(calendar_service, "latest_calendar_trade_date", lambda db, market="CN": date(2026, 7, 3))

    sync_start, sync_end, up_to_date = calendar_service.resolve_calendar_sync_window(
        db=None,
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 8),
        incremental=True,
    )

    assert sync_start == date(2026, 7, 4)
    assert sync_end == date(2026, 7, 8)
    assert up_to_date is False


def test_resolve_calendar_sync_window_marks_up_to_date(monkeypatch) -> None:
    monkeypatch.setattr(calendar_service, "latest_calendar_trade_date", lambda db, market="CN": date(2026, 7, 8))

    sync_start, sync_end, up_to_date = calendar_service.resolve_calendar_sync_window(
        db=None,
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 8),
        incremental=True,
    )

    assert sync_start == date(2026, 7, 1)
    assert sync_end == date(2026, 7, 8)
    assert up_to_date is True
