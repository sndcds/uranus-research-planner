"""Offline acceptance diagnostics: all model HTTP is mocked, including opt-in paths."""

import json
import logging

import httpx
import pytest
from pydantic import ValidationError
from pydantic_ai.exceptions import UnexpectedModelBehavior, UsageLimitExceeded

from research_planner.app import create_app
from research_planner.errors import PlannerError
from research_planner.model_client import StructuredModelClient
from research_planner.research_v7_schema import ResearchQueryPlanV7
from scripts import run_v7_live_acceptance as runner
from tests.conftest import KEY, MODEL_KEY
from tests.test_model_client import completion
from tests.v7_comparison import Difference, brief_differences, structural_diff
from tests.v7_golden import (
    assert_v7_expectations,
    compare_v7_expectations,
    example_plan,
    load_v7_golden_cases,
)
from tests.v7_live_diagnostics import (
    REFERENCE_DATE,
    LiveCaseDiagnostic,
    LiveSession,
    Observation,
    ObservingTransport,
    build_report,
    debug_enabled,
    git_sha,
    invalid_details,
    write_report,
)

CASES = {c.id: c for c in load_v7_golden_cases()}
CASE = CASES["ranking-039-004"]


@pytest.fixture
def live_debug(monkeypatch):
    monkeypatch.setenv("RESEARCH_PLANNER_LIVE_TEST", "1")
    monkeypatch.setenv("RESEARCH_PLANNER_LIVE_DEBUG", "1")


def test_exact_pass_and_strict_assertion():
    plan = example_plan(CASE)
    assert compare_v7_expectations(plan, CASE) == []
    assert_v7_expectations(plan, CASE)


def test_intent_mismatch_is_structured_and_bounded():
    value = example_plan(CASE).model_dump(mode="json") | {"intent": "aggregate"}
    plan = ResearchQueryPlanV7.model_validate_json(json.dumps(value))
    differences = compare_v7_expectations(plan, CASE)
    assert differences == [
        Difference(path="intent", expected="rank", actual="aggregate", kind="mismatch")
    ]
    with pytest.raises(AssertionError, match="path=intent expected=rank actual=aggregate"):
        assert_v7_expectations(plan, CASE)
    assert CASE.question not in brief_differences(CASE.id, differences)


def test_nested_missing_forbidden_and_stable_ordering():
    case = CASES["geography-051-011"].model_copy(deep=True)
    plan = example_plan(case)
    case.expect = {"spatial.relation": "inside", "intent": "rank"}
    case.forbid = {"intent": ["list"]}
    differences = compare_v7_expectations(plan, case)
    assert [(d.path, d.kind) for d in differences] == [
        ("intent", "forbidden_value"),
        ("intent", "mismatch"),
        ("spatial.relation", "mismatch"),
    ]
    assert differences[-1].expected == "inside" and differences[-1].actual == "within_radius"
    missing = compare_v7_expectations(plan.model_copy(update={"spatial": None}), case)
    assert missing[-1].kind == "missing" and missing[-1].actual is None
    assert structural_diff("filters", [], [{"field": "venue", "operator": "missing"}])
    assert structural_diff("price", {"mode": "free"}, {"mode": "free", "currency": None})


class Chunks(httpx.AsyncByteStream):
    def __init__(self, data):
        self.data = data
        self.closed = False

    async def __aiter__(self):
        for start in range(0, len(self.data), 127):
            yield self.data[start : start + 127]

    async def aclose(self):
        self.closed = True


