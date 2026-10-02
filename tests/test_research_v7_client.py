"""Native output wire tests use mocked inference; no live language-accuracy claim."""

import asyncio
import json
import logging
from datetime import UTC, date, datetime

import httpx
import pytest

from research_planner.app import create_app
from research_planner.errors import PlannerError
from research_planner.model_client import StructuredModelClient
from research_planner.research_v7_prompts import RESEARCH_V7_PROMPT
from research_planner.research_v7_schema import PlanResponseV7
from research_planner.schemas import PlanRequest
from tests.conftest import MODEL_KEY, FakePlanner
from tests.test_model_client import completion
from tests.test_research_v7_contract import closed_objects
from tests.v7_golden import assert_v7_expectations, example_plan, load_v7_golden_cases

CASES = load_v7_golden_cases()


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_reviewed_v7_model_outputs_and_endpoint(settings, auth, case):
    expected = example_plan(case)
    calls = []

    def respond(request):
        calls.append(json.loads(request.content))
        return httpx.Response(200, json=completion(settings, expected.model_dump_json()))

    model = StructuredModelClient(settings, httpx.MockTransport(respond))
    try:
        plan = await model.plan_v7(PlanRequest(query=case.question), date(2026, 10, 2))
        assert_v7_expectations(plan, case)
        assert len(calls) == 1
        assert not calls[0].get("tools") and not calls[0].get("stream")
        native = calls[0]["response_format"]["json_schema"]
        assert native["strict"] is True
        closed_objects(native["schema"])
        assert set(native["schema"]["properties"]) == set(type(expected).model_fields)
        assert not model.research_v7_agent.instrument
    finally:
        await model.close()
    provider = FakePlanner()

    async def plan_v7(request, reference):
        assert request.query == case.question
        return expected

    provider.plan_v7 = plan_v7
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(settings, provider)), base_url="http://test"
    ) as api:
        response = await api.post("/v7/plan", headers=auth, json={"query": case.question})
    assert response.status_code == 200, response.text
    envelope = PlanResponseV7.model_validate_json(response.content)
    assert_v7_expectations(envelope.plan, case)
    assert envelope.schema_version == "research-query-plan-v7"
    assert (
        envelope.prompt_version
        == envelope.diagnostics.planner_prompt_version
        == "research-planner-v10"
    )
    assert envelope.kind == (
        "unsupported"
        if expected.unsupported_reason
        else "needs_clarification"
        if expected.clarification != "none"
        else "plan"
    )


@pytest.mark.parametrize(
    "mutation",
    ["altered_query", "extra", "metric", "tool", "sql", "not_json", "refusal", "truncated"],
)
async def test_invalid_model_response_is_not_repaired_or_retried(settings, mutation):
    case = next(c for c in CASES if c.id == "ranking-039-004")
    data = example_plan(case).model_dump(mode="json")
    if mutation == "altered_query":
        data["original_query"] = "changed"
    elif mutation == "extra":
        data["answer"] = "invented result"
    elif mutation == "metric":
        data["metric"]["operation"] = "execute_sql"
    content = (
        "SELECT 1"
        if mutation == "sql"
        else "not json"
        if mutation == "not_json"
        else json.dumps(data)
    )
    reply = completion(settings, content)
    if mutation == "tool":
        reply["choices"][0]["message"]["tool_calls"] = [{"name": "fetch"}]
    if mutation == "refusal":
        reply["choices"][0]["message"]["refusal"] = "private body"
    if mutation == "truncated":
        reply["choices"][0]["finish_reason"] = "length"
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(200, json=reply)

    model = StructuredModelClient(settings, httpx.MockTransport(respond))
    try:
        with pytest.raises(PlannerError, match="planner_invalid_response"):
            await model.plan_v7(PlanRequest(query=case.question), date(2026, 10, 2))
        assert len(calls) == 1
    finally:
        await model.close()


async def test_terra_transport_options_are_unchanged(provider_settings, monkeypatch):
    settings = provider_settings
    settings.model = "gpt-5.6-terra"
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "OPENAI_BASE_URL"):
        monkeypatch.setenv(key, "https://not-allowed.invalid")
    case = CASES[0]
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(200, json=completion(settings, example_plan(case).model_dump_json()))

    model = StructuredModelClient(settings, httpx.MockTransport(respond))
    try:
        await model.plan_v7(PlanRequest(query=case.question), date(2026, 10, 2))
        body = json.loads(calls[0].content)
        if settings.model_provider == "openai":
            assert body["reasoning_effort"] == "none"
            assert "temperature" not in body
        assert not body.get("tools") and len(calls) == 1
        assert model.sdk.max_retries == 0
        assert not model.client.trust_env and not model.client.follow_redirects
        assert body["max_completion_tokens"] == settings.max_tokens
        assert json.loads(body["messages"][-1]["content"])["reference_date"] == "2026-10-02"
    finally:
        await model.close()


