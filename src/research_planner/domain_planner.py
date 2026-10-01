"""Reviewed DE/EN/DA catalogue. Full-question matching never drops a constraint."""

import re

from research_planner.domain_schema import DataPlan, KnowledgePlan, PlanEnvelopeV4
from research_planner.errors import PlannerError

DATA_QUESTIONS = [
    (
        "event",
        "description_characters",
        (
            "Welches Event hat den längsten Veranstaltungstext?",
            "Which event has the longest description?",
            "Hvilket arrangement har den længste beskrivelse?",
        ),
    ),
    (
        "organization",
        "event_count",
        (
            "Welche Organisation hat die meisten Veranstaltungen?",
            "Which organization has the most events?",
            "Hvilken organisation har flest arrangementer?",
        ),
    ),
    (
        "venue",
        "occurrence_count",
        (
            "Welcher Veranstaltungsort hat die meisten Termine?",
            "Which venue has the most occurrences?",
            "Hvilket sted har flest tidspunkter?",
        ),
    ),
    (
        "event",
        "occurrence_count",
        (
            "Welches Event hat die meisten Termine?",
            "Which event has the most occurrences?",
            "Hvilket arrangement har flest tidspunkter?",
        ),
    ),
    (
        "organization",
        "venue_count",
        (
            "Welche Organisation nutzt die meisten unterschiedlichen Orte?",
            "Which organization uses the most distinct venues?",
            "Hvilken organisation bruger flest forskellige steder?",
        ),
    ),
    (
        "category",
        "event_count",
        (
            "Welche Kategorie kommt am häufigsten vor?",
            "Which category occurs most often?",
            "Hvilken kategori forekommer oftest?",
        ),
    ),
]
KNOWLEDGE_QUESTIONS = [
    (
        "uranus_overview",
        "Uranus Projekt",
        ("Was ist Uranus?", "What is Uranus?", "Hvad er Uranus?"),
    ),
    (
        "admin_overview",
        "uranus-admin Architektur",
        ("Was ist uranus-admin?", "What is uranus-admin?", "Hvad er uranus-admin?"),
    ),
    (
        "semantic_search_repository",
        "Implementierung der semantischen Suche",
        (
            "Welches Repository implementiert die semantische Suche?",
            "Which repository implements semantic search?",
            "Hvilket repository implementerer semantisk søgning?",
        ),
    ),
    (
        "embedding_component",
        "Komponente erzeugt Embeddings für Eventsuche",
        (
            "Welche Komponente erzeugt die Embeddings?",
            "Welche Komponente erzeugt die Embeddings für die Eventsuche?",
            "Which component produces embeddings for event search?",
            "Hvilken komponent genererer embeddings til arrangementssøgning?",
        ),
    ),
    (
        "embedding_model",
        "Jina Embedding Modell",
        (
            "Welches Modell wird für die Embeddings verwendet?",
            "Which model is used for embeddings?",
            "Hvilken model bruges til embeddings?",
        ),
    ),
    (
        "qdrant_usage",
        "Qdrant Verwendung",
        ("Wo wird Qdrant verwendet?", "Where is Qdrant used?", "Hvor bruges Qdrant?"),
    ),
    (
        "encoder_communication",
        "uranus-admin research-encoder HTTP Kommunikation",
        (
            "Wie kommuniziert uranus-admin mit dem research-encoder?",
            "How does uranus-admin communicate with research-encoder?",
            "Hvordan kommunikerer uranus-admin med research-encoder?",
        ),
    ),
    (
        "planner_component",
        "Komponente interpretiert natürliche Recherchefragen",
        (
            "Welche Komponente interpretiert natürliche Recherchefragen?",
            "Which component interprets natural language research questions?",
            "Hvilken komponent fortolker naturlige researchspørgsmål?",
        ),
    ),
    (
        "geocoding",
        "Geocoding Implementierung",
        (
            "Wo ist das Geocoding implementiert?",
            "Where is geocoding implemented?",
            "Hvor er geokodning implementeret?",
        ),
    ),
    (
        "architecture",
        "Kulturbytes Recherchearchitektur Services Beziehungen",
        (
            "Welche Services gehören zur Kulturbytes-Recherchearchitektur?",
            "Wie hängen uranus-admin, research-planner und research-encoder zusammen?",
            "Which services form the Kulturbytes research architecture?",
            "Hvilke tjenester indgår i Kulturbytes researcharkitekturen?",
        ),
    ),
    (
        "founding_date",
        "Kulturbytes explizites Gründungsdatum",
        (
            "Wann wurde Kulturbytes gegründet?",
            "When was Kulturbytes founded?",
            "Hvornår blev Kulturbytes grundlagt?",
        ),
    ),
]


def normalize(query: str) -> str:
    return " ".join(query.casefold().strip().removesuffix("?").split())


def interpret(query: str) -> PlanEnvelopeV4:
    normalized = normalize(query)
    for entity, metric, examples in DATA_QUESTIONS:
        if normalized in {normalize(q) for q in examples}:
            return PlanEnvelopeV4(
                original_query=query,
                plan=DataPlan.model_validate({"entity_type": entity, "metric": metric}),
            )
    # Geography is the only extra constraint supported by the first catalogue.
    prefixes = (
        r"welche organisation hat die meisten veranstaltungen in (.+)",
        r"which organization has the most events in (.+)",
        r"hvilken organisation har flest arrangementer i (.+)",
    )
    for prefix in prefixes:
        match = re.fullmatch(prefix, query.strip().removesuffix("?"), flags=re.I)
        if match and re.fullmatch(r"[\wÀ-ž .'-]{1,160}", match[1]):
            return PlanEnvelopeV4(
                original_query=query,
                plan=DataPlan(
                    entity_type="organization", metric="event_count", area_query=match[1]
                ),
            )
    for fact, retrieval, knowledge_examples in KNOWLEDGE_QUESTIONS:
        if normalized in {normalize(q) for q in knowledge_examples}:
            return PlanEnvelopeV4(
                original_query=query,
                plan=KnowledgePlan.model_validate({"knowledge_query": retrieval, "fact": fact}),
            )
    raise PlannerError("planner_unsupported_plan", 422)
