"""Opt-in current-provider language acceptance; no ordinary-test inference."""

import os
from datetime import date

import pytest

from research_planner.config import Settings
from research_planner.model_client import StructuredModelClient
from research_planner.schemas import PlanRequest
from tests.test_analytics import CASES

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RESEARCH_PLANNER_LIVE_TEST") != "1",
        reason="Live model acceptance requires explicit provider configuration",
    ),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["query"])
async def test_analytical_language_acceptance(case):
    provider = StructuredModelClient(Settings())
    try:
        actual = await provider.plan_v5(PlanRequest(query=case["query"]), date(2026, 10, 2))
        assert actual.model_dump(mode="json") == case["plan"]
    finally:
        await provider.close()
