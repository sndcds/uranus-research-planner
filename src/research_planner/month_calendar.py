"""Calendar facts for model context, without interpreting the query's time semantics."""

import re
from calendar import monthrange
from datetime import date


def month_bounds(year: int, month: int) -> tuple[date, date]:
    """Inclusive local dates, including Gregorian leap years and December 9999."""
    return date(year, month, 1), date(year, month, monthrange(year, month)[1])


def month_calendar(reference_date: date, query: str) -> dict[str, list[dict[str, str | int]]]:
    """Supply arithmetic only; a four-digit token is not an interpreted date.

    The model still decides whether a month is concrete, recurring, or not a date.
    Explicit year candidates get the same calendar facts as the supplied local
    reference year. No clock, next-occurrence default, or server timezone is used.
    """
    years = {reference_date.year}
    years.update(int(token) for token in re.findall(r"\b[0-9]{4}\b", query) if int(token))
    calendars: dict[str, list[dict[str, str | int]]] = {}
    for year in sorted(years):
        months: list[dict[str, str | int]] = []
        for month in range(1, 13):
            start, end = month_bounds(year, month)
            months.append(
                {"month": month, "from_date": start.isoformat(), "to_date": end.isoformat()}
            )
        calendars[str(year)] = months
    return calendars
