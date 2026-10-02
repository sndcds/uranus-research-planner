"""Internal proposal normalization; the public v8 model remains strictly validated."""

import json
from copy import deepcopy
from typing import Any

from pydantic import ConfigDict, create_model, model_validator

from research_planner.research_v8_schema import ResearchQueryPlanV8
from research_planner.research_v8_types import COUNT_OPERATIONS, ClosedV8

# Reuse every field constraint and nested validator, without duplicating vocabulary
# or invoking the final plan's cross-field validator before normalization. This is
# internal only: NativeOutput and OpenAPI still expose ResearchQueryPlanV8's schema.
# Any is confined to Pydantic's model-construction API, never a plan field.
_fields: dict[str, Any] = {
    name: (field.annotation, deepcopy(field))
    for name, field in ResearchQueryPlanV8.model_fields.items()
}
ProposalV8 = create_model("ProposalV8", __base__=ClosedV8, **_fields)


def canonicalize_v8(value: object) -> object:
    # Check even fields that will be neutralized. Unknown enums, extra properties,
    # malformed nested constraints and missing fields must never be hidden.
    proposal = ProposalV8.model_validate_json(json.dumps(value, allow_nan=False))
    data = proposal.model_dump(mode="python")
    intent = data["intent"]
    if intent != "taxonomy":
        data["taxonomy"] = None
    else:
        data["entity_type"] = "event"
        data["group_by"] = "none"
        data["metric"] = None
        data["metric_filter"] = None
    if intent == "rank" and data["group_by"] in {"category", "event_type", "genre"}:
        data["entity_type"] = "event"
    # An explicitly unsupported subject must never become a supported entity just
    # to satisfy an invented entity grouping. Keep the unsupported subject/metric.
    if (
        intent == "rank"
        and data["entity_type"] is None
        and data["unsupported_reason"] == "unsupported_constraint"
        and data["group_by"]
        in {"event", "occurrence", "venue", "space", "organization", "municipality", "region"}
    ):
        data["group_by"] = "none"
    # Approved temporal-frequency presentation default; never infer intent/metric
    # or replace explicitly supplied ordering/limit. Scalar/category tables differ.
    if (
        intent == "aggregate"
        and data["group_by"] in {"hour", "weekday", "week", "month", "year"}
        and data["metric"] is not None
        and data["metric"]["operation"] in COUNT_OPERATIONS
    ):
        if data["ordering"] is None:
            data["ordering"] = "desc"
        if data["limit"] is None:
            data["limit"] = 20
    if intent != "anomaly":
        data["anomaly"] = None
    if intent != "trend":
        data["trend"] = None
    if intent not in {"relation", "rank", "count", "aggregate", "compare"}:
        data["relation"] = None
    return data


class CanonicalModelOutputV8(ResearchQueryPlanV8):
    # A model class avoids NativeOutput's wrapper for non-model annotated types.
    # Only the internal adapter normalizes; the public plan validators are unchanged.
    model_config = ConfigDict(title="ResearchQueryPlanV8")

    @model_validator(mode="before")
    @classmethod
    def canonical_form(cls, value: object) -> object:
        return canonicalize_v8(value)
