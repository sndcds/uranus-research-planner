"""Coverage and semantic assertions are test data, never production routing."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from research_planner.research_v7_schema import ResearchQueryPlanV7
from tests.v7_golden import (
    GoldenCase,
    assert_v7_expectations,
    example_plan,
    load_v7_golden_cases,
    neutral_plan,
)

CASES = load_v7_golden_cases()


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_every_question_has_valid_witness_and_expectations(case):
    plan = example_plan(case)
    assert_v7_expectations(plan, case)
    assert plan.model_dump(mode="json") == json.loads(plan.model_dump_json())
    if case.capability_status in {"supported", "planned"}:
        assert plan.unsupported_reason is None and plan.clarification == "none"
    if case.capability_status == "unsupported":
        assert plan.unsupported_reason in {"unsupported_constraint", "outside_research"}
    if case.capability_status == "needs_clarification":
        assert plan.clarification in {"needs_date", "needs_location", "needs_criteria"}
        assert plan.unsupported_reason is None
    if case.capability_status == "needs_structured_data":
        assert plan.unsupported_reason == "insufficient_structured_data"
        assert case.required_data
    if case.capability_status == "needs_definition":
        assert plan.clarification in {"needs_definition", "needs_criteria"}
    if case.capability_status == "needs_context":
        assert plan.clarification == "needs_context"
    if case.capability_status == "semantic_only":
        assert plan.intent == "search" and plan.semantic is not None
    if case.capability_status == "knowledge":
        assert plan.intent == "knowledge" and plan.entity_type is None


def test_manifest_covers_every_supplied_catalog_section_and_preserves_variations():
    manifest = json.loads(Path("tests/fixtures/v7_catalog.json").read_text())
    assert len(CASES) == 447  # Reviewed question occurrences; do not silently shrink the corpus.
    sections = {c["section"] for c in manifest["cases"]}
    assert set(range(39, 75)) <= sections
    assert {
        4,
        8,
        10,
        11,
        13,
        14,
        15,
        16,
        17,
        18,
        19,
        20,
        22,
        23,
        24,
        25,
        26,
        78,
        90,
        91,
        92,
    } <= sections
    questions = [c.question for c in CASES]
    assert questions.count("Welche Veranstaltungen sind kostenlos?") >= 4
    assert all(
        q in questions
        for q in (
            "Welche Veranstalter haben die meisten Veranstaltungen?",
            "Welche Organisation hat die meisten Veranstaltungen?",
            "Wer veranstaltet die meisten Veranstaltungen?",
            "Welches Event hat die meisten Termine?",
        )
    )
    for file in ("analytics.json", "geography.json"):
        assert all(
            c["query"] in questions for c in json.loads(Path("tests/fixtures", file).read_text())
        )


@pytest.mark.parametrize("mutation", ["id", "category", "capability_status", "expect", "forbid"])
def test_fixture_metadata_is_required(mutation):
    data = CASES[0].model_dump()
    del data[mutation]
    with pytest.raises(ValidationError):
        GoldenCase.model_validate(data)


@pytest.mark.parametrize("field", ["category", "capability_status"])
def test_unknown_fixture_classifications_rejected(field):
    with pytest.raises(ValidationError):
        GoldenCase.model_validate(CASES[0].model_dump() | {field: "invented"})


@pytest.mark.parametrize("mutation", ["duplicate", "missing", "unreferenced", "changed_question"])
def test_loader_detects_catalog_damage(tmp_path, mutation):
    import shutil

    shutil.copytree("tests/fixtures/v7", tmp_path / "v7")
    shutil.copy("tests/fixtures/v7_catalog.json", tmp_path)
    file = tmp_path / "v7/ranking.json"
    values = json.loads(file.read_text())
    if mutation == "duplicate":
        values.append(deepcopy(values[0]))
    elif mutation == "missing":
        values.pop()
    elif mutation == "unreferenced":
        (tmp_path / "v7/untracked.json").write_text("[]")
    else:
        values[0]["question"] = "changed"
    file.write_text(json.dumps(values))
    with pytest.raises(AssertionError):
        load_v7_golden_cases(tmp_path)


@pytest.mark.parametrize(
    "case", [c for c in CASES if c.expect["intent"] not in {"list", "search"}], ids=lambda c: c.id
)
def test_analytical_and_context_questions_never_accept_generic_list_as_golden(case):
    generic = ResearchQueryPlanV7.model_validate(neutral_plan(case.question))
    with pytest.raises(AssertionError):
        assert_v7_expectations(generic, case)


def test_report_is_derived_and_contains_each_capability_question():
    from scripts.report_v7_corpus import report

    result = report()
    assert result["total_questions"] == 447
    assert sum(result["by_capability_status"].values()) == 447
    assert sum(result["by_intent"].values()) == 447
    assert result == json.loads(Path("docs/v7-corpus-report.json").read_text())
