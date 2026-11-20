"""The Groq client against a mocked transport: fallback chain, retries, rate-limit
skipping and recovery, the overall deadline, token logging and the guardrails."""

import asyncio
import json
import logging
import time

import prompts
from agents import master_agent
from conftest import ok_body
from services import llm_service, research_engine as engine, usage_service

from test_master_brief import GOOD

M120, M20, QWEN = "openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"
RATE_LIMITED = (429, {"retry-after": "10", "x-ratelimit-remaining-tokens": "0"}, {"error": {"message": "rate limited"}})


def _generate(prompt="hello", budget=30.0):
    async def run():
        loop = asyncio.get_running_loop()
        return await llm_service.generate(prompt, deadline_at=loop.time() + budget)
    return asyncio.run(run())


def test_429_retries_once_with_capped_wait_then_falls_back(groq, monkeypatch):
    monkeypatch.setenv("GROQ_MODEL", M120)
    groq.reset(by_model={M120: [RATE_LIMITED, RATE_LIMITED]}, answers=['{"ok": 1}'])
    result = _generate()
    assert groq.models == [M120, M120, M20]                 # retried once, then the next model
    assert groq.sleeps == [3.0]                             # Retry-After 10 s capped at 3 s
    assert result.model == M20 and result.fallback_used and result.fallback_step == 1
    assert [c.status for c in result.calls] == [429, 429, 200]


def test_5xx_retry_recovers_on_same_model(groq, monkeypatch):
    monkeypatch.setenv("GROQ_MODEL", M120)
    groq.reset(by_model={M120: [(503, {}, {"error": "busy"})]}, answers=['{"ok": 1}'])
    result = _generate()
    assert groq.models == [M120, M120] and result.model == M120 and not result.fallback_used
    assert groq.sleeps == [1.0]                             # no Retry-After: 1 s default


def test_rate_limited_model_is_skipped_then_recovers(groq, monkeypatch):
    monkeypatch.setenv("GROQ_MODEL", M120)
    groq.reset(by_model={M120: [RATE_LIMITED, RATE_LIMITED]}, answers=['{"a": 1}', '{"b": 2}', '{"c": 3}'])
    _generate()                                             # 120b is now cooling down
    groq.models.clear()
    second = _generate()
    assert groq.models == [M20]                             # 120b skipped without a wasted call
    assert second.calls[0].status == "skipped" and "cooling down" in second.calls[0].error

    # Automatic recovery: once the cooldown has passed, 120b is first again.
    state = llm_service.rate_limits._state[M120]
    state["cooldown_until"] = time.monotonic() - 1
    state["reset_at"] = time.monotonic() - 1
    groq.models.clear()
    third = _generate()
    assert groq.models == [M120] and third.model == M120


def test_model_near_its_token_limit_is_skipped(groq, monkeypatch):
    monkeypatch.setenv("GROQ_MODEL", M120)
    low = (200, {"x-ratelimit-remaining-tokens": "900", "x-ratelimit-reset-tokens": "40s"}, ok_body('{"a": 1}'))
    groq.reset(by_model={M120: [low]}, answers=['{"b": 2}'])
    _generate()                                             # 120b answers but reports 900 tokens left
    groq.models.clear()
    result = _generate()
    assert groq.models == [M20]
    assert "near its token limit" in result.calls[0].error


def test_overall_deadline_stops_the_chain(groq, monkeypatch):
    monkeypatch.setenv("GROQ_MODEL", M120)
    groq.reset(answers=['{"a": 1}'])
    try:
        _generate(budget=0.5)                               # less than the minimum time for a call
        raised = False
    except llm_service.AllModelsFailed as err:
        raised = err.deadline_exceeded
    assert raised and groq.models == []


def test_all_models_failing_raises_with_every_attempt(groq, monkeypatch):
    monkeypatch.setenv("GROQ_MODEL", M120)
    bad = (400, {}, {"error": {"code": "json_validate_failed"}})
    groq.reset(by_model={M120: [bad], M20: [bad], QWEN: [bad]})
    try:
        _generate()
        calls = None
    except llm_service.AllModelsFailed as err:
        calls = err.calls
    assert [c.model for c in calls] == [M120, M20, QWEN]    # 400 is not retried
    assert all(c.status == 400 for c in calls)


def test_token_usage_is_logged_and_aggregated(groq, monkeypatch, caplog):
    monkeypatch.setenv("GROQ_MODEL", M120)
    groq.reset(answers=['{"a": 1}'])
    with caplog.at_level(logging.INFO, logger="quantum_agent.llm_service"):
        result = _generate()
    assert result.usage == {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
    event = next(r.event for r in caplog.records if getattr(r, "event", {}).get("type") == "llm_call")
    assert event["model"] == M120 and event["total_tokens"] == 150 and event["fallback_step"] == 0
    assert event["latency_ms"] >= 0
    day = next(iter(usage_service.snapshot()["days"].values()))
    assert day["llm"][M120]["total_tokens"] == 150 and day["llm"][M120]["ok"] == 1


def _research(monkeypatch, uptrend):
    monkeypatch.setattr(engine, "_history", lambda s, p: uptrend)
    monkeypatch.setattr(engine, "_statements", lambda s: {})
    monkeypatch.setattr(engine, "_calendar", lambda s: {})
    return engine.build("TEST", {"name": "Test Co", "price": 300.0, "currency": "USD"}, articles=[])


def test_guardrails_reject_advice_and_invented_numbers_then_fall_back(groq, monkeypatch, uptrend):
    monkeypatch.setenv("GROQ_MODEL", M120)
    research = _research(monkeypatch, uptrend)
    sentiment = {"positive_drivers": [], "negative_drivers": []}
    advice = json.dumps(dict(GOOD, summary=GOOD["summary"] + " We recommend investors buy the stock now."))
    invented = json.dumps(dict(GOOD, bull_case=["Revenue reaches 412.5.", "Margins hit 47.8.", "Price is 905."]))
    groq.reset(answers=[advice, invented])
    out = asyncio.run(master_agent.analyze({}, {}, sentiment, research))
    assert out["llm"]["outcome"] == "rule" and out["fallback_active"]
    assert "advice" in out["llm"]["rejections"][0]
    assert "numbers not in the evidence" in out["llm"]["rejections"][1]
    assert out["llm"]["prompt_version"] == prompts.active_version()
    assert out["llm"]["tokens"]["total"] == 300


def test_prompt_registry_versions_and_env_override(monkeypatch):
    fields = dict(name="X", evidence="E", stance="is mixed", composite=50, confidence=60, risk="Low", categories="[]")
    v20 = prompts.render("v2.0", conflicted=True, **fields)
    v21 = prompts.render("v2.1", conflicted=True, **fields)
    assert "Mixed signals:" in v21 and "Mixed signals:" not in v20
    assert "Mixed signals" not in prompts.render("v2.1", conflicted=False, **fields)
    monkeypatch.setenv("PROMPT_VERSION", "v2.0")
    assert prompts.active_version() == "v2.0"
    monkeypatch.setenv("PROMPT_VERSION", "v9.9")
    assert prompts.active_version() == prompts.DEFAULT_PROMPT_VERSION
