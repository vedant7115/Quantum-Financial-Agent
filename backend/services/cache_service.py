# cache_service.py
# A simple in-memory cache to avoid analyzing the same stock twice in quick succession.
# This is a basic Python dict-based cache — no Redis or database needed.
# Cache expires after 5 minutes (300 seconds).

import time

# The cache is just a plain Python dictionary stored in memory.
# Structure: { "AAPL": { "data": {...}, "timestamp": 1234567890 } }
_cache = {}

# How long to keep a result before considering it stale (in seconds)
import os

# Daily closes and annual statements do not change minute to minute, so a report
# is reused for 15 minutes by default. This is also the main lever on LLM cost.
CACHE_TTL = int(os.getenv("CACHE_TTL_SECONDS", "900"))


def get_from_cache(key: str):
    """
    Try to get a cached result.
    Returns None if:
      - The key doesn't exist in cache
      - The cached result is older than CACHE_TTL
    """
    if key not in _cache:
        return None  # Nothing cached for this key

    entry = _cache[key]
    age = time.time() - entry["timestamp"]  # How old is this cache entry?

    if age > CACHE_TTL:
        # Cache is stale, remove it and return None
        del _cache[key]
        return None

    return entry["data"]  # Return fresh cached data


def set_in_cache(key: str, data: dict):
    """
    Store a result in the cache with the current timestamp.
    Next time the same key is requested, we return this instead of recomputing.
    """
    _cache[key] = {
        "data": data,
        "timestamp": time.time(),  # Record when we cached this
    }


def clear_cache():
    """Remove all cached entries. Useful for testing."""
    _cache.clear()


def get_cache_info(key: str) -> dict:
    """
    Returns a dict indicating if key is cached, and the remaining TTL.
    """
    if key not in _cache:
        return {"hit": False, "ttl_remaining": 0}

    entry = _cache[key]
    age = time.time() - entry["timestamp"]
    ttl_remaining = int(max(0, CACHE_TTL - age))

    if age > CACHE_TTL:
        # It's expired
        return {"hit": False, "ttl_remaining": 0}

    return {"hit": True, "ttl_remaining": ttl_remaining}

