# cache_service.py
# In-memory report cache, keyed by resolved symbol (for example "RELIANCE.NS").
#
# The analyze endpoint runs in FastAPI's thread pool, so several requests can
# touch the cache at once. Every read and write holds _lock, which makes each
# operation (including the expire-and-delete in get_from_cache) atomic.
#
# The cache lives in this process only: it is empty after a restart and is not
# shared between server instances.

import copy
import os
import threading
import time

# Structure: { "AAPL": { "data": {...}, "timestamp": 1234567890.0 } }
_cache = {}
_lock = threading.Lock()

# Daily closes and annual statements do not change minute to minute, so a report
# is reused for 15 minutes by default. This is also the main lever on LLM cost.
CACHE_TTL = int(os.getenv("CACHE_TTL_SECONDS", "900"))


def get_from_cache(key: str):
    """A private copy of the cached report for key, or None if it is missing or
    older than CACHE_TTL. Callers may modify the copy without affecting other requests."""
    with _lock:
        entry = _cache.get(key)
        if entry is None:
            return None
        if time.time() - entry["timestamp"] > CACHE_TTL:
            del _cache[key]
            return None
        return copy.deepcopy(entry["data"])


def set_in_cache(key: str, data: dict):
    """Store a report with the current time."""
    with _lock:
        _cache[key] = {"data": data, "timestamp": time.time()}


def clear_cache():
    """Remove all cached entries."""
    with _lock:
        _cache.clear()


def get_cache_info(key: str) -> dict:
    """Whether key is cached and how many seconds it has left."""
    with _lock:
        entry = _cache.get(key)
        if entry is None:
            return {"hit": False, "ttl_remaining": 0}
        age = time.time() - entry["timestamp"]
    if age > CACHE_TTL:
        return {"hit": False, "ttl_remaining": 0}
    return {"hit": True, "ttl_remaining": int(max(0, CACHE_TTL - age))}
