"""Semantic witnesses and conservative normalization; no live provider dependencies."""

import json
from copy import deepcopy
from datetime import date

import httpx
import pytest
from pydantic import ValidationError

from research_planner.errors import PlannerError
from research_planner.model_client import StructuredModelClient
from research_planner.research_v9_canonical import CanonicalModelOutputV9
from research_planner.research_v9_prompts import RESEARCH_V9_PROMPT
from research_planner.research_v9_schema import ResearchQueryPlanV9
from research_planner.schemas import PlanRequest
from tests.test_model_client import completion
from tests.v7_golden import load_v7_golden_cases
from tests.v9_golden import compare_v9_expectations, example_plan, load_v9_golden_cases

CASES = {c.id: c for c in load_v9_golden_cases()}


def witness(identifier):
    return example_plan(CASES[identifier]).model_dump(mode="json")


def validate(data, model=CanonicalModelOutputV9):
    return model.model_validate_json(
        json.dumps(data), context={"original_query": data["original_query"]}
    )


def metric(operation, **operands):
    return (
        dict(
            operation=operation,
            field=None,
            distinct_by=None,
            numerator=None,
            denominator=None,
            measure=None,
            window=None,
            currency=None,
        )
        | operands
    )


def empty_temporal():
    data = witness("temporal-065-002")["temporal"]
    data["overlap"] = False
    return data


def test_provenance_product_decision_changes_only_metric_and_audit_note():
    old = next(c for c in load_v7_golden_cases() if c.id == "provenance-071-004")
    new = CASES[old.id]
    assert old.expect["metric"]["operation"] == "frequency"
    assert old.expect["metric"]["measure"] == "occurrence_count"
    assert old.expect["metric"]["window"] == "month"
    expected = deepcopy(old.expect)
    expected.update(metric=None, group_by=[])
    assert new.expect == expected
    assert new.forbid == old.forbid
    plan = example_plan(new)
    assert plan.intent == "rank" and plan.entity_type is None
    assert plan.metric is None and plan.clarification == "none"
    assert plan.unsupported_reason == "insufficient_structured_data"
    assert (plan.ordering, plan.limit) == ("desc", 20)


@pytest.mark.parametrize("identifier", ["combined-060-011", "temporal-065-002"])
@pytest.mark.parametrize(
    "operation,operands", [("occurrence_count", {}), ("value", {"field": "start_date"})]
)
def test_record_overlap_removes_only_unused_valid_metric(identifier, operation, operands):
    data = witness(identifier)
    data["metric"] = metric(operation, **operands)
    with pytest.raises(ValidationError, match="unexpected_metric"):
        validate(data, ResearchQueryPlanV9)
    actual = validate(data)
    assert actual.metric is None and actual.temporal.overlap
    assert not compare_v9_expectations(actual, CASES[identifier])


def test_search_record_scalar_is_unused_without_quantitative_consumers():
    data = witness("temporal-065-002")
    data.update(intent="search", semantic={"query": "music", "focus": None})
    data["metric"] = metric("value", field="start_date")
    assert validate(data).metric is None


@pytest.mark.parametrize("conflict", ["group_by", "metric_filter", "ordering"])
def test_quantitative_consumers_are_not_discarded(conflict):
    data = witness("temporal-065-002")
    data["metric"] = metric("occurrence_count")
    data[conflict] = {
        "group_by": ["event"],
        "metric_filter": {"operator": "gt", "value": 2, "upper": None},
        "ordering": "desc",
    }[conflict]
    with pytest.raises(ValidationError):
        validate(data)


def test_undefined_diversity_preserves_block_without_inventing_dimension():
    data = witness("comparisons-045-004")
    data["clarification"] = "needs_definition"
    data["metric"] = metric("diversity")
    actual = validate(data)
    assert actual.metric is None and actual.intent == "compare"
    assert actual.clarification == "needs_definition"
    assert actual.unsupported_reason == "insufficient_structured_data"
    data["metric"] = metric("distinct_count")
    with pytest.raises(ValidationError, match="distinct_dimension_required"):
        validate(data)
    data["metric"] = metric("diversity", distinct_by="genre")
    assert validate(data).metric.distinct_by == "genre"


@pytest.mark.parametrize("identifier", ["quality-069-007", "quality-069-008", "quality-069-009"])
def test_publication_lead_time_has_no_fabricated_metric(identifier):
    data = witness(identifier)
    assert validate(data).metric is None
    assert data["intent"] == "anomaly" and data["anomaly"]["measure"] is None
    assert data["unsupported_reason"] == "insufficient_structured_data"
    for invalid in (
        metric("duration", field="created_at"),
        metric("regularity", field="created_at", measure="event_count", window="week"),
    ):
        data["metric"] = invalid
        with pytest.raises(ValidationError, match="metric_field_required_or_unexpected"):
            validate(data)


@pytest.mark.parametrize("identifier", ["graph-064-004", "organizations-063-003"])
def test_rank_subject_is_not_counted_counterpart(identifier):
    data = witness(identifier)
    actual = validate(data)
    assert actual.intent == "rank" and actual.entity_type == "venue"
    assert actual.group_by == ["venue"]
    assert actual.metric.operation == "distinct_count"
    assert actual.metric.distinct_by == "organization"
    data["group_by"] = ["organization"]
    with pytest.raises(ValidationError, match="rank_entity_group_mismatch"):
        validate(data)


