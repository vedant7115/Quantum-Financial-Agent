import React, { useMemo, useState } from "react";
import {
  Area, Bar, BarChart, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { Download, RefreshCw } from "lucide-react";
import LockedSection from "./LockedSection";

const STANCE = {
  Bullish: { title: "Leans positive", glow: "rgba(48, 209, 88, 0.18)" },
  Neutral: { title: "Mixed picture", glow: "rgba(255, 159, 10, 0.16)" },
  Bearish: { title: "Leans negative", glow: "rgba(255, 69, 58, 0.18)" },
};
const PILLAR_NAMES = {
  trend: "Trend", momentum: "Momentum", stability: "Stability", quality: "Profitability",
  growth: "Growth", valuation: "Valuation", balance: "Balance sheet", news: "News flow",
};
const RANGES = [["3M", 63], ["6M", 126], ["1Y", 252]];

const scoreColor = (s) => (s == null ? "var(--qx-text-faint)" : s >= 60 ? "var(--qx-good)" : s >= 40 ? "var(--qx-mid)" : "var(--qx-bad)");
const signed = (v, digits = 1) => (v == null ? "n/a" : `${v > 0 ? "+" : ""}${v.toFixed(digits)}%`);
const toneClass = (v) => (v == null || v === 0 ? "qx-flat" : v > 0 ? "qx-up" : "qx-down");
const shortDate = (iso) => new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short" });
const longDate = (iso) => new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" });

function ago(iso) {
  if (!iso) return "";
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86400000);
  if (days <= 0) return "Today";
  return days === 1 ? "Yesterday" : `${days} days ago`;
}

function ScoreRing({ score }) {
  const r = 58;
  const c = 2 * Math.PI * r;
  return (
    <div className="qx-ring" role="img" aria-label={`Overall score ${score} out of 100`}>
      <svg width="132" height="132" viewBox="0 0 132 132">
        <circle cx="66" cy="66" r={r} fill="none" stroke="rgba(255,255,255,0.09)" strokeWidth="8" />
        <circle cx="66" cy="66" r={r} fill="none" stroke={scoreColor(score)} strokeWidth="8" strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c * (1 - score / 100)} style={{ transition: "stroke-dashoffset 1s cubic-bezier(0.2,0.8,0.2,1)" }} />
      </svg>
      <div className="qx-ring-label"><strong>{score}</strong><span>of 100</span></div>
    </div>
  );
}

