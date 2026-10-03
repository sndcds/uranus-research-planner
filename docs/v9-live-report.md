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
