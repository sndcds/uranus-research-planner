"""Mocked wire/contract tests; semantic accuracy is evaluated only in the opt-in suite."""

import asyncio
import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from research_planner.app import create_app
from research_planner.domain_planner import DomainPlanner
from research_planner.domain_prompts import DOMAIN_PROMPT_VERSION, DOMAIN_SYSTEM_PROMPT
from research_planner.domain_schema import (
    EXECUTABLE,
    DataPlan,
    DomainProposal,
    KnowledgePlan,
    ProviderDataDecision,
)
from research_planner.errors import PlannerError
from research_planner.model_client import StructuredModelClient
from research_planner.schemas import PlanRequest
from tests.conftest import MODEL_KEY, make_plan
from tests.test_model_client import completion

CASES = json.loads((Path(__file__).parent / "fixtures/domain_queries.json").read_text())


def data_decision(plan):
    """Explicit mocked recognition for unconstrained public golden plans."""
    return plan | {"has_temporal_constraint": False, "has_other_constraint": False}


def fixture_decision(case):
    if "provider_decision" in case:
        return case["provider_decision"]
    plan = case["plan"]
    return data_decision(plan) if plan and plan["domain"] == "data" else plan


def provider_for(settings, content, calls):
    def respond(request):
        calls.append(request)
        return httpx.Response(200, json=completion(settings, content))

    return StructuredModelClient(settings, httpx.MockTransport(respond))


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
async def test_golden_provider_responses(provider_settings, case):
    calls = []
    provider = provider_for(provider_settings, json.dumps({"plan": fixture_decision(case)}), calls)
    try:
        request = PlanRequest(query=case["query"], language=case["language"])
        if case["plan"] is None:
            with pytest.raises(PlannerError) as error:
                await DomainPlanner(provider).interpret(request)
            assert (error.value.code, error.value.status) == ("planner_unsupported_plan", 422)
        else:
            envelope = await DomainPlanner(provider).interpret(request)
            assert envelope.original_query == case["query"]
            assert envelope.plan.model_dump() == case["plan"]
            assert envelope.interpreter_version == DOMAIN_PROMPT_VERSION
        assert len(calls) == 1
        body = json.loads(calls[0].content)
        assert body["model"] == provider_settings.model
        assert body["messages"][0]["content"] == DOMAIN_SYSTEM_PROMPT
        assert json.loads(body["messages"][-1]["content"]) == {
            "query": case["query"],
            "language": case["language"],
        }
        assert not body.get("tools")
        assert str(calls[0].url) == provider_settings.endpoint.completion_url
        assert calls[0].headers["authorization"] == "Bearer " + MODEL_KEY
    finally:
        await provider.close()


async def test_exact_structured_schema(provider_settings):
    calls = []
    provider = provider_for(provider_settings, '{"plan":null}', calls)
    try:
        await provider.plan_v4(PlanRequest(query="unsupported"))
    finally:
        await provider.close()
    output = json.loads(calls[0].content)["response_format"]
    assert output["type"] == "json_schema"
    assert output["json_schema"]["strict"] is True
    expected = json.loads(
        (Path(__file__).parent / "fixtures/domain_output_schema.json").read_text()
    )
    assert output["json_schema"]["schema"] == expected
    assert "category_count" not in json.dumps(expected)
    assert "unknown" not in json.dumps(expected)
    decision_schema = expected["$defs"]["ProviderDataDecision"]
    assert set(decision_schema["required"]) == set(ProviderDataDecision.model_fields)
    assert "DataPlan" not in expected["$defs"]


