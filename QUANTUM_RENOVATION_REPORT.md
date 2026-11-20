# QUANTUM Renovation Report (v1 → v2.0.0)

Written 2026-11-20 from the code on `main` (tag `v2.0.0`, commit `b4cbcf4`). v1 means commit `9b4a208`, the last commit before the renovation.

Every item carries one label:

- **VERIFIED IN CODE**: present in the code, with file and function cited, and it runs.
- **PARTIAL**: present but incomplete, or with a limitation stated next to it.
- **NOT IMPLEMENTED**: not in the code. Do not claim it.

Numbers marked *measured* come from the benchmark in section 2.4. They were run on one Windows laptop against the live Groq API on 2026-11-20, with three stocks per version. That is a small sample; quote the numbers as approximate.

---

## 1. Summary

| | v1 | v2 |
| :-- | :-- | :-- |
| Who decides the score | Code computed a weighted score (technical 40%, fundamental 35%, sentiment 25%), but the model's JSON could overwrite `market_bias`, `confidence` and `risk` (v1 `master_agent.py`, lines 299–301) | Fixed rules calculate every score; the model only writes the explanation and cannot change the bias, confidence or risk |
| LLM calls per report | 1 by default (master). Each sub-agent had its own LLM call, switched off unless `ENABLE_SUBAGENT_LLM=true`, giving 4 | 1 (master brief only); sub-agent LLM code removed |
| Sub-agent inputs | About 8 indicators from 1 year of prices; fundamentals from `ticker.info` | Up to 28 checks from 5 years of prices, the benchmark and reported statements |
| Fundamentals | `ticker.info`, which failed on Render and returned zeros | Reported financial statements from yfinance |
| Bad tickers / failed data | Random mock prices and headlines labelled as Reuters or Bloomberg | 400 `INVALID_TICKER` or 502 `DATA_UNAVAILABLE`; mock data only with `ALLOW_MOCK_DATA=true` |
| Catalyst dates | Invented by the model, some in the past | Real earnings and ex-dividend dates from yfinance, future dates only |
| Business model | None | Free / Plus ₹149 / Pro ₹499 plans with daily quotas and signed keys |
| Frontend | 86 KB report file with formulas invented in the browser | New home, report and pricing pages; shareable URLs |

- **Added:** evidence engine (8 pillars, up to 28 checks), historical base rates, benchmark comparison, LLM output checks, model fallback chain sized to Groq's free tier, plans and quotas, new UI.
- **Fixed:** dead fundamentals on Render, reports for non-existent tickers, fabricated headlines, invented catalyst dates, misread "downgrade" headlines, browser-side invented numbers.
- **Removed from use:** per-agent LLM calls, mock data in production, the old landing, report and architecture screens (unlinked; files still in the repo).

---

## 2. Models and fallbacks

### 2.1 Model chain

**VERIFIED IN CODE**: `backend/services/llm_service.py`, `query_groq()`; `backend/agents/master_agent.py`, `analyze()`.

The chain, in order:

| Step | What runs | Trigger to move to the next step |
| :-- | :-- | :-- |
| 1 | `GROQ_MODEL` env var (Render sets `openai/gpt-oss-120b`; code default is the same) | Any exception from the HTTP call |
| 2 | `openai/gpt-oss-20b` | Same |
| 3 | `qwen/qwen3.8-27b` | Same |
| 4 | Rule-written brief, `master_agent._rule_view()` | All models failed, or the answer was rejected (see below) |

Models are de-duplicated, so if `GROQ_MODEL` is one of the three it is not tried twice (`FALLBACK_MODELS`).

