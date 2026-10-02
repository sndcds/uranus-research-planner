"""Negative algebra, closed schema, typed values, and frozen legacy contracts."""

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from research_planner.app import create_app
from research_planner.research_v7_schema import ResearchQueryPlanV7
from tests.v7_golden import example_plan, load_v7_golden_cases

CASES = {c.id: c for c in load_v7_golden_cases()}


def data(identifier="ranking-039-004"):
    return example_plan(CASES[identifier]).model_dump(mode="json")


def closed_objects(schema):
    if isinstance(schema, dict):
        if schema.get("type") == "object":
            assert schema["additionalProperties"] is False
            assert set(schema["required"]) == set(schema["properties"])
        assert "default" not in schema
        for child in schema.values():
            closed_objects(child)
    elif isinstance(schema, list):
        for child in schema:
            closed_objects(child)


def test_schema_snapshot_and_all_nested_models_are_closed():
    schema = ResearchQueryPlanV7.model_json_schema()
    assert schema == json.loads(Path("tests/fixtures/v7_schema.json").read_text())
    closed_objects(schema)
    assert "answer_mode" not in schema["properties"]
    assert "coordinates" not in schema["$defs"]["SpatialV7"]["properties"]


@pytest.mark.parametrize("field", list(ResearchQueryPlanV7.model_fields))
def test_every_top_level_wire_field_is_required(field):
    value = data()
    del value[field]
    with pytest.raises(ValidationError):
        ResearchQueryPlanV7.model_validate_json(json.dumps(value))


@pytest.mark.parametrize(
    "changes",
    [
        {"intent": "longest_description"},
        {"entity_type": "admin_user"},
        {"entity_type": "venue"},
        {"sql": "SELECT 1"},
        {"answer_mode": "records"},
        {"original_query": " "},
        {"original_query": ""},
        {"original_query": "x" * 2001},
        {"limit": 0},
        {"limit": 21},
        {"limit": True},
        {"limit": "1"},
        {"metric": None},
        {"ordering": None},
        {"group_by": "invented"},
        {"filters": [{"field": "description", "operator": "like", "value": "%"}]},
        {"filters": [{"field": "secret", "operator": "missing"}]},
        {"filters": [{"field": "venue", "operator": "gt", "value": 3}]},
        {"filters": [{"field": "coordinates", "operator": "eq", "value": "54,9"}]},
        {
            "filters": [
                {
                    "field": "price",
                    "predicate": {"operator": "eq", "value": "10", "upper": None},
                    "currency": "EUR",
                }
            ]
        },
        {"filters": [{"field": "description", "operator": "missing", "value": None}]},
        {"filters": [{"field": "description", "operator": "eq", "value": " "}]},
        {
            "filters": [
                {"field": "genre", "operator": "eq", "value": "Jazz"},
                {"field": "genre", "operator": "eq", "value": " jazz "},
            ]
        },
        {
            "filters": [
                {"field": "image", "operator": "missing"},
                {"field": "image", "operator": "present"},
            ]
        },
        {"filters": [{"field": "image", "operator": "missing"}] * 17},
        {
            "spatial": {
                "relation": "none",
                "place_query": None,
                "area_query": None,
                "radius_m": 10,
                "reference": "named",
            }
        },
        {"semantic": {"query": "accessible", "focus": None}},
        {"intent": "relation", "metric": None, "ordering": None, "limit": None, "group_by": "none"},
        {"intent": "trend", "metric": None, "ordering": None, "limit": None, "group_by": "none"},
        {"intent": "anomaly", "metric": None, "ordering": None, "limit": None, "group_by": "none"},
    ],
)
def test_invalid_top_level_combinations(changes):
    with pytest.raises(ValidationError):
        ResearchQueryPlanV7.model_validate_json(json.dumps(data() | changes))


@pytest.mark.parametrize(
    "changes",
    [
        {"operation": "invented"},
        {"field": "password"},
        {"numerator": {}},
        {"operation": "distinct_count", "distinct_by": None},
        {"operation": "field_length", "field": None},
        {"operation": "field_length", "field": "start_date"},
        {"operation": "ratio", "numerator": None, "denominator": None},
        {"operation": "average", "field": "description"},
        {"operation": "average", "field": "min_price", "currency": None},
        {"field": "start_date"},
        {"distinct_by": "genre"},
        {"window": "month"},
    ],
)
def test_invalid_metric_operands(changes):
    value = data()
    value["metric"].update(changes)
    with pytest.raises(ValidationError):
        ResearchQueryPlanV7.model_validate_json(json.dumps(value))


