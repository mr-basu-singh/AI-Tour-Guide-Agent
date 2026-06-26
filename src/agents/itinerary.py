from datetime import date
from src.state import AgentState
from src.config import invoke_structured
from src.tools.search import search_web
from src.schemas import Itinerary


def _compute_trip_structure(req: dict) -> dict:
    start = date.fromisoformat(req["start_date"])
    end = date.fromisoformat(req["end_date"])
    total_calendar_days = (end - start).days + 1

    dep = (req.get("departure_timing") or "any").lower()
    ret = (req.get("return_timing") or "any").lower()

    dep_is_night = any(w in dep for w in ("night", "8 pm", "evening", "pm –", "pm -",
                                           "late night", "12 am", "6 pm"))
    ret_is_evening = any(w in ret for w in ("night", "8 pm", "evening", "pm –", "pm -",
                                             "late night", "12 am", "6 pm"))

    activity_days = total_calendar_days
    if dep_is_night:
        activity_days -= 1
    activity_days = max(1, activity_days)

    return {
        "total_calendar_days": total_calendar_days,
        "activity_days": activity_days,
        "dep_is_night": dep_is_night,
        "ret_is_evening": ret_is_evening,
    }


def _messages(req, place, route, context, trip_info, feedback=""):
    n_days = trip_info["activity_days"]

    if trip_info["dep_is_night"]:
        day1_note = (f"The traveler departs on {req['start_date']} evening/night and arrives "
                     f"the NEXT MORNING. Day 0 is just boarding — no sightseeing. "
                     f"The first full activity day is the day AFTER departure.")
    else:
        day1_note = f"The traveler departs on {req['start_date']} and arrives the same day."

    if trip_info["ret_is_evening"]:
        last_note = (f"On {req['end_date']}, the traveler departs in the evening, "
                     f"so they have the full day for activities before leaving.")
    else:
        last_note = f"On {req['end_date']}, the traveler departs."

    system = (
        "You are an expert local tour guide who knows this destination intimately. "
        "Build a DETAILED day-by-day plan using ONLY real places from the SEARCH RESULTS.\n\n"
        "RULES:\n"
        "- Each activity day MUST have 5-7 entries covering morning, afternoon, and evening\n"
        "- Format each entry as: 'Morning: [Place Name] — [what to do, time to spend, tips]'\n"
        "- MUST include food: where to eat breakfast, lunch, dinner (real restaurant or cafe names from results)\n"
        "- Include practical details: best time to visit, entry fee if known, what to carry\n"
        "- Include a sunset/evening activity for each day\n"
        "- If the traveler arrives in the morning after an overnight journey, the first activity should be check-in and freshening up, then a leisurely brunch\n"
        "- The last day should end with packing and heading to the bus/train station\n"
        "- Match the traveler's selected activities and pace\n"
        "- Make it feel like a real tour guide wrote this, not a generic list\n\n"
        f"TRAVEL TIMING:\n{day1_note}\n{last_note}\n"
        "Never invent attractions not in the search results."
    )
    change = f"APPLY THIS CHANGE REQUEST: {feedback}\n" if feedback else ""
    human = (
        f"DESTINATION: {place}\n"
        f"DATES: {req['start_date']} to {req['end_date']} ({n_days} activity days)\n"
        f"DEPARTURE TIMING: {req.get('departure_timing', 'any')}\n"
        f"RETURN TIMING: {req.get('return_timing', 'any')}\n"
        f"GROUP: {req.get('group_type')} ({req.get('num_travelers')} people)\n"
        f"PACE: {req.get('pace')}\n"
        f"ACTIVITIES WANTED: {req.get('trip_vibe')}\n"
        f"FOOD PREFERENCE: {req.get('food_pref', 'any')}\n"
        f"PURPOSE: {req.get('purpose')}\n"
        f"SPECIAL NEEDS: {req.get('special_requirements')}\n"
        f"ARRIVAL ROUTE: {route.get('summary', '')}\n"
        f"{change}\n"
        f"SEARCH RESULTS (attractions + food + activities):\n{context}"
    )
    return [("system", system), ("human", human)]


def itinerary_node(state: AgentState) -> dict:
    if state.get("error"):
        return {}
    req = state["request"]
    place = state["selected_place"]
    route = state.get("route", {})
    feedback = state.get("itinerary_feedback", "")

    trip_info = _compute_trip_structure(req)

    # broader search for richer results
    context1 = search_web(
        f"top things to do in {place} complete itinerary morning afternoon evening",
        max_results=6)
    context2 = search_web(
        f"best restaurants cafes street food in {place} where to eat",
        max_results=4)

    context = ""
    if not context1.startswith("SEARCH_ERROR"):
        context += context1
    if not context2.startswith("SEARCH_ERROR"):
        context += f"\n\nFOOD & DINING:\n{context2}"

    if not context:
        return {"error": f"Could not fetch attractions for {place}."}

    try:
        result = invoke_structured(Itinerary,
                                   _messages(req, place, route, context, trip_info, feedback))
    except Exception as e:
        return {"error": f"Could not build the itinerary: {e}"}

    return {"itinerary": result.model_dump()["days"]}