**What counts as a failure in `query_groq()`.** Any exception inside the `try` moves to the next model:
- HTTP error status via `raise_for_status()`: 429 rate limit, 400 (including Groq's own `json_validate_failed`, because `response_format: json_object` is set), 404 model not found, 5xx.
- Timeout: `timeout=25.0` seconds per model (httpx raises).
- Network errors.
- A response with no `choices`.

**What sends a report straight to the rule-written brief in `master_agent.analyze()`.** These do **not** try the next model:
- `json.loads` fails on the returned text.
- The text matches `ADVICE_PATTERN` ("we recommend", "target price", "should buy" and similar).
- More than 2 numbers in the text are not found in the evidence (`_unsupported_numbers()`).
- All models raised.

**Retries and backoff: NOT IMPLEMENTED.** Each model is tried exactly once. There is no retry on the same model, no exponential backoff, and the `retry-after` header is not read. The worst case is three timeouts, about 75 seconds, which is longer than the frontend's 45-second axios timeout (`frontend/src/api.js`). In that case the user sees an error even though the backend would eventually answer with the rule-written brief.

### 2.2 Ollama, local models, routing

- **Ollama or local models: NOT IMPLEMENTED.** No Ollama client or local model anywhere in the code. All LLM calls go to `https://api.groq.com/openai/v1/chat/completions`.
- **Routing: NOT IMPLEMENTED.** This is a fixed-order **fallback chain**, not routing. Every request starts with the same model; there is no selection by task, cost or prompt size.
- **Dead code:** `backend/agents/base_agent.py` contains an OpenRouter client. Nothing imports it.

### 2.3 Token use and the 8,000 tokens-per-minute limit

**VERIFIED IN CODE**: `llm_service.py`.

- Groq's free tier gives each model 8,000 tokens a minute; `qwen/qwen3.8-27b` also has a 1,000 output-tokens-a-minute limit (read from Groq's 429 response during testing).
- Handling in code:
  - One LLM call per report; the optional sub-agent LLM calls from v1 are removed, so the four-call path can no longer be switched on.
  - `max_completion_tokens` = 1,600 (`MAX_OUTPUT_TOKENS`, env `GROQ_MAX_OUTPUT_TOKENS`). **This cap is on the master call's answer.** It is not a reduction inside the sentiment agent; the sentiment agent makes no LLM call at all.
  - `reasoning_effort: "low"` for the gpt-oss models.
  - When a model returns 429, the next model is tried immediately; each model has its own per-minute allowance.
  - Reports are cached for 15 minutes, so repeat views use no tokens.
- **There is no token budgeting, queueing or pre-emptive rate tracking.** The code does not read the `x-ratelimit-remaining-tokens` header; it reacts to 429s after they happen.

### 2.4 Measured: tokens and latency, v1 vs v2

**Method.** A script patched `httpx.Client.post` to record Groq's `usage` field and the time of every LLM call, then sent `POST /api/analyze` through FastAPI's `TestClient` with an empty cache, 65 seconds apart so the per-minute token window reset. v1 was run from a checkout of `9b4a208` with `GROQ_MODEL=openai/gpt-oss-20b` (its Render setting); v2 from `main` with `openai/gpt-oss-120b`. The script is not in the repo.

| Configuration | LLM calls per report | Tokens per report | Full report time |
| :-- | :-- | :-- | :-- |
| v1, default (`ENABLE_SUBAGENT_LLM` off) | 1 (one report needed 2 because 20b failed JSON validation) | 2,200 – 2,590 | 7.4 – 11.5 s |
| v1, sub-agent LLM on | 4 (5 when 20b failed JSON validation) | **8,368 – 8,394** | 13.8 – 19.8 s |
| v2 | 1 | 2,013 – 2,346 | 8.3 – 10.1 s |

What this does and does not show:

- **Against v1's default setting, v2 did not reduce tokens or latency in any meaningful way.** Tokens are about the same; the time is about the same, because v2 fetches more data (5 years of prices, a benchmark and four financial statements) while dropping v1's intraday fetches.
- **Against v1 with sub-agent LLM calls on, v2 uses 72–76% fewer tokens and is faster on average (9.1 s against 16.8 s).** That v1 configuration used more than 8,000 tokens per report, so a single report exceeded Groq's free-tier minute limit for that model.
- What v2 actually gained is **correctness and reliability**, not speed: the scores no longer depend on the model, fundamentals work on Render, and the brief is checked.
- In v1, `gpt-oss-20b` failed Groq's JSON validation on 2 of 9 calls measured here; in v2 the 120b model passed on all calls in this run.
- The AI call itself took 2.3 – 2.8 s in v2; the rest of each report is data fetching.
- An earlier test (2026-11-17) on six stocks gave v2 1,844 – 2,322 tokens per brief, and a burst of nine reports with no pauses all received an AI brief: five from 120b, then the rest via fallback after 120b returned 429.
- Live on Render (2026-11-17): 4.8 s and 7.2 s for two reports.

