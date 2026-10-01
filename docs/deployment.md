# Planner deployment examples (no deployment performed)

Current releases require a [coordinated v3/v6 deployment](chronological-records.md).
Historical v4 acceptance below does not establish live v5 accuracy.

The lightweight planner API uses a separately provisioned internal model
server or the explicitly allowlisted Groq or OpenAI API. It never installs or
downloads weights.
Use the [model decision](research-ai/models.md) to evaluate the existing host first.
The repository contains examples, not verified live paths, units or capacity claims.

## Current recommended production candidate

OpenAI `gpt-5.6-terra` with `research-planner-v4` is the current recommended production
candidate based on operator-run prompt-v4 acceptance: **37/37 golden plans passed**.
The operator's 2026-09-30 results are:

- Previously problematic five cases (location, tomorrow, comparison, injection,
  private): **5 passed, 32 deselected**, 14.77 s pytest duration.
- Full current golden suite: **37 passed**, 82.42 s pytest duration;
  wall clock **83.098 s** (`real 1m23.098s`).

Recommended configuration: provider=openai, base_url=https://api.openai.com/v1,
model=gpt-5.6-terra, prompt=research-planner-v4, output_mode=json_schema,
timeout=30 seconds, max_tokens=1200, max_concurrent_requests=2. The prompt version
comes from the application, not an environment override. Use the complete OpenAI
shell example below or the commented block in [.env.example](../.env.example).

The generic/internal code defaults remain provider=internal and
model=Qwen/Qwen3-4B-Instruct-2507, with timeout=8 seconds. OpenAI deployment must set
the recommended values explicitly. Model selection remains configurable; this does
not remove Luna, Sol, Groq GPT-OSS or local Qwen support.

The suite accepted structured output and all current golden interpretations under
the existing comparison rules. Suite duration is not API p50/p95/p99 latency and
establishes no uptime, production rate-limit suitability, universal language accuracy
or future model-version stability. Continue monitoring and regression testing;
production rollout remains an operator decision.

