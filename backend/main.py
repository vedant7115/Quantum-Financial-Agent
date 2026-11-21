# main.py — The entry point of our FastAPI backend
# Run this file to start the server: uvicorn main:app --reload
#
# Interactive API documentation available at:
#   /docs   ← Swagger UI
#   /redoc  ← ReDoc UI

import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router
from dotenv import load_dotenv

# Load environment variables at server start
load_dotenv()

# ── Thread pool for blocking work ────────────────────────────────────────────
# asyncio.to_thread uses the loop's default executor. Python sizes it from the
# CPU count (5 threads on a 1-CPU instance), but one report runs up to six
# blocking fetches at once, so the pool is sized for I/O instead.
THREAD_POOL_SIZE = int(os.getenv("THREAD_POOL_SIZE", "32"))


@asynccontextmanager
async def lifespan(app):
    executor = ThreadPoolExecutor(max_workers=THREAD_POOL_SIZE, thread_name_prefix="quantum-io")
    asyncio.get_running_loop().set_default_executor(executor)
    yield
    executor.shutdown(wait=False, cancel_futures=True)


# ── Create the FastAPI Application ───────────────────────────────────────────
app = FastAPI(
    lifespan=lifespan,
    title="QUANTUM AGENT API",
    description="Multi-Agent Financial Intelligence Platform — Technical, Fundamental & Sentiment Analysis",
    version="2.1.1",
)

# ── CORS (Cross-Origin Resource Sharing) ──────────────────────────────────────
# Allows frontend clients (Vercel, Netlify, localhost, etc.) to communicate with the API.
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "*").strip()

if allowed_origins_env == "*" or not allowed_origins_env:
    # Public / Open CORS (Standard for stateless public APIs)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    # Specific restricted origins
    origins = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# ── Register Routes ────────────────────────────────────────────────────────────
# All routes defined in api/routes.py are mounted under /api
app.include_router(router, prefix="/api")


# ── Root & Health Endpoints ──────────────────────────────────────────────────
@app.api_route("/", methods=["GET", "HEAD"])
async def root():
    """Welcome message and metadata for the API root."""
    return {
        "name": "QUANTUM AGENT API",
        "status": "online",
        "version": "2.1.1",
        "docs": "/docs",
        "endpoints": {
            "analyze": "POST /api/analyze",
            "health": "GET /api/health",
            "stock": "GET /api/stock/{symbol}",
            "price": "GET /api/price/{symbol}",
        },
    }


@app.api_route("/health", methods=["GET", "HEAD"])
@app.api_route("/api/health", methods=["GET", "HEAD"])
async def root_health():
    """Liveness probe / health check for cloud load balancers, orchestrators, and keep-alive pings."""
    return {
        "status": "ok",
        "groq_configured": bool(os.getenv("GROQ_API_KEY", "").strip()),
    }


# ── Run directly (for local development) ──────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    is_dev = os.getenv("ENV", "development").lower() != "production"
    uvicorn.run("main:app", host=host, port=port, reload=is_dev)
