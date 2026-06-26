import copy
from src.agents.intake import intake_node
from src.agents.research import research_node
from src.agents.route import route_node
from src.agents.itinerary import itinerary_node
from src.agents.hotel import hotel_node
from src.agents.budget import budget_node
from src.agents.finalize import finalize_node


def run_phase1(raw_input: dict) -> dict:
    state = {"raw_input": copy.deepcopy(raw_input)}
    state.update(intake_node(state))
    if state.get("error"):
        return state
    state.update(research_node(state))
    return state


def run_phase2(state: dict, selected_place: str, hotel_prefs: dict) -> dict:
    state = copy.deepcopy(state)
    state["selected_place"] = selected_place
    state["hotel_prefs"] = copy.deepcopy(hotel_prefs)

    state.update(route_node(state))
    if state.get("error"):
        return state
    state.update(itinerary_node(state))
    if state.get("error"):
        return state
    state.update(hotel_node(state))
    state.update(budget_node(state))
    state.update(finalize_node(state))
    return state