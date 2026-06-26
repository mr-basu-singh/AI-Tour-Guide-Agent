from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from src.state import AgentState
from src.agents.intake import intake_node
from src.agents.research import research_node
from src.agents.select import select_place_node
from src.agents.route import route_node
from src.agents.itinerary import itinerary_node
from src.agents.hotel import hotel_node
from src.agents.budget import budget_node
from src.agents.finalize import finalize_node


def _after_intake(state): return "error" if state.get("error") else "research"
def _after_research(state): return "error" if state.get("error") else "select"
def _after_select(state): return "error" if state.get("error") else "route"
def _after_route(state): return "error" if state.get("error") else "itinerary"
def _after_itinerary(state): return "error" if state.get("error") else "hotel"
def _after_hotel(state): return "error" if state.get("error") else "budget"
def _after_budget(state): return "error" if state.get("error") else "finalize"


def build_graph():
    g = StateGraph(AgentState)
    g.add_node("intake", intake_node)
    g.add_node("research", research_node)
    g.add_node("select", select_place_node)
    g.add_node("route", route_node)
    g.add_node("itinerary", itinerary_node)
    g.add_node("hotel", hotel_node)
    g.add_node("budget", budget_node)
    g.add_node("finalize", finalize_node)

    g.add_edge(START, "intake")
    g.add_conditional_edges("intake", _after_intake, {"research": "research", "error": END})
    g.add_conditional_edges("research", _after_research, {"select": "select", "error": END})
    g.add_conditional_edges("select", _after_select, {"route": "route", "error": END})
    g.add_conditional_edges("route", _after_route, {"itinerary": "itinerary", "error": END})
    g.add_conditional_edges("itinerary", _after_itinerary, {"hotel": "hotel", "error": END})
    g.add_conditional_edges("hotel", _after_hotel, {"budget": "budget", "error": END})
    g.add_conditional_edges("budget", _after_budget, {"finalize": "finalize", "error": END})
    g.add_edge("finalize", END)

    return g.compile(checkpointer=MemorySaver())