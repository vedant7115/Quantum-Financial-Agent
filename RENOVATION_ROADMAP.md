# QUANTUM — Renovation Roadmap and Business Model

Audit date: 15 November 2026. Based on a full read of the repository and live tests of
`quantum-financial-agent.vercel.app` (frontend) and `quantum-financial-agent.onrender.com` (API).

**The short version.** The idea is sound and the pipeline runs: a ticker goes in, a
structured multi-agent report comes out in about five seconds. But the product is not
ready to charge for. In production today, one of the three agents is silently broken
for every stock, made-up data is shown as real, and several report sections display
numbers that are invented in the browser. Paying customers for financial research will
find these within minutes. The order of work is therefore: make every number true,
then put up the paywall, then redesign.

---

## 1. What works today (verified live)

| Area | Status |
| :-- | :-- |
| API uptime | `/health` answered in 0.3 s; keep-alive is working |
| Analysis speed | AAPL 5.5 s, RELIANCE 3.9 s, NVDA 4.6 s end to end |
| Price and technicals | Live prices, RSI, MACD, 50/200-day averages, support/resistance and five timeframes are computed from real Yahoo history |
| News | Real headlines with real sources and timestamps (Yahoo Finance, CNBC, Morningstar, etc.) |
| Master synthesis | The Groq model writes a coherent summary, bull/bear case, risk register |
| Indian tickers | `RELIANCE` resolves to `RELIANCE.NS` correctly |
| Frontend | Landing page, dashboard, 16-section report, TradingView chart, print-to-PDF all render |

## 2. What is broken (ranked by damage to a paid product)

### P0 — wrong or invented data shown to users

1. **The Fundamental agent is dead in production.** On Render, Yahoo's `ticker.info`
   call fails and the code swallows the error and continues with zeros. Every stock
   tested returned market cap `N/A`, P/E empty, health score `10/100`, verdict `Weak`.
   The live AAPL report tells the reader Apple has "weak solvency" and "a deficit in
   net income". The same for NVDA and Reliance. This also drags the 35% fundamental
   weight into every consensus score.
   (`backend/services/stock_service.py:128-134`, `backend/agents/fundamental_agent.py`)
2. **A ticker that does not exist gets a full report.** `ZZZZQQ` returned HTTP 200:
   price $162.29, market cap $118.7B, Bullish at 76% confidence. All random numbers.
   (`stock_service.py:271-305`, `is_ticker_valid` at `:397`)
3. **Fabricated headlines attributed to real publishers.** When news fails, the app
   generates headlines such as "Regulatory probe launched against {ticker}" and labels
   the source "Reuters", "Bloomberg" or "MarketWatch". This is the most serious item
   in the audit; it has to go before any public launch. (`news_service.py:190-236`)
4. **Report sections computed from made-up formulas in the browser.**
   - Scenario price targets and probabilities (`bullProb = confidence * 0.4`, base
     fixed at 60%). The live NVDA report was rated Bearish while showing the bear
     scenario at 10% probability. (`InstitutionalReport.jsx:138-144`)
   - "Institutional positioning (FII/DII)" is derived from news ratio and health
     score, with fixed bar widths. Its own footnote says the flows are simulated.
   - Scorecard tiles show figures with no source: "Consensus trend +83 pts (90D)",
     "Benchmark industry avg 56/100", "Revenue growth 16.5%" on the same page where
     the fundamental desk says revenue growth is N/A.
   - News "impact scores" are a hash of the headline text. (`App.jsx:180-186`)
   - "Recent research activity" shows hardcoded bias, confidence and times.
   - Sector is guessed from the ticker; anything unknown is "Technology & Software".
5. **Catalyst calendar dates are invented by the model, and many are in the past.**
   The prompt hardcodes "the current date is June 2026"; the live report listed an
   "Investor Day 2026-06-20" as upcoming. (`master_agent.py:242`, `:285-296`)
6. **The sentiment lexicon misreads obvious headlines.** "HSBC downgrades Nvidia",
   "A House of Cards (Rating Downgrade)" and "Burry says 'get out' of Nvidia" were all
   tagged Neutral. The sub-agent LLM path that would fix this is switched off
   (`ENABLE_SUBAGENT_LLM` defaults to false). An RSI of 24.9 is described as "neutral".
