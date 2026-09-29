"""Only fixed safe error messages may cross the service boundary."""

from typing import Literal

ErrorCode = Literal[
    "planner_unavailable",
    "planner_invalid_response",
    "planner_unsupported_plan",
    "invalid_request",
    "unauthorized",
    "request_too_large",
]
MESSAGES: dict[ErrorCode, str] = {
    "planner_unavailable": "Planner temporarily unavailable.",
    "planner_invalid_response": "Planner returned an invalid plan.",
    "planner_unsupported_plan": "This question cannot be represented by the research plan.",
    "invalid_request": "Invalid research planning request.",
    "unauthorized": "Service authentication required.",
    "request_too_large": "Request body exceeds the allowed size.",
}


class PlannerError(Exception):
    def __init__(self, code: ErrorCode, status: int = 503):
        self.code = code
        self.status = status
        super().__init__(code)