---

## 3. Agents

In v2 the three agents are **thin formatters over the evidence engine**. They contain no LLM calls and no scoring logic of their own; they reshape `research_engine.build()` output into the response schema.

### 3.1 Technical agent

**VERIFIED IN CODE**: indicators in `backend/services/research_engine.py`, `analyse_price()` and `_rsi()`; formatting in `backend/agents/technical_agent.py`, `analyze()`.

- **Data:** yfinance `Ticker.history(period="5y", interval="1d")` for the stock and `period="2y"` for the benchmark (`_history()`). Daily closes only; no intraday data in v2.
- **Benchmark:** `^GSPC` (S&P 500), or `^NSEI` (Nifty 50) for `.NS`, `^BSESN` (Sensex) for `.BO` (`benchmark_for()`).
- **Computed in code:**
  - 50-day and 200-day simple moving averages; slope of the 200-day over 21 trading days
  - RSI(14), Wilder smoothing via EWM
  - MACD (12, 26, 9) histogram
  - Returns over 1, 3, 6 and 12 months
  - 60-day annualised volatility
  - Max drawdown over 1 year; distance from the 52-week high; 52-week range position
  - Beta against the benchmark (1 year of daily returns, aligned by calendar date)
  - Relative return against the benchmark over 3 and 12 months
  - 3-month high and low, used as support and resistance
- **Scoring:** three pillars (trend, momentum, stability). Each check calls `Pillar.add(points, max_points, title, detail)`; pillar score = `50 + 50 × points / max_points`, clamped to 0–100 (`Pillar.score`).
- **What the LLM may do:** nothing in this agent. The master brief may describe these findings but cannot change them.
- **Not computed** (despite v1 marketing copy): ADX, Bollinger bands, volume indicators, chart patterns.

### 3.2 Fundamental agent

**VERIFIED IN CODE**: `research_engine.py`, `_statements()` and `analyse_fundamentals()`; formatting in `backend/agents/fundamental_agent.py`, `analyze()`.

- **Data source:** yfinance `income_stmt`, `balance_sheet`, `cashflow`, `quarterly_income_stmt` (annual and quarterly statements). Market cap, sector and currency come from `stock_service.get_stock_data()`.
- **Metrics:** revenue growth (1 year and 3-year CAGR), EPS growth, latest-quarter revenue growth year on year, operating margin and its change, net margin, return on average equity, free-cash-flow conversion, P/E (trailing four quarters of EPS when available, else annual EPS), PEG, free-cash-flow yield, price/sales, EV/EBITDA, net debt / EBITDA, interest cover, current ratio, share-count change.
- **Scoring:** four pillars (profitability, growth, valuation, balance sheet) using fixed bands through `_band()`, for example operating margin ≥25% = +2, ≥12% = +1, ≥5% = 0, ≥0% = −1, else −2. Fundamental score = profitability 0.30, growth 0.30, valuation 0.25, balance 0.15.
- **Labels:** the agent reports Strong (≥62), Average, or Weak (≤40).
- **Missing data:**
  - No income statement → agent returns `"fundamental": "Unavailable"`, `data_available: false`, score `None`; the composite is re-weighted without it. **VERIFIED IN CODE.**
  - Banks and lenders (sector contains "financial") → balance-sheet pillar not scored, operating-margin test skipped. **VERIFIED IN CODE.**
  - Price currency differs from reporting currency → valuation not scored. **PARTIAL:** only works when yfinance reports `financialCurrency`.
  - New listings: fewer than 30 daily closes raises `ValueError` in `build()`, which the route turns into an HTTP 500 for the whole report. **PARTIAL:** no graceful partial report for very new listings. Base rates need about 323 trading days and are simply omitted before that.
  - Indian tickers: a bare symbol gets `.NS` appended only if it is in a hard-coded list of 13 names (`stock_service.resolve_symbol()`, `INDIAN_TICKERS`). **PARTIAL:** any other Indian stock must be typed with `.NS` or `.BO`.
