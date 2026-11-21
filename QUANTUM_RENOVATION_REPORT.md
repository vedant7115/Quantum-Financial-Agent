# QUANTUM Renovation Report (v2.1.0)

Updated 2026-11-20. **Deployed:** v2.1.0 is merged into `main` (tag `v2.1.0`) and live on Render (backend) and Vercel (frontend), checked live on 2026-11-20 (section 3b).

- **v1:** commit `9b4a208`, before the renovation.
- **v2.0:** tag `v2.0.0`.
- **v2.1:** tag `v2.1.0`.

**Pending fix (v2.1.1, branch `fix/company-name-news`, not deployed yet):** company names and news on Render, section 3c and gap 13.

The interview study pack is in `INTERVIEW_STUDY_v2.1.md`; the plan for what comes next is in `FUTURE_PLAN.md`.

Every item carries one label:

- **VERIFIED IN CODE**: in the code, with file and function cited, and exercised by a test or a live run.
- **PARTIAL**: present but limited; the limit is stated.
- **NOT IMPLEMENTED**: not in the code. Do not claim it.

Measured numbers come from section 3: **3a is local** (one Windows laptop against live Yahoo and Groq) and **3b is live** (the deployed Render service, called from the internet). All runs were on 2026-11-20 with a few stocks each, so quote them as approximate.

---

## 1. Summary

| | v1 | v2.0 | v2.1 |
| :-- | :-- | :-- | :-- |
| Scores | Weighted rules, but the model could overwrite bias, confidence and risk | Fixed rules; the model only explains | Same rules, unchanged |
| Request handling | `async def` with blocking calls | Same | Async I/O, thread pool for yfinance, agents fan out with `asyncio.gather` |
| LLM calls per report | 1 by default, 4 with a flag | 1 | 1, plus 1 corrective retry if the answer is rejected |
| LLM failure handling | Try the next model | Try the next model | Per-model retry with Retry-After, rate-limit-aware skipping and recovery, 30 s deadline |
| Output checks | None | Advice regex, number check | Pydantic schema, advice regex, number check, one retry |
| Observability | Plain logs | Plain logs | JSON logs with request_id; per-call tokens and latency; traces; `/api/admin/usage` and `/api/admin/traces` |
| Prompt | Inline f-string | Inline f-string | Versioned files with registry and changelog |
| Cache | Dict, 60 s, no lock | Dict, 900 s, no lock | Four tiers, lock, coalescing, counters |
| Tests | None | None | 25 offline pytest tests, run by GitHub Actions on every push and pull request |

- **v1 → v2.0:** rebuilt the analysis as a deterministic evidence engine and redesigned the app. Real fundamentals; no invented tickers, headlines or dates; Free / ₹149 / ₹499 plans.
- **v2.0 → v2.1:** operations work only. Async fan-out, tracing, prompt versioning, usage observability, validated output, retries with a deadline, tiered cache, a conflict flag, ticker resolution, and dead-code removal. Scoring formulas, weights and thresholds are unchanged; the response only gains fields.

---

## 2. The seven target claims

