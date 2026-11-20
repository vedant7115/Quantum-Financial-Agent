# Quantum v2.1 — Interview Study Pack

For a technical interview at Capgemini. Everything here matches the code on `main` (tag `v2.1.0`). Paths are relative to `backend/`. Numbers come from `QUANTUM_RENOVATION_REPORT.md`, section 3.

**How to use this file:**
1. Open each file in part A next to this page and read the named function once.
2. Say each three-sentence explanation out loud until you can do it without looking.
3. Practise the 2-minute walkthrough (part D) until it takes under 2 minutes.
4. Read the "do not claim" list (part C) the night before.

---

## A. Code reading guide

### 1. Request flow
**Where:** `api/routes.py` → `analyze_stock`, then `services/pipeline.py` → `build_report`.

> A `POST /api/analyze` first checks the rate limit, the ticker format and the plan quota, then resolves the symbol (a bare Indian ticker falls back to `.NS`, then `.BO`). It asks the report cache for that symbol; on a miss `build_report` fetches the quote, runs the three agents at the same time, combines their results in the consensus step and asks the LLM to explain them. The route then adds per-request fields (request ID, trace, plan locks) and returns the JSON.

### 2. Agent interface and `asyncio.gather`
**Where:** `agents/base.py` → `Agent`, `TechnicalAgent`, `FundamentalAgent`, `SentimentAgent`, `run_agent`; called from `pipeline.build_report`.

> Every agent implements one method, `async run(evidence, ctx) -> AgentResult`, which holds a name, status, score, data and error. `build_report` runs all three with `asyncio.gather`, and `run_agent` wraps each one in a trace span and a 15-second timeout, so it never raises: a failure becomes `status="error"`. The agents fetch data and compute scores with fixed rules; none of them calls the LLM.

### 3. contextvars trace IDs
**Where:** `core/context.py` → `request_id_var`, `trace_var`, `new_request_id`, `Trace.span`, `span`, `TraceStore`.

> Each request gets a 12-character request ID and a `Trace` object stored in `ContextVar`s, which asyncio copies into every task created by `gather` and every `to_thread` worker. So any code, even deep inside an agent, can call `span("name")` and the timing lands on the right request's trace. Traces are returned in the response, logged as JSON lines, and the last 200 are kept in memory for `GET /api/admin/traces`.

### 4. Prompt registry
**Where:** `prompts/__init__.py` → `PROMPT_VERSIONS`, `active_version`, `render`; templates `prompts/brief_v2_0.txt`, `brief_v2_1.txt`; `prompts/CHANGELOG.md`.

> Prompts are text files, and a dictionary maps each version name to its file. The `PROMPT_VERSION` environment variable picks one, falling back to `v2.1` with a warning if the name is unknown. The version is returned with every report and written on every log line, so any brief can be traced back to the exact prompt that produced it, and rolling back is one setting.

### 5. Usage logging
**Where:** `services/llm_service.py` → `CallRecord`, `_log_call`; `services/usage_service.py` → `record_llm_call`, `record_brief`, `snapshot`; route `admin_usage`.

> After every Groq call, `_log_call` records the model, HTTP status, prompt and completion tokens from Groq's `usage` field, latency and fallback step, and writes it as a JSON log line. `usage_service` adds it to per-day totals per model, along with brief outcomes, fallback counts and cache hit rates. `GET /api/admin/usage` returns these, but they are kept in memory and reset when the server restarts.

### 6. Groq retry, skip and deadline logic
**Where:** `services/llm_service.py` → `generate`, `RateLimitTracker` (`update`, `cool_down`, `skip_reason`), `model_chain`; deadline set in `pipeline.build_report`.

> The chain is gpt-oss-120b, then gpt-oss-20b, then qwen3.8-27b, then a rule-written brief. A 429 or 5xx is retried once on the same model after `Retry-After` (capped at 3 s); a model is skipped while it cools down after a 429 or when Groq's `x-ratelimit-remaining-tokens` says this prompt won't fit, and it is used again once its window resets. Everything shares one deadline, the earlier of 30 s from now or 42 s from the request start, so the frontend's 45-second limit is never hit.

