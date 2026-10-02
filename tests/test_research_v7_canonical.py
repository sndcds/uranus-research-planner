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


@pytest.mark.parametrize("id", ["regressions-091-026", "media-070-004"])
def test_known_daypart_and_unsupported_record_age_preserve_structural_witness(id):
    case = CASES[id]
    witness = example_plan(case)
    value = witness.model_dump(mode="json")
    assert normalize(value) == witness
    if id == "regressions-091-026":
        assert witness.temporal.period == "none"
        assert witness.temporal.time_of_day == "morning"
        from tests.v7_golden import assert_v7_expectations

        with pytest.raises(AssertionError, match="temporal"):
            assert_v7_expectations(normalize(value | {"temporal": None}), case)
    else:
        assert witness.intent == "rank" and witness.entity_type is None
        assert witness.metric.operation == "value" and witness.metric.field == "created_at"
        assert witness.unsupported_reason == "unsupported_constraint"
        assert witness.clarification == "needs_definition" and witness.semantic is None
        from tests.v7_golden import assert_v7_expectations

        with pytest.raises(AssertionError, match="clarification"):
            assert_v7_expectations(normalize(value | {"clarification": "none"}), case)
        with pytest.raises(ValidationError, match="data_intent_requires_entity"):
            normalize(value | {"unsupported_reason": None})


def test_unsupported_subject_does_not_become_an_entity_to_match_spurious_group():
    witness = example_plan(CASES["media-070-004"])
    value = witness.model_dump(mode="json")
    assert normalize(value | {"group_by": "event"}) == witness
    assert witness.entity_type is None and witness.unsupported_reason == "unsupported_constraint"
    with pytest.raises(ValidationError, match="rank_entity_group_mismatch"):
        ResearchQueryPlanV7.model_validate_json(json.dumps(value | {"group_by": "event"}))


@pytest.mark.parametrize(
    "id", ["temporal-050-009", "temporal-065-005", "trends-061-010", "trends-061-011"]
)
def test_approved_temporal_profile_defaults_preserve_explicit_choices(id):
    witness = example_plan(CASES[id])
    value = witness.model_dump(mode="json")
    assert normalize(value | {"ordering": None, "limit": None}) == witness
    explicit = normalize(value | {"ordering": "asc", "limit": 5})
    assert explicit.ordering == "asc" and explicit.limit == 5
    assert explicit.intent == "aggregate" and explicit.metric == witness.metric


@pytest.mark.parametrize("id", ["taxonomy-048-002", "prices-056-004", "temporal-041-003"])
def test_temporal_profile_defaults_do_not_spill_into_other_aggregates(id):
    witness = example_plan(CASES[id])
    assert normalize(witness.model_dump(mode="json")) == witness
    assert witness.ordering is witness.limit is None


def test_taxonomy_discovery_subject_is_the_event_population():
    witness = example_plan(CASES["regressions-091-002"])
    value = witness.model_dump(mode="json")
    assert witness.intent == "taxonomy" and witness.entity_type == "event"
    assert normalize(value | {"entity_type": None}) == witness
    with pytest.raises(ValidationError, match="data_intent_requires_entity"):
        ResearchQueryPlanV7.model_validate_json(json.dumps(value | {"entity_type": None}))


@pytest.mark.parametrize(
    "id,intent,entity,metric",
    [
        ("regressions-023-002", "list", "venue", None),
        ("regressions-023-001", "list", "event", None),
        ("regressions-074-007", "list", "event", None),
        ("regressions-091-007", "rank", "event", "event_count"),
        ("regressions-091-024", "list", "event", None),
        ("organizations-053-005", "list", "organization", None),
        ("venues-054-002", "list", "venue", None),
    ],
)
def test_subject_and_eligibility_rules_retain_existing_golden_semantics(id, intent, entity, metric):
    from tests.v7_golden import assert_v7_expectations

    case = CASES[id]
    witness = example_plan(case)
    assert_v7_expectations(normalize(witness.model_dump(mode="json")), case)
    assert witness.intent == intent and witness.entity_type == entity
    assert (witness.metric.operation if witness.metric else None) == metric
    assert witness.relation is None
    if id in {"regressions-023-002", "regressions-023-001", "regressions-074-007"}:
        assert witness.clarification == "needs_definition" and witness.temporal is None
        with pytest.raises(AssertionError, match="clarification"):
            assert_v7_expectations(witness.model_copy(update={"clarification": "none"}), case)
    if id == "regressions-091-024":
        assert witness.unsupported_reason == "unsupported_constraint"
    if id in {"organizations-053-005", "venues-054-002"}:
        assert witness.filters[0].field == "event_type"
