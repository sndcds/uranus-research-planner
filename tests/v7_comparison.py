"""Strict structural comparisons and bounded, non-sensitive assertion formatting."""

import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue


class DiagnosticModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class Difference(DiagnosticModel):
    path: str
    expected: JsonValue = Field(repr=False)
    actual: JsonValue = Field(repr=False)
    kind: Literal["mismatch", "missing", "forbidden_value"]


def lookup(data: Any, path: str) -> tuple[bool, Any]:
    try:
        for part in path.split("."):
            data = data[int(part)] if isinstance(data, list) else data[part]
        return True, data
    except (KeyError, IndexError, TypeError, ValueError):
        return False, None


def structural_diff(path: str, expected: Any, actual: Any) -> list[Difference]:
    if expected == actual:
        return []
    if isinstance(expected, dict) and isinstance(actual, dict):
        differences = []
        for key in sorted(expected.keys() | actual.keys()):
            child = f"{path}.{key}"
            if key not in expected or key not in actual:
                differences.append(
                    Difference(
                        path=child,
                        expected=expected.get(key),
                        actual=actual.get(key),
                        kind="missing",
                    )
                )
            else:
                differences.extend(structural_diff(child, expected[key], actual[key]))
        return differences
    if isinstance(expected, list) and isinstance(actual, list):
        differences = []
        for index in range(max(len(expected), len(actual))):
            child = f"{path}.{index}"
            if index >= len(expected) or index >= len(actual):
                differences.append(
                    Difference(
                        path=child,
                        expected=expected[index] if index < len(expected) else None,
                        actual=actual[index] if index < len(actual) else None,
                        kind="missing",
                    )
                )
            else:
                differences.extend(structural_diff(child, expected[index], actual[index]))
        return differences
    return [Difference(path=path, expected=expected, actual=actual, kind="mismatch")]


def compare_fields(
    data: dict[str, Any], question: str, expect: dict[str, Any], forbid: dict[str, list[Any]]
) -> list[Difference]:
    differences = structural_diff("original_query", question, data["original_query"])
    for path, expected in sorted(expect.items()):
        found, actual = lookup(data, path)
        if not found:
            differences.append(
                Difference(path=path, expected=expected, actual=None, kind="missing")
            )
        else:
            differences.extend(structural_diff(path, expected, actual))
    for path, forbidden in sorted(forbid.items()):
        found, actual = lookup(data, path)
        if not found or actual in forbidden:
            differences.append(
                Difference(
                    path=path,
                    expected=forbidden,
                    actual=actual,
                    kind="forbidden_value" if found else "missing",
                )
            )
    return sorted(differences, key=lambda d: (d.path, d.kind))


def brief_differences(case_id: str, differences: list[Difference]) -> str:
    # Never put free-text query/name/output fields into pytest tracebacks. Enum values
    # remain useful; entire objects and lists are represented only by their JSON type.
    from research_planner.research_v7_schema import ResearchQueryPlanV7

    enums: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            enums.update(v for v in value.get("enum", []) if isinstance(v, str))
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(ResearchQueryPlanV7.model_json_schema())

    def brief(value: JsonValue) -> str:
        if value is None or isinstance(value, (bool, int, float)):
            return json.dumps(value)
        if isinstance(value, str) and value in enums:
            return value
        return (
            "<string>"
            if isinstance(value, str)
            else "<array>"
            if isinstance(value, list)
            else "<object>"
        )

    entries = [
        f"path={d.path[:100]} expected={brief(d.expected)} actual={brief(d.actual)} kind={d.kind}"
        for d in differences[:5]
    ]
    return f"case={case_id} differences={len(differences)}: " + "; ".join(entries)