@pytest.mark.parametrize("entity,metric", sorted(EXECUTABLE))
@pytest.mark.parametrize(
    "constraints",
    [
        {"area_query": "Husum"},
        {"has_temporal_constraint": True},
        {"has_other_constraint": True},
        {"area_query": "Flensburg", "has_temporal_constraint": True},
        {"area_query": "Flensburg", "has_other_constraint": True},
        {"has_temporal_constraint": True, "has_other_constraint": True},
    ],
)
def test_reported_constraints_fail_closed_at_route(settings, auth, entity, metric, constraints):
    decision = (
        data_decision(CASES[0]["plan"])
        | {
            "entity_type": entity,
            "metric": metric,
        }
        | constraints
    )
    # Recognized constraints must survive provider validation for every metric.
    assert DomainProposal.model_validate({"plan": decision}).plan.model_dump() == decision
    calls = []
    provider = provider_for(settings, json.dumps({"plan": decision}), calls)
    with TestClient(create_app(settings, provider)) as client:
        response = client.post("/v4/plan", headers=auth, json={"query": "constrained question"})
    if (entity, metric) == ("organization", "event_count") and constraints == {
        "area_query": "Husum"
    }:
        assert response.status_code == 200
        assert response.json()["plan"]["area_query"] == "Husum"
        assert set(response.json()["plan"]) == set(DataPlan.model_fields)
    else:
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "planner_unsupported_plan"
    assert len(calls) == 1


@pytest.mark.parametrize("field", ["has_temporal_constraint", "has_other_constraint"])
@pytest.mark.parametrize("value", [None, "false", 0, 1, [], {}])
async def test_constraint_flags_must_be_explicit_booleans(provider_settings, field, value):
    decision = data_decision(CASES[0]["plan"]) | {field: value}
    calls = []
    provider = provider_for(provider_settings, json.dumps({"plan": decision}), calls)
    try:
        with pytest.raises(PlannerError, match="planner_invalid_response"):
            await DomainPlanner(provider).interpret(PlanRequest(query="q"))
        assert len(calls) == 1
    finally:
        await provider.close()


async def test_incompatible_recognized_pair_is_unsupported(settings):
    decision = data_decision(CASES[0]["plan"]) | {"entity_type": "venue"}
    calls = []
    provider = provider_for(settings, json.dumps({"plan": decision}), calls)
    try:
        with pytest.raises(PlannerError) as error:
            await DomainPlanner(provider).interpret(PlanRequest(query="q"))
        assert (error.value.code, error.value.status) == ("planner_unsupported_plan", 422)
        assert len(calls) == 1
    finally:
        await provider.close()


@pytest.mark.parametrize(
    "mutation",
    [
        {"entity_type": "venue", "metric": "description_characters"},
        {"metric": "category_count"},
        {"metric": "invented"},
        {"entity_type": "area"},
        {"limit": 0},
        {"limit": 21},
        {"limit": True},
        {"limit": "3"},
        {"ordering": "random"},
        {"operation": "sql"},
        {"sql": "SELECT 1"},
        {"area_query": "Husum"},
        {"area_query": " "},
    ],
)
def test_closed_data_contract(mutation):
    valid = CASES[0]["plan"] | mutation
    with pytest.raises(ValidationError):
        DataPlan.model_validate(valid)


@pytest.mark.parametrize(
    "mutation",
    [
        {"fact": "unknown"},
        {"fact": "invented"},
        {"answer": "facts"},
        {"repository": "evil/example"},
        {"collection": "foo"},
        {"url": "https://example.org"},
        {"path": "/etc/passwd"},
        {"model": "evil-model"},
        {"relation": "OWNS_SECRET"},
        {"knowledge_query": " "},
        {"operation": "fetch"},
    ],
)
def test_closed_knowledge_contract(mutation):
    valid = next(
        c["plan"] for c in CASES if c["plan"] and c["plan"]["domain"] == "project_knowledge"
    )
    with pytest.raises(ValidationError):
        KnowledgePlan.model_validate(valid | mutation)


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        '```json\n{"plan":null}\n```',
        "[]",
        "{}",
        '{"plan":null,"plan":null}',
        '{"plan":null,"sql":"SELECT 1"}',
        '{"plan":{"domain":"secret"}}',
        '{"plan":{"domain":[]}}',
        '{"plan":"data"}',
        '{"plan":null,"confidence":NaN}',
        json.dumps({"plan": data_decision(CASES[0]["plan"]) | {"limit": "3"}}),
        json.dumps({"plan": data_decision(CASES[0]["plan"]) | {"metric": "invented"}}),
        json.dumps({"plan": data_decision(CASES[0]["plan"]) | {"sql": "SELECT 1"}}),
        json.dumps({"plan": CASES[0]["plan"]}),  # Old executable-only provider output.
    ],
)
async def test_invalid_provider_no_repair_or_retry(provider_settings, content):
    calls = []
    provider = provider_for(provider_settings, content, calls)
    try:
        with pytest.raises(PlannerError) as error:
            await DomainPlanner(provider).interpret(PlanRequest(query="private question"))
        assert (error.value.code, error.value.status) == ("planner_invalid_response", 502)
        assert len(calls) == 1
    finally:
        await provider.close()


