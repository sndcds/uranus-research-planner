"""Offline regressions for the comparator used by the opt-in model evaluation."""

import pytest

from tests.conftest import FIXTURES, assert_golden_plan, fixture_plan, make_plan


def test_all_fixtures_are_complete_without_implicit_defaults():
    assert len({case["id"] for case in FIXTURES}) == len(FIXTURES)
    for case in FIXTURES:
        assert fixture_plan(case).model_dump(mode="json") == case["plan"]


def test_semantic_query_casing_is_the_only_text_flexibility():
    expected = make_plan(semantic_query="Kunst", requires_semantic_relevance=True)
    actual = make_plan(semantic_query="kunst", requires_semantic_relevance=True)
    assert_golden_plan(actual, expected)
    assert actual.semantic_query == "kunst"  # comparing never mutates either plan


@pytest.mark.parametrize(
    "changes",
    [
        {"semantic_query": "Musik"},
        {"semantic_query": "keine Kunst"},
        {"semantic_query": " Kunst "},
        {"semantic_focus": "Kunst"},
        {"entity_type": "venue"},
        {"original_query": "Suche events in Glücksburg"},
        {"area_query": "glücksburg"},
        {"venue_query": "Kühlhaus"},
        {"organization_query": "Stadt Glücksburg"},
        {"category_queries": ["Konzerte"]},
        {"genre_queries": ["Jazz"]},
        {"temporal": "today", "time_of_day": "evening"},
        {"clarification": "needs_location"},
        {"unsupported_reason": "unsupported_constraint"},
        {"intent": "recommend", "answer_mode": "recommendation"},
        {
            "intent": "aggregate",
            "answer_mode": "aggregate",
            "metric": "event_count",
            "group_by": "venue",
        },
    ],
)
def test_full_comparison_rejects_unexpected_but_valid_plan_changes(changes):
    expected = make_plan(semantic_query="Kunst", requires_semantic_relevance=True)
    actual = make_plan(
        **({"semantic_query": "Kunst", "requires_semantic_relevance": True} | changes)
    )
    with pytest.raises(AssertionError):
        assert_golden_plan(actual, expected)
