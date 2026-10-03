"""Additive calendar and concrete audience interpretation, with no runtime question rules."""

from research_planner.research_v9_prompts import RESEARCH_V9_PROMPT

RESEARCH_V10_PROMPT_VERSION = "research-planner-v16"
RESEARCH_V10_PROMPT = (
    RESEARCH_V9_PROMPT.replace("ResearchQueryPlanV9", "ResearchQueryPlanV10").replace(
        "missing year => needs_date, no guessed year or invalid explicit_range object.",
        "Missing year for concrete dates => needs_date. "
        "Bare month ranges instead use recurring_months.",
    )
    + """
V10 RECURRING CALENDAR (these rules specialize the preceding generic time rules):
Each temporal object includes recurring_weekdays and recurring_months, empty [] when unused.
recurring_weekdays: unique ISO integers Monday=1, Tuesday=2, Wednesday=3, Thursday=4,
Friday=5, Saturday=6, Sunday=7. recurring_months: unique integers January=1 through December=12.
Use ascending set order. Values within a set are OR; sets and date bounds combine with AND.
Use field=start_date. No implicit year, date, timezone conversion or guessed date bounds.
Recurring weekday wording (sonntags, samstags, on Sundays, om søndagen) restricts weekdays,
NOT the next occurrence of that day. Generic am Wochenende/in recurring frequency analysis
means [6,7]; explicit dieses/kommendes Wochenende or this/coming weekend means this_weekend.
Concrete dated Sunday remains a concrete date. Bare July-to-September means months [7,8,9];
November-to-February means [1,2,11,12]. Month range with explicit year keeps explicit_range.
Recurring sets may coexist with explicit date bounds when BOTH restrictions are requested.
No date restriction => period=none, from_date/to_date=null. Use weekday=null with recurring sets.
Weekday distributions use group_by=[weekday], count logical events if explicitly requested,
occurrence_count for term frequencies. Event-type/genre strength by weekday is aggregate/event,
occurrence_count, group_by=[event_type,weekday] or [genre,weekday], desc/20, clarification=none.
Specific recurring weekday/weekend strength: aggregate/event/occurrence_count and the requested
[event_type] or [genre] grouping plus weekday set; never invent a date or a second grouping.
Type/genre strength during a recurring month subset: same structured counts plus month set;
include month in group_by ONLY when the month distribution itself is requested.
Deterministic calendar frequency is never semantic, trend or anomaly merely for 'besonders stark'.

CONCRETE AUDIENCE RECORDS:
Named audience concepts such as Schüler:innen, Familien, Jugendliche are concrete search
concepts. Records for these audiences: search/event, semantic.query preserves the actual
requested audience concept, clarification=none, unsupported_reason=null. Lack of an exact
structured audience taxonomy does not imply needs_definition. Preserve hard time/place/type
filters. No invented keywords, taxonomy IDs or records.
Undefined evaluative criteria (besonders gut, pädagogisch wertvoll) may need_definition.
Quantitative audience requests keep count/aggregate/rank etc., the semantic condition and
insufficient_structured_data; never convert them to search or claim an exact semantic count.
"""
)
