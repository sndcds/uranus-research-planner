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


def test_where_discovery_does_not_request_user_location():
    from tests.v7_golden import assert_v7_expectations

    case = CASES["regressions-092-013"]
    witness = example_plan(case)
    assert witness.entity_type == "event" and witness.clarification == "none"
    assert witness.spatial is None
    assert_v7_expectations(normalize(witness.model_dump(mode="json")), case)
    with pytest.raises(AssertionError, match="clarification"):
        assert_v7_expectations(witness.model_copy(update={"clarification": "needs_location"}), case)


def test_explicitly_undefined_diversity_has_no_guessed_dimension():
    witness = example_plan(CASES["combined-060-001"])
    empty = {name: None for name in CASES["regressions-090-004"].expect["metric"]}
    empty["operation"] = "diversity"
    value = witness.model_dump(mode="json") | {"metric": empty}
    assert normalize(value) == witness
    with pytest.raises(ValidationError, match="distinct_dimension_required"):
        ResearchQueryPlanV7.model_validate_json(json.dumps(value))
    for update in [{"clarification": "none"}, {"clarification": "needs_criteria"}]:
        with pytest.raises(ValidationError, match="distinct_dimension_required"):
            normalize(value | update)
    for update in [
        {"operation": "distinct_count"},
        {"field": "description"},
        {"window": "week"},
    ]:
        with pytest.raises(ValidationError, match="distinct_dimension_required"):
            normalize(value | {"metric": empty | update})
    for update in [{"field": "sql"}, {"invented": True}]:
        with pytest.raises(ValidationError):
            normalize(value | {"metric": empty | update})


def test_relation_order_is_neutral_but_known_count_is_preserved():
    witness = example_plan(CASES["taxonomy-049-007"])
    value = witness.model_dump(mode="json")
    count = example_plan(CASES["regressions-090-004"]).metric.model_dump(mode="json")
    actual = normalize(value | {"metric": count, "ordering": "desc", "limit": 20})
    assert actual.ordering is None and actual.metric.operation == "occurrence_count"
    assert actual.relation == witness.relation
    with pytest.raises(ValidationError, match="unexpected_ordering"):
        ResearchQueryPlanV7.model_validate_json(json.dumps(value | {"ordering": "desc"}))


def test_change_metric_only_belongs_to_trend_and_never_invents_one():
    witness = example_plan(CASES["trends-061-012"])
    change = example_plan(CASES["regressions-090-004"]).metric.model_dump(mode="json") | {
        "operation": "absolute_change",
        "measure": "event_count",
        "window": "month",
    }
    value = witness.model_dump(mode="json") | {"metric": change}
    assert normalize(value) == witness
    with pytest.raises(ValidationError, match="change_requires_trend"):
        ResearchQueryPlanV7.model_validate_json(json.dumps(value))
    with pytest.raises(ValidationError, match="measure_and_window_required"):
        normalize(value | {"metric": change | {"window": None}})


@pytest.mark.parametrize(
    "id,update,path",
    [
        (
            "geography-066-009",
            {"unsupported_reason": "insufficient_structured_data"},
            "unsupported_reason",
        ),
        ("taxonomy-048-007", {"clarification": "needs_definition"}, "clarification"),
    ],
)
def test_undefined_measure_and_missing_selection_are_distinct(id, update, path):
    from tests.v7_golden import assert_v7_expectations

    case = CASES[id]
    witness = example_plan(case)
    assert_v7_expectations(normalize(witness.model_dump(mode="json")), case)
    wrong = normalize(witness.model_dump(mode="json") | update)
    with pytest.raises(AssertionError, match=path):
        assert_v7_expectations(wrong, case)


def test_blocked_distance_retains_known_reference_concept():
    from tests.v7_golden import assert_v7_expectations

    case = CASES["geography-066-008"]
    value = example_plan(case).model_dump(mode="json")
    assert value["spatial"]["place_query"] == "Zentrum"
    assert value["clarification"] == "needs_definition"
    value["spatial"]["place_query"] = None
    with pytest.raises(AssertionError, match="spatial.place_query"):
        assert_v7_expectations(normalize(value), case)


@pytest.mark.parametrize("source", ["category", "event_type", "genre"])
@pytest.mark.parametrize("target", ["category", "event_type", "genre"])
@pytest.mark.parametrize("operation", ["shared", "related"])
def test_unanchored_taxonomy_cooccurrence_normal_form(source, target, operation):
    data = example_plan(CASES["taxonomy-049-007"]).model_dump(mode="json")
    data["relation"].update(source=source, target=target, operation=operation)
    actual = normalize(data)
    assert actual.relation.operation == ("shared" if source == target else "related")
    assert actual.relation.source == source and actual.relation.target == target
    assert actual.relation.via == ["event"]
    assert normalize(actual.model_dump(mode="json")) == actual