@pytest.mark.parametrize(
    "changes",
    [
        {"radius_m": -1},
        {"radius_m": 0},
        {"radius_m": 500001},
        {"radius_m": True},
        {"radius_m": 1.5},
        {"relation": "inside"},
        {"relation": "nearby"},
        {"area_query": "Schleswig-Holstein"},
        {"radius_m": None},
    ],
)
def test_invalid_radius_and_conflicting_slots(changes):
    value = data("geography-051-011")
    value["spatial"].update(changes)
    with pytest.raises(ValidationError):
        ResearchQueryPlanV7.model_validate_json(json.dumps(value))


def test_nearby_requires_location_and_cannot_carry_place():
    value = data("regressions-074-005")
    for changes in [
        {"clarification": "none"},
        {"spatial": value["spatial"] | {"place_query": "Flensburg"}},
    ]:
        with pytest.raises(ValidationError):
            ResearchQueryPlanV7.model_validate_json(json.dumps(value | changes))


@pytest.mark.parametrize(
    "changes",
    [
        {"period": "explicit_range"},
        {"from_date": "2026-10-02"},
        {"period": "explicit_range", "from_date": "2026-10-02", "to_date": "2026-10-01"},
        {"before_time": "18:00:00", "after_time": "20:00:00"},
        {"before_time": "12:00:00", "time_of_day": "evening"},
        {"before_time": "20:00:00", "after_time": "08:00:00", "time_of_day": "night"},
        {"after_time": "20:00:00+02:00"},
        {"weekday": "funday"},
        {"field": "created_at", "time_of_day": "morning"},
        {"lookback": 6},
        {"calendar_area_query": "Hamburg"},
    ],
)
def test_temporal_consistency(changes):
    value = data("temporal-050-001")
    value["temporal"].update(changes)
    with pytest.raises(ValidationError):
        ResearchQueryPlanV7.model_validate_json(json.dumps(value))


@pytest.mark.parametrize(
    "changes",
    [
        {"mode": "between"},
        {"mode": "between", "minimum": 11},
        {"minimum": 1},
        {"maximum": -1},
        {"maximum": float("nan")},
        {"maximum": float("inf")},
        {"maximum": True},
        {"currency": "XYZ"},
        {"currency": None},
        {"mode": "free"},
    ],
)
def test_price_consistency(changes):
    value = data("prices-056-002")
    value["price"].update(changes)
    with pytest.raises(ValidationError):
        ResearchQueryPlanV7.model_validate_json(json.dumps(value))


@pytest.mark.parametrize("intent", ["count", "aggregate"])
def test_semantic_exact_population_rejected_but_explicit_boundary_preserved(intent):
    value = data("accessibility-020-002")
    value.update(
        intent=intent,
        group_by="venue" if intent == "aggregate" else "none",
        unsupported_reason=None,
    )
    with pytest.raises(ValidationError, match="semantic_exact_population_forbidden"):
        ResearchQueryPlanV7.model_validate_json(json.dumps(value))
    value["unsupported_reason"] = "insufficient_structured_data"
    assert ResearchQueryPlanV7.model_validate_json(json.dumps(value)).intent == intent


def test_event_and_occurrence_cannot_be_interchanged_in_counts():
    for identifier, wrong in [
        ("regressions-004-001", "occurrence"),
        ("regressions-004-002", "event"),
    ]:
        with pytest.raises(ValidationError, match="count_entity_mismatch"):
            ResearchQueryPlanV7.model_validate_json(
                json.dumps(data(identifier) | {"entity_type": wrong})
            )


@pytest.mark.parametrize(
    "targets",
    [
        [],
        [{"kind": "venue", "query": "X"}],
        [{"kind": "venue", "query": "X"}, {"kind": "venue", "query": " x "}],
        [{"kind": "venue", "query": str(i)} for i in range(5)],
    ],
)
def test_comparison_bounds(targets):
    with pytest.raises(ValidationError):
        ResearchQueryPlanV7.model_validate_json(
            json.dumps(data("comparisons-045-001") | {"comparison_targets": targets})
        )


def test_closed_relation_edges_and_bounds():
    value = data("relations-040-001")
    for changes in [
        {"via": []},
        {"via": ["event"] * 4},
        {"target": "admin_user"},
        {"operation": "sql"},
    ]:
        with pytest.raises(ValidationError):
            ResearchQueryPlanV7.model_validate_json(
                json.dumps(value | {"relation": value["relation"] | changes})
            )


@pytest.mark.parametrize(
    "field,value",
    [
        ("filters", [{"field": "description", "operator": "eq", "value": "SELECT 1"}]),
        ("entity_type", "event"),
        ("price", {"mode": "free", "minimum": None, "maximum": None, "currency": None}),
        (
            "spatial",
            {
                "relation": "nearby",
                "reference": "user_location",
                "place_query": None,
                "area_query": None,
                "radius_m": None,
            },
        ),
    ],
)
@pytest.mark.parametrize("identifier", ["knowledge-047-001", "explain-073-001"])
def test_knowledge_explain_cannot_smuggle_data_query(identifier, field, value):
    with pytest.raises(ValidationError):
        ResearchQueryPlanV7.model_validate_json(json.dumps(data(identifier) | {field: value}))


