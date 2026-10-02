"""PydanticAI structured output, without tools, memory, retries or provider fallback."""

import asyncio
import json
import logging
from datetime import date

import httpx
from openai import APIError, AsyncOpenAI
from pydantic_ai import Agent, NativeOutput, PromptedOutput
from pydantic_ai.exceptions import ModelAPIError, UnexpectedModelBehavior, UsageLimitExceeded
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.profiles.openai import OpenAIJsonSchemaTransformer, OpenAIModelProfile
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

from research_planner.analytics_prompts import ANALYTICS_PROMPT
from research_planner.analytics_schema import AnalyticalQueryPlan
from research_planner.config import Settings
from research_planner.domain_prompts import DOMAIN_SYSTEM_PROMPT
from research_planner.domain_schema import DomainProposal
from research_planner.errors import PlannerError
from research_planner.geography_prompts import GEOGRAPHY_PROMPT
from research_planner.geography_schema import GeographicQueryPlan
from research_planner.json_codec import decode
from research_planner.prompts import SYSTEM_PROMPT
from research_planner.research_v7_canonical import CanonicalModelOutputV7
from research_planner.research_v7_prompts import RESEARCH_V7_PROMPT, RESEARCH_V7_PROMPT_VERSION
from research_planner.research_v7_schema import ResearchQueryPlanV7
from research_planner.research_v8_canonical import CanonicalModelOutputV8
from research_planner.research_v8_prompts import RESEARCH_V8_PROMPT, RESEARCH_V8_PROMPT_VERSION
from research_planner.research_v8_schema import ResearchQueryPlanV8
from research_planner.research_v9_canonical import CanonicalModelOutputV9
from research_planner.research_v9_prompts import RESEARCH_V9_PROMPT, RESEARCH_V9_PROMPT_VERSION
from research_planner.research_v9_schema import ResearchQueryPlanV9
from research_planner.schemas import PlanRequest, ResearchQueryPlan
from research_planner.transport import BoundedModelTransport


