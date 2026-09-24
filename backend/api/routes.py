# routes.py
# This file defines the FastAPI routes and wires them to the analytical pipeline.
# Includes structured logging, validation error handlers, and dotenv reading.

from fastapi import APIRouter, HTTPException, Depends, Request
from models.schemas import AnalyzeRequest, AnalyzeResponse
from agents import technical_agent, fundamental_agent, sentiment_agent, master_agent
from services import stock_service, news_service, cache_service
import logging
import os
from dotenv import load_dotenv
import time
import re
import json
import math
from collections import defaultdict

# Load environment variables from .env
load_dotenv()

from logging.handlers import RotatingFileHandler

# Setup logging
log_handlers = [logging.StreamHandler()]
try:
    log_file = os.getenv("LOG_FILE", "quantum_system.log")
    log_handlers.append(RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5, encoding="utf-8"))
except Exception:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=log_handlers
)
logger = logging.getLogger("quantum_agent.api")

# In-memory IP rate limiter state
_rate_limits = defaultdict(list)

def is_rate_limited(ip: str, limit: int = 5, window: int = 60) -> bool:
    """Allows up to 'limit' requests per 'window' seconds from a single IP."""
    now = time.time()
    # Keep only timestamps within the sliding window
    _rate_limits[ip] = [t for t in _rate_limits[ip] if now - t < window]
    if len(_rate_limits[ip]) >= limit:
        return True
    _rate_limits[ip].append(now)
    return False

def is_valid_symbol_format(symbol: str) -> bool:
    """Checks for standard equity tickers (1-15 Alphanumerics, optional NSE dot or suffix)."""
    return bool(re.match(r"^[A-Z0-9\.\-]{1,15}$", symbol))

# Demo Mode Setup
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
DEMO_REPORTS = {}

if DEMO_MODE:
    try:
        demo_path = os.path.join(os.path.dirname(__file__), "..", "config", "demo_reports.json")
        if os.path.exists(demo_path):
            with open(demo_path, "r", encoding="utf-8") as f:
                DEMO_REPORTS = json.load(f)
            logger.info(f"DEMO_MODE active. Loaded {len(DEMO_REPORTS)} demo reports from cache.")
        else:
            logger.warning(f"DEMO_MODE is active but demo_reports.json was not found at {demo_path}")
    except Exception as demo_err:
        logger.error(f"Error loading demo_reports.json in API initialization: {str(demo_err)}")

router = APIRouter()

