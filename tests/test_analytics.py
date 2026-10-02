"""Golden fixtures verify full contracts and mocked inference, not live model accuracy."""

import json
from datetime import date
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from research_planner.analytics_guard import analytical_mismatch
from research_planner.analytics_schema import AnalyticalQueryPlan
from research_planner.app import create_app
from research_planner.model_client import StructuredModelClient
from research_planner.schemas import PlanRequest
from tests.conftest import FakePlanner, make_plan
from tests.test_model_client import completion

CASES = json.loads((Path(__file__).parent / "fixtures/analytics.json").read_text())


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["query"])
async def test_full_reviewed_plan_and_native_output(settings, case):
    calls = []

    def respond(request):
        calls.append(json.loads(request.content))
        return httpx.Response(200, json=completion(settings, json.dumps(case["plan"])))

    client = StructuredModelClient(settings, httpx.MockTransport(respond))
    try:
        result = await client.plan_v5(PlanRequest(query=case["query"]), date(2026, 10, 2))
        assert result.model_dump(mode="json") == case["plan"]
        assert len(calls) == 1 and not calls[0].get("tools")
        schema = calls[0]["response_format"]["json_schema"]["schema"]
        assert set(schema["required"]) == set(AnalyticalQueryPlan.model_fields)
        assert schema["additionalProperties"] is False
        assert (
            not analytical_mismatch(
                case["query"],
                result.intent,
                result.group_by,
                result.taxonomy,
                result.area_relation,
                result.time_of_day,
            )
            or result.unsupported_reason
        )
    finally:
        await client.close()


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["query"])
async def test_authenticated_v5_endpoint(settings, auth, case):
    provider = FakePlanner()

    async def plan_v5(request, reference):
        return AnalyticalQueryPlan.model_validate_json(json.dumps(case["plan"]))

    provider.plan_v5 = plan_v5
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(settings, provider)), base_url="http://test"
    ) as client:
        assert (await client.post("/v5/plan", json={"query": case["query"]})).status_code == 401
        response = await client.post("/v5/plan", headers=auth, json={"query": case["query"]})
        if case["plan"]["unsupported_reason"]:
            assert (
                response.status_code == 422
                and response.json()["error"]["code"] == "planner_unsupported_plan"
            )
        else:
            assert response.status_code == 200, response.text
            assert response.json()["schema_version"] == "research-query-plan-v5"
            assert response.json()["prompt_version"] == "research-planner-v10"
            assert response.json()["plan"] == case["plan"]


@pytest.mark.parametrize(
    "query",
    [
        "Welche Genres gibt es?",
        "Welche Veranstaltungstypen gibt es?",
        "Welche Instrumente kommen vor?",
        "Welche Veranstaltung liegt am westlichsten?",
        "Wie viele rollstuhlgerechte Veranstaltungen gibt es?",
        "Wo finden viele Veranstaltungen statt?",
    ],
)
async def test_generic_event_fallback_is_rejected(settings, auth, query):
    data = make_plan(query, area_query=None).model_dump() | dict(
        taxonomy=None, spatial_metric=None, area_relation="inside"
    )
    provider = FakePlanner()

    async def plan_v5(request, reference):
        return AnalyticalQueryPlan.model_validate(data)

    provider.plan_v5 = plan_v5
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(settings, provider)), base_url="http://test"
    ) as client:
        response = await client.post("/v5/plan", headers=auth, json={"query": query})
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "planner_unsupported_plan"


@pytest.mark.parametrize(
    "changes",
    [
        {"sql": "select 1"},
        {"area_relation": "outside"},
        {"spatial_metric": "latitude"},
        {"taxonomy": "genre"},
        {"time_of_day": "dawn"},
        {"group_by": "instrument"},
        {
            "intent": "count",
            "answer_mode": "count",
            "metric": "event_count",
            "semantic_query": "accessible",
            "requires_semantic_relevance": True,
        },
    ],
)
def test_closed_analytic_invariants(changes):
    data = make_plan(area_query=None).model_dump() | dict(
        taxonomy=None, spatial_metric=None, area_relation="inside"
    )
    with pytest.raises(ValidationError):
        AnalyticalQueryPlan.model_validate(data | changes)


async def test_legacy_endpoint_refuses_unrepresentable_taxonomy(settings, auth):
    provider = FakePlanner(make_plan("Welche Genres gibt es?", area_query=None))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(settings, provider)), base_url="http://test"
    ) as client:
        response = await client.post(
            "/plan", headers=auth, json={"query": "Welche Genres gibt es?"}
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "planner_unsupported_plan"


async def test_v5_boundary_rejects_browser_execution_fields(settings, auth):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(settings, FakePlanner())),
        base_url="http://test",
    ) as client:
        for extra in ["plan", "sql", "model", "collection", "taxonomy"]:
            response = await client.post(
                "/v5/plan", headers=auth, json={"query": "Events", extra: "untrusted"}
            )
            assert response.status_code == 422
        response = await client.post(
            "/v5/plan?model=untrusted", headers=auth, json={"query": "Events"}
        )
        assert response.status_code == 422
        response = await client.post("/v5/plan", headers=auth, json={"query": "x" * 17000})
        assert response.status_code == 413


RANKING_CASES = [
    c
    for c in CASES
    if c["plan"]["metric"] == "occurrence_count"
    and c["plan"]["intent"] == "aggregate"
    and c["plan"]["limit"] is not None
]


@pytest.mark.parametrize("case", RANKING_CASES, ids=lambda c: c["query"])
@pytest.mark.parametrize(
    "grouping", ["event", "event_type", "genre", "venue", "organization", "category", "none"]
)
def test_ranking_never_substitutes_dimensions(case, grouping):
    assert analytical_mismatch(case["query"], "aggregate", grouping) == (
        grouping != case["plan"]["group_by"]
    )


@pytest.mark.parametrize(
    "metric,entity",
    [("event_count", "event"), ("venue_count", "venue"), ("organization_count", "organization")],
)
def test_event_grouping_requires_occurrences(metric, entity):
    case = next(c for c in CASES if c["query"] == "Welches Event hat die meisten Termine?")
    with pytest.raises(ValidationError, match="event_grouping_requires_occurrence_count"):
        AnalyticalQueryPlan.model_validate_json(
            json.dumps(case["plan"] | {"metric": metric, "entity_type": entity})
        )


async def test_event_type_substitution_rejected_at_planner_boundary(settings, auth):
    case = next(c for c in CASES if c["query"] == "Welches Event hat die meisten Termine?")
    provider = FakePlanner()

    async def plan_v5(request, reference):
        return AnalyticalQueryPlan.model_validate(case["plan"] | {"group_by": "event_type"})

    provider.plan_v5 = plan_v5
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(settings, provider)), base_url="http://test"
    ) as client:
        response = await client.post("/v5/plan", headers=auth, json={"query": case["query"]})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "planner_unsupported_plan"