| Claim | Status | Where |
| :-- | :-- | :-- |
| Prompt versioning | VERIFIED IN CODE | `backend/prompts/__init__.py` (`PROMPT_VERSIONS`, `active_version`, `render`), templates `brief_v2_0.txt` / `brief_v2_1.txt`, `prompts/CHANGELOG.md`; env `PROMPT_VERSION`; returned as `llm.prompt_version` and `trace.prompt_version`; on every JSON log line via `core/logging_setup.JsonFormatter`. Test: `test_prompt_registry_versions_and_env_override` |
| Token-usage observability | VERIFIED IN CODE, in memory only | `services/llm_service._log_call` logs model, status, prompt/completion/total tokens, latency and fallback step per call; `services/usage_service` keeps daily totals; `GET /api/admin/usage`; `llm.tokens` in the response. Test: `test_token_usage_is_logged_and_aggregated` |
| Cross-agent tracing | VERIFIED IN CODE, in process only | `core/context.py` (`Trace`, `span`, `TraceStore`, contextvars); spans for validate, quote, each agent, consensus, brief and each LLM attempt; returned as `trace`; last 200 at `GET /api/admin/traces`. Test: `test_agents_fan_out_concurrently_and_trace_is_returned`. No OpenTelemetry, no external tracing backend |
| Thread-safe TTL caching | VERIFIED IN CODE | `services/cache_service.TieredCache` (one `threading.Lock`, per-tier TTL, `get_or_compute` coalescing). Tests: `test_lock_survives_concurrent_threads`, `test_identical_concurrent_requests_compute_once`, and the API test where three identical requests computed once |
| Concurrent agent fan-out | VERIFIED IN CODE | `services/pipeline.build_report` runs `asyncio.gather(*(run_agent(a, …) for a in AGENTS))`; `agents/base.py` defines `Agent.run(evidence, ctx) -> AgentResult`. Test: all three agent spans overlap. Live trace: three agents started at the same millisecond |
| Model fallback with automatic recovery | VERIFIED IN CODE | `services/llm_service.generate` and `RateLimitTracker` (cooldown after 429, skip when near the token limit, used again once the window resets). Tests: `test_429_retries_once_with_capped_wait_then_falls_back`, `test_rate_limited_model_is_skipped_then_recovers`, `test_model_near_its_token_limit_is_skipped` |
| Output guardrails | VERIFIED IN CODE | `agents/master_agent.check_brief` (Pydantic `Brief`, `ADVICE_PATTERN`, `_unsupported_numbers`), retry loop in `analyze`. Tests: `test_check_brief_accepts_valid_and_rejects_bad_output`, `test_guardrails_reject_advice_and_invented_numbers_then_fall_back`, `test_retry_once_then_fall_back_to_rules` |

---

## 3. Measured benchmark

### 3a. Local: v2.0 against v2.1

**Method.**
- Each version was run in its own process through FastAPI's ASGI transport, against live Yahoo and Groq, with an empty cache and `GROQ_MODEL=openai/gpt-oss-120b`.
- v2.0 ran from a checkout of tag `v2.0.0`; v2.1 from this branch.
- Phase 1: AAPL, RELIANCE and TSLA one after another.
- Phase 2: 65 seconds later, MSFT, INFY and NVDA sent at the same time.
- Groq calls were counted by wrapping `httpx` and reading the `usage` field.
- The script is not in the repo.

| | v2.0.0 | v2.1.0 |
| :-- | :-- | :-- |
| One request at a time: time per report | 7.1 – 9.7 s | 7.3 – 11.1 s (the 11.1 s was the first, cold request) |
| One request at a time: tokens per report | 2,025 – 2,170 | 2,136 – 2,171 |
| LLM calls per report | 1 | 1 (no retries were needed) |
| **Three concurrent requests: total wall time** | **23.0 s** (7.3 + 8.2 + 7.4: they ran one after another) | **10.2 s** (they overlapped) |
| Three concurrent requests: total tokens | 6,511 over 3 calls | 6,450 over 3 calls |
| Model used | gpt-oss-120b for all | gpt-oss-120b for all; no fallback was triggered |

What this shows:

- **Concurrent requests:** v2.1 served three at once in 10.2 s against 23.0 s for v2.0, about 2.25× faster, because v2.0's handler blocked the event loop.
- **A single report is not faster.** Time is dominated by the Groq call (about 2–3 s) and the data fetch, and the work is the same. Do not claim a single-report speed-up.
- **Tokens are unchanged** at about 2,000–2,200 per report. The prompt was moved, not shortened.
- **Fan-out inside one report** shows in the traces rather than the totals. In a live run (2026-11-20), Infosys's three agents took 2.6 s, 2.2 s and 3.0 s and ran in parallel, so the step took 3.0 s instead of about 7.8 s one after another.
- **Measurement note:** in the concurrent phase, the per-request token figures in the raw script output overlap, because the requests shared one call list. The totals above are the real ones.

Earlier measurements for context: v1 with all four LLM calls used 8,368–8,394 tokens per report (2026-11-20).

**Release check (local, v2.1.0 from `main` before the push, real Uvicorn server, `GROQ_MODEL=openai/gpt-oss-120b`):**

| Request | Result | Time | Model | Tokens (prompt / completion / total) |
| :-- | :-- | :-- | :-- | :-- |
| MSFT | 200, AI brief | 6.6 s | gpt-oss-120b | 1,366 / 1,011 / 2,377 |
| HDFCBANK (typed without suffix) | 200, resolved to HDFCBANK.NS, AI brief | 4.3 s | gpt-oss-120b | 1,269 / 739 / 2,008 |
| ZZQXQ (invalid) | 400 `INVALID_TICKER` | 2.1 s | – | – |
| NVDA, ITC, KO at the same time | all 200, AI briefs | **7.1 s wall time** | gpt-oss-120b | 1,893 / 1,989 / 2,241 |
| JPM twice at the same time | both 200; second is `coalesced` | 4.2 s | gpt-oss-20b (120b was skipped: 68 tokens left in its minute) | 1,656 |

