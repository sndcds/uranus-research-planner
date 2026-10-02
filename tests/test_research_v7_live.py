"""Explicit opt-in language acceptance; never an ordinary CI dependency."""

import os
from datetime import date

import pytest

from research_planner.config import Settings
from research_planner.model_client import StructuredModelClient
from research_planner.schemas import PlanRequest
from tests.v7_golden import assert_v7_expectations, load_v7_golden_cases

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RESEARCH_PLANNER_LIVE_TEST") != "1",
        reason="Explicit live provider opt-in required",
    ),
]


@pytest.mark.parametrize("case", load_v7_golden_cases(), ids=lambda c: c.id)
async def test_live_v7_language_acceptance(case):
    provider = StructuredModelClient(Settings())
    try:
        actual = await provider.plan_v7(PlanRequest(query=case.question), date(2026, 10, 2))
        assert_v7_expectations(actual, case)
    finally:
        await provider.close()