@pytest.mark.parametrize("streamed", [False, True])
@pytest.mark.parametrize(
    "mutation,stage",
    [
        ("metric", "pydantic_validation_error"),
        ("original_query", "post_validation_error"),
        ("json", "invalid_json"),
        ("outer_json", "invalid_json"),
        ("duplicate", "invalid_json"),
        ("truncated", "truncated_output"),
        ("refusal", "structured_output_error"),
        ("tools", "structured_output_error"),
    ],
)
async def test_real_client_failure_classification(settings, live_debug, streamed, mutation, stage):
    value = example_plan(CASE).model_dump(mode="json")
    if mutation == "metric":
        value["metric"] = None
    if mutation == "original_query":
        value["original_query"] = "altered"
    content = json.dumps(value)
    if mutation == "json":
        content = "not JSON"
    if mutation == "duplicate":
        content = '{"intent":"list","intent":"rank"}'
    reply = completion(settings, content)
    reply["usage"] = {"completion_tokens": 1200, "prompt_tokens": 999}
    reply["id"] = "sensitive-provider-id"
    reply["private_metadata"] = {"Authorization": "Bearer " + MODEL_KEY}
    if mutation == "truncated":
        reply["choices"][0]["finish_reason"] = "length"
        reply["choices"][0]["message"]["content"] = '{"intent":'
    if mutation == "refusal":
        reply["choices"][0]["message"]["refusal"] = "Authorization " + KEY
    if mutation == "tools":
        reply["choices"][0]["message"]["tool_calls"] = [{"name": "fetch"}]
    body = b"broken" if mutation == "outer_json" else json.dumps(reply).encode()
    chunks = Chunks(body)
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(
            200,
            headers={"Content-Type": "application/json", "Set-Cookie": KEY},
            **({"stream": chunks} if streamed else {"content": body}),
        )

    session = LiveSession(settings, httpx.MockTransport(respond))
    try:
        outcome = await session.run_case(CASE)
        assert outcome.status == "invalid_response" and outcome.validation_stage == stage
        assert outcome.safe_error_code == "planner_invalid_response"
        assert len(calls) == 1
        assert session.observer.observation.content is None
        if stage.endswith("validation_error"):
            assert outcome.validation_errors
            assert set(outcome.validation_errors[0].model_dump()) == {"loc", "type", "msg"}
            assert "input" not in outcome.validation_errors[0].model_dump()
        if mutation == "truncated":
            assert outcome.finish_reason == "length" and outcome.output_tokens == 1200
        for prohibited in [
            KEY,
            MODEL_KEY,
            "Authorization",
            "Bearer",
            "sensitive-provider-id",
            "private_metadata",
            "prompt_tokens",
        ]:
            assert prohibited not in outcome.model_dump_json()
    finally:
        await session.close()
    if streamed:
        assert chunks.closed


@pytest.mark.parametrize(
    "identifier,changes,reason",
    [
        ("regressions-074-005", {"clarification": "none"}, "deictic_geography_requires_location"),
        (
            "accessibility-020-002",
            {"unsupported_reason": None},
            "semantic_exact_population_forbidden",
        ),
        ("relations-040-001", {"relation": None}, "relation_required"),
        ("trends-061-003", {"trend": None}, "trend_required_or_unexpected"),
        (
            "prices-056-002",
            {"price": {"mode": "between", "minimum": 20, "maximum": 10, "currency": "EUR"}},
            "between_requires_ordered_price_bounds",
        ),
    ],
)
async def test_cross_field_reasons_visible(settings, live_debug, identifier, changes, reason):
    case = CASES[identifier]
    content = example_plan(case).model_dump(mode="json") | changes
    session = LiveSession(
        settings,
        httpx.MockTransport(
            lambda r: httpx.Response(200, json=completion(settings, json.dumps(content)))
        ),
    )
    try:
        result = await session.run_case(case)
        assert result.validation_stage == "pydantic_validation_error"
        assert any(reason in e.msg for e in result.validation_errors)
    finally:
        await session.close()


@pytest.mark.parametrize(
    "cause,stage",
    [
        (UsageLimitExceeded("Authorization Bearer " + MODEL_KEY), "usage_limit_error"),
        (UnexpectedModelBehavior("private", body=KEY), "unexpected_model_behavior"),
    ],
)
def test_exception_types_only_never_exception_payload(cause, stage):
    error = PlannerError("planner_invalid_response", 502)
    error.__context__ = cause
    got, details, raw = invalid_details(error, Observation(), CASE.question)
    assert got == stage and not details and raw is None


async def test_secret_redaction_in_valid_and_invalid_plan_fields(
    settings, live_debug, caplog, capsys
):
    case = CASE.model_copy(update={"question": "query " + KEY})
    value = example_plan(case).model_dump(mode="json")
    value["filters"] = [{"field": "venue", "operator": "eq", "value": "Bearer " + MODEL_KEY}]
    responses = [value, value | {"metric": None}]
    session = LiveSession(
        settings,
        httpx.MockTransport(
            lambda r: httpx.Response(200, json=completion(settings, json.dumps(responses.pop(0))))
        ),
    )
    try:
        results = [await session.run_case(case), await session.run_case(case)]
        payload = build_report(results, session.model, REFERENCE_DATE, debug=True).model_dump_json()
        for secret in (KEY, MODEL_KEY, "Bearer", "Authorization"):
            assert secret not in payload and secret not in caplog.text
            captured = capsys.readouterr()
            assert secret not in captured.out + captured.err
        assert "[redacted]" in payload
    finally:
        await session.close()


