import os
import json
import warnings
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_community.cache import SQLiteCache
from langchain_core.globals import set_llm_cache
from json_repair import repair_json

load_dotenv()

# silence a harmless pending-deprecation notice from the LLM cache
warnings.filterwarnings("ignore", message=".*allowed_objects.*")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

LARGE_MODEL = "llama-3.3-70b-versatile"
SMALL_MODEL = "llama-3.1-8b-instant"
TEMPERATURE = 0


class ConfigError(Exception):
    """Raised when required keys are missing."""


def validate_config():
    missing = [k for k, v in {
        "GROQ_API_KEY": GROQ_API_KEY,
        "TAVILY_API_KEY": TAVILY_API_KEY,
    }.items() if not v]
    if missing:
        raise ConfigError(f"Missing keys in .env: {', '.join(missing)}")


set_llm_cache(SQLiteCache(database_path=".langchain.db"))


def get_large_llm():
    validate_config()
    return ChatGroq(model=LARGE_MODEL, temperature=TEMPERATURE)


def get_small_llm():
    validate_config()
    return ChatGroq(model=SMALL_MODEL, temperature=TEMPERATURE)


def get_structured_llm(schema, large=True, temperature=TEMPERATURE):
    validate_config()
    model = LARGE_MODEL if large else SMALL_MODEL
    return ChatGroq(model=model, temperature=temperature).with_structured_output(schema)


def _json_fallback(schema, messages, large, temperature):
    """Robust fallback: ask for plain JSON, repair malformed brackets, then validate."""
    model = LARGE_MODEL if large else SMALL_MODEL
    schema_str = json.dumps(schema.model_json_schema())
    instruction = ("Return ONLY a JSON object matching this schema — no markdown, no code "
                   f"fences, no extra text.\nSCHEMA:\n{schema_str}")
    msgs = list(messages) + [("human", instruction)]
    raw = ChatGroq(model=model, temperature=temperature).invoke(msgs).content
    raw = raw.replace("```json", "").replace("```", "").strip()
    data = repair_json(raw, return_objects=True)
    return schema(**data)


def invoke_structured(schema, messages, large=True, retries=2):
    """Structured output with retry; if Groq's function-calling keeps emitting
    malformed JSON, fall back to plain JSON + automatic repair."""
    last_err = None
    for attempt in range(retries + 1):
        temp = 0.0 if attempt == 0 else 0.4
        try:
            return get_structured_llm(schema, large=large, temperature=temp).invoke(messages)
        except Exception as e:
            last_err = e
    try:
        return _json_fallback(schema, messages, large, 0.2)   # repair fallback
    except Exception as e:
        last_err = e
    raise last_err