- **Valuation is judged on absolute thresholds, not against sector peers. PARTIAL;** the report says so in the pillar note.

### 3.3 Sentiment agent

**VERIFIED IN CODE**: news in `backend/services/news_service.py`, `get_news()`; agent in `backend/agents/sentiment_agent.py`, `analyze()`; pillar in `research_engine._news_pillar()`.

- **Sources:** yfinance `Ticker.news` (`_from_yahoo()`), and Google News RSS searched by company name over the last 14 days with US or India locale (`fetch_rss_news()`).
- **Filtering:** `NOISE` regex removes filing notices, price pages and "stocks to watch" lists; a headline must contain the company name or ticker (`_relevant_terms()`); duplicates removed; older than 30 days dropped; at most 10 kept.
- **Tone:** rule-based lexicon of phrases and words (`tag_sentiment()`). Tested: "HSBC downgrades Nvidia" and "(Rating Downgrade)" now read negative; "Burry says 'get out' of Nvidia" still reads neutral.
- **Agent:** counts positive, negative and neutral headlines, tags event types by keyword (earnings, analyst rating, legal, deal, product, management, capital return), and sets confidence = `min(90, 35 + 3 × min(count, 10) + 35 × |net lean|)`.
- **"Token reduction to ~1,600": does not apply to this agent.** It makes no LLM call, so it uses zero tokens. The 1,600 figure is the output cap on the single master call (section 2.3).
- **Rule-based fallback:** not needed; the agent is entirely rule-based. With no headlines it says so and the news pillar is left out of the composite. **VERIFIED IN CODE.**
- **Mock news:** only when `ALLOW_MOCK_DATA=true`, and labelled "Mock News Engine" (`get_mock_news()`). Off in production.

---

## 4. Consensus engine

**VERIFIED IN CODE**: `research_engine.build()` and `_weighted()`; text in `master_agent.analyze()`.

### 4.1 Formula

```
technical   = 0.65 × trend + 0.35 × momentum
fundamental = 0.30 × profitability + 0.30 × growth + 0.25 × valuation + 0.15 × balance
composite   = 0.40 × technical + 0.45 × fundamental + 0.15 × news
```

- Each line is a weighted mean of the parts that exist; missing parts are dropped and the remaining weights re-normalised (`_weighted()`).
- The stability pillar is not in the composite. It drives risk instead:
  `risk_points = 0.7 × (100 − stability) + 0.3 × (100 − balance)` → High ≥60, Medium ≥40, else Low.

### 4.2 Bands and labels

| Composite | Bias label | Shown to user |
| :-- | :-- | :-- |
| ≥ 60 | Bullish | "Leans positive" |
| 41–59 | Neutral | "Mixed" |
| ≤ 40 | Bearish | "Leans negative" |

Pillar verdicts: ≥75 Strong, ≥60 Good, ≥40 Mixed, ≥25 Soft, else Weak (valuation and stability use their own words, such as Cheap…Expensive).

### 4.3 Confidence, disagreement, missing agents

```
confidence = min(92, 30 + 30 × coverage + 20 × agreement + 20 × conviction)
coverage   = scored pillars / 8
agreement  = max(0, 1 − std_dev(pillar scores excluding stability) / 30)
conviction = min(1, |composite − 50| / 25)
```

- **Disagreement lowers confidence: VERIFIED IN CODE,** but at **pillar** level (spread of the seven pillar scores), not as an explicit agent-versus-agent vote. There is no rule such as "technical bullish and fundamental bearish → flag conflict".
- **Missing or failed part: VERIFIED IN CODE.** Weights re-normalise, coverage lowers confidence, the agent reports "Unavailable", and the response carries `insight.coverage` (`prices`, `financials`, `headlines`, `benchmark`, `earnings_date`). The UI shows coverage in the method note.
- **Exception:** if price history itself fails (fewer than 30 closes), the whole request fails with HTTP 500. There is no partial report without prices.
- **Calibration: NOT IMPLEMENTED.** Confidence is a hand-set heuristic; it has never been tested against outcomes. Weights and thresholds are judgement, not fitted. The historical base rates are descriptive statistics shown to the user; they do not adjust the score.

