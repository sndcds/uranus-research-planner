"""Internal proposal normalization; the public v7 model remains strictly validated."""

import json
from copy import deepcopy
from typing import Any

from pydantic import ConfigDict, create_model, model_validator

from research_planner.research_v7_constraints import RelationV7
from research_planner.research_v7_schema import ResearchQueryPlanV7
from research_planner.research_v7_types import COUNT_OPERATIONS, ClosedV7, MetricV7

# Reuse field constraints and nested validators without duplicating vocabulary.
# Metric operands and taxonomy co-occurrence have explicit normal forms below;
# final plan cross-validation always follows normalization. This is
# internal only: NativeOutput and OpenAPI still expose ResearchQueryPlanV7's schema.
# Any is confined to Pydantic's model-construction API, never a plan field.
_fields: dict[str, Any] = {
    name: (field.annotation, deepcopy(field))
    for name, field in ResearchQueryPlanV7.model_fields.items()
}
# Only an explicitly undefined, operand-free diversity descriptor has a neutral
# form before metric cross-validation. Keep every metric field/type constraint.
_metric_fields: dict[str, Any] = {
    name: (field.annotation, deepcopy(field)) for name, field in MetricV7.model_fields.items()
}
ProposalMetricV7 = create_model("MetricV7", __base__=ClosedV7, **_metric_fields)
_fields["metric"] = (ProposalMetricV7 | None, deepcopy(ResearchQueryPlanV7.model_fields["metric"]))
_relation_fields: dict[str, Any] = {
    name: (field.annotation, deepcopy(field)) for name, field in RelationV7.model_fields.items()
}
ProposalRelationV7 = create_model("RelationV7", __base__=ClosedV7, **_relation_fields)
_fields["relation"] = (
    ProposalRelationV7 | None,
    deepcopy(ResearchQueryPlanV7.model_fields["relation"]),
)
ProposalV7 = create_model("ProposalV7", __base__=ClosedV7, **_fields)


def canonicalize_v7(value: object) -> object:
    # Type-check even neutralized fields: unknown enums, extra properties and
    # missing fields are rejected. Deferred cross-field rules are explicit below.
    proposal = ProposalV7.model_validate_json(json.dumps(value, allow_nan=False))
    data = proposal.model_dump(mode="python")
    intent = data["intent"]
    relation = data["relation"]
    if relation is not None:
        # A single event joins the explicitly supplied taxonomy dimensions.
        # Same-dimension co-occurrence is shared, cross-dimension is related.
        # Never alter paths, anchored queries or operations with other semantics.
        if (
            intent == "relation"
            and relation["operation"] in {"related", "shared"}
            and relation["source"] in {"category", "event_type", "genre"}
            and relation["target"] in {"category", "event_type", "genre"}
            and relation["via"] == ["event"]
            and relation["source_query"] is None
            and relation["target_query"] is None
        ):
            relation["operation"] = (
                "shared" if relation["source"] == relation["target"] else "related"
            )
            # The declared event path supplies the population; taxonomy nodes
            # are dimensions, not standalone entity types in the public model.
            if data["unsupported_reason"] != "unsupported_constraint":
                data["entity_type"] = "event"
        RelationV7.model_validate_json(json.dumps(relation, allow_nan=False))
    metric = data["metric"]
    if metric is not None:
        if metric["operation"] in COUNT_OPERATIONS:
            # Direct counts have no nested measure or frequency window. Their
            # population is already completely specified by the count operation.
            metric["measure"] = None
            metric["window"] = None
        if (
            intent == "rank"
            and data["clarification"] == "needs_definition"
            and metric["operation"] == "diversity"
            and all(value is None for key, value in metric.items() if key != "operation")
            and data["metric_filter"] is None
        ):
            # No dimension/method was declared. Preserve the block, never guess one.
            data["metric"] = None
        else:
            # Every other metric must pass the unchanged public operand validator,
            # including fields that a later intent normal form would neutralize.
            MetricV7.model_validate_json(json.dumps(metric, allow_nan=False))
    if intent not in {"rank", "aggregate", "trend", "taxonomy", "anomaly"}:
        data["ordering"] = None
    if intent != "trend" and metric is not None:
        if metric["operation"] in {"absolute_change", "percentage_change"}:
            data["metric"] = None
            data["metric_filter"] = None
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


class CanonicalModelOutputV7(ResearchQueryPlanV7):
    # A model class avoids NativeOutput's wrapper for non-model annotated types.
    # Only the internal adapter normalizes; the public plan validators are unchanged.
    model_config = ConfigDict(title="ResearchQueryPlanV7")

    @model_validator(mode="before")
    @classmethod
    def canonical_form(cls, value: object) -> object:
        return canonicalize_v7(value)
