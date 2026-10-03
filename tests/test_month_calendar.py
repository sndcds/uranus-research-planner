from datetime import date

import pytest

from research_planner.month_calendar import month_bounds, month_calendar


@pytest.mark.parametrize("year,february_end", [(2024, 29), (2026, 28), (2000, 29), (2100, 28)])
@pytest.mark.parametrize("month", range(1, 13))
def test_every_month_has_complete_inclusive_bounds(year, february_end, month):
    expected_days = [31, february_end, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    assert month_bounds(year, month) == (
        date(year, month, 1),
        date(year, month, expected_days[month - 1]),
    )


def test_calendar_uses_supplied_year_even_for_months_already_past():
    calendar = month_calendar(date(2026, 10, 3), "Veranstaltungen im Januar")
    assert list(calendar) == ["2026"]
    assert len(calendar["2026"]) == 12
    assert calendar["2026"][0] == {"month": 1, "from_date": "2026-01-01", "to_date": "2026-01-31"}
    assert calendar["2026"][9] == {"month": 10, "from_date": "2026-10-01", "to_date": "2026-10-31"}


def test_explicit_year_candidates_have_their_own_calendar():
    calendar = month_calendar(date(2026, 10, 3), "Februar 2024 und Oktober 2025")
    assert set(calendar) == {"2024", "2025", "2026"}
    assert calendar["2024"][1]["to_date"] == "2024-02-29"
    assert calendar["2025"][9]["from_date"] == "2025-10-01"


def test_calendar_does_not_interpret_recurring_or_range_semantics():
    reference = date(2026, 10, 3)
    assert month_calendar(reference, "jeden Oktober") == month_calendar(
        reference, "von Juli bis September"
    )


def test_valid_date_extremes_and_invalid_months():
    assert month_bounds(9999, 12) == (date(9999, 12, 1), date(9999, 12, 31))
    assert month_bounds(1, 1) == (date(1, 1, 1), date(1, 1, 31))
    for year, month in [(0, 1), (10000, 1), (2026, 0), (2026, 13)]:
        with pytest.raises(ValueError):
            month_bounds(year, month)


def test_non_year_tokens_cannot_create_invalid_calendars():
    assert list(month_calendar(date(2026, 10, 3), "0000 10000 abc2024")) == ["2026"]
