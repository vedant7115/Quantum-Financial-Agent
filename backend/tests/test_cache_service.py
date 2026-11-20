"""Tiered cache: TTLs, private copies, thread safety and request coalescing."""

import asyncio
import threading

from services.cache_service import TieredCache


def test_tiers_have_their_own_ttls_and_reports_are_copied():
    cache = TieredCache({"report": 300, "price": 300, "news": 1800, "fundamentals": 86400})
    cache.set("report", "AAPL", {"timeline": []})
    copy_a = cache.get("report", "AAPL")
    copy_a["timeline"].append("edited")
    assert cache.get("report", "AAPL")["timeline"] == []  # stored report untouched

    cache.set("fundamentals", "statements:AAPL", {"x": 1})
    cache.ttls["report"] = -1                              # expire only the report tier
    assert cache.get("report", "AAPL") is None
    assert cache.get("fundamentals", "statements:AAPL") == {"x": 1}
    stats = cache.stats()
    assert stats["report"]["misses"] >= 1 and stats["fundamentals"]["hits"] == 1


def test_lock_survives_concurrent_threads():
    cache = TieredCache({"report": 300, "price": 300, "news": 1800, "fundamentals": 86400})
    errors = []

    def worker(i):
        try:
            for j in range(300):
                key = f"S{(i + j) % 7}"
                cache.set("price", key, {"i": i, "j": j})
                cache.get("price", key)
                cache.ttl_remaining("price", key)
                if j % 50 == 0:
                    cache.clear("price")
        except Exception as err:
            errors.append(err)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []


def test_identical_concurrent_requests_compute_once():
    cache = TieredCache({"report": 300, "price": 300, "news": 1800, "fundamentals": 86400})
    calls = []

    async def slow_build():
        calls.append(1)
        await asyncio.sleep(0.2)
        return {"composite": 70}

    async def main():
        return await asyncio.gather(*(cache.get_or_compute("report", "AAPL", slow_build) for _ in range(5)))

    results = asyncio.run(main())
    assert len(calls) == 1
    assert sorted(source for _, source in results) == ["coalesced"] * 4 + ["miss"]
    assert all(value == {"composite": 70} for value, _ in results)

    # A failure reaches every waiter and is not cached.
    async def broken():
        await asyncio.sleep(0.05)
        raise RuntimeError("provider down")

    async def main_fail():
        return await asyncio.gather(*(cache.get_or_compute("report", "MSFT", broken) for _ in range(3)),
                                    return_exceptions=True)

    outcomes = asyncio.run(main_fail())
    assert all(isinstance(o, RuntimeError) for o in outcomes)
    assert cache.get("report", "MSFT") is None
