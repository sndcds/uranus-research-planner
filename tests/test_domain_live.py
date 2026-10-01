"""Explicit operator-only v4 language acceptance. Never part of ordinary CI inference."""

import os

import pytest

from research_planner.config import Settings
from research_planner.domain_planner import DomainPlanner
from research_planner.errors import PlannerError
from research_planner.model_client import StructuredModelClient
from research_planner.schemas import PlanRequest
from tests.test_domain_planner import CASES

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RESEARCH_PLANNER_LIVE_TEST") != "1",
        reason="v4 model inference explicitly opt-in only",
    ),
]


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
async def test_domain_language_acceptance(case):
    provider = StructuredModelClient(Settings())
    try:
        planner = DomainPlanner(provider)
        request = PlanRequest(query=case["query"], language=case["language"])
        if case["plan"] is None:
            with pytest.raises(PlannerError) as error:
                await planner.interpret(request)
            assert (error.value.code, error.value.status) == ("planner_unsupported_plan", 422)
        else:
            result = await planner.interpret(request)
            assert result.original_query == case["query"]
            assert result.plan.model_dump() == case["plan"]
    finally:
        await provider.close()
