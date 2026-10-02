"""Safe normal forms, invariant strict boundaries and real one-request integration."""

import json

import httpx
import pytest
from pydantic import TypeAdapter, ValidationError

from research_planner.errors import PlannerError
from research_planner.model_client import StructuredModelClient
from research_planner.research_v7_canonical import CanonicalModelOutputV7, ProposalV7
from research_planner.research_v7_schema import ResearchQueryPlanV7
from research_planner.schemas import PlanRequest
from tests.test_model_client import completion
from tests.v7_golden import example_plan, load_v7_golden_cases
from tests.v7_live_diagnostics import REFERENCE_DATE

CASES = {c.id: c for c in load_v7_golden_cases()}
ADAPTER = TypeAdapter(CanonicalModelOutputV7)


def normalize(value):
    return ResearchQueryPlanV7.model_validate_json(
        ADAPTER.validate_json(json.dumps(value)).model_dump_json()
    )


def test_canonical_adapter_keeps_exact_native_schema_and_proposal_field_constraints():
    expected = ResearchQueryPlanV7.model_json_schema()
    assert ADAPTER.json_schema() == expected
    proposal = ProposalV7.model_json_schema()
    assert proposal | {"title": expected["title"]} == expected


@pytest.mark.parametrize("case", CASES.values(), ids=lambda c: c.id)
def test_all_reviewed_witnesses_are_unchanged_and_idempotent(case):
    witness = example_plan(case)
    actual = normalize(witness.model_dump(mode="json"))
    assert actual == witness
    assert normalize(actual.model_dump(mode="json")) == actual


@pytest.mark.parametrize(
    "id,updates",
    [
        ("comparisons-058-007", {"taxonomy": "category"}),
        ("regressions-090-003", {"taxonomy": "event_type", "entity_type": "occurrence"}),
        ("regressions-090-004", {"taxonomy": "genre", "entity_type": "occurrence"}),
        ("comparisons-058-007", {"anomaly": {"kind": "outlier", "measure": None}}),
        (
            "organizations-053-002",
            {
                "relation": {
                    "operation": "related",
                    "source": "organization",
                    "target": "event",
                    "via": [],
                    "source_query": None,
                    "target_query": None,
                }
            },
        ),
        (
            "regressions-074-002",
            {
                "group_by": "genre",
                "metric": example_plan(CASES["comparisons-058-007"]).metric.model_dump(mode="json"),
            },
        ),
        (
            "comparisons-058-007",
            {
                "trend": {
                    "measure": "event_count",
                    "comparison": "previous_period",
                    "window": "week",
                    "change": "absolute_change",
                }
            },
        ),
    ],
)
async def test_safe_normal_forms_use_single_request_and_strict_final_plan(settings, id, updates):
    case = CASES[id]
    expected = example_plan(case)
    proposal = expected.model_dump(mode="json") | updates
    calls = []

    def respond(request):
        calls.append(json.loads(request.content))
        return httpx.Response(200, json=completion(settings, json.dumps(proposal)))

    client = StructuredModelClient(settings, httpx.MockTransport(respond))
    try:
        actual = await client.plan_v7(PlanRequest(query=case.question), REFERENCE_DATE)
        assert actual == expected
        assert ResearchQueryPlanV7.model_validate_json(actual.model_dump_json()) == actual
        assert len(calls) == 1 and not calls[0].get("tools") and client.sdk.max_retries == 0
    finally:
        await client.close()


@pytest.mark.parametrize(
    "update,error",
    [
        ({"taxonomy": "invented"}, "literal_error"),
        ({"anomaly": {"kind": "sql", "measure": None}}, "literal_error"),
        ({"answer": "invented"}, "extra_forbidden"),
        ({"metric": None}, "rank_requires_metric_order_and_limit"),
        ({"intent": "admin_user"}, "literal_error"),
        ({"semantic": {"query": "children", "focus": None}}, "semantic_exact_population_forbidden"),
        ({"limit": 21}, "less_than_equal"),
        ({"filters": [{"field": "price", "operator": "execute"}]}, "literal_error"),
        (
            {
                "relation": {
                    "operation": "related",
                    "source": "genre",
                    "target": "category",
                    "via": [],
                    "source_query": None,
                    "target_query": None,
                }
            },
            "unknown_relation_edge",
        ),
    ],
)
def test_normalization_does_not_hide_unknown_or_missing_semantics(update, error):
    value = example_plan(CASES["comparisons-058-007"]).model_dump(mode="json") | update
    with pytest.raises(ValidationError, match=error):
        normalize(value)


def test_taxonomy_dimension_is_not_inferred_from_grouping():
    value = example_plan(CASES["regressions-074-002"]).model_dump(mode="json")
    with pytest.raises(ValidationError, match="taxonomy_required"):
        normalize(value | {"taxonomy": None, "group_by": "genre"})


async def test_original_query_still_rejected_without_repair(settings):
    case = CASES["regressions-090-004"]
    value = example_plan(case).model_dump(mode="json") | {"original_query": "changed"}
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(200, json=completion(settings, json.dumps(value)))

    client = StructuredModelClient(settings, httpx.MockTransport(respond))
    try:
        with pytest.raises(PlannerError, match="planner_invalid_response"):
            await client.plan_v7(PlanRequest(query=case.question), REFERENCE_DATE)
        assert len(calls) == 1
    finally:
        await client.close()
