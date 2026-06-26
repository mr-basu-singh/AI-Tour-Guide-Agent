from datetime import date
from src.config import invoke_structured
from src.tools.search import search_web
from pydantic import BaseModel, Field
from typing import Optional


class TravelCheck(BaseModel):
    travel_hours_one_way: Optional[float] = Field(
        description="Approximate hours for one-way travel. Null if unknown.")
    is_reachable_by_mode: bool = Field(
        description="True if the destination is reachable by the requested transport mode.")
    alternative_mode: str = Field(
        default="", description="If not reachable by requested mode, suggest an alternative.")
    min_fare_per_person: Optional[float] = Field(
        default=None, description="Cheapest one-way fare per person if found.")


def _max_travel_hours(start: str, end: str) -> float:
    """Max acceptable one-way travel time = roughly 1/3 of total trip hours.
    A 3-day trip (72 hrs) allows ~12 hrs one-way max. A 7-day trip allows ~24 hrs."""
    s = date.fromisoformat(start)
    e = date.fromisoformat(end)
    total_hours = (e - s).days * 24
    return min(max(total_hours / 3, 6), 24)  # at least 6 hrs, at most 24


def check_feasibility(origin: str, place: str, mode: str, budget: float,
                      n_travelers: int, start: str, end: str) -> dict:
    """Check if a place is realistically reachable. Returns a dict with the verdict."""
    max_hours = _max_travel_hours(start, end)

    # reject if the suggestion is the origin itself
    if place.strip().lower() in origin.strip().lower() or origin.strip().lower() in place.strip().lower():
        return {"feasible": False, "place": place,
                "reason": f"same as origin city ({origin}) — traveler wants to go somewhere else"}

    context = search_web(f"travel time from {origin} to {place} by {mode} hours distance",
                         max_results=4)
    if context.startswith("SEARCH_ERROR"):
        # can't verify — give benefit of the doubt but flag it
        return {"feasible": True, "reason": "could not verify travel time", "place": place}

    system = (
        f"Given the search results, estimate the one-way travel time from {origin} to "
        f"{place} by {mode}. Is the destination reachable by {mode}? If not, what's the "
        f"best alternative mode? What's the cheapest one-way fare per person if mentioned?"
    )
    try:
        check = invoke_structured(TravelCheck,
                                  [("system", system), ("human", context)], large=False)
    except Exception:
        return {"feasible": True, "reason": "could not verify", "place": place}

    result = check.model_dump()
    hours = result.get("travel_hours_one_way")
    reachable = result.get("is_reachable_by_mode", True)

    # check 1: is the mode even possible?
    if not reachable:
        alt = result.get("alternative_mode", "")
        return {"feasible": False, "place": place,
                "reason": f"not reachable by {mode}",
                "alternative": alt}

    # check 2: is the travel time realistic for the trip duration?
    if hours and hours > max_hours:
        return {"feasible": False, "place": place,
                "reason": f"one-way travel is ~{hours:.0f} hrs but max acceptable is ~{max_hours:.0f} hrs for this trip length",
                "alternative": result.get("alternative_mode", "")}

    # check 3: does the minimum fare fit the budget?
    fare = result.get("min_fare_per_person")
    if fare and budget > 0:
        round_trip_total = fare * n_travelers * 2
        if round_trip_total > budget * 0.7: # transport shouldn't eat > 70% of budget
            return {"feasible": False, "place": place,
                    "reason": f"transport alone (~{round_trip_total:.0f}) would eat most of the budget",
                    "alternative": result.get("alternative_mode", "")}

    return {"feasible": True, "place": place, "hours": hours, "fare": fare}