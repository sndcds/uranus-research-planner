# Additive domain planning contract v4

Existing `/plan` keeps `research-query-plan-v3`. `POST /v4/plan` accepts the same
bounded authenticated question request but returns `research-query-plan-v4` with
`original_query`, `interpreter_version=reviewed-catalogue-v1` and a discriminated
`plan`. The new endpoint uses a deterministic reviewed DE/EN/DA question catalogue,
not the v3 LLM. Unknown wording/constraints fail with `planner_unsupported_plan`.

Data: `domain=data`, `operation=rank`, entity, compatible allowlisted metric,
ordering, bounded limit and optional unresolved area name. Project:
`domain=project_knowledge`, `operation=evidence_answer`, bounded knowledge_query,
closed fact intent and `answer_mode=evidence`. Plans contain no factual result,
SQL, repository URL, collection, path, API URL or backend selector.

Examples:

| Question | Plan |
| --- | --- |
| Welches Event hat den längsten Veranstaltungstext? | data / event / rank / description_characters / desc / 1 |
| Welche Organisation hat die meisten Veranstaltungen? | data / organization / rank / event_count / desc / 1 |
| Welche Organisation hat die meisten Veranstaltungen in Flensburg? | same, area_query=Flensburg |
| Welches Repository implementiert die semantische Suche? | project_knowledge / evidence_answer / semantic_search_repository |
| Welche Komponente erzeugt die Embeddings für die Eventsuche? | project_knowledge / evidence_answer / embedding_component |
| Wann wurde Kulturbytes gegründet? | project_knowledge / evidence_answer / founding_date; no date supplied |

The complete metric catalogue is in `domain_schema.py`. Only the six implemented
entity/metric pairs validate; duration, per-capita and other reserved metrics cannot
reach an executor yet. Requested other data examples have explicit catalogue entries.
Project questions with no reviewed source assertion can retrieve excerpts but must
return unsupported through the knowledge service; the planner never fabricates facts.

Admin alone routes validated plans: exact PostgreSQL locally, or the authenticated
knowledge service for source evidence. Initial source registry, graph vocabulary,
provenance and reconcile design live in
[uranus-research-knowledge](https://github.com/sndcds/uranus-research-knowledge).
The encoder contract is unchanged.

Migration: deploy only after separate authorization and review. Add the new service
and source corpus, then opt Admin's separate `/api/v1/research/v4/query` into this
endpoint. The existing Research UI and v3 route do not change. A later LLM-backed
v4 interpreter requires language evaluation and must preserve the same closed
contract. No model evaluation, deployment or production configuration change is
part of this PR. Standard tests use fake v3 providers; the new catalogue has DE/EN/DA
fixtures and authentication regression coverage.
