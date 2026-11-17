# Changelog

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
