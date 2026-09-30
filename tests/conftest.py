import json
import os
import socket
from datetime import date
from pathlib import Path

import pytest
from pydantic import SecretStr

from research_planner.config import Settings
from research_planner.schemas import PlanRequest, ResearchQueryPlan

KEY = "test-service-key-not-a-secret"
MODEL_KEY = "test-model-key-not-a-secret"
FIXTURES = json.loads((Path(__file__).parent / "fixtures" / "queries.json").read_text())


def fixture_plan(case):
    """Golden plans are complete wire objects; never inherit make_plan defaults."""
    plan = ResearchQueryPlan.model_validate_json(json.dumps(case["plan"]))
    assert plan.original_query == case["query"]
    return plan


def assert_golden_plan(actual, expected):
    """Only semantic_query casing may vary; its full content must still match.

    Names, original_query, semantic_focus, dates, lists and all other fields stay exact.
    This normalization is exclusively a test comparison, never runtime plan repair.
    """

    def normalized(plan):
        data = plan.model_dump(mode="json")
        if data["semantic_query"] is not None:
            data["semantic_query"] = data["semantic_query"].casefold()
        return data

    assert normalized(actual) == normalized(expected)


@pytest.fixture(autouse=True)
def forbid_unconfigured_network(monkeypatch):
    if os.getenv("RESEARCH_PLANNER_LIVE_TEST") == "1":
        return

    def blocked(*args, **kwargs):
        raise AssertionError("Ordinary tests must not access network services")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)


def make_plan(query="suche events in glücksburg", **changes):
    data = {
        "original_query": query,
        "intent": "list",
        "entity_type": "event",
        "semantic_query": None,
        "area_query": "Glücksburg",
        "venue_query": None,
        "organization_query": None,
        "category_queries": [],
        "genre_queries": [],
        "temporal": "none",
        "explicit_from_date": None,
        "explicit_to_date": None,
        "time_of_day": "none",
        "metric": "none",
        "group_by": "none",
        "comparison_targets": [],
        "semantic_focus": None,
        "requires_semantic_relevance": False,
        "answer_mode": "records",
        "clarification": "none",
        "unsupported_reason": None,
    }
    data.update(changes)
    return ResearchQueryPlan.model_validate_json(json.dumps(data))


class FakePlanner:
    def __init__(self, plan=None):
        self.result = plan or make_plan()
        self.calls = []
        self.closed = False
        self.available = True

    async def plan(self, request: PlanRequest, reference_date: date) -> ResearchQueryPlan:
        self.calls.append((request, reference_date))
        return self.result

    async def ready(self):
        return self.available

    async def close(self):
        self.closed = True


@pytest.fixture
def settings():
    return Settings(
        model_url="http://127.0.0.1:8091",
        service_api_key=SecretStr(KEY),
        model_api_key=SecretStr(MODEL_KEY),
        _env_file=None,
    )


@pytest.fixture
def auth():
    return {"Authorization": "Bearer " + KEY}
