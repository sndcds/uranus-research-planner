"""Stack integration: independent versioned wires behind one shared boundary."""

import asyncio
import json
from datetime import UTC, date, datetime
from pathlib import Path

import httpx
import pytest

from research_planner.app import create_app
from research_planner.errors import PlannerError
from research_planner.model_client import StructuredModelClient
from research_planner.planner import UnavailablePlanner
from research_planner.research_v7_schema import ResearchQueryPlanV7
from research_planner.research_v8_canonical import CanonicalModelOutputV8
from research_planner.research_v8_schema import PlanResponseV8, ResearchQueryPlanV8
from research_planner.research_v9_canonical import CanonicalModelOutputV9
from research_planner.research_v9_schema import PlanResponseV9, ResearchQueryPlanV9
from research_planner.schemas import PlanRequest
from tests.test_model_client import completion
from tests.v7_golden import example_plan as example_v7
from tests.v7_golden import load_v7_golden_cases
from tests.v9_golden import example_plan as example_v9
from tests.v9_golden import load_v9_golden_cases


class VersionedPlanner(UnavailablePlanner):
    def __init__(self):
        self.plans = {
            "v7": example_v7(load_v7_golden_cases()[0]),
            "v8": ResearchQueryPlanV8.model_validate_json(
                json.dumps(json.loads(Path("tests/fixtures/v8_administrative.json").read_text())[6])
            ),
            "v9": example_v9(next(c for c in load_v9_golden_cases() if c.id == "trends-061-010")),
        }
        self.calls = []
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.release.set()

    async def _answer(self, version, request, reference):
        self.calls.append((version, request, reference))
        self.started.set()
        await self.release.wait()
        return self.plans[version]

    async def plan_v7(self, request, reference):
        return await self._answer("v7", request, reference)

    async def plan_v8(self, request, reference):
        return await self._answer("v8", request, reference)

    async def plan_v9(self, request, reference):
        return await self._answer("v9", request, reference)


def test_all_versioned_endpoints_and_distinct_openapi_models(settings):
    schema = create_app(settings).openapi()
    assert {"/plan", "/v4/plan", "/v5/plan", "/v6/plan", "/v7/plan", "/v8/plan", "/v9/plan"} <= set(
        schema["paths"]
    )
    for version, response_model, plan_model, canonical in [
        ("v8", PlanResponseV8, ResearchQueryPlanV8, CanonicalModelOutputV8),
        ("v9", PlanResponseV9, ResearchQueryPlanV9, CanonicalModelOutputV9),
    ]:
        wire = schema["paths"][f"/{version}/plan"]["post"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]
        assert wire == {"$ref": f"#/components/schemas/{response_model.__name__}"}
        assert canonical.model_json_schema() == plan_model.model_json_schema()


@pytest.mark.parametrize(
    "version,prompt,model", [("v8", "v14", PlanResponseV8), ("v9", "v15", PlanResponseV9)]
)
async def test_endpoint_calls_only_its_version_and_keeps_local_date(
    settings, auth, version, prompt, model, caplog
):
    provider = VersionedPlanner()
    expected = provider.plans[version]
    app = create_app(settings, provider, clock=lambda: datetime(2026, 10, 1, 23, 30, tzinfo=UTC))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as api:
        response = await api.post(
            f"/{version}/plan",
            headers=auth,
            json={"query": expected.original_query, "timezone": "Europe/Berlin"},
        )
    assert response.status_code == 200
    parsed = model.model_validate_json(response.content)
    assert parsed.plan.model_dump() == expected.model_dump()
    assert parsed.schema_version == f"research-query-plan-{version}"
    assert (
        parsed.prompt_version
        == parsed.diagnostics.planner_prompt_version
        == f"research-planner-{prompt}"
    )
    assert parsed.reference_date == date(2026, 10, 2)
    assert [(v, d) for v, _, d in provider.calls] == [(version, date(2026, 10, 2))]
    assert expected.original_query not in caplog.text
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("version", ["v8", "v9"])
@pytest.mark.parametrize("bad_output", ["other_version", "changed_query"])
async def test_provider_output_revalidation_fails_closed(settings, auth, version, bad_output):
    provider = VersionedPlanner()
    query = provider.plans[version].original_query
    if bad_output == "other_version":
        other = "v9" if version == "v8" else "v8"
        provider.plans[version] = provider.plans[other].model_copy(update={"original_query": query})
    else:
        provider.plans[version] = provider.plans[version].model_copy(
            update={"original_query": "changed"}
        )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(settings, provider)), base_url="http://test"
    ) as api:
        response = await api.post(f"/{version}/plan", headers=auth, json={"query": query})
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "planner_invalid_response"
    assert "changed" not in response.text and query not in response.text
    assert len(provider.calls) == 1


