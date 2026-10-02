# v7 live acceptance diagnostics

Audit base after PR #18: `42320a7e3098a67c9d641c442ea7eb2349f570b8`.
Branch: `feat/v7-live-diagnostics`. This work observes the existing 455 cases and
research-query-plan-v7 / research-planner-v12; it does not repair interpretations.

## Audit and design

Read the model client, v7 schema/constraints/types/prompt, errors and strict JSON codec;
the live/client/contract/corpus tests and golden loader; the corpus reporter and v7
contract/implementation documentation. Also inspected the bounded transport and the
installed PydanticAI exception/message capture interfaces.

Three existing boundaries collapse output failures to planner_invalid_response (502):

1. BoundedModelTransport rejects invalid content type/encoding/size, malformed or
   duplicate-key JSON, unexpected completion shape/model/role, non-stop finish reasons,
   tools/refusal/reasoning fields, and non-object message content before PydanticAI sees it.
2. StructuredModelClient._infer catches UnexpectedModelBehavior, UsageLimitExceeded and
   ValueError (including validation errors). SDK/HTTP errors can wrap transport errors;
   its bounded cause walk preserves only safe PlannerError codes.
3. plan_v7 revalidates with trusted original_query context and collapses ValueError,
   TypeError and AttributeError. The API independently revalidates again.

UnexpectedModelBehavior.body and exception strings can include unfiltered provider data.
PydanticAI capture_run_messages is public but includes prompts and cannot observe answers
rejected by the preceding transport. Neither is dumped. A test-only passive response-stream
observer will select only assistant content, finish_reason and completion_tokens inside
the existing byte bound. The unchanged StructuredModelClient/plan_v7 remains authoritative.
Failure diagnosis replays the same strict JSON/Pydantic validators locally, without any
second model request, result repair, retry or fallback. No production files need changes.

## Safety and activation

All new executable support is under `tests/` and `scripts/`. Nothing under `src/`, no
production settings, no API/health/metrics endpoint, logging configuration, schema,
prompt or fixture changes. The service does not import these modules. Setting debug
alone, or even both flags in the service environment, cannot activate instrumentation.
Normal errors remain planner_invalid_response (502); no raw diagnostic enters the API.

`RESEARCH_PLANNER_LIVE_TEST=1` explicitly permits the developer runner/live pytest to
call the configured provider. **Detailed invalid-output capture additionally requires
RESEARCH_PLANNER_LIVE_DEBUG=1.** No credentials are loaded by import or CLI help.
Without live opt-in the runner exits 2 before constructing a client or creating a file.
Debug alone does nothing. There are no new ordinary production settings.

The runner is sequential, preserves loader order and uses the same StructuredModelClient,
plan_v7 and comparison logic as live pytest. Original request/token/timeout/transport
limits, one request, zero tools, zero retries and no provider fallback are preserved.
No database, geocoder, retrieval, memory, prompt repair or question-specific routing.

Reports are private developer artifacts. Query/plan content appears only in an explicitly
requested live report. No HTTP request headers, response headers, cookies, configuration,
exception repr/body, system prompt, reasoning content, provider IDs or environment dump
is serialized. Only a 200 JSON/identity response is observed inside the existing 32 KiB
bound. Oversized/unparseable bodies are not retained. Provider error bodies are ignored.

Configured model/service credentials are redacted across report questions, expectations,
actual plans, differences, validation messages/locations and selected model output before
returning a case record. Header/credential markers and long base64-like strings are also
redacted. A sensitive object key redacts its associated value. Unknown external secrets
without recognizable markers cannot be identified reliably; do not put unrelated secrets
in a test question. Provider metadata is excluded rather than relying on redaction.

Files are written atomically with mode 0600, only at an explicit path. The final file's
symlink is replaced, never followed for writing. No default report location in the repo,
no automatic artifact upload and no report in stdout, journald or OpenTelemetry. A
redacted field is an observation with sensitive text withheld, not a modified plan sent
to the model or accepted by the service. Pass/fail is computed **before** redaction.

## Runner

