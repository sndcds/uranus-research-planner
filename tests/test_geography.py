"""Reviewed geographic corpus; mock inference proves wiring, not live model accuracy."""

import json
from datetime import date
from pathlib import Path

import httpx
import pytest

from research_planner.app import create_app
from research_planner.geography_prompts import GEOGRAPHY_PROMPT
from research_planner.geography_schema import GeographicQueryPlan
from research_planner.model_client import StructuredModelClient
from research_planner.schemas import PlanRequest
from tests.conftest import FakePlanner
from tests.test_model_client import completion

CASES = json.loads((Path(__file__).parent / "fixtures/geography.json").read_text())


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["query"])
async def test_reviewed_plans_native_schema_and_authenticated_endpoint(settings, auth, case):
    calls = []

    def respond(request):
        calls.append(json.loads(request.content))
        return httpx.Response(200, json=completion(settings, json.dumps(case["plan"])))

    client = StructuredModelClient(settings, httpx.MockTransport(respond))
    try:
        result = await client.plan_v6(PlanRequest(query=case["query"]), date(2026, 10, 2))
        assert result.model_dump(mode="json") == case["plan"]
        assert len(calls) == 1 and not calls[0].get("tools")
        schema = calls[0]["response_format"]["json_schema"]["schema"]
        assert set(schema["required"]) == set(GeographicQueryPlan.model_fields)
        assert schema["additionalProperties"] is False
    finally:
        await client.close()
    provider = FakePlanner()

    async def plan_v6(request, reference):
        return GeographicQueryPlan.model_validate_json(json.dumps(case["plan"]))

    provider.plan_v6 = plan_v6
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(settings, provider)), base_url="http://test"
    ) as api:
        assert (await api.post("/v6/plan", json={"query": case["query"]})).status_code == 401
        response = await api.post("/v6/plan", headers=auth, json={"query": case["query"]})
        assert response.status_code == 200, response.text
        assert response.json()["plan"] == case["plan"]
        assert response.json()["schema_version"] == "research-query-plan-v6"
        assert response.json()["prompt_version"] == "research-planner-v9"


def test_prompt_distinguishes_where_from_deictic_and_names():
    for rule in [
        "wo / where / hvor ALONE never",
        "named street/square/local place -> place_query",
        "named administrative region/city -> area_query",
        "known event venue/business-like event location -> venue_query",
        "location_relation=nearby",
        "Bachstraße Flensburg",
        "Nordermarkt",
        "Südermarkt",
    ]:
        assert rule in GEOGRAPHY_PROMPT
    assert "WHERE events take place -> aggregate" not in GEOGRAPHY_PROMPT


async def test_v6_keeps_body_and_query_security_boundary(settings, auth):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(settings)), base_url="http://test"
    ) as client:
        assert (
            await client.post("/v6/plan", headers=auth, json={"query": "x" * 17000})
        ).status_code == 413
        assert (
            await client.post("/v6/plan?url=http://evil.invalid", headers=auth, json={"query": "x"})
        ).status_code == 422
        assert (
            await client.post("/v6/plan", headers=auth, json={"query": "x", "latitude": 54.79})
        ).status_code == 422
        assert (
            await client.post(
                "/v6/plan", headers={"Authorization": "Bearer wrong"}, json={"query": "x"}
            )
        ).status_code == 401
