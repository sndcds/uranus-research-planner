# Frozen v9 acceptance measurement

Planner implementation: `6bf6f1580f45a4155a2009bacb59b33176053468`.
Admin implementation: `7eb8fe520d10354d2d525c2d7785d2fdeaf626fa`.
Schema v9 / prompt v15. All live gates use the exact same committed candidate.
The final report commit changes documentation only. There were no retries, fallback,
deployment, merge, local Docker or local PostgreSQL execution.

## Product decision and scope

V7 and its 455 Golden cases remain frozen. V9 mechanically converts scalar grouping
to ordered arrays; only trends-061-010 changes semantic expectations under the
explicit product decision. It now requires an executable occurrence-count aggregate
over event_type × month. V8/prompt v14 is reserved for administrative geography.
Existing clients are not switched automatically.

| Gate | Pass | Mismatch | Invalid | Provider |
| --- | ---: | ---: | ---: | ---: |
| core121 | 119/121 | 2 | 0 | 0 |
| target239 | 192/239 | 45 | 2 | 0 |
| full455 | 309/455 | 134 | 12 | 0 |

## Local validation

- Planner: 4494 passed, 710 optional live tests skipped. Focused v9: 468 passed.
- Admin Research/API suite: 1364 passed, 213 DB-dependent tests skipped.
- Additional focused grouping/API suite: 11 passed, 4 PostgreSQL tests skipped.
- Admin SQL alias correction: 244 relevant tests passed, 82 DB-dependent tests skipped.
- Initial Admin PostgreSQL CI found two alias-scope errors (4340 other tests passed).
- The outer aliases are now parameterized without rewriting shared taxonomy subqueries.
- This Admin-only correction does not change the frozen Planner used for any live gate.
- Frontend: 1078 tests passed; lint, typecheck and production build passed.
- Both repositories: Ruff, format, mypy, generated OpenAPI checks and diff checks passed.
- Planner documentation links passed. SQL integration runs in GitHub CI.

## Live interpretation

The v12 baseline was 178/455 pass, 208 mismatches and 69 invalid responses.
Comparisons are not a pure model-improvement measure: prior audited v13 Golden
corrections and the explicit v9 product decision also change expectations.
Live acceptance measures language planning, not PostgreSQL execution correctness.

### core121

- security: 4/4, invalid 0.
- knowledge: 8/8, invalid 0.
- regressions: 75/77, invalid 0.
- supported: 58/58.

Most common mismatch roots:

- `metric`: 2

### target239

- security: 4/4, invalid 0.
- knowledge: 8/8, invalid 0.
- regressions: 75/77, invalid 0.
- supported: 59/59.
- seasonal product regression: **pass**.

Invalid outputs remain rejected by the strict contract:

- `combined-060-011`: Value error, unexpected_metric
- `temporal-065-002`: Value error, unexpected_metric

Most common mismatch roots:

- `clarification`: 16
- `intent`: 15
- `group_by`: 13
- `metric`: 12
- `unsupported_reason`: 9
- `anomaly`: 8
- `entity_type`: 7
- `limit`: 3

### full455

- security: 4/4, invalid 0.
- knowledge: 8/8, invalid 0.
- regressions: 75/77, invalid 0.
- supported: 59/59.
- seasonal product regression: **pass**.

Invalid outputs remain rejected by the strict contract:

- `anomalies-057-010`: Value error, unused_temporal_must_be_null
- `comparisons-045-004`: Value error, distinct_dimension_required
- `graph-064-002`: Value error, unknown_relation_edge
- `graph-064-004`: Value error, unexpected_grouping
- `media-070-008`: Value error, measure_and_window_required
- `organizations-063-003`: Value error, unexpected_grouping
- `provenance-071-004`: Value error, metric_field_required_or_unexpected
- `quality-069-007`: Value error, metric_field_required_or_unexpected
- `quality-069-008`: Value error, metric_field_required_or_unexpected
- `quality-069-009`: Value error, metric_field_required_or_unexpected
- `ranking-039-005`: Value error, metric_field_required_or_unexpected
- `temporal-041-001`: Value error, event_count_per_event_is_meaningless

Most common mismatch roots:

- `unsupported_reason`: 75
- `intent`: 61
- `clarification`: 47
- `metric`: 37
- `group_by`: 23
- `ordering`: 20
- `entity_type`: 16
- `limit`: 13

## Status

**Not merge-ready.** Core regressions are not 77/77 and Target239 contains invalid
outputs. No expectations or validators were changed to conceal these failures.
Remaining language/canonicalization errors are reported in the complete JSON cases.
The requested multidimensional capability is implemented; broader acceptance remains open.

[Machine-readable reports](v9-live-results.json)