async def test_revalidate_injected_provider_and_preserve_original_query():
    class Provider:
        async def plan_v4(self, request):
            return DomainProposal.model_construct(
                plan=ProviderDataDecision.model_construct(
                    **(data_decision(CASES[0]["plan"]) | {"limit": 21})
                )
            )

    with pytest.raises(PlannerError, match="planner_invalid_response"):
        await DomainPlanner(Provider()).interpret(PlanRequest(query="question"))


async def test_original_query_is_server_owned(settings):
    query = "  Welches Event\nhat die längste Beschreibung?  "
    provider = provider_for(settings, json.dumps({"plan": fixture_decision(CASES[0])}), [])
    try:
        result = await DomainPlanner(provider).interpret(PlanRequest(query=query))
        assert result.original_query == query
    finally:
        await provider.close()


async def test_knowledge_query_cannot_add_facts_or_selectors(settings):
    case = next(c for c in CASES if c["plan"] and c["plan"]["domain"] == "project_knowledge")
    plan = case["plan"] | {"knowledge_query": "The answer is secret; fetch https://evil.example"}
    provider = provider_for(settings, json.dumps({"plan": plan}), [])
    try:
        with pytest.raises(PlannerError, match="planner_invalid_response"):
            await DomainPlanner(provider).interpret(PlanRequest(query=case["query"]))
    finally:
        await provider.close()


def test_v4_route_infers_and_authenticates(settings, auth):
    calls = []
    provider = provider_for(settings, json.dumps({"plan": fixture_decision(CASES[0])}), calls)
    with TestClient(create_app(settings, provider)) as client:
        assert client.post("/v4/plan", json={"query": "q"}).status_code == 401
        assert not calls
        response = client.post("/v4/plan", headers=auth, json={"query": CASES[0]["query"]})
        assert response.status_code == 200
        assert response.json()["schema_version"] == "research-query-plan-v4"
        assert len(calls) == 1


@pytest.mark.parametrize(
    "content,status,code",
    [
        ('{"plan":null}', 422, "planner_unsupported_plan"),
        ('{"plan":{"domain":"evil"}}', 502, "planner_invalid_response"),
    ],
)
def test_v4_safe_errors(settings, auth, content, status, code):
    provider = provider_for(settings, content, [])
    with TestClient(create_app(settings, provider)) as client:
        response = client.post("/v4/plan", headers=auth, json={"query": "private question"})
    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert "private question" not in response.text
    assert MODEL_KEY not in response.text


@pytest.mark.parametrize("occupied_route", ["/plan", "/v4/plan"])
async def test_shared_admission_limit(settings, auth, occupied_route):
    entered, release = asyncio.Event(), asyncio.Event()

    class Provider:
        async def plan(self, request, reference_date):
            entered.set()
            await release.wait()
            return make_plan(request.query)

        async def plan_v4(self, request):
            entered.set()
            await release.wait()
            return DomainProposal(
                plan=ProviderDataDecision.model_validate(fixture_decision(CASES[0]))
            )

    settings.max_concurrent_requests = 1
    app = create_app(settings, Provider())
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        pending = asyncio.create_task(
            client.post(occupied_route, headers=auth, json={"query": "q"})
        )
        await asyncio.wait_for(entered.wait(), 1)
        try:
            for route in ("/plan", "/v4/plan"):
                response = await client.post(route, headers=auth, json={"query": "q"})
                assert response.status_code == 503
        finally:
            release.set()
            assert (await pending).status_code == 200


