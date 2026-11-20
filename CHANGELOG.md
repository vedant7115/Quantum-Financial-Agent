# Changelog

## Quantum v2.1.1 (on branch `fix/company-name-news`, not deployed yet)

Fixes company names and news on the live site. Scoring formulas, weights and thresholds are unchanged; the response gains one field.

- **What was wrong:** on Render, Yahoo's `quoteSummary` endpoint (what `ticker.info` reads; it needs a cookie and crumb) comes back empty for cloud IPs, while price history, `fast_info` and the statements still work. Evidence from the live AAPL report: `sector` and `industry` were null and there was no earnings date, but market cap and financials were present. The name then fell back to "AAPL Corp.", and the news filter, which needs a word from the name in each headline, kept only headlines containing the literal ticker (1 headline for AAPL).
- **Company name, layered fallbacks** (`backend/services/company_names.py`):
  1. `ticker.info`, then the metadata of the price-history call already made (the chart endpoint works from Render);
  2. Yahoo's search endpoint, exact symbol match only;
  3. a built-in map of 52 common US and Indian tickers;
  4. the plain ticker, never "AAPL Corp.".
- **Name cache:** a found name is cached in the fundamentals tier (24 h); a failed lookup is cached for only 5 minutes.
- **News:** with no company name, Google News is searched by ticker plus "stock", plus the exchange for Indian listings ("RELIANCE NSE stock"); the ticker is always a relevance term. Google News is now added when fewer than four Yahoo headlines survive the relevance filter (before, it was decided on the unfiltered count). No headlines still means `coverage.headlines = 0` and the news pillar is reweighted, as before.
- **Response:** `insight.name_source` added (`yahoo_quote`, `yahoo_chart`, `yahoo_search`, `builtin` or `ticker`). Backend version 2.1.1.
- **Tests:** 11 new offline tests (`tests/test_company_names.py`) for each layer, the all-failed case, the negative cache and the news query and filter; 36 in total.

## Quantum v2.1.0 (2026-11-20)

Operations release. Scoring formulas, weights and thresholds are unchanged, and the response only gains fields. See `ARCHITECTURE.md` and `QUANTUM_RENOVATION_REPORT.md`.

- **Async pipeline:** `/api/analyze` no longer blocks the event loop. Groq and Google News use `httpx.AsyncClient`; yfinance and pandas run in `asyncio.to_thread`; independent fetches use `asyncio.gather`.
- **Agent fan-out:** one `Agent` interface; the technical, fundamental and sentiment agents fetch and compute their evidence concurrently, then the consensus step and the brief.
- **Tracing:** a `request_id` and timed spans per request, returned as `trace`, logged as JSON, last 200 at `GET /api/admin/traces`.
- **Prompt versioning:** prompts in `backend/prompts/` (v2.0, v2.1) with a registry and changelog; `PROMPT_VERSION` selects the active one; the version appears in the response, logs and traces.
- **Usage observability:** tokens, latency, model and fallback step per Groq call; `llm` block in the response; daily aggregates at `GET /api/admin/usage`.
- **Validated brief:** Pydantic schema, one corrective retry, then the rule-written brief; advice and invented-number guardrails kept.
- **Retries and deadline:** 429/5xx retried once per model (Retry-After, max 3 s); models near their token limit are skipped and recover after their window; one 30-second LLM deadline inside a 42-second request budget.
- **Tiered cache:** report 5 min, prices 5 min, news 30 min, fundamentals 24 h; lock, in-flight coalescing, hit/miss counters. The report cache default drops from 15 to 5 minutes.
- **Conflict flag:** `insight.conflict` when technical and fundamental scores are on opposite sides of 50 and more than 15 points apart; confidence capped at 60; the brief says "Mixed signals". `insight.agent_scores` added.
- **Tickers:** any Indian stock resolves without a suffix (.NS, then .BO); market cap is shown in the listing's currency; very new listings return 422 `INSUFFICIENT_HISTORY`.
- **Cleanup:** 17 unused frontend components, the unused OpenRouter client, empty Dockerfiles and the unused `google-generativeai` dependency removed.
- **Logging and tests:** JSON log lines with `request_id` and `prompt_version`; 25 offline pytest tests (`backend/tests`), run by GitHub Actions on every push and pull request.
- **Checked before release (local, 2026-11-20):** 25/25 tests pass with no `.env`; US and Indian reports (Indian typed without a suffix) get an AI brief from `gpt-oss-120b` on prompt v2.1; an invalid ticker returns 400; three simultaneous reports for different stocks finish in 7.1 s; two simultaneous requests for one stock compute once (`coalesced: 1`); both admin endpoints return 403 without the right `x-admin-token`.

### Deploying v2.1.0

- **Render:** set `ADMIN_TOKEN` (new) and `ENV=production`; keep `GROQ_API_KEY`, `GROQ_MODEL=openai/gpt-oss-120b` and `ACCESS_KEY_SECRET`. All other new settings have defaults (see `QUANTUM_RENOVATION_REPORT.md`, section 7).
- **Vercel:** no change.