Historical evaluations of Luna v3, Terra v3, Sol's partial v3 run, Groq GPT-OSS and
internal Qwen remain in the [model evaluation notes](research-ai/models.md).
See the [dated acceptance record and comparison table](research-ai/models.md#operator-acceptance-gpt-56-terra--prompt-v4)
for measured scope and runtime; no deployment is performed by these examples.

## Configuration

| Variable | Default / contract |
| --- | --- |
| `RESEARCH_PLANNER_MODEL_PROVIDER` | `internal`; only `internal`, `groq` or `openai`, never auto-detected |
| `RESEARCH_PLANNER_MODEL_BASE_URL` | Full API base URL; unset (with no legacy URL) disables planning |
| `RESEARCH_PLANNER_MODEL_URL` | Deprecated internal origin without `/v1`; cannot coexist with MODEL_BASE_URL or provider=groq/openai |
| `RESEARCH_PLANNER_MODEL_API_KEY` | Separate outgoing Bearer secret; 16–512 printable ASCII characters |
| `RESEARCH_PLANNER_SERVICE_API_KEY` | Incoming service Bearer secret; same bounds; never delivered to a browser |
| `RESEARCH_PLANNER_MODEL` | `Qwen/Qwen3-4B-Instruct-2507`; set `openai/gpt-oss-20b` for Groq or `gpt-5.6-terra` for the recommended OpenAI candidate; always operator-configurable |
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
  bounded max tokens and provider/model-specific generation settings (below).
  No tools or returned reasoning. Completion includes exactly one
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

### Systemd variants

Choose one repository-managed unit for the configured provider:

| Variant | Repository unit | Network policy |
| --- | --- | --- |
| Internal llama.cpp | [uranus-research-planner.service](../deploy/systemd/uranus-research-planner.service) | `IPAddressDeny=any`, `IPAddressAllow=localhost`; non-loopback traffic blocked |
| OpenAI / Terra | [uranus-research-planner-openai.service](../deploy/systemd/uranus-research-planner-openai.service) | OS-level outbound networking enabled for DNS + HTTPS; no systemd hostname filter |

Both run as `research-planner:research-planner` from a pre-provisioned
`/opt/uranus-research-planner` and venv, reading the protected
`/etc/research-planner/planner.env`. The operator must provision that user, installed
code/dependencies, paths and environment file first. Keep the environment file
root-owned with mode 0600; systemd reads it before dropping privileges. Both units
bind one uvicorn worker to **127.0.0.1:8090**, suppress access logs, and preserve
NoNewPrivileges, PrivateTmp, PrivateDevices, ProtectSystem=strict, ProtectHome,
ProtectKernelTunables, ProtectKernelModules, ProtectControlGroups, RestrictSUIDSGID,
LockPersonality, restricted address families, UMask=0077, MemoryMax=512M and TasksMax=64.

Use the internal unit for:

```env
RESEARCH_PLANNER_MODEL_PROVIDER=internal
RESEARCH_PLANNER_MODEL_BASE_URL=http://127.0.0.1:8091/v1
```

It deliberately blocks OpenAI, Groq and remote private endpoints. For a remote
internal model, prefer a separately provisioned SSH tunnel to loopback. The internal
unit and its network boundary remain unchanged.

Use the OpenAI unit with the [recommended production configuration](#current-recommended-production-candidate):

```env
RESEARCH_PLANNER_MODEL_PROVIDER=openai
RESEARCH_PLANNER_MODEL_BASE_URL=https://api.openai.com/v1
RESEARCH_PLANNER_MODEL=gpt-5.6-terra
```

Supply both existing keys and timeout/token/output/concurrency settings as shown in
the complete OpenAI environment example below. No new environment variables are
introduced. The OpenAI unit waits for network-online.target and needs working DNS
and outbound HTTPS to **api.openai.com:443** through the host/cloud network.

The operator observed `/health` succeeding but `/ready` returning planner_unavailable
when an OpenAI environment was paired with the internal-only unit. Liveness makes
no provider call; readiness needs outbound network access. Install the matching
repository variant rather than an undocumented local network override.

The OpenAI unit omits IPAddressDeny/IPAddressAllow and therefore has **OS-level
outbound network access**, not a hostname allowlist. systemd IPAddressAllow accepts
IPs/CIDRs, not dynamic api.openai.com DNS names. With provider=openai, the unchanged
application policy accepts only the exact base `https://api.openai.com/v1`, and its
transport permits only:

- `GET https://api.openai.com/v1/models`
- `POST https://api.openai.com/v1/chat/completions`

The transport retains trust_env=False, follow_redirects=False, zero retries, fixed
Bearer credential replacement, 64 KiB request/32 KiB response bounds and strict
response validation. No arbitrary or request-controlled model URL is accepted.
This application boundary does not replace an OS-level egress policy. Operators
wanting stronger host restrictions can provision reviewed nftables/firewall rules,
cloud egress controls or network-managed proxy infrastructure separately. Ordinary
HTTP_PROXY/HTTPS_PROXY variables will not work: this client ignores proxy environment
variables. A proxy-based deployment needs a separately reviewed compatible design;
no proxy, firewall or cloud policy is implemented here.

### Install one systemd variant

Run these commands **only as an operator deployment action**, after provisioning
the prerequisites and matching environment. Both variants install under the same
service name; install **exactly one**, not both as separate running services. They
share the same port. Existing local drop-ins can still override the installed file;
inspect `sudo systemctl cat uranus-research-planner.service` and explicitly resolve
any conflicting overrides before switching variants. No local override is required
by this repository procedure.

From the repository checkout, choose the internal variant:

```bash
sudo install -m 0644 \
  deploy/systemd/uranus-research-planner.service \
  /etc/systemd/system/uranus-research-planner.service
```

**Or**, for OpenAI/Terra, choose:

```bash
sudo install -m 0644 \
  deploy/systemd/uranus-research-planner-openai.service \
  /etc/systemd/system/uranus-research-planner.service
```

Then apply the selected unit:

```bash
sudo systemctl daemon-reload
sudo systemctl enable uranus-research-planner.service
sudo systemctl restart uranus-research-planner.service
```

These installation/restart commands are documentation only; they are not run by CI
or during implementation. Unit-file validation is read-only:

```bash
systemd-analyze verify deploy/systemd/uranus-research-planner.service
systemd-analyze verify deploy/systemd/uranus-research-planner-openai.service
```

Verification also checks the absolute ExecStart executable; it requires the
pre-provisioned `/opt/uranus-research-planner/.venv/bin/uvicorn` path to exist.

### Verify the installed service

```bash
sudo systemctl status uranus-research-planner.service --no-pager -l
curl -sS http://127.0.0.1:8090/health | jq .
```

Expected liveness: `{"status":"ok"}`. For authenticated checks, use a trusted operator
Bash shell and a shell-compatible, protected planner.env (simple KEY=value entries
as in the examples). Do not enable shell tracing or publish the environment contents.
The commands below load existing credentials; they do not create or print new keys.

```bash
set +x
set -o pipefail
set -a
source <(sudo cat /etc/research-planner/planner.env)
set +a

curl -sS \
  -H "Authorization: Bearer $RESEARCH_PLANNER_SERVICE_API_KEY" \
  http://127.0.0.1:8090/ready | jq .
```

Expected readiness for a working OpenAI/Terra deployment: `{"status":"ready"}`.
It confirms that the exact configured model is listed, not full inference quality.

The following **real, paid inference smoke test** is operator-only:

```bash
curl -sS --fail \
  -X POST \
  -H "Authorization: Bearer $RESEARCH_PLANNER_SERVICE_API_KEY" \
  -H "Content-Type: application/json" \
  http://127.0.0.1:8090/plan \
  -d '{
    "query": "Was ist heute Abend in Flensburg kulturell interessant?",
    "timezone": "Europe/Berlin",
    "language": "de"
  }' | jq .
```

Expect HTTP success and a valid plan envelope with
`prompt_version=research-planner-v6`, `schema_version=research-query-plan-v3` and
`model=gpt-5.6-terra`, without credentials in the response. Inspect the returned plan;
this smoke test does not prescribe exact semantic fields or replace golden acceptance.
No verification request above is performed automatically by installation or CI.

### Docker examples

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

For the recommended OpenAI Terra candidate, use this configuration instead. Replace
the key placeholders through the same secure operator workflow:

```sh
unset RESEARCH_PLANNER_MODEL_URL
export RESEARCH_PLANNER_MODEL_PROVIDER=openai
export RESEARCH_PLANNER_MODEL_BASE_URL=https://api.openai.com/v1
export RESEARCH_PLANNER_MODEL_API_KEY='sk_example_redacted'
export RESEARCH_PLANNER_SERVICE_API_KEY='service_example_redacted'
export RESEARCH_PLANNER_MODEL=gpt-5.6-terra
export RESEARCH_PLANNER_TIMEOUT_SECONDS=30
export RESEARCH_PLANNER_MAX_TOKENS=1200
export RESEARCH_PLANNER_OUTPUT_MODE=json_schema
export RESEARCH_PLANNER_MAX_CONCURRENT_REQUESTS=2
export RESEARCH_PLANNER_LIVE_TEST=1
```

The endpoint policy supplies fixed generation settings; these are not arbitrary
operator/request parameters:

| Provider/model | Outgoing generation parameters |
| --- | --- |
| `openai`, model starts with `gpt-5.6-` | `reasoning_effort=none`; `temperature` omitted |
| `groq`, `openai/gpt-oss-20b` or `openai/gpt-oss-120b` | `temperature=0`, `include_reasoning=false`; no reasoning_effort |
| Internal Qwen and other configured models | `temperature=0`; no reasoning_effort or include_reasoning |

OpenAI never receives Groq's `include_reasoning` or `reasoning_format`. PydanticAI
serializes the policy's `openai_reasoning_effort` as `reasoning_effort`. Its existing
`max_tokens` setting already becomes `max_completion_tokens` on the wire; mocked
requests verify exactly one token-limit field, with the configured value (1200 above).
No temperature=1, top_p, verbosity or alternative reasoning effort is injected.

The operator reproduced a `temperature=0` rejection for `gpt-5.6-luna`. A minimal
Chat Completions JSON request with reasoning_effort=none, no temperature and
max_completion_tokens=100 succeeded, returning the exact model ID, finish_reason=stop
and zero reasoning tokens. This verifies parameter compatibility for that minimal
request only. Subsequent Terra prompt-v4 acceptance passed all 37 golden plans;
see the dated record above. Mocked GPT-5.6 sibling tests alone do not establish live
sibling support. Other models require their own acceptance; unrelated or future
model families receive no GPT-5.6 override.

Readiness must still list the exact model, and completion model IDs must match
exactly. An alias mismatch, unsupported parameter, oversized model list or rejected
schema fails closed; investigate before any separately reviewed change.

For local Qwen, use MODEL_PROVIDER=internal, MODEL_BASE_URL=http://127.0.0.1:8091/v1,
the internal model key and MODEL=Qwen/Qwen3-4B-Instruct-2507 instead. The test file
retains its name for compatibility; it evaluates any explicitly configured provider.
Normal CI disables live inference and mocks all three providers. Never enable the live
flag merely to run the ordinary unit suite against production.

Use `RESEARCH_PLANNER_OUTPUT_MODE=json_schema` as the preferred default. Small
models need the schema-friendly contract, prompt v4 rules and complete golden
example.
llama.cpp supports only a subset of JSON Schema regex features; the plan now uses
min/max string lengths with Pydantic nonblank validation instead of `pattern=\S`.
Inspect the pinned server's schema conversion warnings. Pydantic remains the
final boundary; invalid output is never automatically repaired. `json_object`
is only an explicitly selected diagnostic alternative, with no automatic fallback.

First run the three persistent v3 failures with prompt v4. Require **3 passed**:

```sh
RESEARCH_PLANNER_OUTPUT_MODE=json_schema RESEARCH_PLANNER_LIVE_TEST=1 \
  uv run pytest -q tests/test_local_model.py -k 'tomorrow or injection or private'
```

The tomorrow plan must keep `Workshops für Kinder` intact in semantic_query, with
empty category/genre lists. Injection/private requests must return the canonical
neutral outside_research plan. A noncanonical unsupported plan is invalid (502),
not repaired; a valid unsupported plan retains the API's unsupported mapping (422).

Then rerun the five historical critical cases below; require **5 passed with v4**
for each evaluated model before the full corpus. Terra's recorded v4 full-suite pass
covers these cases; repeat the gates for model, prompt or dependency changes.
In particular count_venues must use temporal=none, and organizations_area must
use intent=list, semantic_query=null and temporal=none:

```sh
RESEARCH_PLANNER_OUTPUT_MODE=json_schema RESEARCH_PLANNER_LIVE_TEST=1 \
  uv run pytest -q tests/test_local_model.py \
  -k 'count_past_kuehlhaus or events_deutsches_haus or venues_area or count_venues or organizations_area'
```

Only after both gates pass, run all 37 complete golden plans (including semantic
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

Use the same commit, prompt v4, json_schema mode, 37 fixtures, timezone and test
reference date for local Qwen, Groq gpt-oss-20b and OpenAI gpt-5.6-terra; Luna and
Sol remain configurable comparison candidates. Future models must use an explicitly
supported provider and pass the same gate. Keep timeout/max tokens and concurrency
constant when comparing; record any deliberate changes.

To compare the accepted `gpt-5.6-terra` candidate with `gpt-5.6-sol`, set MODEL to one,
run the three-case gate, five-case gate and full corpus, then repeat for the other.
Use the OpenAI configuration above with timeout=30, max tokens=1200 and concurrency=2;
change only MODEL between runs. Keep prompt v4, output mode, fixtures and their fixed
reference date (2026-09-29) identical. Do not infer sibling accuracy from the shared
GPT-5.6 request-parameter policy. Sol has only the recorded partial v3 result,
not a full acceptance pass. Operator results are recorded in
[the dated comparison table](research-ai/models.md#operator-acceptance-gpt-56-terra--prompt-v4).

After both gates, retain a separate JUnit report per provider/model:

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
Reasoning effort is not operator-configurable: OpenAI GPT-5.6 uses the fixed `none`
compatibility policy; other models retain their provider default. Record that policy
when comparing runs. Other reasoning settings require separately reviewed tests.
