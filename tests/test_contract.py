import json

import pytest
from pydantic import ValidationError

from research_planner.schemas import PlanRequest, ResearchQueryPlan
from tests.conftest import FIXTURES, make_plan


@pytest.mark.parametrize("case", FIXTURES, ids=lambda case: case["id"])
def test_reviewed_query_plan_fixtures(case):
    plan = make_plan(case["query"], **case["plan"])
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
