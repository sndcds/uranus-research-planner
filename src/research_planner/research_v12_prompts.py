"""V12 retains modern semantics and restores v8 administrative expectations."""

from research_planner.research_v11_prompts import RESEARCH_V11_PROMPT

RESEARCH_V12_PROMPT_VERSION = "research-planner-v18"
RESEARCH_V12_PROMPT = (
    RESEARCH_V11_PROMPT.replace("ResearchQueryPlanV11", "ResearchQueryPlanV12").replace(
        "all nested objects null, arrays []", "all nested objects null, spatial=[], arrays []"
    )
    + """
V12 ADMINISTRATIVE GEOGRAPHY (specializes prior spatial and context rules):
spatial is ALWAYS an array, [] if unused; never null or a single object. Up to FOUR
predicates combined by AND. Multiple predicates must be named inside/outside area
membership. Values are unresolved wording, not geographic facts. No Boolean trees,
OR/NOT DSL, IDs, codes, AGS, ISO, OSM, coordinates, geometry or parent identities.
Every spatial object includes area_level: municipality|district|state|country|region|null.
Administrative inside/outside uses reference=named, area_query, place_query=null,
radius_m=null. area_level is the expected administrative kind, NOT resolved authority.
Kreis/Landkreis -> district; Bundesland -> state; Gemeinde/Stadt -> municipality;
Deutschland used administratively -> country; Norddeutschland -> region.
"im Kreis Schleswig-Flensburg" -> area_query="Schleswig-Flensburg", area_level=district.
"im Bundesland Schleswig-Holstein" -> area_query="Schleswig-Holstein", area_level=state.
"in der Gemeinde Harrislee" -> area_query="Harrislee", area_level=municipality.
"in Deutschland" -> Deutschland/country; "in Norddeutschland" -> Norddeutschland/region.
"in Schleswig-Holstein" -> Schleswig-Holstein/state when used as the named state.
"im Kreis Schleswig" -> area_query="Schleswig", area_level=district. Preserve informal/
historic lexical names; NEVER invent an official name or change it to Schleswig-Flensburg.
Admin/geocoder resolves one district, district ambiguity or no district. Never substitute
municipalities. Unknown expected level stays null; no fabricated authoritative identity.
Non-administrative place_query and user_location require area_level=null. Keep existing
radius/place/border semantics separate; administrative membership is not a radius lookup.
"außerhalb Schleswig-Holsteins, innerhalb Deutschlands" -> TWO predicates:
outside/named/Schleswig-Holstein/state AND inside/named/Deutschland/country.
Unrepresentable composition (>4, OR, mixed radius/place and administrative predicates)
requires unsupported_reason=unsupported_constraint; NEVER silently drop a requested clause
or emit an executable partial interpretation. Preserve all representable constraints.
"Veranstaltungen am Wochenende im Kreis Schleswig" -> list/event, recurring_weekdays=[6,7],
period=none, null dates, district Schleswig. Generic weekend is recurring, not this_weekend.
"von Juli bis September in Schleswig-Holstein besonders stark" retains recurring_months
[7,8,9] AND state Schleswig-Holstein; no year guessed. A concrete single month still uses
reference_date's CURRENT year (January is not next year), with application calendar bounds;
explicit years override it, recurring wording (jeden Oktober) still means recurring_months=[10].
Ordered multidimensional group_by is unchanged: event_type×month, event_type×weekday,
category×municipality all compose with administrative filters; never replace grouping with area.
Conversation areas now retain name, relation and expected_level, up to four AND constraints.
They remain advisory, bounded (four summaries, 2048 bytes each, 8192 total), identity-free.
After "Veranstaltungen im Kreis Schleswig-Flensburg", "Und nur sonntags?" retains the
inside district expectation and sets recurring_weekdays=[7], no concrete dates. An explicit
new place/level overrides inherited geography. Other compatible prior constraints survive.
Current query and exact original_query rules, context privacy, and needs_context for visible
result identities remain unchanged. No raw transcript, results, SQL, parameters or auth data.

V12 SEASONAL DISTRIBUTIONS (specializes generic strength/rank and anomaly rules):
"Welche Veranstaltungstypen treten saisonal besonders stark auf?" asks for the event-type
by calendar-month distribution of occurrences, NOT a global event-type ranking, anomaly,
trend, frequency/regularity metric or a derived seasonality score. No year is implied.
Return this complete plan, copying the actual current query exactly into original_query:
{
  "original_query": "Welche Veranstaltungstypen treten saisonal besonders stark auf?",
  "intent": "aggregate", "entity_type": "event",
  "metric": {"operation": "occurrence_count", "field": null, "distinct_by": null,
             "numerator": null, "denominator": null, "measure": null,
             "window": null, "currency": null},
  "group_by": ["event_type", "month"], "ordering": "desc", "limit": 20,
  "filters": [], "metric_filter": null, "taxonomy": null, "temporal": null,
  "spatial": [], "price": null, "semantic": null, "relation": null, "trend": null,
  "anomaly": null, "explain": null, "knowledge": null, "comparison_targets": [],
  "clarification": "none", "unsupported_reason": null
}
Equivalent questions use the same interpretation:
"Welche Eventtypen sind saisonal besonders stark?"
"Welche Veranstaltungstypen haben saisonale Schwerpunkte?"
"Wann treten welche Veranstaltungstypen besonders stark auf?"
"Which event types are particularly strong seasonally?"
"Hvilke arrangementstyper er sæsonmæssigt særligt stærke?"
"Welche Genres treten saisonal besonders stark auf?" uses [genre,month] instead.
Month is a GROUPING dimension here, never metric.window. Count metrics require measure=null
and window=null; do not copy occurrence_count into measure or month into window.
Without a requested date/weekday/month restriction, temporal MUST be null. Do not emit an
all-neutral temporal object (period=none, empty recurring sets): that is invalid. Null temporal
means no recurring-month subset and no concrete dates; never needs_date for this distribution.
Only actual requested or compatibly inherited restrictions create a temporal object:
- "Welche Veranstaltungstypen sind sonntags besonders stark?" -> aggregate/event,
  occurrence_count, group_by=[event_type], desc/20; recurring_weekdays=[7],
  recurring_months=[], period=none, null dates. No invented weekday/month grouping.
- "Welche Veranstaltungstypen sind im Oktober saisonal stark?" -> same aggregate/count,
  group_by=[event_type], recurring_months=[10], recurring_weekdays=[], period=none,
  null dates. Include month in group_by ONLY if a month distribution is requested.
- "Welche Veranstaltungstypen sind im Oktober 2025 besonders stark?" -> same aggregate/count,
  group_by=[event_type], start_date/explicit_range with supplied full October 2025 bounds,
  recurring_months=[], recurring_weekdays=[]. Explicit year wins over reference year.
Concrete single-month questions still use the CURRENT reference year; recurring wording
and yearless month ranges keep their recurring filters. Requested weekday distributions
still use [event_type,weekday], never month. These are counts, not seasonality scores.
Preserve requested administrative predicates and compatible conversation constraints;
current wording overrides inherited semantics as before. No anomaly/rank fallback or schema
repair. The unrestricted example is not permission to drop a requested time or area filter.
"""
)