### 7. Cache tiers and coalescing
**Where:** `services/cache_service.py` → `TieredCache`, `get_or_compute`, `stats`.

> There are four tiers with different lifetimes: reports 5 minutes, prices 5 minutes, news 30 minutes, fundamentals 24 hours. One `threading.Lock` guards the entries, and `get_or_compute` keeps an in-flight future per key, so if two requests ask for the same stock at the same moment the second waits for the first instead of computing again. Hits, misses and coalesced waits are counted per tier; live, two simultaneous JPM requests computed once.

### 8. Mixed-signals rule
**Where:** `services/research_engine.py` → `assess_conflict`, `CONFLICT_MIN_GAP = 15`, `CONFLICT_CONFIDENCE_CAP = 60`; `agents/master_agent.py` → `_mixed_signals`.

> A report is "conflicted" when the technical score and the fundamental score sit on opposite sides of 50 and are more than 15 points apart. Confidence is then capped at 60%, and `insight.conflict` explains which side is which. The prompt asks the LLM to start with "Mixed signals", and `_mixed_signals` adds it if the model forgets, so it is guaranteed.

### 9. Pydantic brief validation
**Where:** `agents/master_agent.py` → `Brief`, `RiskItem`, `one_point_per_item`, `check_brief`, `_unsupported_numbers`, `ADVICE_PATTERN`, `analyze`.

> The LLM's JSON must parse into the `Brief` model: summary length, 2–6 key drivers, 2–5 points per case, and risk items whose levels must be Low, Medium or High. `check_brief` also rejects advice words like "buy" or "target price", and more than two numbers that are not in the evidence. A rejected answer is retried once with the reason attached; a second failure uses the rule-written brief.

---

## B. 30 likely questions with honest answers

### Architecture
**1. Walk me through the architecture.**
React on Vercel calls a FastAPI backend on Render. A report request runs three agents concurrently (technical, fundamental, sentiment), combines their scores with fixed rules, and asks a Groq model to explain the result. The answer is validated before it is shown.

**2. Why is the LLM not allowed to score?**
Scores must be repeatable and explainable. The same data always gives the same score, and every point traces to a rule. In v1 the model could overwrite scores and sometimes invented numbers; now it only writes the explanation, and the checks reject invented numbers.

**3. Are these real "agents"?**
No, not in the autonomous-LLM sense. They are concurrent workers behind one interface, each fetching its own data and computing its pillars deterministically. Only the brief step calls an LLM.

**4. Why FastAPI?**
It has native async support, Pydantic validation for requests and responses, and automatic API docs. That suits a service that mostly waits on network calls.

**5. How many workers do you run?**
One Uvicorn worker on one Render instance. Concurrency comes from the event loop plus a 32-thread pool. More workers would break the in-memory cache, quotas and traces, because each process would have its own copy.

### Async and concurrency
**6. The endpoint is async but yfinance is synchronous. How does that work?**
yfinance calls run in `asyncio.to_thread`, so the event loop stays free; Groq and Google News use `httpx.AsyncClient`. This is threads, not true async I/O, but it stops one slow fetch from blocking other users.

**7. What about the GIL?**
The GIL stops Python threads running Python code at the same time, but it is released while a thread waits on the network. Our threads mostly wait on Yahoo, so threads help. The pandas scoring is CPU work and short; heavy CPU work would need processes instead.

**8. Why did you set the thread pool size yourself?**
Python's default is the CPU count plus 4, which is 5 on a 1-CPU Render instance, and one report runs up to six blocking fetches. So I set 32 in the FastAPI lifespan hook (`THREAD_POOL_SIZE`).

**9. What happens if one agent hangs?**
`run_agent` uses `asyncio.wait_for` with a 15-second timeout and marks the agent as `error`. The consensus step re-weights without it. The thread itself can't be killed and finishes in the background; that's a known limit of `to_thread`.

