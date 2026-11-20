import React, { useCallback, useEffect, useRef, useState } from "react";
import { Check, Search } from "lucide-react";
import HomePage from "./components/HomePage";
import PricingPage from "./components/PricingPage";
import ResearchReport from "./components/ResearchReport";
import { analyzeStock, getUsage } from "./api";

const STEPS = [
  "Fetching five years of prices",
  "Reading the company's financial statements",
  "Collecting recent headlines",
  "Scoring eight pillars",
  "Writing the brief",
];

// Routes live in the URL hash so a report can be bookmarked or shared: #/s/AAPL
function readRoute() {
  const hash = window.location.hash.replace(/^#\/?/, "");
  if (hash === "pricing") return { page: "pricing" };
  if (hash.startsWith("s/")) return { page: "report", symbol: decodeURIComponent(hash.slice(2)).toUpperCase() };
  return { page: "home" };
}

function errorMessage(err) {
  const status = err?.response?.status;
  const detail = err?.response?.data?.detail;
  if (detail === "INVALID_TICKER") return { title: "We could not find that ticker.", body: "Check the symbol and try again. Indian stocks use their NSE symbol, such as RELIANCE or TCS." };
  if (detail === "DATA_UNAVAILABLE") return { title: "Market data is unavailable right now.", body: "The data provider did not answer for this stock. Try again in a minute." };
  if (detail === "INSUFFICIENT_HISTORY") return { title: "This stock is too new to assess.", body: "It has fewer than 30 trading days of prices, which the price checks need. Try again once it has traded longer." };
  if (status === 429) return { title: "That was a lot of requests.", body: "Wait a minute, then try again." };
  if (!err?.response) return { title: "The research engine is waking up.", body: "It sleeps when idle and takes up to a minute to start. Try again shortly." };
  return { title: "Something went wrong.", body: "The report could not be produced. Try again." };
}

function Loading({ symbol }) {
  const [step, setStep] = useState(0);
  useEffect(() => {
    const timer = setInterval(() => setStep((s) => Math.min(s + 1, STEPS.length - 1)), 2200);
    return () => clearInterval(timer);
  }, []);
  return (
    <div className="qx-page">
      <div className="qx-loading" role="status" aria-live="polite">
        <h2>Researching {symbol}</h2>
        <ol>
          {STEPS.map((label, i) => (
            <li key={label} data-state={i < step ? "done" : i === step ? "active" : "todo"}>
              <span className="qx-tick">{i < step && <Check size={13} strokeWidth={3} />}</span>{label}
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}

export default function App() {
  const [route, setRoute] = useState(readRoute);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [quota, setQuota] = useState(null);
  const [access, setAccess] = useState(null);
  const [navQuery, setNavQuery] = useState("");
  const requestId = useRef(0);

  const go = useCallback((hash) => { window.location.hash = hash; }, []);

  useEffect(() => {
    const onHash = () => setRoute(readRoute());
    window.addEventListener("hashchange", onHash);
    getUsage().then(setAccess).catch(() => {});
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const run = useCallback(async (symbol) => {
    const id = ++requestId.current;
    setLoading(true); setError(null); setQuota(null); setReport(null);
    try {
      const data = await analyzeStock(symbol);
      if (id !== requestId.current) return;
      setReport(data);
      if (data.access) setAccess(data.access);
    } catch (err) {
      if (id !== requestId.current) return;
      const detail = err?.response?.data?.detail;
      if (err?.response?.status === 402 && detail?.code === "QUOTA_EXCEEDED") { setQuota(detail); setAccess(detail); }
      else setError(errorMessage(err));
    } finally {
      if (id === requestId.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    window.scrollTo(0, 0);
    if (route.page === "report" && route.symbol) run(route.symbol);
  }, [route.page, route.symbol, run]);

  const search = (symbol) => go(`/s/${encodeURIComponent(symbol.toUpperCase().trim())}`);
  const usage = access?.usage;

  return (
    <div className="qx qx-app">
      <nav className="qx-nav" aria-label="Main">
        <div className="qx-nav-inner">
          <button type="button" className="qx-brand" onClick={() => go("/")}><span className="qx-brand-mark" aria-hidden="true" />Quantum</button>
          <div className="qx-nav-links">
            <button type="button" className="qx-nav-link" aria-current={route.page !== "pricing" ? "page" : undefined} onClick={() => go("/")}>Research</button>
            <button type="button" className="qx-nav-link" aria-current={route.page === "pricing" ? "page" : undefined} onClick={() => go("/pricing")}>Pricing</button>
          </div>
          {usage && <span className="qx-meter"><strong>{access.plan_name}</strong> · {usage.remaining} of {usage.limit} reports left today</span>}
          {route.page !== "home" && (
            <form className="qx-nav-search" role="search" onSubmit={(e) => { e.preventDefault(); if (navQuery.trim()) { search(navQuery); setNavQuery(""); } }}>
              <Search size={15} />
              <input value={navQuery} onChange={(e) => setNavQuery(e.target.value)} placeholder="Search a ticker" aria-label="Search a ticker" autoComplete="off" spellCheck="false" />
            </form>
          )}
        </div>
      </nav>

      <main>
        {route.page === "home" && <HomePage onSearch={search} onPricing={() => go("/pricing")} usage={usage} />}
        {route.page === "pricing" && <PricingPage onStartResearch={() => go("/")} onAccessChange={setAccess} />}
        {route.page === "report" && (
          <>
            {loading && <Loading symbol={route.symbol} />}
            {!loading && quota && (
              <div className="qx-page"><div className="qx-panel">
                <h2 className="qx-h2" style={{ fontSize: 28 }}>You have used today's {quota.usage.limit} reports.</h2>
                <p className="qx-body" style={{ marginTop: 12 }}>Your {quota.plan_name} plan resets at midnight UTC. Companies you already opened today stay free to re-open.</p>
                <button type="button" className="qx-btn qx-btn-primary" style={{ marginTop: 24, width: "auto" }} onClick={() => go("/pricing")}>See plans</button>
              </div></div>
            )}
            {!loading && error && (
              <div className="qx-page"><div className="qx-panel">
                <h2 className="qx-h2" style={{ fontSize: 28 }}>{error.title}</h2>
                <p className="qx-body" style={{ marginTop: 12 }}>{error.body}</p>
                <button type="button" className="qx-btn qx-btn-primary" style={{ marginTop: 24, width: "auto" }} onClick={() => run(route.symbol)}>Try again</button>
              </div></div>
            )}
            {!loading && report && <ResearchReport report={report} onUpgrade={() => go("/pricing")} onRefresh={() => run(route.symbol)} />}
          </>
        )}
        <div className="qx-page" style={{ paddingBottom: 48 }}>
          <footer className="qx-footer">
            Quantum organises public market data, company financial statements and news into research briefs for education.
            It is not investment advice or a recommendation to buy or sell any security, and it does not take your
            circumstances into account. Market data may be delayed or inaccurate. Past performance does not predict future returns.
          </footer>
        </div>
      </main>
    </div>
  );
}
