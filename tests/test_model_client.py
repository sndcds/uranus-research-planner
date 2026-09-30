import asyncio
import json
import logging
from datetime import date

import httpx
import pytest

from research_planner.errors import PlannerError
from research_planner.model_client import StructuredModelClient
from research_planner.schemas import PlanRequest, ResearchQueryPlan
from research_planner.transport import MAX_MODEL_RESPONSE_BYTES, BoundedModelTransport
from tests.conftest import FIXTURES, MODEL_KEY, fixture_plan, make_plan


@pytest.fixture
def settings(provider_settings):
    """Run every client/transport regression against both provider policies."""
    return provider_settings


def completion(settings, content=None):
    return {
        "id": "chat-test",
        "object": "chat.completion",
        "created": 1,
        "model": settings.model,
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": content or make_plan().model_dump_json(),
                },
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
    }


@pytest.mark.parametrize("case", FIXTURES, ids=lambda case: case["id"])
async def test_pydanticai_parses_reviewed_outputs_without_llm(settings, case):
    expected = fixture_plan(case)
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(200, json=completion(settings, expected.model_dump_json()))

    client = StructuredModelClient(settings, httpx.MockTransport(respond))
    try:
        actual = await client.plan(PlanRequest(query=case["query"]), date(2026, 9, 29))
        assert actual == expected
        assert len(calls) == 1
        assert str(client.sdk.base_url) == settings.model_base_url + "/"
        assert str(calls[0].url) == settings.model_base_url + "/chat/completions"
        assert client.client.trust_env is False
        assert client.client.follow_redirects is False
        assert client.sdk.max_retries == 0
        body = json.loads(calls[0].content)
        if settings.model_provider == "groq":
            assert body["include_reasoning"] is False
        else:
            assert "include_reasoning" not in body
        assert "reasoning_effort" not in body
        assert "reasoning_format" not in body
        assert body["model"] == settings.model
        assert body["temperature"] == 0
        assert body.get("max_tokens", body.get("max_completion_tokens")) == 1200
        assert body["response_format"]["type"] == "json_schema"
        assert body["response_format"]["json_schema"]["strict"] is True
        schema = body["response_format"]["json_schema"]["schema"]
        assert set(schema["required"]) == set(ResearchQueryPlan.model_fields)
        assert schema["additionalProperties"] is False
        assert schema["$defs"]["ComparisonTarget"]["additionalProperties"] is False
        assert '"pattern"' not in json.dumps(schema)
        assert '"default"' not in json.dumps(schema)
        assert schema["properties"]["group_by"]["type"] == "string"
        assert "none" in schema["properties"]["group_by"]["enum"]
        assert {"type": "null"} in schema["properties"]["semantic_focus"]["anyOf"]
        assert not body.get("tools")
        assert not body.get("stream")
        user = json.loads(body["messages"][-1]["content"])
        assert user["query"] == case["query"]
        assert user["reference_date"] == "2026-09-29"
        assert calls[0].headers["authorization"] == "Bearer " + MODEL_KEY
        assert client.agent.instrument is False
    finally:
        await client.close()


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        "```json\n{}\n```",
        "[]",
        '{"intent":"list","intent":"count"}',
        '{"confidence":NaN}',
        '{"confidence":Infinity}',
        '{"intent":"query_users"}',
        '{"sql":"SELECT email FROM users"}',
        "<think>reasoning</think>{}",
    ],
)
async def test_invalid_output_fails_closed_without_retry(settings, content):
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(200, json=completion(settings, content))

    client = StructuredModelClient(settings, httpx.MockTransport(respond))
    try:
        with pytest.raises(PlannerError) as error:
            await client.plan(PlanRequest(query="events"), date(2026, 9, 29))
        assert error.value.code == "planner_invalid_response"
        assert len(calls) == 1
    finally:
        await client.close()