@pytest.mark.parametrize("status", [307, 429, 503])
async def test_v7_transport_errors_do_not_retry_or_leak(settings, status, caplog):
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(
            status, text="PRIVATE " + MODEL_KEY, headers={"Location": "https://example.com"}
        )

    model = StructuredModelClient(settings, httpx.MockTransport(respond))
    try:
        with (
            caplog.at_level(logging.DEBUG),
            pytest.raises(PlannerError, match="planner_unavailable"),
        ):
            await model.plan_v7(PlanRequest(query="Private query"), date(2026, 10, 2))
        assert len(calls) == 1
        assert (
            "PRIVATE" not in caplog.text
            and MODEL_KEY not in caplog.text
            and "Private query" not in caplog.text
        )
    finally:
        await model.close()


async def test_v7_request_boundary_and_provider_revalidation(settings, auth):
    provider = FakePlanner()
    case = CASES[0]
    calls = []

    async def plan_v7(request, reference):
        calls.append(request)
        return example_plan(case).model_copy(update={"original_query": "altered"})

    provider.plan_v7 = plan_v7
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(settings, provider)), base_url="http://test"
    ) as api:
        assert (await api.post("/v7/plan", json={"query": "x"})).status_code == 401
        assert (
            await api.post("/v7/plan", headers=auth, json={"query": "x" * 17000})
        ).status_code == 413
        for body in [
            {"query": "x", "plan": {}},
            {"query": "x", "latitude": 54},
            {"query": "x", "sql": "x"},
            {"query": "x", "timezone": "Mars/Guess"},
        ]:
            assert (await api.post("/v7/plan", headers=auth, json=body)).status_code == 422
        assert (
            await api.post("/v7/plan?model=evil", headers=auth, json={"query": "x"})
        ).status_code == 422
        assert not calls
        response = await api.post("/v7/plan", headers=auth, json={"query": case.question})
        assert (
            response.status_code == 502
            and response.json()["error"]["code"] == "planner_invalid_response"
        )
        assert response.headers["cache-control"] == "no-store"
        assert len(calls) == 1


async def test_v7_uses_shared_admission_timeout_and_local_reference(settings, auth, caplog):
    started = asyncio.Event()
    finish = asyncio.Event()
    seen = []
    case = CASES[0]
    provider = FakePlanner()

    async def plan_v7(request, reference):
        seen.append(reference)
        started.set()
        await finish.wait()
        return example_plan(case)

    provider.plan_v7 = plan_v7
    settings.max_concurrent_requests = 1
    app = create_app(settings, provider, clock=lambda: datetime(2026, 10, 1, 23, 30, tzinfo=UTC))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as api:
        request = asyncio.create_task(
            api.post(
                "/v7/plan", headers=auth, json={"query": case.question, "timezone": "Europe/Berlin"}
            )
        )
        await started.wait()
        try:
            for path in ["/plan", "/v4/plan", "/v5/plan", "/v6/plan", "/v7/plan"]:
                assert (
                    await api.post(path, headers=auth, json={"query": "Events"})
                ).status_code == 503
        finally:
            finish.set()
        response = await request
        assert response.status_code == 200 and response.json()["reference_date"] == "2026-10-02"
        assert seen == [date(2026, 10, 2)]
        assert case.question not in caplog.text
    settings.timeout_seconds = 0.1
    finish.clear()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(settings, provider)), base_url="http://test"
    ) as api:
        assert (
            await api.post("/v7/plan", headers=auth, json={"query": case.question})
        ).status_code == 503
        finish.set()
        assert (
            await api.post("/v7/plan", headers=auth, json={"query": case.question})
        ).status_code == 200


def test_prompt_is_algebra_not_a_fixture_lookup_or_catalog():
    assert len(RESEARCH_V7_PROMPT) < 14000
    assert sum(c.question in RESEARCH_V7_PROMPT for c in CASES) < 10
    assert "answer_mode" in RESEARCH_V7_PROMPT
    assert "unsupported_constraint" in RESEARCH_V7_PROMPT
