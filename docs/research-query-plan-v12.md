# Combined Research contract v12 / prompt v18

Audited main: Planner `5f7313f`; Admin `adca790`. The next reserved pair is
`research-query-plan-v12` / `research-planner-v18`, served by `POST /v12/plan`.

| Schema / prompt | Capability |
| --- | --- |
| v8 / v14 | Administrative geography |
| v9 / v15 | Ordered multidimensional grouping |
| v10 / v16 | Recurring weekdays/months and concrete single-month reference-year default |
| v11 / v17 | Bounded conversational context |
| v12 / v18 | Combined modern contract with administrative geography |

V9 branched from the broad v7 algebra rather than v8. Its scalar spatial object
omitted `area_level` and v8's bounded spatial list. V10 and v11 inherited that
representation, so their normalizer could only create an administrative reference
with an unknown expected level. Display-label matches could then include
municipalities whose labels mention their containing district.

V12 keeps every v11 field and ordered grouping/calendar behavior, replacing only
`spatial` with a required array of zero to four predicates. A named administrative
predicate has `relation=inside|outside`, `reference=named`, `area_query`, and
`area_level=municipality|district|state|country|region|null`. Other place, radius,
border and user-location meanings retain v8's spatial validation; places and user
location cannot receive an administrative level. Several spatial predicates are
allowed only for named administrative membership and are combined with AND.
There is no Boolean DSL. Unsupported combinations remain explicitly unsupported.

The level is a **semantic expectation, not authoritative geographic truth**.
Planner understands wording; Admin/geocoder resolves identity; PostGIS executes
membership. No AGS/OSM/ISO/district/parent IDs, coordinates or geometry are generated.
“im Kreis Schleswig” retains lexical `Schleswig` and `district`; Planner does not
invent the official name Schleswig-Flensburg.

Examples covered by coordinated fixtures:

- Kreis Schleswig-Flensburg → district; Bundesland Schleswig-Holstein → state;
  Gemeinde Harrislee → municipality; Deutschland → country; Norddeutschland → region.
- “Veranstaltungen am Wochenende im Kreis Schleswig” → recurring weekdays `[6,7]`
  plus inside district Schleswig, without concrete dates.
- July–September strength in Schleswig-Holstein → recurring months `[7,8,9]`
  plus state membership; explicit year still produces an explicit date range.
- A concrete October with reference year 2026 → October 1–31, no `needs_date`;
  January stays in 2026. Explicit years override; “jeden Oktober” remains recurring.
- Event type × month, event type × weekday and category × municipality retain their
  ordered dimensions alongside administrative filters.
- Outside Schleswig-Holstein AND inside Deutschland retains both predicates.

The v12 request uses a separate typed conversation model. It retains four summaries,
2048 bytes per summary and 8192 total; current wording and exact `original_query`
rules remain authoritative. Summary areas now contain `name`, `relation` and
`expected_level`, with at most four AND areas. “Und nur sonntags?” can retain a
previous district and replace the weekday restriction. No raw transcript, results,
answer prose, SQL/parameters, IDs, location coordinates, scores or user identity
enter summaries. References to actual result identities still need `needs_context`.
The v11 request/response models and endpoint remain unchanged.

Admin adapts v12 to `InternalResearchPlan`, retaining each expectation in
`UnresolvedAdministrativeAreaRef`. Existing cached candidates are filtered by
expected level before ranking/LIMIT, and loaded authoritative boundary metadata is
checked again. The common resolver, executor, grouping and SQL-provenance paths
remain responsible for execution. No version-specific executor is introduced.

Validation combines mocked native-model/HTTP contract tests with real isolated
PostgreSQL/PostGIS tests in Admin. Shared fixtures demonstrate the wire contract,
not live-model language accuracy. The Kreis Schleswig regression tests zero, one
and multiple districts, excluding Ahneby, Arnis, Ausacker, Bollingstedt and Boren
whose display labels mention Kreis Schleswig-Flensburg. Wrong loaded levels cannot
execute. Older version tests remain part of the regression gates.

Live language acceptance is opt-in: run
`RESEARCH_PLANNER_LIVE_TEST=1 uv run pytest tests/test_research_v12_live.py`
with an explicitly configured model provider. The shared modern examples cover all five
levels, calendar/grouping composition, inherited context and result references;
additional seasonal fixtures include the production question
“Welche Veranstaltungstypen treten saisonal besonders stark auf?” and DE/DA/EN variants.

This seasonal question means `aggregate/event`, `occurrence_count`, ordered grouping
`[event_type,month]`, descending order and limit 20. It describes an occurrence
distribution, not a statistical seasonality score, anomaly or global type ranking.
Count metrics require `measure=null` and `window=null`; month belongs in grouping.
With no time restriction the valid representation is `temporal=null`, not an empty
temporal object. Thus no concrete year/date or recurring-month subset is invented.
Genres use `[genre,month]`. Specific Sunday/October restrictions keep their recurring
sets and only the subject grouping unless a distribution is requested. Explicit years
and concrete single-month reference-year rules remain unchanged. The v12 validators,
schema/prompt version identifiers and external invalid-response envelope are unchanged.

Rollout is coordinated: install compatible Planner and Admin, run provider language
acceptance, then explicitly select `RESEARCH_PLANNER_CONTRACT=v12` in Admin. Keep
`legacy`, `v9`, `v10`, `v11` available. No automatic retries or fallback. A v12 summary
containing level expectations cannot be silently sent to v11; reset the conversation
when rolling back. There is no migration or automatic production activation.

Limitations: lexical/historic ambiguity and boundary availability remain resolver
concerns. A requested level never proves identity or parentage. Mixed spatial
compositions and additional executability limitations still fail explicitly at the
shared capability gate. Unsupported district/state grouping or other new execution
families are not inferred merely because a district/state filter is representable.
