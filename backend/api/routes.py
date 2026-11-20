# routes.py
# HTTP routes. The analysis itself lives in services/pipeline.py.
#
# /analyze is async end to end: blocking work runs in worker threads
# (asyncio.to_thread), the agents fan out with asyncio.gather, and identical
# concurrent requests share one computation through the tiered cache.

import asyncio
import json
import logging
import math
import os
import re
import threading
import time
from collections import defaultdict

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Request

import prompts
from core.context import (Trace, new_request_id, prompt_version_var, request_id_var, trace_var, traces)
from core.logging_setup import configure_logging
from models.schemas import AnalyzeRequest, AnalyzeResponse
from services import billing_service, cache_service, llm_service, pipeline, stock_service, usage_service
from services.cache_service import cache

load_dotenv()
configure_logging()
logger = logging.getLogger("quantum_agent.api")

# ── Per-client rate limit (sliding window, in memory) ─────────────────────────
_rate_limits = defaultdict(list)
_rate_lock = threading.Lock()


def is_rate_limited(client_id: str, limit: int = 5, window: int = 60) -> bool:
    """Allows up to `limit` requests per `window` seconds from one client."""
    now = time.time()
    with _rate_lock:
        recent = [t for t in _rate_limits[client_id] if now - t < window]
        if len(recent) >= limit:
            _rate_limits[client_id] = recent
            return True
        recent.append(now)
        _rate_limits[client_id] = recent
        return False


def is_valid_symbol_format(symbol: str) -> bool:
    """Equity tickers: 1-15 letters, digits, dots or dashes (RELIANCE.NS, BRK-B)."""
    return bool(re.match(r"^[A-Z0-9\.\-]{1,15}$", symbol))


# ── Demo mode ─────────────────────────────────────────────────────────────────
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
DEMO_REPORTS = {}
if DEMO_MODE:
    try:
        demo_path = os.path.join(os.path.dirname(__file__), "..", "config", "demo_reports.json")
        with open(demo_path, "r", encoding="utf-8") as f:
            DEMO_REPORTS = json.load(f)
        logger.info(f"DEMO_MODE active. Loaded {len(DEMO_REPORTS)} demo reports.")
    except Exception as demo_err:
        logger.error(f"Could not load demo_reports.json: {demo_err}")

router = APIRouter()


