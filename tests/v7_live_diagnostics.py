"""Opt-in developer instrumentation. Never imported by the production package."""

import json
import math
import os
import re
import subprocess
import tempfile
from collections import Counter
from collections.abc import AsyncIterator
from datetime import date
from pathlib import Path
from typing import Literal, cast

import httpx
from pydantic import Field, JsonValue, ValidationError
from pydantic_ai.exceptions import UnexpectedModelBehavior, UsageLimitExceeded

from research_planner.config import Settings
from research_planner.errors import ErrorCode, PlannerError
from research_planner.json_codec import decode
from research_planner.model_client import StructuredModelClient
from research_planner.research_v7_canonical import CanonicalModelOutputV7
from research_planner.research_v7_prompts import RESEARCH_V7_PROMPT_VERSION
from research_planner.research_v7_schema import ResearchQueryPlanV7
from research_planner.schemas import PlanRequest
from research_planner.transport import MAX_MODEL_RESPONSE_BYTES
from tests.v7_comparison import DiagnosticModel, Difference
from tests.v7_golden import Capability, Category, GoldenCase, compare_v7_expectations

REFERENCE_DATE = date(2026, 10, 2)
Stage = Literal[
    "structured_output_error",
    "pydantic_validation_error",
    "post_validation_error",
    "usage_limit_error",
    "invalid_json",
    "truncated_output",
    "unexpected_model_behavior",
]
FinishReason = Literal["stop", "length", "content_filter", "tool_calls", "function_call"]


class ValidationDetail(DiagnosticModel):
    loc: list[str | int]
    type: str
    msg: str


class Expectations(DiagnosticModel):
    expect: dict[str, JsonValue]
    forbid: dict[str, list[JsonValue]]
    resolver_name_variants: dict[str, list[str]] = Field(default_factory=dict)


class LiveCaseDiagnostic(DiagnosticModel):
    case_id: str
    category: Category
    capability_status: Capability
    question: str
    status: Literal["pass", "mismatch", "invalid_response", "provider_error"]
    expected: Expectations
    actual: dict[str, JsonValue] | None
    differences: list[Difference]
    validation_stage: Stage | None
    validation_errors: list[ValidationDetail]
    model_output: dict[str, JsonValue] | None
    finish_reason: FinishReason | None
    output_tokens: int | None = Field(ge=0)
    safe_error_code: ErrorCode | None


class Counts(DiagnosticModel):
    total: int
    passed: int
    mismatch: int
    invalid_response: int
    provider_error: int


class LiveReport(DiagnosticModel):
    schema_version: Literal["research-query-plan-v7"]
    # Historical reports remain readable; new reports always identify the active prompt.
    prompt_version: Literal["research-planner-v12", "research-planner-v13"]
    model: str
    reference_date: date
    git_commit: str | None
    debug_enabled: bool
    total: int
    passed: int
    failed: int
    mismatch_count: int
    invalid_response_count: int
    provider_error_count: int
    by_category: dict[str, Counts]
    by_capability_status: dict[str, Counts]
    by_difference_path: dict[str, int]
    cases: list[LiveCaseDiagnostic]


def require_live() -> None:
    if os.getenv("RESEARCH_PLANNER_LIVE_TEST") != "1":
        raise ValueError("RESEARCH_PLANNER_LIVE_TEST=1 is required; no provider call was made")


def debug_enabled() -> bool:
    return (
        os.getenv("RESEARCH_PLANNER_LIVE_TEST") == "1"
        and os.getenv("RESEARCH_PLANNER_LIVE_DEBUG") == "1"
    )