7. **The landing page contradicts the product.** The sample card shows BUY/HOLD
   verdicts while the engine is built to never say BUY/SELL. The Apple sample shows a
   price of $182.50 with support at $292. Marketing copy claims "100+ financial
   indicators" (about 8 are computed), "local SEC databases", "ADX", "DCF model" and
   "analyst revisions"; none exist in the code. `index.html` still advertises
   "BUY/HOLD/SELL recommendations".

### P1 — things that block running it as a business

- No accounts, no database, no payments. Search history lives in the browser.
- Rate limit and cache are in server memory: lost on every restart, wrong with more
  than one server process, and the limiter sees the proxy IP on Render, not the user.
- `/api/clear-cache` and `/docs` are open to anyone.
- CORS is `*`.
- The data source is unofficial Yahoo scraping. It is unreliable from cloud IPs (see
  item 1) and Yahoo's terms do not allow commercial redistribution. A paid product
  needs a licensed feed.
- All agents run one after another inside a single request; each yfinance call blocks
  the event loop. Fine for a demo, not for concurrent users.
- No tests beyond one manual script; no error monitoring; no analytics.

### P2 — code and UX debt

- `InstitutionalReport.jsx` is 86 KB in one file; `LandingPage.jsx` 55 KB; `App.jsx`
  39 KB. No router, so no shareable report URLs, no back button, no SEO per page.
- `index.css` overrides Tailwind's own size classes with `!important` (for example
  `.text-sm` is forced to 16px), so no class means what it says.
- Two headers are rendered on the home page (the app's and the landing page's).
- Dead code: `base_agent.py` (OpenRouter, unused), `google-generativeai` dependency,
  empty Dockerfiles and `docker-compose.yml`, duplicated `Procfile`/`render.yaml`.
- README still describes Gemini and has `file:///c:/Users/DELL/...` links.
- Not usable on a phone: 9–10px mono text, 12-column desktop grids.
- The print report says "Antigravity AI ... assume no liability" and "SEC-ID".

---

## 3. Business model

### Who pays

Self-directed retail investors in India and the US who already pay for TradingView,
Screener, Tickertape or Seeking Alpha, and want one readable brief instead of five
tabs. Second audience later: small advisory desks and finfluencers who need
client-ready PDFs.

### What they pay for

Free users get the conclusion. Paying users get the reasoning, the history, and the
alerts. The paywall should sit on depth and convenience, never on correctness.

| | **Free** | **Pro** | **Desk** |
| :-- | :-- | :-- | :-- |
| Price | ₹0 | ₹499 / month (US$9) | ₹2,999 / month (US$39) |
| Reports per day | 3 | 50 | 500 |
| Summary, technicals, fundamentals, news | Yes | Yes | Yes |
| Bull vs bear debate | Locked | Yes | Yes |
| Risk register and catalyst calendar | Locked | Yes | Yes |
| PDF export | Locked | Yes | Yes, white-label (to build) |
| Watchlist and saved reports | — | To build | To build |
| Price and news alerts | — | To build | To build |
| API access | — | — | To build |

Annual billing at two months free. Prices are starting points to test, not findings;
they are set in one place (`backend/services/billing_service.py`).

### Unit economics (rough)

A report costs one Groq call (a few thousand tokens) plus data. I have not priced
this against Groq's current rate card; do that before fixing prices, and again if the
sub-agent LLM calls are switched on (four calls per report instead of one). Inference
for a model of this size is normally a small fraction of a ₹499 subscription even for
a heavy user. The cost line to watch is the market-data licence, not the model.

### Other revenue, in order of how soon it is realistic

1. Subscriptions (above).
2. Pay-per-report packs for occasional users (10 reports for ₹199).
3. Weekly "top movers" email digest as the free-to-paid funnel.
4. API and white-label PDFs for small advisory firms.

### Two things to settle before taking money

- **Regulation.** In India, selling research or recommendations on listed securities
  for a fee generally falls under SEBI's Research Analyst regulations. Wording like
  "Strategic accumulation on support floor" and the BUY badges read as advice. Get a
  proper opinion from a securities lawyer before launch; the options are usually to
  register, to partner with a registered analyst, or to position strictly as a data
  and education tool with no recommendations. I am flagging this, not ruling on it.