@pytest.mark.parametrize(
    "mutation", ["truncated", "tool", "refusal", "reasoning", "groq_reasoning", "model", "two"]
)
async def test_completion_envelope_is_not_trusted(settings, mutation):
    response = completion(settings)
    if mutation == "truncated":
        response["choices"][0]["finish_reason"] = "length"
    elif mutation in {"tool", "refusal", "reasoning", "groq_reasoning"}:
        key = {
            "tool": "tool_calls",
            "refusal": "refusal",
            "reasoning": "reasoning_content",
            "groq_reasoning": "reasoning",
        }[mutation]
        response["choices"][0]["message"][key] = "private model output"
    elif mutation == "model":
        response["model"] = "another-model"
    else:
        response["choices"] *= 2
    client = StructuredModelClient(
        settings, httpx.MockTransport(lambda request: httpx.Response(200, json=response))
    )
    try:
        with pytest.raises(PlannerError, match="planner_invalid_response"):
            await client.plan(PlanRequest(query="events"), date(2026, 9, 29))
    finally:
        await client.close()


@pytest.mark.parametrize("status", [301, 307, 401, 429, 500, 503])
async def test_no_redirect_no_retry_no_provider_error_leak(settings, status, caplog):
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(
            status,
            headers={"Location": "https://attacker.test"},
            text="PROVIDER SECRET " + MODEL_KEY,
        )

    client = StructuredModelClient(settings, httpx.MockTransport(respond))
    try:
        with caplog.at_level(logging.DEBUG), pytest.raises(PlannerError) as error:
            await client.plan(PlanRequest(query="private user query"), date(2026, 9, 29))
        assert error.value.code == "planner_unavailable"
        assert len(calls) == 1
        for secret in ("PROVIDER SECRET", MODEL_KEY, "private user query"):
            assert secret not in caplog.text + str(error.value)
    finally:
        await client.close()


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, text="<html>private provider text</html>"),
        httpx.Response(
            200,
            content=b"x" * (MAX_MODEL_RESPONSE_BYTES + 1),
            headers={"Content-Type": "application/json"},
        ),
        httpx.Response(
            200,
            content=b"{}",
            headers={"Content-Type": "application/json", "Content-Encoding": "unknown"},
        ),
    ],
)
async def test_response_bounds_and_type(settings, response):
    client = StructuredModelClient(settings, httpx.MockTransport(lambda request: response))
    try:
        with pytest.raises(PlannerError, match="planner_invalid_response"):
            await client.plan(PlanRequest(query="events"), date(2026, 9, 29))
    finally:
        await client.close()


async def test_total_deadline(settings):
    async def slow(request):
        await asyncio.sleep(0.2)
        return httpx.Response(200, json=completion(settings))

    settings.timeout_seconds = 0.1
    client = StructuredModelClient(settings, httpx.MockTransport(slow))
    try:
        with pytest.raises(PlannerError, match="planner_unavailable"):
            await client.plan(PlanRequest(query="events"), date(2026, 9, 29))
    finally:
        await client.close()


async def test_json_only_is_explicit_and_validated(settings):
    settings.output_mode = "json_object"
    calls = []

    def respond(request):
        calls.append(json.loads(request.content))
        return httpx.Response(200, json=completion(settings))

    client = StructuredModelClient(settings, httpx.MockTransport(respond))
    try:
        await client.plan(PlanRequest(query=make_plan().original_query), date(2026, 9, 29))
        assert calls[0]["response_format"]["type"] == "json_object"
        assert "ResearchQueryPlan" in json.dumps(calls[0]["messages"])
    finally:
        await client.close()


async def test_ready_checks_fixed_model(settings):
    for models, ready in [
        ([], False),
        ([{"id": "other"}], False),
        ([{"id": settings.model}], True),
    ]:
        client = StructuredModelClient(
            settings,
            httpx.MockTransport(
                lambda request, items=models: httpx.Response(200, json={"data": items})
            ),
        )
        try:
            assert await client.ready() is ready
        finally:
            await client.close()


