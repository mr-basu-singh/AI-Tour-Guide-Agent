from src.state import AgentState
from src.safety import validate_trip_request
from src.tools.currency import currency_for_country, symbol_for


def intake_node(state: AgentState) -> dict:
    req, error = validate_trip_request(state["raw_input"])
    if error:
        return {"error": error}

    code = currency_for_country(req.origin_country)
    return {
        "request": req.model_dump(mode="json"),
        "home_currency": code,
        "currency_symbol": symbol_for(code),
    }