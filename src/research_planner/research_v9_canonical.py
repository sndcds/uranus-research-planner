"""Internal proposal normalization; the public v9 model remains strictly validated."""

import json
from copy import deepcopy
from typing import Any

from pydantic import ConfigDict, create_model, model_validator

from research_planner.research_v9_constraints import RelationV9, TemporalV9
from research_planner.research_v9_schema import ResearchQueryPlanV9
from research_planner.research_v9_types import COUNT_OPERATIONS, ClosedV9, MetricV9

# Reuse field constraints and nested validators without duplicating vocabulary.
# Metric operands and taxonomy co-occurrence have explicit normal forms below;
# final plan cross-validation always follows normalization. This is
# internal only: NativeOutput and OpenAPI still expose ResearchQueryPlanV9's schema.
# Any is confined to Pydantic's model-construction API, never a plan field.
_fields: dict[str, Any] = {
    name: (field.annotation, deepcopy(field))
    for name, field in ResearchQueryPlanV9.model_fields.items()
}
# Only an explicitly undefined, operand-free diversity descriptor has a neutral
# form before metric cross-validation. Keep every metric field/type constraint.
_metric_fields: dict[str, Any] = {
    name: (field.annotation, deepcopy(field)) for name, field in MetricV9.model_fields.items()
}
ProposalMetricV9 = create_model("MetricV9", __base__=ClosedV9, **_metric_fields)
_fields["metric"] = (ProposalMetricV9 | None, deepcopy(ResearchQueryPlanV9.model_fields["metric"]))
_relation_fields: dict[str, Any] = {
    name: (field.annotation, deepcopy(field)) for name, field in RelationV9.model_fields.items()
}
ProposalRelationV9 = create_model("RelationV9", __base__=ClosedV9, **_relation_fields)
_fields["relation"] = (
    ProposalRelationV9 | None,
    deepcopy(ResearchQueryPlanV9.model_fields["relation"]),
)
_temporal_fields: dict[str, Any] = {
    name: (field.annotation, deepcopy(field)) for name, field in TemporalV9.model_fields.items()
}
ProposalTemporalV9 = create_model("TemporalV9", __base__=ClosedV9, **_temporal_fields)
_fields["temporal"] = (
    ProposalTemporalV9 | None,
    deepcopy(ResearchQueryPlanV9.model_fields["temporal"]),
)
ProposalV9 = create_model("ProposalV9", __base__=ClosedV9, **_fields)


def canonicalize_v9(value: object) -> object:
    # Type-check even neutralized fields: unknown enums, extra properties and
    # missing fields are rejected. Deferred cross-field rules are explicit below.
    proposal = ProposalV9.model_validate_json(json.dumps(value, allow_nan=False))
    data = proposal.model_dump(mode="python")
    if len(data["group_by"]) != len(set(data["group_by"])):
        raise ValueError("duplicate_grouping_dimensions")
    intent = data["intent"]
    temporal = data["temporal"]
    if temporal is not None:
        # Only a completely empty occurrence-time descriptor under an explicit
        # date block is redundant. Metadata fields, partial dates/lookbacks and
        # every actual constraint retain their meaning and strict validation.
        empty = {
            "field": "start_date",
            "period": "none",
            "time_of_day": "none",
            "calendar_relation": "none",
            "overlap": False,
            "multi_day": False,
        }
        if data["clarification"] == "needs_date" and all(
            value == empty.get(key) for key, value in temporal.items()
        ):
            data["temporal"] = None
        else:
            TemporalV9.model_validate_json(
                json.dumps(proposal.model_dump(mode="json")["temporal"], allow_nan=False)
            )
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
        RelationV9.model_validate_json(json.dumps(relation, allow_nan=False))
    metric = data["metric"]
    if metric is not None:
        if metric["operation"] in COUNT_OPERATIONS:
            # Direct counts have no projected field, nested measure or frequency window. Their
            # population is already completely specified by the count operation.
            metric["field"] = None
            metric["measure"] = None
            metric["window"] = None
        if (
            intent in {"rank", "compare"}
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
            MetricV9.model_validate_json(json.dumps(metric, allow_nan=False))
            if (
                intent in {"list", "search"}
                and not data["group_by"]
                and data["metric_filter"] is None
                and data["ordering"] is None
                and data["relation"] is None
                and data["trend"] is None
                and data["anomaly"] is None
                and metric["operation"] in COUNT_OPERATIONS | {"value"}
            ):
                # A validated record-selection proposal declares no quantitative
                # operation consuming this scalar. Conflicting rank/group/filter
                # semantics are not repaired or discarded here.
                data["metric"] = None
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
        data["group_by"] = []
        data["metric"] = None
        data["metric_filter"] = None
    if (
        intent == "rank"
        and len(data["group_by"]) == 1
        and data["group_by"][0] in {"category", "event_type", "genre"}
    ):
        data["entity_type"] = "event"
    if intent != "compare":
        data["comparison_targets"] = []
    targets = data["comparison_targets"]
    if (
        intent == "compare"
        and len(targets) >= 2
        and len({target["kind"] for target in targets}) == 1
        and targets[0]["kind"] in {"venue", "organization", "municipality", "region"}
        and data["group_by"] in ([], [targets[0]["kind"]])
        and data["unsupported_reason"] != "unsupported_constraint"
    ):
        # Explicit homogeneous targets define the comparison subject, not its
        # measure. Never fill missing targets, metrics or clarification states.
        data["entity_type"] = targets[0]["kind"]
        data["group_by"] = [targets[0]["kind"]]
    # An explicitly unsupported subject must never become a supported entity just
    # to satisfy an invented entity grouping. Keep the unsupported subject/metric.
    if (
        intent == "rank"
        and data["entity_type"] is None
        and data["unsupported_reason"] == "unsupported_constraint"
        and len(data["group_by"]) == 1
        and data["group_by"][0]
        in {"event", "occurrence", "venue", "space", "organization", "municipality", "region"}
    ):
        data["group_by"] = []
    # Approved temporal-frequency presentation default; never infer intent/metric
    # or replace explicitly supplied ordering/limit. Scalar/category tables differ.
    if (
        intent == "aggregate"
        and len(data["group_by"]) == 1
        and data["group_by"][0] in {"hour", "weekday", "week", "month", "year"}
        and data["metric"] is not None
        and data["metric"]["operation"] in COUNT_OPERATIONS
    ):
        if data["ordering"] is None:
            data["ordering"] = "desc"
        if data["limit"] is None:
            data["limit"] = 20
    if (
        intent == "rank"
        and data["clarification"] == "needs_definition"
        and data["metric"] is not None
        and data["metric"]["operation"] == "regularity"
        and data["ordering"] is None
    ):
        # The documented blocked regularity descriptor defaults to descending.
        # Preserve explicit direction and never invent its metric/window/limit.
        data["ordering"] = "desc"
    if intent != "anomaly":
        data["anomaly"] = None
    if intent != "trend":
        data["trend"] = None
    if intent not in {"relation", "rank", "count", "aggregate", "compare"}:
        data["relation"] = None
    return data


class CanonicalModelOutputV9(ResearchQueryPlanV9):
    # A model class avoids NativeOutput's wrapper for non-model annotated types.
    # Only the internal adapter normalizes; the public plan validators are unchanged.
    model_config = ConfigDict(title="ResearchQueryPlanV9")

    @model_validator(mode="before")
    @classmethod
    def canonical_form(cls, value: object) -> object:
        return canonicalize_v9(value)