Use existing provider configuration; do not paste credentials into commands or reports:

```sh
RESEARCH_PLANNER_LIVE_TEST=1 \
RESEARCH_PLANNER_LIVE_DEBUG=1 \
uv run python -m scripts.run_v7_live_acceptance \
  --output /tmp/v7-live-report.json

RESEARCH_PLANNER_LIVE_TEST=1 RESEARCH_PLANNER_LIVE_DEBUG=1 \
uv run python -m scripts.run_v7_live_acceptance \
  --output /tmp/v7-trends.json --category trends

RESEARCH_PLANNER_LIVE_TEST=1 RESEARCH_PLANNER_LIVE_DEBUG=1 \
uv run python -m scripts.run_v7_live_acceptance \
  --output /tmp/v7-one.json --case ranking-039-004

RESEARCH_PLANNER_LIVE_TEST=1 RESEARCH_PLANNER_LIVE_DEBUG=1 \
uv run python -m scripts.run_v7_live_acceptance \
  --output /tmp/v7-definitions.json --capability needs_definition
```

Each filter can be repeated: values within one filter are ORed, different filters are
ANDed. Unknown filters or an empty selection exit 2 without model calls or an artifact.
Default reference date is 2026-10-02, matching the existing live pytest; override explicitly
with `--reference-date YYYY-MM-DD`. Language/timezone use the existing request defaults.
Optional local Git SHA is recorded without a network request; absent Git yields null.

Exit 0 means every selected case passed. Exit 1 means at least one mismatch, invalid
response or provider error; the complete JSON is still written, including later cases.
Exit 2 means opt-in, selection, configuration or output failure. A process interruption
or filesystem failure cannot guarantee a completed report. Console output is counts or
fixed safe error text, never individual model outputs or exception payloads.

## JSON contract

`LiveReport`, `LiveCaseDiagnostic`, `Expectations`, `Difference`, `ValidationDetail` and
`Counts` are strict Pydantic models with extra fields forbidden and nonfinite values
rejected. Arbitrary JSON is limited to observed/expected data values, not executable DSL.

Top level:

- schema_version, prompt_version, model, reference_date, optional git_commit, debug_enabled
- total, passed, failed, mismatch_count, invalid_response_count, provider_error_count
- by_category and by_capability_status: total/passed/mismatch/invalid_response/provider_error
- by_difference_path and cases in original golden loader order

Per case: case_id, category, capability_status, question, status, expected, actual,
differences, validation_stage, validation_errors, model_output, finish_reason,
output_tokens, safe_error_code. Unused fields consistently use null or empty arrays.
`expected` preserves separate **expect** and **forbid** maps; no fabricated full expected
plan is emitted. `actual` is the validated plan's model_dump(mode="json"), subject only
to credential redaction. The diagnostic models are not part of the service OpenAPI.

Differences compare JSON structure, not serialized strings. Example:

```json
{"path":"intent","expected":"rank","actual":"aggregate","kind":"mismatch"}
```

Nested objects and lists are compared recursively, including unexpected keys and list
length/order. A missing dotted path is a failure even when null might otherwise match.
A forbid violation uses kind=forbidden_value and expected contains the forbidden list.
Differences sort by path/kind; exact query equality is still checked. No tolerances,
normalization, reordered filters, aliases or alternative golden answers are introduced.
The original strict assertion uses the same comparator and still raises on any difference.

`by_difference_path` counts each leaf difference and its ancestor paths. For example,
price.maximum increments both price.maximum and price. Thus root price/spatial/metric/etc.
counts are derived generically; ancestor/leaf totals overlap and must not be added as an
independent case count. The two status breakdowns count cases, not differences.

## Invalid output stages

| validation_stage | Meaning |
| --- | --- |
| structured_output_error | Transport/completion structure gate; no more precise safe cause available |
| invalid_json | Strict outer/content JSON failed, including duplicate keys/nonfinite values |
| truncated_output | Observed finish_reason=length, not guessed from validation failure |
| pydantic_validation_error | Closed plan/type/cross-field validation failed |
| post_validation_error | Base plan valid but trusted original_query revalidation failed |
| usage_limit_error | Typed UsageLimitExceeded found in the bounded exception chain |
| unexpected_model_behavior | Typed UnexpectedModelBehavior without a more precise validation cause |

