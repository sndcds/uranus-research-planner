# Instruction model decision

Assessment date: 2026-09-29. These are candidates, not locally benchmarked winners.
No model is installed by this repository and no production service is changed.
The local-model assessment below is historical; see the hosted-provider section
for the subsequently added Groq and OpenAI options.

The inspected admin documentation describes an AMD64 **CPU** AI host, with existing
budgets of two CPUs/5 GiB for the encoder and two CPUs/2 GiB for Qdrant. It does not
establish free host RAM, a GPU or spare capacity for a generative model. A planner
requires a separate resource budget; it must not displace the working encoder.

| Candidate | Relevant technical properties | Limits / decision |
| --- | --- | --- |
| `Qwen/Qwen3-4B-Instruct-2507` | 4B, non-thinking instruction model, Apache-2.0, multilingual; native context 262,144, but serve only 8192 here | First candidate: moderate weights, no thinking mode required; German/Danish/English slot accuracy still needs local evaluation |
| `Qwen/Qwen2.5-7B-Instruct` | 7B, Apache-2.0, multilingual including German/English; model card specifically discusses JSON output | Larger memory and generation cost; Danish suitability is not established by the card's short language list; compare only if 4B slot accuracy is insufficient |
| `google/gemma-3-4b-it` | 4B instruction model, multilingual, text use possible; Gemma terms rather than Apache-2.0 | Reasonable comparison candidate; additional model-family/template and license review cost, no demonstrated advantage for this workload yet |

