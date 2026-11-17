import React, { useState } from "react";
import { ArrowRight } from "lucide-react";

const PICKS = [
  ["AAPL", "Apple"], ["NVDA", "Nvidia"], ["MSFT", "Microsoft"], ["TSLA", "Tesla"],
  ["RELIANCE", "Reliance"], ["TCS", "TCS"], ["HDFCBANK", "HDFC Bank"], ["INFY", "Infosys"],
];
const PILLARS = ["Trend", "Momentum", "Stability", "Profitability", "Growth", "Valuation", "Balance sheet", "News flow"];
// Decorative bar lengths for the illustration only. They are not scores for any stock.
const ART_WIDTHS = [78, 62, 54, 88, 70, 38, 66, 50];

export default function HomePage({ onSearch, onPricing, usage }) {
  const [query, setQuery] = useState("");

  function submit(e) {
    e.preventDefault();
    if (query.trim()) onSearch(query.trim());
  }

  return (
    <div className="qx-page">
      <section className="qx-hero">
        <h1>Stock research that <em>shows its work.</em></h1>
        <p className="qx-hero-lede">
          Enter a company. In well under a minute you get a clear view, scored on eight pillars,
          with the number behind every claim.
        </p>
        <form className="qx-hero-search" onSubmit={submit} role="search">
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Ticker, such as AAPL or RELIANCE"
            aria-label="Stock ticker" autoCapitalize="characters" autoComplete="off" spellCheck="false" autoFocus />
          <button type="submit" className="qx-btn qx-btn-primary">Research <ArrowRight size={17} /></button>
        </form>
        <div className="qx-picks">
          {PICKS.map(([symbol, name]) => (
            <button key={symbol} type="button" className="qx-pick" onClick={() => onSearch(symbol)}>{name}<span>{symbol}</span></button>
          ))}
        </div>
        <p className="qx-fineprint">
          US and Indian stocks. {usage ? `${usage.remaining} of ${usage.limit} free reports left today.` : "Three free reports a day."} No account needed.
        </p>
      </section>

      <section className="qx-section">
        <div className="qx-bento">
          <div className="qx-card wide">
            <h3>Eight pillars. One clear view.</h3>
            <p>Price trend, momentum and stability. Profitability, growth, valuation and balance sheet. News flow. Each scored from 0 to 100 by fixed rules, then weighed into a single result.</p>
            <div className="qx-bento-art qx-art-bars" aria-hidden="true">
              {PILLARS.slice(0, 5).map((name, i) => (
                <div key={name}>{name}<span className="qx-bar"><i style={{ width: `${ART_WIDTHS[i]}%`, background: i === 3 ? "var(--qx-good)" : "rgba(255,255,255,0.35)" }} /></span></div>
              ))}
            </div>
          </div>
          <div className="qx-card wide">
            <h3>Every claim carries its number.</h3>
            <p>No "strong fundamentals" hand-waving. Each finding states the figure it rests on and explains, in a sentence, why that figure matters.</p>
            <div className="qx-bento-art">
              <div className="qx-art-quote">
                Operating profit covers interest 6.1 times
                <small>The cushion between what the business earns and what its lenders are owed each year.</small>
              </div>
            </div>
          </div>
          <div className="qx-card">
            <h3>History, not hype.</h3>
            <p>See what the stock actually did over the next three months, each time its trend looked the way it does today.</p>
          </div>
          <div className="qx-card">
            <h3>Both sides, argued properly.</h3>
            <p>The strongest case for and the strongest case against, side by side, so you can weigh them yourself.</p>
          </div>
          <div className="qx-card">
            <h3>AI that cannot make things up.</h3>
            <p>The scores are arithmetic. The AI only writes the explanation, and its text is checked against the evidence before you see it.</p>
          </div>
        </div>
      </section>

      <section className="qx-section">
        <div className="qx-section-head"><div><p className="qx-kicker">How it works</p><h2 className="qx-h2">From ticker to brief.</h2></div></div>
        <div className="qx-steps">
          <div className="qx-step"><h3>Gather</h3><p>Five years of daily prices, the market benchmark, the company's reported statements and the latest headlines.</p></div>
          <div className="qx-step"><h3>Measure</h3><p>Up to 28 checks, from the 200-day trend to free cash flow, each with a fixed threshold.</p></div>
          <div className="qx-step"><h3>Score</h3><p>Checks roll up into eight pillars and one overall result, with a confidence level that reflects how complete the data was.</p></div>
          <div className="qx-step"><h3>Explain</h3><p>A plain-English brief you can read in two minutes, with nothing in it you cannot trace back to a figure.</p></div>
        </div>
      </section>

      <section className="qx-section">
        <div className="qx-card qx-cta">
          <h2 className="qx-h2">Start free. Go deeper from ₹149 a month.</h2>
          <p className="qx-sub" style={{ margin: "12px auto 0" }}>Three reports a day cost nothing. Plus and Pro add the historical record, both cases, the risk register and more reports.</p>
          <button type="button" className="qx-btn qx-btn-primary" onClick={onPricing}>See plans</button>
        </div>
      </section>
    </div>
  );
}