function PriceChart({ chart, symbol, cur }) {
  const [range, setRange] = useState(252);
  const rows = useMemo(() => {
    const all = chart.dates.map((d, i) => ({ d, close: chart.close[i], ma50: chart.ma50[i], ma200: chart.ma200[i] }));
    return all.slice(-range);
  }, [chart, range]);
  const change = rows.length > 1 ? (rows[rows.length - 1].close / rows[0].close - 1) * 100 : 0;
  const stroke = change >= 0 ? "#30d158" : "#ff453a";
  const fmt = (v) => `${cur}${Number(v).toLocaleString("en-IN", { maximumFractionDigits: v > 999 ? 0 : 2 })}`;

  return (
    <div className="qx-card qx-chart-card">
      <div className="qx-chart-head">
        <div>
          <div className="qx-chart-title">
            Price <span className={toneClass(change)} style={{ marginLeft: 8, fontVariantNumeric: "tabular-nums" }}>{signed(change)}</span>
          </div>
          <div className="qx-legend">
            <span><i style={{ background: stroke }} />Close</span>
            <span><i style={{ background: "#2997ff" }} />50-day average</span>
            <span><i style={{ background: "#bf5af2" }} />200-day average</span>
          </div>
        </div>
        <div className="qx-seg small" role="group" aria-label="Chart range">
          {RANGES.map(([label, n]) => (
            <button key={label} type="button" aria-pressed={range === n} onClick={() => setRange(n)}>{label}</button>
          ))}
        </div>
      </div>
      <div style={{ flex: 1, minHeight: 300 }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={rows} margin={{ top: 8, right: 4, bottom: 0, left: 4 }}>
            <defs>
              <linearGradient id={`fill-${symbol}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={stroke} stopOpacity={0.28} />
                <stop offset="100%" stopColor={stroke} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
            <XAxis dataKey="d" tickFormatter={shortDate} tick={{ fill: "#6e6e73", fontSize: 11 }} axisLine={false} tickLine={false} minTickGap={56} />
            <YAxis orientation="right" domain={["auto", "auto"]} tickFormatter={fmt} tick={{ fill: "#6e6e73", fontSize: 11 }} axisLine={false} tickLine={false} width={64} />
            <Tooltip cursor={{ stroke: "rgba(255,255,255,0.25)", strokeWidth: 1 }} content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const p = payload[0].payload;
              return (
                <div className="qx-tooltip">
                  {longDate(p.d)}
                  <strong>{fmt(p.close)}</strong>
                  {p.ma50 != null && <div>50-day {fmt(p.ma50)}</div>}
                  {p.ma200 != null && <div>200-day {fmt(p.ma200)}</div>}
                </div>
              );
            }} />
            <Area type="monotone" dataKey="close" stroke={stroke} strokeWidth={2} fill={`url(#fill-${symbol})`} dot={false} isAnimationActive={false} />
            <Line type="monotone" dataKey="ma50" stroke="#2997ff" strokeWidth={1.25} dot={false} isAnimationActive={false} connectNulls />
            <Line type="monotone" dataKey="ma200" stroke="#bf5af2" strokeWidth={1.25} dot={false} isAnimationActive={false} connectNulls />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function Finding({ f, showTag }) {
  return (
    <div className="qx-finding">
      <span className="qx-dot" data-tone={f.tone} aria-hidden="true" />
      <div className="qx-finding-title">
        {f.title}
        {showTag && <span className="qx-finding-tag">{PILLAR_NAMES[f.pillar]}</span>}
      </div>
      <p className="qx-finding-detail">{f.detail}</p>
    </div>
  );
}

function Stat({ label, value, note, tone }) {
  return (
    <div className="qx-stat">
      <div className="qx-stat-label">{label}</div>
      <div className={`qx-stat-value ${tone || ""}`}>{value}</div>
      {note && <div className="qx-stat-note">{note}</div>}
    </div>
  );
}

function BaseRates({ base }) {
  // Scale shared by the box (middle half of outcomes) and the zero line.
  const lo = Math.min(base.lower_quartile, 0) - 4;
  const hi = Math.max(base.upper_quartile, 0) + 4;
  const pos = (v) => `${((v - lo) / (hi - lo)) * 100}%`;
  const diff = base.positive_rate - base.baseline_positive_rate;
  return (
    <div className="qx-base">
      <div className="qx-card">
        <div className="qx-card-title">Three months later <span>{base.days} trading days in {base.episodes} separate stretches</span></div>
        <div className="qx-base-big">{base.positive_rate}%</div>
        <p className="qx-base-cap">
          of the time the price was higher, against {base.baseline_positive_rate}% across all days.
          {Math.abs(diff) < 5 ? " Being in this state made little difference." : diff > 0 ? " Better than this stock's usual odds." : " Worse than this stock's usual odds."}
        </p>
        <div className="qx-dist" aria-hidden="true">
          <div className="qx-dist-axis" />
          <div className="qx-dist-zero" style={{ left: pos(0) }} />
          <div className="qx-dist-box" style={{ left: pos(base.lower_quartile), width: `calc(${pos(base.upper_quartile)} - ${pos(base.lower_quartile)})` }} />
          <div className="qx-dist-median" style={{ left: pos(base.median_return) }} />
        </div>
        <div className="qx-dist-labels">
          <span>Lower quarter {signed(base.lower_quartile)}</span>
          <span>Median {signed(base.median_return)}</span>
          <span>Upper quarter {signed(base.upper_quartile)}</span>
        </div>
      </div>
      <div className="qx-card">
        <div className="qx-card-title">Where it stands today</div>
        <p className="qx-finding-title" style={{ fontSize: 19, lineHeight: 1.35 }}>{base.regime_label}.</p>
        <div className="qx-metrics" style={{ marginTop: 24, gridTemplateColumns: "repeat(3, 1fr)" }}>
          <div><div className="qx-stat-label">Typical outcome</div><div className={`qx-stat-value ${toneClass(base.median_return)}`}>{signed(base.median_return)}</div></div>
          <div><div className="qx-stat-label">Worst</div><div className="qx-stat-value qx-down">{signed(base.worst, 0)}</div></div>
          <div><div className="qx-stat-label">Best</div><div className="qx-stat-value qx-up">{signed(base.best, 0)}</div></div>
        </div>
        <p className="qx-caveat">
          Measured on this stock's own last {base.years} years. Consecutive days overlap, so the {base.episodes} separate
          stretches are the real sample size. This describes the past and is not a forecast.
        </p>
      </div>
    </div>
  );
}

export default function ResearchReport({ report, onUpgrade, onRefresh }) {
  const ins = report.insight;
  const decision = report.final_decision;
  const access = report.access || {};
  const locked = new Set(access.locked_sections || []);
  const [pillar, setPillar] = useState(null);
  const [showAll, setShowAll] = useState(false);

  if (!ins) {
    return <div className="qx-page"><div className="qx-panel"><p className="qx-body">This report was produced by an older version of the engine. Run it again to see the full evidence.</p></div></div>;
  }

  const cur = ins.currency_symbol;
  const money = (v) => `${cur}${Number(v).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  const stance = STANCE[ins.bias] || STANCE.Neutral;
  const price = ins.price;
  const fund = ins.fundamentals;
  const symbol = report.stock;
  const paragraphs = (decision.summary || "").split(/\n\n+/).filter(Boolean);
  const articles = report.sentiment?.articles || [];
  const shown = pillar ? ins.findings.filter((f) => f.pillar === pillar) : ins.findings;
  const pillarNote = pillar ? ins.scorecard.find((p) => p.key === pillar)?.note : "";
  const history = (fund?.history || []).map((h) => ({ ...h, revenueB: h.revenue, profitB: h.net_income }));
  const compact = (v) => new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 }).format(v);

  function pickPillar(key) {
    setPillar((current) => (current === key ? null : key));
    setShowAll(true);
    document.getElementById("evidence")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  return (
    <div className="qx-page">
      {/* ── Header ── */}
      <header className="qx-report-head">
        <div>
          <h1>{ins.name || symbol}</h1>
          <div className="qx-meta">
            <span className="qx-chip"><b>{symbol}</b></span>
            {ins.sector && <span className="qx-chip">{ins.sector}</span>}
            {ins.market_cap && <span className="qx-chip">Market value <b>{ins.market_cap}</b></span>}
          </div>
        </div>
        <div className="qx-quote">
          <div className="qx-quote-price">{money(report.current_price)}</div>
          <div className={`qx-quote-change ${toneClass(report.change_pct)}`}>{signed(report.change_pct, 2)} today</div>
          <div className="qx-quote-asof">Data to {longDate(ins.as_of)}</div>
        </div>
      </header>

      {!ins.coverage.financials && (
        <div className="qx-banner">Company financial statements could not be retrieved for this stock, so profitability, growth, valuation and balance sheet are not scored. The view below rests on price behaviour and news only.</div>
      )}

      {/* ── The view ── */}
      <div className="qx-view">
        <section className="qx-card qx-verdict" style={{ "--verdict-glow": stance.glow }}>
          <div className="qx-verdict-top">
            <ScoreRing score={ins.composite} />
            <div>
              <div className="qx-stance">{stance.title}</div>
              <p className="qx-stance-sub">The weighted result of {ins.scorecard.filter((p) => p.score != null).length} scored pillars. Above 60 leans positive, below 40 leans negative.</p>
            </div>
          </div>
          <div className="qx-chiprow">
            <span className="qx-chip">Confidence <b>{ins.confidence}%</b></span>
            <span className="qx-chip">Risk <b>{ins.risk}</b></span>
            <span className="qx-chip">Price <b>{ins.technical_score ?? "n/a"}</b></span>
            <span className="qx-chip">Business <b>{ins.fundamental_score ?? "n/a"}</b></span>
          </div>
          <div className="qx-prose">{paragraphs.map((p, i) => <p key={i}>{p}</p>)}</div>
          <div className="qx-actions" style={{ marginTop: "auto" }}>
            <button type="button" className="qx-btn qx-btn-quiet" onClick={onRefresh}><RefreshCw size={15} /> Refresh</button>
            <button type="button" className="qx-btn qx-btn-quiet" onClick={() => (access.pdf_export ? window.print() : onUpgrade())}>
              <Download size={15} /> {access.pdf_export ? "Save as PDF" : "PDF · Pro"}
            </button>
          </div>
        </section>
        <PriceChart chart={ins.chart} symbol={symbol.replace(/\W/g, "")} cur={cur} />
      </div>

      {/* ── Scorecard ── */}
      <section className="qx-section">
        <div className="qx-section-head">
          <div>
            <p className="qx-kicker">Scorecard</p>
            <h2 className="qx-h2">Eight pillars, each scored from the data.</h2>
            <p className="qx-sub">50 is neutral. Select a pillar to see exactly what moved its score.</p>
          </div>
        </div>
        <div className="qx-pillars">
          {ins.scorecard.map((p) => (
            <button key={p.key} type="button" className="qx-pillar" aria-pressed={pillar === p.key} onClick={() => pickPillar(p.key)}>
              <span className="qx-pillar-label">{p.label}</span>
              <span className="qx-pillar-score" style={{ color: p.score == null ? "var(--qx-text-faint)" : "var(--qx-text)" }}>
                {p.score ?? "–"}{p.score != null && <small>/100</small>}
              </span>
              <span className="qx-bar"><i style={{ width: `${p.score ?? 0}%`, background: scoreColor(p.score) }} /></span>
              <span className="qx-pillar-verdict" style={{ color: scoreColor(p.score) }}>{p.verdict}</span>
            </button>
          ))}
        </div>
      </section>

      {/* ── Evidence ── */}
      <section className="qx-section" id="evidence">
        <div className="qx-section-head">
          <div>
            <p className="qx-kicker">Evidence</p>
            <h2 className="qx-h2">{pillar ? `What moved ${PILLAR_NAMES[pillar].toLowerCase()}.` : "What counts for it, and against."}</h2>
          </div>
          {pillar
            ? <button type="button" className="qx-link" onClick={() => setPillar(null)}>Show all pillars</button>
            : <button type="button" className="qx-link" onClick={() => setShowAll((v) => !v)}>{showAll ? "Show the main points" : `See all ${ins.findings.length} findings`}</button>}
        </div>
        {showAll || pillar ? (
          <div className="qx-card">
            {pillarNote && <p className="qx-empty" style={{ paddingTop: 0 }}>{pillarNote}</p>}
            {shown.length ? shown.map((f, i) => <Finding key={i} f={f} showTag={!pillar} />) : !pillarNote && <p className="qx-empty">Nothing was scored for this pillar.</p>}
          </div>
        ) : (
          <div className="qx-evidence">
            <div className="qx-card">
              <h3><span className="qx-dot" data-tone="positive" /> In its favour</h3>
              {ins.strengths.length ? ins.strengths.map((f, i) => <Finding key={i} f={f} showTag />) : <p className="qx-empty">Nothing scored positively.</p>}
            </div>
            <div className="qx-card">
              <h3><span className="qx-dot" data-tone="negative" /> Against it</h3>
              {ins.concerns.length ? ins.concerns.map((f, i) => <Finding key={i} f={f} showTag />) : <p className="qx-empty">Nothing scored negatively.</p>}
            </div>
          </div>
        )}
      </section>

      {/* ── Price behaviour ── */}
      <section className="qx-section">
        <div className="qx-section-head"><div><p className="qx-kicker">Price behaviour</p><h2 className="qx-h2">How the shares have traded.</h2></div></div>
        <div className="qx-stats">
          <Stat label="1 month" value={signed(price.return_1m)} tone={toneClass(price.return_1m)} />
          <Stat label="3 months" value={signed(price.return_3m)} tone={toneClass(price.return_3m)} />
          <Stat label="6 months" value={signed(price.return_6m)} tone={toneClass(price.return_6m)} />
          <Stat label="1 year" value={signed(price.return_1y)} tone={toneClass(price.return_1y)} note={price.benchmark_return_1y != null ? `${price.benchmark} ${signed(price.benchmark_return_1y)}` : null} />
          <Stat label={`Against the ${price.benchmark}`} value={price.relative_1y == null ? "n/a" : `${price.relative_1y > 0 ? "+" : ""}${price.relative_1y.toFixed(1)} pts`} tone={toneClass(price.relative_1y)} note="Over one year" />
          <Stat label="Volatility" value={price.volatility == null ? "n/a" : `${price.volatility.toFixed(0)}%`} note="A year, from the last 60 days" />
          <Stat label="Largest fall" value={`${price.max_drawdown_1y.toFixed(0)}%`} note="Peak to trough, past year" />
          <Stat label="Beta" value={price.beta == null ? "n/a" : price.beta.toFixed(2)} note="1.00 moves with the market" />
        </div>
        <div className="qx-card" style={{ marginTop: 16 }}>
          <div className="qx-card-title">52-week range <span>{price.range_position}% of the way from low to high</span></div>
          <div className="qx-range-track">
            <div className="qx-range-pin" style={{ left: `${Math.min(98, Math.max(2, price.range_position ?? 50))}%` }}><span>{money(price.last)}</span></div>
          </div>
          <div className="qx-range-ends"><span>Low {money(price.low_52w)}</span><span>High {money(price.high_52w)}</span></div>
        </div>
      </section>

      {/* ── The business ── */}
      {fund && (
        <section className="qx-section">
          <div className="qx-section-head"><div><p className="qx-kicker">The business</p><h2 className="qx-h2">What the company reported.</h2><p className="qx-sub">From its financial statements for the {fund.period_label}.</p></div></div>
          <div className="qx-two">
            <div className="qx-card">
              <div className="qx-metrics">
                {fund.metrics.map((m) => (
                  <div key={m.label}><div className="qx-stat-label">{m.label}</div><div className="qx-stat-value" style={{ fontSize: 22 }}>{m.value}</div></div>
                ))}
              </div>
            </div>
            <div className="qx-card" style={{ display: "flex", flexDirection: "column" }}>
              <div className="qx-card-title">Revenue and profit by year <span>{fund.currency}</span></div>
              <div style={{ flex: 1, minHeight: 220 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={history} margin={{ top: 4, right: 0, bottom: 0, left: 0 }} barGap={4}>
                    <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
                    <XAxis dataKey="period" tick={{ fill: "#6e6e73", fontSize: 12 }} axisLine={false} tickLine={false} />
                    <YAxis hide />
                    <Tooltip cursor={{ fill: "rgba(255,255,255,0.04)" }} content={({ active, payload }) => (active && payload?.length ? (
                      <div className="qx-tooltip">{payload[0].payload.period}<strong>Revenue {compact(payload[0].payload.revenue)}</strong>{payload[0].payload.net_income != null && <div>Net profit {compact(payload[0].payload.net_income)}</div>}</div>
                    ) : null)} />
                    <Bar dataKey="revenueB" fill="#2997ff" radius={[6, 6, 0, 0]} isAnimationActive={false} />
                    <Bar dataKey="profitB" fill="#30d158" radius={[6, 6, 0, 0]} isAnimationActive={false} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="qx-legend"><span><i style={{ background: "#2997ff", height: 8, width: 8 }} />Revenue</span><span><i style={{ background: "#30d158", height: 8, width: 8 }} />Net profit</span></div>
            </div>
          </div>
        </section>
      )}

      {/* ── Base rates (Plus) ── */}
      <section className="qx-section">
        <div className="qx-section-head"><div><p className="qx-kicker">The record</p><h2 className="qx-h2">What happened next, the last times it looked like this.</h2></div></div>
        {locked.has("base_rates") ? (
          <LockedSection title="Historical base rates" description="How this stock behaved over the following three months, every time its trend looked the way it does today. Included in Plus." onUpgrade={onUpgrade} />
        ) : ins.base_rates ? <BaseRates base={ins.base_rates} /> : (
          <div className="qx-card"><p className="qx-empty" style={{ padding: 0 }}>There is not enough price history in this trend state to give a meaningful record.</p></div>
        )}
      </section>

      {/* ── Debate (Plus) ── */}
      <section className="qx-section">
        <div className="qx-section-head"><div><p className="qx-kicker">Both sides</p><h2 className="qx-h2">The case for. The case against.</h2></div></div>
        {locked.has("debate") ? (
          <LockedSection title="Bull case and bear case" description="The strongest honest argument on each side, each point tied to a number from the evidence. Included in Plus." onUpgrade={onUpgrade} />
        ) : (
          <div className="qx-evidence">
            <div className="qx-card qx-case"><h3><span className="qx-dot" data-tone="positive" /> The case for</h3><ul>{decision.bull_case.map((t, i) => <li key={i}>{t}</li>)}</ul></div>
            <div className="qx-card qx-case"><h3><span className="qx-dot" data-tone="negative" /> The case against</h3><ul>{decision.bear_case.map((t, i) => <li key={i}>{t}</li>)}</ul></div>
          </div>
        )}
      </section>

      {/* ── Risks (Pro) ── */}
      <section className="qx-section">
        <div className="qx-section-head"><div><p className="qx-kicker">Risk</p><h2 className="qx-h2">Where it could go wrong.</h2></div></div>
        {locked.has("risks") ? (
          <LockedSection title="Risk register" description="Each risk the evidence supports, rated for how severe and how likely it is. Included in Pro." onUpgrade={onUpgrade} />
        ) : (
          <div className="qx-card">
            {decision.risk_register.map((r, i) => (
              <div className="qx-risk" key={i}>
                <span className="qx-risk-name">{r.category}</span>
                <span className="qx-level" data-level={r.severity}>{r.severity}</span>
                <span className="qx-risk-text">{r.explanation}</span>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ── What to watch (Pro) ── */}
      <section className="qx-section">
        <div className="qx-section-head"><div><p className="qx-kicker">Next</p><h2 className="qx-h2">What would change this view.</h2></div></div>
        {locked.has("watch") ? (
          <LockedSection title="Levels and dates to watch" description="The price levels and scheduled events that would update this report's conclusion. Included in Pro." onUpgrade={onUpgrade} />
        ) : (
          <div className="qx-card">
            <ul className="qx-list">
              {(ins.watch || []).map((t, i) => <li key={i}>{t}</li>)}
              {(ins.calendar || []).filter((e) => e.event !== "Earnings release").map((e, i) => <li key={`c${i}`}>{e.event}: {longDate(e.expected_date)}. {e.potential_impact}</li>)}
            </ul>
          </div>
        )}
      </section>

      {/* ── News ── */}
      <section className="qx-section">
        <div className="qx-section-head"><div><p className="qx-kicker">In the news</p><h2 className="qx-h2">Recent headlines.</h2><p className="qx-sub">{report.sentiment.summary}</p></div></div>
        {articles.length ? (
          <div className="qx-card qx-news">
            {articles.map((a, i) => (
              <a key={i} href={a.link} target="_blank" rel="noreferrer">
                <span className="qx-dot" data-tone={a.sentiment} aria-label={a.sentiment} />
                <span><div className="qx-news-title">{a.title}</div><div className="qx-news-src">{a.source}</div></span>
                <span className="qx-news-when">{ago(a.published)}</span>
              </a>
            ))}
          </div>
        ) : <div className="qx-card"><p className="qx-empty" style={{ padding: 0 }}>No recent headlines about this company were found.</p></div>}
      </section>

      {/* ── Method ── */}
      <section className="qx-section">
        <div className="qx-card qx-method">
          <p><b>How this was made.</b> Scores are calculated by fixed rules from five years of daily prices, the company's reported annual and quarterly statements, and recent headlines. Sources: Yahoo Finance market data{articles.length ? ", Google News" : ""}. {decision.fallback_active ? "The written summary was produced by rule from the same evidence." : "An AI model wrote the summary, the two cases and the risk notes from that evidence only; its text is checked so that it cannot introduce figures of its own."}</p>
          <p style={{ marginTop: 10 }}><b>What it is not.</b> This is research and education, not investment advice or a recommendation to buy or sell. It does not know your circumstances. Data can be late or wrong; check anything important against the company's own filings.</p>
        </div>
      </section>
    </div>
  );
}
