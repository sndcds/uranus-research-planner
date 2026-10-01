import json

from research_planner.prompts import SYSTEM_PROMPT
from tests.conftest import FIXTURES, fixture_plan


def test_prompt_contains_complete_validated_live_case():
    assert SYSTEM_PROMPT.startswith("CRITICAL OUTPUT RULES:")
    example = SYSTEM_PROMPT.split("\n{", 1)[1].split("\n}", 1)[0]
    golden = json.loads("{" + example + "\n}")
    case = next(case for case in FIXTURES if case["id"] == "count_past_kuehlhaus")
    assert golden == fixture_plan(case).model_dump(mode="json")
    assert "Use this exact field set for every response." in SYSTEM_PROMPT


def test_prompt_contains_complete_canonical_outside_research_example():
    from research_planner.schemas import ResearchQueryPlan

    section = SYSTEM_PROMPT.split("OUTSIDE_RESEARCH:", 1)[1]
    example = section.split("\n{", 1)[1].split("\n}", 1)[0]
    golden = json.loads("{" + example + "\n}")
    case = next(case for case in FIXTURES if case["id"] == "injection")
    assert golden == fixture_plan(case).model_dump(mode="json")
    assert ResearchQueryPlan.model_validate_json(json.dumps(golden)).original_query == case["query"]


def test_prompt_separates_taxonomies_and_preserves_parentage():
    assert "Never map an event type to category_queries." in SYSTEM_PROMPT
    assert '"Jazz Konzerte", "Jazz-Konzerte", "Jazzkonzerte"' in SYSTEM_PROMPT
    assert "genres are subordinate to event types" in SYSTEM_PROMPT
    assert 'Konzerte -> category_queries=["Konzerte"]' not in SYSTEM_PROMPT
