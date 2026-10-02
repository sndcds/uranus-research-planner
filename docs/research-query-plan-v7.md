# Research Query Language v7

`POST /v7/plan` → `research-query-plan-v7` / `research-planner-v13`.
This is an additive proposal for coordinated Admin integration, not a client migration.
The integration-fix base is `0396761b8de4791e9808711f32c0ec13925c4e08`.
The frozen legacy baseline is the accepted PR #16 commit `b6c78636e0674becc12d5f29ffe74dda87dd202d`.

## Boundary and compatibility

Natural question → one configured model interpretation → closed Pydantic plan →
**later** Admin capability validation, name resolution and execution → source evidence.
Planner interprets; Admin resolves and executes; source databases remain authoritative.
There are no database, SQL, PostGIS, Qdrant, Jina, Nominatim, knowledge retrieval,
coordinate, result, generated keyword, arbitrary expression or tool slots in v7.
Names are resolver proposals, never invented IDs. No counts are calculated here.

`/plan`, `/v4/plan`, `/v5/plan` and `/v6/plan` retain their existing contracts and
behavior. v7 uses independent classes, not inheritance from analytical/geographic plans.
Legacy source/fixture hashes and every old OpenAPI operation/component are pinned in
`tests/fixtures/v7_legacy_contracts.json`; old fixtures still run normally.
v5 remains research-query-plan-v5 / research-planner-v10;
v6 remains research-query-plan-v6 / research-planner-v11.
v7 uses research-query-plan-v7 / research-planner-v13, without changing its data algebra.

The request remains `{query, timezone, language}` with existing defaults/bounds.
No browser coordinates, result context or executor capabilities are accepted.
`reference_date` is computed in the request timezone. Auth, RequestBoundary, concurrency
semaphore and timeout are shared. All provider output is revalidated, including exact
`original_query` equality, at both client and endpoint boundaries.

The existing transport is unchanged: one inference, request_limit=1, tool_calls_limit=0,
retries=0, supports_tools=False; no redirects, environment proxies, memory or repair call.
Terra retains reasoning_effort=none and no temperature. Configuration/token/timeout
limits are unchanged; large v7 outputs may exceed the existing token budget and fail
closed. Live language accuracy, latency and token adequacy require separate acceptance.

## Envelope and neutrality

Responses include `kind`, `schema_version`, `prompt_version`, `model`, `plan`,
`reference_date`, `timezone`, and timing/request/model/intent/version diagnostics.
V7 uses HTTP 200 for validated interpretations, with explicit disposition:

| kind | Meaning |
| --- | --- |
| plan | Structurally executable interpretation; Admin must still validate capabilities/data |
| needs_clarification | Missing definition, criterion, date, location or context; do not execute |
| unsupported | Explicit capability boundary; do not execute, even if partial fields are present |

Invalid provider output remains `planner_invalid_response` (502), without another call.
The question/provider body is not logged. Older endpoint error semantics are unchanged.
Unsupported reason takes precedence over clarification in envelope disposition.

Every object forbids extra fields, uses strict types and rejects NaN/Infinity.
All wire properties are required, including nullable ones. Unused nested objects use
**null**, arrays use `[]`, grouping uses `none`, clarification uses `none`.
There is no redundant `answer_mode`. Result shape is derived from intent by Admin.
There is no all-neutral non-null temporal/spatial/price object.

Query length ≤2000; names ≤160; semantic query/focus ≤500; filters ≤16;
comparison targets ≤4; relation intermediates ≤3; result limit 1..20.
Blank strings, unknown enum values, extra properties, duplicate targets/filters and
contradictory named/presence constraints are rejected. The supplied query is preserved
byte-for-byte, without trimming or rewriting it.

## Entities and intents

Entities: `event`, `occurrence`, `venue`, `space`, `organization`, `municipality`, `region`.
Event is a logical event; occurrence is one event date. "Veranstaltungen" counts events;
"Termine" counts occurrences. Taxonomy dimensions do not invent new entity types.
`entity_type=null` is reserved for knowledge, explain and unsupported non-data subjects.