---

## 5. Robustness

### 5.1 LLM output validation

| Check | Status | Where |
| :-- | :-- | :-- |
| JSON mode requested from Groq | VERIFIED IN CODE | `query_groq()`, `response_format: json_object` |
| Markdown fences stripped, outer `{...}` extracted | VERIFIED IN CODE | `clean_json_text()` |
| Parse with `json.loads`, fall back to rules on failure | VERIFIED IN CODE | `master_agent.analyze()` |
| Advice wording blocked | VERIFIED IN CODE | `ADVICE_PATTERN` |
| Numbers not in the evidence blocked (more than 2 → reject) | VERIFIED IN CODE | `_unsupported_numbers()`, ±1% or ±0.6 tolerance; numbers ≤12 and 14/50/52/100/200 ignored |
| Per-field type check before use | PARTIAL | `isinstance(value, type(view[field]))`; checks list vs string only |
| Pydantic schema for the LLM output | NOT IMPLEMENTED | `risk_register` items, severity values and list lengths are not validated |
| Retry with a corrective prompt | NOT IMPLEMENTED | |
| Pydantic on the API response | VERIFIED IN CODE | `AnalyzeResponse` in `backend/models/schemas.py`; `insight` and `access` are untyped `Dict[str, Any]` |

### 5.2 Concurrency

- **Agent calls are not concurrent, and do not need to be.** The three agents run one after another in `routes.analyze_stock()`, but they are pure Python over already-fetched data and take milliseconds.
- **Data fetches are parallel: VERIFIED IN CODE.** `research_engine.build()` runs four yfinance fetches (5-year history, benchmark history, statements, calendar) in a `ThreadPoolExecutor(max_workers=4)`. The quote and news fetches before it are sequential.
- **The endpoint blocks the event loop. Known problem.** `analyze_stock` is `async def` but calls synchronous yfinance, `httpx.Client` (sync) and `ThreadPoolExecutor.result()` directly. No `asyncio.gather`, no `run_in_threadpool`, no async HTTP client. With one uvicorn worker (`main.py`, no `workers` setting), one slow report stalls every other request on that server for 5–10 seconds.
- **Fix (not done):** make the handler `def` (FastAPI then runs it in a thread pool), or wrap the pipeline in `run_in_threadpool`, and switch to `httpx.AsyncClient`.

### 5.3 Cache

**VERIFIED IN CODE**: `backend/services/cache_service.py`.

- Plain Python dict in process memory: `{symbol: {"data": ..., "timestamp": ...}}`.
- **Key:** the resolved symbol, for example `RELIANCE.NS`. Not keyed by plan; plan locks are applied after the cache read (`billing_service.apply_entitlements()`), so one cached report serves all plans correctly.
- **TTL:** 900 seconds by default, env `CACHE_TTL_SECONDS` (v1 was 60 seconds).
- **Tiered TTLs: NOT IMPLEMENTED.** One TTL for everything.
- **Locking: NOT IMPLEMENTED in the cache.** There is no lock. It is safe today only because the handler runs on the single event-loop thread (see 5.2). If the handler is moved to a thread pool, the check-then-delete in `get_from_cache()` can race. Two simultaneous requests for the same uncached stock both compute it (no request coalescing).
- The quota store in `billing_service.py` **does** use `threading.Lock()` (`_usage_lock`).
- **Multiple instances:** each instance has its own cache and quota counts, and both are lost on restart. A shared store (Redis or Postgres) is needed before scaling out.

---

## 6. LLMOps

| Item | Status | Detail |
| :-- | :-- | :-- |
| Prompt storage | PARTIAL | One prompt, an f-string inside `master_agent.analyze()`. Versioned only by git history |
| Prompt version IDs (v2, v2.1) | NOT IMPLEMENTED | No version constant; nothing logged per report |
| Model used per report | PARTIAL | Logged as `Groq query succeeded using model: …` (`query_groq()`); not returned in the API response |
| Token and usage tracking | NOT IMPLEMENTED | Groq returns `usage`; the code ignores it. Token figures in this report come from an external benchmark script |
| Request ID across agents | NOT IMPLEMENTED | No correlation ID; logs are joined by symbol and timestamp only |
| Structured logs | PARTIAL | Python `logging` to stdout and a rotating file (`routes.py`), plain text, not JSON |
| Quality evaluation | NOT IMPLEMENTED | No eval set, no grading of briefs, no backtest of scores |
| Automated tests | NOT IMPLEMENTED | No pytest or unittest files. `backend/test_verification.py` is a manual script and is **broken in v2**: it calls the v1 agent signatures and fails with `KeyError: 'price'` |
| Guardrails on output | VERIFIED IN CODE | Advice regex and number check (section 5.1) |