def test_query_equality_uses_trusted_context_not_model_fields():
    value = data()
    with pytest.raises(ValidationError, match="original_query_changed"):
        ResearchQueryPlanV7.model_validate_json(
            json.dumps(value), context={"original_query": "changed"}
        )


def test_legacy_files_and_openapi_are_frozen(settings):
    expected = json.loads(Path("tests/fixtures/v7_legacy_contracts.json").read_text())
    for path, digest in expected["files"].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, path
    current = create_app(settings).openapi()
    for section, items in [
        ("paths", current["paths"]),
        ("components", current["components"]["schemas"]),
    ]:
        for name, digest in expected[section].items():
            assert (
                hashlib.sha256(json.dumps(items[name], sort_keys=True).encode()).hexdigest()
                == digest
            ), name


@pytest.mark.parametrize(
    "operation,operands",
    [
        *[
            (op, {})
            for op in (
                "event_count",
                "occurrence_count",
                "venue_count",
                "space_count",
                "organization_count",
                "duration",
                "distance",
            )
        ],
        ("distinct_count", {"distinct_by": "organization"}),
        ("diversity", {"distinct_by": "genre"}),
        ("minimum", {"field": "start_date"}),
        ("maximum", {"field": "modified_at"}),
        ("average", {"field": "min_price", "currency": "EUR"}),
        ("median", {"field": "population"}),
        ("field_length", {"field": "description"}),
        ("value", {"field": "longitude"}),
        *[
            (op, {"measure": "occurrence_count", "window": "month"})
            for op in (
                "frequency",
                "regularity",
                "absolute_change",
                "percentage_change",
            )
        ],
        (
            "ratio",
            {
                "numerator": {"operation": "event_count", "distinct_by": None, "subset": "all"},
                "denominator": {"operation": "population", "distinct_by": None, "subset": "all"},
            },
        ),
        (
            "percentage",
            {
                "numerator": {"operation": "event_count", "distinct_by": None, "subset": "free"},
                "denominator": {"operation": "event_count", "distinct_by": None, "subset": "all"},
            },
        ),
    ],
)
def test_metric_algebra_has_a_closed_witness_for_every_operation(operation, operands):
    from research_planner.research_v7_types import MetricV7

    metric = data()["metric"] | {"operation": operation} | operands
    assert MetricV7.model_validate(metric).operation == operation


@pytest.mark.parametrize("identifier", ["security-078-001", "security-078-002"])
@pytest.mark.parametrize("mutation", ["entity", "filter", "semantic", "clarification"])
def test_outside_research_requires_neutral_non_executable_plan(identifier, mutation):
    value = data(identifier)
    value.update(
        {
            "entity": {"entity_type": "event"},
            "filter": {"filters": [{"field": "image", "operator": "missing"}]},
            "semantic": {"semantic": {"query": "anything", "focus": None}},
            "clarification": {"clarification": "needs_definition"},
        }[mutation]
    )
    with pytest.raises(ValidationError):
        ResearchQueryPlanV7.model_validate_json(json.dumps(value))


@pytest.mark.parametrize("field", ["temporal", "price", "spatial", "semantic", "relation", "trend"])
def test_unused_nested_objects_are_null_not_empty_objects(field):
    with pytest.raises(ValidationError):
        ResearchQueryPlanV7.model_validate_json(json.dumps(data() | {field: {}}))


def test_event_grouping_is_never_an_event_type_substitution():
    expected = {
        "ranking-039-004": "event",
        "regressions-090-003": "event_type",
        "regressions-090-004": "genre",
        "regressions-090-005": "venue",
        "regressions-090-006": "organization",
    }
    for identifier, grouping in expected.items():
        plan = example_plan(CASES[identifier])
        assert plan.intent == "rank"
        assert plan.metric.operation == "occurrence_count"
        assert plan.group_by == grouping and plan.ordering == "desc" and plan.limit == 1
    value = data()
    value["metric"]["operation"] = "event_count"
    with pytest.raises(ValidationError, match="event_count_per_event_is_meaningless"):
        ResearchQueryPlanV7.model_validate_json(json.dumps(value))


def test_unknown_spatial_none_cannot_smuggle_a_radius():
    value = data("geography-051-011")
    value["spatial"]["relation"] = "none"
    with pytest.raises(ValidationError):
        ResearchQueryPlanV7.model_validate_json(json.dumps(value))


def test_meaningless_temporal_object_is_rejected():
    value = data("temporal-050-001")
    value["temporal"]["period"] = "none"
    with pytest.raises(ValidationError, match="unused_temporal_must_be_null"):
        ResearchQueryPlanV7.model_validate_json(json.dumps(value))
