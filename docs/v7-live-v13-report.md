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
passed. Generated OpenAPI equality is checked again after committing its intentional
version/local-clock annotation update.

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