def sanitize_nans(obj):
    """Recursively replace NaN/Infinity floats with 0.0 for JSON safety."""
    if isinstance(obj, dict):
        return {k: sanitize_nans(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_nans(i) for i in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return 0.0
    return obj


def _require_admin(req: Request):
    token = os.getenv("ADMIN_TOKEN", "").strip()
    if not token or req.headers.get("x-admin-token", "") != token:
        raise HTTPException(status_code=403, detail="FORBIDDEN")


def _timeline(spans: list, started_at: float) -> list:
    """The older timeline field, derived from the trace spans."""
    out = [{"timestamp": time.strftime("%H:%M:%S", time.localtime(started_at)), "event": "Request Received"}]
    for s in spans:
        if s["name"].startswith("llm."):
            continue
        out.append({"timestamp": time.strftime("%H:%M:%S", time.localtime(started_at + s["end_ms"] / 1000)),
                    "event": f"{s['name']} ({s['status']}, {s['duration_ms']:.0f} ms)"})
    return out


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_stock(request: AnalyzeRequest, req: Request):
    """
    POST /analyze
    quote -> technical | fundamental | sentiment (concurrent) -> consensus -> brief.
    """
    access = billing_service.resolve_access(req)
    if is_rate_limited(access["client_id"], limit=10, window=60):
        logger.warning(f"Rate limit exceeded for {billing_service.client_ip(req)}")
        raise HTTPException(status_code=429, detail="RATE_LIMIT_EXCEEDED")

    symbol = request.symbol.upper().strip()
    if not symbol:
        raise HTTPException(status_code=400, detail="Stock ticker symbol cannot be empty")
    if not is_valid_symbol_format(symbol):
        raise HTTPException(status_code=400, detail="INVALID_TICKER")

    loop = asyncio.get_running_loop()
    request_started = loop.time()
    request_id = new_request_id()
    version = prompts.active_version()
    trace = Trace(request_id, symbol, version)
    tokens = (request_id_var.set(request_id), prompt_version_var.set(version), trace_var.set(trace))
    usage_service.record_report("requests")

    try:
        with trace.span("resolve") as sp:
            resolved = await asyncio.to_thread(stock_service.resolve_symbol, symbol)
            sp.update(resolved=resolved)
        trace.symbol = resolved

        # Quota is counted against the resolved symbol, so "RELIANCE" and "RELIANCE.NS" count once.
        if not billing_service.can_analyze(access, resolved):
            raise HTTPException(status_code=402, detail={"code": "QUOTA_EXCEEDED", **billing_service.access_summary(access)})

        def deliver(report: dict) -> dict:
            billing_service.record_analysis(access, resolved)
            return billing_service.apply_entitlements(report, access)

        if DEMO_MODE and symbol in DEMO_REPORTS:
            demo = json.loads(json.dumps(DEMO_REPORTS[symbol]))
            demo.setdefault("system_status", {})["cache_status"] = "Demo Hit"
            return deliver(demo)

        with trace.span("validate") as sp:
            valid, source = await cache.get_or_compute(
                "price", f"valid:{resolved}", lambda: asyncio.to_thread(stock_service.is_ticker_valid, resolved))
            sp.update(cache=source, valid=valid)
        if not valid:
            raise HTTPException(status_code=400, detail="INVALID_TICKER")

        try:
            with trace.span("report") as sp:
                report, source = await cache.get_or_compute(
                    "report", resolved, lambda: pipeline.build_report(resolved, request_started))
                sp.update(cache=source)
        except stock_service.MarketDataUnavailable as err:
            logger.error(f"Market data unavailable for {resolved}: {err}")
            raise HTTPException(status_code=502, detail="DATA_UNAVAILABLE")
        except pipeline.InsufficientHistory as err:
            logger.error(f"Not enough price history for {resolved}: {err}")
            raise HTTPException(status_code=500, detail=f"Data pipeline failure for {resolved}: {err}")

        if source == "hit":
            usage_service.record_report("cache_hits")
        elif source == "coalesced":
            usage_service.record_report("coalesced")

        generated = report.pop("generated", {}) or {}
        exec_time = round(loop.time() - request_started, 3)
        llm = report.get("llm") or {}
        fallback_active = report["final_decision"].get("fallback_active", False)
        trace.attrs.update({"cache": source, "generated_by_request": generated.get("request_id")})
        trace_dict = trace.to_dict()
        if source != "miss":
            # The spans that built the report belong to the request that generated it.
            trace_dict["generation_spans"] = generated.get("spans", [])

        report["system_status"] = {
            "backend_status": "Online",
            "groq_status": "Fallback Mode" if fallback_active else ("Online" if os.getenv("GROQ_API_KEY") else "Offline"),
            "yfinance_status": "Online",
            "news_status": "Online",
            "cache_status": {"hit": "Hit", "coalesced": "Coalesced", "miss": "Miss"}[source],
            "cache_ttl_sec": cache.ttl_remaining("report", resolved) if source != "miss" else cache.ttls["report"],
            "execution_time_sec": exec_time,
        }
        report["timeline"] = _timeline(trace_dict["spans"], trace.started_at)
        report["meta"] = {
            "request_id": request_id,
            "prompt_version": llm.get("prompt_version", version),
            "cache": source,
            "generated_by_request": generated.get("request_id"),
            "execution_time_sec": exec_time,
        }
        report["trace"] = trace_dict
        report = sanitize_nans(report)
        logger.info("report", extra={"event": {
            "type": "report", "symbol": resolved, "cache": source, "execution_ms": round(exec_time * 1000, 1),
            "composite": report["insight"]["composite"], "conflicted": report["insight"].get("conflicted"),
            "model": llm.get("model"), "outcome": llm.get("outcome"),
            "total_tokens": (llm.get("tokens") or {}).get("total")}})
        return deliver(report)
    except HTTPException:
        raise
    except Exception as err:
        usage_service.record_report("errors")
        logger.exception(f"Analysis failed for {symbol}")
        raise HTTPException(status_code=500, detail=f"Analysis failure for {symbol}: {err}")
    finally:
        traces.add(trace.to_dict())
        for var, token in zip((request_id_var, prompt_version_var, trace_var), tokens):
            var.reset(token)


@router.get("/plans")
async def list_plans():
    """GET /plans — the plans and prices shown on the pricing page."""
    return {"plans": billing_service.public_plans()}


@router.get("/usage")
async def get_usage(req: Request):
    """GET /usage — the caller's plan, locked sections and reports left today."""
    return billing_service.access_summary(billing_service.resolve_access(req))


@router.get("/health")
async def health_check():
    """GET /health — liveness and configuration flags."""
    groq_loaded = bool(os.environ.get("GROQ_API_KEY", "").strip())
    gemini_loaded = bool(os.environ.get("GEMINI_API_KEY", "").strip())
    return {
        "status": "ok",
        "message": "QUANTUM AGENT Backend is fully operational",
        "environment": {
            "groq_api_key_configured": groq_loaded,
            "gemini_api_key_configured": gemini_loaded,
            "prompt_version": prompts.active_version(),
        },
    }


@router.get("/stock/{symbol}")
async def get_stock_info(symbol: str):
    """GET /stock/{symbol} — raw quote metrics and several historical timeframes."""
    resolved = await asyncio.to_thread(stock_service.resolve_symbol, symbol)
    try:
        stock_data, timeframe_data = await asyncio.gather(
            asyncio.to_thread(stock_service.get_stock_data, resolved),
            asyncio.to_thread(stock_service.get_multiple_timeframes, resolved))
        return sanitize_nans({"stock": stock_data, "timeframes": timeframe_data})
    except stock_service.MarketDataUnavailable:
        raise HTTPException(status_code=502, detail="DATA_UNAVAILABLE")
    except Exception as e:
        logger.error(f"Error fetching stock info for {resolved}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch stock detail for {resolved}: {e}")


def _live_price(resolved: str) -> dict:
    import yfinance as yf
    fi = yf.Ticker(resolved, session=stock_service._yf_session).fast_info
    last_price = getattr(fi, "last_price", None)
    prev_close = getattr(fi, "previous_close", None)
    if not last_price:
        raise ValueError("fast_info returned no price")
    last_price = float(last_price)
    prev_close = float(prev_close) if prev_close else last_price
    change = last_price - prev_close
    return {
        "symbol": resolved,
        "price": round(last_price, 2),
        "change": round(change, 2),
        "change_pct": round((change / prev_close * 100) if prev_close else 0.0, 2),
        "previous_close": round(prev_close, 2),
        "market_cap": getattr(fi, "market_cap", None),
        "source": "Yahoo Finance fast_info (live)",
    }


@router.get("/price/{symbol}")
async def get_live_price(symbol: str):
    """GET /price/{symbol} — live price from fast_info, bypassing the cache."""
    resolved = await asyncio.to_thread(stock_service.resolve_symbol, symbol.upper().strip())
    try:
        return sanitize_nans(await asyncio.to_thread(_live_price, resolved))
    except Exception as e:
        logger.error(f"Live price fetch failed for {resolved}: {e}")
        raise HTTPException(status_code=500, detail=f"Live price unavailable for {resolved}: {e}")


@router.post("/clear-cache")
async def clear_analysis_cache(req: Request):
    """POST /clear-cache — empties every cache tier. Requires the x-admin-token header."""
    _require_admin(req)
    cache_service.clear_cache()
    logger.info("Cache cleared via admin endpoint.")
    return {"status": "ok", "message": "Analysis cache cleared. Next requests will fetch fresh data."}


@router.get("/admin/traces")
async def admin_traces(req: Request, limit: int = 50):
    """GET /admin/traces — the most recent request traces (up to 200 kept). Requires x-admin-token."""
    _require_admin(req)
    return {"traces": traces.recent(min(max(limit, 1), 200))}


@router.get("/admin/usage")
async def admin_usage(req: Request):
    """GET /admin/usage — daily LLM usage, brief outcomes and cache counters. Requires x-admin-token."""
    _require_admin(req)
    return {
        "prompt_version": prompts.active_version(),
        "model_chain": llm_service.model_chain(),
        "rate_limits": llm_service.rate_limits.snapshot(),
        "cache": cache.stats(),
        **usage_service.snapshot(),
    }
