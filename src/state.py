from typing import TypedDict


class AgentState(TypedDict, total=False):
    raw_input: dict
    request: dict
    hotel_prefs: dict
    home_currency: str
    currency_symbol: str
    suggestions: dict
    selected_place: str
    route: dict
    itinerary: list
    room_config: dict
    hotels: list
    hotel_note: str
    hotel_booking_links: list
    budget: dict
    budget_headline: str
    packing_list: list
    safety_notes: list
    booking_order: list
    map_link: str
    hotel_query_extra: str
    itinerary_feedback: str
    error: str