Report-cache counter `coalesced` went from 0 to 1, so the two JPM requests computed once. The 20b fallback on JPM is the rate-limit skip working as designed: five 120b calls inside one minute had used its 8,000-token allowance.

### 3b. Live: the deployed service (Render, 2026-11-20)

Called from a laptop over the internet against `quantum-financial-agent.onrender.com`, Render's single instance, empty cache.

| Request | Result | Time | Model | Tokens (prompt / completion / total) |
| :-- | :-- | :-- | :-- | :-- |
| AAPL | 200, AI brief | 7.9 s | gpt-oss-120b, prompt v2.1 | 1,280 / 760 / 2,040 |
| RELIANCE (typed without suffix) | 200, resolved to RELIANCE.NS, AI brief | 5.1 s | gpt-oss-120b, prompt v2.1 | 1,326 / 620 / 1,946 |
| MSFT, TCS, KO at the same time | all 200, AI briefs | **11.6 s wall time** (single reports 10.7–11.6 s) | gpt-oss-120b | 2,223 / 1,945 / 2,181 |
| JPM twice at the same time | both 200; second is `coalesced` | 6.5 s | gpt-oss-120b | 1,752 |

- **Trace spans on every fresh report:** `validate`, `quote`, `report`, `agent.technical`, `agent.fundamental`, `agent.sentiment`, `consensus`, `brief`, `llm.generate#1`. The coalesced request shows only `validate` and `report`, plus the builder's `generation_spans`.
- **No report fell back to the rule-written brief**, locally or live.
- **Admin endpoints live:** `/api/admin/traces` and `/api/admin/usage` return 403 with no token or a wrong token, and 200 with the right `x-admin-token`.
- **Access keys live:** with a valid Pro key `/api/usage` reports plan `pro`; without one, `free`.
- **Frontend live:** `quantum-financial-agent.vercel.app/#/s/AAPL` loads a full report with no console errors.
- **Found live (not caused by v2.1):** on Render, Yahoo does not return company names, so names fall back to "AAPL Corp."; because Google News is searched by name, AAPL got 0 headlines and "News flow: not assessed". The fallback (`stock_service.get_stock_data`, line 251) dates from June 2026. See gap 13. Fixed on branch `fix/company-name-news`, not yet deployed (section 3c).

### 3c. Company-name and news fix (v2.1.1, local, 2026-11-21, not deployed)

**Root cause (from the live AAPL report):** `sector` and `industry` null, no earnings date, name "AAPL Corp.", but market cap and financials present. So Yahoo's `quoteSummary` endpoint (`ticker.info`, crumb-authenticated) returns nothing for Render's cloud IP, while the chart, `fast_info` and statements endpoints work. Not a full rate limit, and not a missing field: an empty info dict. Yahoo's news endpoint was also failing during testing, locally too (yfinance reports "Yahoo Finance is currently down").

**Fix:** `services/company_names.resolve`: quote, then chart metadata, then Yahoo search, then a built-in map, then the plain ticker. Cached 24 h when found, 5 minutes when not. News searches by ticker (plus exchange for India) when the name is unknown, and adds Google News when fewer than four Yahoo headlines survive the filter.

| Ticker | Normal (local) | `ticker.info` empty (Render-like) | Also no chart name, search blocked | Headlines | News pillar |
| :-- | :-- | :-- | :-- | :-- | :-- |
| AAPL | Apple Inc. (`yahoo_quote`) | Apple Inc. (`yahoo_chart`) | Apple Inc. (`builtin`) | 10 | Mixed (40) |
| MSFT | Microsoft Corporation | same, `yahoo_chart` | same, `builtin` | 10 | Good (60) |
| KO | The Coca-Cola Company | same, `yahoo_chart` | same, `builtin` | 10 | Mixed (55) |
| RELIANCE → .NS | Reliance Industries Limited | same, `yahoo_chart` | same, `builtin` | 10 | Good (70) |
| TCS → .NS | Tata Consultancy Services Limited | same, `yahoo_chart` | same, `builtin` | 10 | Soft (35) |

