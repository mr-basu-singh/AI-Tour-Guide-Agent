from src.state import AgentState
from src.config import invoke_structured
from src.tools.search import search_web
from src.schemas import HotelPreferences, HotelOptions
from src.rooms import suggest_room_config


def _messages(place, prefs, context, currency_code=""):
    band = ""
    if prefs.hotel_per_night_min or prefs.hotel_per_night_max:
        band = f"Traveler's price band per night: {prefs.hotel_per_night_min}–{prefs.hotel_per_night_max}.\n"
    
    currency_note = ""
    if currency_code:
        currency_note = (f"IMPORTANT: Extract prices in {currency_code}. If the search results "
                        f"show prices in USD or other currencies, convert approximately to {currency_code}. "
                        f"For example if a result shows $50 and currency is INR, put 4000-4500 as the range.\n")

    system = (
        "You are a hotel finder. Using the SEARCH RESULTS, list 3 to 5 real, named "
        "places to stay in the destination.\n\n"
        "CRITICAL: You MUST extract a per-night price for each hotel. Look for:\n"
        "- Numbers with ₹, $, Rs, INR, USD near hotel names\n"
        "- 'starting from', 'from', 'per night', 'avg price' mentions\n"
        "- Price ranges in the search snippets\n"
        f"{currency_note}"
        "If you genuinely cannot find ANY price for a hotel, set per_night_min to null — "
        "but try hard to find one. Most search results contain prices.\n\n"
        "Never invent a hotel name. Prefer options matching the traveler's property type "
        "and area preference."
    )
    human = (
        f"DESTINATION: {place}\n"
        f"Property type: {prefs.property_type}\n"
        f"Preferred area: {prefs.preferred_area}\n"
        f"Amenities wanted: {prefs.amenities}\n"
        f"{band}\n"
        f"SEARCH RESULTS:\n{context}"
    )
    return [("system", system), ("human", human)]


def hotel_node(state: AgentState) -> dict:
    if state.get("error"):
        return {}
    req = state["request"]
    place = state["selected_place"]
    prefs = HotelPreferences(**state.get("hotel_prefs", {}))
    currency_code = state.get("home_currency", "")

    # 1. room configuration (pure Python)
    room_config = suggest_room_config(req["group_type"], req["num_travelers"], prefs)

    # 2. hotel search — two queries for better coverage
    ptype = "" if prefs.property_type == "any" else prefs.property_type
    extra = state.get("hotel_query_extra", "")

    # query 1: named hotels with prices
    query1 = f"best {ptype} hotels in {place} price per night {currency_code} {prefs.preferred_area} {extra}".strip()
    context1 = search_web(query1, max_results=6)

    # query 2: budget/cheap options with rates
    query2 = f"cheap budget {ptype} hotels in {place} room rate cost per night".strip()
    context2 = search_web(query2, max_results=4)

    context = ""
    if not context1.startswith("SEARCH_ERROR"):
        context += context1
    if not context2.startswith("SEARCH_ERROR"):
        context += f"\n\nADDITIONAL RESULTS:\n{context2}"

    hotels, note = [], ""
    if context:
        try:
            result = invoke_structured(HotelOptions, _messages(place, prefs, context, currency_code))
            hotels = result.model_dump()["hotels"]
            if not hotels:
                note = "No specific hotels found in search; use the booking link."
        except Exception as e:
            note = f"Hotel extraction issue: {e}"
    else:
        note = "Could not fetch hotel listings; use the booking link."

    # 3. booking link
    link = f"https://www.booking.com/searchresults.html?ss={place.replace(' ', '+')}"
    for h in hotels:
        if not h.get("booking_link"):
            h["booking_link"] = link

    return {"room_config": room_config.model_dump(), "hotels": hotels,
            "hotel_note": note, "hotel_booking_link": link}