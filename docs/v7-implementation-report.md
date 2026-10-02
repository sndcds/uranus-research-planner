# v7 implementation report

Historical report for v12. Current canonical changes and results: [v13 report](v7-live-v13-report.md).

Integration-fix base: `0396761b8de4791e9808711f32c0ec13925c4e08` (freshly fetched main).
Branch: `fix/v7-post-merge-integration`.
This repairs the combined PR #16/#17 state; no new Research capability or v7 redesign.

Endpoint: `POST /v7/plan`. Schema: `research-query-plan-v7`. Prompt: `research-planner-v12`.
v5: research-query-plan-v5 / research-planner-v10.
v6: research-query-plan-v6 / research-planner-v11.
Existing v3/v4/v5/v6 endpoints, schemas, prompts and fixtures are frozen at the
accepted post-PR-#16 baseline. No Admin code,
client migration, SQL, database access, retrieval, deployment or merge is included.

## Final contract

Seven entities, twelve generic intents, nonrecursive metrics, typed conjunctive filters,
bounded temporal/spatial/price constraints, closed relation paths, comparisons, trends,
anomaly boundaries, explainability and knowledge routing. No answer_mode or generic DSL.
All fields required; nullable nested objects use null. All models strict, finite and closed.
Executable ranks require a metric; unsupported/undefined partial interpretations cannot
execute and must use an explicit boundary. See the [contract](research-query-plan-v7.md).

The exact production regression is rank/event, metric.operation=occurrence_count,
group_by=event, ordering=desc, limit=1. Event type, genre, venue and organization contrasts
remain separate golden cases and explicit assertions. No execution/UI change is made.

## Golden corpus

455 question occurrences across 25 categories. Every supplied catalog section 39–74,
earlier examples, injection cases, DE/EN/DA additions and all old analytics/geography
questions are retained. Repeated wording across sections is intentional; none removed.

| Capability | Questions |
| --- | ---: |
| knowledge | 8 |
| needs_clarification | 26 |
| needs_context | 21 |
| needs_definition | 91 |
| needs_structured_data | 58 |
| planned | 154 |
| semantic_only | 17 |
| supported | 58 |
| unsupported | 22 |

| Intent | Questions |
| --- | ---: |
| aggregate | 17 |
| anomaly | 47 |
| compare | 12 |
| count | 9 |
| explain | 18 |
| knowledge | 8 |
| list | 130 |
| rank | 142 |
| relation | 22 |
| search | 20 |
| taxonomy | 18 |
| trend | 12 |

Every needs_definition, needs_structured_data, needs_context, knowledge and semantic_only
question is listed individually by ID, wording, notes and dependency in the generated
[capability report](v7-corpus-report.json). It also includes category/entity/feature counts.
The 58 supported cases indicate likely reuse of existing Admin families through an adapter,
not deployed v7 support. Additional needs_clarification/unsupported statuses prevent
misrepresenting unresolved or unrepresentable questions as complete planned capabilities.

## Admin follow-up and limitations

See the [Admin handoff](v7-admin-handoff.md) for every executor family and source dependency.
Candidate reuse: structured lists/counts, taxonomy, existing name/area/place resolution,
relative timing and coordinate extrema. New/verified execution: prices, missing fields,
event/description/duration/distinct ranks, graph paths, radii/borders, ratios and trends.
Missing authoritative data includes population, history, provenance, POIs, media lineage
and audience/accessibility classifications for exact statistics. Prior-result explanations
need a future context contract; project knowledge routes to its separate service.

Known language limits: one grouping, AND filters, no arbitrary OR/set difference, no
consecutive-day measure, price-range subtraction, largest-group share, image/source entity
or graph-centrality expression. These are explicit unsupported cases, not substituted questions.
Currency initially EUR only. Regularity, outlier and evaluative terms require definitions.
Semantic evidence is never an exact population. Live Terra acceptance has not been run;
mocked model tests prove wire/validation/coverage, not language accuracy. Existing token
and timeout bounds remain unchanged; adequacy for complex live v7 output is unverified.

## Validation

Before changes, the combined main reproduced exactly **2 failed, 3306 passed,
702 skipped** in 52.00 s: the legacy freeze and corpus coverage tests. No other
failures occurred. Final integration-fix result: **3335 passed, 710 skipped** in 58.57 s.
All normal tests pass; the eight added live cases remain opt-in (702 + 8 skipped).
Locked dev sync, Ruff, format (60 files), Mypy (28 source files), documentation links,
OpenAPI regeneration and diff checks passed. No live provider test was forced.
The strict legacy freeze and corpus coverage tests both pass; no protection was weakened.
Local commands: uv sync --locked --group dev; uv run pytest -q; uv run ruff check .;
uv run ruff format --check .; uv run mypy; git diff --check;
uv run python scripts/check_doc_links.py; reproducible scripts/export_openapi.py.
No local Docker, PostgreSQL, Qdrant, Jina, Nominatim or live provider calls.
Backward compatibility is checked with the original suites plus frozen source/fixture and
all old OpenAPI-operation/component digests. GitHub CI is started by the PR; no waiting
for its completion, deployment or merge.

