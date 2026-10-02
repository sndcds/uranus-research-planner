"""Test/developer-only corpus loading and dotted expectations; no production routing."""

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from research_planner.research_v7_schema import ResearchQueryPlanV7
from tests.v7_comparison import Difference, brief_differences, compare_fields

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
    resolver_name_variants: dict[str, list[str]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def reviewed_name_variants(self) -> Self:
        if len(self.resolver_name_variants) > 16:
            raise ValueError("too_many_name_variant_slots")
        for path, variants in self.resolver_name_variants.items():
            if path in {"spatial.area_query", "spatial.place_query"}:
                spatial = self.expect.get("spatial", self.example.get("spatial"))
                if (
                    not isinstance(spatial, dict)
                    or spatial.get(path.split(".")[1]) not in variants
                    or not 2 <= len(variants) <= 4
                    or len(set(variants)) != len(variants)
                    or any(not v.strip() or len(v) > 160 for v in variants)
                    or spatial.get("relation") is None
                    or spatial.get("reference") not in {"named", "border"}
                ):
                    raise ValueError("invalid_geo_name_variants")
                continue
            match = re.fullmatch(r"filters\.(\d+)\.value", path)
            if match is None or not 2 <= len(variants) <= 4:
                raise ValueError("invalid_name_variant_slot")
            filters = self.expect.get("filters", self.example.get("filters", []))
            index = int(match[1])
            if index >= len(filters):
                raise ValueError("missing_name_variant_filter")
            predicate = filters[index]
            if (
                predicate.get("field") not in {"event_type", "genre"}
                or predicate.get("operator") not in {"eq", "neq"}
                or predicate.get("value") not in variants
                or len(set(variants)) != len(variants)
                or any(not v.strip() or len(v) > 160 for v in variants)
            ):
                raise ValueError("invalid_name_variants")
        return self


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


def compare_v7_expectations(actual: ResearchQueryPlanV7, case: GoldenCase) -> list[Difference]:
    data = actual.model_dump(mode="json")
    differences = compare_fields(data, case.question, case.expect, case.forbid)
    # Only explicitly audited unresolved-name slots. Never normalize the actual plan,
    # unrelated names, roles, filter order/length, forbidden values or missing paths.
    accepted = set()
    for path, variants in case.resolver_name_variants.items():
        if path in {"spatial.area_query", "spatial.place_query"}:
            expected_spatial = case.expect.get("spatial", case.example.get("spatial"))
            observed_spatial = data["spatial"]
            if (
                isinstance(expected_spatial, dict)
                and observed_spatial is not None
                and observed_spatial["relation"] == expected_spatial["relation"]
                and observed_spatial["reference"] == expected_spatial["reference"]
                and observed_spatial[path.split(".")[1]] in variants
            ):
                accepted.add(path)
            continue
        index = int(path.split(".")[1])
        expected = case.expect.get("filters", case.example.get("filters", []))[index]
        if index < len(data["filters"]):
            observed = data["filters"][index]
            if (
                observed.get("field") == expected["field"]
                and observed.get("operator") == expected["operator"]
                and observed.get("value") in variants
            ):
                accepted.add(path)
    return [d for d in differences if d.kind != "mismatch" or d.path not in accepted]


def assert_v7_expectations(actual: ResearchQueryPlanV7, case: GoldenCase) -> None:
    differences = compare_v7_expectations(actual, case)
    if differences:
        # Explicit raise avoids pytest rewriting and dumping the full Difference payloads.
        raise AssertionError(brief_differences(case.id, differences))


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
