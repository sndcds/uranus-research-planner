"""Optional semantic evaluation; mocks do NOT establish real language accuracy."""

import os
from datetime import date

import pytest

from research_planner.config import Settings
from research_planner.model_client import StructuredModelClient
from research_planner.schemas import PlanRequest
from tests.conftest import FIXTURES, assert_golden_plan, fixture_plan

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RESEARCH_PLANNER_LIVE_TEST") != "1",
        reason="local model explicitly opt-in only",
    ),
]


@pytest.mark.parametrize("case", FIXTURES, ids=lambda case: case["id"])
async def test_local_model_semantics(case):
    expected = fixture_plan(case)
    client = StructuredModelClient(Settings())
    try:
        result = await client.plan(PlanRequest(query=case["query"]), date(2026, 9, 29))
        assert_golden_plan(result, expected)
    finally:
        await client.close()