| Intent | Requested result |
| --- | --- |
| list | Structured records |
| search | Semantic evidence records |
| count | Exact count of the selected entity |
| aggregate | Grouped measures, or one scalar statistic |
| rank | Entity/dimension ordering by an explicit metric |
| compare | One metric across 2..4 distinct named targets |
| taxonomy | Dictionary values for category, event_type or genre |
| relation | Closed domain connections |
| trend | Defined period comparison |
| anomaly | Explicit criterion, or clarification |
| explain | Evidence/definition/context request |
| knowledge | Project-knowledge routing |

Executable ranks require metric, ordering and limit. Counts require countable metrics
matching their entity. Aggregates require a metric; count aggregates also require grouping.
Comparisons require a metric and 2..4 targets. Taxonomy, relation and trend require their
respective constraint. Undefined/unsupported **non-executable partial interpretations**
may omit a rank metric or relation that the contract cannot express; inventing a substitute
would be worse than preserving the explicit boundary. They cannot have `kind=plan`.

## Metrics and grouping

Metric properties: `operation`, `field`, `distinct_by`, `numerator`, `denominator`,
`measure`, `window`, `currency`. Unused operands are null. Operators are closed:

| Operation | Meaning / required operands |
| --- | --- |
| event_count, occurrence_count, venue_count, space_count, organization_count | Distinct authoritative entity identities |
| distinct_count | Required closed distinct_by dimension |
| minimum, maximum | Extremum of a compatible numeric/date/time field |
| average, median | Numeric field statistic |
| field_length | description only; Unicode text length, no LLM assessment |
| value | Direct numeric/date/time projection, including latitude/longitude extrema |
| duration | Elapsed occurrence start/end; event ranking uses longest complete occurrence |
| distance | Spatial reference required; distance computation belongs to Admin |
| diversity | Distinct category/genre/event_type/organization/venue count, not Shannon |
| ratio, percentage | Nonrecursive numerator and denominator |
| frequency | Count measure per named calendar window |
| regularity | Reserved concept; needs_definition until a method is defined |
| absolute_change, percentage_change | Trend constraint with matching measure/window |

Fields: description, start_date, start_time, end_date, end_time, created_at, modified_at,
min_price, max_price, latitude, longitude, population. No free database field names.
Missing values do not become zero or inferred endpoints. Admin must define eligibility,
null handling, timezone boundaries and report exclusions. Zero denominators must yield
an undefined measure, not Infinity or fabricated zero. No per-capita value is supplied
by the model. Before activation Admin must implement and test these metric definitions.

Ratio operands are only the five counts, distinct_count or population, with closed
subset `all`, `free`, `paid`. Percentage requires a free/paid subset of the same count
population. Arbitrary nested expressions, max-minus-min, share-of-largest-group and
multi-dimensional group expressions are intentionally absent and fail closed.

Groupings: none, event, occurrence, venue, space, organization, category, event_type,
genre, municipality, region, country, hour, weekday, week, month, year.
`event_count` grouped by event is rejected. Event occurrence ranking uses
`occurrence_count` grouped by event, never event_type. `metric_filter` is a typed numeric
predicate on the computed measure (e.g. distinct venues >1). Zero-count groups need an
explicit authoritative universe in Admin; absence from a retrieved list proves nothing.

## Filters, taxonomy and prices

Filters form an AND conjunction. Each union variant restricts fields/operators/types:

- Presence/missing: description, venue, space, organization, category, event_type, genre,
  price, image, coordinates, start_date/time, created_at, modified_at, status,
  ticket_link, registration_link.
- Name equality/inequality: venue, space, organization, category, event_type, genre.
- Description equality/inequality: bounded literal text, not an expression.
- Status equality/inequality: released/cancelled; Admin must verify source mapping.
- Numeric price/population: eq, neq, lt, lte, gt, gte, between with typed predicate bounds.
- Dates start_date/created_at/modified_at and local start_time: typed comparisons/ranges.