class StructuredModelClient:
    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None):
        if settings.model_base_url is None or settings.model_api_key is None:
            raise ValueError("model_configuration_required")
        self.settings = settings
        self.endpoint = settings.endpoint
        # SDK DEBUG logs contain request bodies. Disable even under OPENAI_LOG=debug.
        for name in ("openai", "openai._base_client", "openai._client", "httpx"):
            logging.getLogger(name).disabled = True
        self.client = httpx.AsyncClient(
            base_url=self.endpoint.base_url,
            timeout=httpx.Timeout(
                settings.timeout_seconds, connect=min(settings.timeout_seconds, 2)
            ),
            trust_env=False,
            follow_redirects=False,
            transport=BoundedModelTransport(settings, transport),
        )
        self.sdk = AsyncOpenAI(
            base_url=self.endpoint.base_url,
            api_key=settings.model_api_key.get_secret_value(),
            organization="",
            project="",
            max_retries=0,
            http_client=self.client,
        )
        model = OpenAIChatModel(
            settings.model,
            provider=OpenAIProvider(openai_client=self.sdk),
            profile=OpenAIModelProfile(
                supports_tools=False,
                supports_json_schema_output=True,
                supports_json_object_output=True,
            ),
        )
        output: NativeOutput[ResearchQueryPlan] | PromptedOutput[ResearchQueryPlan]
        output = (
            NativeOutput(ResearchQueryPlan, strict=True)
            if settings.output_mode == "json_schema"
            else PromptedOutput(ResearchQueryPlan)
        )
        model_settings = self.endpoint.generation_options(settings.model)
        model_settings["max_tokens"] = settings.max_tokens
        model_settings["timeout"] = settings.timeout_seconds
        self.agent: Agent[None, ResearchQueryPlan] = Agent(
            model,
            output_type=output,
            system_prompt=SYSTEM_PROMPT,
            retries=0,
            model_settings=model_settings,
        )
        self.agent.instrument = False
        # V4 needs required nullable fields with no JSON Schema defaults. Keep the v3
        # profile/wire request unchanged; both adapters share the one SDK/transport.
        domain_model = OpenAIChatModel(
            settings.model,
            provider=OpenAIProvider(openai_client=self.sdk),
            profile=OpenAIModelProfile(
                supports_tools=False,
                supports_json_schema_output=True,
                json_schema_transformer=OpenAIJsonSchemaTransformer,
            ),
        )
        self.domain_agent: Agent[None, DomainProposal] = Agent(
            domain_model,
            output_type=NativeOutput(DomainProposal, strict=True),
            system_prompt=DOMAIN_SYSTEM_PROMPT,
            retries=0,
            model_settings=model_settings,
        )
        self.domain_agent.instrument = False
        self.analytics_agent: Agent[None, AnalyticalQueryPlan] = Agent(
            domain_model,
            output_type=NativeOutput(AnalyticalQueryPlan, strict=True),
            system_prompt=ANALYTICS_PROMPT,
            retries=0,
            model_settings=model_settings,
        )
        self.analytics_agent.instrument = False
        self.geography_agent: Agent[None, GeographicQueryPlan] = Agent(
            domain_model,
            output_type=NativeOutput(GeographicQueryPlan, strict=True),
            system_prompt=GEOGRAPHY_PROMPT,
            retries=0,
            model_settings=model_settings,
        )
        self.geography_agent.instrument = False

        self.research_v7_agent: Agent[None, ResearchQueryPlanV7] = Agent(
            domain_model,
            output_type=NativeOutput(CanonicalModelOutputV7, strict=True),
            system_prompt=RESEARCH_V7_PROMPT,
            name=RESEARCH_V7_PROMPT_VERSION,
            retries=0,
            model_settings=model_settings,
        )
        self.research_v7_agent.instrument = False

        self.research_v8_agent: Agent[None, ResearchQueryPlanV8] = Agent(
            domain_model,
            output_type=NativeOutput(CanonicalModelOutputV8, strict=True),
            system_prompt=RESEARCH_V8_PROMPT,
            name=RESEARCH_V8_PROMPT_VERSION,
            retries=0,
            model_settings=model_settings,
        )
        self.research_v8_agent.instrument = False

        self.research_v9_agent: Agent[None, ResearchQueryPlanV9] = Agent(
            domain_model,
            output_type=NativeOutput(CanonicalModelOutputV9, strict=True),
            system_prompt=RESEARCH_V9_PROMPT,
            name=RESEARCH_V9_PROMPT_VERSION,
            retries=0,
            model_settings=model_settings,
        )
        self.research_v9_agent.instrument = False

    async def plan_v8(self, request: PlanRequest, reference_date: date) -> ResearchQueryPlanV8:
        output = await self._infer(
            self.research_v8_agent,
            {**request.model_dump(mode="json"), "reference_date": reference_date.isoformat()},
        )
        try:
            return ResearchQueryPlanV8.model_validate_json(
                output.model_dump_json(), context={"original_query": request.query}
            )
        except (ValueError, TypeError, AttributeError):
            raise PlannerError("planner_invalid_response", 502) from None


    async def plan_v9(self, request: PlanRequest, reference_date: date) -> ResearchQueryPlanV9:
        output = await self._infer(
            self.research_v9_agent,
            {**request.model_dump(mode="json"), "reference_date": reference_date.isoformat()},
        )
        try:
            return ResearchQueryPlanV9.model_validate_json(
                output.model_dump_json(), context={"original_query": request.query}
            )
        except (ValueError, TypeError, AttributeError):
            raise PlannerError("planner_invalid_response", 502) from None

    async def plan_v7(self, request: PlanRequest, reference_date: date) -> ResearchQueryPlanV7:
        output = await self._infer(
            self.research_v7_agent,
            {**request.model_dump(mode="json"), "reference_date": reference_date.isoformat()},
        )
        try:
            return ResearchQueryPlanV7.model_validate_json(
                output.model_dump_json(), context={"original_query": request.query}
            )
        except (ValueError, TypeError, AttributeError):
            raise PlannerError("planner_invalid_response", 502) from None

    async def plan_v6(self, request: PlanRequest, reference_date: date) -> GeographicQueryPlan:
        return await self._infer(
            self.geography_agent,
            {**request.model_dump(mode="json"), "reference_date": reference_date.isoformat()},
        )

    async def plan_v5(self, request: PlanRequest, reference_date: date) -> AnalyticalQueryPlan:
        return await self._infer(
            self.analytics_agent,
            {**request.model_dump(mode="json"), "reference_date": reference_date.isoformat()},
        )

    async def close(self) -> None:
        await self.client.aclose()

    async def ready(self) -> bool:
        try:
            async with asyncio.timeout(min(self.settings.timeout_seconds, 2)):
                response = await self.client.get(self.endpoint.models_url)
                models = decode(response.content).get("data")
                return isinstance(models, list) and any(
                    isinstance(item, dict) and item.get("id") == self.settings.model
                    for item in models
                )
        except (PlannerError, httpx.HTTPError, TimeoutError, ValueError, AttributeError):
            return False

    async def plan(self, request: PlanRequest, reference_date: date) -> ResearchQueryPlan:
        output = await self._infer(
            self.agent,
            {**request.model_dump(mode="json"), "reference_date": reference_date.isoformat()},
        )
        if output.original_query != request.query:
            raise PlannerError("planner_invalid_response", 502)
        return output

    async def plan_v4(self, request: PlanRequest) -> DomainProposal:
        return await self._infer(
            self.domain_agent, {"query": request.query, "language": request.language}
        )

    async def _infer[T](self, agent: Agent[None, T], context: dict[str, object]) -> T:
        try:
            async with asyncio.timeout(self.settings.timeout_seconds):
                result = await agent.run(
                    json.dumps(context, ensure_ascii=False),
                    usage_limits=UsageLimits(request_limit=1, tool_calls_limit=0),
                )
            return result.output
        except (UnexpectedModelBehavior, UsageLimitExceeded, ValueError):
            raise PlannerError("planner_invalid_response", 502) from None
        except (APIError, ModelAPIError, httpx.HTTPError, TimeoutError) as exc:
            # SDK wraps transport errors. Preserve only known safe codes, never provider text.
            cause: BaseException | None = exc
            for _ in range(5):
                if isinstance(cause, PlannerError):
                    raise PlannerError(cause.code, cause.status) from None
                cause = cause.__cause__ if cause is not None else None
            raise PlannerError("planner_unavailable") from None
