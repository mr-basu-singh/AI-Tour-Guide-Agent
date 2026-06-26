from langgraph.types import interrupt
from src.state import AgentState


def select_place_node(state: AgentState) -> dict:
    if state.get("error"):
        return {}
    suggestions = state["suggestions"]
    options = [s["name"] for s in suggestions.get("suggestions", [])]

    # user already named a place -> no need to pause
    if not options:
        return {"selected_place": suggestions["top_recommendation"]}

    choice = interrupt({"message": "Pick one place to plan", "options": options})

    if choice not in options:   # guardrail
        return {"error": f"'{choice}' is not one of the suggested places: {options}"}
    return {"selected_place": choice}