Between requires both ordered bounds. Name/presence filters cannot take numeric
operators. Repeated taxonomy equality means intersection, not OR. There is no arbitrary
Boolean DSL. Resolver names remain authoritative only after Admin resolution.
Category, event_type and genre are separate: Konzert is event_type, Jazz is genre.
No text-derived taxonomy inference is allowed.

Price modes: free, paid, less_than, greater_than, between. Null is neutral.
Numeric limits are finite, nonnegative and ≤1,000,000; minimum ≤ maximum.
EUR is the initial closed currency allowlist for the supplied Euro requirements.
The Planner repository does not prove other source currencies; Admin must verify them
before an explicit contract extension. No conversion or averaging across currencies.
Free means known zero admission, never unknown/missing price. Paid means known positive
admission. Ranking minimum advertised price uses min_price, maximum uses max_price;
these are nominal advertised bounds, not actual ticket sales or historical prices.

## Temporal and spatial constraints

Temporal field separates occurrence start_date from created_at/modified_at recency.
Periods: none, today, tomorrow, this_weekend, next_week, this_month, this_year, past,
future, explicit_range. Explicit ranges require both dates including year in order.
A missing year remains needs_date. Past lookback uses bounded integer 1..120 plus
unit day/week/month/year. "New" without a definition needs_definition; never semantic.

Time of day: none/morning (06..12)/afternoon (12..18)/evening (18..22)/night (22..06),
plus consistent local before/after time and weekday. Calendar relation is none/holiday/
school_holiday with jurisdiction name, not an invented calendar. Missing jurisdiction
needs_location. overlap is interval intersection; multi_day spans local calendar dates.
Neither establishes audience competition or causal effects. Metadata times cannot carry
occurrence-only clock/calendar/overlap/multi-day clauses.

Spatial relations: at, inside, outside, nearby, within_radius, near_border, across_border,
north_of, south_of, east_of, west_of, nearest. Null means no spatial constraint.
Reference is named/user_location/border/nearest_venue. `at` is named-place membership;
inside/outside use area_query. Street/square references use place_query. Venue names
use entity name filters. Place and area slots cannot conflict. Named radius references
use place_query, e.g. Flensburg with 10000 metres, not a hidden semantic phrase.
Radius is integer 1..500000, only within_radius/near_border; within_radius requires it.

Nearby is deictic: user_location, no named slots, needs_location. "Wo finden
Veranstaltungen statt?" does not request location permission. The model never sees
browser coordinates. Border relations preserve the reference area and never create
geometry. Unspecified border needs location; undefined "near" needs a distance definition.
Rural/large-city/coverage boundaries are not guessed. Nearest venue is a declared data
reference, not an invented point; exclude self-comparisons in later execution.

## Relations, trends and anomalies

Relations use related/shared/path/distinct_count with source, target, bounded via path
and optional resolver names. Only undirected edges organization–event, event–occurrence,
event–venue, event–space, space–venue, event–category/type/genre are legal.
Organization–venue is explicitly via event. Shared organizations via venues use
organization → event → venue → event → organization. Shared data does not prove
collaboration. No arbitrary graph edges, image/source nodes or graph centrality exist.

Trend measures: event_count, occurrence_count, venue_count, organization_count.
Comparison: previous_period/previous_year. Window: day/week/month/quarter/year; day
supports "today compared with last year". Change: absolute_change/percentage_change.
No history is inferred from current rows. Missing time window needs_date.

Anomalies are rare/inactive/outlier. Rare/inactive require explicit numeric criteria;
outlier and regularity have no mathematical method in this version and remain blocked.
Unusual events need needs_definition with anomaly outlier/measure null. Dominance, influence, rurality, surprising diversity,
network hubs and similar undefined terms need_definition. The model cannot decide these
subjectively. Source history, long-term baselines and complete populations are separate
capability dependencies, not model-generated facts.

## Semantic, explainability and knowledge

