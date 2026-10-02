# v13 controlled acceptance improvement

Status: **draft for review; acceptance targets not achieved**. No complete v13 acceptance claim.
Base: `2710c57c228bac954ad3acb51a9473ced9119bff` (main after PR #19).
Branch: `feat/v7-acceptance-v13`. Separate initial audit commit: `5f32e84`.
Schema version remains research-query-plan-v7; active prompt is research-planner-v13.
All 455 question occurrences, IDs, categories and language variants remain present.

## v12 evidence and golden audit

Verified original operator artifact: `/tmp/v7-live-report-v12.json` locally, originally
`/tmp/v7-live-report.json` on the operator's server. SHA256:
`7961cbb9a3d661e1dede86b73f2a52cd8f5c671f84cd1fda993b26671d2298f7`.
Model gpt-5.6-terra; reference date 2026-10-02; base commit matches the checkout.

| Original v12 outcome | Count |
| --- | ---: |
| Total | 455 |
| Pass | 178 |
| Mismatch | 208 |
| Invalid response | 69 |
| Provider error | 0 |

The [complete audit](v7-live-audit-v12.md) and [JSON evidence](v7-live-audit-v12.json)
classify every mismatch exactly once: 82 MODEL_ERROR, 15 GOLDEN_TOO_STRICT,
82 CANONICALIZATION_GAP, 29 CONTRACT_AMBIGUITY. All 69 invalid responses were reviewed:
68 Pydantic failures and one original_query post-validation failure.

44 case edits have individual before/after rationales (43 initial corrections plus a
separately documented taxonomy-population consistency addendum). Eighteen declare exact
resolver-name variants, not fuzzy matching. Other corrections remove unrequested scalar
ordering/limits, distinguish undefined anomaly concepts from simple rarity rankings,
retain missing comparison measures, choose shared-relation encoding, and mark unsupported
pairwise-distance/long-term-baseline operations honestly. No question was removed.

**Isolated golden effect:** replaying the unchanged valid v12 outputs against the audited
expectations gives **188 pass, 198 mismatch, 69 invalid**. Twelve previously mismatching
cases pass and two previously passing cases fail. This is a net +10 from golden changes,
not a model improvement or a second live run. In particular, correcting an inconsistent
genre-ranking population and unusualness boundary can lower an individual baseline score.

## Prompt changes and bounded contract correction

The prompt now follows 17 ordered construction steps: exact query, routing, blocking
state, intent, subject, metric, grouping, order/limit, structured filters, time, geography,
price, relation, trend/anomaly, semantic evidence, neutrality, silent consistency check.
It is below the existing 14000-character limit and contains fewer than ten exact corpus
questions. The corpus is never loaded by production. No question lookup/routing table.

Canonical conventions include subject-first related orientation, surface taxonomy concepts
resolved by Admin, null free/paid currency, rank versus distribution, singular/plural/open
Wer limits, definition versus criterion/context, neutral explain/knowledge, exact semantic
population boundaries, matching trend operands, and offset-free local clocks.

The **only plan-schema annotation correction** replaces RFC3339 `format: time` on four
v7 local-clock slots with an explicit offset-free HH:MM:SS[.microseconds] pattern. Live
clock probes exposed a conflict between the old schema annotation and the already strict
local-time validator. The audit documents the evidence and standard reference. The full
AST of every function/validator in the three v7 contract modules remains unchanged.
Schema version stays v7; no operation, field, execution capability or accepted timezone is
added. V5/v6 code, fixtures, versions and freeze pins remain unchanged.

Production still performs one model request, no tools, no retries, no repair/fallback.
Provider options, token budget, transport, timeouts and logging policy are unchanged.
Diagnostics remain explicit developer opt-in; credentials stayed in the operator's
existing server environment file and never entered the repo or report.

## Targeted iterations

Each report comes from the PR #19 runner and the same golden loader/comparator. Reports
are private mode-0600 files in `/tmp`; no full provider bodies or headers are published.
The isolated checkout is `/tmp/uranus-v13-acceptance-2710c57`, not the production `/opt`
checkout. No git pull, service restart or deployment was performed there.

| Candidate / selection | Total | Pass | Mismatch | Invalid | Provider error |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1: security, knowledge, regressions | 89 | 31 | 1 | 57 | 0 |
| 2: focused neutrality probes | 8 | 5 | 1 | 2 | 0 |
| 3: focused construction probes | 12 | 8 | 2 | 2 | 0 |
| 4: targeted union (core + remainder) | 239 | 155 | 70 | 14 | 0 |
| 5: fourteen invalids + four controls | 18 | 8 | 9 | 1 | 0 |
| 6: final targeted union | 239 | 152 | 82 | 5 | 0 |

Candidate 1 passed security 4/4 and knowledge 8/8. All 57 invalids were unnecessary
all-neutral TemporalV7 objects. Candidate 2 clarified that absent timing means temporal
null and isolated local-time offsets plus unsupported taxonomy construction. Candidate 3
retained explicit clock constraints but still received offsets despite prompt guidance;
this motivated the audited schema-annotation correction rather than validator relaxation.
Candidate 4 improved the core to 85/89 (security 4/4, knowledge 8/8, regressions
73/77), but retained 14 invalids across the broader union. Candidate 5 probed those
14 construction failures plus four controls. It produced one remaining invalid relation
plan; valid does not mean correct, as nine mismatches remained. Candidate 6 makes required
relation blocking explicit, keeps lookback=past, forbids partial metric operands, and
copies trend operands together. No additional golden changes were made in response to
these results. None of these partial runs is represented as complete acceptance.

Candidate 4 prompt SHA256:
`ae382be5fd5684fd6c763421dd8910276e2f6f50fb33f308018802e0969f6fcc`.
Transferred test bundle SHA256:
`31b4e48334a2d8126e2af17feb032a0ee125e781031852d2d9f6796cdc6c2615`.
The archive has no .git directory, so runner git_commit is null; these hashes identify the
candidate without pretending it was already committed. Reference date remains 2026-10-02.

Both broad targeted candidates use the **239-case union** of categories security, knowledge,
regressions, trends, temporal, taxonomy and capabilities supported, needs_definition.
It is split into 89 core cases and 150 remaining cases, without duplicate calls within
that final selection. Two sequential runners run concurrently, respecting the verified
configured maximum of two requests. Each report preserves golden corpus ordering.

No 455-case v13 live run was started. The final candidate has **152/239 pass (63.6%)**,
82 mismatches and five invalid responses. Security is 4/4, knowledge **6/8**, regressions
72/77 (93.5%, zero invalid), supported 50/58 (86.2%). The knowledge gate fails; the five
remaining construction failures and 82 mismatches also preclude a stability claim.
Earlier knowledge 8/8 and core 85/89 results are not substituted for this final evidence.

### Same-selection comparison

| Same 239 questions | Pass | Mismatch | Invalid | Provider error |
| --- | ---: | ---: | ---: | ---: |
| v12 original goldens | 99 | 103 | 37 | 0 |
| v12 replay, audited goldens | 104 | 98 | 37 | 0 |
| v13 live, audited goldens | 152 | 82 | 5 | 0 |

The +5 in the first comparison is the golden effect on this subset. The subsequent +48
passes and 37-to-5 invalid reduction compare the same questions/expectations, but are
single-run observations, not a statistical stability guarantee. The full 455 v12 score
must not be compared directly with this targeted 239 v13 score.

Final runtime prompt SHA256:
`6199a2c5e044b1f9978c997de1150e7a28d0d8e96616114e38d05f3ff5a6c9ee` (13945 characters).
Source-only line continuations fix line lengths without changing these exact runtime
bytes tested remotely. Candidate 5 probe prompt SHA256 was
`dbec02467316b6023112719bf75ee4947e6478fdbceabdf932a4374ee0abbd15`.

The [machine-readable results](v7-live-v13-results.json) contain all 239 case outcomes
in corpus order, v12 original/audited dispositions, every remaining structured difference,
validation details, category/capability totals, and final private artifact SHA256s.
They exclude full provider bodies, headers and credentials.


### Final category results

| Category | Total | Pass | Mismatch | Invalid |
| --- | ---: | ---: | ---: | ---: |
| anomalies | 8 | 6 | 2 | 0 |
| audiences | 1 | 1 | 0 | 0 |
| combined | 6 | 1 | 4 | 1 |
| comparisons | 9 | 4 | 5 | 0 |
| content | 1 | 0 | 0 | 1 |
| gaps | 2 | 2 | 0 | 0 |
| geography | 20 | 15 | 5 | 0 |
| graph | 6 | 0 | 6 | 0 |
| journalism | 8 | 4 | 3 | 1 |
| knowledge | 8 | 6 | 2 | 0 |
| media | 2 | 0 | 2 | 0 |
| organizations | 6 | 0 | 6 | 0 |
| prices | 2 | 0 | 2 | 0 |
| quality | 7 | 1 | 6 | 0 |
| regressions | 77 | 72 | 5 | 0 |
| security | 4 | 4 | 0 | 0 |
| taxonomy | 24 | 15 | 9 | 0 |
| temporal | 29 | 14 | 14 | 1 |
| trends | 16 | 7 | 8 | 1 |
| venues | 3 | 0 | 3 | 0 |

### Final capability results

| Capability | Total | Pass | Mismatch | Invalid |
| --- | ---: | ---: | ---: | ---: |
| knowledge | 8 | 6 | 2 | 0 |
| needs_clarification | 14 | 11 | 2 | 1 |
| needs_context | 1 | 0 | 1 | 0 |
| needs_definition | 86 | 32 | 50 | 4 |
| needs_structured_data | 5 | 3 | 2 | 0 |
| planned | 58 | 45 | 13 | 0 |
| supported | 58 | 50 | 8 | 0 |
| unsupported | 9 | 5 | 4 | 0 |

### Remaining construction failures

| Case | Existing validator error |
| --- | --- |
| combined-060-008 | Value error, semantic_exact_population_forbidden |
| content-072-005 | Value error, unknown_relation_edge |
| journalism-059-012 | Value error, unknown_relation_edge |
| temporal-065-009 | Value error, metric_filter_requires_metric |
| trends-022-001 | Value error, lookback_requires_unit |

All five are Pydantic validation failures; no provider error or truncation class occurred.
The plan still needs protection against blocked semantic population combinations, illegal
relation edges, orphan metric filters and partially populated lookbacks. The validators
correctly reject these; they have not been relaxed.

### Remaining mismatch concentration

Root counts count individual differences, including forbidden-value violations, not unique
cases. These are derived from paths, not semantic classifications:

| Difference root | Count |
| --- | ---: |
| intent | 38 |
| clarification | 36 |
| metric | 27 |
| anomaly | 25 |
| unsupported_reason | 24 |
| entity_type | 13 |
| ordering | 9 |
| limit | 8 |
| group_by | 7 |
| relation | 5 |
| temporal | 5 |
| spatial | 4 |
| filters | 4 |
| trend | 3 |
| semantic | 2 |
| knowledge | 2 |
| metric_filter | 1 |

Definition-boundary cases remain the largest problem (32/86 pass). Ranking versus anomaly,
missing definitions/criteria, resolver slots, regularity placeholders, relation representation
and unsupported-data boundaries need further review. Two project-repository questions
(`knowledge-047-004`, `knowledge-026-004`) route incorrectly to semantic search. Five strict
regressions remain mismatches: `regressions-091-010`, `regressions-091-011`,
`regressions-091-013`, `regressions-091-023`, `regressions-093-001`.
These are recorded failures, not waived acceptance conditions.

## Remaining disputed golden semantics

The audit retains disputed cases rather than altering them solely to raise a score:
pairwise thematic similarity versus query evidence (content-072-001/002/003), locality
scope versus anomaly (graph-064-007), provision universes (journalism-059-010), venue
anomaly as an event-list predicate (journalism-059-016, venues-054-010), concentration
conventions (organizations-063-001/005), short-description thresholds (quality-068-001),
text-equality groups (quality-068-003), and provenance partial-intent conventions
(provenance-071-003/007/010). These remain explicit audit disputes, not model-correctness
claims or newly enabled execution capabilities.

## Offline validation

Final complete suite: **3406 passed, 710 skipped**. No local live tests were enabled.
`uv sync --locked --group dev`, Ruff check, Ruff format check (68 files), mypy
(29 source files), OpenAPI generation, local documentation links, and `git diff --check`
passed. After committing the intentional version/local-clock annotation update,
`uv run python scripts/export_openapi.py` followed by
`git diff --exit-code docs/openapi.json` also passed with no diff.

The 27 new test instances cover audit completeness and unaudited-edit detection, strict
canonical comparisons, narrowly scoped resolver variants, exact security input with one
request/no tools/no retries, unchanged cross-field validators, and actual NativeOutput
local-time schema. Existing backward-compatibility and production safe-error tests pass.
The temporary snapshot-order failure in an early targeted test invocation was a Literal
union-cache/import-order effect introduced by the new test's early model-client import;
using a local import fixed it without changing enum snapshots or weakening their equality.

Known unresolved contract conventions also include blocked regularity window placeholders
versus a null metric, taxonomy set-difference disposition, and structural versus anaphoric
location context. They were not changed to fit new model outputs.

## Delivery boundary

This is a reviewable audit and v13 candidate, not a merge-ready acceptance success.
The full 455-case v13 run was **not started** because the targeted stability gate failed.
No golden was changed to accommodate the final targeted mismatches. Additional prompt
rules are not assumed to solve unresolved semantic/capability disputes or stochastic
routing errors; those remain explicit review work. A single pass is not a stability proof.

Production requests still fail closed on invalid output. Existing transport/provider
settings and one-request limits remain intact. No deployment, merge, Admin mutation,
SQL execution, database access, Docker, geocoding or retrieval was performed.

## Changed files

- `README.md`
- `docs/openapi.json`
- `docs/research-query-plan-v7.md`
- `docs/v7-admin-handoff.md`
- `docs/v7-corpus-report.json`
- `docs/v7-implementation-report.md`
- `docs/v7-live-audit-v12.json`
- `docs/v7-live-audit-v12.md`
- `docs/v7-live-diagnostics.md`
- `docs/v7-live-v13-report.md`
- `docs/v7-live-v13-results.json`
- `src/research_planner/app.py`
- `src/research_planner/research_v7_constraints.py`
- `src/research_planner/research_v7_prompts.py`
- `src/research_planner/research_v7_schema.py`
- `src/research_planner/research_v7_types.py`
- `tests/fixtures/v7/anomalies.json`
- `tests/fixtures/v7/comparisons.json`
- `tests/fixtures/v7/explain.json`
- `tests/fixtures/v7/gaps.json`
- `tests/fixtures/v7/geography.json`
- `tests/fixtures/v7/graph.json`
- `tests/fixtures/v7/journalism.json`
- `tests/fixtures/v7/organizations.json`
- `tests/fixtures/v7/prices.json`
- `tests/fixtures/v7/quality.json`
- `tests/fixtures/v7/regressions.json`
- `tests/fixtures/v7/relations.json`
- `tests/fixtures/v7/taxonomy.json`
- `tests/fixtures/v7/temporal.json`
- `tests/fixtures/v7/trends.json`
- `tests/fixtures/v7/venues.json`
- `tests/fixtures/v7_schema.json`
- `tests/test_research_v7_client.py`
- `tests/test_research_v7_v13.py`
- `tests/test_v7_live_diagnostics.py`
- `tests/v7_golden.py`
- `tests/v7_live_diagnostics.py`

## Narrow blocker follow-up (starting at a917ad6)

This follow-up retains the preceding audit and all previous live outcomes unchanged.
Starting/current remote PR head was `a917ad6e1aff4ea95b4876c4d3f8df78ad1c5e2e`,
branch `feat/v7-acceptance-v13`, prompt `research-planner-v13`, clean working tree.
The prompt, three schema modules, golden loader, v13 tests, live pytest, and committed
report/results were read before edits. The private candidate-6 reports identified the
five rejected model objects; the committed results identified the seven valid mismatches.

Only local construction/routing passages changed; the 17-step structure remains. The
prompt is 13873 characters (previously 13945). No question lookup, new execution ability,
provider change or retry. **Golden changes: 0. Schema/validator changes: 0.** The corpus,
comparator, JSON Schema/OpenAPI snapshots and v5/v6 remain unchanged from this PR head.

Two details differ from an assumed diagnosis: combined-060-008 is evidence discovery,
not exact statistics; its golden requires search with needs_definition. The temporal
regularity golden retains a blocked occurrence_count/week descriptor; it does not ask
for metric=null. Both witnesses satisfy the existing contract; no golden change is proposed.

| Case | Exact question | Root cause / local rule |
| --- | --- | --- |
| combined-060-008 | Welche Veranstaltungen richten sich an Kinder, finden aber außerhalb der größeren Städte statt? | Evidence discovery was emitted as list+semantic, forbidden even when a separate size definition is missing. Use search with semantic evidence and needs_definition. This question requests no exact statistic; no metric/grouping or insufficient_structured_data should be invented. Exact semantic statistics instead retain intent/metric/grouping and require insufficient_structured_data. |
| content-072-005 | Welche Genres treten häufig gemeinsam mit bestimmten Kategorien auf? | event -> category -> genre contains an illegal category-genre edge. Use the existing legal related genre -> event -> category path, via=[event], with needs_criteria for the unspecified category. |
| journalism-059-012 | Welche Veranstaltungen verbinden Schleswig-Holstein und Dänemark? | The model invented an event-event self edge and put geographical areas into event-name slots. Retain the golden blocked related event -> venue descriptor, via=[], null names, needs_definition. No geographical node or executable interpretation of connects is invented. |
| temporal-065-009 | Welche Veranstalter planen regelmäßig mehrere Veranstaltungen gleichzeitig? | The old prompt demanded a null metric for undefined regularity but still encouraged a numeric metric_filter for several. Retain the existing blocked regularity/occurrence_count/week descriptor and overlap=true, needs_definition. Week is a non-executable placeholder. Construct metric first; a null metric must always imply a null metric_filter. |
| trends-022-001 | Was hat sich beim Veranstaltungsangebot in den letzten Wochen verändert? | The model emitted lookback=null with lookback_unit=week, and dropped weekly grouping. Lookback and unit are atomic. Unquantified last weeks remains needs_date with both slots null; trend.window and group_by are week. |
| knowledge-047-004 | Welches Repo implementiert die semantische Suche? | Project implementation ownership was mistaken for semantic retrieval of cultural records. Project repository/component/service ownership routes to knowledge with exact original query and neutral cultural fields; not a keyword-based general technical Q&A route. |
| knowledge-026-004 | Welches Repo implementiert die semantische Suche? | Separate corpus occurrence of the same project-repository routing failure. Same project-bound routing rule, preserving the separate golden ID and execution. |
| regressions-091-010 | Wo finden viele Veranstaltungen statt? | Simple quantity was incorrectly treated as undefined, dropping the occurrence-count metric. Venue utilization ranks occurrences by venue, desc/20; viele alone requires neither definition nor criteria. |
| regressions-091-011 | Wo ist am meisten los? | The final stored result asked for a definition and dropped the metric; it did not have the earlier limit/date variant. Open Wo venue ranking counts occurrences, desc/20. No requested time means all eligible records, not needs_date. |
| regressions-091-013 | Welche Orte veranstalten besonders viel? | Venue utilization was treated as undefined and its occurrence metric removed. Rank venue utilization by occurrence_count, not distinct event_count, without clarification for besonders viel. |
| regressions-091-023 | Wie viele Jazz-Termine gab es im August 2026? | The model treated the complete Jazz-Termine compound as event_type instead of separating genre and occurrence entity. Termine is the occurrence entity, not a taxonomy type; retain genre Jazz, occurrence_count and the exact August 2026 date interval. |
| regressions-093-001 | Welche Veranstaltungen haben besonders viele Termine? | A simple count ranking of events by dates was treated as undefined and its metric removed. Rank events by occurrence_count, group_by=event, desc/20; besonders viele is quantity, not an undefined anomaly. |

The JSON report's `blocker_followup.audit` preserves expected paths, actual prior plans,
structured differences and each rationale. In particular regressions-091-023 requires
filters[0].field=genre/value=Jazz instead of event_type/Jazz-Termine;
regressions-093-001 requires clarification=none and metric.operation=occurrence_count
instead of needs_definition with metric=null.

Tests extend the existing v13 test module with canonical-witness and negative-validator
checks for all twelve blockers, including exact-semantic blocking, legal adjacent edges,
metric-filter dependency, lookback pairs, neutral knowledge routing, open ranking limits,
occurrence utilization and taxonomy/occurrence compounds. These offline tests validate
contracts and acceptance targets, not an assertion that the model understands the prompt.

The live gate sequence is strict: first these twelve, then repeat only if 12/12; core
only after both pass; 239 only after core passes; 455 only after the specified 239 gates.
Any failing twelve-case run stops expansion. Results are appended below; historical
239/455 statistics above are not represented as results of this follow-up.

### Blocker run #1 — STOP, 10/12

Isolated checkout: `/tmp/uranus-v13-blockers-a917ad6`, built from the exact starting PR
head plus this prompt. The existing runner executed these twelve sequentially with the
unchanged provider settings. Artifact: `/tmp/v13-blockers.json` (private mode 0600),
reference date 2026-10-02, model gpt-5.6-terra. Runtime prompt SHA256:
`2156f60f04854513803272d22f9dda295594095bb3b4972b97266f8fded5ee9a`.
The archive has no .git directory, so artifact git_commit=null; the base and prompt hash
identify the tested code. Full sanitized case evidence and artifact hash are appended in
`blocker_followup.runs`; earlier JSON top-level results remain unchanged historical data.

| Run | Total | Pass | Mismatch | Invalid | Provider error |
| --- | ---: | ---: | ---: | ---: | ---: |
| Blockers #1 | 12 | 10 | 2 | 0 | 0 |

| Case | Result |
| --- | --- |
| combined-060-008 | pass |
| content-072-005 | pass |
| journalism-059-012 | pass |
| knowledge-047-004 | pass |
| knowledge-026-004 | pass |
| regressions-091-010 | pass |
| regressions-091-011 | pass |
| regressions-091-013 | pass |
| regressions-091-023 | pass |
| regressions-093-001 | pass |
| temporal-065-009 | mismatch |
| trends-022-001 | mismatch |

All five formerly invalid cases returned valid ResearchQueryPlanV7 objects in this run.
Three also meet their golden; two remain acceptance blockers:

- **temporal-065-009:** expected regularity/occurrence_count/week plus temporal.overlap=true;
  actual metric=null and temporal=null. The orphan metric_filter is gone, but the intended
  descriptor and overlap are still lost. Golden remains unchanged and authoritative.
- **trends-022-001:** expected group_by=week, actual group_by=none. The atomic lookback
  construction now validates, but weekly grouping is still lost. Golden remains unchanged.

The two selected Knowledge cases and all five selected hard regression cases pass. This
is **2/2 selected Knowledge**, not a new 8/8 category result, and **5/5 selected regressions**,
not a new 77/77 result. Security and the complete supported category were not rerun.

**Stop condition applied:** because run #1 was not 12/12, run #2, Core, 239 and 455 were
not started. No subsequent prompt tuning, retry or golden change was performed to hide
this outcome. No claim of stable acceptance or merge readiness. PR #20 remains Draft.
The other historical mismatches were outside this narrow follow-up and were not retested.

### Follow-up validation and scope

- `uv sync --locked --group dev`: passed.
- `uv run pytest -q`: **3418 passed, 710 skipped**, including 12 added witness/negative tests.
- Ruff check, format check (68 files), and mypy (29 source files): passed.
- OpenAPI export followed by `git diff --exit-code docs/openapi.json`: unchanged.
- Documentation link check and `git diff --check`: passed.
- Changed files: `src/research_planner/research_v7_prompts.py`,
  `tests/test_research_v7_v13.py`, and these two v13 report files only.

No schema, validator, golden, comparator, API, dependency, provider setting, retry/tool/
fallback, Admin, SQL or retrieval change. No production deployment or merge.

## Two remaining blockers: structural preservation follow-up

Starting/current remote head verified: `040606b52eae75c2f7307b4fe133c422274d030b`;
clean branch `feat/v7-acceptance-v13`. Prompt remains research-planner-v13. This follow-up
changes only local regularity/trend/neutralization guidance and focused offline tests.
Golden, schema, validator, comparator, API and provider changes: **zero**.

The previous temporal output kept rank/organization/desc/20 and needs_definition but
lost both its regularity metric and simultaneous temporal constraint. The previous trend
kept its week metric/window and needs_date but lost group_by=week. The revised guidance
retains the blocked regularity descriptor and explicit overlap, limits null metrics to
unknown metrics, and states that weekly grouping survives needs_date. A clarification
represents missing information; it does not make otherwise known fields unused.

Three focused negative tests prove that dropping metric, temporal or weekly grouping
still fails the unchanged golden comparator even if the plan remains schema-valid and
retains its intent/clarification. Existing witness tests assert the required descriptor,
overlap, ordering, limit and week grouping. No exact-question routing was introduced.

### Two-case live gate: failed, STOP

Isolated checkout: `/tmp/uranus-v13-preserve-040606b`; source is the starting PR head plus
this prompt. Existing opt-in runner, sequential requests, unchanged provider settings,
model gpt-5.6-terra, reference date 2026-10-02. No service checkout or deployment change.
The archive has no .git directory, so the artifact's git_commit is null.

Runtime prompt SHA256: `26c56c8cc0a74edc086eb7275701c2bd6d92dbdd86a25eb329df2a8126878318` (13998 characters).
Private artifact: `/tmp/v13-structure-two.json`, SHA256 `942b74abdd064ba7be82d800e0194fbdcf61540b5ad5bbe03a3ceeb336470dbb`.

The JSON report appends complete safe evidence under `structural_followup`; all earlier
run objects and their outcomes remain unchanged.

| Case | Result | Observed structure |
| --- | --- | --- |
| temporal-065-009 | pass | rank; organization grouping; regularity/occurrence_count/week; overlap=true; desc/20; needs_definition; metric_filter=null |
| trends-022-001 | mismatch | group_by=none instead of week; trend.window=month instead of week; needs_date retained |

**Total: 2; pass: 1; mismatch: 1; invalid_response: 0; provider_error: 0.**
The regularity case passed once, not twice. The trend remains a merge blocker and now
also loses the known week window. This worsening is recorded, not hidden or recategorized.

**STOP applied:** neither 12-case run, Core, 239 nor 455 was started. No post-failure
prompt adjustment, retry, golden change or fallback. Full-category security/knowledge/
regression/supported rates are not newly measured. Historical category results are not
substituted for this gate. PR remains Draft; **merge-ready: no**.

### Validation and changed files

Focused v13 tests: 42 passed. Full offline suite: **3421 passed, 710 skipped**.
`uv sync --locked --group dev`, Ruff check, Ruff format (68 files), mypy (29 source files),
OpenAPI export with zero diff, documentation links, and `git diff --check` all passed.
Only these four files change in this follow-up:

- `src/research_planner/research_v7_prompts.py`
- `tests/test_research_v7_v13.py`
- `docs/v7-live-v13-report.md`
- `docs/v7-live-v13-results.json`

No merge, deployment, Admin, SQL, retrieval, geocoder, provider, retry or fallback change.

## Named granularity versus unknown duration (base 6f977dd)

Starting/current remote head: `6f977ddfaca5b9ef7e3d0f7ed186eceac61eea43`, clean
`feat/v7-acceptance-v13`. Prompt remains research-planner-v13. This follow-up changes
only the trend construction passage, one focused witness test, and these two reports.
No golden/schema/validator/comparator/API/provider changes and no new capability.

The prior wording conflated an unknown number of periods with an unknown calendar unit.
The rule now extracts the named analysis unit first. Days/weeks/months/quarters/years
retain their corresponding trend and metric window. A requested supported calendar
grouping remains week/month/year even with needs_date. A month placeholder applies only
when no unit is named at all; an unknown number of weeks never licenses changing weeks
to months or dropping weekly grouping. No guessed lookback is introduced.

Contract boundary: `day` and `quarter` are valid trend windows but are not members of
GroupingV7. This fix does not invent day/quarter groupings or expand the schema. The
requested weekly case is fully representable without any contract change.

The focused test uses the existing trends-022-001 witness and asserts trend/event,
needs_date, group_by=week, event_count/previous_period/week/absolute_change. Negative
assertions reject group_by=none and trend.window=month through the unchanged golden
comparator, while keeping any emitted metric internally consistent. No question-ID or
exact-string handling exists in production.

Live runs use `/tmp/uranus-v13-granularity-6f977dd`, an isolated archive of the starting
head plus this prompt, with the existing opt-in runner and unchanged provider settings.
The archive has no .git directory (artifact git_commit=null). Model: gpt-5.6-terra;
reference date: 2026-10-02. Runtime prompt SHA256:
`adc74e5a57991264d7b7fc0acc1d57e1d09dab0edbbb57553efe4bff66efcc47` (13989 characters).

The JSON report appends evidence under `granularity_followup`; every previous top-level
run, audit and follow-up is retained unchanged. Core selection is the corpus-order union
of security, knowledge, regressions and supported: 121 unique cases, with no duplicate
requests. Required counts are security 4/4, knowledge 8/8, regressions 77/77, supported
at least 50/58, zero invalid and zero provider error. Later 239/455 runs remain conditional.


### Granularity follow-up live outcomes

All stages used exactly the same prompt and provider configuration. No retries, prompt
changes or golden edits occurred between stages.

| Gate | Total | Pass | Mismatch | Invalid | Provider error |
| --- | ---: | ---: | ---: | ---: | ---: |
| Single trend | 1 | 1 | 0 | 0 | 0 |
| Structural pair | 2 | 2 | 0 | 0 | 0 |
| 12 blockers #1 | 12 | 12 | 0 | 0 | 0 |
| 12 blockers #2 | 12 | 12 | 0 | 0 | 0 |
| Core union | 121 | 108 | 11 | 2 | 0 |

The trend case passes four consecutive requested stages; regularity passes the pair and
both 12-case stages. This supports the narrow fix but does not waive later merge gates.

| Core requirement | Observed | Gate |
| --- | ---: | --- |
| Security 4/4 | 4/4 | pass |
| Knowledge 8/8 | 8/8 | pass |
| Regressions 77/77 | 70/77 | **fail** |
| Supported >=50/58 | 51/58 | pass |
| Invalid response =0 | 2 | **fail** |
| Provider error =0 | 0 | pass |

**STOP at Core.** No 239-case or 455-case run was started. PR remains Draft and is
**not merge-ready**. No post-failure tuning, golden changes or hidden reruns.

### Remaining Core failures

The broader gate exposes these seven hard regression mismatches:

- `regressions-090-003`, `regressions-090-004`, `regressions-090-005`,
  `regressions-090-006`, `regressions-093-006`, `regressions-093-008`:
  expected singular limit=1, actual limit=20.
- `regressions-091-004`: expected taxonomy/genre with event_type=Konzert filter;
  actual relation, taxonomy=null and missing filter.

Two invalid responses still fail closed under the existing validators:

- `comparisons-058-007`: `unexpected_anomaly`.
- `organizations-053-002`: `unexpected_relation`.

Other Core mismatches: `combined-060-009` and `comparisons-058-008` introduce
needs_definition and lose event_count; `organizations-053-005` returns relation instead
of list; `venues-054-002` returns relation and loses the event_type filter. These are
observations from this run, not a causal claim that the narrow trend edit introduced them.
None is repaired by changing its golden or loosening validation.

Full private JSON artifacts are retained under `/tmp/v13-granularity-*.json`; each path
and SHA256 is recorded in `granularity_followup.runs`. Core evidence in the repository
keeps all 121 IDs, category/capability statuses, outcomes, differences and validation
errors; the referenced private artifact retains complete plans. Core categories overlap
with the supported capability set, so category/capability gate totals must not be added.

### Final checks for this follow-up

- Focused v13 tests: **43 passed**.
- Complete offline suite: **3422 passed, 710 skipped**.
- Locked dev sync, Ruff, format (68 files), mypy (29 source files): passed.
- OpenAPI export: no diff; documentation links and `git diff --check`: passed.
- Historical JSON report objects were checked for exact equality after excluding only
  the newly appended `granularity_followup` section.
- Changed files: prompt, existing v13 test module, and the two existing v13 report files.
- Prompt stays v13; no golden/schema/validator/comparator/API/provider changes.

No deployment, merge, Admin, SQL, retrieval, geocoder, fallback or new capability.

## Core-error follow-up (base 214f22d)

This narrow follow-up starts at `214f22d17852131a4f8e15eb80912d7ba326e637` on
`feat/v7-acceptance-v13`. The fetched PR head matches. Prompt remains v13.
The baseline is the **latest** `granularity_followup` Core run: 108/121 passed,
11 mismatches, 2 invalid responses, no provider errors. Its private artifact hash
was verified against the committed evidence before selecting any cases.

### Nine-case audit and rule changes

Complete question, expected fields, actual validated plan (or invalid model output),
differences and rationale are appended under `core_error_followup.audit` in the
[JSON results](v7-live-v13-results.json). No historical run is replaced.

| Case | Question | Observed failure | Classification / correction |
| --- | --- | --- | --- |
| comparisons-058-007 | Welche Kategorien sind in Flensburg besonders stark vertreten? | rank with metric=null, needs_definition and outlier anomaly; `unexpected_anomaly` | Quantity ranking retains event_count. Anomaly is null outside anomaly intent. |
| organizations-053-002 | Welche Veranstalter bieten heute Veranstaltungen an? | list/organization/today with organization-event relation; `unexpected_relation` | Date/type/price eligibility does not itself request a graph; list has relation=null. |
| regressions-090-003 | Welcher Veranstaltungstyp hat die meisten Termine? | limit=20 instead of 1; all other expected paths match | singular-limit |
| regressions-090-004 | Welches Genre hat die meisten Termine? | limit=20 instead of 1; all other expected paths match | singular-limit |
| regressions-090-005 | Welcher Ort hat die meisten Termine? | limit=20 instead of 1; all other expected paths match | singular-limit |
| regressions-090-006 | Welche Organisation hat die meisten Termine? | limit=20 instead of 1; all other expected paths match | singular-limit |
| regressions-091-004 | Welche Genres zum Eventtyp Konzert gibt es? | intent=relation instead of taxonomy, taxonomy=null instead of genre, type filter missing | taxonomy-discovery, including inventories restricted by event type |
| regressions-093-006 | Hvilken begivenhed har færrest datoer? | limit=20 instead of 1; all other expected paths match | singular-limit |
| regressions-093-008 | Hvilken begivenhedstype har flest datoer? | limit=20 instead of 1; all other expected paths match | singular-limit |

The seven regressions classify as **6 singular-limit, 1 taxonomy-discovery, 0 other**.
The unconditional venue-utilization `desc/20` instruction conflicted with the singular
rule. Limit now follows the grammatical subject noun, not the plural counted objects;
German feminine singular and Danish singular are explicit. Plural/open Wer/Wo stays 20;
an explicit N takes precedence. Type-restricted genre discovery remains a taxonomy
inventory with a filter, not a graph traversal. No exact-question routing was added.

The new offline witnesses cover these nine failures plus plural/open contrasts, pure
category/type/genre discovery and compare/list anomaly rejection. They verify strict
Golden and validator rejection of counterexamples; they do not simulate language-model
interpretation. There are **19 new tests**, all 62 focused v13 tests pass.
Golden, schema, validators, comparator, API and provider changes: **0**.

### Live gate result — stopped at the first nine cases

| Gate | Total | Pass | Mismatch | Invalid | Provider error |
| --- | ---: | ---: | ---: | ---: | ---: |
| Nine Core cases #1 | 9 | 6 | 0 | 3 | 0 |
| Nine Core cases #2 | — | — | — | — | — |
| Core / 239 / 455 | — | — | — | — | — |

**STOP: first nine-case gate failed. PR stays Draft; not merge-ready.**
No second run, broader run, post-failure prompt tuning, retry or fallback occurred.
This candidate has no new security/knowledge/full-regression/supported-set measurement;
the historical Core figures above must not be presented as its results.

Six cases pass: `organizations-053-002`, `regressions-090-005`,
`regressions-090-006`, `regressions-091-004`, `regressions-093-006`,
`regressions-093-008`.

Three cases now fail strict validation with **unexpected_taxonomy**:

- `comparisons-058-007`: rank/event_count/category, anomaly=null and clarification=none,
  but also taxonomy=category.
- `regressions-090-003`: rank/occurrence_count/event_type and limit=1,
  but also taxonomy=event_type.
- `regressions-090-004`: rank/occurrence_count/genre and limit=1,
  but also taxonomy=genre.

These are invalid outputs, not accepted plans. Their intended quantity/limit fields
no longer show the previous failure, but a ranking must express its taxonomy dimension
only through group_by, with taxonomy=null. The existing validator correctly rejects all
three. The new wording has not established stable separation of taxonomy discovery
from taxonomy grouping; one stochastic run does not identify a unique causal sentence.
No result was repaired after generation or counted as passed because selected fields
looked correct.

The complete safe nine-case report is appended in the JSON results, with private artifact
`/tmp/v13-corefix-nine-first.json` and its SHA256. The isolated server checkout contains
base 214f22d plus the exact recorded prompt; the running service was not modified.

### Validation and remaining limitations

- Focused v13 tests: **62 passed**; full offline suite: **3441 passed, 710 skipped**.
- Ruff, format (68 files), mypy (29 source files): passed.
- OpenAPI export: unchanged; local documentation links and `git diff --check`: passed.
- Historical JSON objects remain exactly unchanged; this follow-up is appended only.
- Four files changed: prompt, focused v13 tests, and these two existing report files.
- Prompt remains v13. Golden/schema/validator/comparator/API/provider changes remain zero.
- Offline witnesses establish contract expectations, not successful live interpretation.
  The merge gates are unmet; no acceptance stability or merge readiness is claimed.

No deployment, merge, Admin, SQL, retrieval, geocoder or new capability.

## Taxonomy-separation follow-up (base 4ff8811)

Starting commit: `4ff8811319f876bd6285b87c6bd6040cc46d2c56`, matching the fetched
`feat/v7-acceptance-v13` PR head. This follow-up only addresses the three
`unexpected_taxonomy` outputs from the preceding nine-case run:

| Case | Question | Invalid extra field on rank |
| --- | --- | --- |
| comparisons-058-007 | Welche Kategorien sind in Flensburg besonders stark vertreten? | taxonomy=category |
| regressions-090-003 | Welcher Veranstaltungstyp hat die meisten Termine? | taxonomy=event_type |
| regressions-090-004 | Welches Genre hat die meisten Termine? | taxonomy=genre |

The existing validator already enforces the correct distinction. A taxonomy-dimensional
ranking has entity=event and its dimension in group_by; taxonomy must be null.
An inventory uses intent=taxonomy, a nonnull taxonomy dimension, group_by=none and
null metric/ordering/limit. A type-filtered genre inventory remains discovery with a
name filter. Prompt guidance and the existing final self-check now state both branches
explicitly; duplicated subject guidance was shortened to preserve the existing length
limit. Prompt stays **research-planner-v13** (13,997 characters).

Five added contract-witness tests cover valid category/type/genre rankings and reject
an extra taxonomy field for each; both plain and type-filtered genre inventories validate
and reject a missing taxonomy with `taxonomy_required`. No prompt-substring-only test
was substituted for these checks. Golden/schema/validator/comparator/API/provider
changes: **zero**. Existing historical report objects are preserved.

### Live result — STOP at the first three-case gate

| Gate | Total | Pass | Mismatch | Invalid | Provider error |
| --- | ---: | ---: | ---: | ---: | ---: |
| Three taxonomy cases #1 | 3 | 2 | 1 | 0 | 0 |
| Three taxonomy cases #2 | — | — | — | — | — |
| Previous nine / Core / 239 / 455 | — | — | — | — | — |

All three outputs now have intent=rank and taxonomy=null. The category and event-type
cases pass their complete Golden expectations. `regressions-090-004` is valid but
mismatches **entity_type**: expected `event`, actual `occurrence`. Its genre grouping,
occurrence_count metric, taxonomy=null and singular limit=1 match. Counting dates does
not change a taxonomy ranking's subject entity to occurrence; the unchanged Golden
expectation remains authoritative.

**The gate failed, so execution stopped. PR remains Draft and not merge-ready.**
No second three-case, nine-case, Core, 239 or 455 run was started. No post-failure tuning,
retry, fallback or repair was performed. Zero invalids in this small run does not establish
stability or satisfy the Core merge gates. There are no fresh broader-gate scores for this
candidate. The two historical blocker passes and previous Core scores remain historical.

The complete safe report is appended under `taxonomy_separation_followup.runs` in the
[JSON results](v7-live-v13-results.json), with artifact path
`/tmp/v13-taxonomy-three-first.json`, SHA256, exact prompt hash and base commit. The isolated
checkout used this exact candidate without changes to the running service.

### Final validation

- Full offline suite: **3446 passed, 710 skipped**; focused v13 tests: **67 passed**.
- Ruff, format (68 files), mypy (29 source files): passed.
- OpenAPI export: unchanged; documentation links and `git diff --check`: passed.
- An intermediate prompt exceeded the existing length limit and failed two tests.
  Redundant taxonomy guidance was shortened; the final full suite passed. No test limit
  or assertion was weakened.
- Historical JSON sections are unchanged; only this follow-up was appended.
- Changed files: prompt, existing v13 test module, and the two existing reports.
- No Golden, schema, validator, comparator, API or provider change. No new capability.

No deployment or merge. Remaining blocker: genre-ranking subject entity; broader
acceptance remains unmeasured on this candidate because the first gate failed.

## Deterministic canonicalization follow-up (base 9f055c9)

The scope now explicitly permits autonomous iteration and safe deterministic normal forms.
The new internal NativeOutput adapter validates every proposal field with the existing
strict field types and nested validators, normalizes only explicit intent-dependent
invariants, then applies all unchanged `ResearchQueryPlanV7` cross-field validators.
`plan_v7` still revalidates the final public plan with exact original-query equality.
No retry, fallback, tool, second model call or question-dependent routing is added.

Rules: non-taxonomy intents clear taxonomy; taxonomy discovery clears grouping, metric
and its dependent metric_filter; category/event_type/genre rankings use entity=event;
non-anomaly and non-trend intents clear their respective unused objects; intents that
cannot carry relations clear relation. Unknown enums, missing fields, extra properties
and invalid nested constraints are rejected **before** neutralization. No intent, metric,
name, clarification or unsupported reason is invented. Existing unsupported states remain.

The proposal model derives its typed fields from the public model to avoid a second
vocabulary. Tests prove exact NativeOutput schema equality, all 455 Golden witnesses
unchanged/idempotent, strict rejection boundaries, and single-request integration.
The live diagnostic replay uses the same adapter to report the actual remaining error,
rather than reporting a pre-normalization error already resolved by the real client.
Public API/OpenAPI/schema versions and strict plan validators are unchanged.

### Candidate c1: unchanged prompt plus deterministic adapter

Offline: **3920 passed, 710 skipped**; focused adapter/client suite **947 passed**.
Ruff, format, mypy, unchanged OpenAPI export, links and diff checks pass.

| Stage | Total | Pass | Mismatch | Invalid | Provider error |
| --- | ---: | ---: | ---: | ---: | ---: |
| Direct genre rank | 1 | 1 | 0 | 0 | 0 |
| Previous nine Core fixes | 9 | 9 | 0 | 0 | 0 |
| Core union | 121 | 119 | 2 | 0 | 0 |

Core gates all pass: security 4/4, knowledge 8/8, regressions 77/77, supported 56/58
(required >=51/58), invalid=0, provider=0. The two remaining supported mismatches are
`comparisons-058-008` (quantity ranking interpreted as undefined anomaly) and
`geography-013-001` (unnecessary needs_location for nondeictic where-events discovery).
They do not justify altering Golden or inventing semantics in the canonicalizer.
The unchanged candidate proceeds to the historical 239-case union.

### c1 Target: remaining clusters and independent c2 work

The 239-case run returned **167 pass, 71 mismatch, 1 invalid, 0 provider errors**.
Security remains 4/4, knowledge 8/8, supported 57/58; regressions are 76/77.
The full 455 run is not authorized by these gate results yet.

The only invalid (`media-070-004`) selected semantic search for an unsupported image
subject with entity=null but no unsupported reason. The hard regression
(`regressions-091-026`) dropped an explicit morning constraint. These are normal
interpretation errors: c2 clarifies daypart-without-date preservation and unsupported
record subjects/age. No missing semantic information is guessed by the canonicalizer.
Redundant prompt instructions for already deterministic normal forms were removed;
there is no question/ID lookup. Prompt remains v13 and below the existing length bound.

Broader differences cluster around undefined evaluative concepts versus quantity ranking,
comparison subject/group preservation, temporal descriptors under clarification, and
unsupported composition boundaries. Difference-path totals overlap: intent 38,
clarification 33, anomaly 25, unsupported_reason 20, metric 18, grouping 14. These are
not 71 unrelated special cases and will not become per-question production rules.

### Actual fachliche decision: distribution defaults

`temporal-050-009`, “Wie verändert sich das Veranstaltungsangebot über die Woche?”,
has Golden intent=aggregate/group_by=weekday **ordering=desc, limit=20**.
The documented v13 rule in [the contract guide](research-query-plan-v7.md#v13-canonical-interpretation-unchanged-algebra-and-validators)
says distributions and scalar statistics are aggregate **without implicit ordering/limit**;
the production prompt likewise says null unless requested. The question does not request
a ranking or a result limit. Both forms are schema-valid, but the two acceptance rules
conflict. Canonicalization cannot make both authoritative at once.

A decision was requested: retain the documented null/null default and audit-correct
Golden, or explicitly define a distribution ordering/limit default and retain Golden.
**No automatic Golden change and no guessed exception.** The independent daypart/media
fixes proceed while this decision remains open. This is distinct from normal model errors.

### Decision resolved; c3 normal forms

The user chose to retain Golden and explicitly define the distribution defaults.
Temporal frequency profiles grouped by hour/weekday/week/month/year with a count metric
therefore default to ordering=desc, limit=20. Explicit order/limit values win. Ordinary
category tables, unresolved grouping and scalar aggregates keep their existing null
defaults. This defines presentation, not a new intent or a new metric. The guide and prompt
now agree. All Golden cases remain unchanged; no metric or intent is synthesized.

The c2 direct run was **1/2 pass, 0 mismatches, 1 invalid, 0 provider errors**: morning
preservation passed; unsupported image-age rank now retained its known descriptor but
emitted group_by=event with entity=null (`rank_entity_group_mismatch`). c3 neutralizes
such an incompatible entity group only for an explicitly unsupported null-entity rank.
It never changes the unsupported subject into an event or removes the unsupported reason.
Strict public validation continues to reject the unnormalized proposal.

Tests cover all temporal-profile witnesses, preservation of explicit asc/5 choices,
non-interference with category/scalar/unresolved aggregates and the unsupported-subject
normal form. The independent c2 offline phase had 3922 passed, 710 skipped. No hidden
live retries or discarded runs occurred.

c3 passes its three direct cases (image age, morning-only, intra-week distribution)
**3/3**, then the historical Core-fix set **9/9**, with no invalid/provider errors.
The full offline suite is **3930 passed, 710 skipped**; the focused canonical/v13 suite
is **551 passed**. Core is rerun on this exact candidate before another Target run.
The user decision is resolved; there is no pending fachliche decision at this point.

### c3 Core and c4 corrections

c3 Core returned **115/121 pass, 5 mismatches, 1 invalid, 0 provider errors**:
security 4/4, knowledge 8/8, regressions 73/77, supported 55/58. CI for `a441682`
passed. The gate failures are retained in the machine-readable report; no Target/455
run followed this failed Core result.

The invalid taxonomy inventory had entity=null. Inventory intent already fixes the
population as event, so c4 adds that deterministic normal form. Prompt corrections
address normal interpretation errors: an unknown event attribute retains the event
population, unlike an unsupported subject; new-record discovery remains list rather
than age ranking; taxonomy frequency defaults to event_count unless dates are explicit;
taxonomy eligibility of organizers/venues is not a named graph counterpart. These are
general distinctions, not question or ID routing. New witness tests protect all six
observed cases and the public validator remains unchanged.

c4 offline: **3936 passed, 710 skipped**; focused **557 passed**. Its direct set returned
**7/9 pass, 2 mismatches, 0 invalid/provider errors**. The remaining two ordinary model
errors were an unsupported attribute-value inventory interpreted as semantic event
search (`regressions-091-024`) and loss of the blocked record-age metric (`media-070-004`).
All six previously observed Core cases except the attribute inventory passed. c5 tightens
only the general distinction between requested attribute values and requested event
evidence, and preservation of a known age descriptor even for unsupported subjects.
Golden and strict schema remain untouched. Every intermediate result stays recorded.

### c5/c6 narrowing and c7 offline candidate

c5's direct set returned **1/2 pass, 0 mismatches, 1 invalid, 0 provider errors**.
Attribute inventory passed; the unsupported record-age question combined list with an age
metric (`unexpected_metric`). c6 moved the existing age-ranking rule into primary intent
selection. Its direct set returned **1/2 pass, 1 mismatch, 0 invalid/provider errors**:
the age plan retained the correct rank, metric, ordering, unsupported subject and limit,
but cleared the independently required `needs_definition`. The other case passed.

c7 clarifies that an unsupported subject/operator does not remove an independently
undefined field-value cutoff. This affects blocking-state interpretation only; the
canonicalizer does not infer a clarification from an unsupported reason. A negative
witness assertion protects the omitted clarification. No Golden, comparator, public
schema or validator changes were made.

c7 offline validation: **3936 passed, 710 skipped**; Ruff, format, Mypy, OpenAPI no-diff,
documentation links and diff check pass. Live validation has **not started**: SSH to the
authorized server returns `No route to host`; GitHub API access fails with the same
network error. This is an infrastructure block, not a live provider result, and is not
counted as a case or a provider error. c7 has no acceptance claim. PR remains Draft and
not merge-ready. The next steps remain direct cases, nine-case set, Core, Target239,
then full455 only after the preceding gates pass. No full455 was run.

The network interruption resolved before stopping work. Commit `779de44` was pushed;
c7's direct cases pass **2/2**, with zero mismatch/invalid/provider errors. The nine-case
gate follows on the same isolated source snapshot. The unavailable-network observation
above is retained as history, not the current status.

c7 Core returned **116/121 pass, 4 mismatches, 0 invalid, 1 provider error**:
security 4/4, knowledge 8/8, regressions 74/77, supported 56/58. Three regression
variations of undefined new-record discovery lost `needs_definition`; organizer eligibility
by event type was incorrectly interpreted as a graph request. The separate taxonomy case
returned safe error `planner_unavailable`, with no output to reinterpret. No Target/455
run followed this failed Core. CI for `779de44` passed.

c8 clarifies undefined new-record discovery and distinguishes filtered record lists from
requested graph links. No intent/clarification repair was added: these require language
interpretation, not field-invariant canonicalization. The three new-record witnesses now
also negatively assert that clearing the clarification fails Golden acceptance.

c8 direct: **5/6 pass, 1 mismatch, 0 invalid/provider errors**. Undefined new-record
discovery now passes all three variations, as do the unsupported age case and type-filtered
taxonomy discovery. Organizer-by-type eligibility still emits a relation and omits the
type predicate. c9 replaces the generic eligibility wording with a short illustrative
theatre-organizer list/filter example. This is prompt guidance for the general operation,
not an exact-question lookup or a guessed canonicalizer filter.

c9 direct: **5/6 pass, 1 mismatch, 0 invalid/provider errors**. Organizer eligibility and
all three new-record variants pass. The age question regressed to list with no metric/order/limit.
c10 restores the explicit rank-not-list wording for age selection, including unsupported
subjects and undefined cutoffs; it does not weaken its Golden expectation. c9 offline:
**3938 passed, 710 skipped**, all quality/schema/documentation gates passed.

c10 offline: **3938 passed, 710 skipped**, focused **559 passed**. Ruff, format, Mypy,
OpenAPI no-diff, documentation links and diff check pass. No c10 live calls have been
made. Following the user's cost concern, further provider calls await an explicit cost
limit. Even a first-pass success through direct6/nine9/Core121/Target239/full455 would
require 830 more calls; further iteration would add cost. The latest completed direct
run is still c9 (5/6); latest completed Core is c7 (116/121, zero invalid, one provider
error). Neither historical success nor local witness validation proves c10 live acceptance.
PR remains Draft; no merge-ready or full455 stability claim is made.

The user explicitly chose to continue the complete gates despite the estimated remaining
830-call minimum. c10 direct validation starts; the cost-pause note above is historical.

c10 direct passes **6/6**, then the historical Core-fix set **9/9**, both with zero
mismatch/invalid/provider errors. The tested code is committed as `9fcd497`; Core runs
on the same unchanged source snapshot.

c10 Core: **118/121 pass, 3 mismatches, 0 invalid/provider errors**. Security 4/4,
knowledge 8/8, supported 55/58 satisfy their gates; regressions are 76/77. The only hard
regression is Danish location discovery incorrectly requesting user location. The two
non-regression mismatches are an unnecessary quantity-definition clarification and
ordering/limit on an ordinary category distribution. They are retained as failures; no
Golden or comparator correction is made. CI for `9fcd497` passed.

c11 clarifies that a where/wo/hvor question asking where events occur is not itself a
request for user location. The direct set covers DE/EN/DA plus a real near-me contrast.
Offline: **3939 passed, 710 skipped**; focused **560 passed**. No strict schema changes.

c11 direct returned **1/6 pass, 5 mismatches, 0 invalid/provider errors**. The near-me
contrast passes; all five ordinary where-discovery variants wrongly switch entity to
venue. The wording "asks for locations" removed the earlier explicit event-record
subject. c12 restores `list/event records with locations` while retaining the no-location-
clarification distinction. This is a correction to the prompt, not a Golden reinterpretation.

c12 direct passes **6/6** across DE/EN/DA and the near-me contrast. Its nine-case gate
returns **8/9 pass, 1 mismatch, 0 invalid/provider errors**: the category quantity rank
adds an unnecessary `needs_definition`. The existing quantity-before-anomaly rule was
located after the blocking-state decision. c13 moves that unchanged rule to the start
of blocking-state construction; no added case-specific exception or inferred clarification.

c13 direct passes **1/1**, then **9/9** in the historical Core-fix set, with zero
mismatch/invalid/provider errors. Core follows on the same sources. Offline:
**3939 passed, 710 skipped**; all quality, schema and documentation checks pass.

c13 Core is **121/121 pass, 0 mismatch, 0 invalid, 0 provider errors**: security 4/4,
knowledge 8/8, regressions 77/77, supported 58/58. CI for `40fb85d` passed. The historical
239-case Target selection ran on precisely the same isolated sources.

c13 Target: **168/239 pass, 64 mismatches, 7 invalid, 0 provider errors**. Security
4/4, knowledge 8/8, supported 58/58; regressions 76/77 (new-venue discovery became rank).
No full455 run follows these failed gates. New invalid clusters are unbound diversity,
time-frequency without a window on co-occurrence, distance encoded as a missing radius,
incompatible rank entity/group, ordering on relation and a change metric on anomaly.

c14 adds small deterministic normal forms only where the contract fixes the result:
forbidden ordering is null; non-trend change metrics are null; an explicitly undefined
rank-diversity descriptor with all operands null and no metric_filter becomes metric=null.
For the last case an internal closed metric proposal defers operand validation just for
that exact neutral form. All other metrics still pass unchanged strict operand validation
before any normalization. NativeOutput/public JSON schemas are identical; all455 reviewed
witnesses remain unchanged and idempotent. Negative tests cover nonblocked/other missing
operands and unknown enums/fields.

Prompt changes distinguish bare new-record discovery from age ordering, co-occurrence
from time-frequency, distance extrema from radius membership and entity grouping from
a regional filter. Unsupported multi-dimension distributions preserve their outer group;
undefined density and long-term historical anomalies remain blocked. Golden stays unchanged.

c14 direct: **5/8 pass, 3 mismatches, 0 invalid/provider errors**. All seven formerly
invalid outputs now validate and the new-venue regression passes. Remaining exact
differences: generic reference `größeres Zentrum` versus `Zentrum`; missing desc/20 on
a frequency-qualified blocked multi-distribution; same-genre co-occurrence incorrectly
using the previously illustrative genre-category edge with needs_criteria.

c15 generalizes taxonomy co-occurrence by same versus different requested dimensions;
no unmentioned dimension or selection parameter is invented. Generic undefined size
qualifiers are represented by the blocking state while the base reference concept stays
in place_query; actual proper names remain verbatim. Frequency-qualified multi-distributions
retain requested descending presentation/limit20 while blocked. No Golden modification.

c15 direct: **4/8 pass, 4 mismatches, 0 invalid/provider errors**. All formerly invalid
constructions remain valid; the new-record regression and co-occurrence cases pass.
Remaining differences: unresolved area-name genitive, missing generic spatial reference,
undefined density planned as rank/missing data, and multi-grouping selection incorrectly
classified as an undefined concept. Offline **3942 passed, 710 skipped**; all quality,
OpenAPI and documentation gates pass.

A fachliche decision is requested before changing Geo-name acceptance: `combined-060-001`
uses `spatial.area_query="Schleswig-Holsteins"`, while Golden requires `Schleswig-Holstein`.
The public contract has unresolved name queries but no explicit geographic inflection
normalization policy. Existing reviewed resolver variants are deliberately scoped to
taxonomy filter values, not Geo slots. Options: document grammatical-base-form extraction
in Planner and retain Golden, or audit a narrowly scoped Geo resolver-name equivalence.
No Golden/comparator change has been made. Other differences remain ordinary model errors.
The next candidate's independent density/selection wording is only a local temporary draft;
no further live run or 455 gate has started pending this policy decision.

### Geo-name decision resolved; c16

The user chose resolver-side inflection normalization. One audited Golden declaration
now accepts Schleswig-Holsteins alongside Schleswig-Holstein at combined-060-001's
area_query only. The canonical expectation stays unchanged; all other paths remain strict.
This is one additional Golden correction, separate from the original 44-case audit.
The test comparator recognizes only explicitly declared Geo-name slots with unchanged
relation/reference. Actual outputs are never rewritten and forbidden values still fail.

c16 also distinguishes undefined density from raw quantity ranking, multi-grouping
selection from concept definition, and preserves a known generic spatial reference while
blocked. These are prompt changes; strict public schema and validators are unchanged.
Historical live results have not been recomputed or overwritten under the new expectation.

Offline c16: **3953 passed, 710 skipped**; Ruff, format, Mypy, OpenAPI, links and whitespace checks pass.
c16 direct: **5/8 pass, 1 mismatch, 2 invalid, 0 provider errors**. Reviewed Geo inflection
and density pass; remaining constructions are shared across unlike taxonomy nodes, a missing
blocked distance reference, and omitted ordering/limit on a frequency-qualified distribution.
c17 tightens these three existing prompt rules, without schema or further Golden changes.

c17 direct: **6/8 pass, 2 mismatches, 0 invalid/provider errors**. Remaining: generic
reference retains undefined size adjective; same-taxonomy co-occurrence chooses related.
c18 adds a deterministic operation normal form only for unanchored taxonomy endpoints
joined via exactly one event: same endpoints shared, different endpoints related. It never
changes endpoints, queries, path, intent or metric. Other relation shapes still pass the
unchanged RelationV7 validator; all455 witnesses and both NativeOutput schemas are unchanged.
The prompt drops undefined size adjectives from a generic reference while retaining its block.
Focused validation: **596 passed**; Ruff and Mypy pass.

c18 direct: **6/8 pass, 1 mismatch, 1 invalid, 0 provider errors**. The taxonomy relation
now has legal operation/path but lacks entity_type; historical outlier invents event_count
as its undefined anomaly measure. c19 derives event population from the already declared
taxonomy-event-taxonomy path, except explicitly unsupported subjects, and clarifies the
existing null anomaly measure rule. Focused validation: **600 passed**, Ruff/Mypy pass.

c19 direct: **7/8 pass, 1 mismatch, 0 invalid/provider errors**. Only frequent same-genre
co-occurrence incorrectly requests a definition. c20 clarifies that structural co-occurrence
does not require a statistical definition merely because frequency is mentioned. A negative
Golden witness continues to reject this extra clarification; no acceptance relaxation.

c20 direct: **8/8 pass, 0 mismatch, 0 invalid, 0 provider errors**. The same unchanged
isolated source snapshot proceeds to the historical nine-case gate and then Core if green.
No broad acceptance claim is made from this subset.

c20 nine: **9/9 pass, 0 mismatch/invalid/provider errors**. Core121 is running on the
same snapshot. Offline c20: **3980 passed, 710 skipped**; Ruff, format, Mypy, public
OpenAPI no-diff, documentation links and whitespace checks pass. PR remains Draft.

c20 Core: **118/121 pass, 3 mismatches, 0 invalid/provider errors**. Security4/4,
knowledge8/8, regressions75/77, supported57/58. Two venue-activity questions choose distinct
event count rather than occurrence count; singular category ranking chooses limit20.
CI for 4fab402 passed. c21 clarifies the venue-activity/count distinction and includes
category among singular subjects. No deterministic metric/limit guessing or Golden change.

c21 direct: **3/3 pass**; nine: **9/9 pass**, both zero mismatch/invalid/provider errors.
Offline: **3983 passed, 710 skipped**; Ruff, format, Mypy, OpenAPI no-diff, doc links
and whitespace checks pass. Full Core121 is running on these unchanged sources.

c21 Core: **121/121 pass**, security4/4, knowledge8/8, regressions77/77, supported58/58;
zero mismatch/invalid/provider errors. CI for f932d2d passed. The full historical239 Target
selection is now running on the same snapshot; no full455 has started yet.

c21 Target239: **179 pass, 52 mismatches, 8 invalid, 0 provider errors**. All Core
groups remain perfect: security4/4, knowledge8/8, regressions77/77, supported58/58.
Invalid clusters: taxonomy anomaly missing event subject; undefined spatial dispersion as
reference-free distance rank; synthetic geographic graph edge; local/overregional semantics
as exact semantic lists; unsupported media age with list+metric; undefined completeness
as incomplete frequency metric; direct event count with redundant nested measure.
c22 makes these existing interpretation boundaries explicit. Direct-count proposals now
neutralize only measure/window (forbidden for direct counts), retaining operation and other
operands before strict metric validation. No guessed intent/metric or Golden change.
Full455 remains gated by the failed Target invalid count.

c22 direct: **4/8 pass, 2 mismatches, 2 invalid, 0 provider errors**. Geo connectivity,
local/overregional routing and publication-history boundary now pass. Undefined dispersion
and completeness still become incomplete rank metrics; unusual rarity chooses generic outlier,
and unsupported media age loses its independent definition block. Offline **3996 passed,
710 skipped**, all quality/OpenAPI/doc gates pass. c23 clarifies these existing precedence
rules; focused witnesses **617 passed**. No new normalizer or Golden change in c23.

c23 direct: **4/8 pass, 2 mismatches, 2 invalid, 0 provider errors**. The same four
boundaries remain unstable: rare taxonomy disjunction is treated as an unsupported
multigroup query; undefined dispersion/completeness invent distance/frequency; unsupported
media age drops needs_definition. c24 clarifies property-before-quantity precedence and
keeps an undefined anomaly dimension unselected. Existing focused witnesses: **617 passed**.

c24 direct: **7/8 pass, 1 mismatch, 0 invalid/provider errors**. The only residual
difference is unsupported_constraint on the undefined rarity question with alternative
taxonomy dimensions. c25 clarifies that an unselected anomaly dimension remains neutral
with needs_definition; it is not yet an unsupported executable multi-group request.

c25 direct: **6/8 pass, 1 mismatch, 1 invalid, 0 provider errors**. Rarity now passes;
dispersion again becomes a reference-free distance rank, and inactive publication history
uses needs_date instead of its undefined duration threshold. c26 makes these existing
distinctions explicit, including the final silent consistency check. Focused: **618 passed**.

c26 direct: **4/8 pass, 2 mismatches, 2 invalid, 0 provider errors**. The instability
remains in rarity/multigroup precedence, spatial dispersion, completeness and inactivity
thresholds. Offline c25/c26: **3997 passed, 710 skipped**; all quality/OpenAPI/docs gates pass.
c27 makes undefined-property precedence explicit over later quantity and multigroup rules,
and narrows the field-cutoff exception to actual text-length/price/record-age fields.
No new question examples, Golden changes or validator changes. Focused: **618 passed**.

c27 direct: **6/8 pass, 0 mismatches, 2 invalid, 0 provider errors**. Undefined quality
is now correctly anomaly, but a partial frequency metric remains attached; unsupported
media rank loses metric/order/limit. Offline **3997 passed, 710 skipped**, all gates pass.
c28 clarifies unused metric neutralization for undefined outliers and preserves known
rank structure despite unsupported subject. No deterministic inference of absent semantics.
Focused witnesses: **618 passed**.

c28 direct: **6/8 pass, 2 mismatches, 0 invalid/provider errors**. The remaining
outputs omit overregional metric_filter>1 and request needs_date for undefined inactivity.
c29 binds those existing rules to their explicit output slots, without inferred-code repair.
Focused witnesses: **618 passed**.

c29 direct: **8/8 pass, 0 mismatch/invalid/provider errors**. Historical nine then
**8/9 pass, 1 mismatch, 0 invalid/provider errors**: category strength becomes an undefined
anomaly. c30 restores explicit raw-frequency vocabulary so the undefined-property precedence
does not capture ordinary counts. Direct verification includes the previous eight plus this
Core failure; no broad gate starts until they pass together.

c30 direct (eight Target boundaries plus the regressed category count): **9/9 pass**.
Historical nine: **9/9 pass**. Both have zero mismatches/invalid/provider errors.
The same isolated source snapshot now runs Core121.

Offline c30: **3997 passed, 710 skipped**; Ruff, format, Mypy, OpenAPI no-diff, docs
links and whitespace gates pass. All historical run entries remain unchanged.

c30 Core: **117/121 pass, 1 mismatch, 3 invalid, 0 provider errors**. Security4/4,
knowledge8/8, regressions73/77, supported57/58. Three exact accessibility counts incorrectly
route to search while retaining count metrics; geographic existence routes to list.
c31 restores explicit quantitative-intent precedence over semantic evidence and existence
count routing. Four strict regression witnesses added; focused **622 passed**.
Direct selection now covers these four plus the prior eight Target boundaries and the
category-count regression (13 cases), to test the rule groups together.

c31 direct: **12/13 pass, 1 mismatch, 0 invalid/provider errors**. All quantitative
accessibility/existence regressions now pass; category strength still becomes anomaly.
Offline **4001 passed, 710 skipped**, all gates pass. c32 explicitly distinguishes
emphatic ordinary quantity (besonders) from an anomaly request, preserving the undefined
quality/dispersion precedence. Focused: **622 passed**.

c32 direct: **13/13 pass, 0 mismatch/invalid/provider errors**. The unchanged snapshot
proceeds to the historical nine-case gate before Core.

c32 historical nine: **9/9 pass**, zero mismatch/invalid/provider errors. Core121 is
running on the same sources. Offline c32: **4001 passed, 710 skipped**; Ruff, format,
Mypy, OpenAPI no-diff, docs links and whitespace checks pass.

c32 Core: **119/121 pass, 2 mismatches, 0 invalid/provider errors**. Security4/4,
knowledge8/8, regressions76/77, supported57/58. Geo genitive appears in geography-015-003;
under the user-approved resolver policy this second case receives its own audited exact
name pair (all other expectations unchanged). Instrument inventory routes to search.
c33 moves the existing non-taxonomy inventory boundary directly before semantic routing.
Focused audit/contract/corpus validation: **1397 passed**. The direct set adds both cases
to the previous13; all historical scores retain their original acceptance semantics.

c33 direct: **14/15 pass, 1 mismatch, 0 invalid/provider errors**. Only non-taxonomy
instrument inventory still routes to evidence search. The second audited Geo inflection
passes. Offline **4003 passed, 710 skipped**, all gates pass. c34 adds a short illustrative
attribute noun to the existing inventory boundary; no question string/ID routing.
Focused: **624 passed**.

c34 direct: **15/15 pass, 0 mismatch/invalid/provider errors**. The unchanged snapshot
proceeds through historical nine, then Core if green.

c34 historical nine: **9/9 pass**, zero mismatch/invalid/provider errors. Core121 is
running. Offline **4003 passed, 710 skipped**; Ruff, format, Mypy, OpenAPI no-diff,
docs links and whitespace gates pass. The original44 audited corrections plus two
individually audited Geo inflection declarations are the full Golden-change scope.

c34 Core: **120/121 pass, 1 mismatch, 0 invalid/provider errors**. Security4/4,
knowledge8/8, regressions76/77, supported57/58. The sole failure treats a public market
square as a venue filter instead of named spatial reference. CI for 8cb5331 passed.
c35 clarifies public streets/squares/marketplaces versus businesses; a negative witness
rejects resolver-slot substitution. Focused **625 passed**. Direct selection adds this
case to the preceding15; no name-based production routing.

c35 direct: **16/16 pass, 0 mismatch/invalid/provider errors**. Historical nine runs
next on the same snapshot.

c35 nine: **9/9 pass**, zero mismatch/invalid/provider errors. Core121 runs on the
same snapshot. Offline: **4004 passed, 710 skipped**; Ruff, format, Mypy, OpenAPI
no-diff, docs links and whitespace gates pass.

c35 Core: **120/121 pass, 0 mismatch, 0 invalid, 1 provider error**. The one error is
planner_unavailable on regressions-092-005. Security4/4, knowledge8/8, regressions76/77
(one provider error), supported57/58. This does not meet the zero-provider gate. A separate
one-case availability check and then a fresh full Core run use the same unchanged candidate;
no model retry/fallback/configuration changes are introduced. CI for 4b43b3f passed.
Inactive c1–c34 virtual environments were removed to reclaim temporary RAM; source snapshots,
lockfiles and every report remain available, and the active c35 checkout is unchanged.

c35 availability check: **1/1 pass**. Fresh complete Core: **121/121 pass**,
security4/4, knowledge8/8, regressions77/77, supported58/58, zero mismatch/invalid/provider.
This is a new full run, not a replacement or patch-up of the earlier provider-failed result.
Target239 now runs on identical sources, with the same one-request provider settings.

c35 Target239: **188 pass, 46 mismatches, 5 invalid, 0 provider errors**. Core groups
remain perfect: security4/4, knowledge8/8, regressions77/77, supported58/58. Invalids concern
a metric-free unblocked comparison, unqualified record population, plain rarity as anomaly,
extra frequency on co-occurrence, and malformed clock-frequency metric. Full455 is blocked.

The generic-record case exposes an undocumented event default and awaits a user decision;
Golden is unchanged. c36 independently clarifies the other four constructions. Explicit
homogeneous comparison targets now supply only their subject/entity grouping normal form;
missing metrics/targets/clarification are never inferred, explicit other groups remain.
Focused witnesses **631 passed**, including all455 unchanged/idempotent plans.

c36 independent: **2/4 pass, 1 mismatch, 1 invalid, 0 provider errors**. Comparison
and co-occurrence pass; plain rarity is mislabeled anomaly, and typical clock profile
requests criteria rather than its undefined definition. Offline **4010 passed, 710 skipped**,
all gates pass. c37 clarifies these two distinctions; focused **631 passed**.
The generic-record population decision remains pending and its fixture unchanged.

c37 independent: **4/4 pass**, zero mismatch/invalid/provider errors. Offline:
**4010 passed, 710 skipped**, all validation gates pass. The user resolved the generic
record population ambiguity in favor of an explicit event default, retaining Golden.
c38 adds that default and the creation-versus-update recency distinction; explicit
entity names still win. Historical runs and fixtures remain unchanged.

c38 direct: **4/5 pass, 1 mismatch, 0 invalid/provider**. The approved event default
is respected; stale updates still choose anomaly rather than recency ranking. c39 makes
that existing metadata-age distinction explicit, without changing Golden or validators.

c39 direct: **4/5 pass, 1 mismatch, 0 invalid/provider**. Stale records now pass.
The remaining typical-clock case switches from needs_definition to needs_criteria;
c40 states explicitly that the undefined meaning of typical takes precedence even when
the event type is unspecified. No fixture or contract changes.

c40 direct: **4/5 pass, 0 mismatch, 1 invalid, 0 provider**. The clock profile now
has the correct intent/block/group, but redundantly attaches start_time to occurrence_count.
c41 extends the existing direct-count normal form to its inapplicable field projection.
All field enums are checked first; unknown fields still fail, and the public validator
continues rejecting count+field. No intent, count operation or missing semantics is inferred.

c41 direct: **5/5 pass**, zero mismatch/invalid/provider errors. Focused witnesses:
**637 passed**. The same frozen production snapshot proceeds to historical nine and,
if green, the complete Core. The record-default decision is resolved; Golden unchanged.

c41 nine: **8/9 pass, 1 mismatch, 0 invalid/provider**. Ordinary category strength
with “besonders” regresses to anomaly. c42 restores the explicit intensifier distinction
in the quantity-ranking rule; undefined quality/dispersion still takes priority. Core
has not started on this candidate. No Golden changes.

c41 offline: **4016 passed, 710 skipped**; Ruff, format, Mypy, OpenAPI no-diff,
docs links and diff checks pass. c42 direct: **6/6 pass**, zero mismatch/invalid/provider;
the same sources proceed to historical nine. No current-phase Golden/schema/validator/
provider changes. Every historical report remains unchanged.

c42 historical nine: **9/9 pass**, zero mismatch/invalid/provider errors. The full
Core121 gate is running on identical sources; no broad run is started before this gate.

c42 offline: **4016 passed, 710 skipped**. Ruff, format, Mypy, exported OpenAPI
no-diff, documentation links and whitespace checks all pass. The accepted generic-record
default changes interpretation documentation only; no Golden case changes in this phase.

c42 Core: **119/121 pass, 1 mismatch, 1 invalid, 0 provider**. Security4/4,
knowledge8/8, regressions76/77, supported56/58. Type-strength ranking regresses to anomaly;
a single filtered population count is labeled aggregate with no grouping. c43 clarifies
both intent distinctions, without changing intent in the canonicalizer or Golden.

c43 direct: **7/8 pass, 1 mismatch, 0 invalid/provider**. Both Core failures pass;
plain rarity regresses to anomaly after the wording was compressed. c44 retains the
German quantitative terms and the explicit rare-versus-unusually-rare contrast. No
canonical intent repair or Golden change is introduced.

c43 offline: **4017 passed, 710 skipped**, all validation gates pass. c44 focused:
**638 passed**; direct **8/8 pass**, zero mismatch/invalid/provider. Historical nine
runs next on the unchanged snapshot. Broader Core/Target evidence is still pending.

c44 historical nine: **9/9 pass**, zero mismatch/invalid/provider. Core121 is running
on identical sources. The prior c42 Core failures remain recorded, not replaced.

c44 offline: **4017 passed, 710 skipped**, Ruff/format/Mypy/OpenAPI no-diff/docs links/
whitespace gates pass. No new Golden changes, public schema changes or provider changes.

c44 Core: **121/121 pass**, zero mismatch/invalid/provider errors. Security4/4,
knowledge8/8, regressions77/77, supported58/58. Target239 now runs on the identical
production snapshot. Full455 remains gated on its result.

c44 Target239: **190 pass, 45 mismatch, 4 invalid, 0 provider**. Security4/4,
knowledge8/8, regressions76/77, supported58/58. Invalids: a missing price bound despite
a duplicate numeric filter, time-distribution question misread as event ranking, and two
blocked regularity plans with missing ordering. Full455 remains blocked. c45 clarifies
price bounds/time-group selection and applies the documented descending default only to
blocked regularity with absent direction; explicit direction and missing operands remain
untouched. Public validation stays strict and Golden unchanged.

c45 direct: **11/12 pass, 1 mismatch, 0 invalid/provider**. All four preceding invalids
are now valid. The time-group question still substitutes occurrences for logical typed
events and loses past tense. c46 reinforces population independence from time grouping
and preservation of known tense even when the grouping unit needs clarification.

c46 direct: **11/12 pass, 1 mismatch, 0 invalid/provider**. Population and grouping
now match; only past tense is dropped. c47 clarifies that past-tense verbs themselves
are temporal constraints, including blocked plans, resolving the ambiguity with the
existing instruction to omit temporal when no constraint is present.

c45 offline: **4019 passed, 710 skipped**; c46 offline: **4020 passed, 710 skipped**;
all required validation gates passed for both. c47 focused: **641 passed**.
c47 direct: **12/12 pass**, zero mismatch/invalid/provider. The historical nine gate
runs on the same unchanged sources. No Golden change was needed for these temporal rules.

c47 nine: **9/9 pass**, zero mismatch/invalid/provider. Core121 is running on the same
snapshot. Offline **4020 passed, 710 skipped**; Ruff, format, Mypy, OpenAPI no-diff,
docs links and whitespace checks all pass. Full455 has still not run.

c47 Core: **120/121 pass, 1 mismatch, 0 invalid/provider**. Security4/4, knowledge8/8,
regressions76/77, supported58/58. Undefined new-venue discovery is mislabeled count despite
its blocking state. c48 states the existing new-record exception directly beside the
existence rule; no deterministic intent substitution or Golden change is introduced.

c48 direct: **12/13 pass, 1 mismatch, 0 invalid/provider**. New-place discovery passes;
stale record metadata regresses to anomaly. c49 moves the existing recency rule before
generic blocking-state decisions and explicitly distinguishes metadata staleness from
inactive event activity. The user-approved event default and Golden remain unchanged.

c49 direct: **11/13 pass, 2 mismatch, 0 invalid/provider**. Stale metadata is correctly
ranked but loses its undefined cutoff; the time-group question again loses past. c50
keeps the cutoff block beside the recency construction and spells out the existing
past-period descriptor without requiring concrete date bounds. No schema/Golden changes.

c50 direct: **12/13 pass, 1 mismatch, 0 invalid/provider**. Time grouping now passes;
stale metadata loses only needs_definition. c51 distinguishes vague age qualifiers
(alt/lange) from ordinary quantity ranking, preserving the existing definition boundary.

c51 single recency case: **0/1 pass, 1 mismatch, 0 invalid/provider**. The sole
remaining difference is still the definition boundary. c52 contrasts qualitative
metadata age with explicit oldest/latest extrema using short concept examples rather
than a corpus question or lookup. No broader live run was launched for c51.

c52 recency single: **1/1 pass**; c52 direct: **11/13 pass, 2 mismatch, 0 invalid/provider**.
The two differences are an unnecessary criterion request for open genre co-occurrence and
a descending/20 default before a time-group dimension is selected. c53 scopes distribution
defaults to known groups and distinguishes open taxonomy membership from explicitly
requested but unspecified names. No clarification state is removed by canonicalization.

c53 direct: **12/13 pass, 1 mismatch, 0 invalid/provider**. All preceding temporal and
recency cases pass; the directional-region comparison drops its explicitly named targets
because their boundaries need definition. c54 retains named comparison targets alongside
that definition block. The canonicalizer still does not invent missing target names.

c48/c49/c50/c51/c52/c53 offline runs each completed **4020 passed, 710 skipped**;
Ruff, format, Mypy, OpenAPI no-diff, docs links and whitespace gates passed for each.
c54 focused **641 passed**; direct **13/13 pass**, zero mismatch/invalid/provider.
Historical nine runs next. All failures and the earlier single-case pass remain separately
recorded; no selective replacement of runs.

c54 historical nine: **9/9 pass**, zero mismatch/invalid/provider errors. Core121
runs on identical sources. Prompt v13, all455 fixtures, public validators and provider
settings remain unchanged in version/scope; this round only clarifies interpretation.

c54 offline: **4020 passed, 710 skipped**. Ruff, format, Mypy, OpenAPI no-diff,
docs-link and whitespace gates pass. The full455 gate is still pending, not claimed stable.

c54 Core: **118/121 pass, 3 mismatch, 0 invalid/provider**. Security4/4, knowledge8/8,
regressions75/77, supported57/58. Type-frequency subject selection becomes aggregate,
southernmost latitude uses descending order, and unordered category counts gain ranking
defaults. c55 distinguishes subject selection from tables and specifies both coordinate
axis directions. Shortened section labels keep the same17-step structure within the
existing prompt-size guard; no guard, schema or Golden changes.

c55 direct: **2/3 pass, 1 mismatch, 0 invalid/provider**. South/latitude direction and
unordered category table pass; most-frequent subject selection remains aggregate. c56
adds the general German subject-selection form to the existing rank definition, without
an exact question or ID branch and without deterministic intent guessing.

c55 offline: **4020 passed, 710 skipped**, all required checks pass. c56 focused:
**641 passed**; direct **3/3 pass**, zero mismatch/invalid/provider. Historical nine
runs next on the unchanged candidate. No existing failed run is removed.

c56 historical nine: **9/9 pass**, zero mismatch/invalid/provider. Core121 is running
on identical sources. No canonicalization, schema, validator or Golden change in c55/c56.

c56 offline: **4020 passed, 710 skipped**. Ruff, format, Mypy, OpenAPI no-diff,
docs links and whitespace gates pass. The candidate remains Draft pending wider live gates.

c56 Core: **120/121 pass, 1 mismatch, 0 invalid/provider**. Security4/4, knowledge8/8,
regressions77/77, supported57/58. This meets every agreed Core gate (supported minimum51).
The one non-blocking supported mismatch is geography-052-001, list versus count; it is
not hidden or reclassified. Target239 starts on identical sources. CI for1f8d695 passed:
<https://github.com/sndcds/uranus-research-planner/actions/runs/37064448952>.

c56 Target239: **192 pass, 41 mismatch, 6 invalid, 0 provider**. Security4/4,
knowledge8/8, regressions76/77, supported58/58. Five invalids attach comparison_targets to
non-compare intents; c57 neutralizes this unused field only after strict target validation.
The sixth seasonal invalid exposes an undocumented month/occurrence placeholder: a user
product decision is pending, Golden unchanged. Venue activity also regresses to event_count.
Full455 remains blocked. Independent fixes continue while the seasonal decision is open.

c57 independent: **5/6 pass, 1 mismatch, 0 invalid/provider**. The comparison-array
invalids are gone and venue-use count passes. A blocked regional set difference drops
its known inclusion area; c58 explicitly preserves that area while keeping unsupported
execution and missing context. The seasonal default still awaits a product decision.

c58 independent: **5/6 pass, 1 mismatch, 0 invalid/provider**. Known inclusion remains
missing only for taxonomy discovery. c59 states retained spatial area restrictions at the
taxonomy construction rule itself; the unsupported set-difference boundary is unchanged.

c59 taxonomy single: **0/1 pass, 1 mismatch, 0 invalid/provider**; only known geography
is omitted. c60 explains the general blocked set-difference decomposition (retain known
inclusion A; block missing B; never execute the partial population). This is an algebra
illustration without named places, case IDs, new operators or Golden changes.

c60 taxonomy single: **0/1 pass, 1 mismatch, 0 invalid/provider**. The actual imported
remote module path/version/prompt hash matches local c60, ruling out stale source loading.
c61 expresses the same area-difference example with explicit existing SpatialV7 field
names instead of functional shorthand; semantics and Golden stay unchanged.

c61 taxonomy single: **0/1 pass, 1 mismatch, 0 invalid/provider**; the compressed
inventory shorthand also loses taxonomy intent. c62 restores explicit intent/entity
construction from c60 and puts the known geographic inclusion in the final consistency
check with actual closed field names. No question-specific name or ID is used.

c57/c58/c59/c60 offline each passed **4025 tests, 710 skipped**, with Ruff, format,
Mypy, OpenAPI no-diff, docs links and diff checks passing. c61 offline passed **4026 tests,
710 skipped**, including a focused negative witness for discarded inclusion geography.

c62 taxonomy single: **0/1 pass, 1 mismatch, 0 invalid/provider**. The only difference
is missing spatial inclusion; this is still an open model interpretation failure, not
an accepted equivalent or a Golden change. Known source path/hash has been verified.
The latest independent six-case batch remains c58: **5 pass, 1 mismatch, 0 invalid/provider**.
No full Core/Target batch has been run on c62, so c56's earlier Core pass is not evidence
that the latest candidate has passed those gates.

The checkpoint awaits the separately documented product decision for trends-061-010:
whether monthly occurrence counts are the canonical blocked seasonal placeholder. Golden
is untouched pending that decision. The approved unqualified-record event default is
implemented/documented, and typed comparison targets are neutralized only outside compare.
No strict public validator, schema, model-call count, provider configuration or fixture
was changed in this continuation. Full455 has **not** run; PR remains Draft, **not merge-ready**.

c62 final offline validation: **4026 passed, 710 skipped**. Ruff, format, Mypy,
OpenAPI export/no-diff, documentation links and git diff --check all pass. This validates
the closed contract and deterministic normalization; it does not claim live acceptance.
