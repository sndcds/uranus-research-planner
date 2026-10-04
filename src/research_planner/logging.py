"""Emit only explicitly constructed fields, never request/model/exception text."""

import json
import logging

LOGGER = logging.getLogger("research_planner.metrics")


def configure_logging() -> None:
    LOGGER.setLevel(logging.INFO)
    if not LOGGER.hasHandlers():
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        LOGGER.addHandler(handler)


def log_plan(
    *,
    request_id: str,
    model: str,
    prompt_version: str,
    intent: str | None,
    planner_ms: float,
    total_ms: float,
    error_type: str,
    interaction_kind: str | None = None,
    validation_stage: str | None = None,
) -> None:
    LOGGER.info(
        json.dumps(
            {
                "event": "research_plan",
                "request_id": request_id,
                "planner_model": model,
                "planner_prompt_version": prompt_version,
                "planner_intent": intent,
                "planner_ms": planner_ms,
                "total_ms": total_ms,
                "error_type": error_type,
                **(
                    {"interaction_kind": interaction_kind, "validation_stage": validation_stage}
                    if validation_stage is not None
                    else {}
                ),
            },
            allow_nan=False,
            separators=(",", ":"),
        )
    )
