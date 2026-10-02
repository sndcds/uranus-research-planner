"""Offline developer report; never imported by the service."""

import json
from collections import Counter

from tests.v7_golden import example_plan, load_v7_golden_cases


def report() -> dict[str, object]:
    cases = load_v7_golden_cases()
    plans = [(c, example_plan(c)) for c in cases]
    return {
        "total_questions": len(cases),
        "by_category": dict(sorted(Counter(c.category for c in cases).items())),
        "by_capability_status": dict(sorted(Counter(c.capability_status for c in cases).items())),
        "by_intent": dict(sorted(Counter(p.intent for _, p in plans).items())),
        "by_entity_type": dict(sorted(Counter(p.entity_type or "none" for _, p in plans).items())),
        "features": {
            "structured": sum(
                p.intent not in {"knowledge", "explain"} and p.semantic is None for _, p in plans
            ),
            **{
                name: sum(getattr(p, name) is not None for _, p in plans)
                for name in ("spatial", "semantic", "relation", "trend", "knowledge")
            },
            **{
                name: sum(c.capability_status == name for c in cases)
                for name in ("needs_definition", "needs_structured_data", "needs_context")
            },
        },
        "questions_by_capability": {
            status: [
                {
                    "id": c.id,
                    "question": c.question,
                    "notes": c.notes,
                    "required_data": c.required_data,
                }
                for c in cases
                if c.capability_status == status
            ]
            for status in sorted({c.capability_status for c in cases})
        },
    }


if __name__ == "__main__":
    print(json.dumps(report(), ensure_ascii=False, indent=2))
