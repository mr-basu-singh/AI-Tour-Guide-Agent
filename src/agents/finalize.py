from datetime import date
from urllib.parse import quote_plus
from src.state import AgentState
from src.config import invoke_structured
from src.tools.search import search_web
from src.schemas import TravelExtras
from src.tools.links import booking_links_for_leg, hotel_booking_links

PLAUSIBLE_NIGHTLY_FLOOR = 300


def _messages(place, month, req, context):
    system = (
        "You are a travel assistant. Using the SEARCH RESULTS plus general knowledge, give a "
        "practical packing list and honest safety/seasonal notes for this trip. Keep each item "
        "short. Only flag risks that genuinely apply to THIS destination's terrain and season "
        "(for example, do not mention landslides for flat plains areas, or snow for summer "
        "lowlands). Do not invent specific facts not supported by the results."
    )
    human = (
        f"DESTINATION: {place}\nTRAVEL MONTH: {month}\n"
        f"WEATHER WANTED: {req.get('weather_pref')}\n"
        f"SPECIAL NEEDS: {req.get('special_requirements')}\n\n"
        f"SEARCH RESULTS:\n{context}"
    )
    return [("system", system), ("human", human)]


def finalize_node(state: AgentState) -> dict:
    if state.get("error"):
        return {}
    req = state["request"]
    place = state["selected_place"]
    month = date.fromisoformat(req["start_date"]).strftime("%B")

    # 1. packing + safety, grounded in current seasonal conditions
    context = search_web(f"{place} {month} weather travel safety road conditions", max_results=5)
    packing, safety = [], []
    try:
        extras = invoke_structured(TravelExtras, _messages(place, month, req, context))
        d = extras.model_dump()
        packing, safety = d["packing_list"], d["safety_notes"]
    except Exception:
        pass  # graceful: empty lists if it fails

    # 2. booking order (deterministic)
    booking_order = [
        "Book transport first — fares rise as the date gets closer.",
        "Then book your stay using the booking link.",
        "Reserve any permits, safaris, or activities that need advance booking.",
    ]

    # 3. map link (free, worldwide)
    map_link = f"https://www.google.com/maps/search/?api=1&query={quote_plus(place)}"

    # 4. drop implausible hotel prices — floor depends on currency
    currency = state.get("home_currency", "INR")
    if currency in ("USD", "GBP", "EUR", "CAD", "AUD", "SGD", "CHF"):
        price_floor = 20  # $20/night minimum makes sense for these currencies
    elif currency in ("JPY",):
        price_floor = 2000  # ¥2000/night
    else:
        price_floor = 300  # ₹300 for INR and similar

    hotels = state.get("hotels", [])
    for h in hotels:
        if h.get("per_night_min") and h["per_night_min"] < price_floor:
            h["per_night_min"] = None
            h["per_night_max"] = None

    # 5. booking links for each transport leg (multiple sites)
    route = dict(state.get("route", {}))
    legs = [dict(leg) for leg in route.get("legs", [])]
    for leg in legs:
        if not leg.get("booking_links"):
            leg["booking_links"] = booking_links_for_leg(leg)
    route["legs"] = legs

    # 6. hotel booking links (multiple sites)
    h_links = hotel_booking_links(place)

    return {"packing_list": packing, "safety_notes": safety,
            "booking_order": booking_order, "map_link": map_link, "hotels": hotels,
            "route": route, "hotel_booking_links": h_links}