# Verified uranus-admin baseline

Read-only analysis on 2026-09-29 against freshly fetched main
`2ef188b9e685253d57c5760bbbd951762fbbf673`. Planner repository base:
`ad00ff8e9ef887ee30d348d5b998076b9258a515` (license only).

[PR #152](https://github.com/sndcds/uranus-admin/pull/152) was **merged** at
2026-09-29 13:31:42 UTC; its merge commit is the main SHA above. No unmerged PR is
assumed. Source links below are pinned to that commit.

## Backend and authority

[`services/semantic_search.py`](https://github.com/sndcds/uranus-admin/blob/2ef188b9e685253d57c5760bbbd951762fbbf673/backend/app/services/semantic_search.py)
uses fixed `jina-v3`, an eight-second total budget and Qdrant top 50. It embeds the
full free-text query, applies selected area IDs and genre keys at retrieval, groups
validated candidates, then acquires a PostgreSQL reader. The database is authoritative;
the vector payload does not establish public eligibility. Semantic search is event-only.

[`repositories/research.py`](https://github.com/sndcds/uranus-admin/blob/2ef188b9e685253d57c5760bbbd951762fbbf673/backend/app/repositories/research.py)
implements public projections, effective occurrence venue/space inheritance, date,
status, city, category, organization and venue filters. Spatial eligibility uses an
effective venue point with `ST_Covers` and the Research Area geometry. A textual
mention of Glücksburg cannot replace a missing point. Classic pagination has a
PostgreSQL count. Monthly activity and usage count distinct event UUIDs and group by
venue, organization and category. There is no general natural-language executor.

[`repositories/research_areas.py`](https://github.com/sndcds/uranus-admin/blob/2ef188b9e685253d57c5760bbbd951762fbbf673/backend/app/repositories/research_areas.py)
reads `admin.research_area`; selected multiple areas are unioned. Selection already
checks area/filter identity consistency. A name-to-reference resolver with explicit
exact/ambiguous/unresolved outcomes still needs to be built in the admin follow-up.

[`repositories/entity_search.py`](https://github.com/sndcds/uranus-admin/blob/2ef188b9e685253d57c5760bbbd951762fbbf673/backend/app/repositories/entity_search.py)
includes admin-only search surfaces (including contact data). Research builds a
restricted projection in `research.py::search_sql`, removing private search fields.
A new name resolver must use public names/metadata, never generic admin autocomplete
or UUID/email search as an existence oracle.

[`repositories/vector_events.py`](https://github.com/sndcds/uranus-admin/blob/2ef188b9e685253d57c5760bbbd951762fbbf673/backend/app/repositories/vector_events.py)
already extracts public occurrences, area membership, genre keys and evidence contexts.
[`research/semantic_contracts.py`](https://github.com/sndcds/uranus-admin/blob/2ef188b9e685253d57c5760bbbd951762fbbf673/backend/app/research/semantic_contracts.py)
and `semantic_evidence.py` validate identity, chunk and occurrence context.
`contextualize_event_hit` selects valid evidence after database occurrence selection;
results are reranked and limited only after this check. `semantic_explanations.py`
builds explanations from that evidence. **Occurrence-aware evidence is on main.**

`research/vector_transport.py` provides fixed-origin internal HTTP with credentials,
timeouts, disabled redirects/environment proxies and bounded bodies. Qdrant search
accepts area/genre filters. Venue, organization and dates are not all implemented as
Qdrant query filters; the admin executor must keep them authoritative in PostgreSQL
and document any retrieval recall limitation rather than claiming identical support.

## Routes, authorization and diagnostics

[`api/research.py`](https://github.com/sndcds/uranus-admin/blob/2ef188b9e685253d57c5760bbbd951762fbbf673/backend/app/api/research.py)
requires `get_current_research_user` (system administrator or journalist), independently
of Operations. Existing routes include classic search, semantic search, export,
options, public entities and areas. There is no `POST /api/v1/research/query` yet.
The internal planner service key must never substitute for these user permissions.

The live semantic path logs `embedding_ms`, `qdrant_ms`, `retrieval_ms`,
`postgres_rehydrate_ms`, `candidate_count`, `returned_count`, `total_ms`, `error_type`.
Candidate and returned counts distinguish retrieval from final output only coarsely;
separate PostgreSQL-eligible/context-valid funnel counters were not found on this main.
There is no planner diagnostic integration.
Index metadata diagnostics in `vector_diagnostics.py` concern payload differences,
not the search funnel. A complete per-stage funnel must be added in the admin PR.

## Frontend and tests

[`ResearchSearch.vue`](https://github.com/sndcds/uranus-admin/blob/2ef188b9e685253d57c5760bbbd951762fbbf673/frontend/app/components/ResearchSearch.vue)
and the Research page have classic and experimental semantic modes.
`admin-api.ts`, shared Zod contracts and the Nitro allowlist enforce the HTTP boundary.
`ResearchSemanticExplanation.vue` shows “Warum passt das?”, the matched aspect,
public supporting text and similarity (not a calibrated probability).
The new natural-language UI belongs in the separate admin PR, together with all
Pydantic/Zod/proxy/OpenAPI contract updates.

Existing `test_research.py` and `test_semantic_search.py` cover public projections,
permissions, area filters, invalid payloads, context-aware evidence and reranking.
They are reference material here, not rerun or claimed as validation of this new
repository. The service cannot prove the Glücksburg/Harrislee/Flensburg database
regression until admin integration tests exercise real repository filters.