Headline counts and pillars were the same in all three modes. Also checked: the search layer returns "Palantir Technologies Inc." for PLTR, and ticker-only news finds 10 headlines for "PLTR stock" and 7 for "IRFC NSE stock". The Render-like modes are simulated by patching yfinance locally; **not yet verified on Render**.

---

## 4. P0 items, one by one

### 4.1 Async correctness — VERIFIED IN CODE

- `api/routes.analyze_stock` is `async def`, and nothing inside it blocks the event loop:
  - Groq: `httpx.AsyncClient` in `llm_service.generate`.
  - Google News: `httpx.AsyncClient` in `news_service.fetch_rss_news_async`.
  - Yahoo news, quotes, prices, statements and the calendar: `asyncio.to_thread`.
  - Independent fetches use `asyncio.gather`: the stock history and benchmark history together, the statements and calendar together, Yahoo and Google News together, and the three agents together.
- `/api/stock/{symbol}` and `/api/price/{symbol}` also run their blocking calls in threads.
- **Thread pool:** `main.lifespan` sets a 32-thread default executor (`THREAD_POOL_SIZE`). Python's own default is sized from CPU count, which gives 5 threads on a 1-CPU instance.
- **Tests:**
  - `test_two_requests_do_not_serialize_and_identical_ones_compute_once`: two concurrent requests take less than 1.5× one request.
  - Section 3 measures the same thing against live data.
- **PARTIAL:** yfinance is synchronous, so concurrency comes from threads. A truly async data client does not exist for it.

### 4.2 Agent fan-out and tracing — VERIFIED IN CODE

- **Agent interface:** `agents/base.Agent.run(evidence: Evidence, ctx: AgentContext) -> AgentResult(name, status, score, data, error, duration_ms)`.
- **The three agents:**
  - `TechnicalAgent`: 5 years of prices and the benchmark → trend, momentum, stability.
  - `FundamentalAgent`: statements and calendar → profitability, growth, valuation, balance.
  - `SentimentAgent`: headlines → news pillar.
- Each fetches through the cache, computes in a thread, and runs concurrently with the others. `research_engine.build` was split into `price_part`, `fundamental_part` and `assemble` so each agent runs its own part; the formulas did not change.
- **Failure handling (`run_agent`):** never raises. An exception becomes `status="error"`, and an agent running longer than 15 s (`AGENT_TIMEOUT_SECONDS`) is abandoned. The consensus step re-weights without failed agents (`pipeline._consensus`). Only the technical agent is required: too few closes gives 422, any other failure gives 502. Test: `test_slow_agent_times_out_without_sinking_the_report`.
- **request_id:** `core/context.new_request_id()`, stored in a `ContextVar` and copied into every gather task and `to_thread` worker.
- **Trace:** spans of name, start/end ms, duration, status, error and attributes. They are returned as `trace`, logged as `type: span` JSON lines, and kept in a ring buffer of 200 (`TraceStore`) at `GET /api/admin/traces`, protected by `ADMIN_TOKEN` via the `x-admin-token` header.
- **PARTIAL:** traces are in memory and per process. There is no OpenTelemetry export.

### 4.3 Prompt versioning — VERIFIED IN CODE

- `backend/prompts/brief_v2_0.txt` is v2.0.0's prompt, extracted word for word. `brief_v2_1.txt` adds the "Mixed signals" instruction for conflicted reports.
- `PROMPT_VERSIONS` registry, `DEFAULT_PROMPT_VERSION = "v2.1"`, env `PROMPT_VERSION`. An unknown value falls back to the default with a warning.
- `prompts/CHANGELOG.md` records each version; published files are not edited.
- The version appears in `llm.prompt_version`, `meta.prompt_version`, `trace.prompt_version`, `/api/health`, `/api/admin/usage`, and every JSON log line.
- **PARTIAL:** nothing stops someone editing a published template in place. Versioning is a convention backed by the changelog.

### 4.4 Token and usage observability — VERIFIED IN CODE, in memory only

- **Per Groq call** (`llm_service._log_call`): model, fallback_step, attempt, HTTP status, latency_ms, prompt/completion/total tokens from Groq's `usage`, and error. It is logged as JSON with request_id and prompt_version, and added to `usage_service`.
- **Response:** `llm: {model, prompt_version, tokens: {prompt, completion, total}, latency_ms, fallback_used, fallback_step, outcome, attempts[], rejections[], deadline_exceeded}`.
- **`GET /api/admin/usage`:** per UTC day, the last 7 days:
  - per model: calls, ok, rate_limited, errors, skipped, tokens, average latency;
  - brief outcomes and fallback counts;
  - report counts: requests, generated, cache hits, coalesced, conflicted, errors;
  - cache hits, misses and hit rate per tier;
  - live rate-limit state and the model chain.
