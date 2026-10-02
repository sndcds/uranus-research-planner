"""Test/developer-only corpus loading and dotted expectations; no production routing."""

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from research_planner.research_v7_schema import ResearchQueryPlanV7

ROOT = Path(__file__).parent / "fixtures"
Category = Literal[
    "ranking",
    "relations",
    "temporal",
    "geography",
    "content",
    "quality",
    "comparisons",
    "graph",
    "knowledge",
    "taxonomy",
    "organizations",
    "venues",
    "audiences",
    "prices",
    "anomalies",
    "journalism",
    "combined",
    "trends",
    "gaps",
    "media",
    "provenance",
    "explain",
    "regressions",
    "accessibility",
    "security",
]
Capability = Literal[
    "supported",
    "planned",
    "needs_clarification",
    "unsupported",
    "needs_definition",
    "needs_structured_data",
    "semantic_only",
    "needs_context",
    "knowledge",
]


class GoldenCase(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    id: str = Field(min_length=1)
    question: str = Field(min_length=1, max_length=2000)
    category: Category
    capability_status: Capability
    expect: dict[str, Any] = Field(min_length=1)
    forbid: dict[str, list[Any]]
    example: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None
    required_data: list[str] = Field(default_factory=list)


def neutral_plan(question: str) -> dict[str, Any]:
    """A mock-output witness, not a planner. No question interpretation here."""
    return dict(
        original_query=question,
        intent="list",
        entity_type="event",
        metric=None,
        group_by="none",
        ordering=None,
        limit=None,
        filters=[],
        metric_filter=None,
        taxonomy=None,
        temporal=None,
        spatial=None,
        price=None,
        semantic=None,
        relation=None,
        trend=None,
        anomaly=None,
        explain=None,
        knowledge=None,
        comparison_targets=[],
        clarification="none",
        unsupported_reason=None,
    )


def value_at(data: dict[str, Any], path: str) -> Any:
    value: Any = data
    for part in path.split("."):
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def set_at(data: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    target = data
    for part in parts[:-1]:
        target = target[part]
    target[parts[-1]] = deepcopy(value)


def example_plan(case: GoldenCase) -> ResearchQueryPlanV7:
    data = neutral_plan(case.question)
    for path, value in (case.example | case.expect).items():
        set_at(data, path, value)
    return ResearchQueryPlanV7.model_validate_json(
        json.dumps(data), context={"original_query": case.question}
    )


def assert_v7_expectations(actual: ResearchQueryPlanV7, case: GoldenCase) -> None:
    data = actual.model_dump(mode="json")
    assert data["original_query"] == case.question, case.id
    for path, expected in case.expect.items():
        assert value_at(data, path) == expected, f"{case.id}: {path} differs"
    for path, forbidden in case.forbid.items():
        assert value_at(data, path) not in forbidden, f"{case.id}: {path} forbidden"


def load_v7_golden_cases(root: Path = ROOT) -> list[GoldenCase]:
    manifest = json.loads((root / "v7_catalog.json").read_text())
    files = manifest["files"]
    assert len(files) == len(set(files)), "duplicate manifest file"
    assert set(files) == {p.stem for p in (root / "v7").glob("*.json")}, "unreferenced corpus file"
    cases = []
    for category in files:
        raw = json.loads((root / "v7" / f"{category}.json").read_text())
        assert raw, f"empty corpus category: {category}"
        parsed = [GoldenCase.model_validate(c) for c in raw]
        assert all(c.category == category for c in parsed)
        cases.extend(parsed)
    assert len(cases) == len({c.id for c in cases}), "duplicate case ID"
    expected = {c["id"]: (c["question"], c["category"]) for c in manifest["cases"]}
    assert len(expected) == len(manifest["cases"]), "duplicate catalog ID"
    assert {c.id: (c.question, c.category) for c in cases} == expected, "catalog coverage changed"
    return cases
