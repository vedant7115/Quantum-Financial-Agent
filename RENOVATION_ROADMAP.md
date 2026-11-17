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

| | **Free** | **Plus** | **Pro** |
| :-- | :-- | :-- | :-- |
| Price | ₹0 | ₹149 / month (US$1.99) | ₹499 / month (US$5.99) |
| Reports per day | 3 | 15 | 60 |
| Overall view, 8-pillar scorecard, evidence, financials, news | Yes | Yes | Yes |
| Historical base rates for the current trend | Locked | Yes | Yes |
| Bull case and bear case | Locked | Yes | Yes |
| Risk register | Locked | Locked | Yes |
| What would change the view, with key dates | Locked | Locked | Yes |
| PDF export | Locked | Locked | Yes |
| Watchlist, saved reports, alerts | — | To build | To build |

Nothing is priced above ₹499. Annual billing at two months free (₹1,490 and ₹4,990).
Prices live in one place: `backend/services/billing_service.py`.

### Budget plan (cheapest workable setup)

Figures marked * come from third-party pricing pages read in November 2026, not from
the vendor's own page. Check each one before relying on it. Rupee figures assume
roughly ₹88 to the dollar.

**Fixed cost each month**

| Item | Cheap choice | Cost | Note |
| :-- | :-- | :-- | :-- |
| Backend hosting | Render Starter, 512 MB | US$7* (about ₹620) | The free tier sleeps after 15 idle minutes and takes up to a minute to wake. Fine for testing, not for people who paid. |
| Frontend hosting | Cloudflare Pages or a Render static site | ₹0 (verify terms) | Vercel's Hobby plan is for non-commercial use only, by Vercel's own fair-use rules. Charging money on it breaks them. Moving a static Vite build is a small job. |
| Database and login | Supabase free tier | ₹0 (verify limits) | Needed for accounts, usage counts and saved reports. |
| Domain | .in or .com | about ₹80 (₹900 a year) | |
| AI model | Groq, `openai/gpt-oss-120b` | pay per use, below | Free tier reported at 200K tokens a day* on this model, roughly 70 fresh reports. Enough to launch. |
| Market data | Yahoo Finance via yfinance | ₹0 | Not licensed for commercial use. This is the largest open risk, see below. |
| **Total** | | **about ₹700 a month** | |

**Cost of one report**

One model call: about 1,500 tokens in and up to 1,200 out. At US$0.15 and US$0.60 per
million tokens* that is about US$0.001, or **9 paise**. Reports are cached for 15
minutes (`CACHE_TTL_SECONDS`), so a popular stock is paid for once and served to
everyone who asks in that window.

**What a subscriber leaves after costs**

| | Plus ₹149 | Pro ₹499 |
| :-- | :-- | :-- |
| Payment gateway, 2% plus 18% GST on the fee* | ₹3.50 | ₹11.80 |
| Subscription add-on, about 1%* | ₹1.50 | ₹5.00 |
| Model cost, typical use (5 and 20 reports a day) | ₹13 | ₹54 |
| Model cost, worst case (every report, every day) | ₹40 | ₹160 |
| **Left, typical** | **about ₹130** | **about ₹430** |
| **Left, worst case** | about ₹104 | about ₹322 |

Break-even on the ₹700 fixed cost is **about 6 Plus subscribers or 2 Pro**. Even the
heaviest possible user stays profitable, so the daily limits are safe as set.

**Things that change these numbers**

- GST: 18% is due on your sales once you must register (check the threshold with a CA).
  The pricing page already says prices exclude taxes.
- Licensed market data. When Yahoo has to be replaced, expect the data bill to become
  the largest cost. Price it before growth, not after.
- UPI AutoPay for recurring billing has its own per-debit pricing that Razorpay does
  not publish as a flat rate.

**Order to spend money in**

1. ₹0: launch on the free tiers to a small group, with keys issued by hand.
2. About ₹700 a month: Render Starter and a domain, when the first person pays.
3. Later, only when revenue covers it: licensed data, then a larger backend instance.

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
| `ACCESS_KEY_SECRET` | backend | Signs Plus/Pro access keys. Without it only the Free plan exists. |
| `CACHE_TTL_SECONDS` | backend | How long a report is reused (default 900). The main lever on model cost. |
| `ADMIN_TOKEN` | backend | Required header value for `/api/clear-cache`. |
| `ALLOW_MOCK_DATA` | backend | `true` re-enables mock data for offline development only. |
| `FREE_DAILY_REPORTS` | backend | Overrides the free quota (default 3). |
| `VITE_UPGRADE_URL` | frontend | Payment link the upgrade buttons open. |

Issue a key for a paying customer:

```bash
python scripts/issue_access_key.py plus 30
python scripts/issue_access_key.py pro 30
```

Known limits of this foundation: usage counters are in memory (reset on restart) and
free users are identified by IP address. Both are replaced by accounts and a database
in Phase 1.

## 7. Second pass: evidence engine and redesign

**The model.** Analysis no longer depends on what the language model says.
`backend/services/research_engine.py` calculates everything from five years of daily
prices, the market benchmark and the company's reported statements:

- Eight pillars scored 0 to 100: trend, momentum, stability, profitability, growth,
  valuation, balance sheet, news flow. Up to 28 checks, each with a fixed threshold.
- Every check records a finding that states its number and why it matters.
- Fundamentals come from the financial statements (revenue, margins, return on
  equity, free cash flow, debt, interest cover) instead of the summary endpoint that
  Render could not reach. Banks are handled separately: debt tests are not applied.
- Historical base rates: what this stock did over the next three months from every
  past day in the same trend state, with the count of separate stretches shown.
- Confidence now measures the evidence (data coverage, agreement between pillars,
  distance from neutral), not the model's mood.
- The language model writes the summary, the two cases and the risk notes from the
  findings only. Its answer is rejected, and a rule-written version used, if it
  contains advice wording or numbers that are not in the evidence.
- Earnings dates come from the exchange calendar. The model is no longer asked for dates.
- Headlines: filing-notice spam and price-page links are filtered out, headlines must
  name the company, and the tone lexicon handles upgrades, downgrades and target cuts.

**The interface.** New shell, home page and report in the "calm, exact" language
(`frontend/src/App.jsx`, `components/HomePage.jsx`, `components/ResearchReport.jsx`,
`styles/quantum-app.css`). Reports have shareable links (`#/s/AAPL`). Every section
shows calculated data; the browser-invented sections are gone with the old report.

**Known limits**

- Whether statement data loads on Render is not yet verified. It works locally. Each
  report states its coverage, so the first deploy will show it. If it is blocked, the
  free fallbacks are SEC EDGAR for US companies (official, no key) and a paid feed for India.
- Valuation is judged on absolute levels, not against sector peers.
- Foreign listings that report in another currency are only detected when the
  provider returns the reporting currency.
- Yahoo sometimes carries figures that differ from the company's filings.
- The old screens (`LandingPage.jsx`, `InstitutionalReport.jsx`, `ArchitecturePage.jsx`
  and their helpers) are no longer imported. They are still in the repo and can be
  deleted once the team agrees.