class Redactor:
    """Only explicit credentials, never an environment/config dump. No repr leaks."""

    def __init__(self, settings: Settings):
        self._secrets = tuple(
            secret.get_secret_value()
            for secret in (settings.model_api_key, settings.service_api_key)
            if secret is not None and secret.get_secret_value()
        )

    def text(self, text: str) -> str:
        for secret in sorted(self._secrets, key=len, reverse=True):
            text = text.replace(secret, "[redacted]")
        # Discard the entire string, not just the prefix of a credential/header value.
        if re.search(
            r"authorization|bearer|cookie|api[ _-]?key|\bsk-[\w-]+|[A-Za-z0-9+/]{160,}={0,2}",
            text,
            re.I,
        ):
            return "[redacted]"
        return text

    def json(self, value: JsonValue) -> JsonValue:
        if isinstance(value, str):
            return self.text(value)
        if isinstance(value, list):
            return [self.json(v) for v in value]
        if isinstance(value, dict):
            return {
                self.text(k): self.json(v) if self.text(k) == k else "[redacted]"
                for k, v in value.items()
            }
        return value

    def case(self, value: LiveCaseDiagnostic) -> LiveCaseDiagnostic:
        return LiveCaseDiagnostic.model_validate(self.json(value.model_dump(mode="json")))


class Observation:
    """Single request's bounded private content. Never retain response headers/body/IDs."""

    def __init__(self) -> None:
        self.content: str | None = None
        self.finish_reason: FinishReason | None = None
        self.output_tokens: int | None = None
        self.stage: Stage | None = None

    def accept(self, body: bytes) -> None:
        try:
            value = decode(body)
        except (ValueError, RecursionError):
            self.stage = "invalid_json"
            return
        if not isinstance(value, dict):
            self.stage = "structured_output_error"
            return
        choices = value.get("choices")
        if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
            self.stage = "structured_output_error"
            return
        choice = choices[0]
        reason = choice.get("finish_reason")
        if reason in ("stop", "length", "content_filter", "tool_calls", "function_call"):
            self.finish_reason = cast(FinishReason, reason)
        usage = value.get("usage")
        tokens = usage.get("completion_tokens") if isinstance(usage, dict) else None
        if type(tokens) is int and tokens >= 0:
            self.output_tokens = tokens
        message = choice.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if isinstance(content, str):
            self.content = content
        if reason == "length":
            self.stage = "truncated_output"


class ObservedStream(httpx.AsyncByteStream):
    def __init__(self, inner: httpx.AsyncByteStream, observation: Observation):
        self.inner = inner
        self.observation = observation

    async def __aiter__(self) -> AsyncIterator[bytes]:
        buffer = bytearray()
        oversized = False
        try:
            async for chunk in self.inner:
                if not oversized and len(buffer) + len(chunk) <= MAX_MODEL_RESPONSE_BYTES:
                    buffer.extend(chunk)
                else:
                    oversized = True
                    buffer.clear()
                yield chunk  # Original bytes and transport validation remain authoritative.
        finally:
            if oversized:
                self.observation.stage = "structured_output_error"
            elif buffer:
                self.observation.accept(bytes(buffer))
            buffer.clear()

    async def aclose(self) -> None:
        await self.inner.aclose()


class ObservingTransport(httpx.AsyncBaseTransport):
    def __init__(self, inner: httpx.AsyncBaseTransport):
        if not debug_enabled():
            raise ValueError("Live debug requires both explicit opt-ins")
        self.inner = inner
        self.observation = Observation()

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        response = await self.inner.handle_async_request(request)
        if (
            response.status_code == 200
            and response.headers.get("content-type", "").split(";")[0] == "application/json"
            and response.headers.get("content-encoding", "identity") == "identity"
        ):
            # MockTransport may return an already-buffered response; no extra read is needed.
            if response.is_stream_consumed:
                if len(response.content) <= MAX_MODEL_RESPONSE_BYTES:
                    self.observation.accept(response.content)
            elif isinstance(response.stream, httpx.AsyncByteStream):
                response.stream = ObservedStream(response.stream, self.observation)
        return response

    async def aclose(self) -> None:
        await self.inner.aclose()


