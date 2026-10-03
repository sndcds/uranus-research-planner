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
No new executor, migration, timezone conversion or year inference is required.
Rollout: deploy compatible Planner and Admin, pass model acceptance gates, then
explicitly opt in with `RESEARCH_PLANNER_CONTRACT=v10`. Default stays legacy;
rollback selects legacy or v9. Mocked tests prove contracts/execution, not live
model language accuracy. No production activation is part of this change.
