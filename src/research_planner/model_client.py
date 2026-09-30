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
from pydantic_ai.profiles.openai import OpenAIModelProfile
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

from research_planner.config import Settings
from research_planner.errors import PlannerError
from research_planner.json_codec import decode
from research_planner.prompts import SYSTEM_PROMPT
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
        self.agent: Agent[None, ResearchQueryPlan] = Agent(
            model,
            output_type=output,
            system_prompt=SYSTEM_PROMPT,
            retries=0,
            model_settings={
                "temperature": 0,
                "max_tokens": settings.max_tokens,
                "timeout": settings.timeout_seconds,
                "extra_body": self.endpoint.completion_options(settings.model),
            },
        )
        self.agent.instrument = False

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
        try:
            async with asyncio.timeout(self.settings.timeout_seconds):
                result = await self.agent.run(
                    json.dumps(
                        {
                            **request.model_dump(mode="json"),
                            "reference_date": reference_date.isoformat(),
                        },
                        ensure_ascii=False,
                    ),
                    usage_limits=UsageLimits(request_limit=1, tool_calls_limit=0),
                )
            if result.output.original_query != request.query:
                raise PlannerError("planner_invalid_response", 502)
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