- **PARTIAL:** aggregates reset on restart and are per instance. There is no database, dashboard or alerting.

### 4.5 Validation — VERIFIED IN CODE

- **Pydantic `Brief`:** summary 80–3,000 characters; key_drivers 2–6; bull and bear 2–5 each; risk_register 1–6 items with `severity` and `probability` in `Low | Medium | High`. Unknown fields are ignored. Several points packed into one string are split before validation.
- **Guardrails kept:** `ADVICE_PATTERN` and more than two numbers absent from the evidence.
- **On failure:** one retry with the rejection reason appended; then the rule-written brief (`_rule_view`). Outcome is `ai`, `ai_after_retry` or `rule`.
- **NOT IMPLEMENTED:** the risk category is not limited to the five named categories, and the checks catch invented numbers, not invented qualitative claims.

### 4.6 Retries and time budget — VERIFIED IN CODE

- **Chain:** `GROQ_MODEL` (default `openai/gpt-oss-120b`) → `openai/gpt-oss-20b` → `qwen/qwen3.8-27b` → rule-written brief (`model_chain`).
- **Per model:** 429 and 5xx are retried once after `Retry-After` (capped at 3 s; 1 s if absent). Timeouts, network errors, other 4xx and malformed responses move to the next model at once.
- **Skipping:** a 429 starts a cooldown (Retry-After, or the token reset time, or 10 s). A model whose last `x-ratelimit-remaining-tokens` is below the estimated need (prompt characters ÷ 4 + 1,600) is skipped until its window resets. Both recover automatically.
- **Deadline:** `pipeline.build_report` sets `deadline_at = min(now + 30 s, request start + 42 s)` (`LLM_DEADLINE_SECONDS`, `REQUEST_BUDGET_SECONDS`). Every call's timeout is the smaller of 25 s and the time left. No call starts with less than 1 s left. The validation retry shares the same deadline.
- **Data phase:** each agent is capped at 15 s. Worst case is roughly quote (5 s session timeout) + agents (15 s) + LLM (deadline capped so the request stays under 42 s), which is under the frontend's 45 s.
- **PARTIAL:** the per-call timeout cannot interrupt a hung yfinance thread; the request moves on and the thread finishes in the background.

### 4.7 Cache — VERIFIED IN CODE

| Tier | Holds | TTL (env) |
| :-- | :-- | :-- |
| report | finished report per symbol | 300 s (`CACHE_TTL_SECONDS`, was 900 in v2.0) |
| price | quote, 5-year and benchmark history, ticker resolution | 300 s (`CACHE_TTL_PRICES`) |
| news | filtered headlines | 1,800 s (`CACHE_TTL_NEWS`) |
| fundamentals | statements, calendar | 86,400 s (`CACHE_TTL_FUNDAMENTALS`) |

- One `threading.Lock` guards entries, the in-flight table and counters.
- `get_or_compute` coalesces identical concurrent requests: the API test sent three identical requests and the quote was fetched once; responses report `meta.cache` as `miss`, `coalesced` or `hit`. A failure is passed to every waiter and not cached.
- Report and news values are deep-copied on read.
- Hit, miss and coalesced counters per tier are shown in `/api/admin/usage`.
- **PARTIAL:** in process memory, lost on restart, not shared between instances.

### 4.8 Conflict flag — VERIFIED IN CODE

- `research_engine.assess_conflict`: the two scores are on opposite sides of 50 (50 itself is neither side) **and more than 15 points apart** (`CONFLICT_MIN_GAP`). Confidence is then capped at 60.
- `insight.conflict = {label: "Mixed signals", technical_score, fundamental_score, gap, confidence_cap, note}` or `null`; `insight.conflicted` (bool) is kept.
- `insight.agent_scores = {technical, fundamental, sentiment: {score, status, error}}`.
- **"Mixed signals" in the brief:** prompt v2.1 asks for it, and `master_agent._mixed_signals` adds it if the model left it out, so it is guaranteed.
- **Live:** Infosys was flagged (technical 18, fundamental 77); Apple was not.
- **NOT IMPLEMENTED:** the frontend does not yet show the conflict badge or the per-agent scores; the data is in the response.

