"""Provider-independent interpretation boundary; there is deliberately no executor."""

from datetime import date
from typing import Protocol

from research_planner.analytics_schema import AnalyticalQueryPlan
from research_planner.domain_schema import DomainProposal
from research_planner.errors import PlannerError
from research_planner.geography_schema import GeographicQueryPlan
from research_planner.research_v7_schema import ResearchQueryPlanV7
from research_planner.research_v8_schema import ResearchQueryPlanV8
from research_planner.research_v9_schema import ResearchQueryPlanV9
from research_planner.research_v10_schema import ResearchQueryPlanV10
from research_planner.schemas import PlanRequest, ResearchQueryPlan


class ResearchPlanner(Protocol):
    async def plan(self, request: PlanRequest, reference_date: date) -> ResearchQueryPlan: ...

    async def plan_v4(self, request: PlanRequest) -> DomainProposal: ...

    async def plan_v5(self, request: PlanRequest, reference_date: date) -> AnalyticalQueryPlan: ...

    async def plan_v6(self, request: PlanRequest, reference_date: date) -> GeographicQueryPlan: ...

    async def plan_v7(self, request: PlanRequest, reference_date: date) -> ResearchQueryPlanV7: ...

    async def plan_v8(self, request: PlanRequest, reference_date: date) -> ResearchQueryPlanV8: ...

    async def plan_v10(
        self, request: PlanRequest, reference_date: date
    ) -> ResearchQueryPlanV10: ...

    async def plan_v9(self, request: PlanRequest, reference_date: date) -> ResearchQueryPlanV9: ...

    async def ready(self) -> bool: ...

    async def close(self) -> None: ...


class UnavailablePlanner:
    async def plan(self, request: PlanRequest, reference_date: date) -> ResearchQueryPlan:
        raise PlannerError("planner_unavailable")

    async def plan_v4(self, request: PlanRequest) -> DomainProposal:
        raise PlannerError("planner_unavailable")

    async def plan_v5(self, request: PlanRequest, reference_date: date) -> AnalyticalQueryPlan:
        raise PlannerError("planner_unavailable")

    async def plan_v6(self, request: PlanRequest, reference_date: date) -> GeographicQueryPlan:
        raise PlannerError("planner_unavailable")

    async def plan_v7(self, request: PlanRequest, reference_date: date) -> ResearchQueryPlanV7:
        raise PlannerError("planner_unavailable")

    async def plan_v8(self, request: PlanRequest, reference_date: date) -> ResearchQueryPlanV8:
        raise PlannerError("planner_unavailable")

    async def plan_v10(self, request: PlanRequest, reference_date: date) -> ResearchQueryPlanV10:
        raise PlannerError("planner_unavailable")

    async def plan_v9(self, request: PlanRequest, reference_date: date) -> ResearchQueryPlanV9:
        raise PlannerError("planner_unavailable")

    async def ready(self) -> bool:
        return False

    async def close(self) -> None:
        pass
