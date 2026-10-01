"""Model-backed v4 boundary. No catalogue matching, repair, execution or factual answers."""

from typing import Protocol

from research_planner.domain_schema import DomainProposal, KnowledgePlan, PlanEnvelopeV4
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
            if isinstance(proposal.plan, KnowledgePlan):
                if proposal.plan.knowledge_query != request.query:
                    raise ValueError("knowledge_query_must_preserve_question")
            if proposal.plan is not None:
                envelope = PlanEnvelopeV4(original_query=request.query, plan=proposal.plan)
                return PlanEnvelopeV4.model_validate_json(envelope.model_dump_json())
        except (ValueError, TypeError, AttributeError):
            raise PlannerError("planner_invalid_response", 502) from None
        raise PlannerError("planner_unsupported_plan", 422)