**10. How do you prove the agents run in parallel?**
Each agent records a span with start and end times. A test asserts all three start before any finishes. Live, three simultaneous reports took 7.1 s locally against 23.0 s for v2.0, which ran them one after another.

**11. Did v2.1 make a single report faster?**
No. A single report takes about the same time, 5–8 s, because the Groq call and the data fetch dominate. The gain is under concurrent load: about 2.25× faster for three simultaneous requests.

### Tracing and observability
**12. How does tracing work across concurrent tasks?**
The request ID and trace live in `contextvars`, which asyncio copies into each task and `to_thread` worker. Spans recorded anywhere attach to the right request. It's in-process tracing, not OpenTelemetry.

**13. Where do traces and usage data live?**
In memory: a ring buffer of 200 traces and per-day usage totals for 7 days. They reset on restart and aren't shared across instances. The next step is Postgres or a hosted tracing tool.

**14. What do you log for each LLM call?**
Model, fallback step, attempt number, HTTP status, latency, and prompt, completion and total tokens, as one JSON line tagged with the request ID and prompt version.

**15. How are the admin endpoints protected?**
They need an `x-admin-token` header matching the `ADMIN_TOKEN` environment variable. If that variable isn't set, they refuse everyone, so they're closed by default. Verified live: 403 without the token, 200 with it.

### LLM reliability
**16. What happens when Groq rate-limits you?**
Retry once on the same model after `Retry-After`, capped at 3 s, then move down the chain. Groq's remaining-token header also lets us skip a model before calling it, and it's tried again once its window resets.

**17. Why a 30-second deadline?**
The frontend gives up after 45 s. The LLM gets the earlier of 30 s from now or 42 s from the request start, and no call starts with less than 1 s left. If time runs out, the rule-written brief is used.

**18. How many tokens does a report use?**
About 1,900–2,400: roughly 1,300 prompt tokens and 600–1,000 completion tokens, one call per report. v1 used about 8,400 with all four calls.

**19. How do you stop hallucination?**
The prompt contains only computed evidence. The output must pass the Pydantic schema, contain no advice words, and include at most two numbers not found in the evidence. It catches invented numbers, not every invented sentence. There is no evaluation set yet.

**20. Why one retry and not more?**
Each retry costs tokens against an 8,000-tokens-per-minute free-tier limit and adds latency. One corrective retry fixes most format slips; after that a rule-written brief is safer than waiting.

**21. How do you version prompts?**
Each version is a file in a registry with a changelog. An environment variable picks the active one, and the version is recorded with every report and log line. Nothing technically stops editing a published file; it's a convention.

### Caching and data
**22. Is your cache thread-safe?**
Yes. One lock guards every read, write and counter. Agents run code in threads, so the lock matters.

**23. What is request coalescing?**
If a computation for a key is already in flight, later callers await the same future instead of starting another. A test proves it, and live two simultaneous JPM requests computed once.

**24. Why different TTLs?**
Data changes at different speeds. Prices go stale in minutes, news in half an hour, financial statements quarterly. Fundamentals are cached for 24 hours, which saves the slowest Yahoo calls.

**25. How do Indian tickers work?**
`resolve_and_validate` tries the symbol as typed, then with `.NS` (NSE), then `.BO` (BSE). It's a fallback, not a search API. Market cap is formatted in the listing's currency, for example "₹2.50 lakh Cr".

**26. Where does the data come from, and is that OK for a paid product?**
Yahoo Finance through yfinance, and Google News RSS. Yahoo's data isn't licensed for commercial use, so a paid launch needs a licensed provider. On Render, Yahoo also doesn't return company names, which I found during the live check.

### Testing, deployment, limits
**27. How is it tested?**
25 pytest tests, fully offline. Groq is replaced by a fake HTTP transport, and prices are synthetic. They cover the scoring engine, the fallback chain, retries, the deadline, guardrails, the cache and API concurrency. GitHub Actions runs them on every push and pull request.