@pytest.mark.parametrize(
    "update",
    [
        {"source_query": "Jazz"},
        {"via": []},
        {"source": "organization"},
        {"operation": "invented"},
    ],
)
def test_relation_normal_form_never_repairs_other_shapes(update):
    data = example_plan(CASES["content-072-005"]).model_dump(mode="json")
    data["relation"].update(operation="shared")
    data["relation"].update(update)
    with pytest.raises(ValidationError):
        normalize(data)


@pytest.mark.parametrize("entity", [None, "occurrence", "event"])
def test_taxonomy_cooccurrence_population_follows_declared_event_path(entity):
    witness = example_plan(CASES["content-072-005"])
    data = witness.model_dump(mode="json") | {"entity_type": entity}
    assert normalize(data) == witness


def test_unsupported_taxonomy_relation_does_not_acquire_supported_subject():
    data = example_plan(CASES["content-072-005"]).model_dump(mode="json")
    data.update(entity_type=None, unsupported_reason="unsupported_constraint")
    assert normalize(data).entity_type is None


def test_frequency_qualified_cooccurrence_requires_no_undefined_method():
    from tests.v7_golden import compare_v7_expectations

    case = CASES["taxonomy-049-007"]
    witness = example_plan(case)
    assert witness.intent == "relation" and witness.clarification == "none"
    assert witness.relation.operation == "shared"
    wrong = normalize(witness.model_dump(mode="json") | {"clarification": "needs_definition"})
    assert [d.path for d in compare_v7_expectations(wrong, case)] == ["clarification"]


@pytest.mark.parametrize("id", ["regressions-091-010", "regressions-091-013"])
def test_venue_activity_rejects_distinct_event_count_substitution(id):
    from tests.v7_golden import compare_v7_expectations

    case = CASES[id]
    witness = example_plan(case)
    data = witness.model_dump(mode="json")
    assert witness.entity_type == "venue" and witness.group_by == "venue"
    assert witness.metric.operation == "occurrence_count"
    data["metric"]["operation"] = "event_count"
    assert [d.path for d in compare_v7_expectations(normalize(data), case)] == ["metric.operation"]


def test_singular_taxonomy_noun_preserves_top_one():
    from tests.v7_golden import compare_v7_expectations

    case = CASES["taxonomy-048-003"]
    witness = example_plan(case)
    assert witness.limit == 1 and witness.group_by == "category"
    wrong = normalize(witness.model_dump(mode="json") | {"limit": 20})
    assert [d.path for d in compare_v7_expectations(wrong, case)] == ["limit"]


@pytest.mark.parametrize(
    "operation",
    ["event_count", "occurrence_count", "venue_count", "space_count", "organization_count"],
)
def test_direct_count_has_no_nested_frequency_measure_or_window(operation):
    data = example_plan(CASES["trends-061-008"]).model_dump(mode="json")
    data["metric"] = example_plan(CASES["comparisons-058-007"]).metric.model_dump(mode="json")
    data["metric"].update(operation=operation, measure="event_count", window="week")
    actual = normalize(data)
    assert actual.metric.operation == operation
    assert actual.metric.measure is actual.metric.window is None
    with pytest.raises(ValidationError, match="measure_and_window_required"):
        ResearchQueryPlanV7.model_validate_json(json.dumps(data))
    data["metric"]["window"] = "century"
    with pytest.raises(ValidationError):
        normalize(data)


@pytest.mark.parametrize(
    "id",
    [
        "combined-060-010",
        "geography-066-002",
        "graph-064-006",
        "graph-064-007",
        "graph-064-008",
        "media-070-004",
        "quality-068-006",
        "trends-061-008",
    ],
)
def test_target_boundary_witness_retains_known_semantics(id):
    from tests.v7_golden import assert_v7_expectations

    case = CASES[id]
    witness = example_plan(case)
    assert witness.clarification == "needs_definition"
    assert witness.semantic is None
    assert_v7_expectations(normalize(witness.model_dump(mode="json")), case)
    if witness.intent == "anomaly":
        assert witness.anomaly is not None
    elif witness.intent == "relation":
        assert witness.relation.via == ["event"]
    elif id == "graph-064-008":
        assert witness.metric.distinct_by == "region" and witness.metric_filter.value == 1


def test_unselected_anomaly_dimension_is_not_an_executor_constraint():
    from tests.v7_golden import compare_v7_expectations

    case = CASES["combined-060-010"]
    witness = example_plan(case)
    assert witness.clarification == "needs_definition"
    assert witness.unsupported_reason is None and witness.group_by == "none"
    wrong = normalize(
        witness.model_dump(mode="json") | {"unsupported_reason": "unsupported_constraint"}
    )
    assert [d.path for d in compare_v7_expectations(wrong, case)] == ["unsupported_reason"]


