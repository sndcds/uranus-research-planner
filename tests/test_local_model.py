"""Optional semantic evaluation; mocks do NOT establish real language accuracy."""

import os
from datetime import date

import pytest

from research_planner.config import Settings
from research_planner.model_client import StructuredModelClient
from research_planner.schemas import PlanRequest
from tests.conftest import FIXTURES

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RESEARCH_PLANNER_LIVE_TEST") != "1",
        reason="local model explicitly opt-in only",
    ),
]


@pytest.mark.parametrize("case", FIXTURES, ids=lambda case: case["id"])
async def test_local_model_semantics(case):
    client = StructuredModelClient(Settings())
    try:
        result = await client.plan(PlanRequest(query=case["query"]), date(2026, 9, 29))
        actual = result.model_dump(mode="json")
        for key, expected in case["plan"].items():
            if key == "semantic_query":
                assert bool(actual[key]) == bool(expected)
            else:
                assert actual[key] == expected
        # Critical negative constraints matter even where fixtures omit default values.
        from tests.conftest import make_plan

        expected_plan = make_plan(case["query"], **case["plan"])
        for key in (
            "area_query",
            "venue_query",
            "organization_query",
            "metric",
            "requires_semantic_relevance",
            "intent",
            "temporal",
        ):
            assert actual[key] == getattr(expected_plan, key)
    finally:
        await client.close()