@pytest.mark.parametrize(
    "url",
    [
        "https://attacker.test/v1/chat/completions",
        "http://127.0.0.1:8091/admin",
        "http://127.0.0.1:8091/v1/models?q=x",
    ],
)
async def test_transport_is_path_and_origin_allowlisted(settings, url):
    async def forbidden(request):
        pytest.fail("network must not be called")

    transport = BoundedModelTransport(settings, httpx.MockTransport(forbidden))
    with pytest.raises(PlannerError):
        await transport.handle_async_request(httpx.Request("GET", url))


async def test_sdk_environment_cannot_change_provider_or_forward_secrets(settings, monkeypatch):
    for name in ("OPENAI_BASE_URL", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
        monkeypatch.setenv(name, "https://public-provider.invalid")
    for name in ("OPENAI_API_KEY", "OPENAI_ORG_ID", "OPENAI_PROJECT_ID"):
        monkeypatch.setenv(name, "ENV_SECRET_NEVER_FORWARD")
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(200, json=completion(settings))

    client = StructuredModelClient(settings, httpx.MockTransport(respond))
    try:
        await client.plan(PlanRequest(query=make_plan().original_query), date(2026, 9, 29))
        assert str(calls[0].url) == settings.model_base_url + "/chat/completions"
        assert "ENV_SECRET" not in str(calls[0].headers) + calls[0].content.decode()
        assert client.client.trust_env is False
        assert client.client.follow_redirects is False
    finally:
        await client.close()


async def test_chunked_response_limit_closes_upstream(settings):
    class Chunks(httpx.AsyncByteStream):
        closed = False

        async def __aiter__(self):
            for _ in range(40):
                yield b" " * 1024

        async def aclose(self):
            self.closed = True

    chunks = Chunks()
    client = StructuredModelClient(
        settings,
        httpx.MockTransport(
            lambda request: httpx.Response(
                200, headers={"Content-Type": "application/json"}, stream=chunks
            )
        ),
    )
    try:
        with pytest.raises(PlannerError, match="planner_invalid_response"):
            await client.plan(PlanRequest(query="events"), date(2026, 9, 29))
        assert chunks.closed
    finally:
        await client.close()


@pytest.mark.parametrize("output_mode", ["json_schema", "json_object"])
@pytest.mark.parametrize(
    "mutation",
    [
        "accessibility",
        "free_admission",
        "interesting",
        "unsupported_constraint",
        "null_group_by",
        "null_time_of_day",
        "null_clarification",
        "missing_semantic_focus",
        "wrong_entity",
        "observed_live_output",
    ],
)
async def test_live_failure_regressions_are_not_repaired(settings, output_mode, mutation):
    case = next(case for case in FIXTURES if case["id"] == "count_past_kuehlhaus")
    data = fixture_plan(case).model_dump(mode="json")
    if mutation.startswith("null_"):
        data[mutation.removeprefix("null_")] = None
    elif mutation == "missing_semantic_focus":
        del data["semantic_focus"]
    elif mutation == "wrong_entity":
        data["entity_type"] = "venue"
    elif mutation == "observed_live_output":
        data["entity_type"] = "venue"
        del data["semantic_focus"]
        for field in ("group_by", "time_of_day", "clarification"):
            data[field] = None
        for field in (
            "accessibility",
            "free_admission",
            "family_suitable",
            "young_children",
            "teenagers",
            "creative",
            "interesting",
            "spannend",
            "similarity",
        ):
            data[field] = None
        data.update(external_research=False, unsupported_constraint=False)
    else:
        data[mutation] = None
    settings.output_mode = output_mode
    calls = []

    def respond(request):
        calls.append(json.loads(request.content))
        return httpx.Response(200, json=completion(settings, json.dumps(data)))

    client = StructuredModelClient(settings, httpx.MockTransport(respond))
    try:
        with pytest.raises(PlannerError) as error:
            await client.plan(PlanRequest(query=case["query"]), date(2026, 9, 29))
        assert error.value.code == "planner_invalid_response"
        assert error.value.status == 502
        assert len(calls) == 1
        assert calls[0]["response_format"]["type"] == output_mode
    finally:
        await client.close()


async def test_schema_rejection_does_not_downgrade_to_json_object(settings):
    calls = []

    def respond(request):
        calls.append(json.loads(request.content))
        return httpx.Response(400, json={"error": {"message": "schema unsupported"}})

    client = StructuredModelClient(settings, httpx.MockTransport(respond))
    try:
        with pytest.raises(PlannerError, match="planner_unavailable"):
            await client.plan(PlanRequest(query="events"), date(2026, 9, 29))
        assert len(calls) == 1
        assert calls[0]["response_format"]["type"] == "json_schema"
    finally:
        await client.close()


@pytest.mark.parametrize("output_mode", ["json_schema", "json_object"])
@pytest.mark.parametrize("case_id", ["count_venues", "organizations_area"])
async def test_observed_v2_failures_are_not_repaired(settings, output_mode, case_id):
    from tests.conftest import assert_golden_plan

    case = next(case for case in FIXTURES if case["id"] == case_id)
    expected = fixture_plan(case)
    mutation = {"temporal": "past"} if case_id == "count_venues" else {"intent": "search"}
    content = json.dumps(expected.model_dump(mode="json") | mutation)
    settings.output_mode = output_mode
    calls = []

    def respond(request):
        calls.append(json.loads(request.content))
        return httpx.Response(200, json=completion(settings, content))

    client = StructuredModelClient(settings, httpx.MockTransport(respond))
    try:
        if case_id == "organizations_area":
            with pytest.raises(PlannerError) as error:
                await client.plan(PlanRequest(query=case["query"]), date(2026, 9, 29))
            assert error.value.code == "planner_invalid_response"
            assert error.value.status == 502
        else:
            # Grammar/consistency cannot determine tense from language. The golden
            # evaluation detects the semantic error; runtime must never repair it.
            actual = await client.plan(PlanRequest(query=case["query"]), date(2026, 9, 29))
            assert actual.model_dump(mode="json") == json.loads(content)
            with pytest.raises(AssertionError):
                assert_golden_plan(actual, expected)
        assert len(calls) == 1
        assert calls[0]["response_format"]["type"] == output_mode
    finally:
        await client.close()


async def test_readiness_uses_authenticated_api_base_models_path(settings):
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(200, json={"data": [{"id": settings.model}]})

    client = StructuredModelClient(settings, httpx.MockTransport(respond))
    try:
        assert await client.ready() is True
        assert len(calls) == 1
        assert calls[0].method == "GET"
        assert str(calls[0].url) == settings.model_base_url + "/models"
        assert calls[0].headers["authorization"] == "Bearer " + MODEL_KEY
        assert calls[0].content == b""
    finally:
        await client.close()


@pytest.mark.parametrize(
    "failure", ["timeout", "connect", "json", "data", "oversize", "redirect", "error"]
)
async def test_readiness_fails_closed_without_retry_or_body_leak(settings, failure, caplog):
    calls = []
    secret = "PROVIDER_BODY_SECRET " + MODEL_KEY

    async def respond(request):
        calls.append(request)
        if failure == "timeout":
            await asyncio.sleep(0.2)
        if failure == "connect":
            raise httpx.ConnectError(secret)
        if failure == "json":
            return httpx.Response(200, content=secret, headers={"Content-Type": "application/json"})
        if failure == "data":
            return httpx.Response(200, json={"data": secret})
        if failure == "oversize":
            return httpx.Response(
                200,
                content=b"x" * (MAX_MODEL_RESPONSE_BYTES + 1),
                headers={"Content-Type": "application/json"},
            )
        if failure == "redirect":
            return httpx.Response(
                307, headers={"Location": "https://evil.example/models"}, text=secret
            )
        return httpx.Response(503, text=secret)

    settings.timeout_seconds = 0.1
    client = StructuredModelClient(settings, httpx.MockTransport(respond))
    try:
        with caplog.at_level(logging.DEBUG):
            assert await client.ready() is False
        assert len(calls) == 1
        assert secret not in caplog.text
        assert MODEL_KEY not in caplog.text
    finally:
        await client.close()


@pytest.mark.parametrize(
    "mutation",
    [
        "method",
        "models_post",
        "scheme",
        "host",
        "port",
        "userinfo",
        "query",
        "fragment",
        "path",
        "encoded",
    ],
)
async def test_transport_rejects_unexpected_destinations_before_auth(settings, mutation):
    url = httpx.URL(settings.endpoint.models_url)
    method = "GET"
    if mutation == "method":
        method = "DELETE"
    elif mutation == "models_post":
        method = "POST"
    elif mutation == "scheme":
        url = url.copy_with(scheme="ftp")
    elif mutation == "host":
        url = url.copy_with(host="api.groq.com.evil.example")
    elif mutation == "port":
        url = url.copy_with(port=8443)
    elif mutation == "userinfo":
        url = url.copy_with(username="injected", password="injected")
    elif mutation == "query":
        url = url.copy_with(query=b"x=1")
    elif mutation == "fragment":
        url = url.copy_with(fragment="fragment")
    elif mutation == "path":
        url = url.copy_with(path="/admin")
    else:
        url = url.copy_with(raw_path=url.raw_path.replace(b"models", b"%6dodels"))

    def forbidden(request):
        pytest.fail("rejected destination must never reach the network")

    transport = BoundedModelTransport(settings, httpx.MockTransport(forbidden))
    try:
        with pytest.raises(PlannerError, match="planner_unavailable"):
            await transport.handle_async_request(httpx.Request(method, url))
    finally:
        await transport.aclose()


@pytest.mark.parametrize("model", ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "another-model"])
async def test_reasoning_suppression_is_scoped_to_groq_gpt_oss(settings, model):
    settings.model = model
    calls = []

    def respond(request):
        calls.append(json.loads(request.content))
        return httpx.Response(200, json=completion(settings))

    client = StructuredModelClient(settings, httpx.MockTransport(respond))
    try:
        await client.plan(PlanRequest(query=make_plan().original_query), date(2026, 9, 29))
        assert calls[0]["model"] == model
        if settings.model_provider == "groq" and model != "another-model":
            assert calls[0]["include_reasoning"] is False
        else:
            assert "include_reasoning" not in calls[0]
        assert "reasoning_effort" not in calls[0]
        assert "reasoning_format" not in calls[0]
    finally:
        await client.close()