---

## 5. P1 items

| Item | Status | Detail |
| :-- | :-- | :-- |
| 9. Pytest suite with mocked Groq | VERIFIED IN CODE | 25 tests, about 6 s, fully offline: `tests/test_llm_chain.py` (429 chain, 5xx, skip and recovery, near-limit, deadline, all-fail, token logging, guardrails, prompt registry), `test_master_brief.py`, `test_research_engine.py`, `test_cache_service.py`, `test_api_pipeline.py` (fan-out, concurrency, coalescing, admin auth, ticker errors, agent timeout). Run by GitHub Actions (`.github/workflows/tests.yml`, Python 3.11, no secrets) on every push and pull request; first run passed |
| 9b. `test_verification.py` | VERIFIED IN CODE | Manual live script; runs the engine, the agent formatters and the async brief for AAPL and INFY; exits non-zero on failure |
| 10a. Partial report for new listings | NOT IMPLEMENTED | Fewer than 30 closes now returns a clear `422 INSUFFICIENT_HISTORY` with a frontend message instead of a 500. A report without price data would need frontend changes |
| 10b. Indian ticker lookup | VERIFIED IN CODE | `stock_service.resolve_and_validate`: tries the symbol as typed, then `.NS`, then `.BO`. Live: ASIANPAINT → ASIANPAINT.NS, MARUTI → MARUTI.NS. This is a fallback, not a search API |
| 10c. Market cap in the listing currency | VERIFIED IN CODE | `stock_service.format_market_cap`. Live: Asian Paints "₹2.50 lakh Cr" (was "$…") |
| 11. Dead code | VERIFIED IN CODE | Removed 17 unused frontend components, 2 unused stylesheets, `base_agent.py` (OpenRouter), empty Dockerfiles and `docker-compose.yml`, and `google-generativeai`. `vite build` passes |
| 11b. Working Dockerfile | NOT IMPLEMENTED | Deleted instead, as the brief allowed |
| 13. Company names and news on Render | VERIFIED IN CODE, local only (not deployed) | `services/company_names.py` (`resolve`, `from_quote`, `search_name`, `builtin_name`), `news_service._rss_query` and `select_articles`. Tests: `tests/test_company_names.py` (11). Section 3c |
| 12. Structured JSON logging | VERIFIED IN CODE | `core/logging_setup.py`: one JSON object per line with ts, level, logger, msg, request_id, prompt_version and event fields; `LOG_FORMAT=text` for local use |

---

## 6. Stack truth check

| Technology | Used? | Evidence |
| :-- | :-- | :-- |
| FastAPI, Uvicorn, Pydantic v2 | Yes | `main.py`, `api/routes.py`, `models/schemas.py`, `master_agent.Brief` |
| asyncio (gather, to_thread, contextvars) | Yes | `services/pipeline.py`, `agents/base.py`, `core/context.py` |
| httpx (async) | Yes | Groq and Google News |
| yfinance, pandas, NumPy | Yes | data and scoring |
| Groq: gpt-oss-120b, gpt-oss-20b, qwen3.8-27b | Yes | `llm_service.py` |
| pytest | Yes | `backend/tests`, `requirements-dev.txt` |
| GitHub Actions (CI) | Yes, tests only | `.github/workflows/tests.yml`; it runs tests, it does not deploy |
| React 19, Vite, Recharts | Yes | `frontend/` |
| n8n, LangChain, Flask, Next.js | **No** | Not in the code |
| Docker | **No** | Empty files removed |
| OpenRouter, Gemini | **No** | Removed |
| Redis, Postgres, OpenTelemetry, CD pipeline | **No** | Not in the code; deploys are Render's and Vercel's own auto-deploy from `main` |
| Razorpay or any payment gateway | **No** | Not in the code; paid keys are issued by hand |

---

## 7. Deployment

**Status: done on 2026-11-20.** `main` = merge of `feat/v2.1-ops` plus the changelog and CI commits, tagged `v2.1.0`; Render and Vercel auto-deployed it, and the live checks are in section 3b. Rollback: redeploy the previous Render deploy (v2.0.0) from the Render dashboard, or set `PROMPT_VERSION=v2.0` to roll back only the prompt.

### What was set or changed

**Render (backend web service):**

