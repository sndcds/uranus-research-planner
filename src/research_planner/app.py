"""Internal service: liveness, readiness and language planning only."""

import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from time import perf_counter
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer

from research_planner.config import Settings
from research_planner.errors import PlannerError
from research_planner.logging import configure_logging, log_plan
from research_planner.model_client import StructuredModelClient
from research_planner.planner import ResearchPlanner, UnavailablePlanner
from research_planner.prompts import RESEARCH_PLANNER_PROMPT_VERSION
from research_planner.schemas import (
    ClarificationResponse,
    ErrorResponse,
    HealthResponse,
    PlanDiagnostics,
    PlannedResponse,
    PlanRequest,
    PlanResponse,
    ResearchQueryPlan,
)
from research_planner.security import RequestBoundary, error_response


def create_app(
    settings: Settings | None = None,
    planner: ResearchPlanner | None = None,
    clock: Callable[[], datetime] | None = None,
) -> FastAPI:
    settings = settings if settings is not None else Settings()
    now = clock or (lambda: datetime.now(UTC))
    provider: ResearchPlanner = planner or UnavailablePlanner()
    slots = asyncio.Semaphore(settings.max_concurrent_requests)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        nonlocal provider
        configure_logging()
        if planner is None and settings.model_base_url is not None:
            provider = StructuredModelClient(settings)
        try:
            yield
        finally:
            await provider.close()

    app = FastAPI(
        title="Kulturbytes Research Planner",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        redirect_slashes=False,
    )
    app.add_middleware(RequestBoundary, settings=settings)
    service_auth = HTTPBearer(
        auto_error=False, description="Internal service key, not a user token"
    )

    @app.exception_handler(PlannerError)
    async def planner_error(request: Request, exc: PlannerError) -> JSONResponse:
        return error_response(exc.code, exc.status)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        # FastAPI's default includes input values; keep them out of all error responses.
        return error_response("invalid_request", 422)

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.get(
        "/ready",
        response_model=HealthResponse,
        dependencies=[Depends(service_auth)],
        responses={code: {"model": ErrorResponse} for code in (401, 422, 503)},
    )
    async def ready() -> HealthResponse:
        try:
            async with asyncio.timeout(min(settings.timeout_seconds, 2)):
                if not await provider.ready():
                    raise PlannerError("planner_unavailable")
        except TimeoutError:
            raise PlannerError("planner_unavailable") from None
        return HealthResponse(status="ready")

    @app.post(
        "/plan",
        response_model=PlanResponse,
        dependencies=[Depends(service_auth)],
        responses={code: {"model": ErrorResponse} for code in (401, 413, 422, 502, 503)},
    )
    async def plan(request: PlanRequest) -> PlanResponse:
        started = perf_counter()
        request_id = uuid4().hex
        intent = None
        error_type = "none"
        planner_ms = 0.0
        try:
            # No unbounded queue in front of the model. Admission rejection is a safe 503.
            if slots.locked():
                raise PlannerError("planner_unavailable")
            reference_date = now().astimezone(ZoneInfo(request.timezone)).date()
            async with slots, asyncio.timeout(settings.timeout_seconds):
                model_started = perf_counter()
                try:
                    proposal = await provider.plan(request, reference_date)
                finally:
                    planner_ms = round((perf_counter() - model_started) * 1000, 2)
            # Revalidate every provider, including injected implementations. Never trust model_copy.
            try:
                proposal = ResearchQueryPlan.model_validate_json(proposal.model_dump_json())
                if proposal.original_query != request.query:
                    raise ValueError
            except (ValueError, TypeError, AttributeError):
                raise PlannerError("planner_invalid_response", 502) from None
            intent = proposal.intent
            if proposal.unsupported_reason is not None:
                raise PlannerError("planner_unsupported_plan", 422)
            diagnostics = PlanDiagnostics(
                request_id=request_id,
                planner_intent=proposal.intent,
                planner_model=settings.model,
                planner_prompt_version=RESEARCH_PLANNER_PROMPT_VERSION,
                planner_ms=planner_ms,
                total_ms=round((perf_counter() - started) * 1000, 2),
            )
            response_type = (
                ClarificationResponse if proposal.clarification != "none" else PlannedResponse
            )
            return response_type(
                prompt_version=RESEARCH_PLANNER_PROMPT_VERSION,
                model=settings.model,
                plan=proposal,
                reference_date=reference_date,
                timezone=request.timezone,
                diagnostics=diagnostics,
            )
        except TimeoutError:
            error_type = "planner_unavailable"
            raise PlannerError("planner_unavailable") from None
        except PlannerError as exc:
            error_type = exc.code
            raise
        finally:
            log_plan(
                request_id=request_id,
                model=settings.model,
                prompt_version=RESEARCH_PLANNER_PROMPT_VERSION,
                intent=intent,
                planner_ms=planner_ms,
                total_ms=round((perf_counter() - started) * 1000, 2),
                error_type=error_type,
            )

    return app
