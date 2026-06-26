from src.state import AgentState
from src.config import invoke_structured
from src.tools.search import search_web
from src.schemas import Route


def _route_query(origin, place, mode, timing=""):
    base = f"how to reach {place} from {origin} by {mode} nearest bus stand drop point"
    if timing and timing != "Any time":
        base += f" departing {timing}"
    return base


def _fare_query(origin, place, mode, timing=""):
    base = f"{origin} to {place} {mode} fare price range cheapest to premium"
    if timing and timing != "Any time":
        base += f" {timing} departure"
    return base


def _messages(req, place, context):
    dep_time = req.get('departure_timing', 'Any time')
    ret_time = req.get('return_timing', 'Any time')

    system = (
        "You are a travel routing expert. Using ONLY the SEARCH RESULTS, work out the real "
        "route and per-person cost from origin to destination by the requested mode.\n\n"
        "IMPORTANT RULES:\n"
        "1. Buses/trains to small hill towns are often advertised as 'direct' but actually "
        "DROP passengers at a nearby hub town. Check for drop points. If so, model as TWO "
        "legs and set is_direct to false.\n"
        "2. For each leg, find the FULL PRICE RANGE:\n"
        "   - cost_min = the CHEAPEST fare you can find in the results (non-AC seater, basic bus)\n"
        "   - cost_max = the MOST EXPENSIVE fare (AC sleeper, Volvo, premium)\n"
        "   - These should be DIFFERENT numbers representing the real range of options\n"
        "   - If results show multiple prices like ₹324, ₹500, ₹899, ₹1618 then cost_min=324 and cost_max=1618\n"
        "   - Only leave them null if truly NO number appears anywhere\n"
        "3. Set per_vehicle=TRUE for cab/taxi legs (one cab carries the group). "
        "Set per_vehicle=FALSE for bus/train (each person buys a ticket).\n"
        "4. For cab legs, the cost is for THE WHOLE CAB, not per person.\n"
        "5. Never invent a price or a connection."
    )
    human = (
        f"FROM: {req.get('origin_city')}, {req.get('origin_country')}\n"
        f"TO: {place}\n"
        f"PREFERRED MODE: {req.get('transport_mode')}\n"
        f"USER WANTS TO BOARD AT: {dep_time}\n"
        f"USER WANTS RETURN AT: {ret_time}\n"
        f"Find options matching these time windows. If no exact match, mention the closest.\n\n"
        f"SEARCH RESULTS:\n{context}"
    )
    return [("system", system), ("human", human)]


def _sanity(route_dict: dict) -> dict:
    for leg in route_dict.get("legs", []):
        lo, hi = leg.get("cost_min"), leg.get("cost_max")
        if lo is not None and hi is not None and lo > hi:
            leg["cost_min"], leg["cost_max"] = hi, lo
    return route_dict


def route_node(state: AgentState) -> dict:
    if state.get("error"):
        return {}
    req = state["request"]
    place = state["selected_place"]
    origin = req["origin_city"]
    mode = req["transport_mode"]
    dep_timing = req.get("departure_timing", "Any time")

    route_ctx = search_web(_route_query(origin, place, mode, dep_timing), max_results=6)
    fare_ctx = search_web(_fare_query(origin, place, mode, dep_timing), max_results=6)

    # search for the last-mile leg cost
    lastmile_ctx = search_web(f"cab taxi fare cost from nearest city to {place}", max_results=4)

    # combine all context
    context = ""
    if not route_ctx.startswith("SEARCH_ERROR"):
        context += f"ROUTE INFO:\n{route_ctx}"
    if not fare_ctx.startswith("SEARCH_ERROR"):
        context += f"\n\nFARE INFO:\n{fare_ctx}"
    if not lastmile_ctx.startswith("SEARCH_ERROR"):
        context += f"\n\nLAST MILE TRANSPORT:\n{lastmile_ctx}"

    if not context:
        return {"error": f"Could not fetch route data for {place}."}

    try:
        route = invoke_structured(Route, _messages(req, place, context))
    except Exception as e:
        return {"error": f"Could not work out the route: {e}"}

    return {"route": _sanity(route.model_dump())}