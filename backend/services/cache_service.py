# cache_service.py
# Tiered in-memory TTL cache with request coalescing.
#
# Tiers and default lifetimes (seconds, overridable by env):
#   report        CACHE_TTL_SECONDS        300    the finished report for a symbol
#   price         CACHE_TTL_PRICES         300    quote, daily price history, ticker check
#   news          CACHE_TTL_NEWS           1800   filtered headlines
#   fundamentals  CACHE_TTL_FUNDAMENTALS   86400  financial statements and calendar
#
# Thread safety: one threading.Lock guards the entries, the in-flight table and
# the counters, so reads, writes and expiry are atomic from both the event loop
# and asyncio.to_thread workers.
#
# Coalescing: get_or_compute() lets the first caller for a (tier, key) compute
# the value while later callers await the same future, so two identical
# requests compute once. Futures belong to the event loop that created them;
# the server runs one loop per process.
#
# Report and news values are deep-copied on the way out so a caller can modify
# its copy. The cache lives in this process only: it is empty after a restart
# and not shared between instances.

import asyncio
import copy
import os
import threading
import time

from services import usage_service

TIERS = {
    "report": ("CACHE_TTL_SECONDS", 300),
    "price": ("CACHE_TTL_PRICES", 300),
    "news": ("CACHE_TTL_NEWS", 1800),
    "fundamentals": ("CACHE_TTL_FUNDAMENTALS", 86400),
}
COPY_ON_READ = {"report", "news"}


def _ttls() -> dict:
    return {tier: int(os.getenv(env, str(default))) for tier, (env, default) in TIERS.items()}


class TieredCache:
    def __init__(self, ttls: dict = None):
        self.ttls = ttls or _ttls()
        self._lock = threading.Lock()
        self._data = {}       # (tier, key) -> (value, stored_at)
        self._inflight = {}   # (tier, key) -> asyncio.Future
        self._stats = {tier: {"hits": 0, "misses": 0, "coalesced": 0} for tier in self.ttls}

    def _count(self, tier: str, event: str):
        self._stats.setdefault(tier, {"hits": 0, "misses": 0, "coalesced": 0})[event] += 1
        usage_service.record_cache(tier, event)

    def _out(self, tier, value):
        return copy.deepcopy(value) if tier in COPY_ON_READ else value

    def _fresh(self, tier, key, now):
        entry = self._data.get((tier, key))
        if entry is None:
            return None
        if now - entry[1] > self.ttls.get(tier, 0):
            del self._data[(tier, key)]
            return None
        return entry

    def get(self, tier: str, key: str, count: bool = True):
        with self._lock:
            entry = self._fresh(tier, key, time.time())
            if count:
                self._count(tier, "hits" if entry else "misses")
            return None if entry is None else self._out(tier, entry[0])

    def set(self, tier: str, key: str, value):
        with self._lock:
            self._data[(tier, key)] = (value, time.time())

    def ttl_remaining(self, tier: str, key: str) -> int:
        with self._lock:
            entry = self._fresh(tier, key, time.time())
            return 0 if entry is None else int(max(0, self.ttls.get(tier, 0) - (time.time() - entry[1])))

    async def get_or_compute(self, tier: str, key: str, factory):
        """Returns (value, source) where source is "hit", "miss" or "coalesced".
        factory is an async callable run only by the first caller."""
        with self._lock:
            entry = self._fresh(tier, key, time.time())
            if entry is not None:
                self._count(tier, "hits")
                return self._out(tier, entry[0]), "hit"
            future = self._inflight.get((tier, key))
            owner = future is None
            if owner:
                future = asyncio.get_running_loop().create_future()
                self._inflight[(tier, key)] = future
                self._count(tier, "misses")
            else:
                self._count(tier, "coalesced")

        if not owner:
            value = await asyncio.shield(future)
            return self._out(tier, value), "coalesced"

        try:
            value = await factory()
        except BaseException as err:
            with self._lock:
                self._inflight.pop((tier, key), None)
            if not future.done():
                future.set_exception(err if isinstance(err, Exception) else RuntimeError(str(err)))
                future.exception()  # mark as retrieved when nobody else was waiting
            raise
        with self._lock:
            self._data[(tier, key)] = (value, time.time())
            self._inflight.pop((tier, key), None)
        if not future.done():
            future.set_result(value)
        return self._out(tier, value), "miss"

    def clear(self, tier: str = None):
        with self._lock:
            if tier is None:
                self._data.clear()
            else:
                for k in [k for k in self._data if k[0] == tier]:
                    del self._data[k]

    def stats(self) -> dict:
        with self._lock:
            entries = {}
            for tier, _ in self._data:
                entries[tier] = entries.get(tier, 0) + 1
            return {tier: {**counts, "entries": entries.get(tier, 0), "ttl_seconds": self.ttls.get(tier)}
                    for tier, counts in self._stats.items()}


cache = TieredCache()

# The report TTL, kept under its old name for callers that report it.
CACHE_TTL = cache.ttls["report"]


# Report-tier helpers kept for older callers and tests.
def get_from_cache(key: str):
    return cache.get("report", key)


def set_in_cache(key: str, data: dict):
    cache.set("report", key, data)


def clear_cache():
    cache.clear()


def get_cache_info(key: str) -> dict:
    remaining = cache.ttl_remaining("report", key)
    return {"hit": remaining > 0, "ttl_remaining": remaining}
