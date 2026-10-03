# Recurring calendar contract audit and rollout

Audited Planner main `4c211c9` and Admin main `8a3868c` before implementation.
V9/prompt v15 has ordered `weekday` grouping and a scalar temporal `weekday`,
but no weekday set or cyclic month predicate. Saturday OR Sunday cannot be encoded
as two AND equality predicates. A month interval without a year is not an absolute
date interval. Adding required fields changes the strict public JSON contract.

Introduce additive `/v10/plan`, `research-query-plan-v10`, prompt
`research-planner-v16`. Keep v7/v13, v8/v14 and v9/v15 unchanged.
V10 temporal objects add required `recurring_weekdays` and `recurring_months`
arrays. Empty arrays mean unrestricted. Weekdays are ISO integers 1 (Monday)
through 7 (Sunday); months are integers 1 through 12. Sets are unique, bounded,
and combine with each other and any concrete date bounds using AND. Values within
each set use OR. They constrain occurrence start_date, not metadata timestamps.
The legacy scalar weekday must not coexist with a nonempty weekday set.

Concrete audience record requests use search/event/semantic; missing structured
audience metadata is not itself a reason to ask for a definition. Quantitative
audience operations retain their intent and insufficient_structured_data. Vague
evaluative suitability may still need a definition. No exact semantic counts.

Admin normalizes into the shared internal temporal selection and grouped executor.
No new executor, migration or timezone conversion is required. Concrete single-month
year defaults are resolved by the Planner using the supplied local reference_date.
Rollout: deploy compatible Planner and Admin, pass model acceptance gates, then
explicitly opt in with `RESEARCH_PLANNER_CONTRACT=v10`. Default stays legacy;
rollback selects legacy or v9. Mocked tests prove contracts/execution, not live
model language accuracy. No production activation is part of this change.

## Single concrete month default

A standalone month used as a date period without an explicit year uses the year
of the supplied local `reference_date`, never the next occurrence. With
`reference_date=2026-10-03`, “wie viele Events im Oktober” returns count/event_count,
`temporal.field=start_date`, `period=explicit_range`, `from_date=2026-10-01`,
`to_date=2026-10-31`, and `clarification=none`. “Veranstaltungen im Januar” uses
January **2026**, not 2027. Explicit years always take precedence.

“jeden Oktober”, “im Oktober typischerweise”, and clearly seasonal October
analysis use `recurring_months=[10]` across years. “von Juli bis September” uses
`[7,8,9]` without a guessed year; adding 2026 produces July 1 through September 30,
2026. Existing combinations of explicitly requested recurring constraints and
concrete bounds remain supported.

The application supplies calendar-derived inclusive month bounds for the local
reference year and explicit four-digit year candidates. These calendar facts do
not classify the query: the model chooses concrete versus recurring semantics.
Calendar generation reads no independent clock. February 2024 ends on the 29th;
February 2026 on the 28th. Strict output validation rejects invalid dates and
incomplete or reversed ranges. No schema or older-contract change is required.

Offline tests cover all 12 months, leap and century rules, explicit years,
recurring semantics, local New Year boundaries, and model/API transport. Mocked
responses verify contract handling, not live language accuracy. Additional live
acceptance is opt-in against a configured provider:

```sh
RESEARCH_PLANNER_LIVE_TEST=1 uv run pytest -q tests/test_research_v10_live.py
```