@pytest.mark.parametrize("version", ["v8", "v9"])
async def test_both_versions_use_auth_and_bounded_request_boundary(settings, auth, version):
    provider = VersionedPlanner()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(settings, provider)), base_url="http://test"
    ) as api:
        path = f"/{version}/plan"
        assert (await api.post(path, content=b"not json")).status_code == 401
        assert (
            await api.post(path, headers=[*auth.items(), *auth.items()], json={"query": "x"})
        ).status_code == 401
        assert (await api.post(path, headers=auth, json={"query": "x" * 17000})).status_code == 413
        assert (
            await api.post(path + "?model=other", headers=auth, json={"query": "x"})
        ).status_code == 422
        assert (
            await api.post(path, headers=auth, json={"query": "x", "model": "other"})
        ).status_code == 422
        assert (
            await api.post(path, headers=auth | {"Content-Encoding": "gzip"}, json={"query": "x"})
        ).status_code == 422
    assert not provider.calls


@pytest.mark.parametrize("occupied_version", ["v7", "v8", "v9"])
async def test_shared_admission_slot_across_versions(settings, auth, occupied_version):
    settings.max_concurrent_requests = 1
    provider = VersionedPlanner()
    provider.release.clear()
    query = provider.plans[occupied_version].original_query
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(settings, provider)), base_url="http://test"
    ) as api:
        pending = asyncio.create_task(
            api.post(f"/{occupied_version}/plan", headers=auth, json={"query": query})
        )
        try:
            await asyncio.wait_for(provider.started.wait(), timeout=2)
            for path in [
                "/plan",
                "/v4/plan",
                "/v5/plan",
                "/v6/plan",
                "/v7/plan",
                "/v8/plan",
                "/v9/plan",
            ]:
                assert (await api.post(path, headers=auth, json={"query": "x"})).status_code == 503
            assert len(provider.calls) == 1
        finally:
            provider.release.set()
            response = await pending
        assert response.status_code == 200


@pytest.mark.parametrize("version", ["v8", "v9"])
async def test_shared_timeout_releases_slot(settings, auth, version):
    settings.timeout_seconds = 0.1
    provider = VersionedPlanner()
    provider.release.clear()
    query = provider.plans[version].original_query
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(settings, provider)), base_url="http://test"
    ) as api:
        assert (
            await api.post(f"/{version}/plan", headers=auth, json={"query": query})
        ).status_code == 503
        provider.release.set()
        assert (
            await api.post(f"/{version}/plan", headers=auth, json={"query": query})
        ).status_code == 200


async def test_all_agents_share_provider_and_keep_their_own_native_wire(provider_settings):
    provider = VersionedPlanner()
    replies = iter(provider.plans.values())
    calls = []

    def respond(request):
        calls.append(json.loads(request.content))
        return httpx.Response(
            200, json=completion(provider_settings, next(replies).model_dump_json())
        )

    client = StructuredModelClient(provider_settings, httpx.MockTransport(respond))
    try:
        assert client.research_v7_agent.model is client.research_v8_agent.model
        assert client.research_v8_agent.model is client.research_v9_agent.model
        for version, prompt, model in [
            ("v7", "v13", ResearchQueryPlanV7),
            ("v8", "v14", ResearchQueryPlanV8),
            ("v9", "v15", ResearchQueryPlanV9),
        ]:
            plan = provider.plans[version]
            before = len(calls)
            result = await getattr(client, f"plan_{version}")(
                PlanRequest(query=plan.original_query), date(2026, 10, 2)
            )
            assert type(result) is model
            assert result.model_dump() == plan.model_dump()
            assert len(calls) == before + 1 and not calls[-1].get("tools")
            native = calls[-1]["response_format"]["json_schema"]
            assert native["strict"] is True
            properties = native["schema"]["properties"]
            assert properties["group_by"]["type"] == ("array" if version == "v9" else "string")
            if version == "v8":
                assert properties["spatial"]["type"] == "array"
                assert "district" in properties["group_by"]["enum"]
            else:
                assert {"type": "null"} in properties["spatial"]["anyOf"]
            assert getattr(client, f"research_{version}_agent").name == f"research-planner-{prompt}"
        assert client.sdk.max_retries == 0
        assert not client.client.trust_env and not client.client.follow_redirects
    finally:
        await client.close()


@pytest.mark.parametrize("version", ["v8", "v9"])
@pytest.mark.parametrize("failure", ["malformed", "changed_query", "redirect", "rate_limit"])
async def test_client_errors_do_not_retry_fallback_or_leak(settings, version, failure):
    provider = VersionedPlanner()
    plan = provider.plans[version]
    calls = []

    def respond(request):
        calls.append(request)
        if failure in {"redirect", "rate_limit"}:
            return httpx.Response(
                307 if failure == "redirect" else 429,
                text="PRIVATE",
                headers={"Location": "https://example.com"},
            )
        content = (
            "{}"
            if failure == "malformed"
            else plan.model_copy(update={"original_query": "changed"}).model_dump_json()
        )
        return httpx.Response(200, json=completion(settings, content))

    client = StructuredModelClient(settings, httpx.MockTransport(respond))
    try:
        with pytest.raises(PlannerError) as error:
            await getattr(client, f"plan_{version}")(
                PlanRequest(query=plan.original_query), date(2026, 10, 2)
            )
        expected = (
            "planner_unavailable"
            if failure in {"redirect", "rate_limit"}
            else "planner_invalid_response"
        )
        assert error.value.code == expected
        assert "PRIVATE" not in str(error.value)
        assert len(calls) == 1
    finally:
        await client.close()