async def test_transport_replaces_untrusted_headers(settings):
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(200, json={"data": []})

    transport = BoundedModelTransport(settings, httpx.MockTransport(respond))
    try:
        response = await transport.handle_async_request(
            httpx.Request(
                "GET",
                settings.endpoint.models_url,
                headers={
                    "Authorization": "Bearer injected",
                    "Host": "evil.example",
                    "OpenAI-Organization": "injected",
                    "X-Model-Provider": "injected",
                },
            )
        )
        await response.aclose()
        assert calls[0].headers["authorization"] == "Bearer " + MODEL_KEY
        assert calls[0].headers["host"] == httpx.URL(settings.endpoint.models_url).netloc.decode()
        assert "injected" not in str(calls[0].headers)
    finally:
        await transport.aclose()


async def test_legacy_internal_origin_keeps_completion_and_readiness_paths():
    from research_planner.config import Settings
    from tests.conftest import KEY

    settings = Settings(
        model_url="http://127.0.0.1:8091",
        model_api_key=MODEL_KEY,
        service_api_key=KEY,
    )
    calls = []

    def respond(request):
        calls.append((request.method, str(request.url)))
        return httpx.Response(
            200,
            json=(
                {"data": [{"id": settings.model}]}
                if request.method == "GET"
                else completion(settings)
            ),
        )

    client = StructuredModelClient(settings, httpx.MockTransport(respond))
    try:
        assert await client.ready() is True
        assert (
            await client.plan(PlanRequest(query=make_plan().original_query), date(2026, 9, 29))
            == make_plan()
        )
        assert calls == [
            ("GET", "http://127.0.0.1:8091/v1/models"),
            ("POST", "http://127.0.0.1:8091/v1/chat/completions"),
        ]
    finally:
        await client.close()
