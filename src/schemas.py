from datetime import date
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator, model_validator


# ===================== INPUT =====================

class TripRequest(BaseModel):
    # page 1 — basics
    origin_city: str
    origin_country: str
    start_date: date
    end_date: date
    num_travelers: int
    group_type: str
    total_budget: float = 0
    budget_scope: str = "whole group"
    transport_mode: str
    departure_timing: str = "any"
    return_timing: str = "any"

    # page 2 — destination
    place_in_mind: str = ""
    destination_type: str = "Suggest by Agent"
    region_preference: str = "Suggest by Agent"
    weather_pref: str = "No Preference"
    place_preference: str = "A Mix of Both"   # popular / hidden gems / mix
    max_travel_hours: Optional[int] = None

    # page 3 — activities
    trip_vibe: str = ""
    custom_activities: str = ""
    priority_activity: str = ""
    activities_to_avoid: str = ""

    # page 4 — accommodation
    hotel_type: str = "any"
    # hotel budget handled separately in HotelPreferences

    # page 5 — food
    food_pref: str = "No Preference"
    food_allergies: str = ""
    foods_to_avoid: str = ""

    # page 6 — special requirements
    senior_citizens: bool = False
    children_traveling: bool = False
    mobility_restrictions: bool = False
    wheelchair_needed: bool = False
    medical_considerations: str = ""
    special_requests: str = ""

    # page 7 — output
    output_preferences: str = ""
    output_language: str = "English"

    # derived
    pace: str = "relaxed"
    purpose: str = ""
    special_requirements: str = ""
    nationality: str = ""

    @field_validator("num_travelers")
    @classmethod
    def travelers_positive(cls, v):
        if v < 1:
            raise ValueError("must be at least 1")
        return v

    @field_validator("total_budget")
    @classmethod
    def budget_not_negative(cls, v):
        if v < 0:
            raise ValueError("budget cannot be negative")
        return v

    @model_validator(mode="after")
    def end_after_start(self):
        if self.end_date < self.start_date:
            raise ValueError("end date cannot be before start date")
        return self


class HotelPreferences(BaseModel):
    suggest_rooms: bool = True
    rooms_spec: str = ""
    non_couples_sharing: str = "share"
    bed_when_sharing: str = "twin"
    property_type: str = "any"
    preferred_area: str = ""
    room_view: str = "any"
    amenities: str = ""
    local_transport_ok: bool = True
    transport_fare_max: Optional[float] = None
    hotel_per_night_min: Optional[float] = None
    hotel_per_night_max: Optional[float] = None
    min_rating: float = 0


# ===================== SUGGESTIONS =====================

class PlaceSuggestion(BaseModel):
    name: str
    region: str
    why_it_fits: str
    best_for: str
    possible_downside: str
    crowd_level: str
    weather_suitability: str
    transport_convenience: str


class PlaceSuggestions(BaseModel):
    suggestions: List[PlaceSuggestion]
    top_recommendation: str
    reasoning: str


# ===================== ROUTE =====================

class RouteLeg(BaseModel):
    from_place: str
    to_place: str
    mode: str
    per_vehicle: bool = False
    cost_min: Optional[float] = None
    cost_max: Optional[float] = None
    duration: str = ""
    note: str = ""
    booking_links: list = []


class Route(BaseModel):
    legs: List[RouteLeg]
    is_direct: bool
    summary: str


# ===================== ROOMS & HOTELS =====================

class RoomConfig(BaseModel):
    rooms: int
    description: str
    bed_types: str


class HotelOption(BaseModel):
    name: str
    area: str = ""
    per_night_min: Optional[float] = None
    per_night_max: Optional[float] = None
    view: str = ""
    amenities: str = ""
    source: str = "search"
    booking_link: str = ""
    note: str = ""


class HotelOptions(BaseModel):
    hotels: List[HotelOption]


# ===================== ITINERARY & BUDGET =====================

class Itinerary(BaseModel):
    days: List['DayPlan']


class DayPlan(BaseModel):
    day_label: str
    date: str
    activities: List[str]


class BudgetItem(BaseModel):
    item: str
    amount: float
    note: str = ""


class BudgetBreakdown(BaseModel):
    items: List[BudgetItem]
    total: float
    currency_code: str
    currency_symbol: str
    fits_budget: bool
    buffer: float
    note: str = ""


# ===================== EXTRAS =====================

class TravelExtras(BaseModel):
    packing_list: List[str]
    safety_notes: List[str]


class RefineIntent(BaseModel):
    action: Literal["cheaper", "swap_hotel", "change_itinerary", "change_place", "unclear"]
    detail: str = ""


# ===================== FINAL PLAN =====================

class TripPlan(BaseModel):
    destination: str
    summary: str
    budget_headline: str
    route: Route
    room_config: Optional[RoomConfig] = None
    hotels: List[HotelOption] = Field(default_factory=list)
    itinerary: List[DayPlan] = Field(default_factory=list)
    budget: BudgetBreakdown
    packing_list: List[str] = Field(default_factory=list)
    safety_notes: List[str] = Field(default_factory=list)
    booking_order: List[str] = Field(default_factory=list)
    map_link: str = ""