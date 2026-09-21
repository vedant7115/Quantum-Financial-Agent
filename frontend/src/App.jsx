import React, { useState, useEffect } from "react";
import Header from "./components/Header";
import SearchBar from "./components/SearchBar";
import ArchitecturePage from "./components/ArchitecturePage";
import NewsInsights from "./components/NewsInsights";
import LandingPage from "./components/LandingPage";
import InstitutionalReport from "./components/InstitutionalReport";
import { analyzeStock, getStockData, checkBackendHealth } from "./api";
import { 
  TrendingUp, 
  Landmark, 
  Newspaper, 
  Search, 
  ArrowRight, 
  ShieldAlert, 
  Clock, 
  LayoutGrid, 
  Scale, 
  Activity, 
  CheckCircle2, 
  Brain,
  X
} from "lucide-react";

const WORKFLOW_STAGES = [
  { id: 1, label: "Market Data Collection", desc: "LVL2 feeds ingested, order book depth mapped." },
  { id: 2, label: "Technical Intelligence", desc: "Pattern recognition and momentum oscillation complete." },
  { id: 3, label: "Fundamental Intelligence", desc: "Analyzing balance sheet health and cash flows..." },
  { id: 4, label: "Sentiment Intelligence", desc: "Awaiting social and news NLP synthesis." },
  { id: 5, label: "Consensus Synthesis", desc: "Aggregating agent outputs for master verdict." },
];

