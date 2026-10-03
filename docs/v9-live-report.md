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


## Approved provenance decision and stabilization candidate

The user approved the audit recommendation: provenance-071-004 now has metric=null
in a **v9-only override**, retaining rank, entity=null, desc/20, clarification=none,
and insufficient_structured_data. V7 is untouched. This is the second enumerated
semantic override alongside the seasonal event_type × month product decision.
Historical reports and the pre-decision audit above remain unchanged.

The candidate addresses all six audited classes with general rules: record selection
has no metric; undefined/unrepresentable measures stay null; subject ranking differs
from relation discovery; chronological extrema use a date value; real temporal
constraints differ from a neutral placeholder; shared paths traverse legal edges to
and from the shared object. Frequency operands must be complete, never invented.
Publication lead-time does not reuse duration, metadata or regularity metrics.
Organization event cardinality is explicitly separated from venue-use occurrences,
addressing both duplicate-language regression cases without ID/string routing.

Canonicalization is restricted to unused valid count/value metrics on unambiguous
list/search proposals, entirely neutral start_date objects under needs_date, and the
existing operand-free undefined-diversity rule extended from rank to compare.
All nested fields remain closed and typed before normalization; the public validators
and native schema are unchanged. Illegal paths and incomplete frequency metrics fail.
Prompt v15 remains the candidate version and is no longer than the reviewed prompt.
New offline witnesses exercise both accepted normal forms and rejected ambiguity.
Live results will be appended with exact candidate and selection; none are claimed yet.

Candidate offline validation: **4539 passed, 710 skipped**; focused v9 **513 passed**.
Ruff, formatting, mypy, OpenAPI reproduction, docs links and diff checks passed.
The initial reverse-order focused invocation exposed the existing import-sensitive
Literal enum ordering in the schema snapshot; repository collection order and the
full suite pass without re-pinning or changing any public schema. No failure was skipped.
Runtime prompt: 15445 characters, SHA256
`840289d0da9120991760176f31ec668769bb2ed75d478f200aaa321a8ee7d599`.
The focused selection contains 42 cases: all14 invalids, both regressions, seasonal,
security4, knowledge8 and 13 previously passing controls across intent/metric families.

### Focused42 on candidate 4edf4f6 — stop at control regression

Exact candidate: `4edf4f625201a3086df8c486878636ff803d62b2`.
Model: `gpt-5.6-terra`; schema `research-query-plan-v9`; prompt `research-planner-v15`;
reference date `2026-10-02`. Prompt hash is recorded above. Full ordered selection,
control IDs, report metadata, raw safe outcomes and artifact hash are appended under
`stabilization_after_provenance_decision` in the JSON. Historical objects are intact.

| Gate | Pass | Mismatch | Invalid | Provider |
| --- | ---: | ---: | ---: | ---: |
| focused42 | 29 | 13 | 0 | 0 |

- All14 previously invalid cases now produce strictly valid plans: 9 pass, 5 mismatch.
- Both event-cardinality regression cases pass.
- Provenance source updates correctly retain blocked rank with metric=null: pass.
- Seasonal event_type × month: pass.
- Security: **4/4**. Knowledge: **1/8** (previously 8/8).
- Explicit previously passing controls: **12/13**.

The failing control is `taxonomy-048-002`, the unordered per-category count table:
actual aggregate/event_count/category is correct, but ordering=desc and limit=20
replace expected null/null. This is not the approved multidimensional default; the
single-axis category table must retain its documented semantics. Canonicalization
has not rewritten this ordering/limit, and no Golden adjustment is justified.

Seven knowledge cases keep intent=knowledge and neutral data fields but introduce
needs_context: knowledge-047-001/002/004 and knowledge-026-001/002/003/004.
The condensed project-routing phrase “Require project context” may have encouraged
confusing project-domain recognition with a conversation-context requirement. This
is a diagnosis to test, not a causal claim established by a single sample. Golden
remains authoritative: ordinary project questions require no prior conversation.

Other structurally valid mismatches:

| Cluster | Cases | Remaining difference |
| --- | --- | --- |
| Vague current period | anomalies-057-010 | needs_date dropped |
| Competition boundary | combined-060-011 | Adds insufficient_structured_data instead of definition-only block |
| Theme comparison | comparisons-045-004 | Compare becomes anomaly, needs_definition and venue grouping |
| Media source boundary | media-070-008 | Rank/unsupported_constraint rather than blocked list/missing data |
| Pairwise district membership | temporal-065-002 | Unsupported constraint is lost; overlap alone is not the requested predicate |

These are not accepted equivalent answers. In particular, dropping the district
constraint remains a semantic contract violation despite a structurally valid plan.
The reduction to zero invalids does not establish acceptance stability.

**Stop condition reached:** a fix candidate regressed previously passing controls.
No second general fix or additional live call was attempted. Exactly **42** new live
calls were made. The candidate was **not frozen for broad gates**. Core121, Target239
and Full455 were **not rerun**; older candidate scores are not reused as evidence.
PR #20 was verified Draft and remains **not merge-ready**.

No additional product/schema decision is currently identified. A separately scoped
follow-up should isolate knowledge-routing wording and single-axis distribution
defaults against the unchanged controls; no permission to relax Golden or validators
is implied. No further tuning is performed under this continuation's explicit stop rule.

Final offline verification after recording the run: **4539 passed, 710 skipped**;
focused v9 **513 passed**. Ruff, format, mypy, OpenAPI no-diff, docs links and
whitespace checks passed. All public schema/validator/provider files and v7 fixtures
are byte-identical to the reviewed head. Only report files changed after the live
candidate; no newer implementation claims its evidence. No Docker, deployment or merge.
