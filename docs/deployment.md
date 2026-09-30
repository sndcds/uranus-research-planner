# Planner deployment examples (no deployment performed)

The lightweight planner API uses a separately provisioned internal model
server or the explicitly allowlisted Groq or OpenAI API. It never installs or
downloads weights.
Use the [model decision](research-ai/models.md) to evaluate the existing host first.
The repository contains examples, not verified live paths, units or capacity claims.

## Configuration

| Variable | Default / contract |
| --- | --- |
| `RESEARCH_PLANNER_MODEL_PROVIDER` | `internal`; only `internal`, `groq` or `openai`, never auto-detected |
| `RESEARCH_PLANNER_MODEL_BASE_URL` | Full API base URL; unset (with no legacy URL) disables planning |
| `RESEARCH_PLANNER_MODEL_URL` | Deprecated internal origin without `/v1`; cannot coexist with MODEL_BASE_URL or provider=groq/openai |
| `RESEARCH_PLANNER_MODEL_API_KEY` | Separate outgoing Bearer secret; 16–512 printable ASCII characters |
| `RESEARCH_PLANNER_SERVICE_API_KEY` | Incoming service Bearer secret; same bounds; never delivered to a browser |
| `RESEARCH_PLANNER_MODEL` | `Qwen/Qwen3-4B-Instruct-2507`; set `openai/gpt-oss-20b` for Groq or `gpt-5.6-luna` for OpenAI evaluation; always operator-configurable |
| `RESEARCH_PLANNER_TIMEOUT_SECONDS` | 8; allowed 0.1–30; absolute model deadline |
| `RESEARCH_PLANNER_MAX_TOKENS` | 1200; allowed 256–2048 |
| `RESEARCH_PLANNER_OUTPUT_MODE` | `json_schema`; explicit `json_object` alternative |
| `RESEARCH_PLANNER_MAX_CONCURRENT_REQUESTS` | 2; allowed 1–8; per API worker |

Run one API worker so concurrency remains globally bounded for the supplied setup.
Independent admin-client settings such as `RESEARCH_PLANNER_URL/API_KEY` belong in
the future admin PR; do not confuse those with the service's outgoing model URL/key.
Timezone comes from admin's `settings.event_timezone` in each request. There is no
user-controlled URL/model/provider or tools field in the request.

### Endpoint policy and migration

For `internal`, set MODEL_BASE_URL to `http://127.0.0.1:8091/v1` or a numeric
private HTTPS endpoint such as `https://10.0.0.1:8091/v1`. Explicit ports remain
mandatory, HTTP is loopback-only, and hostname/DNS endpoints are forbidden.
Only `/v1` (optionally one trailing slash, normalized away) is accepted. Public,
metadata/link-local and unspecified addresses are rejected. URL credentials,
escapes, query strings, fragments and other paths are rejected before normalization.

For `groq`, the only accepted base URL is exactly
`https://api.groq.com/openai/v1`. No alternate host, port (even explicit :443),
trailing slash, path, userinfo, query or fragment is accepted. Groq uses normal
DNS and verified TLS; internal endpoints still do not use DNS. This fixed external
exception is not permission to access arbitrary public HTTPS services. Future
providers require an explicit policy and tests in `endpoints.py`.

For `openai`, the only accepted base URL is exactly
`https://api.openai.com/v1`. Validation compares the original string before URL
normalization. HTTP, explicit :443 or other ports, trailing slashes, uppercase
hosts, userinfo, queries, fragments, escaped paths and lookalike hosts are rejected.
OpenAI uses DNS and verified TLS. Its fixed allowlist does not change internal or
Groq policy, and choosing a URL never selects a provider automatically.

All three providers use AsyncOpenAI, OpenAIChatModel and OpenAIProvider. The
configured base URL is passed directly to the SDK; it never appends another `/v1`. Transport
checks full destination URLs and only permits the two methods/paths below, replacing
headers with the configured Bearer credential and a small fixed header set.
`trust_env=False`, verified TLS and `follow_redirects=False` remain active, including
on the underlying HTTP transport. No retries, provider fallback, mode downgrade
or output repair exist. Provider errors and bodies are not surfaced to callers.

