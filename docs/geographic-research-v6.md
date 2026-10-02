# Geographic Research v6

`POST /v6/plan` accepts the same closed query/timezone/language request as v5.
It is protected by the same Bearer authentication, request-size, JSON, deadline and
concurrency boundaries. Responses identify `research-query-plan-v6` and
`research-planner-v11`. Existing `/plan`, `/v4/plan` and `/v5/plan` remain frozen.

`GeographicQueryPlan` extends the analytical schema with two required fields:

- `place_query: Slot | null`: named street/square/local place, e.g. Bachstraße Flensburg,
  Nordermarkt, Südermarkt, Museumsberg, Flensburger Hafen, Am Nordertor 2.
- `location_relation: none | nearby`: deictic user-location requirement. Nearby plans
  have `clarification=needs_location`, preserve time/taxonomy/other filters, and leave
  `place_query`, `area_query` and `venue_query` empty. Admin satisfies this requirement
  from existing browser context before execution; coordinates never reach the planner.

Flensburg/Schleswig-Holstein/Hamburg remain area queries, while
Volksbad/Kühlhaus/Aktivitetshuset remain venue queries. “Wo finden heute Veranstaltungen
statt?” is list/event/records with today and no location query or clarification;
without “heute”, temporal is none. `wo / where / hvor` alone never implies location
permission. `hier`, `bei mir`, `in meiner Nähe`, `near me`, `around me`, `her` and
`i nærheden` explicitly refer to the user's location.

Admin owns geocoder lookup, candidate ambiguity and PostgreSQL/PostGIS eligibility.
There are no geocoder keys, tools, source lookups, IDs, coordinates or SQL generation in
this planner. Deploy this endpoint before enabling the Admin geocoder key; there is no
fallback to an older contract when geographic planning fails.

`tests/fixtures/geography.json` and `tests/test_geography.py` cover the reviewed examples,
full schema/native model-output wiring and authenticated endpoint boundaries. They use
mocked inference and do not claim acceptance of a deployed model. The Admin copy of the
JSON Schema and reviewed fixture corpus must remain identical for each contract version.
