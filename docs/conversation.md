# Additive conversational request: v11

Baseline main `3d6d005`: v10 represented recurring weekday/month filters but its
closed request did not accept semantic conversation context. Changing that deployed
request silently would cause version skew, so `/v11/plan` is additive.

- Envelope: `research-query-plan-v11`, exact prompt `research-planner-v17`.
- Output semantics inherit v10; all previous endpoints/prompts remain unchanged.
- Optional `conversation_context.previous_turns`: 1–4 semantic summaries.
- Per-summary limit 2048 UTF-8 JSON bytes; total context 8192 bytes; the existing
  16KiB HTTP body ceiling still applies (including query/envelope).
- Names 160 characters, dimensions 3, filter lists 8, weekdays 7, months 12,
  one administrative area predicate. Extra fields/duplicates are rejected.

Summaries are advisory, untrusted input: intent, entity, metric, groupings,
ordering/limit, calendar semantics, non-sensitive name filters/area and semantic
concept. They contain no query transcript, SQL, source IDs, results, descriptions,
coordinates, geometry, identity or preferences. Admin generates summaries only for
fully representable successful plans; runtime location stays outside this contract.

The current `query` remains exact in `original_query`. Context can resolve ellipsis
without changing the query string. Explicit current wording overrides inherited
semantics; standalone questions are independent. Missing or ambiguous context gives
`needs_context`. Result-identity references are not supported: there is no visible
result-reference inventory, so “which of those” cannot select guessed entities.

One native structured model request, strict schema, no tools/retries/fallback.
No execution or history persistence is introduced. Calendar SQL remains in Admin.
Mocked native-boundary tests are not live-model acceptance evidence: evaluate
follow-up interpretation against the deployed model before enabling Admin's
`RESEARCH_PLANNER_CONTRACT=v11`. Admin defaults remain unchanged.