---

## 7. Stack truth check

| Technology | Used? | Evidence |
| :-- | :-- | :-- |
| FastAPI + Uvicorn | Yes | `backend/main.py`, `backend/api/routes.py` |
| Pydantic | Yes | `backend/models/schemas.py` (request and response models) |
| yfinance, pandas, NumPy | Yes | `stock_service.py`, `research_engine.py` |
| httpx | Yes | Groq calls and Google News RSS |
| Groq API (gpt-oss-120b, gpt-oss-20b, qwen3.8-27b) | Yes | `llm_service.py` |
| React 19 + Vite 8 | Yes | `frontend/package.json` |
| Recharts | Yes | `ResearchReport.jsx`: `ComposedChart` (price area + 50/200-day lines), `BarChart` (revenue and profit) |
| lucide-react, axios | Yes | icons; API client |
| Tailwind CSS | PARTIAL | Installed and configured; the new screens use plain CSS (`quantum-app.css`), Tailwind remains in old unused components |
| framer-motion | PARTIAL | Dependency; not used by the new screens |
| n8n | **No** | Not anywhere in the code |
| LangChain | **No** | Not anywhere in the code; agents are plain Python modules |
| Flask | **No** | Backend is FastAPI |
| Next.js | **No** | Frontend is a Vite single-page app with hash routing |
| Docker | **No** | `backend/Dockerfile`, `frontend/Dockerfile` and `docker-compose.yml` exist but are empty (0 bytes) |
| OpenRouter | **No** (dead code) | `base_agent.py` has a client; nothing imports it |
| Gemini / google-generativeai | **No** | In `requirements.txt` and checked by `/api/health`, never called |

**Frontend changes.** VERIFIED IN CODE: `frontend/src/App.jsx`, `HomePage.jsx`, `ResearchReport.jsx`, `PricingPage.jsx`, `styles/quantum-app.css`.
- Hash router (`#/`, `#/pricing`, `#/s/AAPL`) gives shareable report links and a working back button.
- Report: score ring, price chart with 3M/6M/1Y ranges, clickable pillar tiles that filter the evidence, 52-week range bar, revenue and profit bars, locked previews for paid sections.
- Fixed from v1: browser-side invented numbers removed (scenario probabilities, FII/DII bars, hashed news "impact scores", hard-coded "recent activity", sector guessed from ticker). The new report shows only fields the backend returns.
- Layout tested at 375 px width with no horizontal scroll; `vite build` passes.

---

## 8. Deployment

| Part | Where | Status |
| :-- | :-- | :-- |
| Backend | Render web service `quantum-financial-agent.onrender.com`, auto-deploys from `main` of `vedant7115/Quantum-Financial-Agent` | VERIFIED: `/` reports version 2.0.0 (checked 2026-11-17) |
| Frontend | Vercel project `quantum-financial-agent`, production deploys from `main` | VERIFIED: v2 commit deployed, report page rendered with no console errors |
| Live report | Reliance and Apple returned full data coverage (prices, financials, benchmark, earnings date) and an AI-written brief | VERIFIED 2026-11-17: Reliance 7.2 s, Apple 4.8 s |

**Environment variables read by the code:**

