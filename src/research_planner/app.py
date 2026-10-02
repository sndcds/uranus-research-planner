"""Internal service: liveness, readiness and language planning only."""

import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from time import perf_counter
from typing import Literal
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer

from research_planner.analytics_guard import analytical_mismatch
from research_planner.analytics_schema import (
    AnalyticalClarification,
    AnalyticalDiagnostics,
    AnalyticalPlanResponse,
    AnalyticalQueryPlan,
    AnalyticalResponse,
)
from research_planner.config import Settings
from research_planner.domain_planner import DomainPlanner
from research_planner.domain_schema import PlanEnvelopeV4
from research_planner.errors import PlannerError
from research_planner.geography_schema import (
    GeographicClarification,
    GeographicDiagnostics,
    GeographicPlanResponse,
    GeographicQueryPlan,
    GeographicResponse,
)
from research_planner.logging import configure_logging, log_plan
from research_planner.model_client import StructuredModelClient
from research_planner.planner import ResearchPlanner, UnavailablePlanner
from research_planner.prompts import RESEARCH_PLANNER_PROMPT_VERSION
from research_planner.research_v7_schema import DiagnosticsV7, PlanResponseV7, ResearchQueryPlanV7
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

    @asynccontextmanager
    async def inference_slot() -> AsyncIterator[None]:
        # All plan versions share admission, with no unbounded queue before inference.
        if slots.locked():
            raise PlannerError("planner_unavailable")
        async with slots, asyncio.timeout(settings.timeout_seconds):
            yield

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
            reference_date = now().astimezone(ZoneInfo(request.timezone)).date()
            async with inference_slot():
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
            if proposal.unsupported_reason is not None or (
                proposal.clarification == "none"
                and analytical_mismatch(request.query, proposal.intent, proposal.group_by)
            ):
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

    @app.post(
        "/v5/plan",
        response_model=AnalyticalPlanResponse,
        dependencies=[Depends(service_auth)],
        responses={code: {"model": ErrorResponse} for code in (401, 413, 422, 502, 503)},
    )
    async def analytical_plan(request: PlanRequest) -> AnalyticalPlanResponse:
        started = perf_counter()
        request_id = uuid4().hex
        intent = None
        error_type = "none"
        planner_ms = 0.0
        try:
            reference_date = now().astimezone(ZoneInfo(request.timezone)).date()
            async with inference_slot():
                model_started = perf_counter()
                try:
                    proposal = await provider.plan_v5(request, reference_date)
                finally:
                    planner_ms = round((perf_counter() - model_started) * 1000, 2)
            # Revalidate every provider, including injected implementations. Never trust model_copy.
            try:
                proposal = AnalyticalQueryPlan.model_validate_json(proposal.model_dump_json())
                if proposal.original_query != request.query:
                    raise ValueError
            except (ValueError, TypeError, AttributeError):
                raise PlannerError("planner_invalid_response", 502) from None
            intent = proposal.intent
            if proposal.unsupported_reason is not None or (
                proposal.clarification == "none"
                and analytical_mismatch(
                    request.query,
                    proposal.intent,
                    proposal.group_by,
                    proposal.taxonomy,
                    proposal.area_relation,
                    proposal.time_of_day,
                )
            ):
                raise PlannerError("planner_unsupported_plan", 422)
            diagnostics = AnalyticalDiagnostics(
                request_id=request_id,
                planner_intent=proposal.intent,
                planner_model=settings.model,
                planner_prompt_version="research-planner-v10",
                planner_ms=planner_ms,
                total_ms=round((perf_counter() - started) * 1000, 2),
            )
            response_type = (
                AnalyticalClarification if proposal.clarification != "none" else AnalyticalResponse
            )
            return response_type(
                schema_version="research-query-plan-v5",
                prompt_version="research-planner-v10",
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
                prompt_version="research-planner-v10",
                intent=intent,
                planner_ms=planner_ms,
                total_ms=round((perf_counter() - started) * 1000, 2),
                error_type=error_type,
            )

    @app.post(
        "/v6/plan",
        response_model=GeographicPlanResponse,
        dependencies=[Depends(service_auth)],
        responses={code: {"model": ErrorResponse} for code in (401, 413, 422, 502, 503)},
    )
    async def geographic_plan(request: PlanRequest) -> GeographicPlanResponse:
        started = perf_counter()
        request_id = uuid4().hex
        intent = None
        error_type = "none"
        planner_ms = 0.0
        try:
            reference_date = now().astimezone(ZoneInfo(request.timezone)).date()
            async with inference_slot():
                model_started = perf_counter()
                try:
                    proposal = await provider.plan_v6(request, reference_date)
                finally:
                    planner_ms = round((perf_counter() - model_started) * 1000, 2)
            # Revalidate every provider, including injected implementations. Never trust model_copy.
            try:
                proposal = GeographicQueryPlan.model_validate_json(proposal.model_dump_json())
                if proposal.original_query != request.query:
                    raise ValueError
            except (ValueError, TypeError, AttributeError):
                raise PlannerError("planner_invalid_response", 502) from None
            intent = proposal.intent
            if proposal.unsupported_reason is not None or (
                proposal.clarification == "none"
                and analytical_mismatch(
                    request.query,
                    proposal.intent,
                    proposal.group_by,
                    proposal.taxonomy,
                    proposal.area_relation,
                    proposal.time_of_day,
                )
            ):
                raise PlannerError("planner_unsupported_plan", 422)
            diagnostics = GeographicDiagnostics(
                request_id=request_id,
                planner_intent=proposal.intent,
                planner_model=settings.model,
                planner_prompt_version="research-planner-v11",
                planner_ms=planner_ms,
                total_ms=round((perf_counter() - started) * 1000, 2),
            )
            response_type = (
                GeographicClarification if proposal.clarification != "none" else GeographicResponse
            )
            return response_type(
                schema_version="research-query-plan-v6",
                prompt_version="research-planner-v11",
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
                prompt_version="research-planner-v11",
                intent=intent,
                planner_ms=planner_ms,
                total_ms=round((perf_counter() - started) * 1000, 2),
                error_type=error_type,
            )

    @app.post(
        "/v7/plan",
        response_model=PlanResponseV7,
        dependencies=[Depends(service_auth)],
        responses={code: {"model": ErrorResponse} for code in (401, 413, 422, 502, 503)},
    )
    async def research_plan_v7(request: PlanRequest) -> PlanResponseV7:
        started = perf_counter()
        request_id = uuid4().hex
        intent = None
        error_type = "none"
        planner_ms = 0.0
        try:
            reference_date = now().astimezone(ZoneInfo(request.timezone)).date()
            async with inference_slot():
                model_started = perf_counter()
                try:
                    proposal = await provider.plan_v7(request, reference_date)
                finally:
                    planner_ms = round((perf_counter() - model_started) * 1000, 2)
            try:
                proposal = ResearchQueryPlanV7.model_validate_json(
                    proposal.model_dump_json(), context={"original_query": request.query}
                )
            except (ValueError, TypeError, AttributeError):
                raise PlannerError("planner_invalid_response", 502) from None
            intent = proposal.intent
            kind: Literal["plan", "needs_clarification", "unsupported"] = (
                "unsupported"
                if proposal.unsupported_reason is not None
                else "needs_clarification"
                if proposal.clarification != "none"
                else "plan"
            )
            return PlanResponseV7(
                kind=kind,
                schema_version="research-query-plan-v7",
                prompt_version="research-planner-v12",
                model=settings.model,
                plan=proposal,
                reference_date=reference_date,
                timezone=request.timezone,
                diagnostics=DiagnosticsV7(
                    request_id=request_id,
                    planner_intent=proposal.intent,
                    planner_model=settings.model,
                    planner_prompt_version="research-planner-v12",
                    planner_ms=planner_ms,
                    total_ms=round((perf_counter() - started) * 1000, 2),
                ),
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
                prompt_version="research-planner-v12",
                intent=intent,
                planner_ms=planner_ms,
                total_ms=round((perf_counter() - started) * 1000, 2),
                error_type=error_type,
            )

    @app.post(
        "/v4/plan",
        response_model=PlanEnvelopeV4,
        dependencies=[Depends(service_auth)],
        responses={code: {"model": ErrorResponse} for code in (401, 413, 422, 502, 503)},
    )
    async def domain_plan(request: PlanRequest) -> PlanEnvelopeV4:
        try:
            async with inference_slot():
                return await DomainPlanner(provider).interpret(request)
        except TimeoutError:
            raise PlannerError("planner_unavailable") from None

    return app