def test_chronological_extremum_is_not_event_cardinality():
    data = witness("temporal-041-001")
    actual = validate(data)
    assert (actual.metric.operation, actual.metric.field) == ("value", "start_date")
    assert (actual.group_by, actual.ordering, actual.limit) == (["event"], "asc", 1)
    data["metric"] = metric("event_count")
    with pytest.raises(ValidationError, match="event_count_per_event_is_meaningless"):
        validate(data)


def test_empty_time_only_neutralized_under_explicit_date_block():
    data = witness("anomalies-057-010")
    data["temporal"] = empty_temporal()
    actual = validate(data)
    assert actual.temporal is None and actual.clarification == "needs_date"
    with pytest.raises(ValidationError, match="unused_temporal_must_be_null"):
        validate(data, ResearchQueryPlanV9)
    data["clarification"] = "none"
    with pytest.raises(ValidationError, match="unused_temporal_must_be_null"):
        validate(data)


@pytest.mark.parametrize(
    "update",
    [
        {"overlap": True},
        {"time_of_day": "morning"},
        {"period": "today"},
        {"weekday": "monday"},
        {"before_time": "18:00:00"},
    ],
)
def test_real_temporal_constraints_survive_date_block(update):
    data = witness("anomalies-057-010")
    data["temporal"] = empty_temporal() | update
    assert validate(data).model_dump(mode="json")["temporal"] == data["temporal"]


@pytest.mark.parametrize(
    "update",
    [
        {"lookback": 2},
        {"from_date": "2026-10-02"},
        {"period": "explicit_range"},
        {"field": "modified_at"},
        {"unknown": None},
    ],
)
def test_partial_or_nonempty_temporal_not_repaired(update):
    data = witness("anomalies-057-010")
    data["temporal"] = empty_temporal() | update
    with pytest.raises(ValidationError):
        validate(data)


def test_shared_space_path_uses_only_legal_edges():
    data = witness("graph-064-002")
    actual = validate(data)
    assert actual.relation.operation == "shared"
    assert actual.relation.source == actual.relation.target == "organization"
    assert actual.relation.via == ["event", "space", "event"]
    data["relation"]["via"] = ["event", "occurrence", "space"]
    with pytest.raises(ValidationError, match="unknown_relation_edge"):
        validate(data)


@pytest.mark.parametrize("operation", ["frequency", "regularity"])
@pytest.mark.parametrize("operands", [{}, {"measure": "event_count"}, {"window": "month"}])
def test_partial_frequency_operands_never_guessed(operation, operands):
    data = witness("provenance-071-004")
    data["metric"] = metric(operation, **operands)
    with pytest.raises(ValidationError, match="measure_and_window_required"):
        validate(data)


@pytest.mark.parametrize("identifier", ["regressions-090-019", "regressions-091-009"])
def test_organization_event_count_regression_witness(identifier):
    data = witness(identifier)
    assert validate(data).metric.operation == "event_count"
    data["metric"] = metric("occurrence_count")
    # This is a semantic mismatch, not an invalid public plan: never guess a repair.
    actual = validate(data)
    assert actual.metric.operation == "occurrence_count"
    assert [d.path for d in compare_v9_expectations(actual, CASES[identifier])] == [
        "metric.operation"
    ]


def test_explicit_occurrences_and_seasonal_dimensions_unchanged():
    for case in CASES.values():
        if (
            case.expect.get("metric", {}).get("operation") == "occurrence_count"
            if isinstance(case.expect.get("metric"), dict)
            else False
        ):
            assert validate(witness(case.id)).metric.operation == "occurrence_count"
    data = witness("trends-061-010")
    assert validate(data).group_by == ["event_type", "month"]
    assert data["clarification"] == "none" and data["unsupported_reason"] is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("metric", {"operation": "SQL"}),
        ("metric", metric("unknown")),
        ("group_by", ["unknown"]),
        ("temporal", []),
        ("relation", {"via": []}),
        ("extra", None),
    ],
)
def test_unknown_and_malformed_still_fail(field, value):
    data = witness("temporal-065-002")
    data[field] = value
    with pytest.raises(ValidationError):
        validate(data)


def test_original_query_identity_and_native_schema_stay_strict():
    data = witness("trends-061-010")
    with pytest.raises(ValidationError, match="original_query_changed"):
        CanonicalModelOutputV9.model_validate_json(
            json.dumps(data), context={"original_query": "other"}
        )
    assert CanonicalModelOutputV9.model_json_schema() == ResearchQueryPlanV9.model_json_schema()
    assert len(RESEARCH_V9_PROMPT) <= 15447  # No growth from reviewed v9 prompt.


async def test_invalid_native_output_does_not_retry_or_fallback(settings):
    calls = []
    data = witness("graph-064-002")
    data["relation"]["via"] = ["event", "occurrence", "space"]

    def respond(request):
        calls.append(json.loads(request.content))
        return httpx.Response(200, json=completion(settings, json.dumps(data)))

    client = StructuredModelClient(settings, httpx.MockTransport(respond))
    try:
        with pytest.raises(PlannerError, match="planner_invalid_response"):
            await client.plan_v9(PlanRequest(query=data["original_query"]), date(2026, 10, 2))
        assert len(calls) == 1 and not calls[0].get("tools")
        assert client.sdk.max_retries == 0
        assert not client.client.trust_env and not client.client.follow_redirects
    finally:
        await client.close()
