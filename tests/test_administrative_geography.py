import json
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from research_planner.app import create_app
from research_planner.model_client import StructuredModelClient
from research_planner.research_v8_schema import ResearchQueryPlanV8
from research_planner.schemas import PlanRequest
from tests.test_model_client import completion
from tests.test_research_v7_contract import closed_objects
from tests.v7_live_diagnostics import REFERENCE_DATE

EXAMPLES = json.loads(Path("tests/fixtures/v8_administrative.json").read_text())


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda p: p["original_query"])
async def test_single_request_semantic_wire(settings, example):
    calls = []

    def respond(request):
        calls.append(json.loads(request.content))
        return httpx.Response(200, json=completion(settings, json.dumps(example)))

    client = StructuredModelClient(settings, httpx.MockTransport(respond))
    try:
        actual = await client.plan_v8(PlanRequest(query=example["original_query"]), REFERENCE_DATE)
        assert actual.model_dump(mode="json") == example
        assert len(calls) == 1 and not calls[0].get("tools") and client.sdk.max_retries == 0
    finally:
        await client.close()


def test_v8_contract_snapshot():
    schema = ResearchQueryPlanV8.model_json_schema()
    assert schema == json.loads(Path("tests/fixtures/v8_schema.json").read_text())
    closed_objects(schema)
    assert schema["properties"]["spatial"]["maxItems"] == 4


@pytest.mark.parametrize("key", ["osm_id", "ags", "official_code", "geometry", "resolved_id"])
def test_planner_cannot_invent_resolver_data(key):
    example = json.loads(json.dumps(EXAMPLES[0]))
    example["spatial"][0][key] = "invented"
    with pytest.raises(ValidationError):
        ResearchQueryPlanV8.model_validate_json(json.dumps(example))


def test_conjunction_is_closed_and_bounded():
    example = json.loads(json.dumps(EXAMPLES[6]))
    parsed = ResearchQueryPlanV8.model_validate_json(json.dumps(example))
    assert [(g.relation, g.area_level) for g in parsed.spatial] == [
        ("outside", "state"),
        ("inside", "country"),
    ]
    for value in [example["spatial"] * 3, {"or": example["spatial"]}, None]:
        with pytest.raises(ValidationError):
            ResearchQueryPlanV8.model_validate_json(json.dumps(example | {"spatial": value}))
    example["spatial"][0]["relation"] = "nearest"
    with pytest.raises(ValidationError, match="multiple_spatial_requires_membership"):
        ResearchQueryPlanV8.model_validate_json(json.dumps(example))


def test_expected_level_needs_an_area_and_rank_subject_agrees():
    example = json.loads(json.dumps(EXAMPLES[0]))
    example["spatial"][0]["area_query"] = None
    with pytest.raises(ValidationError, match="area_level_requires_area_query"):
        ResearchQueryPlanV8.model_validate_json(json.dumps(example))
    with pytest.raises(ValidationError, match="rank_entity_group_mismatch"):
        ResearchQueryPlanV8.model_validate_json(json.dumps(EXAMPLES[3] | {"entity_type": "state"}))


def test_versioned_route_preserves_legacy_endpoint(settings):
    paths = create_app(settings).openapi()["paths"]
    assert "/v8/plan" in paths and "/v7/plan" in paths
