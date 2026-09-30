import json

import pytest
from pydantic import ValidationError

from research_planner.schemas import PlanRequest, ResearchQueryPlan
from tests.conftest import FIXTURES, fixture_plan, make_plan


@pytest.mark.parametrize("case", FIXTURES, ids=lambda case: case["id"])
def test_reviewed_query_plan_fixtures(case):
    plan = fixture_plan(case)
    assert plan.original_query == case["query"]
    assert ResearchQueryPlan.model_validate_json(plan.model_dump_json()) == plan


@pytest.mark.parametrize(
    "changes",
    [
        {"intent": "sql"},
        {"sql": "SELECT * FROM users"},
        {"area_id": "invented"},
        {"confidence": 0.99},
        {"group_by": "users.email"},
        {"entity_type": "user"},
        {"venue_query": "x" * 161},
        {"semantic_query": "x" * 501},
        {"genre_queries": ["Jazz"] * 9},
        {"category_queries": ["Kunst"] * 9},
        {"requires_semantic_relevance": "false"},
        {"requires_semantic_relevance": 1},
        {"semantic_query": "interessant"},
        {"requires_semantic_relevance": True},
        {"semantic_focus": "interessant"},
        {"intent": "count", "answer_mode": "count"},
        {"intent": "recommend", "answer_mode": "recommendation"},
        {"intent": "count", "answer_mode": "count", "metric": "venue_count"},
        {"intent": "aggregate", "answer_mode": "aggregate", "metric": "event_count"},
        {"intent": "compare", "answer_mode": "comparison"},
        {"metric": "event_count"},
        {"group_by": "venue"},
        {"answer_mode": "count"},
        {"time_of_day": "evening"},
        {"temporal": "explicit_range"},
        {"explicit_from_date": "2026-09-29"},
        {
            "temporal": "explicit_range",
            "explicit_from_date": "2026-10-02",
            "explicit_to_date": "2026-10-01",
        },
        {"venue_query": " "},
        {"comparison_targets": [{"kind": "venue", "query": "Kühlhaus"}]},
        {"clarification": "needs_criteria"},
    ],
)
def test_closed_and_consistent_schema(changes):
    data = make_plan().model_dump(mode="json") | changes
    with pytest.raises(ValidationError):
        ResearchQueryPlan.model_validate_json(json.dumps(data))


@pytest.mark.parametrize(
    "payload",
    [
        {"query": "x" * 2001},
        {"query": " "},
        {"query": ""},
        {"query": 3},
        {"query": "Events", "timezone": "Mars/Guess"},
        {"query": "Events", "timezone": "../etc"},
        {"query": "Events", "language": "xx"},
        {"query": "Events", "model": "other"},
        {"query": "Events", "url": "https://attacker.test"},
        {"query": "Events", "area_id": "not-allowed"},
    ],
)
def test_bounded_request(payload):
    with pytest.raises(ValidationError):
        PlanRequest.model_validate(payload)


def test_compare_bounds_and_duplicates():
    target = {"kind": "venue", "query": "Kühlhaus"}
    for targets in [[target] * 5, [target, target]]:
        with pytest.raises(ValidationError):
            make_plan(
                intent="compare",
                answer_mode="comparison",
                metric="event_count",
                comparison_targets=targets,
            )


def test_all_model_fields_required_and_objects_closed():
    schema = ResearchQueryPlan.model_json_schema()
    assert set(schema["required"]) == set(schema["properties"])
    assert schema["additionalProperties"] is False
    assert schema["$defs"]["ComparisonTarget"]["additionalProperties"] is False


@pytest.mark.parametrize("field", list(ResearchQueryPlan.model_fields))
def test_no_wire_field_may_be_omitted(field):
    data = make_plan().model_dump(mode="json")
    del data[field]
    with pytest.raises(ValidationError):
        ResearchQueryPlan.model_validate_json(json.dumps(data))


@pytest.mark.parametrize(
    "field", ["temporal", "time_of_day", "metric", "group_by", "clarification"]
)
def test_unused_enum_requires_none_string(field):
    data = make_plan().model_dump(mode="json")
    assert data[field] == "none"
    data[field] = None
    with pytest.raises(ValidationError):
        ResearchQueryPlan.model_validate_json(json.dumps(data))


