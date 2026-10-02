# v7 implementation report

Base: `e73358cc7ceec06f0edeb7d486ba75608c30f92a` (freshly fetched main).
Branch: `feat/research-query-language-v7`.

Endpoint: `POST /v7/plan`. Schema: `research-query-plan-v7`. Prompt: `research-planner-v10`.
Existing v3/v4/v5/v6 endpoints, schemas, prompts and fixtures are frozen. No Admin code,
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

447 question occurrences across 25 categories. Every supplied catalog section 39–74,
earlier examples, injection cases, DE/EN/DA additions and all old analytics/geography
questions are retained. Repeated wording across sections is intentional; none removed.

| Capability | Questions |
| --- | ---: |
| knowledge | 8 |
| needs_clarification | 26 |
| needs_context | 21 |
| needs_definition | 91 |
| needs_structured_data | 58 |
| planned | 146 |
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
| rank | 134 |
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

Final local result: **3122 passed, 685 skipped** (explicit opt-in live tests), 49.54 s.
Locked dependency sync, Ruff, format (59 files), Mypy (28 source files), documentation
links, reproducible OpenAPI export and diff checks passed. No language-accuracy claim.
Local commands: uv sync --locked; uv run pytest -q; uv run ruff check .;
uv run ruff format --check .; uv run mypy; git diff --check;
uv run python scripts/check_doc_links.py; reproducible scripts/export_openapi.py.
No local Docker, PostgreSQL, Qdrant, Jina, Nominatim or live provider calls.
Backward compatibility is checked with the original suites plus frozen source/fixture and
all old OpenAPI-operation/component digests. GitHub CI is started by the PR; no waiting
for its completion, deployment or merge.

## New files

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

## Existing files minimally extended

- `README.md`
- `docs/openapi.json`
- `src/research_planner/app.py`
- `src/research_planner/model_client.py`
- `src/research_planner/planner.py`
- `src/research_planner/security.py`