| Variable | Purpose | Default |
| :-- | :-- | :-- |
| `GROQ_API_KEY` | Groq access | none; without it every brief is rule-written |
| `GROQ_MODEL` | First model in the chain | `openai/gpt-oss-120b` |
| `GROQ_MAX_OUTPUT_TOKENS` | Output cap per brief | 1600 |
| `CACHE_TTL_SECONDS` | Report cache | 900 |
| `ACCESS_KEY_SECRET` | Signs plan keys | none; paid keys cannot be issued or verified without it |
| `ADMIN_TOKEN` | Protects `/api/clear-cache` | none; endpoint returns 403 |
| `ALLOWED_ORIGINS` | CORS | `*` |
| `ALLOW_MOCK_DATA` | Mock data for offline development | false |
| `DEMO_MODE` | Serve `config/demo_reports.json` | false |
| `LOG_FILE` | Log file path | `quantum_system.log` |
| `VITE_API_URL` | Frontend → backend URL | `http://localhost:8000/api` |
| `VITE_UPGRADE_URL` | Frontend upgrade link | none |

**Changed in deployment:** `render.yaml` now sets `GROQ_MODEL=openai/gpt-oss-120b` (was 20b). I have not confirmed whether Render actually reads `render.yaml` for this service or uses its dashboard settings.

**Untested or broken in production:**
- Fallback chain under real load on Render (tested locally only).
- Behaviour after a Render cold start beyond the two reports above.
- Whether `ACCESS_KEY_SECRET` and `ADMIN_TOKEN` are set on Render (not checked).

---

## 9. Known gaps (do not claim these)

1. No user accounts, no database, no payments. Paid keys are issued by hand with `scripts/issue_access_key.py`.
2. Quotas, rate limits and cache live in memory: reset on restart, wrong with more than one instance.
3. The analyze endpoint blocks the event loop (section 5.2).
4. No retries or backoff; worst-case LLM wait (~75 s) exceeds the frontend timeout (45 s).
5. No token tracking, prompt versioning, request IDs, evaluation or automated tests. The one test script is broken.
6. Confidence and weights are not calibrated or backtested.
7. Valuation uses absolute thresholds, not sector-relative ones.
8. Sentiment is a keyword lexicon; it still misses some headlines ("get out of Nvidia").
9. Indian auto-resolution covers only 13 hard-coded tickers.
10. Very new listings (fewer than 30 trading days) fail with HTTP 500.
11. The rate limiter and quota trust the first `X-Forwarded-For` value, which a client can set; quotas can be bypassed by changing it.
12. `/docs` is public and CORS is `*`.
13. Data is from Yahoo Finance via yfinance, which is unofficial and not licensed for commercial use. News fetches sometimes get HTTP 429 from Google or fail from Yahoo.
14. `stock_service.get_stock_data()` still formats market cap with `$` for Indian stocks (seen in the test script output: "INFY Market Cap: $4.44T"). The new report uses the engine's correctly formatted value, but the raw field is wrong.
15. Dead code still in the repo: old frontend screens (`InstitutionalReport.jsx` 88 KB, `LandingPage.jsx` 56 KB, others), `base_agent.py`, empty Dockerfiles, unused `google-generativeai`.
16. Vercel's Hobby plan does not allow commercial use; the frontend must move before charging.
17. Selling research on Indian listed securities may require SEBI research-analyst registration; not resolved.

---

## 10. Resume-ready lines

Each line is supported by the code; numbers are from the code or the measured benchmark in section 2.4.

- Rebuilt the analysis core of a FastAPI stock-research service as a deterministic scoring engine: 8 pillars and up to 28 rule-based checks over 5 years of prices, a market benchmark and reported financial statements, with every finding citing the figure it rests on.
- Restricted the LLM (Groq gpt-oss-120b) to explaining pre-computed evidence, and added output guardrails that discard a brief containing advice wording or more than two numbers absent from the evidence, falling back to a rule-written brief.
- Built a three-model fallback chain (gpt-oss-120b → gpt-oss-20b → qwen3.8-27b) sized to Groq's 8,000 tokens-per-minute free tier; a nine-request burst test returned an AI brief for all nine.
- Cut LLM usage by 72–76% (about 8,400 to 2,000–2,350 tokens per report, measured) against the multi-call agent configuration by moving sub-agents to rule-based scoring, capping output at 1,600 tokens and lowering reasoning effort.
- Fixed production data failures: fundamentals now come from reported statements instead of a source that failed on Render, non-existent tickers return 400 instead of random data, and catalyst dates come from the exchange calendar instead of the model.
- Shipped v2.0.0 to Render and Vercel with Free / ₹149 / ₹499 plans enforced server-side (daily quotas, HMAC-signed access keys) and a redesigned React 19 + Recharts report with shareable URLs.

