from src.config import invoke_structured
from src.schemas import RefineIntent
from src.agents.hotel import hotel_node
from src.agents.itinerary import itinerary_node
from src.agents.budget import budget_node


def _classify(command: str) -> dict:
    system = (
        "Classify the traveler's change request into exactly one action:\n"
        "- cheaper: reduce the cost / lower the budget\n"
        "- swap_hotel: different hotel or stay options\n"
        "- change_itinerary: change the day plan or activities\n"
        "- change_place: a different destination\n"
        "- unclear: none of these\n"
        "Put any specifics in 'detail'."
    )
    intent = invoke_structured(RefineIntent, [("system", system), ("human", command)],
                               large=False).model_dump()
    low = command.lower()
    if intent["action"] == "unclear":
        if any(w in low for w in ("cheap", "budget", "less", "lower", "save")):
            intent["action"] = "cheaper"
        elif any(w in low for w in ("hotel", "stay", "room", "resort")):
            intent["action"] = "swap_hotel"
        elif any(w in low for w in ("day", "itinerary", "activit", "plan", "visit")):
            intent["action"] = "change_itinerary"
        elif any(w in low for w in ("place", "destination", "somewhere else")):
            intent["action"] = "change_place"
    return intent


def refine(state: dict, command: str):
    """Re-run the right specialist based on a free-text change request.
    Returns (updated_state, message)."""
    intent = _classify(command)
    action = intent.get("action", "unclear")
    detail = intent.get("detail", "")
    s = dict(state)

    if action == "cheaper":
        # just re-run budget with a lower hotel band — no search needed
        prefs = dict(s.get("hotel_prefs", {}))
        old = prefs.get("hotel_per_night_min") or 1000
        prefs["hotel_per_night_min"] = max(500, round(old * 0.7))
        s["hotel_prefs"] = prefs
        s.update(budget_node(s))
        return s, f"Trimmed the budget. {s.get('budget_headline', '')}"

    if action == "swap_hotel":
        s["hotel_query_extra"] = detail or "alternative other options"
        s.update(hotel_node(s))
        s.update(budget_node(s))
        names = ", ".join(h["name"] for h in s.get("hotels", [])[:3])
        return s, f"New stay options: {names}"

    if action == "change_itinerary":
        s["itinerary_feedback"] = detail
        s.update(itinerary_node(s))
        return s, "Reworked the day-by-day plan."

    if action == "change_place":
        return s, "To change destination, click 'Start a new trip' and pick a different place."

    return s, "Didn't catch that — try 'make it cheaper', 'swap the hotel', or 'change the itinerary'."