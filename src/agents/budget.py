import math
from datetime import date
from src.state import AgentState
from src.schemas import BudgetItem, BudgetBreakdown


def _get_price_floor(currency):
    if currency in ("USD", "GBP", "EUR", "CAD", "AUD", "SGD", "CHF"):
        return 20
    elif currency in ("JPY",):
        return 2000
    else:
        return 300


def _compute_nights_and_days(req):
    start = date.fromisoformat(req["start_date"])
    end = date.fromisoformat(req["end_date"])
    calendar_nights = (end - start).days

    dep = (req.get("departure_timing") or "any").lower()

    dep_is_night = any(w in dep for w in ("night", "8 pm", "evening", "pm –", "pm -",
                                           "late night", "12 am", "6 pm"))

    hotel_nights = calendar_nights
    if dep_is_night:
        hotel_nights -= 1

    hotel_nights = max(0, hotel_nights)

    activity_days = calendar_nights + 1
    if dep_is_night:
        activity_days -= 1
    activity_days = max(1, activity_days)

    return hotel_nights, activity_days


def budget_node(state: AgentState) -> dict:
    if state.get("error"):
        return {}

    req = state["request"]
    n = req["num_travelers"]
    hotel_nights, activity_days = _compute_nights_and_days(req)
    symbol = state.get("currency_symbol", "")
    currency = state.get("home_currency", "INR")
    price_floor = _get_price_floor(currency)

    items = []

    # ── transport ──
    route = state.get("route", {})
    transport_total = 0.0
    for leg in route.get("legs", []):
        cost = leg.get("cost_min") or 0
        if leg.get("per_vehicle"):
            vehicles = math.ceil(n / 4)
            transport_total += cost * vehicles * 2
        else:
            transport_total += cost * n * 2
    transport_total = round(transport_total, 2)
    items.append(BudgetItem(
        item="Transport (round trip, all travelers)",
        amount=transport_total,
        note="grounded, cheapest option; varies by bus type and booking date"))

    # ── hotel ──
    rooms = state.get("room_config", {}).get("rooms", 1)
    prefs = state.get("hotel_prefs", {})
    band_min = prefs.get("hotel_per_night_min")

    # collect plausible grounded prices
    grounded = [h["per_night_min"] for h in state.get("hotels", [])
                if h.get("per_night_min") and h["per_night_min"] >= price_floor]

    # decide nightly rate
    if hotel_nights == 0:
        nightly = 0
        hnote = "no hotel needed (overnight travel both ways)"
    elif band_min and band_min > 0:
        nightly = band_min
        hnote = "from your stated nightly band"
    elif grounded:
        user_budget = req.get("total_budget", 0)
        if user_budget > 0 and len(grounded) > 1:
            sorted_rates = sorted(grounded)
            nightly = sorted_rates[len(sorted_rates) // 2]
            hnote = "grounded: mid-range option within your budget"
        else:
            nightly = min(grounded)
            hnote = "grounded: cheapest plausible rate found"
    elif req.get("total_budget", 0) > 0 and hotel_nights > 0:
        remaining = req["total_budget"] - transport_total
        nightly = max(800, round(remaining * 0.25 / max(hotel_nights * rooms, 1)))
        hnote = "estimated ~25% of remaining budget for comfortable stay"
    elif hotel_nights > 0:
        nightly = 1500
        hnote = "default estimate — verify on booking link"
    else:
        nightly = 0
        hnote = "no hotel needed"

    hotel_total = round(nightly * hotel_nights * rooms, 2)
    items.append(BudgetItem(
        item=f"Hotel ({rooms} room x {hotel_nights} night{'s' if hotel_nights != 1 else ''})",
        amount=hotel_total,
        note=hnote))

    # ── food ──
    food_per_person_per_day = 400 if currency == "INR" else 20
    food_total = round(food_per_person_per_day * n * activity_days, 2)
    items.append(BudgetItem(
        item="Food",
        amount=food_total,
        note=f"rough estimate ~{food_per_person_per_day}/person/day x {activity_days} days"))

    # ── local transport ──
    local_per_day = 300 if currency == "INR" else 15
    local_total = round(local_per_day * activity_days, 2)
    items.append(BudgetItem(
        item="Local transport / misc",
        amount=local_total,
        note="rough estimate"))

    # ── buffer ──
    subtotal = sum(i.amount for i in items)
    buffer_amt = round(subtotal * 0.10, 2)
    items.append(BudgetItem(item="Buffer (10%)", amount=buffer_amt, note="for surprises"))
    total = round(subtotal + buffer_amt, 2)

    # ── budget fit ──
    user_budget = req.get("total_budget") or 0
    if req.get("budget_scope", "").lower().startswith("per"):
        user_budget *= n

    if user_budget > 0:
        leftover = round(user_budget - total, 2)
        fits = total <= user_budget
        if fits:
            headline = (f"Total est. {symbol}{total:,.0f} of {symbol}{user_budget:,.0f} — "
                        f"within budget, {symbol}{leftover:,.0f} to spare")
        else:
            headline = (f"Total est. {symbol}{total:,.0f} of {symbol}{user_budget:,.0f} — "
                        f"over budget by {symbol}{abs(leftover):,.0f}")
    else:
        leftover = 0.0
        fits = True
        headline = f"Estimated trip cost: {symbol}{total:,.0f}"

    breakdown = BudgetBreakdown(
        items=items, total=total,
        currency_code=currency, currency_symbol=symbol,
        fits_budget=fits, buffer=leftover,
        note="Transport grounded; hotel estimated; food/local are rough estimates.")
    return {"budget": breakdown.model_dump(), "budget_headline": headline}