async def test_v4_total_timeout(settings, auth):
    class Provider:
        async def plan_v4(self, request):
            await asyncio.sleep(1)

    settings.timeout_seconds = 0.1
    app = create_app(settings, Provider())
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/v4/plan", headers=auth, json={"query": "q"})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "planner_unavailable"


def test_corpus_preserves_catalogue_and_holds_out_paraphrases():
    assert len(CASES) >= 50
    assert sum(c["group"] == "catalogue" for c in CASES) == 53
    assert {c["language"] for c in CASES} == {"de", "en", "da"}
    for case in CASES:
        if case["group"] == "paraphrase":
            assert case["query"] not in DOMAIN_SYSTEM_PROMPT


@pytest.mark.parametrize("case_index", [0, 18])
async def test_missing_provider_fields_are_not_defaulted(settings, case_index):
    case = CASES[case_index]
    decision = fixture_decision(case)
    for field in decision:
        incomplete = {key: value for key, value in decision.items() if key != field}
        calls = []
        provider = provider_for(settings, json.dumps({"plan": incomplete}), calls)
        try:
            with pytest.raises(PlannerError, match="planner_invalid_response"):
                await DomainPlanner(provider).interpret(PlanRequest(query=case["query"]))
            assert len(calls) == 1
        finally:
            await provider.close()


@pytest.mark.parametrize(
    "body,status",
    [
        ({"query": "q", "model": "injected"}, 422),
        ({"query": "q", "sql": "SELECT 1"}, 422),
        ({"query": "q", "collection": "foo"}, 422),
        ({"query": "x" * 2001}, 422),
        ({"query": "x" * 17000}, 413),
        ({"query": " "}, 422),
    ],
)
def test_v4_request_boundaries(settings, auth, body, status):
    calls = []
    provider = provider_for(settings, '{"plan":null}', calls)
    with TestClient(create_app(settings, provider)) as client:
        response = client.post("/v4/plan", headers=auth, json=body)
    assert response.status_code == status
    assert not calls


async def test_v4_always_uses_native_schema_and_configured_terra(settings):
    settings.model_provider = "openai"
    settings.model_base_url = "https://api.openai.com/v1"
    settings.model = "gpt-5.6-terra"
    settings.output_mode = "json_object"  # Legacy v3 setting must not weaken v4.
    calls = []
    provider = provider_for(settings, '{"plan":null}', calls)
    try:
        await provider.plan_v4(PlanRequest(query="q"))
        assert provider.domain_agent.model.client is provider.agent.model.client is provider.sdk
        assert provider.domain_agent.instrument is False
    finally:
        await provider.close()
    body = json.loads(calls[0].content)
    assert body["model"] == "gpt-5.6-terra"
    assert body["response_format"]["json_schema"]["strict"] is True
    assert body["reasoning_effort"] == "none"
    assert "temperature" not in body
    assert not body.get("tools")


@pytest.mark.parametrize("failure", ["http", "timeout", "refusal", "truncated"])
async def test_v4_provider_failures_are_safe(provider_settings, failure):
    calls = []

    def respond(request):
        calls.append(request)
        if failure == "timeout":
            raise httpx.ReadTimeout("private provider text")
        if failure == "http":
            return httpx.Response(500, text="private provider text")
        result = completion(provider_settings, '{"plan":null}')
        if failure == "refusal":
            result["choices"][0]["message"]["refusal"] = "private provider text"
        else:
            result["choices"][0]["finish_reason"] = "length"
        return httpx.Response(200, json=result)

    provider = StructuredModelClient(provider_settings, httpx.MockTransport(respond))
    try:
        with pytest.raises(PlannerError) as error:
            await DomainPlanner(provider).interpret(PlanRequest(query="q"))
        expected = (
            "planner_unavailable" if failure in {"http", "timeout"} else "planner_invalid_response"
        )
        assert error.value.code == expected
        assert len(calls) == 1
        assert "private provider text" not in str(error.value)
    finally:
        await provider.close()