| Action | Why |
| :-- | :-- |
| Set `ADMIN_TOKEN` to a long random string | Without it, `/api/admin/traces`, `/api/admin/usage` and `/api/clear-cache` return 403 for everyone |
| Set `ENV=production` | `main.py` starts Uvicorn with `reload=True` unless `ENV=production`; the reloader should not run in production. This was already true in v2.0 |
| Set `GROQ_MODEL=openai/gpt-oss-120b` if it is not already | The repo's `render.yaml` says 120b, but the dashboard value wins if Render is not using the blueprint |
| Optional: `PROMPT_VERSION=v2.1` | Already the default; set it only to pin or roll back (`v2.0`) |
| Optional: `LOG_FORMAT=json` | Already the default |
| Optional: cache and timing overrides | `CACHE_TTL_SECONDS` (300), `CACHE_TTL_PRICES` (300), `CACHE_TTL_NEWS` (1800), `CACHE_TTL_FUNDAMENTALS` (86400), `LLM_DEADLINE_SECONDS` (30), `REQUEST_BUDGET_SECONDS` (42), `AGENT_TIMEOUT_SECONDS` (15), `THREAD_POOL_SIZE` (32) |
| Check | `GROQ_API_KEY` is still set |
| Set `ACCESS_KEY_SECRET` | Without it every visitor is on Free and no Plus/Pro key works (`billing_service.verify_access_key`). Set on 2026-11-20; a Pro key was verified live |
| No change | Build command (`pip install -r requirements.txt`) and start command (`python main.py`) stay the same; `requirements.txt` only lost `google-generativeai` |

**Vercel (frontend):**

| Action | Why |
| :-- | :-- |
| Nothing required | `VITE_API_URL` is unchanged. The only frontend changes are deleted unused files and one new error message |
| Note | The Hobby plan does not allow commercial use (unchanged from before) |

**Post-deploy checks (all passed live):** `GET /` reports `"version": "2.1.0"`; reports return `llm` and `trace`; `GET /api/admin/usage` and `/api/admin/traces` answer only with the `x-admin-token` header.

### Not verified

- Uvicorn's lifespan sets the thread pool; it runs under `python main.py`. FastAPI's `ASGITransport`, which the tests use, does not run lifespan, so the tests do not cover the pool size. The live concurrency run (3b) is the only evidence it works on Render.
- Behaviour under real traffic: the live runs were a handful of requests from one machine.

---

## 8. Known gaps (do not claim these)

1. **All state is in memory, per process:** cache, quotas, rate limits, usage aggregates, traces. Lost on restart; wrong with more than one instance. No Redis or Postgres.
2. **No user accounts, no payments.** Plan keys are issued by hand.
3. **CI runs tests only.** No automated deploy gate: Render and Vercel deploy from `main` whether or not the tests pass.
4. **No quality evaluation** of briefs, and no backtest or calibration of scores or confidence.
5. **No partial report** for listings with fewer than 30 closes (422 instead).
6. **Frontend gaps:** it does not show `insight.conflict`, `insight.agent_scores`, `llm` or `trace`.
7. **Brief guardrails:** they catch invented numbers and malformed output, not invented qualitative claims. The risk category is free text.
8. **Valuation** uses absolute thresholds, not sector peers. **Sentiment** is a keyword lexicon.
9. **Quota trust:** the rate limiter and quota trust the first `X-Forwarded-For` value, which a client can set.
10. **Open surface:** `/docs` is public and CORS is `*`.
11. **Data licensing:** data is from Yahoo via yfinance, which is not licensed for commercial use. Google News sometimes returns 429 and Yahoo news is sometimes down.
12. **Hosting and regulation:** Vercel Hobby does not allow commercial use, and SEBI research-analyst registration is not resolved.
13. **Company names on Render:** live v2.1.0 still shows "AAPL Corp." and few headlines, because `ticker.info` is empty from Render's IP. Fixed on branch `fix/company-name-news` (v2.1.1, section 3c) but **not deployed**; until it is live and checked, do not claim it is fixed in production.
14. **No evaluation set** for brief quality, **no calibration** of confidence, and **one Uvicorn worker** on one instance.

---

## 9. Safe resume lines

Every line below is VERIFIED IN CODE and backed by a test or a measured run.

