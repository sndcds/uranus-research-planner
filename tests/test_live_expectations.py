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


@pytest.mark.parametrize(
    "case_id", ["count_venues", "count_past_venues", "organizations_area", "organizations_past"]
)
def test_live_comparison_rejects_present_past_confusion(case_id):
    expected = fixture_plan(next(case for case in FIXTURES if case["id"] == case_id))
    wrong_period = "past" if expected.temporal == "none" else "none"
    actual = expected.model_copy(update={"temporal": wrong_period})
    with pytest.raises(AssertionError):
        assert_golden_plan(actual, expected)
    assert actual.temporal == wrong_period


def test_tomorrow_golden_rejects_category_splitting_without_runtime_heuristics():
    from research_planner.schemas import ResearchQueryPlan

    expected = fixture_plan(next(case for case in FIXTURES if case["id"] == "tomorrow"))
    assert expected.original_query == "welche Workshops für Kinder gibt es morgen?"
    assert expected.intent == "search"
    assert expected.entity_type == "event"
    assert expected.semantic_query == "Workshops für Kinder"
    assert expected.category_queries == expected.genre_queries == []
    assert expected.temporal == "tomorrow"
    data = expected.model_dump(mode="json") | {
        "semantic_query": "für Kinder",
        "category_queries": ["Workshops"],
    }
    # This combination could be legitimate for a different taxonomy/query.
    actual = ResearchQueryPlan.model_validate(data)
    with pytest.raises(AssertionError):
        assert_golden_plan(actual, expected)
    assert actual.model_dump(mode="json") == data


@pytest.mark.parametrize("case_id", ["injection", "private"])
def test_outside_research_golden_is_complete_and_neutral(case_id):
    expected = fixture_plan(next(case for case in FIXTURES if case["id"] == case_id))
    neutral = make_plan(
        expected.original_query, area_query=None, unsupported_reason="outside_research"
    )
    assert_golden_plan(expected, neutral)
    actual = expected.model_copy(
        update={
            "intent": "search",
            "entity_type": "organization",
            "semantic_query": "admin emails",
            "requires_semantic_relevance": True,
        }
    )
    with pytest.raises(AssertionError):
        assert_golden_plan(actual, expected)
