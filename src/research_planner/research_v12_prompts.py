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
"""
)
