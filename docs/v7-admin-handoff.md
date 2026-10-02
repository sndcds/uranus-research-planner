# v7 Admin handoff (no Admin implementation in this PR)

Integration-fix base: `0396761b8de4791e9808711f32c0ec13925c4e08`.
Frozen v5: research-query-plan-v5 / research-planner-v10.
Frozen v6: research-query-plan-v6 / research-planner-v11.
Proposed endpoint/schema/prompt: `/v7/plan` / research-query-plan-v7 / research-planner-v12.
Keep all existing clients on their existing endpoints until a separately reviewed Admin
adapter and capability validator are ready. No SQL, migrations, source lookups, indexing,
UI, deployment or execution implementation is part of this Planner change.

## Activation boundary

Admin must mirror the closed schema, then reject/clarify any non-plan disposition before
resolution or execution. A valid `kind=plan` is not a guarantee of available source data.
Perform independent capability checks, validate resolved identities and enforce the same
public eligibility filters for every executor. Counts, comparisons and denominators must
use a complete authoritative selected population, not a displayed page or semantic top K.
A missing entity/filter capability must never silently change the question.

The Planner has no live source-model audit. Currency is initially EUR only; released/
cancelled statuses, price bounds, timestamps, population, registration/ticket presence and
all history/provenance claims need source-contract verification. Treat corpus status
supported as a candidate for reuse, not a claim that Admin already accepts v7.

## Executor families

| Family | Contract input | Required follow-up |
| --- | --- | --- |
| Structured records/counts | entity, filters, temporal, price | Adapt existing public population/record/count pipeline; distinguish events from occurrences |
| Taxonomy | taxonomy plus structured constraints | Reuse authoritative category/type/genre resolution; never infer taxonomy from text |
| Aggregates/rankings | metric, group_by, metric_filter, ordering, limit | Entity and dimension groups, distinct IDs, scalar stats, field length, duration; deterministic ties and limit after aggregation |
| Comparisons/per-capita | targets, ratio/percentage operands | Resolve each target independently; compatible units and complete denominators; population source/version |
| Geography | spatial | Named place/area resolution, PostGIS radius/direction/border/distance, eligibility; browser context stays in Admin |
| Relations/graph | source/target/via and operation | Validated domain paths, shared relationships and distinct connected entities; no invented graph edges |
| Temporal/calendar | overlap, multi_day, calendar, lookback | Timezone-aware occurrence intervals, authoritative jurisdiction calendars, metadata recency |
| Trends/anomalies | trend/anomaly plus explicit criteria | Stable comparable windows, zero denominators, coverage and source-history availability; block undefined methods |
| Semantic evidence | semantic query/focus plus structured population filters | Existing Jina/Qdrant family may be adapted; no exact semantic statistics |
| Knowledge | knowledge query | Route to uranus-research-knowledge, never cultural database inference |
| Explainability | explain target/context | New result/context contract with evidence IDs, selected population, filters, exclusions and source lineage |

For `Welches Event hat die meisten Termine?`, resolve the authoritative selected event
population, identify each logical event by UUID/title and count distinct eligible date
identities per event. Do not rank event types or representative date rows. Admin must
provide deterministic ties and result evidence. This document deliberately contains no
SQL and introduces no Admin result model.

Groups with zero matching records require an authoritative universe (e.g. all selected
municipalities), not just inner-linked entities. Missing taxonomy requires a separate
set-difference capability; the current v7 language explicitly blocks it. No conclusion
about absent offers follows from missing source coverage.

## Likely reusable existing families

Existing structured lists/counts, taxonomy discovery/frequency, resolved venue/organization
filters, relative time windows, named places/administrative areas and coordinate extrema
are candidates for a thin adapter. Examples: Jazz concerts today, genres at concerts,
events in Flensburg, events outside Schleswig-Holstein, westernmost event and count of
occurrences in an explicit interval. The report's `supported` list names all 58 candidate
questions. v7 field names differ; zero client migration is assumed here.

Missing fields, EUR prices, per-event occurrence ranks, description length, distinct
connected entities, comparisons, overlap, radii, borders, per-capita ratios and trends
need new or verified deterministic executor capabilities. This is a planning assessment,
not a PostgreSQL/PostGIS integration test result.

## Required structured data

The report's `needs_structured_data` list is the exact per-question backlog. Main groups:

- Authoritative population counts with municipality identity and reference period.
- Audience/accessibility classification for exact counts, exclusions and percentages.
- Publication, cancellation, rescheduling and repeated modification history; current
  status/modified_at cannot prove a sequence of changes.
- Source provenance, multiple-source identity and field-level disagreement/lineage.
- POI/station references and authoritative administrative subdivisions/coverage geometry.
- Media ownership, reuse, age, external source and reachability evidence.
- Co-organizer/collaboration evidence; shared venues alone do not prove cooperation.

Missing coverage must stay visible. The Planner never fetches any of these dependencies.
Live link checking, if added later, requires an independently reviewed bounded executor.

## Explicit language limitations

Single grouping and conjunction-only filters deliberately exclude multidimensional
cross-tabs, arbitrary OR, region set differences, distinct successive days, max-minus-min
price ranges, share of the largest group, image/source entities and arbitrary graph
centrality. Unsupported cases stay in the corpus with preserved questions and reasons.
These need an explicit contract extension, not an Admin approximation or a hidden SQL DSL.

Undefined rural/large-city thresholds, regularity, outlier methods, influence, dominance,
network hubs, cultural gaps and subjective surprise require definitions. The full
`needs_definition` list is in the report. No Shannon diversity or causality is implied.

The `semantic_only` list covers evidence retrieval, including child suitability,
accessibility mentions and thematic similarity. Other analytical questions carry semantic
conditions but are explicitly blocked as insufficient_structured_data. Do not count those
retrieved documents. `knowledge` lists project questions; `needs_context` covers prior
result explanations and unnamed comparisons/referents. A later context contract must
supply stable result handles and auditable evidence, never arbitrary prior model prose.

## Review artifacts and validation

- [Full contract](research-query-plan-v7.md)
- [Corpus counts and every capability-specific question](v7-corpus-report.json)
- [Pre-implementation audit](v7-repository-audit.md)
- Schema fixture: `tests/fixtures/v7_schema.json`
- Catalog/expectations: `tests/fixtures/v7_catalog.json`, `tests/fixtures/v7/`
- Test loader and explicit opt-in live acceptance: `tests/v7_golden.py`,
  `tests/test_research_v7_live.py`

Normal Planner CI verifies algebra/schema/wire boundaries with mocked outputs. It cannot
verify Admin source capabilities or model interpretation quality. Admin's PostgreSQL tests
belong in its later GitHub CI; no local Docker/database execution is authorized here.