## Quantum v2.0.0 (2026-11-17)

Version 2 rebuilds how Quantum reaches its conclusions, how it looks, and how it is sold. In version 1 the language model wrote the scores and several report sections, and some of what it showed was invented. In version 2 every score is calculated from market data and the company's reported financial statements, and every claim in a report can be traced to a number.

### Research engine

- **New evidence engine** (`backend/services/research_engine.py`). It scores eight pillars from 0 to 100 using up to 28 fixed checks:
  - Price: trend, momentum, stability
  - Business: profitability, growth, valuation, balance sheet
  - News flow
- **Overall result:** price behaviour counts for 40%, the business for 45% and news for 15%, reweighted when a part cannot be assessed. The stance is positive at 60 or above and negative at 40 or below.
- **Confidence** reflects how complete the data was, how far the pillars agree and how strong the signal is, so a report built on partial data says so.
- **Every finding states its figure**, for example "Operating profit covers interest 6.1 times", with one line on why it matters.
- **Financials come from the reported statements** (income statement, balance sheet, cash flow, quarterly results). Version 1 relied on a summary source that failed on the hosted server. Banks are detected and judged without debt tests, and valuation is skipped when the price and the statements are in different currencies.
- **Historical record:** what the stock did over the following three months each time its trend looked as it does today, over five years, compared with all days.
- **Benchmarks:** US stocks are compared with the S&P 500, Indian stocks with the Nifty 50 or Sensex.
- **Real dates only:** the calendar shows the company's actual earnings and ex-dividend dates.

### AI brief

- **The AI only explains.** It receives the calculated evidence and writes the summary, the case for, the case against and the risk register. It cannot change the scores.
- **Checked before it is shown.** A brief is discarded and replaced by a rule-written version if it contains advice wording ("buy", "sell", "target price") or numbers that are not in the evidence.
- **One AI call per report** instead of several, about 1,900 tokens.
- **Fits Groq's free tier.** Each model allows 8,000 tokens a minute, so the call uses low reasoning effort, has a 1,600-token cap on its answer and falls back in turn across `openai/gpt-oss-120b`, `openai/gpt-oss-20b` and `qwen/qwen3.8-27b`.
- In testing all three models produced valid briefs, and a burst of nine reports in a row all got an AI brief through the fallback chain.

### News

- Handles the current Yahoo Finance news format and searches Google News by company name.
- Removes filing notices, price pages and "stocks to watch" lists, and keeps only headlines that name the company.
- Removes duplicates, drops anything older than 30 days and keeps the 10 most recent.
- Tone tagging recognises phrases as well as single words.

### Plans and access

| | Free | Plus | Pro |
| :-- | :-- | :-- | :-- |
| Price per month | ₹0 | ₹149 ($1.99) | ₹499 ($5.99) |
| Reports per day | 3 | 15 | 60 |
| Includes | View, scorecard, evidence, news | Adds historical record, case for and against | Adds risk register, what to watch, PDF export |

- Daily quotas, with locked sections shown as previews.
- Signed access keys (`qk_<plan>_<expiry>_<signature>`), issued with `scripts/issue_access_key.py`.
- Invented or mock data is no longer served in production.

### Design

- New dark interface in a calm, Apple-like style.
- **Home page:** search, quick picks, what the report contains and how it works.
- **Report:** score ring, price chart with 50-day and 200-day averages (3 months, 6 months, 1 year), clickable pillar tiles that filter the evidence, strengths and concerns, price facts with a 52-week range bar, reported figures with revenue and profit bars, historical record, both cases, risks, what to watch and news.
- **Shareable links:** a report opens directly at `#/s/AAPL`.
- Loading steps, clear messages for unknown tickers, unavailable data and used-up quotas, and a plain disclaimer in the footer.
- Works at phone width.

### Performance

- A fresh report takes about 5 to 9 seconds locally; the same stock again within 15 minutes returns in about 0.2 seconds.
- Cache length can be set with `CACHE_TTL_SECONDS` (default 900).

### Documentation

- `RENOVATION_ROADMAP.md`: audit of version 1, business model, budget plan (about ₹700 a month fixed, break-even at about 6 Plus or 2 Pro subscribers) and known limits.

### Known limits

- Quotas are held in memory and reset when the server restarts; there are no user accounts yet.
- Payments are not connected; plan keys are issued by hand.
- Market data comes from Yahoo Finance, which is not licensed for a paid product.
- Valuation uses fixed thresholds, not comparison with the company's sector.
- News sources sometimes refuse requests or go down; the report then shows that news was unavailable.
- The old landing, report and architecture screens are no longer used but are still in the repository.

## Quantum v1.0.0

Multi-agent research prototype: technical, fundamental and sentiment agents with a language-model master synthesis, deployed on Render and Vercel.