Existing MODEL_URL deployments continue to work **only** for the internal origin
format: `http://127.0.0.1:8091` maps to `http://127.0.0.1:8091/v1`. To migrate,
remove MODEL_URL and set MODEL_BASE_URL with `/v1`; set MODEL_PROVIDER explicitly.
Supplying both names is an error, even if equivalent. MODEL_URL with groq or openai
is an error; provider selection is never inferred from a URL. Configuration is read
from the server process environment, never from requests, prompts or browser inputs.
See [.env.example](../.env.example). Keep provider and service keys separate and
server-side; neither belongs in JavaScript, a browser response, logs or source control.
Choosing Groq or OpenAI sends the planner system prompt, user research query,
language/timezone request fields, reference date and output schema to that external
provider. It sends no PostgreSQL rows, Qdrant documents, resolved venue records,
organization records or arbitrary admin database state; there are no live lookups.

## Model server contract

- `POST <base_url>/chat/completions`: nonstreaming JSON Schema output, fixed model,
  temperature 0, max tokens. No tools/reasoning. Completion includes exactly one
  choice, assistant text containing a JSON object, `finish_reason=stop`, matching model ID.
- Authenticated `GET <base_url>/models` for readiness; the response data must list
  the exact configured model ID. Internal path: `/v1/models`; Groq path:
  `/openai/v1/models`; OpenAI URL: `https://api.openai.com/v1/models`. Deadline:
  min(configured timeout, 2 seconds). Bad/oversized responses, missing IDs, timeouts
  and redirects return readiness false; no completion
  is generated and no provider response body is exposed.
- Model server's own health endpoint may be `/health` (llama.cpp); the service checks
  model availability via the configured API base plus `/models`, not that health endpoint.
- Disable request-body, prompt, completion and credential logging on the model server
  and reverse proxy. Do not enable tracing/capture middleware around this service.

For an already installed and pinned llama.cpp build, an operator can adapt:

```sh
/opt/llama/bin/llama-server \
  --model /srv/research-models/qwen3-4b-instruct-2507-q4_k_m.gguf \
  --alias Qwen/Qwen3-4B-Instruct-2507 \
  --ctx-size 8192 --parallel 1 --threads 2 \
  --host 127.0.0.1 --port 8091 \
  --api-key-file /etc/research-planner/model-key
```

Paths and quantization filename are examples, not supplied artifacts. Review logging
flags for the exact pinned server build and avoid verbose prompt logging. Reserve a
separate memory/CPU budget before starting it. A GPU vLLM deployment can serve the
same API but must be independently sized, pinned and schema-tested.

## API service

[Systemd example](../deploy/systemd/uranus-research-planner.service) runs from a
pre-provisioned venv and reads a protected EnvironmentFile. Paths/user ownership
must be provisioned by the operator; no installer is executed here. The example
binds loopback, suppresses access logs and denies non-loopback IP traffic. For
remote hosts prefer a separately managed SSH tunnel to a loopback port. Do not
weaken the unit's network restriction silently for remote private HTTPS endpoints.
This unit is deliberately an **internal-only** network example: it blocks Groq and OpenAI.
External-provider systemd deployments need operator-provisioned service egress for
DNS and verified HTTPS to api.groq.com or api.openai.com, respectively. systemd
IPAddressAllow takes IPs/CIDRs, not a dynamic hostname policy; use the host's reviewed egress controls rather than
blindly removing `IPAddressDeny=any`. No unit or infrastructure is changed automatically.

[Dockerfile](../deploy/docker/Dockerfile) and
[Compose example](../deploy/docker/compose.yaml) build only the API. They use an
internal Docker network shared with an explicitly selected, already provisioned
model-server image, local read-only weights and a separate model-key file. Startup
does not fetch models. The planner calls that model over a shared loopback network
namespace, preserving plaintext-loopback-only policy. Image and model artifacts
must be pinned/reviewed by the operator before production use. No default model
image is chosen or downloaded by running ordinary tests.

