# Additive domain planning contract v4

Existing `POST /plan` keeps `research-query-plan-v3`, the `research-planner-v6`
prompt, its response, and its provider output mode. `POST /v4/plan` accepts the same
bounded, authenticated `PlanRequest` and now performs real model inference. It
returns `research-query-plan-v4` with `original_query`,
`interpreter_version=research-domain-planner-v2` and a discriminated `plan`.
The original question is preserved exactly by the server.

## Interpretation and trust

`DomainPlanner.interpret()` calls `StructuredModelClient.plan_v4()`. Both versions
reuse the configured `Settings`, one SDK client and HTTP transport, endpoint
allowlist, authentication, generation settings, timeout and shared concurrency
semaphore. Production's configured `provider=openai`, `model=gpt-5.6-terra` is used
without a hard-coded model or key. V4 always uses native strict JSON Schema, even
if the legacy v3 output mode is `json_object`. Its separate model adapter applies
PydanticAI's strict schema transformer; the v3 adapter and request schema stay
unchanged. This is request-schema preparation, never response repair.

The versioned prompt lives in `src/research_planner/domain_prompts.py`. The provider
receives only that prompt, the schema, the question and its language hint. It receives
no database rows, indexed evidence, credentials in the prompt, or retrieval tools.
The question is untrusted data. German, English and Danish paraphrases are interpreted
by meaning, not an exact catalogue or regex matcher.

The provider-only `DomainProposal` is `{ "plan": DataPlan | KnowledgePlan | null }`.
Null explicitly means unsupported and becomes HTTP 422 `planner_unsupported_plan`;
it never appears as a successful public plan. Malformed JSON, omitted fields, extra
keys, unknown enums, incompatible metrics, unsupported area combinations, changed
knowledge queries and invalid types become HTTP 502 `planner_invalid_response`.
Transport/provider availability failures and deadlines remain safe HTTP 503
`planner_unavailable`. There are no retries, repairs, enum substitutions, prose
extraction, fallback guesses or clamped limits. Pydantic validates inference, and
`DomainPlanner` revalidates the proposal and final envelope, including injected
provider results. Provider refusal/truncation is an invalid response, not a 422.

Data facts are computed later by Admin from PostgreSQL/PostGIS. Only these pairs
are executable and taught as supported:

| Entity | Metric |
| --- | --- |
| event | description_characters |
| event | occurrence_count |
| organization | event_count |
| organization | venue_count |
| venue | occurrence_count |
| category | event_count |

Data plans use `operation=rank`, `ordering=asc|desc`, limit 1–20 (default intent 1)
and optional unresolved `area_query`. Only organization/event_count supports area
constraints. The prompt requires preservation of place names and rejects unsupported
geography, time, radius, filters, ambiguous metrics, multiple intents and limits
outside 1–20. It must never replace category diversity with event count or drop a
constraint. Reserved `METRICS` remain documentation of future ideas, outside the
provider schema. Pydantic checks the six compatible pairs again after inference.

Project plans use `domain=project_knowledge`, `operation=evidence_answer`,
`answer_mode=evidence` and exactly one of the eleven reviewed `FactKey` values.
`knowledge_query` must be the exact original question, checked after inference,
so the model cannot add invented facts or source selectors. It remains untrusted
retrieval text; the downstream service must not interpret it as instructions or
infrastructure configuration. Unknown project facts are unsupported in this PR.
The planner never returns factual answers. A fact intent can ask which repository
implements semantic search or which embedding model is used; the answer and source
selection belong exclusively to the downstream evidence service.

Requests for SQL, credentials, arbitrary repositories, URLs, collections, paths,
models or graph relations are unsupported, including mixed injection attempts.
There are no output fields that select infrastructure. As with any semantic model,
a schema-valid but semantically wrong interpretation cannot be ruled out by schema
validation alone; held-out live acceptance is the language-quality gate.

## Golden fixtures and acceptance

`tests/fixtures/domain_queries.json` preserves all **53** original `DATA_QUESTIONS`
and `KNOWLEDGE_QUESTIONS` examples as golden fixtures. Production imports none of
them. The corpus contains **115** cases: 53 original examples, 35 held-out
paraphrases/variants and 27 unsupported, ambiguous or security cases across DE/EN/DA.
It covers all six metrics, all eleven fact keys, singular/plural wording, limits,
asc/desc and area names. Held-out full questions never occur verbatim in the prompt.
Knowledge fixture retrieval text is now the exact question rather than a
catalogue-supplied retrieval phrase containing assumed facts such as a model name.

Normal CI uses mocked HTTP responses through the real configured client for all
three provider policies. These tests prove contract enforcement, exact structured
output schema, minimal request context, authentication, shared admission limits,
timeouts, error mapping, no repair/retries and original-query preservation. They do
**not** establish Terra's semantic accuracy. The existing v3 suite remains required.

For optional live Terra acceptance, use the existing protected operator environment
from [deployment](deployment.md), with its existing service/model credentials. Do
not copy credentials into commands, reports, fixtures or the repository. Confirm
that it selects OpenAI `gpt-5.6-terra`, native schema output, and the approved timeout
and token policy. Run only the v4 file to avoid unintentionally running other live
suites:

```sh
# Real, billable inference. Run only in the configured protected operator environment.
RESEARCH_PLANNER_LIVE_TEST=1 uv run pytest -q tests/test_domain_live.py \
  --junitxml=/tmp/planner-domain-v4-terra-acceptance.xml
```

All 115 cases must pass: exact full plans for supported questions, and specifically
422 `planner_unsupported_plan` for unsupported questions. Invalid responses and
unavailability do not count as successful rejection. Record the commit, configured
provider/model, prompt version, settings and pass/fail counts. This PR does not run
live inference or claim a live Terra acceptance result.

## Coordinated Admin mirror and migration

Before enabling Admin PR #161 against this branch, mirror:

- `interpreter_version` literal: `reviewed-catalogue-v1` → `research-domain-planner-v2`.
- `DataPlan` entity/metric enums narrowed to the executable vocabulary; retain the
  six-pair validator and enforce area only for organization/event_count.
- `FactKey`: remove `unknown`; retain the eleven reviewed facts.
- Nonblank `knowledge_query`, with exact original-question retrieval semantics.
- Safe handling of 422 unsupported, 502 invalid response and 503 unavailable.

The public envelope retains its field names and non-null discriminated plan.
`DomainProposal` is provider-internal and must not be mirrored into Admin's public
contract. OpenAPI is regenerated in `docs/openapi.json`.

Diagnostics are deferred to a coordinated follow-up with Admin #161. Adding model,
prompt version, request ID and timings would require a new shared diagnostics
contract; no partial or incompatible fields are introduced here. Prompt text,
provider response, reasoning and credentials must never be exposed.

Admin alone routes validated plans to exact PostgreSQL execution or authenticated
project evidence retrieval. The encoder contract is unchanged. Reviewed sources
and graph vocabulary live in
[uranus-research-knowledge](https://github.com/sndcds/uranus-research-knowledge).
No Admin or knowledge repository changes, endpoint switch, deployment or merge are
included. Keep the existing draft PR #12 and coordinate the mirror in Admin #161.
