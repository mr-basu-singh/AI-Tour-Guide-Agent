from src.state import AgentState
from src.config import invoke_structured
from src.tools.search import search_web
from src.schemas import PlaceSuggestions
from src.agents.feasibility import check_feasibility


def _build_query(req: dict) -> str:
    parts = [req.get("trip_vibe", "")]
    if req.get("destination_type") and req["destination_type"] != "Suggest by Agent":
        parts.append(req["destination_type"])
    if req.get("region_preference") and req["region_preference"] != "Suggest by Agent":
        parts.append(req["region_preference"])
    else:
        parts.append(f"near {req.get('origin_city', '')}")
    parts.append(f"for {req.get('group_type', '')}")
    # only clean travel-related terms — no exclusions, no "DO NOT" instructions
    clean_special = req.get("special_requirements", "")
    # strip any "DO NOT suggest" text that may have leaked in from earlier bugs
    if "DO NOT suggest" in clean_special:
        clean_special = clean_special.split("DO NOT suggest")[0].strip().rstrip(";").strip()
    if clean_special:
        parts.append(clean_special)
    if req.get("place_preference") == "Hidden Gems":
        parts.append("offbeat hidden gems")
    if req.get("_search_hint"):
        parts.append(req["_search_hint"])
    return " ".join(p for p in parts if p)


def _messages(req: dict, context: str, excluded: list = None):
    days = 1
    try:
        from datetime import date
        s = date.fromisoformat(req["start_date"])
        e = date.fromisoformat(req["end_date"])
        days = (e - s).days + 1
    except Exception:
        pass

    # combine both sources of exclusions
    all_excluded = list(excluded or [])
    req_excluded = req.get("_excluded_places", [])
    if isinstance(req_excluded, list):
        all_excluded.extend(req_excluded)
    elif isinstance(req_excluded, str) and req_excluded:
        all_excluded.extend([x.strip() for x in req_excluded.split(",") if x.strip()])

    exclude_note = ""
    if all_excluded:
        unique_excluded = list(dict.fromkeys(all_excluded))  # deduplicate, keep order
        exclude_note = f"\nDO NOT suggest these places (already shown to the user): {', '.join(unique_excluded)}\n"

    # build strict matching criteria from the form
    criteria = []
    if req.get("destination_type") and req["destination_type"] != "Suggest by Agent":
        criteria.append(f"- Destination type MUST be: {req['destination_type']}")
    if req.get("region_preference") and req["region_preference"] != "Suggest by Agent":
        criteria.append(f"- Region MUST be: {req['region_preference']}")
    if req.get("weather_pref") and req["weather_pref"] != "No Preference":
        criteria.append(f"- Weather must suit: {req['weather_pref']}")
    if req.get("place_preference") and req["place_preference"] != "A Mix of Both":
        criteria.append(f"- Place style: {req['place_preference']}")
    if req.get("trip_vibe"):
        criteria.append(f"- ONLY suggest places that match THESE activities: {req['trip_vibe']}")
        criteria.append(f"- Do NOT recommend places primarily known for activities the user did NOT select")
    if req.get("activities_to_avoid"):
        criteria.append(f"- MUST AVOID places known for: {req['activities_to_avoid']}")
    if req.get("priority_activity"):
        criteria.append(f"- MUST strongly support this priority activity: {req['priority_activity']}")
    if req.get("senior_citizens"):
        criteria.append("- Must be suitable for senior citizens (easy access, not strenuous)")
    if req.get("children_traveling"):
        criteria.append("- Must be child-friendly")
    if req.get("wheelchair_needed"):
        criteria.append("- Must have wheelchair-accessible facilities")
    if req.get("food_pref") and "No Preference" not in req.get("food_pref", ""):
        criteria.append(f"- Food availability must support: {req['food_pref']}")

    origin = req.get("origin_city", "")
    criteria.append(f"- NEVER suggest {origin} or places within {origin}. "
                    f"The traveler LIVES in {origin} — they want to go AWAY from home, not stay in their own city.")
    criteria_str = "\n".join(criteria) if criteria else "No specific hard constraints."

    system = (
        "You are an expert travel guide. Using ONLY the SEARCH RESULTS, suggest 3 to 5 "
        "real destinations that STRICTLY match ALL the traveler's criteria below.\n\n"
        f"STRICT MATCHING CRITERIA:\n{criteria_str}\n\n"
        f"This is a {days}-day trip by {req.get('transport_mode')}. "
        f"Only suggest places reachable from {req.get('origin_city')} within a reasonable "
        f"travel time for a {days}-day trip.\n"
        "Give an honest downside for each. Choose one top recommendation.\n"
        f"{exclude_note}"
    )
    human = (
        f"TRAVELER:\n"
        f"- From: {req.get('origin_city')}, {req.get('origin_country')}\n"
        f"- Dates: {req.get('start_date')} to {req.get('end_date')} ({days} days)\n"
        f"- Group: {req.get('group_type')} ({req.get('num_travelers')} people)\n"
        f"- Budget: {req.get('total_budget', 0)} ({req.get('budget_scope')})\n"
        f"- Transport: {req.get('transport_mode')}\n"
        f"- Activities wanted: {req.get('trip_vibe')}\n"
        f"- Activities to avoid: {req.get('activities_to_avoid', 'none')}\n"
        f"- Priority activity: {req.get('priority_activity', 'none')}\n"
        f"- Destination type: {req.get('destination_type')}\n"
        f"- Region: {req.get('region_preference')}\n"
        f"- Weather: {req.get('weather_pref')}\n"
        f"- Place style: {req.get('place_preference')}\n"
        f"- Special needs: {req.get('special_requirements')}\n\n"
        f"SEARCH RESULTS:\n{context}"
    )
    return [("system", system), ("human", human)]


