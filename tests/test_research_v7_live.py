"""Explicit opt-in language acceptance; never an ordinary CI dependency."""

import asyncio
import os
from pathlib import Path

import pytest

from research_planner.config import Settings
from tests.v7_comparison import brief_differences
from tests.v7_golden import load_v7_golden_cases
from tests.v7_live_diagnostics import (
    REFERENCE_DATE,
    LiveSession,
    build_report,
    debug_enabled,
    git_sha,
    write_report,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RESEARCH_PLANNER_LIVE_TEST") != "1",
        reason="Explicit live provider opt-in required",
    ),
]


@pytest.mark.parametrize("case", load_v7_golden_cases(), ids=lambda c: c.id)
async def test_live_v7_language_acceptance(case):
    try:
        session = LiveSession(Settings())
    except Exception:
        pytest.fail("Live configuration unavailable; details withheld", pytrace=False)
    try:
        outcome = await session.run_case(case)
        directory = os.getenv("RESEARCH_PLANNER_LIVE_REPORT_DIR")
        if directory:
            report = build_report(
                [outcome],
                session.model,
                REFERENCE_DATE,
                debug=debug_enabled(),
                git_commit=await asyncio.to_thread(git_sha),
            )
            try:
                await asyncio.to_thread(write_report, report, Path(directory) / f"{case.id}.json")
            except Exception:
                pytest.fail("Live report could not be written; details withheld", pytrace=False)
        if outcome.status == "mismatch":
            pytest.fail(brief_differences(case.id, outcome.differences), pytrace=False)
        if outcome.status != "pass":
            pytest.fail(
                f"case={case.id} status={outcome.status} "
                f"stage={outcome.validation_stage} code={outcome.safe_error_code}",
                pytrace=False,
            )
    finally:
        try:
            await session.close()
        except Exception:
            pytest.fail("Live client cleanup failed; details withheld", pytrace=False)