def sanitize_nans(obj):
    """Recursively replace NaN/Infinity float values with 0 or None for JSON safety."""
    if isinstance(obj, dict):
        return {k: sanitize_nans(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_nans(i) for i in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return 0.0
        return obj
    return obj


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_stock(request: AnalyzeRequest, req: Request):
    """
    POST /analyze
    Takes a ticker symbol, coordinates the data fetching and multi-agent 
    analysis flow, aggregates signals through the Master Agent, and returns the analysis.
    """
    # ── Step 0a: Rate Limiting Safety Check ──
    client_ip = req.client.host if req.client else "127.0.0.1"
    if is_rate_limited(client_ip, limit=10, window=60):
        logger.warning(f"Rate limit exceeded for client IP: {client_ip}")
        raise HTTPException(
            status_code=429,
            detail="RATE_LIMIT_EXCEEDED"
        )

    start_time = time.perf_counter()
    symbol = request.symbol.upper().strip()
    
    # ── Step 0b: Input Formatting Validation ──
    if not symbol:
        raise HTTPException(status_code=400, detail="Stock ticker symbol cannot be empty")
        
    if not is_valid_symbol_format(symbol):
        logger.warning(f"Invalid stock ticker symbol format: {symbol}")
        raise HTTPException(status_code=400, detail="INVALID_TICKER")

    # ── Step 0c: Demo Mode Check ──
    if DEMO_MODE and symbol in DEMO_REPORTS:
        logger.info(f"DEMO_MODE active: serving pre-cached report for {symbol} instantly.")
        demo_report = json.loads(json.dumps(DEMO_REPORTS[symbol])) # deep copy
        now_time = time.time()
        
        # Override timestamps dynamically for smooth frontend animation
        demo_report["timeline"] = [
            {"timestamp": time.strftime("%H:%M:%S", time.localtime(now_time)), "event": "Request Received"},
            {"timestamp": time.strftime("%H:%M:%S", time.localtime(now_time + 0.05)), "event": "Market Data Ingested (Demo)"},
            {"timestamp": time.strftime("%H:%M:%S", time.localtime(now_time + 0.1)), "event": "Technical Intel Generated (Demo)"},
            {"timestamp": time.strftime("%H:%M:%S", time.localtime(now_time + 0.15)), "event": "Fundamental Intel Generated (Demo)"},
            {"timestamp": time.strftime("%H:%M:%S", time.localtime(now_time + 0.2)), "event": "Sentiment Intel Generated (Demo)"},
            {"timestamp": time.strftime("%H:%M:%S", time.localtime(now_time + 0.25)), "event": "Consensus Aggregated (Demo)"},
            {"timestamp": time.strftime("%H:%M:%S", time.localtime(now_time + 0.3)), "event": "Report Dispatched"}
        ]
        if "system_status" in demo_report:
            demo_report["system_status"]["execution_time_sec"] = 0.3
            demo_report["system_status"]["cache_status"] = "Demo Hit"
        return demo_report

    # ── Step 0d: Live Ticker Existence Check ──
    # Check if symbol actually exists on yfinance before doing expensive queries
    if not stock_service.is_ticker_valid(symbol):
        logger.warning(f"Ticker validation failed: Ticker {symbol} does not exist.")
        raise HTTPException(status_code=400, detail="INVALID_TICKER")

    timeline = []
    
    def add_to_timeline(event: str):
        current_time_str = time.strftime("%H:%M:%S", time.localtime())
        timeline.append({"timestamp": current_time_str, "event": event})
        
    add_to_timeline("Request Received")
    logger.info(f"Received analysis request for symbol: {symbol}")
    
    # ── Step 1: Check Cache ──
    cached_result = cache_service.get_from_cache(symbol)
    if cached_result:
        logger.info(f"Returning cached analysis for symbol: {symbol}")
        try:
            cache_info = cache_service.get_cache_info(symbol)
            fallback_active = cached_result.get("final_decision", {}).get("fallback_active", False)
            cached_result["system_status"] = {
                "backend_status": "Online",
                "groq_status": "Fallback Mode" if fallback_active else ("Online" if os.getenv("GROQ_API_KEY") else "Offline"),
                "yfinance_status": "Online",
                "news_status": "Online",
                "cache_status": "Hit",
                "cache_ttl_sec": cache_info["ttl_remaining"],
                "execution_time_sec": round(time.perf_counter() - start_time, 3)
            }
            
            # Append cache-specific timeline stages
            cached_result["timeline"] = [
                {"timestamp": time.strftime("%H:%M:%S", time.localtime(time.time() - 0.05)), "event": "Request Received"},
                {"timestamp": time.strftime("%H:%M:%S", time.localtime(time.time())), "event": "Cached Report Retrieved"},
                {"timestamp": time.strftime("%H:%M:%S", time.localtime(time.time())), "event": "Report Dispatched"}
            ]
            return cached_result
        except Exception as cache_err:
            logger.warning(f"Cached schema mismatch for {symbol}. Recalculating. Error: {str(cache_err)}")
            cache_service.clear_cache()
            
    # ── Step 2: Fetch Real-Time Market and News Data ──
    logger.info(f"Fetching market data and historical timeframes for {symbol}...")
    try:
        resolved_symbol = stock_service.resolve_symbol(symbol)
        
        # Sequentially fetch datasets
        stock_data = stock_service.get_stock_data(resolved_symbol)
        timeframe_data = stock_service.get_multiple_timeframes(resolved_symbol)
        news_data = news_service.get_news(resolved_symbol)
        
        add_to_timeline("Market Data Ingested")
        logger.info(f"Successfully retrieved data. Executing analysis pipeline...")
        
    except Exception as data_err:
        logger.error(f"Data acquisition failure for {symbol}: {str(data_err)}")
        raise HTTPException(
            status_code=500,
            detail=f"Data pipeline failure for {symbol}: {str(data_err)}"
        )
        
    # ── Step 3: Run Sub-Agent Analyses ──
    try:
        # Technical Agent (assesses multi-timeframe closes)
        logger.info(f"Running Technical Analysis Agent for {resolved_symbol}...")
        technical_result = technical_agent.analyze(stock_data, timeframe_data)
        add_to_timeline("Technical Intel Generated")
        
        # Fundamental Agent (assesses earnings, margins, valuation)
        logger.info(f"Running Fundamental Analysis Agent for {resolved_symbol}...")
        fundamental_result = fundamental_agent.analyze(stock_data)
        add_to_timeline("Fundamental Intel Generated")
        
        # Sentiment Agent (assesses recent news headlines)
        logger.info(f"Running Sentiment Analysis Agent for {resolved_symbol}...")
        sentiment_result = sentiment_agent.analyze(news_data)
        add_to_timeline("Sentiment Intel Generated")
        
    except Exception as agent_err:
        logger.error(f"Analytical sub-agent failure for {resolved_symbol}: {str(agent_err)}")
        raise HTTPException(
            status_code=500,
            detail=f"Analytical sub-agent failure: {str(agent_err)}"
        )
        
    # ── Step 4: Run Master Agent synthesis ──
    try:
        logger.info(f"Running Master Synthesis Agent to aggregate indicators...")
        final_decision = master_agent.analyze(
            technical_result, 
            fundamental_result, 
            sentiment_result
        )
        add_to_timeline("Consensus Aggregated")
    except Exception as master_err:
        logger.error(f"Master Agent synthesis failure for {resolved_symbol}: {str(master_err)}")
        raise HTTPException(
            status_code=500,
            detail=f"Master Agent synthesis failure: {str(master_err)}"
        )
        
    # ── Step 5: Format and Cache Response ──
    # Attach raw articles to sentiment result for frontend News Insights presentation
    sentiment_result["articles"] = news_data.get("articles", [])

    fallback_active = final_decision.get("fallback_active", False)
    exec_time = round(time.perf_counter() - start_time, 3)

    system_status = {
        "backend_status": "Online",
        "groq_status": "Fallback Mode" if fallback_active else ("Online" if os.getenv("GROQ_API_KEY") else "Offline"),
        "yfinance_status": "Online",
        "news_status": "Online",
        "cache_status": "Miss",
        "cache_ttl_sec": 300,
        "execution_time_sec": exec_time
    }

    add_to_timeline("Report Dispatched")

    response_data = {
        "stock": resolved_symbol,
        "current_price": stock_data["price"],
        "change_pct": stock_data["change_pct"],
        "market_state": stock_data.get("market_state", ""),
        "technical": technical_result,
        "fundamental": fundamental_result,
        "sentiment": sentiment_result,
        "final_decision": final_decision,
        "system_status": system_status,
        "timeline": timeline
    }
    
    # Sanitize all NaN/Inf floats before caching and returning
    response_data = sanitize_nans(response_data)
    
    # Store in cache
    cache_service.set_in_cache(resolved_symbol, response_data)
    logger.info(f"Completed analysis and cached response for {resolved_symbol}")
    
    return response_data


@router.get("/health")
async def health_check():
    """
    GET /health
    Pings backend server status and verifies environment.
    """
    groq_loaded = "GROQ_API_KEY" in os.environ and bool(os.environ["GROQ_API_KEY"].strip())
    gemini_loaded = "GEMINI_API_KEY" in os.environ and bool(os.environ["GEMINI_API_KEY"].strip())
    return {
        "status": "ok",
        "message": "QUANTUM AGENT Backend is fully operational",
        "environment": {
            "groq_api_key_configured": groq_loaded,
            "gemini_api_key_configured": gemini_loaded
        }
    }

@router.get("/stock/{symbol}")
async def get_stock_info(symbol: str):
    """
    GET /stock/{symbol}
    Returns raw ticker metrics and multiple historical timeframe closes.
    """
    resolved_symbol = stock_service.resolve_symbol(symbol)
    try:
        stock_data = stock_service.get_stock_data(resolved_symbol)
        timeframe_data = stock_service.get_multiple_timeframes(resolved_symbol)
        return sanitize_nans({
            "stock": stock_data,
            "timeframes": timeframe_data
        })
    except Exception as e:
        logger.error(f"Error fetching stock info for {resolved_symbol}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch stock detail for {resolved_symbol}: {str(e)}"
        )


@router.get("/price/{symbol}")
async def get_live_price(symbol: str):
    """
    GET /price/{symbol}
    Lightweight, cache-bypassing endpoint that returns the live price
    in ~1 second using fast_info. Ideal for real-time UI polling.
    """
    import yfinance as yf
    resolved_symbol = stock_service.resolve_symbol(symbol.upper().strip())
    try:
        ticker = yf.Ticker(resolved_symbol, session=stock_service._yf_session)
        fi = ticker.fast_info
        last_price    = getattr(fi, "last_price", None)
        prev_close    = getattr(fi, "previous_close", None)
        market_cap    = getattr(fi, "market_cap", None)

        if not last_price:
            raise ValueError("fast_info returned no price")

        last_price = float(last_price)
        prev_close = float(prev_close) if prev_close else last_price
        change     = last_price - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0.0

        return sanitize_nans({
            "symbol": resolved_symbol,
            "price": round(last_price, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "previous_close": round(prev_close, 2),
            "market_cap": market_cap,
            "source": "Yahoo Finance fast_info (live)"
        })
    except Exception as e:
        logger.error(f"Live price fetch failed for {resolved_symbol}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Live price unavailable for {resolved_symbol}: {str(e)}"
        )


@router.post("/clear-cache")
async def clear_analysis_cache():
    """
    POST /clear-cache
    Flushes all in-memory cached analysis results. Use between demo runs
    to ensure fresh data without restarting the server.
    """
    cache_service.clear_cache()
    logger.info("Cache cleared via admin endpoint.")
    return {"status": "ok", "message": "Analysis cache cleared. Next requests will fetch fresh data."}

