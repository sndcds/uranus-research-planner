"""Provider-independent interpretation boundary; there is deliberately no executor."""

from datetime import date
from typing import Protocol

from research_planner.errors import PlannerError
from research_planner.schemas import PlanRequest, ResearchQueryPlan


class ResearchPlanner(Protocol):
    async def plan(self, request: PlanRequest, reference_date: date) -> ResearchQueryPlan: ...

    async def ready(self) -> bool: ...

    async def close(self) -> None: ...


class UnavailablePlanner:
    async def plan(self, request: PlanRequest, reference_date: date) -> ResearchQueryPlan:
        raise PlannerError("planner_unavailable")

    async def ready(self) -> bool:
        return False

    async def close(self) -> None:
        pass
