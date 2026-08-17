from datetime import date
from types import SimpleNamespace

from app.services.recurring_entry_service import advance_recurrence, occurrence_dates_between


def _entry(**overrides):
    values = {
        "active": True,
        "start_date": date(2026, 1, 31),
        "end_date": None,
        "frequency": "monthly",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_advance_monthly_keeps_calendar_semantics():
    assert advance_recurrence(date(2026, 1, 31), "monthly") == date(2026, 2, 28)


def test_occurrences_respect_window_and_end_date():
    entry = _entry(end_date=date(2026, 4, 30))
    assert occurrence_dates_between(entry, date(2026, 2, 1), date(2026, 6, 1)) == [
        date(2026, 2, 28),
        date(2026, 3, 28),
        date(2026, 4, 28),
    ]


def test_inactive_entry_has_no_projected_occurrences():
    entry = _entry(active=False)
    assert occurrence_dates_between(entry, date(2026, 1, 1), date(2026, 12, 31)) == []
