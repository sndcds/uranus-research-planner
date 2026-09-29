"""Enforce transport policy before the SDK or PydanticAI can parse or retry a response."""

from typing import Any

import httpx

from research_planner.config import Settings
from research_planner.errors import PlannerError
from research_planner.json_codec import decode

MAX_MODEL_REQUEST_BYTES = 64 * 1024
MAX_MODEL_RESPONSE_BYTES = 32 * 1024


class BoundedModelTransport(httpx.AsyncBaseTransport):
    def __init__(self, settings: Settings, inner: httpx.AsyncBaseTransport | None = None):
        assert settings.model_url is not None and settings.model_api_key is not None
        self.origin = httpx.URL(settings.model_url)
        self.key = settings.model_api_key.get_secret_value()
        self.model = settings.model
        self.inner = inner or httpx.AsyncHTTPTransport(
            retries=0,
            trust_env=False,
            limits=httpx.Limits(max_connections=settings.max_concurrent_requests + 1),
        )

    async def aclose(self) -> None:
        await self.inner.aclose()

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        url = request.url
        if (
            (url.scheme, url.host, url.port)
            != (self.origin.scheme, self.origin.host, self.origin.port)
            or url.query
            or url.fragment
            or url.username
            or url.password
            or (request.method, url.path)
            not in {
                ("POST", "/v1/chat/completions"),
                ("GET", "/v1/models"),
            }
        ):
            raise PlannerError("planner_unavailable")
        body = await request.aread()
        if len(body) > MAX_MODEL_REQUEST_BYTES:
            raise PlannerError("invalid_request", 422)
        # Never forward organization/project/env-selected credentials or arbitrary SDK headers.
        request.headers = httpx.Headers(
            {
                "Authorization": "Bearer " + self.key,
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Accept-Encoding": "identity",
                "Host": url.netloc.decode("ascii"),
                "Content-Length": str(len(body)),
            }
        )
        response = await self.inner.handle_async_request(request)
        try:
            if response.status_code != 200:
                raise PlannerError("planner_unavailable")
            if (
                response.headers.get("content-type", "").split(";")[0] != "application/json"
                or response.headers.get("content-encoding", "identity") != "identity"
            ):
                raise PlannerError("planner_invalid_response", 502)
            content = bytearray()
            async for part in response.aiter_bytes():
                if len(content) + len(part) > MAX_MODEL_RESPONSE_BYTES:
                    raise PlannerError("planner_invalid_response", 502)
                content.extend(part)
            result = decode(content)
            if not isinstance(result, dict):
                raise ValueError
            if request.method == "POST":
                self.check_completion(result)
            return httpx.Response(
                200, headers={"Content-Type": "application/json"}, content=bytes(content)
            )
        except (ValueError, KeyError, IndexError, AttributeError, TypeError, RecursionError):
            raise PlannerError("planner_invalid_response", 502) from None
        finally:
            await response.aclose()

    def check_completion(self, result: dict[str, Any]) -> None:
        choices = result["choices"]
        if result.get("model") != self.model or not isinstance(choices, list) or len(choices) != 1:
            raise ValueError
        if choices[0]["finish_reason"] != "stop":
            raise ValueError
        message = choices[0]["message"]
        if message.get("role") != "assistant" or any(
            message.get(key)
            for key in ("tool_calls", "function_call", "refusal", "reasoning", "reasoning_content")
        ):
            raise ValueError
        content = message["content"]
        # PydanticAI can strip Markdown fences; this strict gate deliberately forbids them.
        if not isinstance(content, str) or not isinstance(decode(content), dict):
            raise ValueError