[Planner CI](https://github.com/sndcds/uranus-research-planner/actions/runs/37103906321)

[Admin CI](https://github.com/sndcds/uranus-admin/actions/runs/37104773203)

CI status at report time: Planner CI passed on the frozen implementation commit.
Admin CI backend/PostgreSQL tests, lint and typecheck passed after the alias fix;
its final frontend rerun was still in progress. The initial frontend CI and local
frontend gates passed; the follow-up changes only backend SQL aliases and tests.
No CI completion was awaited.


## Invalid-output audit at reviewed head c58ddce

This audit precedes implementation. Reviewed head:
`c58ddcea9506205ae3da45fee50a155bd3436371`; recorded implementation remains
`6bf6f1580f45a4155a2009bacb59b33176053468`. No new candidate or live gate exists.
All historical runs above and in the JSON remain unchanged.

Every recorded invalid proposal was replayed through the current canonical output
adapter: **14/14 reproduce the exact recorded validation errors**. All 14 corresponding
Golden structural witnesses validate. Schema validity alone does not establish semantic
correctness. The JSON audit includes each question, full emitted proposal, validation
errors, full expected witness, cluster and proposed treatment.

| Cluster | Cases | Finding and prospective treatment |
| --- | --- | --- |
| A — spurious metric on record selection | combined-060-011, temporal-065-002 | Count attached to search/list. Narrow typed metric neutralization may be safe without metric_filter; prompt must preserve overlap and distinguish undefined competition from unsupported district pairing. |
| B — metric concept/operand mismatch | comparisons-045-004 | Diversity has no declared dimension. Never substitute genre/category for themes; preserve missing comparison criteria and data boundary. |
| B — unsupported publication lead-time | quality-069-007, quality-069-008, quality-069-009 | Creation metadata is incorrectly attached to duration/regularity. Prompt should preserve blocked anomaly with no fabricated metric. |
| B — redundant operand on valid duration | ranking-039-005 | Duration(start_date) must use implicit occurrence start/end with field=null. This is representable and must not be treated like publication lead-time. |
| B — provenance metric conflict | provenance-071-004 | Both actual and expected metrics substitute a different population for update actions. Product decision required; no automatic repair. |
| C — ranking intent/subject | graph-064-004, organizations-063-003 | Actual intent is relation, not rank. Keep venue as ranked subject and distinct organizations as metric; no deterministic intent guessing. |
| C — chronological extremum | temporal-041-001 | Event cardinality substitutes for value(start_date). Interpretation must supply the chronological field, not infer it from a count proposal. |
| D — empty temporal object | anomalies-057-010 | Explicit needs_date plus entirely neutral temporal object. Exact typed empty-object normalization may be safe; real temporal constraints must remain. |
| E — illegal shared path | graph-064-002 | Actual via=[event,occurrence,space] contains illegal edges. Prompt must construct the legal return path; arbitrary path repair is unsafe. |
| F — partial frequency | media-070-008 | Neither measure nor window supplied for unsupported image-source population. Do not guess operands. |

The two regression mismatches are `regressions-090-019` and
`regressions-091-009`. Both ask “Wer veranstaltet die meisten Veranstaltungen?”
and differ only in `metric.operation`: expected event_count, actual occurrence_count.
This is an event-cardinality versus venue-utilization interpretation error, distinct
from the invalid-output clusters. The venue-use occurrence default must not spill into
organization rankings of explicitly requested logical events. No Golden correction is
justified for these two cases.

### Stop: provenance Golden requires a product decision

`provenance-071-004` asks “Welche Quellen aktualisieren Veranstaltungen besonders häufig?”
Golden requires `frequency`, `measure=occurrence_count`, `window=month`, with
`insufficient_structured_data`. The recorded proposal instead emits
`regularity`, `field=modified_at`, `measure=event_count`, `window=week`; it correctly fails
strict validation. Neither representation measures source update actions.

The [metric contract](research-query-plan-v7.md) defines frequency as a count measure per
named calendar window. The retained [v9 semantics](research-query-plan-v9.md) count
occurrence/date UUIDs, not updates. No documented provenance rule makes month a default
or occurrence_count an update-action measure. The closed algebra has no update-action
measure. A blocked plan may omit an unrepresentable metric; blocking does not redefine
the meaning of an existing metric.

Recommended decision: retain rank, unknown source entity, missing structured data and
known ordering/limit, but require metric=null. This would need an explicitly audited
v9-only Golden correction; v7 must remain frozen. Alternatively, product must explicitly
define a non-executable placeholder policy and its semantics before requiring this
otherwise unrelated metric. **Neither option has been applied.**

Per the requested stop condition, implementation and live tuning stop at this conflict.
Prompt, canonicalizer, public validators, schema, Golden expectations, API/provider and
Admin are unchanged. No live calls were made, no candidate was frozen, and the prior
Core121/Target239/Full455 scores are historical evidence only. PR remains Draft and
**not merge-ready**. No deployment or merge.

Audit validation: full offline suite **4494 passed, 710 skipped**; focused v9 suite
**468 passed**. Ruff, formatting, mypy, OpenAPI reproduction (no diff), local docs
links and git diff --check passed. The proposed blocked metric=null representation
also validates without schema changes; this check does not approve changing Golden.
No new prompt/canonicalization regression tests were added because no implementation
change was made before the explicit contract-decision stop.
