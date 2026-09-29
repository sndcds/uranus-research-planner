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

The 30 reviewed fixtures include all 15 required German questions plus dates,
comparison, privacy/injection, Danish and English examples. Normal tests mock their
outputs. Opt-in live tests compare critical structured slots and semantic presence;
they are an initial smoke gate, not a complete semantic-quality benchmark. Add
unseen paraphrases, typos, ambiguous names, negation, multi-clause constraints and
more Danish before enabling the UI. Measure invalid-plan rate, exact slot accuracy,
inappropriate clarification and silent condition loss; do not replace those metrics
with an LLM-provided confidence score.

No Jina intent classifier: one more classifier still cannot produce all bounded
slots, comparison targets and temporal structure. Jina v3 remains retrieval-only.