def research_node(state: AgentState) -> dict:
    if state.get("error"):
        return {}
    req = state["request"]

    # carry excluded places from raw input (survives Pydantic validation)
    raw = state.get("raw_input", {})
    if raw.get("_excluded_places"):
        req = dict(req)  # make a copy so we can add the field
        req["_excluded_places"] = raw["_excluded_places"]

    # if the user already named a place, skip suggestions
    if req.get("place_in_mind"):
        user_place = req["place_in_mind"].strip()

        # check for excluded places from re-suggest
        excluded = req.get("_excluded_places", [])
        exclude_note = ""
        if excluded:
            exclude_note = f"\nDO NOT suggest these places (already shown): {', '.join(excluded)}\n"

        # search 1: the user's place itself
        context1 = search_web(f"{user_place} travel guide overview", max_results=4)

        # search 2: similar nearby places
        hint = req.get("_search_hint", "")
        context2 = search_web(
            f"places similar to {user_place} nearby alternatives {req.get('trip_vibe', '')} "
            f"for {req.get('group_type', '')} {hint}",
            max_results=6)

        context = ""
        if not context1.startswith("SEARCH_ERROR"):
            context += f"ABOUT {user_place.upper()}:\n{context1}"
        if not context2.startswith("SEARCH_ERROR"):
            context += f"\n\nSIMILAR PLACES NEARBY:\n{context2}"

        if not context:
            return {"suggestions": {
                "suggestions": [],
                "top_recommendation": user_place,
                "reasoning": "User-provided destination.",
            }}

        system = (
            f"The traveler wants to visit '{user_place}'. Using the SEARCH RESULTS:\n\n"
            f"1. Include '{user_place}' as the FIRST suggestion — describe why it fits the traveler.\n"
            f"2. Then suggest 2-4 OTHER DIFFERENT destinations (not parts of {user_place} like "
            f"'{user_place} Mall Road' or '{user_place} Lake') that are:\n"
            f"   - Similar in vibe and character to {user_place}\n"
            f"   - Located nearby or in the same region\n"
            f"   - Matching the traveler's preferences\n"
            f"3. Each suggestion must be a SEPARATE TOWN or CITY, not a location within {user_place}.\n"
            f"   WRONG: 'Mussoorie Mall Road', 'Mussoorie Tibetan Market'\n"
            f"   RIGHT: 'Mussoorie', 'Dhanaulti', 'Kanatal', 'Landour'\n"
            f"4. Give an honest downside for each place.\n"
            f"5. Set top_recommendation to '{user_place}' since the traveler specifically asked for it.\n"
            f"{exclude_note}"
        )
        human = (
            f"TRAVELER:\n"
            f"- From: {req.get('origin_city')}, {req.get('origin_country')}\n"
            f"- Dates: {req.get('start_date')} to {req.get('end_date')}\n"
            f"- Group: {req.get('group_type')} ({req.get('num_travelers')} people)\n"
            f"- Budget: {req.get('total_budget', 0)} ({req.get('budget_scope')})\n"
            f"- Transport: {req.get('transport_mode')}\n"
            f"- Activities: {req.get('trip_vibe')}\n"
            f"- Weather: {req.get('weather_pref')}\n"
            f"- Special needs: {req.get('special_requirements')}\n\n"
            f"USER'S CHOSEN PLACE: {user_place}\n\n"
            f"SEARCH RESULTS:\n{context}"
        )

        try:
            result = invoke_structured(PlaceSuggestions, [("system", system), ("human", human)])
        except Exception as e:
            return {"suggestions": {
                "suggestions": [],
                "top_recommendation": user_place,
                "reasoning": f"User-provided destination.",
            }}

        return {"suggestions": result.model_dump()}
    excluded = []
    max_rounds = 3  # avoid infinite loop

    for attempt in range(max_rounds):
        context = search_web(_build_query(req))
        if context.startswith("SEARCH_ERROR"):
            return {"error": f"Could not fetch destination data. {context}"}

        try:
            result = invoke_structured(PlaceSuggestions, _messages(req, context, excluded))
        except Exception as e:
            return {"error": f"Could not generate suggestions: {e}"}

        raw = result.model_dump()

        # feasibility check each suggestion
        feasible = []
        for s in raw["suggestions"]:
            verdict = check_feasibility(
                origin=req["origin_city"], place=s["name"],
                mode=req["transport_mode"], budget=req["total_budget"],
                n_travelers=req["num_travelers"],
                start=req["start_date"], end=req["end_date"],
            )
            if verdict["feasible"]:
                feasible.append(s)
            else:
                excluded.append(s["name"])
                # annotate the suggestion with the reason (for potential alt-mode suggestion)
                alt = verdict.get("alternative")
                if alt:
                    s["possible_downside"] = (f"Not feasible by {req['transport_mode']} "
                                              f"({verdict['reason']}). "
                                              f"Consider {alt} instead.")

        if len(feasible) >= 2:
            raw["suggestions"] = feasible
            if raw["top_recommendation"] not in [s["name"] for s in feasible]:
                raw["top_recommendation"] = feasible[0]["name"]
            return {"suggestions": raw}

    # if after all rounds we still have too few, return what we have with a note
    if feasible:
        raw["suggestions"] = feasible
        raw["top_recommendation"] = feasible[0]["name"]
        raw["reasoning"] += " (limited options found for your constraints)"
        return {"suggestions": raw}

    return {"error": (f"Could not find places reachable from {req['origin_city']} "
                      f"by {req['transport_mode']} within your trip dates and budget. "
                      f"Try a longer trip, higher budget, or different transport mode.")}