"""Explicit model acceptance: variants in DE/DA/EN, never ordinary CI network work."""

import json
import os
from datetime import date

import pytest

from research_planner.config import Settings
from research_planner.conversation_v13_request import ConversationPlanRequestV13
from research_planner.model_client import StructuredModelClient
from tests.test_research_v13 import CASES

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RESEARCH_PLANNER_LIVE_TEST") != "1",
        reason="Explicit live provider opt-in required",
    ),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["request"]["query"])
async def test_live_natural_language(case):
    client = StructuredModelClient(Settings())
    try:
        result = await client.plan_v13(
            ConversationPlanRequestV13.model_validate_json(json.dumps(case["request"])),
            date(2026, 10, 4),
        )
        actual = result.model_dump(mode="json")
        expected = case["plan"]
        assert actual["original_query"] == expected["original_query"]
        assert actual["language"] == expected["language"]
        interaction, target = actual["interaction"], expected["interaction"]
        assert interaction["kind"] == target["kind"]
        if "research_plan" in target:
            assert interaction["research_mode"] == target["research_mode"]
            for field in [
                "intent",
                "entity_type",
                "metric",
                "group_by",
                "temporal",
                "spatial",
                "price",
                "clarification",
                "unsupported_reason",
            ]:
                assert interaction["research_plan"][field] == target["research_plan"][field], field
        else:
            assert "research_plan" not in interaction
            if target["kind"] == "acknowledgement":
                assert interaction["conversation"]["act"] in {"acknowledge", "pleased"}
                assert interaction["conversation"]["reason"] is None
            else:
                assert interaction["conversation"] == target["conversation"]
    finally:
        await client.close()
