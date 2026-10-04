"""Semantic fixtures verify the wire boundary; only opt-in tests assess live NLP."""

import json
import logging
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest
from pydantic import ValidationError

from research_planner.app import create_app
from research_planner.conversation_v13_request import ConversationPlanRequestV13
from research_planner.model_client import StructuredModelClient
from research_planner.planner import UnavailablePlanner
from research_planner.research_v13_schema import PlanResponseV13, ResearchQueryPlanV13
from tests.test_model_client import completion
from tests.test_recurring_calendar import canonical_schema
from tests.test_research_v7_contract import closed_objects

CASES = json.loads(Path("tests/fixtures/conversation_v13.json").read_text())


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["request"]["query"])
async def test_native_and_http_contract(settings, auth, case, caplog):
    caplog.set_level(logging.INFO, logger="research_planner.metrics")
    calls = []

    def respond(request):
        calls.append(json.loads(request.content))
        return httpx.Response(200, json=completion(settings, json.dumps(case["plan"])))

    model = StructuredModelClient(settings, httpx.MockTransport(respond))
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(
                app=create_app(settings, model, clock=lambda: datetime(2026, 10, 4, tzinfo=UTC))
            ),
            base_url="http://test",
        ) as api:
            response = await api.post("/v13/plan", headers=auth, json=case["request"])
        assert response.status_code == 200, response.text
        envelope = PlanResponseV13.model_validate_json(response.content)
        assert envelope.plan.model_dump(mode="json") == case["plan"]
        assert envelope.schema_version == "research-query-plan-v13"
        assert envelope.prompt_version == "research-planner-v19"
        assert envelope.diagnostics.interaction_kind == case["plan"]["interaction"]["kind"]
        assert envelope.diagnostics.validation_stage == "validated"
        assert len(calls) == 1 and not calls[0].get("tools")
        assert model.sdk.max_retries == 0
        native = calls[0]["response_format"]["json_schema"]
        assert native["strict"] is True
        closed_objects(native["schema"])
        payload = json.loads(calls[0]["messages"][-1]["content"])
        for key, value in case["request"].items():
            assert payload[key] == value
        assert payload["month_calendar"]["2026"][10]["to_date"] == "2026-11-30"
        assert response.headers["cache-control"] == "no-store"
        assert case["request"]["query"] not in caplog.text
        logged = json.loads(
            next(r.message for r in caplog.records if r.name == "research_planner.metrics")
        )
        assert logged["interaction_kind"] == case["plan"]["interaction"]["kind"]
        assert logged["validation_stage"] == "validated"
        if "conversation" in case["plan"]["interaction"]:
            assert logged["planner_intent"] is None
    finally:
        await model.close()


@pytest.mark.parametrize(
    "change",
    [
        "payload_on_social",
        "both_payloads",
        "changed_query",
        "wrong_act",
        "extra_sql",
        "wrong_reason",
    ],
)
def test_invalid_interactions_fail_closed(change):
    value = deepcopy(CASES[0]["plan"])
    research = next(
        c["plan"]["interaction"] for c in CASES if c["plan"]["interaction"]["kind"] == "research"
    )
    if change in {"payload_on_social", "both_payloads"}:
        value["interaction"]["research_plan"] = research["research_plan"]
        if change == "payload_on_social":
            del value["interaction"]["conversation"]
    elif change == "changed_query":
        value["original_query"] = "changed"
    elif change == "wrong_act":
        value["interaction"]["conversation"]["act"] = "help"
    elif change == "extra_sql":
        value["interaction"]["sql"] = "private"
    else:
        value["interaction"]["conversation"]["reason"] = "needs_context"
    with pytest.raises(ValidationError):
        ResearchQueryPlanV13.model_validate_json(
            json.dumps(value), context={"original_query": CASES[0]["request"]["query"]}
        )


async def test_boundary_and_injected_validation(settings, auth):
    provider = UnavailablePlanner()
    provider.plan_v13 = AsyncMock(
        return_value=ResearchQueryPlanV13.model_validate(CASES[0]["plan"]).model_copy(
            update={"original_query": "changed"}
        )
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(settings, provider)), base_url="http://test"
    ) as api:
        assert (await api.post("/v13/plan", json={"query": "x"})).status_code == 401
        for body in [
            {"query": "x", "sql": "private"},
            {"query": "x", "conversation_context": {"raw_history": "private"}},
        ]:
            assert (await api.post("/v13/plan", headers=auth, json=body)).status_code == 422
        assert (
            await api.post("/v13/plan?model=x", headers=auth, json={"query": "x"})
        ).status_code == 422
        assert (
            await api.post(
                "/v13/plan",
                headers={**auth, "Content-Type": "application/json"},
                content=b"x" * 16385,
            )
        ).status_code == 413
        provider.plan_v13.assert_not_awaited()
        assert (
            await api.post("/v13/plan", headers=auth, json={"query": "danke"})
        ).status_code == 502
    provider.plan_v13.assert_awaited_once()


def test_snapshot():
    snapshot = json.loads(Path("tests/fixtures/conversation_v13_schema.json").read_text())
    assert canonical_schema(PlanResponseV13.model_json_schema()) == snapshot["response"]
    assert canonical_schema(ConversationPlanRequestV13.model_json_schema()) == snapshot["request"]
