"""Combined wire, native model and request boundary; fixtures are not live NLP evidence."""

import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest
from pydantic import ValidationError

from research_planner.app import create_app
from research_planner.conversation_v12_schema import ResearchConversationContextV12
from research_planner.model_client import StructuredModelClient
from research_planner.planner import UnavailablePlanner
from research_planner.research_v12_schema import PlanResponseV12, ResearchQueryPlanV12
from tests.test_model_client import completion
from tests.test_recurring_calendar import canonical_schema
from tests.test_research_v7_contract import closed_objects
from tests.v9_golden import example_plan, load_v9_golden_cases

CASES = json.loads(Path("tests/fixtures/modern_v12.json").read_text())
CONTEXT = json.loads(Path("tests/fixtures/modern_v12_context.json").read_text())


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["name"])
async def test_combined_native_and_http_contract(case, settings, auth):
    calls = []

    def respond(request):
        calls.append(json.loads(request.content))
        return httpx.Response(200, json=completion(settings, json.dumps(case["plan"])))

    model = StructuredModelClient(settings, httpx.MockTransport(respond))
    try:
        app = create_app(settings, model, clock=lambda: datetime(2026, 10, 3, tzinfo=UTC))
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as api:
            response = await api.post(
                "/v12/plan",
                headers=auth,
                json={
                    "query": case["query"],
                    **(
                        {"conversation_context": case["conversation_context"]}
                        if "conversation_context" in case
                        else {}
                    ),
                },
            )
        assert response.status_code == 200, response.text
        envelope = PlanResponseV12.model_validate_json(response.content)
        assert envelope.plan.model_dump(mode="json") == case["plan"]
        assert envelope.schema_version == "research-query-plan-v12"
        assert envelope.prompt_version == "research-planner-v18"
        assert envelope.reference_date.isoformat() == "2026-10-03"
        assert len(calls) == 1 and not calls[0].get("tools")
        assert model.sdk.max_retries == 0
        native = calls[0]["response_format"]["json_schema"]
        assert native["strict"] is True
        closed_objects(native["schema"])
        context = json.loads(calls[0]["messages"][-1]["content"])
        assert context["query"] == case["query"]
        assert context["conversation_context"] == case.get("conversation_context")
        assert context["month_calendar"]["2026"][9]["to_date"] == "2026-10-31"
    finally:
        await model.close()


@pytest.mark.parametrize("case", load_v9_golden_cases(), ids=lambda c: c.id)
def test_prior_algebra_is_losslessly_represented(case):
    data = example_plan(case).model_dump(mode="json")
    data["spatial"] = [data["spatial"] | {"area_level": None}] if data["spatial"] else []
    if data["temporal"]:
        data["temporal"].update(recurring_weekdays=[], recurring_months=[])
    assert (
        ResearchQueryPlanV12.model_validate_json(json.dumps(data)).model_dump(mode="json") == data
    )


@pytest.mark.parametrize(
    "field",
    [
        "ags",
        "osm_id",
        "iso_code",
        "district_id",
        "parent_id",
        "coordinates",
        "geometry",
        "latitude",
        "sql",
    ],
)
def test_no_invented_identity_or_private_context_fields(field):
    data = deepcopy(CASES[0]["plan"])
    data["spatial"][0][field] = "invented"
    with pytest.raises(ValidationError):
        ResearchQueryPlanV12.model_validate_json(json.dumps(data))
    context = deepcopy(CONTEXT)
    context["previous_turns"][0]["areas"][0][field] = "private"
    with pytest.raises(ValidationError):
        ResearchConversationContextV12.model_validate_json(json.dumps(context))


@pytest.mark.parametrize(
    "spatial",
    [None, {}, [CASES[0]["plan"]["spatial"][0]] * 5, [CASES[0]["plan"]["spatial"][0]] * 2],
)
def test_bounded_and_not_boolean_dsl(spatial):
    data = deepcopy(CASES[0]["plan"])
    data["spatial"] = spatial
    with pytest.raises(ValidationError):
        ResearchQueryPlanV12.model_validate_json(json.dumps(data))