def exception_chain(exc: BaseException) -> list[BaseException]:
    result: list[BaseException] = []
    pending = [exc]
    while pending and len(result) < 16:
        current = pending.pop()
        if any(current is old for old in result):
            continue
        result.append(current)
        # Suppressed context is useful diagnostically, but is never stringified or serialized.
        pending.extend(e for e in (current.__cause__, current.__context__) if e is not None)
    return result


def validation_details(exc: ValidationError) -> list[ValidationDetail]:
    return [
        ValidationDetail(loc=list(e["loc"]), type=e["type"], msg=e["msg"])
        for e in exc.errors(include_input=False, include_context=False, include_url=False)
    ]


def bounded_json(value: JsonValue, depth: int = 0) -> JsonValue:
    """Malformed plan shapes must not exceed the diagnostic serializer's recursion bound."""
    if depth >= 16:
        return "[omitted-depth]"
    if isinstance(value, float) and not math.isfinite(value):
        return "[omitted-nonfinite]"
    if isinstance(value, dict):
        return {k: bounded_json(v, depth + 1) for k, v in value.items()}
    if isinstance(value, list):
        return [bounded_json(v, depth + 1) for v in value]
    return value


def invalid_details(
    exc: PlannerError, observation: Observation, question: str
) -> tuple[Stage, list[ValidationDetail], dict[str, JsonValue] | None]:
    chain = exception_chain(exc)
    model_output = None
    parsed = None
    if observation.content is not None:
        try:
            parsed = decode(observation.content)
        except (ValueError, RecursionError):
            return observation.stage or "invalid_json", [], None
        if isinstance(parsed, dict):
            # Only declared plan fields; never arbitrary provider metadata or extra answer fields.
            model_output = {
                k: bounded_json(v)
                for k, v in parsed.items()
                if k in ResearchQueryPlanV7.model_fields
            }
    if observation.stage is not None:
        return observation.stage, [], model_output
    if any(isinstance(e, UsageLimitExceeded) for e in chain):
        return "usage_limit_error", [], model_output
    validation = next((e for e in chain if isinstance(e, ValidationError)), None)
    unexpected = any(isinstance(e, UnexpectedModelBehavior) for e in chain)
    if observation.content is not None and (validation is not None or unexpected):
        # Diagnostic-only replay, after the real client already rejected the result. Never repair.
        try:
            CanonicalModelOutputV7.model_validate_json(observation.content)
        except ValidationError as error:
            return "pydantic_validation_error", validation_details(error), model_output
        try:
            CanonicalModelOutputV7.model_validate_json(
                observation.content, context={"original_query": question}
            )
        except ValidationError as error:
            return "post_validation_error", validation_details(error), model_output
    if validation is not None:
        return "pydantic_validation_error", validation_details(validation), model_output
    return (
        ("unexpected_model_behavior" if unexpected else "structured_output_error"),
        [],
        model_output,
    )


