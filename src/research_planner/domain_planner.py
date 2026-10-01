"""Model-backed v4 boundary. No catalogue matching, repair, execution or factual answers."""

from typing import Protocol

from pydantic import ValidationError

from research_planner.domain_schema import (
    DataPlan,
    DomainProposal,
    KnowledgePlan,
    PlanEnvelopeV4,
    ProviderDataDecision,
)
from research_planner.errors import PlannerError
from research_planner.schemas import PlanRequest


class DomainModelClient(Protocol):
    async def plan_v4(self, request: PlanRequest) -> DomainProposal: ...


class DomainPlanner:
    def __init__(self, provider: DomainModelClient):
        self.provider = provider

    async def interpret(self, request: PlanRequest) -> PlanEnvelopeV4:
        proposal = await self.provider.plan_v4(request)
        try:
            # Revalidate even injected providers/model_construct/model_copy results.
            proposal = DomainProposal.model_validate_json(proposal.model_dump_json())
            decision = proposal.plan
            if isinstance(decision, KnowledgePlan):
                if decision.knowledge_query != request.query:
                    raise ValueError("knowledge_query_must_preserve_question")
        except (ValueError, TypeError, AttributeError):
            raise PlannerError("planner_invalid_response", 502) from None

        if decision is None:
            raise PlannerError("planner_unsupported_plan", 422)
        plan: DataPlan | KnowledgePlan
        if isinstance(decision, ProviderDataDecision):
            if decision.has_temporal_constraint or decision.has_other_constraint:
                raise PlannerError("planner_unsupported_plan", 422)
            try:
                # Only false constraint flags may be removed. Preserve geography;
                # DataPlan decides whether the entity/metric/area is executable.
                plan = DataPlan.model_validate(
                    decision.model_dump(exclude={"has_temporal_constraint", "has_other_constraint"})
                )
            except ValidationError:
                raise PlannerError("planner_unsupported_plan", 422) from None
        else:
            plan = decision
        try:
            envelope = PlanEnvelopeV4(original_query=request.query, plan=plan)
            return PlanEnvelopeV4.model_validate_json(envelope.model_dump_json())
        except (ValueError, TypeError, AttributeError):
            raise PlannerError("planner_invalid_response", 502) from None