@pytest.mark.parametrize("debug", [False, True])
async def test_pass_mismatch_provider_error_and_report_counts(
    settings, live_debug, monkeypatch, tmp_path, debug
):
    if not debug:
        monkeypatch.delenv("RESEARCH_PLANNER_LIVE_DEBUG")
    value = example_plan(CASE).model_dump(mode="json")
    replies = [
        httpx.Response(200, json=completion(settings, json.dumps(value))),
        httpx.Response(200, json=completion(settings, json.dumps(value | {"intent": "aggregate"}))),
        httpx.Response(503, text="Authorization Bearer " + MODEL_KEY),
        httpx.Response(200, json=completion(settings, '{"metric":null}')),
    ]
    session = LiveSession(settings, httpx.MockTransport(lambda r: replies.pop(0)))
    try:
        outcomes = [await session.run_case(CASE) for _ in range(4)]
        assert [o.status for o in outcomes] == [
            "pass",
            "mismatch",
            "provider_error",
            "invalid_response",
        ]
        assert outcomes[0].actual == value and outcomes[0].differences == []
        if not debug:
            assert session.observer is None and outcomes[-1].validation_stage is None
        report = build_report(outcomes, session.model, REFERENCE_DATE, debug=debug)
        assert (report.total, report.passed, report.failed) == (4, 1, 3)
        assert report.by_category["ranking"].model_dump() == dict(
            total=4, passed=1, mismatch=1, invalid_response=1, provider_error=1
        )
        assert report.by_capability_status["planned"] == report.by_category["ranking"]
        assert report.by_difference_path == {"intent": 1}
        assert not list(tmp_path.iterdir())
        output = tmp_path / "explicit" / "report.json"
        write_report(report, output)
        first = output.read_bytes()
        write_report(report, output)
        assert first == output.read_bytes()
        assert output.stat().st_mode & 0o777 == 0o600
        assert json.loads(first)["cases"][0]["expected"] == {
            "expect": CASE.expect,
            "forbid": CASE.forbid,
            "resolver_name_variants": CASE.resolver_name_variants,
        }
        assert set(p.name for p in output.parent.iterdir()) == {"report.json"}
    finally:
        await session.close()


def test_filters_preserve_corpus_order_and_reject_unknown_empty():
    cases = load_v7_golden_cases()
    assert len(runner.select_cases(cases, identifiers=[], categories=[], capabilities=[])) == 455
    ids = [c.id for c in cases if c.category == "trends"][:2]
    chosen = runner.select_cases(
        cases, identifiers=ids[::-1], categories=["trends"], capabilities=[]
    )
    assert [c.id for c in chosen] == ids
    assert runner.select_cases(
        cases, identifiers=[CASE.id], categories=["ranking"], capabilities=["planned"]
    ) == [CASE]
    for ids, categories in [(["unknown"], []), ([CASE.id], ["trends"])]:
        with pytest.raises(ValueError):
            runner.select_cases(cases, identifiers=ids, categories=categories, capabilities=[])


def test_debug_alone_cannot_capture_or_create_artifact(settings, monkeypatch, tmp_path, capsys):
    monkeypatch.delenv("RESEARCH_PLANNER_LIVE_TEST", raising=False)
    monkeypatch.setenv("RESEARCH_PLANNER_LIVE_DEBUG", "1")
    assert not debug_enabled()
    with pytest.raises(ValueError):
        LiveSession(settings, httpx.MockTransport(lambda r: pytest.fail("unexpected call")))
    with pytest.raises(ValueError):
        ObservingTransport(httpx.MockTransport(lambda r: pytest.fail("unexpected call")))
    assert runner.main(["--output", str(tmp_path / "report.json")]) == 2
    assert not list(tmp_path.iterdir())
    assert "RESEARCH_PLANNER_LIVE_TEST=1" in capsys.readouterr().err


