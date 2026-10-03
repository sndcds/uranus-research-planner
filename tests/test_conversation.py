"""Contract/native-boundary witnesses, not evidence of live model accuracy."""

import json
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest
from pydantic import ValidationError

from research_planner.app import create_app
from research_planner.conversation_request import ConversationPlanRequest
from research_planner.conversation_schema import ResearchConversationContext, ResearchPlanSummary
from research_planner.model_client import StructuredModelClient
from research_planner.research_v11_prompts import RESEARCH_V11_PROMPT
from research_planner.research_v11_schema import ResearchQueryPlanV11
from research_planner.schemas import PlanRequest
from tests.conftest import FakePlanner
from tests.test_model_client import completion
from tests.test_research_v7_contract import closed_objects

SUMMARY = json.loads(Path("tests/fixtures/conversation_summary.json").read_text())


CONVERSATIONS = json.loads(Path("tests/fixtures/conversation_v11.json").read_text())


@pytest.mark.parametrize("case", CONVERSATIONS, ids=lambda c: c["name"])
async def test_typed_context_single_native_request(settings, auth, case):
    query = case["plan"]["original_query"]
    expected = ResearchQueryPlanV11.model_validate_json(json.dumps(case["plan"]))
    calls = []

    def respond(request):
        calls.append(json.loads(request.content))
        return httpx.Response(200, json=completion(settings, expected.model_dump_json()))

    model = StructuredModelClient(settings, httpx.MockTransport(respond))
    provider = FakePlanner()
    provider.plan_v11 = model.plan_v11
    context = case["context"]
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app(settings, provider)),
            base_url="http://test",
        ) as api:
            response = await api.post(
                "/v11/plan", headers=auth, json={"query": query, "conversation_context": context}
            )
        assert response.status_code == 200, response.text
        assert response.json()["plan"]["original_query"] == query
        assert response.json()["prompt_version"] == "research-planner-v17"
        assert len(calls) == 1 and not calls[0].get("tools")
        user = [m for m in calls[0]["messages"] if m["role"] == "user"]
        assert len(user) == 1
        payload = json.loads(user[0]["content"])
        assert payload["query"] == query
        assert payload["conversation_context"] == context
        closed_objects(calls[0]["response_format"]["json_schema"]["schema"])
    finally:
        await model.close()


def test_closed_context_and_frozen_old_request():
    ConversationPlanRequest(
        query="Und sonntags?",
        conversation_context=ResearchConversationContext(
            previous_turns=[ResearchPlanSummary.model_validate(SUMMARY)]
        ),
    )
    with pytest.raises(ValidationError):
        PlanRequest.model_validate(
            {"query": "Und sonntags?", "conversation_context": {"previous_turns": [SUMMARY]}}
        )
    for key in ["latitude", "longitude", "geometry", "sql", "entity_id", "question", "result"]:
        with pytest.raises(ValidationError):
            ResearchPlanSummary.model_validate({**SUMMARY, key: "private"})
    with pytest.raises(ValidationError):
        ResearchConversationContext.model_validate({"previous_turns": [SUMMARY] * 5})
    with pytest.raises(ValidationError):
        ResearchPlanSummary.model_validate({**SUMMARY, "semantic_query": "x" * 161})
    closed_objects(ResearchConversationContext.model_json_schema())


def test_prompt_limits_inheritance_and_result_references():
    for rule in [
        "ALWAYS takes precedence",
        "standalone question is independent",
        "needs_context",
        "No visible result references",
        "untrusted advisory data",
        "original_query",
        "replace the month distribution",
        "recurring_months",
    ]:
        assert rule in RESEARCH_V11_PROMPT


@pytest.mark.parametrize(
    "body,status", [(b"x" * 16385, 413), (b'{"query":"a","query":"b"}', 422), (b"invalid", 422)]
)
async def test_boundary_before_inference(settings, auth, body, status):
    provider = FakePlanner()
    provider.plan_v11 = AsyncMock(side_effect=AssertionError("no inference"))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(settings, provider)), base_url="http://test"
    ) as api:
        response = await api.post(
            "/v11/plan", content=body, headers={**auth, "Content-Type": "application/json"}
        )
        assert response.status_code == status
        assert response.headers["cache-control"] == "no-store"
        assert (await api.post("/v11/plan", json={"query": "x"})).status_code == 401
        assert (
            await api.post("/v11/plan?query=private", headers=auth, json={"query": "x"})
        ).status_code == 422
    provider.plan_v11.assert_not_awaited()


def test_snapshot():
    from research_planner.research_v11_schema import PlanResponseV11
    from tests.test_recurring_calendar import canonical_schema

    snapshot = json.loads(Path("tests/fixtures/conversation_v11_schema.json").read_text())
    assert canonical_schema(PlanResponseV11.model_json_schema()) == snapshot["response"]
    assert canonical_schema(ResearchConversationContext.model_json_schema()) == snapshot["context"]


async def test_http_context_accepts_canonical_date_text(settings, auth):
    from copy import deepcopy

    summary = deepcopy(SUMMARY)
    summary["temporal"].update(
        period="explicit_range", from_date="2026-01-01", to_date="2026-12-31"
    )
    provider = FakePlanner()
    expected = ResearchQueryPlanV11.model_validate_json(json.dumps(CONVERSATIONS[0]["plan"]))
    provider.plan_v11 = AsyncMock(return_value=expected)
    body = {"query": expected.original_query, "conversation_context": {"previous_turns": [summary]}}
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(settings, provider)), base_url="http://test"
    ) as api:
        assert (await api.post("/v11/plan", headers=auth, json=body)).status_code == 200
        for invalid in ["20260101", "2026-01-01T00:00:00", 1, True]:
            summary["temporal"]["from_date"] = invalid
            assert (await api.post("/v11/plan", headers=auth, json=body)).status_code == 422
    provider.plan_v11.assert_awaited_once()