- Built an async FastAPI research pipeline in which technical, fundamental and sentiment agents share one `Agent` interface and run concurrently with `asyncio.gather`, with blocking market-data calls moved to a thread pool; three concurrent requests completed in 10.2 s versus 23.0 s before (measured).
- Designed a deterministic scoring engine (8 pillars, up to 28 rule-based checks over 5 years of prices, a benchmark and reported financial statements) and restricted the LLM to explaining pre-computed evidence.
- Added LLM output guardrails: Pydantic schema validation, an investment-advice filter and an unsupported-number check, with one corrective retry and a rule-based fallback.
- Built a Groq model fallback chain (gpt-oss-120b → gpt-oss-20b → qwen3.8-27b) with per-model retry honoring Retry-After, rate-limit-aware skipping with automatic recovery, and a 30-second overall deadline.
- Added observability: per-request IDs propagated with contextvars, timed trace spans per agent and LLM call, JSON logs, per-call token and latency logging, and admin endpoints for daily usage and recent traces.
- Introduced versioned prompt templates with a registry and changelog, selectable by environment variable and recorded with every report.
- Implemented a thread-safe tiered TTL cache (prices, news, fundamentals, reports) with in-flight request coalescing, so identical concurrent requests compute once.
- Covered the engine, LLM chain, guardrails, cache and API concurrency with 25 offline pytest tests using a mocked Groq transport, run by GitHub Actions on every push and pull request.
- Deployed the FastAPI backend on Render and the React frontend on Vercel, and verified the release live: version endpoint, AI briefs from gpt-oss-120b, request coalescing and admin-endpoint authentication.

**Do not write:** LangChain, n8n, Docker, Redis, OpenTelemetry or "distributed tracing", "CI/CD" (it is CI for tests only), payments or Razorpay, "calibrated" or "backtested", "production-scale", "live users", or any user or revenue numbers.

---

## 10. Interview prep

A fuller pack (code reading guide, 30 questions, do-not-claim list, 2-minute walkthrough) is in `INTERVIEW_STUDY_v2.1.md`. The ten core answers:

**1. Are these real agents?**
They are concurrent workers behind one interface, not autonomous LLM agents. Each fetches its own data and computes its pillars deterministically. Only the brief step calls an LLM, and it cannot change the scores.

**2. How do you know the agents actually run in parallel?**
Each agent records a trace span with start and end times. A test asserts that all three start before any finishes, and in live traces they start at the same millisecond. Two concurrent requests also finish in about the time of one (section 3).

**3. The endpoint is async but yfinance is synchronous. How?**
yfinance calls run in `asyncio.to_thread`, and Groq and Google News use `httpx.AsyncClient`, so the event loop never blocks. I sized the thread pool explicitly, because Python's default is 5 threads on a 1-CPU machine and one report runs up to six fetches.

**4. What happens when Groq rate-limits you?**
The client retries that model once after `Retry-After` (capped at 3 s), then moves down the chain. It also reads `x-ratelimit-remaining-tokens` and skips a model that cannot fit the request, then uses it again once its window resets. Everything shares a 30-second deadline, and if nothing answers, a rule-written brief is used.

**5. How do you stop hallucination?**
The prompt holds only computed evidence. The answer must match a Pydantic schema, must not contain advice wording, and may not contain more than two numbers absent from the evidence. One retry, then the rule-written brief. It catches invented numbers, not every invented sentence.

**6. How does tracing work across concurrent tasks?**
The request ID and trace live in `contextvars`, which asyncio copies into every task and `to_thread` call. Spans recorded anywhere land on the right request's trace. Traces are returned in the response, logged as JSON, and the last 200 are kept for an admin endpoint. It is in-process, not OpenTelemetry.

**7. Is your cache thread-safe? What about duplicate work?**
One lock guards every read, write and counter. `get_or_compute` keeps an in-flight future per key, so concurrent identical requests await one computation; a test proves three identical requests fetch the quote once. It is per process, so multiple instances would need Redis.

**8. How do you version prompts?**
Each version is a template file in a registry with a changelog. `PROMPT_VERSION` selects it, and the version is returned with every report and written on every log line, so any brief can be traced to its prompt. Editing a published file is prevented only by convention.

**9. What do you measure about LLM usage?**
Per call: model, status, prompt and completion tokens, latency and fallback step. Per day: totals per model, brief outcomes, fallback counts and cache hit rates, at `/api/admin/usage`. It is in memory; the next step is persisting it.

**10. What would you do next?**
Fix company names on the hosted server; move cache, quotas, usage and traces to Redis or Postgres; connect payments so keys are issued automatically; build an evaluation set for briefs; show the conflict and per-agent scores in the UI; and store predictions so confidence can be calibrated.
