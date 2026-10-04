"""Ordered grouping contract, frozen v7, strict native output and trust boundaries."""

import hashlib
import json
from datetime import date
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from research_planner.app import create_app
from research_planner.model_client import StructuredModelClient
from research_planner.research_v9_canonical import CanonicalModelOutputV9
from research_planner.research_v9_schema import ResearchQueryPlanV9
from research_planner.schemas import PlanRequest
from tests.conftest import FakePlanner
from tests.test_model_client import completion
from tests.test_research_v7_contract import closed_objects
from tests.v7_golden import load_v7_golden_cases
from tests.v9_golden import compare_v9_expectations, example_plan, load_v9_golden_cases

CASES = load_v9_golden_cases()
SEASONAL = next(c for c in CASES if c.id == "trends-061-010")
APPROVED_OVERRIDES = {"trends-061-010", "provenance-071-004"}


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_migrated_witnesses(case):
    plan = example_plan(case)
    assert not compare_v9_expectations(plan, case)
    assert (
        CanonicalModelOutputV9.model_validate_json(plan.model_dump_json()).model_dump()
        == plan.model_dump()
    )


def test_only_product_decision_changes_golden_semantics():
    legacy = load_v7_golden_cases()
    assert set(json.loads(Path("tests/fixtures/v9_overrides.json").read_text())) == (
        APPROVED_OVERRIDES
    )
    assert len(CASES) == len(legacy) == 455
    for old, new in zip(legacy, CASES, strict=True):
        assert old.id == new.id and old.question == new.question
        if old.id in APPROVED_OVERRIDES:
            continue
        data = old.model_dump()
        for part in ("expect", "example"):
            if "group_by" in data[part]:
                value = data[part]["group_by"]
                data[part]["group_by"] = [] if value == "none" else [value]
        if "group_by" in data["forbid"]:
            data["forbid"]["group_by"] = [
                [] if value == "none" else [value] for value in data["forbid"]["group_by"]
            ]
        assert new.model_dump() == data


@pytest.mark.parametrize(
    "dimensions",
    [
        ["event_type", "month"],
        ["genre", "month"],
        ["category", "municipality"],
        ["month", "event_type"],
        ["event_type"],
    ],
)
def test_ordered_dimensions(dimensions):
    data = example_plan(SEASONAL).model_dump(mode="json")
    data["group_by"] = dimensions
    plan = ResearchQueryPlanV9.model_validate_json(json.dumps(data))
    assert plan.group_by == dimensions
    assert plan.metric.operation == "occurrence_count"
    assert plan.clarification == "none" and plan.unsupported_reason is None


@pytest.mark.parametrize(
    "dimensions",
    [
        ["month", "month"],
        ["sql"],
        ["none"],
        "month",
        ["genre", "month", "year", "weekday"],
    ],
)
def test_invalid_dimensions(dimensions):
    data = example_plan(SEASONAL).model_dump(mode="json")
    data["group_by"] = dimensions
    for model in (ResearchQueryPlanV9, CanonicalModelOutputV9):
        with pytest.raises(ValidationError):
            model.model_validate_json(json.dumps(data))


def test_frozen_v7_and_closed_v9_snapshot():
    for name, digest in json.loads(Path("tests/fixtures/v9_v7_freeze.json").read_text()).items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest
    schema = ResearchQueryPlanV9.model_json_schema()
    # Literal interning may change enum order when another version is imported first.
    # Use the same enum-only canonicalization as v10-v13; all other schema details
    # and the frozen v7 source digests above remain exact.
    from tests.test_recurring_calendar import canonical_schema

    assert canonical_schema(schema) == canonical_schema(
        json.loads(Path("tests/fixtures/v9_schema.json").read_text())
    )
    closed_objects(schema)
    assert CanonicalModelOutputV9.model_json_schema() == schema


async def test_native_v9_and_endpoint(settings, auth):
    expected = example_plan(SEASONAL)
    calls = []

    def respond(request):
        calls.append(json.loads(request.content))
        return httpx.Response(200, json=completion(settings, expected.model_dump_json()))

    client = StructuredModelClient(settings, httpx.MockTransport(respond))
    try:
        plan = await client.plan_v9(PlanRequest(query=SEASONAL.question), date(2026, 10, 2))
        assert not compare_v9_expectations(plan, SEASONAL)
        assert len(calls) == 1 and not calls[0].get("tools")
        native = calls[0]["response_format"]["json_schema"]
        assert native["strict"] is True
        assert native["schema"]["properties"]["group_by"]["type"] == "array"
        provider = FakePlanner()

        async def answer(request, reference):
            return expected

        provider.plan_v9 = answer
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app(settings, provider)),
            base_url="http://test",
        ) as api:
            assert (await api.post("/v9/plan", json={"query": "x"})).status_code == 401
            response = await api.post("/v9/plan", headers=auth, json={"query": SEASONAL.question})
            assert response.status_code == 200
            assert response.json()["schema_version"] == "research-query-plan-v9"
            assert response.json()["plan"]["group_by"] == ["event_type", "month"]
            expected.original_query = "changed"
            assert (
                await api.post("/v9/plan", headers=auth, json={"query": SEASONAL.question})
            ).status_code == 502
    finally:
        await client.close()