def test_non_admin_places_and_deictic_locations_cannot_have_level():
    for patch in [
        dict(area_query=None, place_query="Marktplatz", relation="at"),
        dict(area_query=None, reference="user_location", relation="nearby"),
    ]:
        data = deepcopy(CASES[0]["plan"])
        data["spatial"][0].update(patch)
        data["clarification"] = "needs_location"
        with pytest.raises(ValidationError):
            ResearchQueryPlanV12.model_validate_json(json.dumps(data))


def test_context_bounds_and_snapshot():
    snapshot = json.loads(Path("tests/fixtures/modern_v12_schema.json").read_text())
    assert canonical_schema(PlanResponseV12.model_json_schema()) == snapshot["response"]
    assert (
        canonical_schema(ResearchConversationContextV12.model_json_schema()) == snapshot["context"]
    )
    for n in [0, 5]:
        with pytest.raises(ValidationError):
            ResearchConversationContextV12.model_validate(
                {"previous_turns": CONTEXT["previous_turns"] * n}
            )
    data = deepcopy(CONTEXT)
    data["previous_turns"][0]["areas"] *= 5
    with pytest.raises(ValidationError):
        ResearchConversationContextV12.model_validate(data)
    data = deepcopy(CONTEXT)
    data["previous_turns"][0]["filters"]["event_types"] = ["x" * 160] * 8
    data["previous_turns"][0]["filters"]["genres"] = ["x" * 160] * 8
    with pytest.raises(ValidationError, match="summary_too_large"):
        ResearchConversationContextV12.model_validate(data)


async def test_boundary_rejects_before_inference(settings, auth):
    provider = UnavailablePlanner()
    provider.plan_v12 = AsyncMock(side_effect=AssertionError("no call"))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(settings, provider)), base_url="http://test"
    ) as api:
        assert (await api.post("/v12/plan", json={"query": "x"})).status_code == 401
        assert (
            await api.post("/v12/plan?model=x", headers=auth, json={"query": "x"})
        ).status_code == 422
        assert (
            await api.post("/v12/plan", headers=auth, json={"query": "x" * 17000})
        ).status_code == 413
        assert (
            await api.post(
                "/v12/plan",
                headers=auth,
                json={"query": "x", "conversation_context": {"sql": "private"}},
            )
        ).status_code == 422
    provider.plan_v12.assert_not_awaited()


@pytest.mark.parametrize("version,prompt", [(8, 14), (9, 15), (10, 16), (11, 17), (12, 18)])
async def test_each_endpoint_retains_its_own_wire(settings, auth, version, prompt):
    from research_planner.research_v8_schema import ResearchQueryPlanV8
    from research_planner.research_v9_schema import ResearchQueryPlanV9
    from research_planner.research_v10_schema import ResearchQueryPlanV10
    from research_planner.research_v11_schema import ResearchQueryPlanV11

    data = deepcopy(CASES[0]["plan"])
    if version == 8:
        data["group_by"] = "none"
    if version in {9, 10, 11}:
        data["spatial"] = data["spatial"][0]
        data["spatial"].pop("area_level")
    models = {
        8: ResearchQueryPlanV8,
        9: ResearchQueryPlanV9,
        10: ResearchQueryPlanV10,
        11: ResearchQueryPlanV11,
        12: ResearchQueryPlanV12,
    }
    provider = UnavailablePlanner()
    method = AsyncMock(return_value=models[version].model_validate_json(json.dumps(data)))
    setattr(provider, f"plan_v{version}", method)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(settings, provider)), base_url="http://test"
    ) as api:
        response = await api.post(
            f"/v{version}/plan", headers=auth, json={"query": data["original_query"]}
        )
    assert response.status_code == 200, response.text
    assert response.json()["schema_version"] == f"research-query-plan-v{version}"
    assert response.json()["prompt_version"] == f"research-planner-v{prompt}"
    method.assert_awaited_once()
