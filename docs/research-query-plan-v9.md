# Research Query Plan v9: ordered grouping

`POST /v9/plan` returns `research-query-plan-v9` / `research-planner-v15`.
V8 / prompt v14 is reserved by the administrative-geography work. V7's wire
schema, prompt v13, validators, canonicalizer and Golden corpus remain frozen.
This additive endpoint extends the v7 language with ordered multidimensional
aggregation. It does not redirect existing clients or replace the separate v8
administrative-geography endpoint.

`group_by` is a required array of zero to three distinct closed dimensions.
No grouping is `[]`; former `group_by="genre"` becomes `["genre"]`.
`none` is not a dimension. Unknown dimensions, duplicates and excess dimensions
fail strict validation. Array order is part of the contract and is never sorted.
The remaining v7 language and exact semantic-population boundary are retained.

A seasonal frequency distribution of event types is an aggregate over the event
population, with `group_by=["event_type","month"]` and
`metric.operation="occurrence_count"`. It has no clarification or unsupported
reason. It is a frequency table, not a claim of statistically significant
seasonality and not a period-over-period trend. Genre × month uses the same
operation. Category × municipality groups occurrence locations into resolved
municipal boundaries; no coordinate or administrative identity is inferred by
the Planner. Admin remains authoritative for resolution and execution.

Month means the local occurrence start date's calendar month, 01–12, across years
unless a date filter restricts the population. Unknown dimension values are
excluded, never assigned invented values. An occurrence with multiple taxonomy
memberships contributes once to each corresponding cell; cell totals are not
necessarily additive across taxonomy dimensions. Effective occurrence venue and
space overrides and all existing public eligibility predicates are preserved.

Ordering applies globally to complete cells, never separately to one axis.
`asc`/`desc` sorts the metric value, then each dimension's lower-cased display name
with C collation and stable key, in the requested dimension order. Null ordering
sorts by the dimension tuple. Month keys are zero-padded for calendar ordering.
Limit applies **after** grouping and counting to complete cells; the default
bound is 20. Multidimensional frequency tables default to desc/20. Results are
bounded cell tables, not an assertion that every cell was returned.

Admin normalizes legacy scalar plans to ordered singleton collections. Its shared
ResearchPlanExecutor dispatches a grouping primitive by capabilities, not a wire
version. It reuses `research_sql(occurrences=True)` and the administrative
selection CTE for polygon membership. Occurrence counts use DISTINCT date UUID
within each cell to remove join duplication; they never count distinct events.

The only semantic Golden change is the explicit product decision for
`trends-061-010`. `tests/fixtures/v9_overrides.json` records the executable two-axis
expectation. All other 454 cases are mechanically projected from v7 with scalar
normalization only; a test proves that no other expectation changed.

Opt-in acceptance uses `scripts.run_v9_live_acceptance`, the same one-request
client and safe diagnostic conventions as v7. No production response/log receives
raw model output. Freeze a commit before Core121, Target239 and Full455; report
each run with that exact commit. Live planning tests do not prove SQL correctness:
PostgreSQL execution tests run in Admin CI, never local Docker.
