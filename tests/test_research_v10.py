"""Calendar, contract and transport checks; mocks do not claim language accuracy."""

import json
from datetime import UTC, date, datetime

import httpx
import pytest
from pydantic import ValidationError

from research_planner.app import create_app
from research_planner.errors import PlannerError
from research_planner.model_client import StructuredModelClient
from research_planner.planner import UnavailablePlanner
from research_planner.research_v10_prompts import RESEARCH_V10_PROMPT
from research_planner.research_v10_schema import PlanResponseV10, ResearchQueryPlanV10
from research_planner.schemas import PlanRequest
from tests.test_model_client import completion
from tests.test_research_v7_contract import closed_objects
from tests.v9_golden import example_plan, load_v9_golden_cases
from tests.v10_month_cases import CASES, MonthCase, assert_month_case, witness


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.query + str(c.reference.year))
async def test_month_regression_native_output_and_endpoint(settings, auth, case):
    calls = []

    def respond(request):
        calls.append(json.loads(request.content))
        return httpx.Response(200, json=completion(settings, json.dumps(witness(case))))

    client = StructuredModelClient(settings, httpx.MockTransport(respond))
    clock = datetime.combine(case.reference, datetime.min.time(), tzinfo=UTC)
    try:
        app = create_app(settings, client, clock=lambda: clock)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as api:
            response = await api.post(
                "/v10/plan",
                headers=auth,
                json={"query": case.query, "timezone": "Europe/Berlin"},
            )
        assert response.status_code == 200, response.text
        envelope = PlanResponseV10.model_validate_json(response.content)
        assert envelope.kind == "plan"
        assert envelope.schema_version == "research-query-plan-v10"
        assert envelope.prompt_version == "research-planner-v16"
        assert envelope.reference_date == case.reference
        assert_month_case(envelope.plan, case)
        assert len(calls) == 1 and not calls[0].get("tools")
        messages = calls[0]["messages"]
        assert messages[0]["content"] == RESEARCH_V10_PROMPT
        context = json.loads(messages[-1]["content"])
        assert context["reference_date"] == case.reference.isoformat()
        assert context["timezone"] == "Europe/Berlin"
        if case.start:
            start = date.fromisoformat(case.start)
            end = date.fromisoformat(case.end)
            calendar = context["month_calendar"][str(start.year)]
            assert calendar[start.month - 1]["from_date"] == case.start
            assert calendar[end.month - 1]["to_date"] == case.end
        native = calls[0]["response_format"]["json_schema"]
        assert native["strict"] is True
        closed_objects(native["schema"])
    finally:
        await client.close()


@pytest.mark.parametrize("case", load_v9_golden_cases(), ids=lambda c: c.id)
def test_v9_algebra_retained_with_empty_recurring_months(case):
    data = example_plan(case).model_dump(mode="json")
    if data["temporal"] is not None:
        data["temporal"]["recurring_months"] = []
        data["temporal"]["recurring_weekdays"] = []
    actual = ResearchQueryPlanV10.model_validate_json(json.dumps(data))
    assert actual.model_dump(mode="json") == data


@pytest.mark.parametrize(
    "changes",
    [
        {"recurring_months": [0]},
        {"recurring_months": [13]},
        {"recurring_months": [10, 10]},
        {"recurring_months": [True]},
        {"recurring_months": ["10"]},
        {"recurring_months": []},
        {"field": "created_at"},
        {"field": "modified_at"},
        {"from_date": "2026-10-01"},
        {"unexpected": None},
    ],
)
def test_recurring_months_reject_invalid_and_conflicting_constraints(changes):
    data = witness(MonthCase("jeden Oktober", months=(10,)))
    data["temporal"].update(changes)
    with pytest.raises(ValidationError):
        ResearchQueryPlanV10.model_validate_json(json.dumps(data))