@pytest.mark.parametrize("live", [False, True])
async def test_production_error_surface_unchanged_with_debug_env(
    settings, auth, monkeypatch, caplog, live
):
    monkeypatch.setenv("RESEARCH_PLANNER_LIVE_DEBUG", "1")
    if live:
        monkeypatch.setenv("RESEARCH_PLANNER_LIVE_TEST", "1")
    else:
        monkeypatch.delenv("RESEARCH_PLANNER_LIVE_TEST", raising=False)
    caplog.set_level(logging.DEBUG)
    bad = example_plan(CASE).model_dump(mode="json") | {"metric": None, "private": MODEL_KEY}
    client = StructuredModelClient(
        settings,
        httpx.MockTransport(
            lambda r: httpx.Response(200, json=completion(settings, json.dumps(bad)))
        ),
    )
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app(settings, client)), base_url="http://test"
        ) as api:
            response = await api.post("/v7/plan", headers=auth, json={"query": CASE.question})
        assert response.status_code == 502
        assert response.json()["error"]["code"] == "planner_invalid_response"
        for sensitive in [
            KEY,
            MODEL_KEY,
            CASE.question,
            "rank_requires_metric",
            "validation_errors",
        ]:
            assert sensitive not in response.text and sensitive not in caplog.text
    finally:
        await client.close()


def test_report_models_forbid_extras():
    with pytest.raises(ValidationError):
        Difference(path="intent", expected="rank", actual="list", kind="mismatch", extra="bad")
    assert LiveCaseDiagnostic.model_config["extra"] == "forbid"


def test_git_sha_absence_is_not_failure(monkeypatch):
    def unavailable(*args, **kwargs):
        raise OSError("sensitive")

    monkeypatch.setattr("tests.v7_live_diagnostics.subprocess.run", unavailable)
    assert git_sha() is None


@pytest.mark.parametrize("failed", [False, True])
def test_cli_writes_complete_report_and_correct_exit_code(
    settings, live_debug, monkeypatch, tmp_path, capsys, failed
):
    case = LiveCaseDiagnostic(
        case_id=CASE.id,
        category=CASE.category,
        capability_status=CASE.capability_status,
        question=CASE.question,
        status="provider_error" if failed else "pass",
        expected={"expect": CASE.expect, "forbid": CASE.forbid},
        actual=None if failed else example_plan(CASE).model_dump(mode="json"),
        differences=[],
        validation_stage=None,
        validation_errors=[],
        model_output=None,
        finish_reason=None,
        output_tokens=None,
        safe_error_code="planner_unavailable" if failed else None,
    )
    report = build_report([case], settings.model, REFERENCE_DATE, debug=True)
    seen = []

    async def mock_run(config, cases, reference, commit):
        seen.extend(c.id for c in cases)
        assert reference == REFERENCE_DATE
        return report

    monkeypatch.setattr(runner, "Settings", lambda: settings)
    monkeypatch.setattr(runner, "run_cases", mock_run)
    output = tmp_path / "explicit.json"
    assert runner.main(
        [
            "--output",
            str(output),
            "--case",
            CASE.id,
            "--category",
            "ranking",
            "--capability",
            "planned",
        ]
    ) == int(failed)
    assert seen == [CASE.id]
    assert json.loads(output.read_text())["failed"] == int(failed)
    captured = capsys.readouterr()
    assert CASE.question not in captured.out and not captured.err
    assert MODEL_KEY not in captured.out


def test_cli_no_implicit_output_and_no_config_exception_dump(
    live_debug, monkeypatch, tmp_path, capsys
):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit):
        runner.main([])
    assert not list(tmp_path.iterdir())

    def broken_settings():
        raise ValueError("Authorization Bearer " + KEY + MODEL_KEY)

    monkeypatch.setattr(runner, "Settings", broken_settings)
    assert runner.main(["--output", str(tmp_path / "report.json")]) == 2
    assert not list(tmp_path.iterdir())
    captured = capsys.readouterr()
    assert all(
        secret not in captured.out + captured.err
        for secret in (KEY, MODEL_KEY, "Authorization", "Bearer")
    )


