import os
import json
import time
import hashlib
from langchain_tavily import TavilySearch

CACHE_FILE = ".search_cache.json"
CACHE_TTL = 3600  # 1 hour


def _load_cache() -> dict:
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_cache(cache: dict):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f)
    except Exception:
        pass


def search_web(query: str, max_results: int = 6) -> str:
    """Search the web with a disk-persisted TTL cache.
    Same query returns identical results across restarts within the TTL window."""
    key = hashlib.md5(f"{query}:{max_results}".encode()).hexdigest()
    now = time.time()
    cache = _load_cache()

    if key in cache:
        text, ts = cache[key]
        if now - ts < CACHE_TTL:
            return text

    try:
        result = TavilySearch(max_results=max_results).invoke(query)
        items = result.get("results", [])
        if not items:
            return "SEARCH_ERROR: no results found"
        text = "\n\n".join(
            f"{i.get('title', '')}: {i.get('content', '')}" for i in items
        )
        cache[key] = [text, now]
        _save_cache(cache)
        return text
    except Exception as e:
        return f"SEARCH_ERROR: {e}"