Semantic contains only query/focus. Children/family suitability, accessibility mentions
and thematic similarity may use evidence search. Semantic retrieval is **not an exact
population**. Exact counts/aggregations/percentages/comparisons/trends with semantic
conditions require unsupported_reason=insufficient_structured_data; intent is preserved.
Missing fields are always structured. Topics must not silently become genres/categories.

Explain targets: result, metric, filter, population, source, definition, exclusion.
Previous-result explanations require needs_context: this request has no conversation
context contract. Definition requests carry their term. Explain cannot carry a disguised
normal cultural data query. Knowledge carries only the unresolved project question,
entity null and neutral data filters; Admin later routes to uranus-research-knowledge.
The Planner never answers the project question itself.

Clarifications: none, needs_criteria, needs_location, needs_date, needs_definition,
needs_context. Unsupported reasons: outside_research, unsupported_constraint,
insufficient_structured_data. Outside research uses a fully neutral non-data plan.
An unknown operation never becomes an unfiltered event list.

## Examples (selected fields, not complete wire payloads)

| Question | Interpretation |
| --- | --- |
| Welches Event hat die meisten Termine? | rank/event; occurrence_count; group event; desc; limit 1 |
| Welcher Veranstaltungstyp hat die meisten Termine? | rank/event; occurrence_count; group event_type; desc; 1 |
| Welches Event hat den längsten Beschreibungstext? | rank/event; field_length(description); desc; 1 |
| Welche Events haben keinen Ort? | list/event; venue missing; semantic null |
| Welche Veranstaltungen kosten weniger als 10 Euro? | list/event; price less_than, maximum 10, EUR |
| Im Umkreis von 10 km um Flensburg | within_radius/place Flensburg/radius_m 10000 |
| Was ist in meiner Nähe? | nearby/user_location; needs_location |
| Welche Kommune hat die meisten Events pro Einwohner? | rank/municipality; ratio(event_count,population); group municipality; structured-data dependency |
| Welche Veranstaltungen sind ungewöhnlich? | anomaly/outlier; needs_definition; no semantic query |
| Was ist Uranus? | knowledge; no cultural-data constraints |

Full schema: `tests/fixtures/v7_schema.json`; endpoint schema: [OpenAPI](openapi.json).
Full coverage and all capability-specific question lists: [corpus report](v7-corpus-report.json).
Admin work and known unsupported compositions: [handoff](v7-admin-handoff.md).

## Executable acceptance specification

455 question occurrences in 25 files retain every supplied catalog question and variation,
including intentional repeats in different sections, DE/EN/DA regressions, security and
all old analytical/geographic fixture questions. No duplicates were removed.
IDs encode category/source section/ordinal; sections 90–92 are added multilingual/legacy
regressions. Section 93 adds the eight missing PR #16 variants (447 + 8 = 455); the
other nine analytics additions and the geography addition were already covered. A separate manifest pins question text, category, ID and source section.
Tests reject missing/unreferenced files, unknown statuses/categories and duplicate IDs.

Capabilities are **test metadata**, never prompt routing:

| Status | Meaning |
| --- | --- |
| supported | Existing Admin execution family is plausibly reusable through a v7 adapter; not deployed v7 support |
| planned | Complete declarative interpretation; new Admin execution work remains |
| needs_clarification | Representable operation awaiting date/location/criteria parameters |
| unsupported | Explicitly unrepresentable composition or outside-research request |
| needs_definition | Undefined evaluative/mathematical term |
| needs_structured_data | Required authoritative data/semantics not established |
| semantic_only | Evidence search, not exact statistical population |
| needs_context | Prior result or referent required |
| knowledge | Project-knowledge service routing |

The two extra statuses prevent labelling blocked interpretations as planned/executable.
The report lists every question under its capability with notes and data dependencies.
Feature counts overlap and include blocked plans; they are not success-rate claims.

Dotted expect/forbid assertions and sample plans exist only in test code. Mocked client
and API tests pass those sample plans through the real structured-output and validation
boundaries; they do **not** prove Terra understands the language. Live tests use the same
expectations with actual model output and require explicit opt-in. The entire corpus is
never loaded into production or copied into the prompt.