@pytest.mark.parametrize(
    "field", ["accessibility", "free_admission", "interesting", "unsupported_constraint"]
)
def test_invented_model_fields_are_forbidden(field):
    data = make_plan().model_dump(mode="json") | {field: None}
    with pytest.raises(ValidationError, match="extra_forbidden"):
        ResearchQueryPlan.model_validate_json(json.dumps(data))


def test_schema_uses_grammar_friendly_string_bounds():
    schema = ResearchQueryPlan.model_json_schema()
    assert ResearchQueryPlan.model_config["strict"] is True
    assert ResearchQueryPlan.model_config["extra"] == "forbid"
    assert '"pattern"' not in json.dumps(schema)
    assert '"default"' not in json.dumps(schema)
    assert schema["properties"]["original_query"]["minLength"] == 1
    assert schema["properties"]["original_query"]["maxLength"] == 2000
    for field in (
        "area_query",
        "venue_query",
        "organization_query",
        "semantic_query",
        "semantic_focus",
    ):
        text, null = schema["properties"][field]["anyOf"]
        assert null == {"type": "null"}
        assert text["minLength"] == 1
        assert text["maxLength"] == (500 if field.startswith("semantic_") else 160)
    for field in ("category_queries", "genre_queries"):
        assert schema["properties"][field]["maxItems"] == 8
        assert schema["properties"][field]["items"]["maxLength"] == 160
    assert schema["properties"]["comparison_targets"]["maxItems"] == 4
    target = schema["$defs"]["ComparisonTarget"]
    assert set(target["required"]) == set(target["properties"])
    assert target["properties"]["query"]["minLength"] == 1
    assert target["properties"]["query"]["maxLength"] == 160


@pytest.mark.parametrize("value", ["   ", "\n\t", "\u00a0\u2003"])
def test_query_slot_topic_reject_whitespace_without_schema_regex(value):
    from pydantic import TypeAdapter

    from research_planner.schemas import Query, Slot, Topic

    for annotation in (Query, Slot, Topic):
        with pytest.raises(ValidationError):
            TypeAdapter(annotation).validate_json(json.dumps(value))


@pytest.mark.parametrize("value", ["Glücksburg", "  Glücksburg\n"])
def test_query_slot_topic_validate_without_modifying_text(value):
    from pydantic import TypeAdapter

    from research_planner.schemas import Query, Slot, Topic

    for annotation in (Query, Slot, Topic):
        assert TypeAdapter(annotation).validate_json(json.dumps(value)) == value


@pytest.mark.parametrize(
    "changes",
    [
        {"original_query": "\n\t"},
        {"area_query": "   "},
        {"venue_query": "\n\t"},
        {"organization_query": "   "},
        {"category_queries": ["   "]},
        {"genre_queries": ["\n\t"]},
        {"semantic_query": "   ", "requires_semantic_relevance": True},
        {"semantic_query": "Kunst", "requires_semantic_relevance": True, "semantic_focus": "\n\t"},
        {
            "intent": "compare",
            "answer_mode": "comparison",
            "clarification": "needs_criteria",
            "comparison_targets": [{"kind": "venue", "query": "   "}],
        },
    ],
)
def test_nonblank_validator_applies_to_every_query_slot_topic(changes):
    with pytest.raises(ValidationError, match="blank_string"):
        make_plan(**changes)


@pytest.mark.parametrize(
    "case_id,entity,area,venue,metric",
    [
        ("count_past_kuehlhaus", "event", None, "Kühlhaus", "event_count"),
        ("events_deutsches_haus", "event", None, "Deutsches Haus", "none"),
        ("venues_area", "venue", "Glücksburg", None, "none"),
        ("count_venues", "venue", "Flensburg", None, "venue_count"),
        ("organizations_area", "organization", "Glücksburg", None, "none"),
    ],
)
def test_entity_is_requested_result_not_filter(case_id, entity, area, venue, metric):
    plan = fixture_plan(next(case for case in FIXTURES if case["id"] == case_id))
    assert (plan.entity_type, plan.area_query, plan.venue_query, plan.metric) == (
        entity,
        area,
        venue,
        metric,
    )
    if metric == "event_count":
        with pytest.raises(ValidationError, match="metric_entity_mismatch"):
            ResearchQueryPlan.model_validate_json(
                json.dumps(plan.model_dump(mode="json") | {"entity_type": "venue"})
            )