async def test_sequential_full_corpus_report_with_real_client_mocked_http(
    settings, live_debug, monkeypatch
):
    cases = load_v7_golden_cases()
    pending = iter(cases)
    calls = []

    def respond(request):
        case = next(pending)
        user = json.loads(json.loads(request.content)["messages"][-1]["content"])
        assert user["query"] == case.question
        assert user["reference_date"] == REFERENCE_DATE.isoformat()
        calls.append(case.id)
        return httpx.Response(200, json=completion(settings, example_plan(case).model_dump_json()))

    class MockSession(LiveSession):
        def __init__(self, config):
            super().__init__(config, httpx.MockTransport(respond))

    monkeypatch.setattr(runner, "LiveSession", MockSession)
    report = await runner.run_cases(settings, cases, REFERENCE_DATE, None)
    assert report.total == report.passed == 455 and report.failed == 0
    assert calls == [c.case_id for c in report.cases] == [c.id for c in cases]
    assert sum(c.total for c in report.by_category.values()) == 455
    assert sum(c.total for c in report.by_capability_status.values()) == 455


async def test_pytest_live_failures_stay_failures_with_optional_artifact(
    settings, live_debug, monkeypatch, tmp_path
):
    from tests import test_research_v7_live as live_test

    class MockSession(LiveSession):
        def __init__(self, config):
            value = example_plan(CASE).model_dump(mode="json") | {"metric": None}
            super().__init__(
                config,
                httpx.MockTransport(
                    lambda r: httpx.Response(200, json=completion(settings, json.dumps(value)))
                ),
            )

    monkeypatch.setattr(live_test, "Settings", lambda: settings)
    monkeypatch.setattr(live_test, "LiveSession", MockSession)
    monkeypatch.setenv("RESEARCH_PLANNER_LIVE_REPORT_DIR", str(tmp_path))
    with pytest.raises(
        pytest.fail.Exception, match="status=invalid_response stage=pydantic_validation_error"
    ):
        await live_test.test_live_v7_language_acceptance(CASE)
    artifact = json.loads((tmp_path / f"{CASE.id}.json").read_text())
    assert artifact["failed"] == 1 and artifact["cases"][0]["validation_errors"]


def test_nested_difference_path_rollup_and_bounded_message():
    differences = structural_diff(
        "price", {"minimum": 5, "maximum": 10}, {"minimum": 1, "maximum": 9}
    )
    case = LiveCaseDiagnostic(
        case_id=CASE.id,
        category=CASE.category,
        capability_status=CASE.capability_status,
        question=CASE.question,
        status="mismatch",
        expected={"expect": {}, "forbid": {}},
        actual={},
        differences=differences,
        validation_stage=None,
        validation_errors=[],
        model_output=None,
        finish_reason=None,
        output_tokens=None,
        safe_error_code=None,
    )
    report = build_report([case], "mock", REFERENCE_DATE, debug=False)
    assert report.by_difference_path == {"price": 2, "price.maximum": 1, "price.minimum": 1}
    secret = Difference(path="original_query", expected=KEY, actual=MODEL_KEY, kind="mismatch")
    assert KEY not in repr(secret) and MODEL_KEY not in repr(secret)
    message = brief_differences(CASE.id, [secret] * 100)
    assert KEY not in message and MODEL_KEY not in message and len(message) < 1000


@pytest.mark.parametrize("mutation", ["oversized", "deep", "overflow"])
async def test_unsafe_raw_output_is_bounded_and_does_not_abort_report(
    settings, live_debug, mutation
):
    value = example_plan(CASE).model_dump(mode="json")
    if mutation == "oversized":
        value["original_query"] = "x" * 40000
    else:
        nested = "text"
        for _ in range(40):
            nested = {"invalid": nested}
        value["semantic"] = nested
    content = json.dumps(value)
    if mutation == "overflow":
        value = example_plan(CASES["prices-056-002"]).model_dump(mode="json")
        content = json.dumps(value).replace('"maximum": 10.0', '"maximum": 1e999')
        assert "1e999" in content
    body = json.dumps(completion(settings, content)).encode()
    session = LiveSession(
        settings,
        httpx.MockTransport(
            lambda r: httpx.Response(
                200, headers={"Content-Type": "application/json"}, stream=Chunks(body)
            )
        ),
    )
    try:
        result = await session.run_case(CASE)
        assert result.status == "invalid_response"
        serialized = build_report(
            [result], session.model, REFERENCE_DATE, debug=True
        ).model_dump_json()
        assert len(serialized) < 10000
    finally:
        await session.close()