class LiveSession:
    """One sequential live/dev session; the real client and plan_v7 are not overridden."""

    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None):
        require_live()
        self.redactor = Redactor(settings)
        self.model = self.redactor.text(settings.model)
        self.observer: ObservingTransport | None = None
        if debug_enabled():
            inner = (
                transport
                if transport is not None
                else httpx.AsyncHTTPTransport(
                    retries=0,
                    trust_env=False,
                    limits=httpx.Limits(max_connections=settings.max_concurrent_requests + 1),
                )
            )
            self.observer = ObservingTransport(inner)
            transport = self.observer
        self.client = StructuredModelClient(settings, transport)

    async def close(self) -> None:
        await self.client.close()

    async def run_case(
        self, case: GoldenCase, reference_date: date = REFERENCE_DATE
    ) -> LiveCaseDiagnostic:
        require_live()
        if self.observer is not None:
            self.observer.observation = Observation()
        outcome = LiveCaseDiagnostic(
            case_id=case.id,
            category=case.category,
            capability_status=case.capability_status,
            question=case.question,
            status="pass",
            expected=Expectations(
                expect=case.expect,
                forbid=case.forbid,
                resolver_name_variants=case.resolver_name_variants,
            ),
            actual=None,
            differences=[],
            validation_stage=None,
            validation_errors=[],
            model_output=None,
            finish_reason=None,
            output_tokens=None,
            safe_error_code=None,
        )
        try:
            actual = await self.client.plan_v7(PlanRequest(query=case.question), reference_date)
            outcome.actual = actual.model_dump(mode="json")
            outcome.differences = compare_v7_expectations(actual, case)
            if outcome.differences:
                outcome.status = "mismatch"
        except PlannerError as exc:
            outcome.safe_error_code = exc.code
            if exc.code == "planner_invalid_response":
                outcome.status = "invalid_response"
                if self.observer is not None:
                    stage, errors, raw = invalid_details(
                        exc, self.observer.observation, case.question
                    )
                    outcome.validation_stage, outcome.validation_errors, outcome.model_output = (
                        stage,
                        errors,
                        raw,
                    )
            else:
                outcome.status = "provider_error"
        except Exception:
            # Unexpected developer/provider exceptions never dump repr, request or configuration.
            outcome.status = "provider_error"
            outcome.safe_error_code = "planner_unavailable"
        finally:
            if self.observer is not None:
                outcome.finish_reason = self.observer.observation.finish_reason
                outcome.output_tokens = self.observer.observation.output_tokens
                self.observer.observation.content = None
        return self.redactor.case(outcome)


def counts(cases: list[LiveCaseDiagnostic]) -> Counts:
    statuses = Counter(c.status for c in cases)
    return Counts(
        total=len(cases),
        passed=statuses["pass"],
        mismatch=statuses["mismatch"],
        invalid_response=statuses["invalid_response"],
        provider_error=statuses["provider_error"],
    )


def build_report(
    cases: list[LiveCaseDiagnostic],
    model: str,
    reference_date: date,
    *,
    debug: bool,
    git_commit: str | None = None,
) -> LiveReport:
    totals = counts(cases)
    paths: Counter[str] = Counter()
    for case in cases:
        for diff in case.differences:
            parts = diff.path.split(".")
            for length in range(1, len(parts) + 1):
                paths[".".join(parts[:length])] += 1
    return LiveReport(
        schema_version="research-query-plan-v7",
        prompt_version=cast(
            Literal["research-planner-v12", "research-planner-v13"], RESEARCH_V7_PROMPT_VERSION
        ),
        model=model,
        reference_date=reference_date,
        git_commit=git_commit,
        debug_enabled=debug,
        total=totals.total,
        passed=totals.passed,
        failed=totals.total - totals.passed,
        mismatch_count=totals.mismatch,
        invalid_response_count=totals.invalid_response,
        provider_error_count=totals.provider_error,
        by_category={
            k: counts([c for c in cases if c.category == k])
            for k in sorted({c.category for c in cases})
        },
        by_capability_status={
            k: counts([c for c in cases if c.capability_status == k])
            for k in sorted({c.capability_status for c in cases})
        },
        by_difference_path=dict(sorted(paths.items())),
        cases=cases,
    )


def git_sha() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        value = result.stdout.strip()
        return value if result.returncode == 0 and re.fullmatch(r"[a-f0-9]{40}", value) else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def write_report(report: LiveReport, output: Path) -> None:
    """Explicit path only. Atomic replace avoids partial reports and symlink writes; mode 0600."""
    require_live()
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = (
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2, allow_nan=False)
        + "\n"
    )
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=output.parent, prefix=".v7-live-", delete=False
        ) as stream:
            temporary = stream.name
            stream.write(payload)
        os.replace(temporary, output)
    finally:
        if temporary is not None:
            Path(temporary).unlink(missing_ok=True)