@pytest.mark.parametrize(
    "start,end",
    [
        ("2026-02-01", "2026-02-29"),
        ("2024-02-01", "2024-02-30"),
        ("2026-04-01", "2026-04-31"),
        ("2026-10-31", "2026-10-01"),
        ("2026-10-01", None),
        (None, "2026-10-31"),
    ],
)
async def test_invalid_concrete_dates_fail_without_retry(settings, start, end):
    data = witness(CASES[0])
    data["temporal"].update(from_date=start, to_date=end)
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(200, json=completion(settings, json.dumps(data)))

    client = StructuredModelClient(settings, httpx.MockTransport(respond))
    try:
        with pytest.raises(PlannerError, match="planner_invalid_response"):
            await client.plan_v10(PlanRequest(query=data["original_query"]), date(2026, 10, 3))
        assert len(calls) == 1
    finally:
        await client.close()


@pytest.mark.parametrize("timezone,year", [("Europe/Berlin", 2027), ("America/New_York", 2026)])
async def test_local_reference_year_at_new_year_boundary(settings, auth, timezone, year):
    calls = []
    case = MonthCase("Veranstaltungen im Januar", start=f"{year}-01-01", end=f"{year}-01-31")

    def respond(request):
        calls.append(json.loads(request.content))
        return httpx.Response(200, json=completion(settings, json.dumps(witness(case))))

    client = StructuredModelClient(settings, httpx.MockTransport(respond))
    try:
        app = create_app(settings, client, clock=lambda: datetime(2026, 12, 31, 23, 30, tzinfo=UTC))
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as api:
            response = await api.post(
                "/v10/plan", headers=auth, json={"query": case.query, "timezone": timezone}
            )
        assert response.status_code == 200
        envelope = PlanResponseV10.model_validate_json(response.content)
        assert envelope.reference_date.year == year
        assert_month_case(envelope.plan, case)
        context = json.loads(calls[0]["messages"][-1]["content"])
        assert list(context["month_calendar"]) == [str(year)]
        assert context["timezone"] == timezone
    finally:
        await client.close()


async def test_v10_security_boundary_and_unavailable_provider(settings, auth):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(settings, UnavailablePlanner())),
        base_url="http://test",
    ) as api:
        assert (await api.post("/v10/plan", content=b"not json")).status_code == 401
        assert (
            await api.post(
                "/v10/plan",
                headers=auth,
                content=b"x" * 17000,
            )
        ).status_code == 422
        assert (
            await api.post("/v10/plan", headers=auth, json={"query": "x" * 17000})
        ).status_code == 413
        assert (
            await api.post("/v10/plan?model=other", headers=auth, json={"query": "x"})
        ).status_code == 422
        assert (await api.post("/v10/plan", headers=auth, json={"query": "x"})).status_code == 503


def test_public_native_and_openapi_contracts_agree(settings):
    schema = create_app(settings).openapi()
    assert schema["paths"]["/v10/plan"]["post"]["responses"]["200"]["content"]["application/json"][
        "schema"
    ] == {"$ref": "#/components/schemas/PlanResponseV10"}
    temporal = schema["components"]["schemas"]["TemporalV10"]
    assert "recurring_months" in temporal["required"]
    assert "recurring_months" not in schema["components"]["schemas"]["TemporalV9"]["properties"]


def test_explicitly_requested_recurrence_with_concrete_bounds_still_supported():
    data = witness(MonthCase("jeden Oktober zwischen 2024 und 2026", months=(10,)))
    data["temporal"].update(
        period="explicit_range",
        from_date="2024-01-01",
        to_date="2026-12-31",
        recurring_weekdays=[6, 7],
    )
    actual = ResearchQueryPlanV10.model_validate_json(json.dumps(data))
    assert actual.temporal.recurring_months == [10]
    assert actual.temporal.recurring_weekdays == [6, 7]
    assert actual.temporal.from_date == date(2024, 1, 1)
    assert actual.temporal.to_date == date(2026, 12, 31)
