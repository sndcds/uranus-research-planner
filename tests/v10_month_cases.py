"""Reviewed language cases; expected dates are independent of production calendar code."""

from dataclasses import dataclass
from datetime import date

from tests.v9_golden import neutral_plan


@dataclass(frozen=True)
class MonthCase:
    query: str
    reference: date = date(2026, 10, 3)
    start: str | None = None
    end: str | None = None
    months: tuple[int, ...] = ()
    intent: str = "list"
    event_type: str | None = None


MONTH_NAMES = (
    "Januar",
    "Februar",
    "März",
    "April",
    "Mai",
    "Juni",
    "Juli",
    "August",
    "September",
    "Oktober",
    "November",
    "Dezember",
)
DAYS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
CASES = [
    MonthCase(
        f"Veranstaltungen im {name}",
        start=f"2026-{month:02}-01",
        end=f"2026-{month:02}-{days}",
    )
    for month, (name, days) in enumerate(zip(MONTH_NAMES, DAYS, strict=True), start=1)
] + [
    MonthCase("wie viele Events im Oktober", start="2026-10-01", end="2026-10-31", intent="count"),
    MonthCase("Konzerte im Dezember", start="2026-12-01", end="2026-12-31", event_type="Konzert"),
    MonthCase("jeden Oktober", months=(10,)),
    MonthCase("im Oktober typischerweise", months=(10,)),
    MonthCase("welche Typen sind im Oktober saisonal stark", months=(10,), intent="aggregate"),
    MonthCase("von Juli bis September", months=(7, 8, 9)),
    MonthCase("von Juli bis September 2026", start="2026-07-01", end="2026-09-30"),
    MonthCase("Oktober 2025", start="2025-10-01", end="2025-10-31"),
    MonthCase("Oktober 2027", start="2027-10-01", end="2027-10-31"),
    MonthCase("Februar 2024", start="2024-02-01", end="2024-02-29"),
    MonthCase("Februar 2026", date(2024, 10, 3), start="2026-02-01", end="2026-02-28"),
    MonthCase("Veranstaltungen im Februar", date(2024, 10, 3), "2024-02-01", "2024-02-29"),
]


def witness(case):
    data = neutral_plan(case.query)
    data["intent"] = case.intent
    data["temporal"] = dict(
        field="start_date",
        period="explicit_range" if case.start else "none",
        from_date=case.start,
        to_date=case.end,
        recurring_months=list(case.months),
        recurring_weekdays=[],
        time_of_day="none",
        before_time=None,
        after_time=None,
        weekday=None,
        calendar_relation="none",
        calendar_area_query=None,
        overlap=False,
        multi_day=False,
        lookback=None,
        lookback_unit=None,
    )
    if case.intent in {"count", "aggregate"}:
        data["metric"] = dict(
            operation="event_count" if case.intent == "count" else "occurrence_count",
            field=None,
            distinct_by=None,
            numerator=None,
            denominator=None,
            measure=None,
            window=None,
            currency=None,
        )
    if case.intent == "aggregate":
        data.update(group_by=["event_type"], ordering="desc", limit=20)
    if case.event_type:
        data["filters"] = [dict(field="event_type", operator="eq", value=case.event_type)]
    return data


def assert_month_case(plan, case):
    assert plan.original_query == case.query
    assert plan.clarification == "none"
    assert plan.unsupported_reason is None
    temporal = plan.temporal
    assert temporal is not None and temporal.field == "start_date"
    assert temporal.period == ("explicit_range" if case.start else "none")
    assert temporal.from_date == (date.fromisoformat(case.start) if case.start else None)
    assert temporal.to_date == (date.fromisoformat(case.end) if case.end else None)
    assert temporal.recurring_months == list(case.months)
    if case.intent == "count":
        assert plan.intent == "count" and plan.metric.operation == "event_count"
    if case.intent == "aggregate":
        assert plan.intent == "aggregate"
        assert plan.group_by == ["event_type"]
