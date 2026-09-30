# Instruction model decision

Assessment date: 2026-09-29. These are candidates, not locally benchmarked winners.
No model is installed by this PR and no production service is changed.

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

The 35 reviewed fixtures (previously 30) contain complete golden plans, including
five explicit entity-versus-filter cases, dates, comparisons, privacy/injection,
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
