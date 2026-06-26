from datetime import date
from pydantic import ValidationError
from src.schemas import TripRequest

# Phrases that suggest someone is trying to hijack the agent through free text
INJECTION_PATTERNS = [
    "ignore previous", "ignore all previous", "disregard above",
    "system prompt", "you are now", "forget your instructions",
    "new instructions", "override your",
]


def _friendly_errors(e: ValidationError) -> str:
    parts = []
    for err in e.errors():
        field = " -> ".join(str(x) for x in err["loc"]) or "input"
        parts.append(f"{field}: {err['msg']}")
    return "Invalid input — " + "; ".join(parts)


def scan_for_injection(text: str) -> bool:
    """True if the text looks like a prompt-injection attempt."""
    if not text:
        return False
    low = text.lower()
    return any(p in low for p in INJECTION_PATTERNS)


def validate_trip_request(raw: dict):
    """Validate raw intake into a TripRequest.
    Returns (TripRequest, None) on success, or (None, reason) on failure."""
    # 1. structural validation (types, ranges, end >= start)
    try:
        req = TripRequest(**raw)
    except ValidationError as e:
        return None, _friendly_errors(e)

    # 2. contextual checks the schema can't do
    if req.start_date < date.today():
        return None, "Invalid input — start date is in the past."

    if req.place_in_mind and \
       req.place_in_mind.strip().lower() == req.origin_city.strip().lower():
        return None, "Invalid input — your destination is the same as your starting city."

    # 3. guardrail: scan free-text fields for injection attempts
    for field in ("special_requirements", "mobility_notes", "place_in_mind", "purpose"):
        if scan_for_injection(getattr(req, field, "")):
            return None, ("Your input looks like it contains an instruction to the system. "
                          "Please describe only your travel preferences.")

    return req, None