**28. How do you deploy?**
Render and Vercel auto-deploy from `main`. Before merging I ran the tests, a local server smoke test, concurrency and auth checks, and a secret scan. After deploying I checked the version, live reports, the admin endpoints and the frontend. CI doesn't block deploys yet.

**29. Is the confidence score calibrated?**
No. It's computed from data completeness, how far the pillars agree and signal strength, but it hasn't been checked against outcomes. Calibration would need stored predictions compared with later returns.

**30. What are the biggest weaknesses, and what would you do next?**
- **Weaknesses:**
  - All state is in memory with one worker.
  - No evaluation set for briefs, and no calibration of confidence.
  - Unlicensed data.
  - Company names fail on the hosted server.
  - No payments yet.
- **Next:**
  - Fix the names.
  - Move quotas and usage to Postgres.
  - Connect Razorpay so keys are issued automatically.
  - Build a small evaluation set.

---

## C. Do not claim

| Do not say | Say instead |
| :-- | :-- |
| "Autonomous AI agents", "multi-agent LLM system" | "Three concurrent workers behind one interface; one LLM call explains the result" |
| "The AI analyses the stock" | "Rules score the stock; the LLM explains the scores" |
| LangChain, n8n, Docker, Kubernetes, Redis, Kafka | Not used |
| "Distributed tracing", OpenTelemetry | "In-process tracing with contextvars" |
| "CI/CD pipeline" | "CI that runs the tests; Render and Vercel auto-deploy" |
| "Fully async" | "Async I/O for HTTP; yfinance runs in a thread pool" |
| "Faster reports" | "About 2.25× faster for 3 concurrent requests; single reports unchanged" |
| "No hallucinations" | "Rejects invented numbers and advice wording; no evaluation set" |
| "Calibrated" or "backtested" confidence | "Rule-based confidence, not calibrated" |
| "Production-scale", "handles thousands of users" | "Single instance, tested with a handful of concurrent requests" |
| "Payments", "Razorpay integration", "subscribers" | "Plans and signed access keys; payments not connected" |
| Any user, revenue or accuracy numbers | None exist |
| "Persistent usage analytics" | "In-memory daily usage, reset on restart" |
| "SEBI-compliant", "licensed data" | Neither is true yet |

---

## D. 2-minute walkthrough (say it aloud)

> Quantum is a stock research app. You type a ticker, US or Indian, and get a scored report with the evidence behind every number.
>
> The key design choice is that the AI never decides anything. A rule-based engine scores eight pillars, such as trend, momentum, profitability, valuation and news, from five years of prices, the company's financial statements and recent headlines. Then one LLM call on Groq writes the explanation.
>
> The backend is FastAPI. When a request comes in, I resolve the ticker, then run three agents concurrently with `asyncio.gather`: technical, fundamental and sentiment. Yahoo's library is synchronous, so those calls run in a thread pool, and the HTTP calls use an async client. A consensus step combines the scores. If the price picture and the business picture disagree by more than 15 points across the midpoint, the report is flagged "mixed signals" and confidence is capped at 60.
>
> For reliability, the LLM call has a fallback chain of three models. It retries rate limits once, skips a model that's out of token budget and returns to it automatically, and everything sits inside a 30-second deadline. The answer must pass a Pydantic schema and checks against advice wording and invented numbers. It gets one retry, then a rule-written brief is used instead.
>
> For operations, every request has an ID carried through contextvars, with timed spans for each step. Token usage is logged per call, prompts are versioned files, and a four-tier cache with request coalescing means identical requests compute once. Three simultaneous reports went from 23 seconds to about 10.
>
> It has 25 offline tests that run in GitHub Actions, and it's deployed on Render and Vercel. The honest limits: state is in memory on one worker, the data source isn't licensed for commercial use, and there's no evaluation set yet. Those are my next steps.