@pytest.mark.parametrize(
    "id",
    [
        "regressions-090-012",
        "regressions-090-018",
        "regressions-091-021",
        "regressions-091-025",
    ],
)
def test_quantification_keeps_count_even_when_evidence_or_geography_is_needed(id):
    from tests.v7_golden import compare_v7_expectations

    case = CASES[id]
    witness = example_plan(case)
    assert witness.intent == "count" and witness.metric.operation == "event_count"
    data = witness.model_dump(mode="json")
    with pytest.raises(ValidationError, match="unexpected_metric"):
        normalize(data | {"intent": "list"})
    wrong = normalize(data | {"intent": "list", "metric": None})
    assert {"intent", "metric"} <= {d.path for d in compare_v7_expectations(wrong, case)}


def test_public_place_reference_cannot_be_substituted_with_a_venue_filter():
    from tests.v7_golden import compare_v7_expectations

    case = CASES["regressions-092-002"]
    witness = example_plan(case)
    assert witness.spatial.relation == "at" and witness.spatial.reference == "named"
    data = witness.model_dump(mode="json")
    wrong = normalize(
        data
        | {
            "spatial": None,
            "filters": [{"field": "venue", "operator": "eq", "value": witness.spatial.place_query}],
        }
    )
    assert "spatial" in {d.path for d in compare_v7_expectations(wrong, case)}


@pytest.mark.parametrize(
    "id", ["comparisons-045-001", "comparisons-058-001", "comparisons-058-006"]
)
def test_explicit_homogeneous_comparison_targets_define_subject_not_measure(id):
    witness = example_plan(CASES[id])
    data = witness.model_dump(mode="json") | {"entity_type": "event", "group_by": "none"}
    assert normalize(data) == witness
    assert normalize(data).comparison_targets == witness.comparison_targets
    missing = data | {"comparison_targets": [], "clarification": "needs_criteria"}
    actual = normalize(missing)
    assert actual.entity_type == "event" and actual.group_by == "none"
    unsupported = data | {"entity_type": None, "unsupported_reason": "unsupported_constraint"}
    assert normalize(unsupported).entity_type is None
    different = normalize(data | {"group_by": "category"})
    assert different.entity_type == "event" and different.group_by == "category"


@pytest.mark.parametrize("id", ["taxonomy-049-003", "taxonomy-049-007", "temporal-065-005"])
def test_quantity_cooccurrence_and_clock_profile_witnesses_remain_distinct(id):
    from tests.v7_golden import assert_v7_expectations

    case = CASES[id]
    witness = example_plan(case)
    assert_v7_expectations(normalize(witness.model_dump(mode="json")), case)
    if witness.intent == "rank":
        assert witness.anomaly is None and witness.ordering == "asc"
    elif witness.intent == "relation":
        assert witness.metric is None
    else:
        assert witness.metric.operation == "occurrence_count" and witness.group_by == "hour"


def test_unqualified_stale_records_keep_event_default_and_modified_time():
    from tests.v7_golden import compare_v7_expectations

    case = CASES["quality-068-010"]
    witness = example_plan(case)
    assert witness.entity_type == witness.group_by == "event"
    assert witness.intent == "rank" and witness.clarification == "needs_definition"
    assert witness.metric.operation == "value" and witness.metric.field == "modified_at"
    assert not compare_v7_expectations(normalize(witness.model_dump(mode="json")), case)
    data = witness.model_dump(mode="json")
    data["metric"]["field"] = "created_at"
    assert "metric.field" in {d.path for d in compare_v7_expectations(normalize(data), case)}


@pytest.mark.parametrize(
    "operation",
    ["event_count", "occurrence_count", "venue_count", "space_count", "organization_count"],
)
def test_direct_count_neutralizes_unused_projection_but_rejects_unknown_field(operation):
    data = example_plan(CASES["temporal-065-005"]).model_dump(mode="json")
    data["metric"].update(operation=operation, field="start_time")
    with pytest.raises(ValidationError, match="metric_field_required_or_unexpected"):
        ResearchQueryPlanV7.model_validate_json(json.dumps(data))
    assert normalize(data).metric.field is None
    assert normalize(data).metric.operation == operation
    data["metric"]["field"] = "arbitrary_column"
    with pytest.raises(ValidationError):
        normalize(data)


def test_filtered_scalar_count_cannot_be_repaired_by_guessing_intent():
    witness = example_plan(CASES["regressions-091-022"])
    assert witness.intent == "count" and witness.group_by == "none"
    assert witness.metric.operation == "event_count"
    assert witness.temporal.period == "explicit_range"
    data = witness.model_dump(mode="json") | {"intent": "aggregate"}
    with pytest.raises(ValidationError, match="aggregate_requires_metric_and_group"):
        normalize(data)
