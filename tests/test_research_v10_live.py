"""Opt-in language acceptance for concrete and recurring month semantics."""

import os

import pytest

from research_planner.config import Settings
from research_planner.model_client import StructuredModelClient
from research_planner.schemas import PlanRequest
from tests.v10_month_cases import CASES, assert_month_case

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RESEARCH_PLANNER_LIVE_TEST") != "1",
        reason="Explicit live provider opt-in required",
    ),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.query + str(c.reference.year))
async def test_live_month_language_acceptance(case):
    client = StructuredModelClient(Settings())
    try:
        actual = await client.plan_v10(
            PlanRequest(query=case.query, timezone="Europe/Berlin"), case.reference
        )
        assert_month_case(actual, case)
    finally:
        await client.close()
