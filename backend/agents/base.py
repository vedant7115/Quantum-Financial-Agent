# base.py
# The Agent interface and the three evidence agents.
#
#   async run(evidence, ctx) -> AgentResult
#
# Each agent fetches the data it needs (through the tiered cache), runs its part
# of the research engine in a worker thread, and returns its pillars and score.
# The pipeline runs all three at once with asyncio.gather and then the
# consensus step combines them. Agents never call the language model.

import asyncio
import os
from dataclasses import dataclass, field

from core.context import span
from services import news_service, research_engine
from services.cache_service import TieredCache


@dataclass
class Evidence:
    """What every agent receives: the symbol and its quote."""
    symbol: str
    stock_data: dict


@dataclass
class AgentContext:
    cache: TieredCache
    request_id: str = "-"


@dataclass
class AgentResult:
    name: str
    status: str                 # "ok", "unavailable" (no data) or "error" (raised)
    score: float = None
    data: dict = field(default_factory=dict)
    error: str = None
    duration_ms: float = 0.0


class Agent:
    name = "agent"

    async def run(self, evidence: Evidence, ctx: AgentContext) -> AgentResult:
        raise NotImplementedError


async def _cached_thread(ctx: AgentContext, tier: str, key: str, fn, *args):
    value, _ = await ctx.cache.get_or_compute(tier, key, lambda: asyncio.to_thread(fn, *args))
    return value


class TechnicalAgent(Agent):
    """Trend, momentum and stability from five years of daily closes and the benchmark."""
    name = "technical"

    async def run(self, evidence: Evidence, ctx: AgentContext) -> AgentResult:
        symbol = evidence.symbol
        bench_symbol, _ = research_engine.benchmark_for(symbol)
        close, bench = await asyncio.gather(
            _cached_thread(ctx, "price", f"history:{symbol}:5y", research_engine._history, symbol, "5y"),
            _cached_thread(ctx, "price", f"history:{bench_symbol}:2y", research_engine._history, bench_symbol, "2y"),
        )
        if len(close) < research_engine.MIN_CLOSES:
            return AgentResult(self.name, "unavailable", data={"close": close, "bench": bench},
                               error=f"only {len(close)} daily closes")
        price = await asyncio.to_thread(research_engine.price_part, symbol, close, bench)
        _, trend, momentum, _, _ = price
        return AgentResult(self.name, "ok", research_engine.technical_score_of(trend, momentum),
                           data={"close": close, "price": price})


class FundamentalAgent(Agent):
    """Profitability, growth, valuation and balance sheet from reported statements."""
    name = "fundamental"

    async def run(self, evidence: Evidence, ctx: AgentContext) -> AgentResult:
        symbol = evidence.symbol
        statements, events = await asyncio.gather(
            _cached_thread(ctx, "fundamentals", f"statements:{symbol}", research_engine._statements, symbol),
            _cached_thread(ctx, "fundamentals", f"calendar:{symbol}", research_engine._calendar, symbol),
        )
        fundamentals = await asyncio.to_thread(research_engine.fundamental_part, symbol, evidence.stock_data, statements)
        facts, quality, growth, valuation, balance = fundamentals
        score = research_engine.fundamental_score_of(quality, growth, valuation, balance)
        status = "ok" if facts is not None and score is not None else "unavailable"
        return AgentResult(self.name, status, score, data={"fundamentals": fundamentals, "events": events or {}})


class SentimentAgent(Agent):
    """Tone of recent, relevant headlines."""
    name = "sentiment"

    async def run(self, evidence: Evidence, ctx: AgentContext) -> AgentResult:
        symbol = evidence.symbol
        # A plain-ticker fallback is not a company name; news then searches by ticker.
        name = "" if evidence.stock_data.get("name_source") == "ticker" else evidence.stock_data.get("name", "")
        news, _ = await ctx.cache.get_or_compute("news", symbol, lambda: news_service.fetch_news(symbol, name))
        pillar = research_engine._news_pillar(news.get("articles", []))
        status = "ok" if pillar.score is not None else "unavailable"
        return AgentResult(self.name, status, pillar.score, data={"news": news, "pillar": pillar})


AGENTS = [TechnicalAgent(), FundamentalAgent(), SentimentAgent()]


# yfinance has no overall timeout of its own; an agent that takes longer than this
# is abandoned (its worker thread finishes in the background) so the request
# stays inside the frontend's 45-second limit.
AGENT_TIMEOUT_SECONDS = float(os.getenv("AGENT_TIMEOUT_SECONDS", "15"))


async def run_agent(agent: Agent, evidence: Evidence, ctx: AgentContext) -> AgentResult:
    """Runs one agent inside its own trace span, with a timeout. Never raises: a
    failure or timeout becomes status "error"."""
    with span(f"agent.{agent.name}") as sp:
        try:
            result = await asyncio.wait_for(agent.run(evidence, ctx), timeout=AGENT_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            result = AgentResult(agent.name, "error", error=f"timed out after {AGENT_TIMEOUT_SECONDS:.0f}s")
        except Exception as err:
            result = AgentResult(agent.name, "error", error=f"{type(err).__name__}: {str(err)[:200]}")
        sp.update(status=result.status, score=None if result.score is None else round(result.score, 1))
        if result.error:
            sp.update(detail=result.error)
    return result