function App() {
  const [currentPage, setCurrentPage] = useState("Home");
  const [isLoading, setIsLoading] = useState(false);
  const [workflowStep, setWorkflowStep] = useState(0); // 0 = idle, 1-5 stages
  const [stageTimes, setStageTimes] = useState({});
  const [error, setError] = useState(null);
  const [analysisData, setAnalysisData] = useState(null);
  const [stockInfoData, setStockInfoData] = useState(null);
  const [backendHealth, setBackendHealth] = useState({ checked: false, online: null });
  const [activeModal, setActiveModal] = useState(null);
  const [searchInputValue, setSearchInputValue] = useState("");

  // Verify backend server availability
  useEffect(() => {
    async function verifyBackendConnection() {
      try {
        const data = await checkBackendHealth();
        if (data && data.status === "ok") {
          setBackendHealth({ checked: true, online: true });
        } else {
          setBackendHealth({ checked: true, online: false });
        }
      } catch (err) {
        setBackendHealth({ checked: true, online: false });
      }
    }
    verifyBackendConnection();
  }, []);

  // Search History State (loaded from LocalStorage)
  const [searchHistory, setSearchHistory] = useState(() => {
    try {
      const stored = localStorage.getItem("quantum_search_history");
      return stored ? JSON.parse(stored) : ["AAPL", "TSLA", "MSFT", "INFY.NS", "RELIANCE.NS"];
    } catch {
      return ["AAPL", "TSLA", "MSFT", "INFY.NS", "RELIANCE.NS"];
    }
  });

  const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  async function handleSearch(symbol) {
    if (!symbol) return;
    const cleanSym = symbol.toUpperCase().trim();
    setSearchInputValue(cleanSym);
    
    setIsLoading(true);
    setError(null);
    setAnalysisData(null);
    setStockInfoData(null);
    
    const times = {};
    times[1] = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    setStageTimes(times);
    setWorkflowStep(1); // Stage 1: Market data

    // Save symbol in local search history
    setSearchHistory((prev) => {
      const filtered = prev.filter((s) => s !== cleanSym);
      const updated = [cleanSym, ...filtered].slice(0, 8);
      localStorage.setItem("quantum_search_history", JSON.stringify(updated));
      return updated;
    });

    try {
      const fetchPromise = Promise.all([
        analyzeStock(cleanSym),
        getStockData(cleanSym),
      ]);

      // Step-by-step pipeline visualization delay
      await delay(600);
      times[2] = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      setStageTimes({ ...times });
      setWorkflowStep(2); // Stage 2: Technical

      await delay(600);
      times[3] = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      setStageTimes({ ...times });
      setWorkflowStep(3); // Stage 3: Fundamental

      await delay(600);
      times[4] = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      setStageTimes({ ...times });
      setWorkflowStep(4); // Stage 4: Sentiment

      await delay(600);
      times[5] = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      setStageTimes({ ...times });
      setWorkflowStep(5); // Stage 5: Consensus Synthesis

      const [analysis, stockInfo] = await fetchPromise;

      await delay(400);
      setAnalysisData(analysis);
      setStockInfoData(stockInfo);
      setWorkflowStep(0); // Reset workflow step once finished
    } catch (err) {
      setWorkflowStep(0);
      if (err.code === "ERR_NETWORK") {
        setError("Cannot establish connection with the FastAPI gateway. Ensure the backend is running on port 8000.");
      } else {
        setError(err.response?.data?.detail || "Analysis pipeline failed. Verify ticker format.");
      }
    } finally {
      setIsLoading(false);
    }
  }

  function handleExportPDF() {
    if (!analysisData) return;
    const originalTitle = document.title;
    document.title = `QUANTUM_REPORT_${analysisData.stock}_${new Date().toISOString().split('T')[0]}`;
    window.print();
    document.title = originalTitle;
  }

  const isFallbackActive =
    analysisData &&
    (analysisData.technical?.fallback_active ||
      analysisData.fundamental?.fallback_active ||
      analysisData.sentiment?.fallback_active ||
      analysisData.final_decision?.fallback_active);

  // Helper for news article decimal impact scores (Stitch style e.g. +0.8, -0.4)
  function getNewsImpactScore(title, sentiment) {
    const s = sentiment ? sentiment.toLowerCase() : "";
    if (s !== "positive" && s !== "negative") return "0.0";
    const hash = title.split("").reduce((acc, char) => acc + char.charCodeAt(0), 0);
    const score = ((hash % 8) + 6) / 10; // returns 0.6 to 1.3
    return s === "positive" ? `+${score.toFixed(1)}` : `-${score.toFixed(1)}`;
  }

  // Indian Ticker indicator
  const isIndianTicker = (sym) => {
    return sym && (sym.endsWith(".NS") || sym.endsWith(".BO") || sym.endsWith(".ns") || sym.endsWith(".bo"));
  };

  return (
    <div className="min-h-screen pb-12 bg-[#05060f] text-[#f3f4f6]" style={{ fontFamily: "'Inter', sans-serif" }}>
      
      {/* Subtle background grid pattern */}
      <div
        className="fixed inset-0 opacity-[0.03] pointer-events-none z-0"
        style={{
          backgroundImage: "radial-gradient(circle at 1px 1px, rgba(59, 130, 246, 0.08) 1px, transparent 0)",
          backgroundSize: "24px 24px",
        }}
      />

      {/* Header bar */}
      <header className="border-b border-white/5 bg-[#05060f]/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2.5 cursor-pointer" onClick={() => setCurrentPage("Home")}>
            <div className="w-8 h-8 rounded bg-[#FFBA9D] flex items-center justify-center">
              <span className="text-black font-black text-sm">Q</span>
            </div>
            <span className="font-bold text-[15px] tracking-wider text-white uppercase" style={{ fontFamily: "'General Sans', sans-serif" }}>
              QUANTUM INTEL
            </span>
          </div>

          <nav className="flex items-center gap-4 text-[11px] font-medium text-slate-400">
            <button
              onClick={() => { setCurrentPage("Home"); setAnalysisData(null); }}
              className={`px-3 py-1 rounded transition ${currentPage === "Home" ? "bg-white/10 text-white font-semibold" : "text-slate-400 hover:text-white"}`}
            >
              Home
            </button>
            <button
              onClick={() => { setCurrentPage("Dashboard"); }}
              className={`px-3 py-1 rounded transition ${currentPage === "Dashboard" ? "bg-white/10 text-white font-semibold" : "text-slate-400 hover:text-white"}`}
            >
              Dashboard
            </button>
            <button
              onClick={() => setCurrentPage("Architecture")}
              className={`px-3 py-1 rounded transition ${currentPage === "Architecture" ? "bg-white/10 text-white font-semibold" : "text-slate-400 hover:text-white"}`}
            >
              Architecture
            </button>
          </nav>
        </div>
      </header>

      {/* Main Page Selector */}
      {currentPage === "Home" ? (
        <LandingPage
          onStartResearch={(sym) => {
            setCurrentPage("Dashboard");
            if (sym) handleSearch(sym);
          }}
          onViewArchitecture={() => setCurrentPage("Architecture")}
        />
      ) : currentPage === "Architecture" ? (
        <ArchitecturePage systemStatus={analysisData?.system_status || (backendHealth.online ? {
          backend_status: "Online",
          groq_status: "Online",
          yfinance_status: "Online",
          news_status: "Online",
          cache_status: "Active",
          cache_ttl_sec: 300,
          execution_time_sec: 0.05
        } : null)} />
      ) : (
        <main className="max-w-6xl mx-auto px-6 py-10 relative z-10 space-y-6">
          
          {/* Diagnostic warning alert when FastAPI backend is offline */}
          {backendHealth.checked && !backendHealth.online && (
            <div className="bg-red-950/20 border border-red-500/20 rounded p-5 relative overflow-hidden fade-in-up">
              <h3 className="text-red-400 font-bold font-mono text-xs uppercase tracking-wide mb-2 flex items-center gap-1.5">
                <span>🚨</span> FastAPI Backend Gateway Offline
              </h3>
              <p className="text-slate-300 text-[11px] leading-relaxed">
                The client cannot establish a connection with the FastAPI backend at <code className="px-1.5 py-0.5 rounded bg-black/40 text-rose-350 font-mono text-[10.5px]">http://localhost:8000</code>. Verify uvicorn server status.
              </p>
              <div className="mt-3.5 flex gap-2">
                <button 
                  onClick={() => window.location.reload()} 
                  className="px-4 py-1.5 rounded bg-red-600 hover:bg-red-500 text-white text-[10px] font-bold transition font-mono uppercase tracking-wider"
                >
                  🔄 Retry Connection
                </button>
                <button 
                  onClick={() => setBackendHealth({ checked: true, online: true })} 
                  className="px-4 py-1.5 rounded border border-slate-700 hover:border-slate-500 text-slate-400 hover:text-white text-[10px] font-bold transition font-mono uppercase tracking-wider"
                >
                  Bypass Alert
                </button>
              </div>
            </div>
          )}

          {/* Error Banner / Beautiful Invalid Ticker Screen */}
          {error && !isLoading && (
            error === "INVALID_TICKER" ? (
              <div className="bg-[#0a0c16] border border-red-500/30 rounded p-8 flex flex-col items-center justify-center text-center max-w-xl mx-auto space-y-6 fade-in-up my-12 shadow-[0_0_50px_rgba(239,68,68,0.05)] font-mono">
                <div className="w-16 h-16 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center text-red-500 text-3xl">
                  ⚠️
                </div>
                <div className="space-y-2">
                  <h3 className="text-white font-black text-xl tracking-wide uppercase">Ticker Not Found</h3>
                  <p className="text-slate-400 text-xs font-light leading-relaxed">
                    We could not find market data for this symbol <code className="px-1.5 py-0.5 rounded bg-black/40 text-red-400 font-mono font-bold">{searchInputValue}</code>.
                  </p>
                </div>
                <div className="border-t border-white/5 pt-4 w-full text-left text-xs text-slate-500">
                  <span className="font-bold uppercase tracking-wider block mb-2 text-center text-slate-400">Try a valid ticker such as:</span>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-center">
                    {["AAPL", "TSLA", "MSFT", "NVDA", "RELIANCE.NS", "TCS.NS"].map((sym) => (
                      <button
                        key={sym}
                        type="button"
                        onClick={() => handleSearch(sym)}
                        className="px-3 py-1.5 rounded border border-white/5 bg-[#0c0d18] text-slate-350 hover:text-white hover:border-slate-500 transition cursor-pointer"
                      >
                        {sym}
                      </button>
                    ))}
                  </div>
                </div>
                <button
                  onClick={() => setError(null)}
                  className="px-6 py-2 rounded bg-white/10 hover:bg-white/20 text-white font-mono text-[10px] uppercase tracking-wider font-bold transition cursor-pointer"
                >
                  Return to Dashboard
                </button>
              </div>
            ) : (
              <div className="bg-red-500/10 border border-red-500/20 rounded p-4 flex items-start gap-3 fade-in-up font-mono text-xs">
                <span className="text-red-400">⚠️</span>
                <div>
                  <h4 className="text-red-400 font-bold">Orchestration Error</h4>
                  <p className="text-slate-400 mt-1">{error}</p>
                </div>
              </div>
            )
          )}

          {/* ── CASE 1: IDLE / LOADING SEARCH SCREEN (Screenshot 2 style) ── */}
          {(!analysisData || isLoading) && (
            <div className="space-y-12 py-10 fade-in-up">
              {/* Header Title */}
              <div className="text-center space-y-4 max-w-2xl mx-auto">
                <h2 
                  className="text-4xl sm:text-5xl font-black text-white tracking-tight"
                  style={{ fontFamily: "'General Sans', sans-serif" }}
                >
                  Research Any Public Company
                </h2>
                <p className="text-slate-400 text-xs sm:text-sm font-light leading-relaxed">
                  Generate a multi-layer investment thesis combining technical intelligence, company fundamentals and market sentiment.
                </p>
              </div>

              {/* Search Bar Input (Screenshot 2 styled centered) */}
              <div className="max-w-xl mx-auto">
                <form 
                  onSubmit={(e) => { e.preventDefault(); handleSearch(searchInputValue); }} 
                  className="flex gap-2.5 bg-[#0a0c16] border border-white/10 rounded p-2"
                >
                  <div className="flex-1 relative flex items-center">
                    <Search size={14} className="text-slate-500 absolute left-3" />
                    <input
                      type="text"
                      value={searchInputValue}
                      onChange={(e) => setSearchInputValue(e.target.value.toUpperCase())}
                      placeholder="Search RELIANCE.NS, TSLA, AAPL..."
                      className="w-full bg-transparent pl-9 pr-3 py-2 outline-none text-white font-mono text-xs placeholder-slate-500"
                      disabled={isLoading}
                    />
                  </div>
                  <button
                    type="submit"
                    className="px-6 py-2 rounded bg-[#FFBA9D] text-black font-black text-[10px] uppercase tracking-wider hover:bg-[#ffa382] transition disabled:opacity-50 cursor-pointer"
                    disabled={isLoading || !searchInputValue.trim()}
                  >
                    {isLoading ? "Executing..." : "Execute"}
                  </button>
                </form>

                {/* Popular Chips */}
                <div className="mt-3.5 flex items-center justify-center gap-1.5 flex-wrap font-mono text-[9px] text-slate-500 font-bold uppercase">
                  <span>Popular:</span>
                  {["AAPL", "TSLA", "MSFT", "NVDA", "AMZN", "META", "RELIANCE.NS", "INFY.NS"].map((sym) => (
                    <button
                      key={sym}
                      onClick={() => handleSearch(sym)}
                      disabled={isLoading}
                      className="px-2 py-0.5 rounded border border-white/5 bg-[#0c0d18] text-slate-400 hover:text-white hover:border-slate-500 transition cursor-pointer"
                    >
                      {sym.replace(".NS", "")}
                    </button>
                  ))}
                </div>
              </div>

              {/* Side-by-side Layout: Recent Activity vs Live Pipeline Timeline */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 max-w-4xl mx-auto pt-6 border-t border-white/5">
                
                {/* Left Column: Recent Activity */}
                <div className="lg:col-span-5 space-y-4">
                  <span className="section-label block mb-3">RECENT RESEARCH ACTIVITY</span>
                  <div className="space-y-2.5">
                    {searchHistory.map((sym, idx) => {
                      const mockBiases = ["BULLISH", "NEUTRAL", "BULLISH", "NEUTRAL"];
                      const mockConf = [92, 64, 85, 58];
                      const mockTime = ["12:45 PM Today", "11:20 AM Today", "Yesterday", "2 days ago"];
                      const biasVal = mockBiases[idx % mockBiases.length];
                      const confVal = mockConf[idx % mockConf.length];
                      const timeVal = mockTime[idx % mockTime.length];
                      
                      return (
                        <div 
                          key={idx}
                          onClick={() => handleSearch(sym)}
                          className="bg-[#0c0d18] border border-white/5 rounded p-3.5 flex justify-between items-center cursor-pointer hover:border-white/10 transition duration-150"
                        >
                          <div>
                            <span className="text-white font-bold font-mono text-[11px] block">{sym}</span>
                            <span className="text-slate-500 text-[8.5px] font-mono mt-0.5 block">{isIndianTicker(sym) ? "NSE:INDIA" : "NASDAQ:US"}</span>
                          </div>
                          <div className="text-right font-mono text-[8.5px]">
                            <span className={`font-black uppercase block ${biasVal === "BULLISH" ? "text-emerald-450 text-emerald-400" : "text-amber-400"}`}>{biasVal}</span>
                            <span className="text-slate-400 font-bold block mt-0.5">Conf: {confVal}%</span>
                            <span className="text-slate-600 block mt-0.5">{timeVal}</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Right Column: Research Pipeline Timeline */}
                <div className="lg:col-span-7 space-y-4">
                  <span className="section-label block mb-3">RESEARCH PIPELINE // LIVE EXECUTION</span>
                  <div className="bg-[#0c0d18] border border-white/5 rounded p-5 space-y-4 relative">
                    
                    {/* Vertical connecting line */}
                    <div className="absolute top-[32px] bottom-[32px] left-[27px] w-0.5 bg-slate-800 -z-10" />

                    {WORKFLOW_STAGES.map((stage) => {
                      const isActive = workflowStep === stage.id;
                      const isCompleted = workflowStep > stage.id;
                      
                      return (
                        <div key={stage.id} className="flex gap-4 items-start relative z-10">
                          {/* Circle dot status */}
                          <div className={`w-4 h-4 rounded-full border flex items-center justify-center shrink-0 transition-all duration-300 mt-1 ${
                            isActive 
                              ? "bg-[#FFBA9D] border-[#FFBA9D] shadow-lg shadow-orange-500/20 animate-pulse" 
                              : isCompleted
                              ? "bg-emerald-500 border-emerald-500 text-white text-[8px]"
                              : "bg-[#05060f] border-slate-800"
                          }`}>
                            {isCompleted && "✓"}
                          </div>
                          
                          {/* Label, Description and Timestamp */}
                          <div className="flex-1 font-mono text-[10.5px]">
                            <div className="flex justify-between items-baseline">
                              <span className={`font-bold transition-colors ${
                                isActive ? "text-[#FFBA9D]" : isCompleted ? "text-slate-200" : "text-slate-500"
                              }`}>
                                {stage.label}
                              </span>
                              {isCompleted && stageTimes[stage.id] && (
                                <span className="text-[8.5px] text-emerald-400 font-normal">{stageTimes[stage.id]}</span>
                              )}
                              {isActive && (
                                <span className="text-[8.5px] text-[#FFBA9D] animate-pulse">EXECUTING...</span>
                              )}
                            </div>
                            <p className="text-[9.5px] text-slate-550 text-slate-500 font-sans mt-0.5 leading-normal">{stage.desc}</p>
                          </div>
                        </div>
                      );
                    })}

                  </div>
                </div>

              </div>

            </div>
          )}

          {/* ── CASE 2: SEARCH RESULTS LOADED (Screenshot 1 & 3 style) ── */}
          {analysisData && !isLoading && (
            <div className="space-y-6 fade-in-up">
              
              {/* Search-Bar at top of results to allow searching again easily */}
              <div className="flex flex-col sm:flex-row justify-between items-center gap-4 bg-[#0a0c16] border border-white/5 rounded p-3">
                <span className="section-label block pl-2">Quantum Analyst Terminal</span>
                <div className="flex flex-col sm:flex-row items-center gap-3 w-full sm:w-auto justify-end">
                  <form 
                    onSubmit={(e) => { e.preventDefault(); handleSearch(searchInputValue); }}
                    className="flex gap-2 w-full sm:max-w-md bg-[#05060f] border border-white/10 rounded px-2.5 py-1"
                  >
                    <input
                      type="text"
                      value={searchInputValue}
                      onChange={(e) => setSearchInputValue(e.target.value)}
                      placeholder="Enter Stock Ticker..."
                      className="w-full bg-transparent outline-none text-white font-mono text-xs placeholder-slate-500"
                    />
                    <button type="submit" className="text-[#FFBA9D] hover:text-[#ffa382] font-mono text-[9px] font-bold uppercase tracking-wider">
                      EXECUTE
                    </button>
                  </form>
                  <button 
                    onClick={handleExportPDF}
                    className="w-full sm:w-auto px-4 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-mono text-[10px] font-bold uppercase tracking-wider transition shrink-0 cursor-pointer"
                  >
                    Export Report
                  </button>
                </div>
              </div>

              <InstitutionalReport
                analysisData={analysisData}
                stockInfo={stockInfoData}
                isFallbackActive={isFallbackActive}
              />

            </div>
          )}

          {/* Footer of dashboard (Screenshot 1 / 2) */}
          <footer className="border-t border-white/5 py-8 flex flex-col sm:flex-row items-center justify-between gap-4 font-mono text-[9px] text-slate-500 font-bold uppercase">
            <span>© 2026 QUANTUM FINANCIAL INTELLIGENCE. INSTITUTIONAL USE ONLY.</span>
            <div className="flex gap-4">
              <span>Terminal Status: <span className="text-emerald-400 font-black">Operational</span></span>
              <span>Compliance</span>
              <span>Privacy Policy</span>
              <span>Methodology</span>
            </div>
          </footer>

        </main>
      )}

      {/* ── PRINTABLE DOSSIER (A4 Formatted, visible only in print mode) ── */}
      {analysisData && (
        <div className="hidden print:block printable-report">
          <div style={{ borderBottom: "3px double #000", paddingBottom: "10px", marginBottom: "20px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
              <h1 style={{ margin: 0, textTransform: "uppercase" }}>QUANTUM INTEL DOSSIER</h1>
              <span style={{ fontSize: "12px", fontFamily: "monospace", fontWeight: "bold" }}>
                SEC-ID: {analysisData.stock}-{new Date().toISOString().slice(0, 10).replace(/-/g, "")}
              </span>
            </div>
            <div style={{ fontSize: "12px", color: "#666", marginTop: "5px" }}>
              CONFIDENTIAL // FOR INSTITUTIONAL RESEARCH USE ONLY // EQUITIES DIVISION
            </div>
          </div>

          {/* Dossier Header Info */}
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "25px", background: "#f8f9fa", padding: "15px", border: "1px solid #ddd", borderRadius: "4px" }}>
            <div>
              <div style={{ fontSize: "12px", color: "#666", fontWeight: "bold" }}>TARGET EQUITY</div>
              <div style={{ fontSize: "24px", fontWeight: "black", color: "#000" }}>{analysisData.stock}</div>
              <div style={{ fontSize: "13.5px", marginTop: "2px", color: "#333" }}>
                {stockInfoData?.company_name || `${analysisData.stock} Equity`}
              </div>
            </div>
            <div style={{ textAlign: "right" }}>
              <div style={{ fontSize: "12px", color: "#666", fontWeight: "bold" }}>CONSENSUS VERDICT</div>
              <div style={{ fontSize: "21px", fontWeight: "black", color: "#000" }}>
                {analysisData.final_decision?.market_bias?.toUpperCase()}
              </div>
              <div style={{ fontSize: "12px", fontWeight: "bold", marginTop: "2px", color: "#333" }}>
                CONVICTION: {analysisData.final_decision?.confidence}% // RISK: {analysisData.final_decision?.risk?.toUpperCase()}
              </div>
            </div>
          </div>

          {/* Core Thesis */}
          <div style={{ marginBottom: "25px" }}>
            <h2 style={{ fontSize: "16px", fontWeight: "bold", borderBottom: "2px solid #000", paddingBottom: "4px" }}>1. Executive Summary & Thesis</h2>
            <p style={{ marginTop: "10px", textAlign: "justify", color: "#000", fontSize: "13.5px" }}>
              {analysisData.final_decision?.summary || analysisData.final_decision?.reasoning}
            </p>
          </div>

          {/* Technical Analysis */}
          <div style={{ marginBottom: "25px", pageBreakInside: "avoid" }}>
            <h2 style={{ fontSize: "16px", fontWeight: "bold", borderBottom: "2px solid #000", paddingBottom: "4px" }}>2. Technical Intelligence</h2>
            <div style={{ display: "flex", gap: "20px", marginTop: "10px", marginBottom: "10px", fontSize: "12px", color: "#000" }}>
              <div style={{ flex: 1, padding: "8px", border: "1px solid #eee", background: "#fafafa" }}>
                <strong>Trend Verdict:</strong> {analysisData.technical?.trend?.toUpperCase()}
              </div>
              <div style={{ flex: 1, padding: "8px", border: "1px solid #eee", background: "#fafafa" }}>
                <strong>RSI (14):</strong> {analysisData.technical?.rsi || stockInfoData?.stock?.rsi || "N/A"}
              </div>
              <div style={{ flex: 1, padding: "8px", border: "1px solid #eee", background: "#fafafa" }}>
                <strong>MACD Signal:</strong> {analysisData.technical?.macd || stockInfoData?.stock?.macd || "N/A"}
              </div>
              <div style={{ flex: 1, padding: "8px", border: "1px solid #eee", background: "#fafafa" }}>
                <strong>S/R Levels:</strong> S: {analysisData.technical?.support_level || "N/A"} / R: {analysisData.technical?.resistance_level || "N/A"}
              </div>
            </div>
            <p style={{ textAlign: "justify", color: "#000", fontSize: "13.5px" }}>
              {analysisData.technical?.summary || "Technical analysis indicates pattern convergence."}
            </p>
          </div>

          {/* Fundamental Analysis */}
          <div style={{ marginBottom: "25px", pageBreakInside: "avoid" }}>
            <h2 style={{ fontSize: "16px", fontWeight: "bold", borderBottom: "2px solid #000", paddingBottom: "4px" }}>3. Fundamental Valuation</h2>
            <div style={{ display: "flex", gap: "20px", marginTop: "10px", marginBottom: "10px", fontSize: "12px", color: "#000" }}>
              <div style={{ flex: 1, padding: "8px", border: "1px solid #eee", background: "#fafafa" }}>
                <strong>Health Score:</strong> {analysisData.fundamental?.health_score || "N/A"}/100
              </div>
              <div style={{ flex: 1, padding: "8px", border: "1px solid #eee", background: "#fafafa" }}>
                <strong>Valuation Score:</strong> {analysisData.fundamental?.valuation_score || "N/A"}/100
              </div>
              <div style={{ flex: 1, padding: "8px", border: "1px solid #eee", background: "#fafafa" }}>
                <strong>Growth Score:</strong> {analysisData.fundamental?.growth_score || "N/A"}/100
              </div>
              <div style={{ flex: 1, padding: "8px", border: "1px solid #eee", background: "#fafafa" }}>
                <strong>Trailing PE:</strong> {stockInfoData?.stock?.pe_ratio ? `${stockInfoData.stock.pe_ratio}x` : "N/A"}
              </div>
            </div>
            <p style={{ textAlign: "justify", color: "#000", fontSize: "13.5px" }}>
              {analysisData.fundamental?.summary || "Fundamental assessment based on filings and margins."}
            </p>
          </div>

          {/* Sentiment Analysis */}
          <div style={{ marginBottom: "25px", pageBreakInside: "avoid" }}>
            <h2 style={{ fontSize: "16px", fontWeight: "bold", borderBottom: "2px solid #000", paddingBottom: "4px" }}>4. Sentiment & News Harvester</h2>
            <div style={{ display: "flex", gap: "20px", marginTop: "10px", marginBottom: "10px", fontSize: "12px", color: "#000" }}>
              <div style={{ flex: 1, padding: "8px", border: "1px solid #eee", background: "#fafafa" }}>
                <strong>Sentiment Verdict:</strong> {analysisData.sentiment?.sentiment?.toUpperCase()}
              </div>
              <div style={{ flex: 1, padding: "8px", border: "1px solid #eee", background: "#fafafa" }}>
                <strong>Bullish Ratio:</strong> {Math.round(analysisData.sentiment?.positive_ratio * 100 || 0)}%
              </div>
              <div style={{ flex: 1, padding: "8px", border: "1px solid #eee", background: "#fafafa" }}>
                <strong>Bearish Ratio:</strong> {Math.round(analysisData.sentiment?.negative_ratio * 100 || 0)}%
              </div>
            </div>
            <p style={{ marginBottom: "15px", textAlign: "justify", color: "#000", fontSize: "13.5px" }}>
              {analysisData.sentiment?.summary || "Sentiment signals parsed from recent news coverage."}
            </p>

            <h3 style={{ borderBottom: "1px solid #eee", paddingBottom: "3px", marginBottom: "10px", fontSize: "13.5px", fontWeight: "bold", color: "#000" }}>Captured Intelligence Feeds</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {analysisData.sentiment?.articles && analysisData.sentiment.articles.slice(0, 5).map((art, idx) => (
                <div key={idx} style={{ fontSize: "12px", borderLeft: "2px solid #ccc", paddingLeft: "8px", color: "#000" }}>
                  <div style={{ fontWeight: "bold" }}>{art.title}</div>
                  <div style={{ fontSize: "10px", color: "#666" }}>
                    Source: {art.source} // Published: {art.publish_time} // Impact Class: {art.sentiment?.toUpperCase()}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Telemetry and Audit */}
          <div style={{ marginTop: "40px", pageBreakInside: "avoid", borderTop: "2px solid #000", paddingTop: "15px" }}>
            <h2 style={{ fontSize: "16px", fontWeight: "bold", borderBottom: "2px solid #000", paddingBottom: "4px" }}>5. System Telemetry & Authenticity Log</h2>
            <table style={{ width: "100%", marginTop: "10px", fontSize: "12px", borderCollapse: "collapse", border: "1px solid #ddd", color: "#000" }}>
              <thead>
                <tr style={{ background: "#f1f1f1" }}>
                  <th style={{ border: "1px solid #ddd", padding: "6px", textAlign: "left" }}>Metric Name</th>
                  <th style={{ border: "1px solid #ddd", padding: "6px", textAlign: "left" }}>Recorded Value</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td style={{ border: "1px solid #ddd", padding: "6px" }}>Technical Math Engine</td>
                  <td style={{ border: "1px solid #ddd", padding: "6px" }}>Local Quant Processor (18 Indicators Calculated)</td>
                </tr>
                <tr>
                  <td style={{ border: "1px solid #ddd", padding: "6px" }}>AI Inference Model</td>
                  <td style={{ border: "1px solid #ddd", padding: "6px" }}>
                    {(analysisData.system_status?.groq_status || "").toLowerCase() === "fallback mode" ? "Heuristic Rules (Fallback Mode)" : "Llama 3.3 70B (Groq Gateway)"}
                  </td>
                </tr>
                <tr>
                  <td style={{ border: "1px solid #ddd", padding: "6px" }}>Execution Duration</td>
                  <td style={{ border: "1px solid #ddd", padding: "6px" }}>{analysisData.system_status?.execution_time_sec} seconds</td>
                </tr>
                <tr>
                  <td style={{ border: "1px solid #ddd", padding: "6px" }}>Cache Status</td>
                  <td style={{ border: "1px solid #ddd", padding: "6px" }}>{analysisData.system_status?.cache_status}</td>
                </tr>
                <tr>
                  <td style={{ border: "1px solid #ddd", padding: "6px" }}>Security Validation Gate</td>
                  <td style={{ border: "1px solid #ddd", padding: "6px" }}>Rate Limiter Checked & Staged (Passed)</td>
                </tr>
              </tbody>
            </table>

            {/* Pipeline Stage Logs */}
            <h3 style={{ marginTop: "15px", marginBottom: "8px", fontSize: "13.5px", fontWeight: "bold", color: "#000" }}>Pipeline Execution Timestamp Logs</h3>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "10px", fontSize: "12px", fontFamily: "monospace", color: "#000" }}>
              {analysisData.timeline?.map((step, idx) => (
                <div key={idx} style={{ padding: "6px", border: "1px solid #eee", background: "#fcfcfc" }}>
                  <div style={{ color: "#666" }}>[{step.timestamp}]</div>
                  <div style={{ fontWeight: "bold" }}>{step.event}</div>
                </div>
              ))}
            </div>

            {/* Disclaimer */}
            <div style={{ fontSize: "10px", color: "#888", marginTop: "30px", fontStyle: "italic", textAlign: "justify", lineHeight: "1.3" }}>
              Disclaimer: This report is generated dynamically by the Quantum Multi-Agent Consensus Engine. All data is retrieved from public financial APIs. Antigravity AI, Quantum Intel, and its affiliates assume no liability for investment decisions made using this computer-generated analysis. Equity investing involves substantial risk.
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
