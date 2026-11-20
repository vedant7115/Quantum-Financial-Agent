"""End-to-end through the FastAPI app with every data source replaced by a slow fake.
Proves: the agents fan out concurrently, separate requests do not serialize,
identical requests compute once, and traces, llm blocks and admin endpoints work."""

import asyncio
import json
import time

import httpx
import pytest

from conftest import make_prices

DELAY = 0.3   # seconds each fake data source takes


@pytest.fixture
def app(monkeypatch, groq):
    import main
    from core.context import traces
    from services import news_service, research_engine, stock_service, usage_service
    from services.cache_service import cache

    cache.clear()
    traces.clear()
    usage_service.reset()
    calls = {"quote": 0}

    def fake_quote(symbol):
        calls["quote"] += 1
        time.sleep(0.1)
        return {"name": f"{symbol} Corp", "price": 300.0, "change_pct": 0.5, "currency": "USD",
                "market_cap_raw": 1e11, "sector": "Technology", "market_state": "REGULAR"}

    def slow(value):
        def fn(*args, **kwargs):
            time.sleep(DELAY)
            return value() if callable(value) else value
        return fn

    async def fake_news(symbol, name=""):
        await asyncio.sleep(DELAY)
        return {"symbol": symbol, "total_articles": 0, "articles": [], "source": "No recent news available"}

    monkeypatch.setattr(stock_service, "get_stock_data", fake_quote)
    monkeypatch.setattr(stock_service, "is_ticker_valid", lambda s: True)
    monkeypatch.setattr(research_engine, "_history",
                        lambda s, p: (time.sleep(DELAY), make_prices(0.0012) if not s.startswith("^")
                                      else make_prices(0.0003, seed=3))[1])
    monkeypatch.setattr(research_engine, "_statements", slow({}))
    monkeypatch.setattr(research_engine, "_calendar", slow({}))
    monkeypatch.setattr(news_service, "fetch_news", fake_news)
    monkeypatch.setenv("ADMIN_TOKEN", "secret")
    groq.answers = ["not json"] * 50   # every brief falls back to rules; keeps the test independent of wording
    main.app.state.calls = calls
    return main.app


async def _post(client, symbol, ip):
    started = time.perf_counter()
    response = await client.post("/api/analyze", json={"symbol": symbol}, headers={"x-forwarded-for": ip})
    return response, time.perf_counter() - started


def _client(app):
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


def test_agents_fan_out_concurrently_and_trace_is_returned(app):
    async def run():
        async with _client(app) as client:
            return await _post(client, "AAPL", "10.0.0.1")

    response, elapsed = asyncio.run(run())
    assert response.status_code == 200, response.text
    body = response.json()

    spans = {s["name"]: s for s in body["trace"]["spans"]}
    agents = [spans[f"agent.{n}"] for n in ("technical", "fundamental", "sentiment")]
    # All three agents start before any of them finishes: they ran at the same time.
    assert max(a["start_ms"] for a in agents) < min(a["end_ms"] for a in agents)
    # Sequential agents would need at least 3 x DELAY; concurrent ones about 1 x DELAY.
    report_ms = spans["report"]["duration_ms"]
    assert report_ms < (100 + 2 * DELAY * 1000), report_ms

    assert body["trace"]["request_id"] == body["meta"]["request_id"]
    assert body["llm"]["prompt_version"] == body["trace"]["prompt_version"]
    assert body["insight"]["agent_scores"]["technical"]["status"] == "ok"
    assert {"consensus", "brief", "quote", "validate"} <= set(spans)


def test_two_requests_do_not_serialize_and_identical_ones_compute_once(app):
    async def single():
        async with _client(app) as client:
            return await _post(client, "MSFT", "10.0.0.2")

    _, one = asyncio.run(single())

    async def pair():
        async with _client(app) as client:
            return await asyncio.gather(_post(client, "NVDA", "10.0.0.3"), _post(client, "TSLA", "10.0.0.4"))

    started = time.perf_counter()
    (r1, _), (r2, _) = asyncio.run(pair())
    both = time.perf_counter() - started
    assert r1.status_code == r2.status_code == 200
    # Serialized requests would take about 2x one request.
    assert both < 1.5 * one, (both, one)

    before = app.state.calls["quote"]

    async def same():
        async with _client(app) as client:
            return await asyncio.gather(*(_post(client, "AMZN", f"10.0.1.{i}") for i in range(3)))

    results = asyncio.run(same())
    assert all(r.status_code == 200 for r, _ in results)
    assert app.state.calls["quote"] - before == 1        # computed once
    sources = sorted(r.json()["meta"]["cache"] for r, _ in results)
    assert sources == ["coalesced", "coalesced", "miss"]


def test_admin_endpoints_require_token_and_expose_traces_and_usage(app):
    async def run():
        async with _client(app) as client:
            r, _ = await _post(client, "META", "10.0.0.9")
            denied = await client.get("/api/admin/traces")
            traces_ = await client.get("/api/admin/traces", headers={"x-admin-token": "secret"})
            usage = await client.get("/api/admin/usage", headers={"x-admin-token": "secret"})
            return r, denied, traces_, usage

    r, denied, traces_, usage = asyncio.run(run())
    assert denied.status_code == 403
    rid = r.json()["meta"]["request_id"]
    assert any(t["request_id"] == rid for t in traces_.json()["traces"])
    body = usage.json()
    today = next(iter(body["days"].values()))
    assert today["llm_totals"]["calls"] >= 2          # one attempt plus the retry
    assert today["llm_totals"]["total_tokens"] >= 300
    assert body["cache"]["report"]["misses"] >= 1
    assert "openai/gpt-oss-120b" in body["model_chain"] and len(body["model_chain"]) == 3
