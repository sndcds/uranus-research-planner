"""Strict JSON: no duplicate keys, NaN/Infinity, or Markdown extraction."""

import json
from typing import Any, NoReturn


def _constant(_: str) -> NoReturn:
    raise ValueError("non_finite_json")


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


def decode(value: str | bytes | bytearray) -> Any:
    return json.loads(value, parse_constant=_constant, object_pairs_hook=_object)
