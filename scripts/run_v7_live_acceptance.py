"""Explicit developer entrypoint; no automatic calls from CI or the service."""

import argparse
import asyncio
import sys
from datetime import date
from pathlib import Path

from research_planner.config import Settings
from tests.v7_golden import GoldenCase, load_v7_golden_cases
from tests.v7_live_diagnostics import (
    REFERENCE_DATE,
    LiveReport,
    LiveSession,
    build_report,
    debug_enabled,
    git_sha,
    require_live,
    write_report,
)


def select_cases(
    cases: list[GoldenCase],
    *,
    identifiers: list[str],
    categories: list[str],
    capabilities: list[str],
) -> list[GoldenCase]:
    filters: list[tuple[list[str], set[str]]] = [
        (identifiers, {c.id for c in cases}),
        (categories, {c.category for c in cases}),
        (capabilities, {c.capability_status for c in cases}),
    ]
    for supplied, valid in filters:
        if not set(supplied) <= valid:
            raise ValueError("Unknown case/category/capability filter")
    selected = [
        c
        for c in cases
        if (not identifiers or c.id in identifiers)
        and (not categories or c.category in categories)
        and (not capabilities or c.capability_status in capabilities)
    ]
    if not selected:
        raise ValueError("Filters selected no cases")
    return selected


async def run_cases(
    settings: Settings, cases: list[GoldenCase], reference_date: date, commit: str | None
) -> LiveReport:
    session = LiveSession(settings)
    try:
        results = [await session.run_case(case, reference_date) for case in cases]
        return build_report(
            results, session.model, reference_date, debug=debug_enabled(), git_commit=commit
        )
    finally:
        await session.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Opt-in v7 live acceptance; never repairs plans")
    parser.add_argument(
        "--output", type=Path, required=True, help="Explicit private JSON report path"
    )
    parser.add_argument("--case", action="append", default=[], dest="identifiers")
    parser.add_argument("--category", action="append", default=[], dest="categories")
    parser.add_argument("--capability", action="append", default=[], dest="capabilities")
    parser.add_argument("--reference-date", type=date.fromisoformat, default=REFERENCE_DATE)
    args = parser.parse_args(argv)
    try:
        require_live()
    except ValueError:
        print(
            "RESEARCH_PLANNER_LIVE_TEST=1 is required; no provider call was made", file=sys.stderr
        )
        return 2
    try:
        cases = select_cases(
            load_v7_golden_cases(),
            identifiers=args.identifiers,
            categories=args.categories,
            capabilities=args.capabilities,
        )
    except ValueError:
        print("Unknown or empty case/category/capability selection", file=sys.stderr)
        return 2
    try:
        # No configuration, provider exception or credential is printed, even at startup failure.
        settings = Settings()
        report = asyncio.run(run_cases(settings, cases, args.reference_date, git_sha()))
        write_report(report, args.output)
    except Exception:
        print(
            "Live acceptance could not complete; configuration/output failure details withheld",
            file=sys.stderr,
        )
        return 2
    print(
        f"total={report.total} passed={report.passed} failed={report.failed}; JSON report written"
    )
    return 1 if report.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
