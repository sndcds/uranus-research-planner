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
