"""Geographic language interpretation only; no geocoding or source access."""

from research_planner.analytics_prompts import ANALYTICS_PROMPT

GEOGRAPHY_PROMPT = (
    ANALYTICS_PROMPT.replace("AnalyticalQueryPlan", "GeographicQueryPlan").replace(
        "WHERE events take place -> aggregate by venue (physical place).",
        "WHERE events take place without a ranking request -> list events, answer_mode records.",
    )
    + """
GEOGRAPHIC V6 RULES (take precedence):
place_query is free geographic text, never an ID, coordinate, URL or SQL.
named street/square/local place -> place_query
named administrative region/city -> area_query
known event venue/business-like event location -> venue_query
Examples of place_query: Bachstraße Flensburg, Nordermarkt, Südermarkt,
Museumsberg, Flensburger Hafen, Am Nordertor 2.
Flensburg, Schleswig-Holstein, Hamburg remain area_query.
Volksbad, Kühlhaus, Aktivitetshuset remain venue_query.

Was ist heute in der Bachstraße Flensburg los?
-> list/event/records, place_query="Bachstraße Flensburg", temporal=today,
semantic_query=null, clarification=none, location_relation=none.
Was läuft am Nordermarkt? -> place_query="Nordermarkt", temporal=none.
Was gibt es heute am Südermarkt? -> place_query="Südermarkt", temporal=today.
Was gibt es in Flensburg? -> area_query="Flensburg", place_query=null.
Was läuft im Volksbad? -> venue_query="Volksbad", place_query=null.

wo / where / hvor ALONE never implies location permission or needs_location.
wo finden heute veranstaltungen statt? -> list/event/records, temporal=today,
clarification=none, location_relation=none, place_query=null, area_query=null,
venue_query=null, semantic_query=null, metric=none, group_by=none.
wo finden veranstaltungen statt? -> same, temporal=none.
Where do events take place? / Hvor finder arrangementer sted? -> same.
Only deictic phrases refer to the user's position: hier, bei mir, in meiner Nähe,
um mich herum, near me, around me, her, i nærheden.
Was ist hier los? / Was gibt es bei mir? / Welche Veranstaltungen sind bei mir?
/ Was ist in meiner Nähe? -> list/event/records, location_relation=nearby,
clarification=needs_location, place_query=null, area_query=null, venue_query=null.
Was ist heute in meiner Nähe? -> same with temporal=today.
The planner never receives coordinates. Admin satisfies needs_location from existing
UI context or asks for it. Preserve all other filters when location is missing.
Unused place_query=null and location_relation=none. Never geocode, infer coordinates,
query a database or transform place names into semantic_query.
"""
)