## Files introduced by the original v7 PR (historical)

- `docs/research-query-plan-v7.md`
- `docs/v7-admin-handoff.md`
- `docs/v7-corpus-report.json`
- `docs/v7-implementation-report.md`
- `docs/v7-repository-audit.md`
- `scripts/report_v7_corpus.py`
- `src/research_planner/research_v7_constraints.py`
- `src/research_planner/research_v7_prompts.py`
- `src/research_planner/research_v7_schema.py`
- `src/research_planner/research_v7_types.py`
- `tests/fixtures/v7/accessibility.json`
- `tests/fixtures/v7/anomalies.json`
- `tests/fixtures/v7/audiences.json`
- `tests/fixtures/v7/combined.json`
- `tests/fixtures/v7/comparisons.json`
- `tests/fixtures/v7/content.json`
- `tests/fixtures/v7/explain.json`
- `tests/fixtures/v7/gaps.json`
- `tests/fixtures/v7/geography.json`
- `tests/fixtures/v7/graph.json`
- `tests/fixtures/v7/journalism.json`
- `tests/fixtures/v7/knowledge.json`
- `tests/fixtures/v7/media.json`
- `tests/fixtures/v7/organizations.json`
- `tests/fixtures/v7/prices.json`
- `tests/fixtures/v7/provenance.json`
- `tests/fixtures/v7/quality.json`
- `tests/fixtures/v7/ranking.json`
- `tests/fixtures/v7/regressions.json`
- `tests/fixtures/v7/relations.json`
- `tests/fixtures/v7/security.json`
- `tests/fixtures/v7/taxonomy.json`
- `tests/fixtures/v7/temporal.json`
- `tests/fixtures/v7/trends.json`
- `tests/fixtures/v7/venues.json`
- `tests/fixtures/v7_catalog.json`
- `tests/fixtures/v7_legacy_contracts.json`
- `tests/fixtures/v7_schema.json`
- `tests/test_research_v7_client.py`
- `tests/test_research_v7_contract.py`
- `tests/test_research_v7_corpus.py`
- `tests/test_research_v7_live.py`
- `tests/v7_golden.py`

## Existing files extended by the original v7 PR (historical)

- `README.md`
- `docs/openapi.json`
- `src/research_planner/app.py`
- `src/research_planner/model_client.py`
- `src/research_planner/planner.py`
- `src/research_planner/security.py`

## Post-merge corpus reconciliation

PR #16 added 17 analytics questions: nine already existed in v7, eight did not.
Its one geography question, “Welches Event hat die meisten Termine?”, already existed
as ranking-039-004. None of the original 447 cases was removed or changed. The eight
new planned rank cases bring the reviewed total to **455**:

| ID | Newly covered question | Group | Order / limit |
| --- | --- | --- | --- |
| regressions-093-001 | Welche Veranstaltungen haben besonders viele Termine? | event | desc / 20 |
| regressions-093-002 | Welche Event-Typen haben die meisten Termine? | event_type | desc / 20 |
| regressions-093-003 | Which event has the fewest dates? | event | asc / 1 |
| regressions-093-004 | Which 5 events have the most occurrences? | event | desc / 5 |
| regressions-093-005 | Which event type has the most occurrences? | event_type | desc / 1 |
| regressions-093-006 | Hvilken begivenhed har færrest datoer? | event | asc / 1 |
| regressions-093-007 | Hvilke 5 arrangementer har flest datoer? | event | desc / 5 |
| regressions-093-008 | Hvilken begivenhedstype har flest datoer? | event_type | desc / 1 |

Each uses entity event and metric.operation occurrence_count, no taxonomy filter,
no semantic search and no generic list. The new section 93 and exact 455-case count
are pinned; both original strict protection tests remain intact. Added regressions
check v5/v6 event grouping and occurrence-count-only validation, complete legacy query
coverage, and distinct v5/v6/v7 versions on actual endpoint responses, diagnostics,
OpenAPI and logs. The v7 agent identity is research-planner-v12; prompt interpretation
text and the entire v7 data algebra are unchanged.

See the [individual legacy hash audit](v7-repository-audit.md) for all 18 pinned files
and the eight updated OpenAPI components. This fix changes no legacy source or fixture.

## Files changed by this integration fix

- `README.md`
- `docs/openapi.json`
- `docs/research-query-plan-v7.md`
- `docs/v7-admin-handoff.md`
- `docs/v7-corpus-report.json`
- `docs/v7-implementation-report.md`
- `docs/v7-repository-audit.md`
- `src/research_planner/app.py`
- `src/research_planner/model_client.py`
- `src/research_planner/research_v7_prompts.py`
- `src/research_planner/research_v7_schema.py`
- `tests/fixtures/v7/regressions.json`
- `tests/fixtures/v7_catalog.json`
- `tests/fixtures/v7_legacy_contracts.json`
- `tests/test_research_v7_client.py`
- `tests/test_research_v7_contract.py`
- `tests/test_research_v7_corpus.py`