```sh
uv run pytest -q
uv run python -m scripts.report_v7_corpus
# Explicit optional acceptance, with provider credentials already configured:
RESEARCH_PLANNER_LIVE_TEST=1 uv run pytest -q tests/test_research_v7_live.py
# Narrow opt-in production regression:
RESEARCH_PLANNER_LIVE_TEST=1 uv run pytest -q tests/test_research_v7_live.py -k ranking-039-004
```

Normal tests make no live provider, database, geocoder or retrieval calls. The live
acceptance suite has not been run for this change; language accuracy remains unverified.

## v13 canonical interpretation (unchanged algebra and validators)

The [v12 audit](v7-live-audit-v12.md) reviews all 208 mismatches and 69 invalids before
any prompt/golden change. [v13 acceptance results](v7-live-v13-report.md) distinguish
prompt effects from the 44 audited fixture corrections. All 455 questions remain.

- Subject selection by most/fewest/multiple/only one is rank; distributions and scalar
  statistics are aggregate without implicit ordering/limit. Rank groups by its subject,
  except an explicitly requested taxonomy/calendar dimension. Singular superlative=1,
  plural/open Wer/Wo=20. Taxonomy ranks use event population even for occurrence_count.
- Undefined concepts use needs_definition; missing selection parameters use needs_criteria.
  Missing comparison targets are not anaphoric context. Only actual referents/previous
  results require needs_context. Unusualness uses a valid blocked outlier object.
- Canonical related direction is source=requested result, target=referenced counterpart;
  node queries stay attached to those roles. Legal edges remain undirected. Shared
  membership uses shared; path is reserved for connection routes. No inverse-comparator
  shortcut is introduced.
- Planner extracts unresolved taxonomy surface concepts; Admin owns normalization and
  authoritative ambiguity. Eighteen golden cases declare exact reviewed name variants
  solely at their event_type value slot. No fuzzy/substring matching, inferred IDs,
  other name normalization, role changes, or filter reordering is accepted.
- Free/paid predicates use null bounds/currency. Numeric price metrics/comparisons use
  EUR; e.g. cheapest paid has metric.currency=EUR and price.currency=null. The existing
  API validator still accepts the noncanonical free/paid EUR representation; canonical
  golden acceptance does not. This PR does not tighten or loosen schema acceptance.
- Clock before/after uses TemporalV7; taxonomy discovery has no grouping/metric.
  Explain/knowledge neutralize all data-execution fields. Semantic exact statistics
  retain their intended intent with insufficient_structured_data.
- Trends construct metric operation=trend.change with matching measure/window. Unknown
  windows remain blocked; a required placeholder month is not permission to execute.
  Long-term mean is not a previous-period comparison. Pairwise venue results are not
  per-entity nearest_venue distances; unsupported pairwise requests have a null metric.

These are canonical interpretation conventions, not a new executor or schema algebra.
Older v5/v6 versions and all legacy freeze pins remain untouched.

The clock-schema addendum in the audit repairs the misleading RFC3339 `format: time`
annotation for v7 local clocks. Generated schemas now advertise an explicit offset-free
HH:MM:SS[.microseconds] pattern. Native output and API documentation agree with the
unchanged local-time validators; no timezone or new temporal capability is introduced.

### Internal proposal canonicalization

The v13 NativeOutput adapter validates a closed proposal using the exact public field
constraints and nested validators before applying deterministic normal forms. Non-taxonomy
intents clear taxonomy; taxonomy discovery clears grouping, metric and metric_filter;
taxonomy-dimensional rank uses entity=event independently of its count metric. Objects
reserved for anomaly/trend are null for other intents; relation is null for intents that
cannot carry it. All unchanged public plan cross-field validators then run, followed by
original-query equality at the client/API boundary. Unknown enums, extra fields and invalid
nested objects are rejected even if the field would otherwise be neutralized.

This adapter neither guesses intent nor invents operands, filters, names, clarifications
or capabilities. It preserves the declared unsupported state. The public JSON schema and
NativeOutput schema are unchanged. There is still one model call and no repair/retry loop.