For external inference, the separate [Groq Compose example](../deploy/docker/compose.groq.yaml)
and [OpenAI Compose example](../deploy/docker/compose.openai.yaml) run only the
planner on a normal bridge with a loopback-bound API port. Each uses a protected
provider environment file, with the provider/base pinned in the example.
The host must allow the required DNS/HTTPS egress; the application still permits
only the selected provider's exact endpoints. Do not combine either with the
internal model Compose file. No example is deployed by this PR.

Liveness: `GET /health`, no dependency calls. Readiness: authenticated `GET /ready`,
two-second limit, fixed model must be listed. Readiness does not establish JSON
Schema support, output quality or latency; run the explicit acceptance tests separately.

## Manual model acceptance after merge

These commands are for an operator after merge with provider configuration and
credentials securely supplied. They perform real model requests;
they are not run by this PR or ordinary CI. Do not install models, restart services
or change production configuration as part of the code checks.

For Groq, configure the operator shell (or a protected environment file) before
running tests. The keys below are deliberately invalid placeholders; replace them
through your secret-management workflow, not a shared shell history:

```sh
unset RESEARCH_PLANNER_MODEL_URL
export RESEARCH_PLANNER_MODEL_PROVIDER=groq
export RESEARCH_PLANNER_MODEL_BASE_URL=https://api.groq.com/openai/v1
export RESEARCH_PLANNER_MODEL_API_KEY='gsk_example_redacted'
export RESEARCH_PLANNER_SERVICE_API_KEY='service_example_redacted'
export RESEARCH_PLANNER_MODEL=openai/gpt-oss-20b
export RESEARCH_PLANNER_OUTPUT_MODE=json_schema
export RESEARCH_PLANNER_LIVE_TEST=1
```

For OpenAI, use this configuration instead. The key placeholders must be replaced
through the same secure operator workflow:

```sh
unset RESEARCH_PLANNER_MODEL_URL
export RESEARCH_PLANNER_MODEL_PROVIDER=openai
export RESEARCH_PLANNER_MODEL_BASE_URL=https://api.openai.com/v1
export RESEARCH_PLANNER_MODEL_API_KEY='sk_example_redacted'
export RESEARCH_PLANNER_SERVICE_API_KEY='service_example_redacted'
export RESEARCH_PLANNER_MODEL=gpt-5.6-luna
export RESEARCH_PLANNER_TIMEOUT_SECONDS=30
export RESEARCH_PLANNER_MAX_TOKENS=1200
export RESEARCH_PLANNER_OUTPUT_MODE=json_schema
export RESEARCH_PLANNER_MAX_CONCURRENT_REQUESTS=2
export RESEARCH_PLANNER_LIVE_TEST=1
```

OpenAI receives no Groq `include_reasoning` field and no `reasoning_effort` or
`reasoning_format`. Token limits and temperature retain the existing client behavior;
there are no speculative model-specific overrides. The operator-confirmed model
lookup does not establish list readiness, Chat Completions compatibility or golden
accuracy. Readiness must still list the exact model, and the completion's model ID
must match exactly. An alias mismatch, unsupported parameter, oversized model list
or rejected schema fails closed; investigate before any separately reviewed change.

For local Qwen, use MODEL_PROVIDER=internal, MODEL_BASE_URL=http://127.0.0.1:8091/v1,
the internal model key and MODEL=Qwen/Qwen3-4B-Instruct-2507 instead. The test file
retains its name for compatibility; it evaluates any explicitly configured provider.
Normal CI disables live inference and mocks all three providers. Never enable the live
flag merely to run the ordinary unit suite against production.

Use `RESEARCH_PLANNER_OUTPUT_MODE=json_schema` as the preferred default. Small
models need the schema-friendly contract, prompt v3 rules and complete golden
example.
llama.cpp supports only a subset of JSON Schema regex features; the plan now uses
min/max string lengths with Pydantic nonblank validation instead of `pattern=\S`.
Inspect the pinned server's schema conversion warnings. Pydantic remains the
final boundary; invalid output is never automatically repaired. `json_object`
is only an explicitly selected diagnostic alternative, with no automatic fallback.

