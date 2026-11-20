"""Cache behaviour under the thread pool."""

import threading

from services import cache_service


def test_cache_returns_private_copies_and_survives_concurrent_access(monkeypatch):
    cache_service.clear_cache()
    cache_service.set_in_cache("AAPL", {"timeline": [], "n": 1})

    copy_a = cache_service.get_from_cache("AAPL")
    copy_a["timeline"].append("edited")
    assert cache_service.get_from_cache("AAPL")["timeline"] == []  # the stored report is untouched

    errors = []

    def worker(i):
        try:
            for j in range(200):
                key = f"S{(i + j) % 5}"
                cache_service.set_in_cache(key, {"i": i, "j": j})
                cache_service.get_from_cache(key)
                cache_service.get_cache_info(key)
        except Exception as err:  # any race would surface here
            errors.append(err)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []

    monkeypatch.setattr(cache_service, "CACHE_TTL", -1)  # everything is now expired
    assert cache_service.get_from_cache("AAPL") is None
    cache_service.clear_cache()