Sources: [Qwen3 model card](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507),
[Qwen2.5 model card](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct),
[Gemma model card](https://huggingface.co/google/gemma-3-4b-it).
Published general benchmarks are not a measurement of our planner's hallucination
rate or Danish entity extraction. No numerical confidence or accuracy claim is made.

## Serving and sizing

Use an independently managed local server with `/v1/chat/completions`, native
`response_format.type=json_schema` support and `/v1/models`. `llama.cpp` is the CPU
candidate; vLLM is an alternative on provisioned GPU hardware. See
[llama.cpp server documentation](https://github.com/ggml-org/llama.cpp/tree/master/tools/server)
and [vLLM structured outputs](https://docs.vllm.ai/en/latest/features/structured_outputs/).
Schema support is a serving-engine property as well as a model behavior; verify the
exact pinned build handles our schema with nested objects, nulls, enums and lists.
Pydantic validation remains mandatory even with grammar-constrained output.

Starting estimates (not measurements): 4B at four-bit quantization has approximately
2 GB of raw quantized weights before metadata/runtime/KV cache. Budget roughly
6–8 GiB RAM for a CPU pilot at an 8192-token context and one generation slot; 7B
may need roughly 8–12 GiB. Actual GGUF format, embeddings, KV precision and backend
change these numbers. GPU memory must similarly include KV and runtime overhead;
do not infer GPU availability from these estimates. Prefer Q4_K_M as an evaluation
candidate, compare against Q5 or higher precision for slot/date regressions.

Pin model revision, GGUF SHA-256, chat template, server build/image digest and alias
in the deployment manifest before rollout. The service's configured model alias is
fixed and must equal the returned completion model ID. Never use auto-routing.
Pre-provision weights separately; production startup should have no download path.

## Latency and acceptance gate

Planner <1–2 seconds is a **target**, not demonstrated CPU performance. Prompt plus
schema and up to 1200 output tokens may take materially longer on a shared two-core
CPU allocation. The eight-second default is a fail-closed budget, not a latency
claim. Warm up the model, measure p50/p95 and saturation with 1/2 concurrent calls,
and observe encoder/Qdrant contention. Increase hardware or simplify the measured
prompt before relaxing deadlines. Native output avoids long reasoning sequences.

The 37 reviewed fixtures (30 initially, 35 after PR #2) contain complete golden
plans, including five explicit entity-versus-filter cases, dates, comparisons, privacy/injection,
Danish and English examples. Normal tests mock their outputs. Opt-in live tests
compare every field, including null/none/empty values, against the full golden plan.
Only `semantic_query` uses case-insensitive comparison (`casefold`); its entire
content must match. All other fields, including names, original_query and
semantic_focus, remain exact. No trimming, paraphrase matching, or presence-only
semantic check is performed. This is an acceptance gate, not a complete language
benchmark; legitimate paraphrases may fail and require reviewed fixtures. Add
unseen paraphrases, typos, ambiguous names, negation, multi-clause constraints and
more Danish before enabling the UI. Measure invalid-plan rate, exact slot accuracy,
inappropriate clarification and silent condition loss; do not replace those metrics
with an LLM-provided confidence score.

No Jina intent classifier: one more classifier still cannot produce all bounded
slots, comparison targets and temporal structure. Jina v3 remains retrieval-only.

## Small-model structured-output correction (2026-09-30)

The operator's Qwen3-4B-Instruct-2507 / llama.cpp / Q4_K_M live run for
“Wie viele Veranstaltungen waren im Kühlhaus?” correctly produced `count`,
`venue_query=Kühlhaus`, `temporal=past` and `metric=event_count`, but used
`entity_type=venue`, invented eleven fields, emitted null for `group_by`,
`time_of_day` and `clarification`, and omitted `semantic_focus`. Rejecting that
output with 502 was correct. The change improves the prompt/schema interface;
it does not establish that Qwen now passes live acceptance.

Small instruction models need schema-friendly output contracts and a concrete
complete example. Prompt v2 starts with output rules and a 21-field golden JSON,
then explains intent, requested entity versus filters, residual semantics, time,
comparison and safety. Long lists resembling additional fields were removed.
The unspecified “welcher ort ist besser?” fixture now explicitly requests `venue`
with `needs_criteria`; its old `event` value was inherited from test defaults.

Before/after measurement of `SYSTEM_PROMPT` alone (schema, user message and chat
template excluded): 6,764 → 6,553 characters; approximately 1,691 → 1,638 tokens
using `round(characters / 4)`. This is a rough consistent estimate, **not** a Qwen
tokenizer measurement or proof of lower CPU latency. No tokenizer/model was
installed; the operator must measure actual prompt tokens and p50/p95 latency.

### Schema audit and validation boundary

The actual `ResearchQueryPlan.model_json_schema()` was inspected before editing:

| Property | Before | After |
| --- | --- | --- |
| Required plan fields | All 21, no defaults | Unchanged |
| Closed objects | `additionalProperties: false`, including ComparisonTarget | Unchanged |
| Nullable fields | Eight `anyOf` unions with null, including unsupported_reason | Unchanged |
| Unused enums | Literal `"none"` for temporal/time_of_day/metric/group_by/clarification | Unchanged |
| Query / Slot / Topic | `minLength: 1`, max 2000 / 160 / 500, `pattern: "\\S"` | Same lengths; nonblank check in Pydantic AfterValidator |
| Arrays | Typed items; category/genre max 8, comparison max 4 | Unchanged |

The plan-schema diff is exclusively removal of `pattern`. The OpenAPI snapshot
also records prompt metadata v2; the plan schema version remains v1.

The observed `pattern \S is not supported` warning comes from converting a regex
outside llama.cpp's supported subset: this pattern is not anchored. The upstream
[grammar documentation](https://github.com/ggml-org/llama.cpp/blob/master/grammars/README.md)
requires `^...$` patterns and documents incomplete JSON Schema support. Grammar
can constrain required properties, closed objects, enums, typed arrays, nullable
alternatives and length bounds. Actual support must be checked on the pinned build.
It does not establish the meaning of a question or execute Pydantic validators.

Pydantic remains the final validation boundary for **all** constraints, especially
whitespace-only text, real calendar dates, ordered ranges, matching entity/metric
and intent/answer mode, semantic dependencies, distinct comparison targets and
other cross-field rules. The shared validator checks `value.strip()` but returns
the original value unchanged. It covers request queries, plan slots, list items
and comparison queries. No extra keys are ignored, missing fields filled, null
enums converted, or wrong entities repaired.

`json_schema` remains the preferred default. `json_object` is an explicit
operator-selected fallback/test mode with identical final validation; schema
rejection never triggers an automatic downgrade. The planner receives no live
PostgreSQL/Qdrant data or venue/area/organization lookups. Name existence and
resolution remain the responsibility of uranus-admin.

## Temporal and list intent correction after PR #2

The operator ran the five critical Qwen3-4B-Instruct-2507 / llama.cpp tests in
json_schema mode with prompt v2: **3 passed, 2 failed**. The venue count question
“Wie viele Veranstaltungsorte gibt es in Flensburg?” had the correct count,
venue entity, Flensburg filter and venue_count metric, but temporal=past.
“Welche Organisationen gibt es in Glücksburg?” had the correct organization,
Glücksburg filter and null semantic_query, but intent=search instead of list.

Prompt **research-planner-v2 → research-planner-v3** explicitly contrasts present
“gibt es” with past “gab es”, defaults to temporal=none without a time reference,
and distinguishes structured record listing from search with a semantic residual.
The existing complete golden plans remain unchanged; two additional past-tense
fixtures cover venue counts and organization listings, bringing the corpus to 37.

The source, documented semantics and all 35 existing fixtures were audited before
adding the consistency rule: all six search fixtures already have semantic text,
including the needs_location clarification. No legitimate search-without-residual
case was found. Pydantic now rejects it with `search_requires_semantic_query`;
the model client reports planner_invalid_response (502), without retry or changing
search to list. List with null remains valid; list with a semantic residual also
remains valid, preserving the existing downstream rule not to discard conditions.

**research-query-plan-v1 is retained:** fields, requiredness, types, enum values,
JSON Schema and valid intended interpretations are unchanged. Validation is
intentionally stricter for a previously accepted inconsistent combination. This
is a semantic consistency bug fix, not a new wire representation; consumers must
still handle the existing invalid-response error. OpenAPI changes only for prompt
version metadata. JSON Schema grammar alone cannot enforce the new validator.

A grammatically valid past plan for a present-tense question can still pass
Pydantic; the complete golden comparison detects that interpretation error.
There is no query-text heuristic or temporal repair. Tests simulate both reported
outputs in both modes and verify rejection or unchanged output as appropriate.
No database/lookups, live model calls or deployments are part of this fix.

The operator must first rerun the same five cases with v3, requiring **5 passed**,
then run all 37 fixtures. See the [manual acceptance commands](../deployment.md#manual-model-acceptance-after-merge).
That result has not yet been measured; offline tests do not establish Qwen accuracy.


## Allowlisted hosted inference: Groq

Local Qwen has been reported too slow on the available AWS host. Groq is an
additional operator-selected inference option using the existing OpenAI-compatible
client, not a planner rewrite. The initial example is `openai/gpt-oss-20b` at
`https://api.groq.com/openai/v1`; MODEL remains configurable. Local llama.cpp remains
supported and the default provider is internal. No automatic provider failover exists.

Groq documents [OpenAI-compatible API access](https://console.groq.com/docs/openai)
and [strict JSON Schema output](https://console.groq.com/docs/structured-outputs)
for GPT-OSS 20B/120B. That supports retaining AsyncOpenAI, OpenAIChatModel,
OpenAIProvider and NativeOutput(strict=True), without a Groq SDK dependency.
Our complete schema and actual planning accuracy still require operator acceptance;
provider marketing guarantees do not replace Pydantic or the 37 golden plans.

The [Groq reasoning documentation](https://console.groq.com/docs/reasoning) states
that GPT-OSS returns a separate reasoning field by default and accepts
`include_reasoning=false` to suppress it. The endpoint adapter sends that documented
option only for Groq's `openai/gpt-oss-20b` and `openai/gpt-oss-120b`, through
PydanticAI's extra_body setting. Other configured models receive no model-specific
option. Returned reasoning is still rejected, never stripped or exposed.

Low/medium/high reasoning effort is documented for these models, and the installed
PydanticAI adapter supports openai_reasoning_effort. This first integration deliberately
leaves effort unset: no latency/accuracy tradeoff has been benchmarked, and other
models have different supported settings. Suppressing returned reasoning does not
disable internal reasoning or its token cost. Token/deadline exhaustion remains a
failure, without retries, enlarged budgets or a switch to another model/output mode.

External inference sends query text and planning context to Groq, using a server-only
provider key. No database, area, venue, organization or Qdrant data is added. Only
the exact allowlisted endpoint is permitted; arbitrary public URLs remain forbidden.
Internal numeric-IP restrictions are unchanged. Public API/schema v1 and prompt v3
are unchanged because provider selection changes no planner semantics.

Use the [deployment acceptance and comparison workflow](../deployment.md#manual-provider-comparison)
to record planner_ms, total_ms, pass/fail, invalid-plan rate, exact golden match,
model/prompt/output mode and token usage when available. First require 5 critical
passes, then run all 37 cases. No live Groq calls, latency measurements or acceptance
results are claimed by this implementation; all provider tests use mocked HTTP.

## Allowlisted hosted inference: OpenAI

OpenAI is a third explicit provider using the same AsyncOpenAI, OpenAIChatModel,
OpenAIProvider and NativeOutput(ResearchQueryPlan, strict=True) integration. Set
MODEL_PROVIDER=openai and exactly MODEL_BASE_URL=https://api.openai.com/v1.
The initial evaluation model is `gpt-5.6-luna`; MODEL remains operator-configurable.
The [official Luna model documentation](https://developers.openai.com/api/docs/models/gpt-5.6-luna)
lists Chat Completions and structured-output support. This is not evidence of
accuracy on our planner fixtures or compatibility with every current request option.

No OpenAI-specific reasoning setting is introduced. Groq's `include_reasoning=false`
remains restricted to Groq GPT-OSS; OpenAI receives neither that field nor
`reasoning_effort`/`reasoning_format`. Temperature, token bounds and response checks
remain unchanged. Any returned reasoning, truncation, model-ID mismatch or invalid
plan still fails closed, without retries, repair, fallback or an output-mode downgrade.
The public API, research-query-plan-v1, research-planner-v3 and 37 golden plans are
unchanged. Local llama.cpp and Groq remain supported.

OpenAI receives the system prompt, user query, language/timezone, reference date
and output schema. It receives no PostgreSQL rows, Qdrant documents, resolved venue
or organization records, or arbitrary admin state. Provider keys stay server-side
and must never be delivered to browsers. Exact endpoint allowlisting and all shared
transport limits remain active; external DNS/HTTPS egress to api.openai.com must be
provisioned separately by the operator. The internal-only systemd unit is unchanged.

The operator has confirmed access to the individual model lookup endpoint. Readiness
still requires `GET https://api.openai.com/v1/models` to list the exact configured
model within the two-second deadline and 32 KiB response bound. This implementation
has not made live OpenAI requests. Listing, exact completion model IDs, native schema
acceptance, parameter compatibility, latency and planning accuracy need the
[manual acceptance procedure](../deployment.md#manual-model-acceptance-after-merge):
first require 5 critical passes, then all 37 golden plans. Use the documented
comparison workflow for latency, invalid-plan rate and exact golden match; do not
interpret mocked tests as model acceptance.
