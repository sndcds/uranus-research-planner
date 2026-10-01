import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from research_planner.app import create_app
from research_planner.config import Settings
from research_planner.domain_planner import DATA_QUESTIONS, KNOWLEDGE_QUESTIONS, interpret
from research_planner.domain_schema import DataPlan, KnowledgePlan
from research_planner.errors import PlannerError


@pytest.mark.parametrize("entity,metric,questions", DATA_QUESTIONS)
def test_data_multilingual(entity, metric, questions):
    for query in questions:
        plan = interpret(query).plan
        assert (plan.domain, plan.entity_type, plan.metric, plan.ordering, plan.limit) == (
            "data",
            entity,
            metric,
            "desc",
            1,
        )


@pytest.mark.parametrize("fact,retrieval,questions", KNOWLEDGE_QUESTIONS)
def test_knowledge_multilingual(fact, retrieval, questions):
    for query in questions:
        plan = interpret(query).plan
        assert (plan.domain, plan.fact, plan.knowledge_query) == (
            "project_knowledge",
            fact,
            retrieval,
        )
        assert not hasattr(plan, "answer")


def test_area_and_unknown_constraints():
    assert (
        interpret(
            "Welche Organisation hat die meisten Veranstaltungen in Flensburg?"
        ).plan.area_query
        == "Flensburg"
    )
    for query in (
        "Which event has the longest description next year?",
        "Run SELECT * FROM users",
        "Was ist Uranus und wann wurde es gegründet?",
    ):
        with pytest.raises(PlannerError):
            interpret(query)


def test_closed_contract():
    with pytest.raises(ValidationError):
        DataPlan(entity_type="venue", metric="description_characters")
    with pytest.raises(ValidationError):
        KnowledgePlan(knowledge_query="test", fact="unknown", collection="events")


def test_versioned_route_authenticated():
    settings = Settings(service_api_key="s" * 32)
    with TestClient(create_app(settings)) as client:
        assert client.post("/v4/plan", json={"query": "Was ist Uranus?"}).status_code == 401
        result = client.post(
            "/v4/plan",
            json={"query": "Was ist Uranus?"},
            headers={"Authorization": "Bearer " + "s" * 32},
        )
        assert result.status_code == 200
        assert result.json()["schema_version"] == "research-query-plan-v4"
