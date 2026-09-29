# Internal deployment example (no deployment performed)

There are two independent processes: this lightweight planner API and a separately
provisioned instruction-model server. The API never installs or downloads weights.
Use the [model decision](research-ai/models.md) to evaluate the existing host first.
The repository contains examples, not verified live paths, units or capacity claims.

## Configuration

| Variable | Default / contract |
| --- | --- |
| `RESEARCH_PLANNER_MODEL_URL` | Unset disables planning; numeric internal origin with explicit port, no `/v1` suffix |
| `RESEARCH_PLANNER_MODEL_API_KEY` | Separate outgoing Bearer secret; 16–512 printable ASCII characters |
| `RESEARCH_PLANNER_SERVICE_API_KEY` | Incoming service Bearer secret; same bounds; never delivered to a browser |
| `RESEARCH_PLANNER_MODEL` | `Qwen/Qwen3-4B-Instruct-2507`; fixed server alias |
| `RESEARCH_PLANNER_TIMEOUT_SECONDS` | 8; allowed 0.1–30; absolute model deadline |
| `RESEARCH_PLANNER_MAX_TOKENS` | 1200; allowed 256–2048 |
| `RESEARCH_PLANNER_OUTPUT_MODE` | `json_schema`; explicit `json_object` alternative |
| `RESEARCH_PLANNER_MAX_CONCURRENT_REQUESTS` | 2; allowed 1–8; per API worker |

Run one API worker so concurrency remains globally bounded for the supplied setup.
Independent admin-client settings such as `RESEARCH_PLANNER_URL/API_KEY` belong in
the future admin PR; do not confuse those with the service's outgoing model URL/key.
Timezone comes from admin's `settings.event_timezone` in each request. There is no
user-controlled URL/model/provider or tools field in the request.

## Model server contract

- `POST /v1/chat/completions`: nonstreaming JSON Schema output, fixed model,
  temperature 0, max tokens. No tools/reasoning. Completion includes exactly one
  choice, assistant text containing a JSON object, `finish_reason=stop`, matching model ID.
- `GET /v1/models`: `{"data":[{"id":"Qwen/Qwen3-4B-Instruct-2507"}]}` for readiness.
- Model server's own health endpoint may be `/health` (llama.cpp); the service checks
  model availability via `/v1/models`, not that engine-specific endpoint.
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

[Dockerfile](../deploy/docker/Dockerfile) and
[Compose example](../deploy/docker/compose.yaml) build only the API. They use an
internal Docker network shared with an explicitly selected, already provisioned
model-server image, local read-only weights and a separate model-key file. Startup
does not fetch models. The planner calls that model over a shared loopback network
namespace, preserving plaintext-loopback-only policy. Image and model artifacts
must be pinned/reviewed by the operator before production use. No default model
image is chosen or downloaded by running ordinary tests.

Liveness: `GET /health`, no dependency calls. Readiness: authenticated `GET /ready`,
two-second limit, fixed model must be listed. Readiness does not establish JSON
Schema support, output quality or latency; run the explicit smoke tests separately.

```sh
# Only after configuring an isolated local model; this performs model calls.
RESEARCH_PLANNER_LIVE_TEST=1 uv run pytest -q tests/test_local_model.py
```

No production restarts, migrations, Qdrant reconcile/reindex, AWS changes or
deployment operations are performed by this PR. Rollout remains an operator task
after model evaluation and the separate admin integration PR.