Validation errors contain only loc/type/msg from errors(include_input=False,
include_context=False, include_url=False), then redaction. No exception repr or input/ctx.
Local diagnostic replay invokes the exact unchanged validators after rejection; it never
changes which output is accepted and never triggers another inference.

In debug mode only, `model_output` may hold safely parsed JSON restricted to declared
plan fields. It is **not** a full raw response dump. Extra top-level fields, malformed or
partial JSON, refusal text and arbitrary provider metadata are omitted. Excessive JSON
nesting and nonfinite numeric overflow are replaced with omission markers so a malformed
plan cannot break report serialization. A truncated output can therefore have
finish_reason=length and model_output=null. Optional output_tokens
comes only from completion_tokens, never prompt tokens or cost inference. Missing metadata
stays null. Capture is reset per case and private content cleared after each call.

Without debug, invalid_response retains its safe code but detailed stage/errors/output
remain null/empty. Provider/network errors retain a safe code only. Unexpected client or
developer exceptions are conservatively recorded as provider_error/planner_unavailable;
no claim about their original private message is made. The runner exercises plan_v7,
not the HTTP envelope validator; API-specific disposition checks remain in offline tests.

## Pytest stays the acceptance specification

The existing live marker and explicit skip gate are retained; no failure became skip/xfail.
To save one report per case while retaining normal FAILED results:

```sh
RESEARCH_PLANNER_LIVE_TEST=1 RESEARCH_PLANNER_LIVE_DEBUG=1 \
RESEARCH_PLANNER_LIVE_REPORT_DIR=/tmp/v7-pytest-reports \
uv run pytest -q tests/test_research_v7_live.py
```

Without the explicit directory, pytest creates no artifact. Mismatch failures show at most
five paths and bounded scalar/enum values. Free text, arrays and objects are withheld from
the failure message; full redacted details belong in the report. Invalid failures show the
safe status/stage/code. Pytest's assertion rewriting does not dump Difference payloads.

Offline tests use MockTransport, including a complete 455-case reporter round trip. These
prove capture, strict comparison, safety, aggregation and output plumbing, **not language
accuracy**. No live provider call is made by ordinary CI. This PR did not rerun the user's
reported 178-pass/277-fail live evaluation and makes no new live acceptance-rate claim.

## Interpreting findings before a future v13

Mismatch means the valid plan differs from the current executable expectations. It does
not establish that the golden is right and the model is wrong. Ambiguity, overly specific
expectations, legitimate alternate plans or a prompt interpretation problem must be
reviewed against the unchanged contract and original question. Invalid_response identifies
rejection, which may be transport/truncation or a schema boundary rather than language.

Before any v13 change, audit the golden expectations professionally: confirm intended
entity, metric, grouping, data dependencies and clarification/capability boundary. Review
patterns by category/capability/path and distinguish model errors from disputed golden
semantics. This diagnostics PR deliberately changes neither side of that comparison.

## Implementation validation

Completed locally without Docker or live provider calls:

- `uv sync --locked --group dev`: passed.
- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: passed (65 files).
- `uv run mypy`: passed (29 source files).
- `uv run pytest -q` with live/debug flags unset: **3379 passed, 710 skipped**.
- `uv run python scripts/export_openapi.py` and
  `git diff --exit-code docs/openapi.json`: passed, no OpenAPI changes.
- `uv run python scripts/check_doc_links.py`: passed.
- `git diff --check`: passed.

The 44 new offline cases include streaming and buffered provider mocks, cross-field
validation, original-query revalidation, truncation, malformed/oversized/deep JSON,
numeric overflow, credential redaction, production error isolation, CLI filtering,
strict pytest failures, and a complete mocked 455-case report. Production source,
all golden fixtures, prompt v12, schema snapshots and legacy pins are unchanged.
