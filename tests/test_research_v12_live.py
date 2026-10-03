"""Opt-in semantic acceptance; ordinary CI does not call a model provider."""

import json
import os
from datetime import date
from pathlib import Path

import pytest

from research_planner.config import Settings
from research_planner.conversation_v12_request import ConversationPlanRequestV12
from research_planner.model_client import StructuredModelClient

CASES = json.loads(Path("tests/fixtures/modern_v12.json").read_text())
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RESEARCH_PLANNER_LIVE_TEST") != "1",
        reason="Explicit live provider opt-in required",
    ),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["name"])
async def test_live_combined_semantics(case):
    client = StructuredModelClient(Settings())
    try:
        request = ConversationPlanRequestV12.model_validate_json(
            json.dumps(
                {
                    "query": case["query"],
                    "conversation_context": case.get("conversation_context"),
                }
            )
        )
        actual = await client.plan_v12(request, date(2026, 10, 3))
        expected = case["plan"]
        data = actual.model_dump(mode="json")
        for key in [
            "original_query",
            "intent",
            "entity_type",
            "spatial",
            "group_by",
            "clarification",
            "unsupported_reason",
        ]:
            assert data[key] == expected[key], key
        if expected["temporal"]:
            for key in [
                "field",
                "period",
                "from_date",
                "to_date",
                "recurring_weekdays",
                "recurring_months",
            ]:
                assert data["temporal"][key] == expected["temporal"][key], key
    finally:
        await client.close()