First rerun exactly the five critical cases below. The operator reported 3 passed
and 2 failed with Qwen prompt v2; require **5 passed with v3** for each provider
before the full corpus. No live Groq or OpenAI pass is claimed here.
In particular count_venues must use temporal=none, and organizations_area must
use intent=list, semantic_query=null and temporal=none:

```sh
RESEARCH_PLANNER_OUTPUT_MODE=json_schema RESEARCH_PLANNER_LIVE_TEST=1 \
  uv run pytest -q tests/test_local_model.py \
  -k 'count_past_kuehlhaus or events_deutsches_haus or venues_area or count_venues or organizations_area'
```

Only after that gate passes, run all 37 complete golden plans (including semantic
requests, count versus occurrences, comparison/clarification, dates, Danish,
English and unsafe requests):

```sh
RESEARCH_PLANNER_OUTPUT_MODE=json_schema RESEARCH_PLANNER_LIVE_TEST=1 \
  uv run pytest -q tests/test_local_model.py
```

Every plan field must match; only the casing of `semantic_query` may vary.
In particular the Kühlhaus case must return `entity_type=event`, all 21 fields,
`semantic_focus=null`, the three previously broken enums as `"none"`, and no
invented keys. See the [complete golden JSON](research-ai/natural-language-research.md#closed-plan).
The tests call the model client directly, so unsupported requests are compared
as plans before the API maps them to 422. No real data/lookups are supplied.

Record model revision, GGUF checksum/quantization, llama.cpp build, prompt version,
output mode, pass/fail counts, invalid-plan rate, actual prompt tokens and latency.
Repeat with unseen paraphrases and concurrency 1/2 in a separate operator-run load
evaluation. A passing mocked suite or readiness check proves no Qwen accuracy;
real live quality and CPU latency remain separate acceptance decisions.

No production restarts, migrations, Qdrant reconcile/reindex, AWS changes or
deployment operations are performed by this PR. Rollout remains an operator task
after model evaluation and the separate admin integration PR.

## Manual provider comparison

Use the same commit, prompt v3, json_schema mode, 37 fixtures, timezone and test
reference date for local Qwen, Groq gpt-oss-20b and OpenAI gpt-5.6-luna. Future models
must use one of the explicitly supported providers and pass the same gate. Keep timeout/max tokens
and concurrency constant when comparing; record any deliberate changes.

After the five-case gate, retain a separate JUnit report per provider/model:

```sh
# Real inference; only in the explicitly configured operator environment above.
uv run pytest -q tests/test_local_model.py --junitxml=/tmp/planner-openai-acceptance.xml
```

Record case ID, provider, model ID, prompt version, output mode, pass/fail, exact
golden match, safe failure code, planner_ms, total_ms, input tokens and output tokens.
Golden match means the existing full-field comparison, with only semantic_query
casing allowed to differ. Count planner_invalid_response failures separately from
valid-but-wrong plans and unavailable/rate-limited calls; report counts and the
invalid-plan rate over all attempted cases. Reports may contain synthetic fixture
text; use this workflow only with the reviewed corpus and keep reports out of git.

The fixture tests call the model client directly and therefore do **not** produce
API planner_ms/total_ms diagnostics. Do not relabel pytest duration as either metric.
For timing, submit the same fixture queries to an operator-run planner API with the
same configuration and record its safe research_plan log events: planner_ms measures
the client/validation stage, total_ms the API stage (including failed calls). Success
responses also contain these diagnostics. Keep test IDs associated with requests
in the operator harness; do not enable prompt/body logging. Record the API's returned
reference_date because it uses the current date, unlike the fixed-date fixture run.

Report cold/warm p50/p95, sample counts and concurrency separately. The current
client does not expose provider token usage in the public response or logs: record
input/output tokens as **unavailable** unless the provider's existing usage reporting
supplies them. Never invent token counts or expose raw responses/keys to obtain them.
Reasoning effort is not configurable in this implementation; document the provider
model default and treat low-effort reasoning as a future separately tested benchmark.
