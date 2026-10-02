# Research v7: initial audit and post-merge baseline

Original pre-implementation audit base: `e73358cc7ceec06f0edeb7d486ba75608c30f92a`.
Original branch: `feat/research-query-language-v7`. PR #16 was absent from that base.
The integration fix starts at `0396761b8de4791e9808711f32c0ec13925c4e08` and preserves PR #16.
The updated frozen baseline is documented below; the original base is historical.

## Frozen contracts

`/plan` (schema v3 / prompt v7), `/v4/plan` (domain proposal and its own versioning),
`/v5/plan` (schema v5 / prompt v10), and `/v6/plan` (schema v6 / prompt v11) retain
their accepted post-PR-#16 behavior, types, prompts and fixtures.
V7 keeps schema v7 and now has the distinct prompt research-planner-v12. In particular v6 inherits v5;
changing that base would silently change both contracts. v7 will not inherit them.
The old analytical language veto remains confined to its old endpoints.

Read in full: analytics_schema.py, analytics_prompts.py, geography_schema.py,
geography_prompts.py, model_client.py, app.py, config.py; test_analytics.py,
test_geography.py, test_model_client.py, test_contract.py, test_live_expectations.py;
analytics.json and geography.json. All references to plan_v5/plan_v6, the analytical
and geographic classes and their version constants were searched, including docs,
protocols, OpenAPI and optional live tests. Also inspected security.py, planner.py,
endpoints.py, transport contracts, CI and pyproject.toml.

## New files

- research_v7_types.py: independent closed base, enums, metrics and typed filters.
- research_v7_constraints.py: temporal, spatial, price, relation, trend and context models.
- research_v7_schema.py: composition, cross-model invariants and versioned envelope.
- research_v7_prompts.py: compositional language interpretation, no question lookup table.
- tests/fixtures/v7/: categorized expectations; independent catalog manifest and schema snapshot.
- Test-only corpus loader/comparator, completeness/negative/client/API/live/compatibility tests.
- Developer corpus report and v7 contract/Admin handoff documentation.

## Minimal existing changes

Add imports and v7 method/agent to model_client.py and planner.py. Add one handler to
app.py and v7 to both RequestBoundary path allowlists in security.py. Add README links
and regenerate docs/openapi.json; assert every old path/component is unchanged.
No changes to provider policy, configuration defaults, old schemas/prompts or old fixtures.

StructuredModelClient.plan_v7 shares the existing SDK, bounded transport and `_infer`.
Its independent NativeOutput agent has retries=0, supports_tools=False and instrumentation
off. `_infer` retains request_limit=1/tool_calls_limit=0. No lookup/retrieval, repair,
second attempt or fallback. Exact query equality is checked at client and API boundaries.

POST /v7/plan uses PlanRequest, RequestBoundary, shared inference_slot, timezone-local
reference_date, provider revalidation, safe diagnostics/logging and independent v7 response.
Unsupported plans remain inspectable as an explicit `kind=unsupported` envelope; they
are never successful executable `kind=plan` responses. Existing endpoint error semantics
are untouched. This is a language contract, not an assertion of executor availability.

## Contract decisions

Seven entity types distinguish logical events from occurrences. Twelve generic intents
replace result-mode duplication. Nullable nested objects have a single neutral state:
null. Non-null objects must contain a meaningful, type-compatible constraint. All wire
fields remain required, including nullable fields. Metrics are bounded and nonrecursive;
ratio/percentage operands cannot contain ratios. Typed filter variants restrict values,
fields and operators. A separate numeric metric predicate expresses conditions on a
computed group (e.g. at least two venues) without a free expression language.

Geography separates administrative membership from named-point radius references;
no coordinate fields exist. Deictic nearby requires needs_location. Unknown border,
calendar jurisdiction, adjective threshold or comparison target requires clarification.
EUR is the initial nominal currency allowlist, required by the supplied Euro examples.
The Planner repository contains no authoritative source currency enumeration. Additional
currencies require Admin contract verification and explicit extension; no conversion
is implied and no claim about live currency coverage is made.

Semantic residuals can retrieve evidence, not establish exact populations. Missing
history, provenance, POIs, demographic data and authoritative accessibility semantics
are explicitly classified. Regularity/outlier methods and evaluative words are not
silently defined. Corpus capability metadata is test/developer data, not a production
routing table or a substitute for Admin capability validation.

## Reviewed post-merge legacy snapshot

PR #16 is commit `b6c78636e0674becc12d5f29ffe74dda87dd202d`; the combined main is
`0396761b8de4791e9808711f32c0ec13925c4e08`. Before any edits, every pinned file was
compared byte-for-byte at the old baseline, PR #16, and combined main. Every old hash
matched the original baseline, and every current file matched PR #16 exactly.
The PR #16 diff was reviewed: event grouping, occurrence-count-only validation,
language/guard rules, v5/v6 version bumps and regression fixtures are legitimate.
Only the six changed file hashes below were replaced; the other twelve were retained.

| Pinned file | Review outcome |
| --- | --- |
| src/research_planner/analytics_schema.py | Updated: event grouping validation and prompt v10 |
| src/research_planner/analytics_prompts.py | Updated: event occurrence ranking semantics |
| src/research_planner/analytics_guard.py | Updated: requested grouping veto |
| src/research_planner/geography_schema.py | Updated: inherited event grouping and prompt v11 |
| src/research_planner/geography_prompts.py | Unchanged file/hash; imports the updated analytical prompt |
| src/research_planner/schemas.py | Unchanged |
| src/research_planner/prompts.py | Unchanged |
| src/research_planner/domain_schema.py | Unchanged |
| src/research_planner/domain_prompts.py | Unchanged |
| src/research_planner/domain_planner.py | Unchanged |
| src/research_planner/config.py | Unchanged |
| src/research_planner/endpoints.py | Unchanged |
| src/research_planner/transport.py | Unchanged |
| tests/fixtures/analytics.json | Updated: 17 ranking/contrast language variants |
| tests/fixtures/domain_output_schema.json | Unchanged |
| tests/fixtures/domain_queries.json | Unchanged |
| tests/fixtures/geography.json | Updated: exact event occurrence ranking regression |
| tests/fixtures/queries.json | Unchanged |

All six pinned OpenAPI paths are unchanged. Eight component hashes changed exactly
as in PR #16: AnalyticalClarification, AnalyticalDiagnostics, AnalyticalQueryPlan,
AnalyticalResponse, GeographicClarification, GeographicDiagnostics, GeographicQueryPlan,
GeographicResponse. Their differences are event grouping enums and prompt v10/v11.
All other twelve pinned components are unchanged. No v7 component was added to the
legacy freeze. The separate v7 schema snapshot remains byte-identical: it describes
the plan algebra, not envelope/diagnostics prompt versions.

The snapshot now names PR #16 as its baseline. The freeze test itself remains strict;
this is an audited re-pin, not automatic acceptance of future drift.
