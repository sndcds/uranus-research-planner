"""Internal proposal normalization; the public v7 model remains strictly validated."""

import json
from copy import deepcopy
from typing import Any

from pydantic import ConfigDict, create_model, model_validator

from research_planner.research_v7_schema import ResearchQueryPlanV7
from research_planner.research_v7_types import ClosedV7

# Reuse every field constraint and nested validator, without duplicating vocabulary
# or invoking the final plan's cross-field validator before normalization. This is
# internal only: NativeOutput and OpenAPI still expose ResearchQueryPlanV7's schema.
# Any is confined to Pydantic's model-construction API, never a plan field.
_fields: dict[str, Any] = {
    name: (field.annotation, deepcopy(field))
    for name, field in ResearchQueryPlanV7.model_fields.items()
}
ProposalV7 = create_model("ProposalV7", __base__=ClosedV7, **_fields)


def canonicalize_v7(value: object) -> object:
    # Check even fields that will be neutralized. Unknown enums, extra properties,
    # malformed nested constraints and missing fields must never be hidden.
    proposal = ProposalV7.model_validate_json(json.dumps(value, allow_nan=False))
    data = proposal.model_dump(mode="python")
    intent = data["intent"]
    if intent != "taxonomy":
        data["taxonomy"] = None
    else:
        data["group_by"] = "none"
        data["metric"] = None
        data["metric_filter"] = None
    if intent == "rank" and data["group_by"] in {"category", "event_type", "genre"}:
        data["entity_type"] = "event"
    if intent != "anomaly":
        data["anomaly"] = None
    if intent != "trend":
        data["trend"] = None
    if intent not in {"relation", "rank", "count", "aggregate", "compare"}:
        data["relation"] = None
    return data


class CanonicalModelOutputV7(ResearchQueryPlanV7):
    # A model class avoids NativeOutput's wrapper for non-model annotated types.
    # Only the internal adapter normalizes; the public plan validators are unchanged.
    model_config = ConfigDict(title="ResearchQueryPlanV7")

    @model_validator(mode="before")
    @classmethod
    def canonical_form(cls, value: object) -> object:
        return canonicalize_v7(value)
