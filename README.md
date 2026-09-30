# Uranus Research Planner

Internal language interpretation service for Kulturbytes. It translates German,
Danish and English research questions into a closed, validated `ResearchQueryPlan`.
It has **no database, Qdrant, encoder, external search, tools or user-session access**.

```text
uranus-admin → POST /plan → configured instruction model → validated plan
uranus-admin → public name resolution → PostgreSQL / Jina + Qdrant → verified results
```

This repository implements the first line. The second line remains a separate
`uranus-admin` integration PR. No Research UI or execution endpoint is introduced here.

## Recommended production candidate

`gpt-5.6-terra` on OpenAI with `research-planner-v4` is the current recommended
production candidate, based on operator-run acceptance on 2026-09-30: **37/37 golden
plans passed**. The 82.42 s pytest suite duration is not a production latency benchmark.
See the [acceptance record](docs/research-ai/models.md#operator-acceptance-gpt-56-terra--prompt-v4)
and [recommended configuration](docs/deployment.md#current-recommended-production-candidate).

This recommendation updates examples only. The generic/internal Qwen default remains
unchanged; internal, Groq and other configured OpenAI models remain supported.
Acceptance covers the current corpus, not every possible query or provider operating
condition. Continue monitoring and regression testing.

Use the internal systemd unit for llama.cpp and the OpenAI systemd unit for Terra;
see [systemd variants and installation](docs/deployment.md#systemd-variants).

## Development

Requires Python 3.13 and uv. Dependencies are locked in `uv.lock`.

```sh
uv sync --locked --group dev
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest -q
uv run python scripts/export_openapi.py
git diff --check
```

Ordinary tests use fake planners and mocked model HTTP. Optional model evaluation is
skipped unless `RESEARCH_PLANNER_LIVE_TEST=1` and a supported provider is explicitly configured.
Passing fixtures proves contracts and dispatch boundaries, **not model language accuracy**.

```sh
uv run uvicorn research_planner.app:create_app --factory --host 127.0.0.1 --port 8090 --no-access-log
```

Without configuration `/health` works; `/ready` and `/plan` return 503.
Configure the variables in [.env.example](.env.example) through the process environment
or an explicitly supplied uvicorn `--env-file`. The application does not load `.env` implicitly.
Both service and model keys are required when a model API base URL is configured.

## API

| Endpoint | Purpose | Authentication |
| --- | --- | --- |
| `GET /health` | Process liveness, no model call | None; internal listener |
| `GET /ready` | Fixed model is listed by configured `<base_url>/models` | Service Bearer key |
| `POST /plan` | One bounded structured planning call | Service Bearer key |

Example body:

```json
{"query":"Wie viele Veranstaltungen waren im Kühlhaus?","timezone":"Europe/Berlin","language":"de"}
```

The response has `kind=plan` or `kind=needs_clarification`, schema/prompt versions,
configured model, local reference date, validated plan and safe timing diagnostics.
This example produces `intent=count`, `venue_query=Kühlhaus`, `temporal=past`,
`metric=event_count`, `semantic_query=null`. It does not produce a database count.

See the generated [OpenAPI contract](docs/openapi.json), the full
[architecture and semantics](docs/research-ai/natural-language-research.md),
[main analysis](docs/research-ai/admin-baseline.md),
[model decision](docs/research-ai/models.md), and [deployment guide](docs/deployment.md).

## Scope and safety

PydanticAI provides typed native JSON output and provider abstraction. Its `Agent`
is configured for **one request, zero tools, zero automatic retries, no history and
no telemetry instrumentation**. There is no autonomous research agent.
The OpenAI-compatible SDK is a protocol adapter for an internal numeric-IP
endpoint or the explicitly allowlisted Groq and OpenAI APIs. Set MODEL_PROVIDER
and the full MODEL_BASE_URL as documented in the [deployment guide](docs/deployment.md).
Internal SSRF restrictions remain; arbitrary external URLs, redirects, environment
proxies and provider fallback are forbidden. Both keys stay server-side. No browser
connects to a model provider or receives its key. Selecting Groq or OpenAI sends
planning input externally; no database records or live lookups are supplied.

Jina v3 continues to perform semantic retrieval in `uranus-admin`. PostgreSQL/PostGIS
remains authoritative for identities, public eligibility, dates and exact counts.
Plans are interpretations, not facts. No production deployment or index change is
part of this repository's initial implementation.