**Do not write:** "multi-agent LLM system", "LangChain", "async/concurrent agents", "Docker", "calibrated confidence", "backtested", "Redis", "production-grade observability", or any latency improvement over v1's default setting.

---

## 11. Interview prep

**1. You call it multi-agent. Are the agents actually agents?**
Not in the autonomous sense. In v2 they are deterministic modules: each reads the evidence engine's output for its domain and formats it. Only the master step calls an LLM, once, to write the explanation. In v1 the model could overwrite the calculated bias and confidence and it invented catalyst dates; in v2 the numbers are fixed before the model sees them, so the scores are reproducible.

**2. Why should anyone trust the scores?**
Every score is a sum of fixed checks, each with a stated threshold and the figure it used (`Pillar.add()` in `research_engine.py`). Same inputs give the same score. What I cannot claim is that the weights are optimal: they are judgement, not fitted or backtested.

**3. How do you stop the LLM from hallucinating?**
Three layers in `master_agent.py`: the prompt contains only the calculated evidence and forbids outside facts; the output is rejected if it contains advice wording (`ADVICE_PATTERN`); and it is rejected if more than two numbers in it are not in the evidence (`_unsupported_numbers()`). A rejected brief is replaced by a rule-written one, so the user always gets a report. The check catches invented numbers, not invented qualitative claims.

**4. Walk me through what happens when Groq rate-limits you.**
`query_groq()` catches the 429 and immediately tries the next model: gpt-oss-120b, then gpt-oss-20b, then qwen3.8-27b, each with its own per-minute allowance. If all fail, the rule-written brief is used. There is no retry or backoff, and I do not read the rate-limit headers, so it is reactive. In a local burst test of nine reports with no pause, all nine got an AI brief through the chain.

**5. Is your FastAPI endpoint actually asynchronous?**
No, and that is the main technical debt. It is declared `async def` but calls blocking yfinance and a sync httpx client, so with one worker a 5–10 second report blocks other requests. The fix is to declare it `def` so FastAPI uses its thread pool, or use `run_in_threadpool` and `httpx.AsyncClient`. Inside the pipeline, the four slow data fetches do run in parallel threads.

**6. How does the consensus handle missing data?**
`_weighted()` drops any part with no score and re-normalises the remaining weights. Confidence has a coverage term (scored pillars out of eight), so partial data lowers it, and the response includes a `coverage` object. One gap: if price history fails entirely the request returns 500 rather than a partial report.

**7. How is confidence calculated, and is it calibrated?**
`30 + 30 × coverage + 20 × agreement + 20 × conviction`, capped at 92, where agreement falls as pillar scores spread apart and conviction rises as the composite moves away from 50. It is not calibrated: I have not checked that "80% confidence" reports are right more often than "60%" ones. That would need stored predictions and outcomes.

**8. Your cache is a dict. Is it thread-safe? What happens with two servers?**
There is no lock. It is safe today only because the handler runs on the single event-loop thread. If I move the handler to a thread pool I need a lock or a proper store. With two instances each has its own cache and quota counts, and both reset on restart; the answer is Redis or Postgres.

**9. How did you cut token use, and what does a report cost?**
By default v1 already made one call (sub-agent calls were behind a flag); with the flag on it made four. I removed the sub-agent LLM code entirely, set `reasoning_effort` to low and capped output at 1,600 tokens. Measured: about 8,400 tokens per report with v1's four calls, about 2,000–2,350 in v2. Against v1's default single call, v2 uses about the same; the gain there is that the output is checked and cannot change the scores. At Groq's free tier the cost is zero but capacity is about 9–10 fresh reports a minute; repeat views are served from a 15-minute cache.

**10. What would you do next?**
In order: make the endpoint non-blocking; move quotas and cache to Postgres or Redis with user accounts; log tokens, model and a prompt version with a request ID for every report; add pytest coverage for the engine's checks and a small evaluation set for the brief; and store each report's score so confidence can be calibrated against what the stock actually did.
