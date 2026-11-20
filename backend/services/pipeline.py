# pipeline.py
# Builds one report:
#
#   quote ──► [technical | fundamental | sentiment]  (asyncio.gather) ──► consensus ──► brief (LLM)
#
# Each stage is a span on the request's trace. Blocking work (yfinance, pandas)
# runs in worker threads via asyncio.to_thread, so the event loop stays free
# for other requests. The report returned here is cached and shared by every
# request for the same symbol; per-request fields (meta, trace, system_status,
# timeline, access) are added by the route.

import asyncio
import os
import time

from agents import fundamental_agent, master_agent, sentiment_agent, technical_agent
from agents.base import AGENTS, AgentContext, Evidence, run_agent
from core.context import current_trace, request_id_var, span
from services import research_engine, stock_service, usage_service
from services.cache_service import cache

LLM_DEADLINE_SECONDS = float(os.getenv("LLM_DEADLINE_SECONDS", "30"))
# The frontend gives up after 45 s; the brief must finish inside this whole-request budget.
REQUEST_BUDGET_SECONDS = float(os.getenv("REQUEST_BUDGET_SECONDS", "42"))


class InsufficientHistory(Exception):
    """Too few daily closes to assess the price."""


async def get_quote(symbol: str) -> dict:
    with span("quote") as sp:
        value, source = await cache.get_or_compute("price", f"quote:{symbol}",
                                                   lambda: asyncio.to_thread(stock_service.get_stock_data, symbol))
        sp.update(cache=source)
        return value


async def build_report(symbol: str, request_started: float) -> dict:
    """request_started is the event-loop time the request began (for the time budget)."""
    loop = asyncio.get_running_loop()
    stock_data = await get_quote(symbol)
    evidence = Evidence(symbol, stock_data)
    ctx = AgentContext(cache=cache, request_id=request_id_var.get())

    technical, fundamental, sentiment = await asyncio.gather(*(run_agent(a, evidence, ctx) for a in AGENTS))

    if technical.status != "ok":
        raise InsufficientHistory(technical.error or "price history unavailable")

    with span("consensus") as sp:
        research, sections = await asyncio.to_thread(_consensus, symbol, stock_data, technical, fundamental, sentiment)
        sp.update(composite=research["composite"], conflicted=research["conflicted"])

    deadline_at = min(loop.time() + LLM_DEADLINE_SECONDS, request_started + REQUEST_BUDGET_SECONDS)
    with span("brief") as sp:
        final_decision = await master_agent.analyze(
            sections["technical"], sections["fundamental"], sections["sentiment"], research, deadline_at=deadline_at)
        llm = final_decision.pop("llm")
        sp.update(outcome=llm["outcome"], model=llm["model"], total_tokens=llm["tokens"]["total"])

    if research["conflicted"]:
        usage_service.record_report("conflicted")
    usage_service.record_report("generated")
    trace = current_trace()

    sentiment_section = sections["sentiment"]
    sentiment_section["articles"] = sections["news"].get("articles", [])
    return {
        "stock": symbol,
        "current_price": stock_data["price"],
        "change_pct": stock_data["change_pct"],
        "market_state": stock_data.get("market_state", ""),
        "technical": sections["technical"],
        "fundamental": sections["fundamental"],
        "sentiment": sentiment_section,
        "final_decision": final_decision,
        "insight": research,
        "llm": llm,
        "generated": {"request_id": request_id_var.get(), "at": round(time.time(), 3),
                      "spans": trace.to_dict()["spans"] if trace else []},
    }


def _consensus(symbol, stock_data, technical, fundamental, sentiment):
    """Combines the agents' evidence (same formulas as research_engine.build) and
    formats the three response sections."""
    close, price = technical.data["close"], technical.data["price"]
    if fundamental.status == "error":
        fundamentals = research_engine.fundamental_part(symbol, stock_data, {})
        events = {}
    else:
        fundamentals, events = fundamental.data["fundamentals"], fundamental.data["events"]
    if sentiment.status == "error":
        news = {"symbol": symbol, "total_articles": 0, "articles": [], "source": "News unavailable"}
        pillar = research_engine._news_pillar([])
    else:
        news, pillar = sentiment.data["news"], sentiment.data["pillar"]

    research = research_engine.assemble(symbol, stock_data, close, price, fundamentals, pillar, events,
                                        news.get("articles", []))
    research["agent_scores"] = {
        r.name: {"score": None if r.score is None else round(r.score, 1), "status": r.status, "error": r.error}
        for r in (technical, fundamental, sentiment)
    }
    sections = {
        "technical": technical_agent.analyze(stock_data, research),
        "fundamental": fundamental_agent.analyze(stock_data, research),
        "sentiment": sentiment_agent.analyze(news),
        "news": news,
    }
    return research, sections
