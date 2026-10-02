"""Authenticate before parsing; bound incoming bytes and slow request bodies."""

import asyncio
import hmac

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from research_planner.config import Settings
from research_planner.errors import MESSAGES, ErrorCode
from research_planner.json_codec import decode

MAX_REQUEST_BYTES = 16 * 1024


def error_response(code: ErrorCode, status: int) -> JSONResponse:
    return JSONResponse(
        {"error": {"code": code, "message": MESSAGES[code]}},
        status_code=status,
        headers={"Cache-Control": "no-store"},
    )


class RequestBoundary:
    def __init__(self, app: ASGIApp, settings: Settings):
        self.app = app
        self.settings = settings

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def safe_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                message["headers"] = [
                    (key, value)
                    for key, value in message.get("headers", [])
                    if key.lower() != b"cache-control"
                ] + [(b"cache-control", b"no-store"), (b"x-content-type-options", b"nosniff")]
            await send(message)

        if scope["path"] not in {
            "/plan",
            "/v4/plan",
            "/v5/plan",
            "/v6/plan",
            "/v7/plan",
            "/v8/plan",
            "/v9/plan",
            "/ready",
        }:
            await self.app(scope, receive, safe_send)
            return
        keys = [value for key, value in scope["headers"] if key.lower() == b"authorization"]
        configured_key = self.settings.service_api_key
        if configured_key is None:
            await error_response("planner_unavailable", 503)(scope, receive, safe_send)
            return
        expected = ("Bearer " + configured_key.get_secret_value()).encode()
        if len(keys) != 1 or not hmac.compare_digest(keys[0], expected):
            await error_response("unauthorized", 401)(scope, receive, safe_send)
            return
        if scope["query_string"]:
            await error_response("invalid_request", 422)(scope, receive, safe_send)
            return
        if (
            scope["path"]
            not in {"/plan", "/v4/plan", "/v5/plan", "/v6/plan", "/v7/plan", "/v8/plan", "/v9/plan"}
            or scope["method"] != "POST"
        ):
            await self.app(scope, receive, safe_send)
            return
        headers = dict(scope["headers"])
        if (
            headers.get(b"content-type", b"").split(b";")[0].lower() != b"application/json"
            or b"content-encoding" in headers
        ):
            await error_response("invalid_request", 422)(scope, receive, safe_send)
            return
        body = bytearray()
        try:
            async with asyncio.timeout(5):
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return
                    chunk = message.get("body", b"")
                    if len(body) + len(chunk) > MAX_REQUEST_BYTES:
                        await error_response("request_too_large", 413)(scope, receive, safe_send)
                        return
                    body.extend(chunk)
                    if not message.get("more_body", False):
                        break
            decode(body)
        except (ValueError, TypeError, RecursionError, TimeoutError):
            await error_response("invalid_request", 422)(scope, receive, safe_send)
            return
        consumed = False

        async def bounded_receive() -> Message:
            nonlocal consumed
            if not consumed:
                consumed = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, bounded_receive, safe_send)