- **Ownership.** The repository's `origin` is a teammate's account and the footer says
  it was built for the Capgemini buildathon. Agree in writing with the team (and check
  the event's terms) who owns the product before commercialising it.

---

## 4. Design direction — "calm, exact, Apple-like"

The current look is a hacker terminal: tiny uppercase mono text, sixteen boxed
sections, peach accents, jargon ("LVL2 feeds ingested", "Upgraded Decision Box").
It signals complexity, not trust. The backend's story is simple and strong, so the
interface should be too.

- **One idea per screen.** The report opens with a single answer: the bias, the
  confidence, and one sentence of why. Everything else is one scroll or one tap away.
- **Typography carries the design.** System font stack (SF Pro on Apple devices,
  Inter elsewhere), large tight headlines, 17px body, mono only for numbers.
- **Restraint with colour.** Near-black and white, one accent, green/red reserved for
  price direction only.
- **Plain language.** "Why now?" instead of "Timing trigger"; "What could go wrong"
  instead of "Risk register matrix". No invented terminal jargon.
- **Show the agents working.** The three-agents-then-synthesis story is the product's
  best visual. Stream real progress from the server instead of a timed animation.
- **Every number has a source and a time.** A small "Yahoo Finance · 14:32 IST"
  under each figure does more for trust than any marketing copy.
- **Mobile first.** Most Indian retail investors will open this on a phone.

The new Pricing page on this branch is built in this language as a reference for the
rest of the redesign.

---

## 5. Roadmap

### Phase 0 — Make it true (this branch covers the starred items)

- ★ Never serve mock prices or fabricated headlines in production; fail honestly.
- ★ Reject unknown tickers instead of inventing a report.
- ★ When fundamentals cannot be fetched, say so and take that agent out of the
  consensus weighting instead of scoring the company 10/100.
- ★ Give the model today's real date; drop catalyst entries dated in the past.
- ★ Lock down `/api/clear-cache`.
- Replace `ticker.info` with a source that works from the server (see Phase 2), which
  is what actually brings the Fundamental agent back to life.
- Remove or rebuild the invented sections: scenario targets, FII/DII positioning,
  benchmark averages, "consensus trend", news impact scores, fake recent activity.
- Turn on LLM sentiment so downgrades are not scored neutral.
- Rewrite the landing page claims and sample card to match what the product does.

### Phase 1 — Take money (foundation on this branch)

- ★ Plans, daily quotas and server-side locking of premium sections.
- ★ Signed access keys so early customers can be upgraded by hand.
- ★ Pricing page and in-report upgrade prompts.
- Accounts (email/Google sign-in) and a database (Postgres) for users, usage, reports.
- Checkout: Razorpay for India, Stripe for international; webhooks set the plan.
- Terms, privacy policy, refund policy, disclaimers reviewed by a lawyer.

### Phase 2 — Make it dependable

- Licensed market data (for example Financial Modeling Prep, Twelve Data or EODHD for
  US; a licensed NSE/BSE vendor for India) behind a provider interface.
- Redis for cache, quotas and rate limits. Run the three agents in parallel.
- Server-sent events so the pipeline animation reflects real progress.
- Tests for each agent with recorded data; error tracking; product analytics.
- Restrict CORS to the production domain; hide `/docs` in production.

### Phase 3 — Redesign

- Add a router; shareable `/report/AAPL` URLs with link previews (free marketing).
- Break the three giant components into small ones; delete the `!important` overrides.
- Rebuild landing, dashboard and report in the design language above. Mobile first.
- Custom domain and a proper logo.

### Phase 4 — Reasons to stay subscribed

- Watchlist with a daily brief; price, news and bias-change alerts by email/WhatsApp.
- Report history: "what changed since last week".
- Compare two stocks side by side. Portfolio view.
- Track record page: how past Bullish/Bearish calls performed. This is the strongest
  sales asset a research product can have, and it only works if the data is honest.

---

## 6. What this branch (`feat/monetization-foundation`) adds

See the commit diff for detail. Environment variables introduced:

| Variable | Where | Purpose |
| :-- | :-- | :-- |
| `ACCESS_KEY_SECRET` | backend | Signs Pro/Desk access keys. Without it only the Free plan exists. |
| `ADMIN_TOKEN` | backend | Required header value for `/api/clear-cache`. |
| `ALLOW_MOCK_DATA` | backend | `true` re-enables mock data for offline development only. |
| `FREE_DAILY_REPORTS` | backend | Overrides the free quota (default 3). |
| `VITE_UPGRADE_URL` | frontend | Payment link the upgrade buttons open. |

Issue a key for a paying customer:

```bash
python scripts/issue_access_key.py pro 30
```

Known limits of this foundation: usage counters are in memory (reset on restart) and
free users are identified by IP address. Both are replaced by accounts and a database
in Phase 1.
