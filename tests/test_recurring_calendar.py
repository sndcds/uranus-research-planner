"""Shared contract witnesses and mocked native boundary; not live model acceptance."""

import json
from datetime import date
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from research_planner.app import create_app
from research_planner.model_client import StructuredModelClient
from research_planner.research_v9_schema import ResearchQueryPlanV9
from research_planner.research_v10_schema import ResearchQueryPlanV10, TemporalV10
from research_planner.schemas import PlanRequest
from tests.conftest import FakePlanner
from tests.test_model_client import completion
from tests.test_research_v7_contract import closed_objects

CASES = json.loads(Path("tests/fixtures/recurring_calendar_v10.json").read_text())


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["name"])
async def test_calendar_and_audience_native_roundtrip(case, settings, auth):
    expected = ResearchQueryPlanV10.model_validate_json(json.dumps(case["plan"]))
    calls = []

    def respond(request):
        calls.append(json.loads(request.content))
        return httpx.Response(200, json=completion(settings, expected.model_dump_json()))

    model = StructuredModelClient(settings, httpx.MockTransport(respond))
    provider = FakePlanner()
    provider.plan_v10 = model.plan_v10
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app(settings, provider)),
            base_url="http://test",
        ) as api:
            response = await api.post(
                "/v10/plan", headers=auth, json={"query": expected.original_query}
            )
        assert response.status_code == 200, response.text
        assert response.json()["plan"] == case["plan"]
        assert response.json()["prompt_version"] == "research-planner-v16"
        assert len(calls) == 1 and not calls[0].get("tools")
        schema = calls[0]["response_format"]["json_schema"]
        assert schema["strict"] is True
        closed_objects(schema["schema"])
    finally:
        await model.close()


@pytest.mark.parametrize(
    "field,values",
    [
        ("recurring_weekdays", [0]),
        ("recurring_weekdays", [8]),
        ("recurring_weekdays", [True]),
        ("recurring_weekdays", ["7"]),
        ("recurring_weekdays", [7, 7]),
        ("recurring_weekdays", list(range(1, 9))),
        ("recurring_months", [0]),
        ("recurring_months", [13]),
        ("recurring_months", [7, 7]),
        ("recurring_months", [7.5]),
        ("recurring_months", ["7"]),
    ],
)
def test_invalid_calendar_sets(field, values):
    temporal = {**CASES[2]["plan"]["temporal"], field: values}
    with pytest.raises(ValidationError):
        TemporalV10.model_validate_json(json.dumps(temporal))


@pytest.mark.parametrize(
    "change",
    [
        {"field": "created_at"},
        {"field": "modified_at"},
        {"weekday": "sunday"},
        {"period": "explicit_range"},
        {"from_date": "2026-07-01"},
        {"extra": []},
    ],
)
def test_inconsistent_calendar(change):
    temporal = {**CASES[2]["plan"]["temporal"], **change}
    with pytest.raises(ValidationError):
        TemporalV10.model_validate_json(json.dumps(temporal))


def test_v9_stays_frozen_and_quantitative_semantic_stays_blocked():
    with pytest.raises(ValidationError):
        ResearchQueryPlanV9.model_validate_json(json.dumps(CASES[2]["plan"]))
    data = next(c["plan"] for c in CASES if c["name"] == "audience-count")
    with pytest.raises(ValidationError):
        ResearchQueryPlanV10.model_validate_json(json.dumps({**data, "unsupported_reason": None}))


async def test_changed_query_fails_once(settings):
    data = CASES[0]["plan"]
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(200, json=completion(settings, json.dumps(data)))

    model = StructuredModelClient(settings, httpx.MockTransport(respond))
    from research_planner.errors import PlannerError

    try:
        with pytest.raises(PlannerError):
            await model.plan_v10(PlanRequest(query="different input"), date(2026, 10, 3))
        assert len(calls) == 1
    finally:
        await model.close()


def test_schema_snapshot_and_prompt_versions():
    from research_planner.research_v7_prompts import RESEARCH_V7_PROMPT_VERSION
    from research_planner.research_v8_prompts import RESEARCH_V8_PROMPT_VERSION
    from research_planner.research_v9_prompts import RESEARCH_V9_PROMPT_VERSION
    from research_planner.research_v10_prompts import (
        RESEARCH_V10_PROMPT,
        RESEARCH_V10_PROMPT_VERSION,
    )

    assert (
        RESEARCH_V7_PROMPT_VERSION,
        RESEARCH_V8_PROMPT_VERSION,
        RESEARCH_V9_PROMPT_VERSION,
        RESEARCH_V10_PROMPT_VERSION,
    ) == (
        "research-planner-v13",
        "research-planner-v14",
        "research-planner-v15",
        "research-planner-v16",
    )
    assert canonical_schema(ResearchQueryPlanV10.model_json_schema()) == json.loads(
        Path("tests/fixtures/v10_schema.json").read_text()
    )
    assert "recurring_weekdays" in RESEARCH_V10_PROMPT and "recurring_months" in RESEARCH_V10_PROMPT
    assert "insufficient_structured_data" in RESEARCH_V10_PROMPT
    assert "missing year => needs_date" not in RESEARCH_V10_PROMPT


def canonical_schema(value):
    # Literal enum order can differ with Python's process-wide type interning.
    # Enum members are a set; preserve every other schema keyword/array exactly.
    if isinstance(value, dict):
        return {
            key: sorted(item) if key == "enum" else canonical_schema(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [canonical_schema(item) for item in value]
    return value
