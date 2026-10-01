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
        {"event_type_queries": ["Konzerte"] * 9},
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
    for field in ("event_type_queries", "category_queries", "genre_queries"):
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
        {"event_type_queries": ["   "]},
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


@pytest.mark.parametrize("entity", ["event", "venue", "organization"])
def test_search_requires_semantic_residual(entity):
    with pytest.raises(ValidationError, match="search_requires_semantic_query"):
        make_plan(intent="search", entity_type=entity, semantic_query=None)


@pytest.mark.parametrize(
    "intent,semantic_query", [("list", None), ("search", "Kunst"), ("list", "Kunst")]
)
def test_list_and_semantic_search_remain_valid(intent, semantic_query):
    plan = make_plan(
        intent=intent,
        semantic_query=semantic_query,
        requires_semantic_relevance=semantic_query is not None,
    )
    assert plan.intent == intent
    assert plan.semantic_query == semantic_query


@pytest.mark.parametrize(
    "case_id,query,intent,entity,area,metric,temporal",
    [
        (
            "count_venues",
            "Wie viele Veranstaltungsorte gibt es in Flensburg?",
            "count",
            "venue",
            "Flensburg",
            "venue_count",
            "none",
        ),
        (
            "count_past_venues",
            "Wie viele Veranstaltungsorte gab es in Flensburg?",
            "count",
            "venue",
            "Flensburg",
            "venue_count",
            "past",
        ),
        (
            "organizations_area",
            "Welche Organisationen gibt es in Glücksburg?",
            "list",
            "organization",
            "Glücksburg",
            "none",
            "none",
        ),
        (
            "organizations_past",
            "Welche Organisationen gab es in Glücksburg?",
            "list",
            "organization",
            "Glücksburg",
            "none",
            "past",
        ),
    ],
)
def test_present_and_past_golden_plans(case_id, query, intent, entity, area, metric, temporal):
    plan = fixture_plan(next(case for case in FIXTURES if case["id"] == case_id))
    assert plan.original_query == query
    assert (plan.intent, plan.entity_type, plan.area_query, plan.metric, plan.temporal) == (
        intent,
        entity,
        area,
        metric,
        temporal,
    )
    assert plan.semantic_query is None
    assert plan.requires_semantic_relevance is False


@pytest.mark.parametrize(
    "field,value",
    [
        ("intent", "search"),
        ("entity_type", "organization"),
        ("semantic_query", "admin emails"),
        ("area_query", "Glücksburg"),
        ("venue_query", "Kühlhaus"),
        ("organization_query", "Stadt Glücksburg"),
        ("event_type_queries", ["Konzerte"]),
        ("category_queries", ["Musik"]),
        ("genre_queries", ["Jazz"]),
        ("temporal", "tomorrow"),
        ("explicit_from_date", "2026-09-30"),
        ("explicit_to_date", "2026-09-30"),
        ("time_of_day", "evening"),
        ("metric", "event_count"),
        ("group_by", "venue"),
        ("comparison_targets", [{"kind": "venue", "query": "Kühlhaus"}]),
        ("semantic_focus", "admin emails"),
        ("requires_semantic_relevance", True),
        ("answer_mode", "comparison"),
        ("clarification", "needs_location"),
    ],
)
def test_outside_research_rejects_every_noncanonical_field(field, value):
    case = next(case for case in FIXTURES if case["id"] == "private")
    data = fixture_plan(case).model_dump(mode="json") | {field: value}
    with pytest.raises(ValidationError, match="outside_research_requires_neutral_plan"):
        ResearchQueryPlan.model_validate_json(json.dumps(data))
    assert data[field] == value  # validation does not repair the supplied plan


@pytest.mark.parametrize("reason", [None, "multi_area", "unsupported_constraint"])
def test_neutral_plan_rule_does_not_apply_to_other_unsupported_reasons(reason):
    plan = make_plan(
        intent="search",
        entity_type="organization",
        semantic_query="Kunst",
        requires_semantic_relevance=True,
        unsupported_reason=reason,
    )
    assert plan.entity_type == "organization"
    assert plan.semantic_query == "Kunst"
    assert plan.area_query == "Glücksburg"


def test_documented_structured_event_type_and_genre_filters_remain_valid():
    plan = make_plan(
        "Jazz Konzerte in Glücksburg",
        event_type_queries=["Konzerte"],
        genre_queries=["Jazz"],
    )
    assert plan.event_type_queries == ["Konzerte"]
    assert plan.category_queries == []
    assert plan.genre_queries == ["Jazz"]
    assert plan.semantic_query is None


@pytest.mark.parametrize("ordering", [None, "asc", "desc"])
@pytest.mark.parametrize("limit", [None, 1, 2, 20])
def test_independent_ordering_limit_contract(ordering, limit):
    plan = make_plan(ordering=ordering, limit=limit)
    assert plan.ordering == ordering and plan.limit == limit
    assert plan.temporal == "none"


@pytest.mark.parametrize(
    "changes",
    [
        *({"ordering": v} for v in ("none", "earliest", "latest", "best", True)),
        *({"limit": v} for v in (0, 21, True, "1", 1.0, 1.5)),
        {"ordering": "asc", "entity_type": "venue"},
        {"ordering": "desc", "entity_type": "organization"},
        {
            "ordering": "asc",
            "intent": "recommend",
            "answer_mode": "recommendation",
            "semantic_query": "interesting",
            "requires_semantic_relevance": True,
        },
        {
            "ordering": "asc",
            "intent": "search",
            "semantic_query": "interesting",
            "requires_semantic_relevance": True,
        },
    ],
)
def test_invalid_ordering_limit_contract(changes):
    with pytest.raises(ValidationError):
        make_plan(**changes)


@pytest.mark.parametrize(
    "intent,mode,extras",
    [
        ("count", "count", {"metric": "event_count"}),
        ("aggregate", "aggregate", {"metric": "event_count", "group_by": "venue"}),
        ("compare", "comparison", {"clarification": "needs_criteria"}),
    ],
)
@pytest.mark.parametrize("changes", [{"ordering": "asc"}, {"ordering": "desc"}, {"limit": 2}])
def test_metrics_reject_ordering_and_limit(intent, mode, extras, changes):
    with pytest.raises(ValidationError):
        make_plan(intent=intent, answer_mode=mode, **extras, **changes)


@pytest.mark.parametrize("entity", ["venue", "organization"])
def test_non_event_record_limit(entity):
    plan = make_plan(entity_type=entity, limit=2)
    assert plan.limit == 2 and plan.ordering is None


@pytest.mark.parametrize("intent,mode", [("search", "records"), ("recommend", "recommendation")])
def test_semantic_limit_without_ordering(intent, mode):
    plan = make_plan(
        intent=intent,
        answer_mode=mode,
        semantic_query="interesting",
        requires_semantic_relevance=True,
        limit=2,
    )
    assert plan.limit == 2 and plan.ordering is None


def test_hybrid_chronology_is_explicitly_unsupported():
    plan = make_plan(
        ordering="asc",
        intent="search",
        semantic_query="interesting",
        requires_semantic_relevance=True,
        unsupported_reason="unsupported_constraint",
    )
    assert plan.unsupported_reason == "unsupported_constraint"


@pytest.mark.parametrize("field", ["ordering", "limit"])
def test_ordering_limit_fields_required(field):
    data = make_plan().model_dump(mode="json")
    del data[field]
    with pytest.raises(ValidationError):
        ResearchQueryPlan.model_validate_json(json.dumps(data))
