import React, { useState, useEffect } from "react";
import { 
  TrendingUp, TrendingDown, Activity, Shield, AlertTriangle, 
  Zap, Target, ChevronDown, ChevronUp, Calendar, Briefcase, Globe, 
  Percent, Award, Cpu, Layers, List, Search, Database, Clock, 
  ArrowUpRight, ArrowDownRight, MessageSquare, ExternalLink, BookOpen,CheckSquare
} from "lucide-react";
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip
} from "recharts";
import TradingViewChart from "./TradingViewChart";

// Helper for circular gauge stroke-dashoffset calculations
const calculateStrokeOffset = (score, r) => {
  const circ = 2 * Math.PI * r;
  return circ - (score / 100) * circ;
};

const renderFormattedText = (text) => {
  if (!text || typeof text !== "string") return text;
  const parts = text.split(/(\*\*.*?\*\*)/g);
  return parts.map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={index} className="text-white font-semibold">
          {part.slice(2, -2)}
        </strong>
      );
    }
    return part;
  });
};

export default function InstitutionalReport({ analysisData, stockInfo, isFallbackActive }) {
  const [activeTimeframe, setActiveTimeframe] = useState("1d");
  const [telemetryCollapsed, setTelemetryCollapsed] = useState(true);
  const [simCapital, setSimCapital] = useState(50000);
  const [activeSection, setActiveSection] = useState("thesis");

  useEffect(() => {
    const sections = document.querySelectorAll("[data-section]");
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setActiveSection(entry.target.id);
          }
        });
      },
      { rootMargin: "-15% 0px -55% 0px" }
    );

    sections.forEach((sec) => observer.observe(sec));
    return () => sections.forEach((sec) => observer.unobserve(sec));
  }, []);

  if (!analysisData) return null;

  const symbol = analysisData.stock || "Ticker";
  const currentPrice = analysisData.current_price || 0.0;
  const changePct = analysisData.change_pct || 0.0;
  const isUp = changePct >= 0;
  const isIndian = symbol.endsWith(".NS") || symbol.endsWith(".BO");
  const currencySymbol = isIndian ? "₹" : "$";

  // Destructure sub-agents results
  const technical = analysisData.technical || {};
  const fundamental = analysisData.fundamental || {};
  const sentiment = analysisData.sentiment || {};
  const finalDecision = analysisData.final_decision || {};

  const bias = (finalDecision.market_bias || "Neutral").toUpperCase();
  const risk = (finalDecision.risk || "Medium").toUpperCase();
  const confidence = finalDecision.confidence || 50;

  const posVal = Math.round((sentiment.positive_ratio || 0.6) * 100);
  const negVal = Math.round((sentiment.negative_ratio || 0.2) * 100);
  const neuVal = Math.max(0, 100 - posVal - negVal);

  const getBiasColor = (b) => {
    const l = b.toLowerCase();
    if (l.includes("bull") || l.includes("strong") || l.includes("pos") || l.includes("buy")) return "text-emerald-400 border-emerald-500/30 bg-emerald-500/5";
    if (l.includes("bear") || l.includes("weak") || l.includes("neg") || l.includes("sell")) return "text-red-400 border-red-500/30 bg-red-500/5";
    return "text-amber-400 border-amber-500/30 bg-amber-500/5";
  };

  const getRiskColor = (r) => {
    const l = r.toLowerCase();
    if (l === "low") return "text-emerald-400 bg-emerald-500/10 border-emerald-500/20";
    if (l === "high") return "text-red-400 bg-red-500/10 border-red-500/20";
    return "text-amber-400 bg-amber-500/10 border-amber-500/20";
  };

  const getSector = (sym) => {
    const s = sym.toUpperCase();
    if (s.includes("AAPL")) return "Consumer Technology";
    if (s.includes("NVDA")) return "Semiconductors";
    if (s.includes("INFY") || s.includes("TCS") || s.includes("WIPRO")) return "IT Services";
    if (s.includes("RELIANCE")) return "Conglomerate / Energy";
    if (s.includes("HDFCBANK") || s.includes("SBIN") || s.includes("ICICIBANK")) return "Banking & Financials";
    return "Technology & Software";
  };

  // Safe arrays extraction with fallbacks
  const bullCase = finalDecision.bull_case || [
    "Technical indicators show an attractive consolidative structure with long-term uptrend support.",
    "Fundamental posture remains solvent with strong health indicators.",
    "Overall sentiment is positive with emerging market catalysts in media flow."
  ];

  const bearCase = finalDecision.bear_case || [
    "Geopolitical chip sales restrictions and potential regulatory policy shifts.",
    "Elevated trailing valuation multiples pricing in hyper-growth expectations.",
    "Volatility levels remain high, raising drawdown risks during tech sector rotations."
  ];

  const riskRegister = finalDecision.risk_register || [
    { category: "Competition Risk", severity: "Medium", probability: "Medium", explanation: "Rising product saturation and competitor capabilities." },
    { category: "Valuation Risk", severity: "Medium", probability: "Medium", explanation: "PE multiple is elevated relative to historical median levels." },
    { category: "Market Risk", severity: "High", probability: "Medium", explanation: "High stock beta and sensitivity to interest rate announcements." },
    { category: "Execution Risk", severity: "Medium", probability: "Low", explanation: "Delays in production yields or hardware release timelines." },
    { category: "Macro Risk", severity: "Medium", probability: "Medium", explanation: "Global inflation pressures dampening overall consumer demand." },
    { category: "Regulatory Risk", severity: "Low", probability: "Low", explanation: "Antitrust compliance or compliance policies in global territories." }
  ];

  const catalystCalendar = finalDecision.catalyst_calendar || [
    { event: "Earnings Release", expected_date: "Next Quarter", importance: "High", potential_impact: "Validation of margin expansions and sales growth." },
    { event: "Product Launch", expected_date: "Next 6 Months", importance: "Medium", potential_impact: "New target market expansion and service expansion." },
    { event: "Investor Day", expected_date: "Within Year", importance: "Medium", potential_impact: "Management strategic growth plan reveal." },
    { event: "Major Economic Event", expected_date: "Ongoing", importance: "High", potential_impact: "Fed interest rate updates affecting growth stock multiples." }
  ];

  // Dynamic Scenario target price math (Internal calculations, no formulas displayed in UI)
  const baseTarget = currentPrice * (1 + (fundamental.growth_score ? fundamental.growth_score / 600 : 0.1) + (sentiment.positive_ratio ? sentiment.positive_ratio * 0.08 : 0.04));
  const bullTarget = Math.max(technical.resistance_level || currentPrice * 1.15, currentPrice * (1 + (confidence / 280)));
  const bearTarget = Math.min(technical.support_level || currentPrice * 0.85, currentPrice * (1 - (risk === "HIGH" ? 0.22 : risk === "LOW" ? 0.07 : 0.14)));

  const baseProb = 60;
  const bullProb = Math.round(confidence * 0.4);
  const bearProb = 100 - baseProb - bullProb;

  // Simplified Capital Returns Calculations
  const calcSimReturn = (target) => {
    const returnPct = ((target - currentPrice) / currentPrice) * 100;
    const endVal = simCapital * (1 + returnPct / 100);
    return {
      value: endVal.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 }),
      pct: returnPct.toFixed(1),
      isLoss: returnPct < 0
    };
  };

  const simBull = calcSimReturn(bullTarget);
  const simBase = calcSimReturn(baseTarget);
  const simBear = calcSimReturn(bearTarget);

  // Institutional Positioning Estimates (Derived logically from indicators)
  const fiiSentiment = sentiment.positive_ratio && sentiment.positive_ratio > 0.55 
    ? "Bullish Accumulation" 
    : (sentiment.negative_ratio && sentiment.negative_ratio > 0.45 ? "Reduced Exposure" : "Steady Holdings");
    
  const diiSentiment = fundamental.health_score && fundamental.health_score >= 75 
    ? "Strong Buying" 
    : (fundamental.health_score && fundamental.health_score <= 45 ? "Hold Stance" : "Steady Accumulation");

  const overallTrend = fiiSentiment.includes("Bull") && diiSentiment.includes("Strong")
    ? "Increasing Support" 
    : (fiiSentiment.includes("Reduced") ? "Slight Distribution" : "Neutral Balance");

  // Investment Checklist Logic
  const checklistItems = [
    {
      name: "Revenue Growth Expansion",
      status: (fundamental.metrics?.revenue_growth_pct || fundamental.revenue_growth || 0) >= 8.0 ? "Pass" : ((fundamental.metrics?.revenue_growth_pct || fundamental.revenue_growth || 0) > 0.0 ? "Warning" : "Fail"),
      desc: `YoY revenue growth is currently ${(fundamental.metrics?.revenue_growth_pct || fundamental.revenue_growth || 0).toFixed(1)}%`
    },
    {
      name: "Balance Sheet Solvency",
      status: (fundamental.health_score || 50) >= 70 ? "Pass" : ((fundamental.health_score || 50) >= 45 ? "Warning" : "Fail"),
      desc: `Fundamental health score registered at ${fundamental.health_score || 50}/100`
    },
    {
      name: "Price Trend Direction",
      status: technical.trend === "Bullish" ? "Pass" : (technical.trend === "Neutral" ? "Warning" : "Fail"),
      desc: `Technical sub-agent validates primary trend as ${technical.trend || "Neutral"}`
    },
    {
      name: "Valuation Posture",
      status: (fundamental.valuation_score || 50) >= 60 ? "Pass" : ((fundamental.valuation_score || 50) >= 35 ? "Warning" : "Fail"),
      desc: `Valuation attractiveness score sits at ${fundamental.valuation_score || 50}/100`
    },
    {
      name: "Media Narrative Score",
      status: sentiment.sentiment === "Positive" ? "Pass" : (sentiment.sentiment === "Neutral" ? "Warning" : "Fail"),
      desc: `Public news desks and RSS feed sentiment registers as ${sentiment.sentiment || "Neutral"}`
    },
    {
      name: "Support Buffer Zone",
      status: (technical.distance_to_support || 5.0) >= 4.0 ? "Pass" : ((technical.distance_to_support || 5.0) > 1.5 ? "Warning" : "Fail"),
      desc: `Stock is trading ${(technical.distance_to_support || 5.0).toFixed(1)}% above local support floor`
    }
  ];

  const passedCount = checklistItems.filter(item => item.status === "Pass").length;

  // Navigation jumping helper
  const scrollToSection = (id) => {
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  // Upgraded Decision Box properties
  const getInvestmentAction = () => {
    if (bias === "BULLISH" && risk === "LOW") return "Strategic Accumulation on Support Floor";
    if (bias === "BULLISH" && (risk === "MEDIUM" || risk === "HIGH")) return "Opportunistic Accumulation on Dips";
    if (bias === "BEARISH") return "Risk-Off Exposure Reduction";
    return "Hold / Maintain Steady Exposure";
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 text-slate-100">
      
      {/* ── STICKY SIDEBAR NAVIGATION (lg:col-span-3) ── */}
      <aside className="lg:col-span-3 h-fit sticky top-6 hidden lg:block z-10 select-none">
        <div className="bg-[#070913]/90 backdrop-blur border border-white/10 rounded-lg p-4 space-y-2.5">
          <div className="font-mono text-[9px] font-bold text-slate-500 uppercase tracking-widest border-b border-white/5 pb-2 mb-3">
            Terminal Sections
          </div>
          {[
            { id: "thesis", label: "Executive Thesis & Snapshot" },
            { id: "whynow", label: "Timing Trigger (Why Now?)" },
            { id: "chart", label: "Price Action Command Center" },
            { id: "scorecard", label: "Quick Scorecard" },
            { id: "technical", label: "Technical Research Desk" },
            { id: "fundamental", label: "Fundamental Quality Desk" },
            { id: "positioning", label: "Institutional Positioning" },
            { id: "sentiment", label: "News Sentiment Intel" },
            { id: "debate", label: "Debate: Bull vs Bear" },
            { id: "scenarios", label: "Scenario Pathways" },
            { id: "simulation", label: "Returns Capital Simulation" },
            { id: "risks", label: "Risk Register Matrix" },
            { id: "calendar", label: "Catalyst Calendar" },
            { id: "checklist", label: "Investment Checklist" },
            { id: "decision", label: "Upgraded Decision Box" },
            { id: "methodology", label: "Methodology & Telemetry" },
          ].map((item) => (
            <button
              key={item.id}
              onClick={() => scrollToSection(item.id)}
              className={`w-full text-left px-3 py-2 text-xs font-mono font-medium rounded transition-all duration-150 flex items-center gap-2 cursor-pointer ${
                activeSection === item.id 
                  ? "bg-[#FFBA9D] text-black font-bold border-l-2 border-black" 
                  : "text-slate-400 hover:text-white hover:bg-white/5"
              }`}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${
                activeSection === item.id ? "bg-black" : "bg-white/10"
              }`} />
              <span>{item.label}</span>
            </button>
          ))}
        </div>
      </aside>

      {/* ── PRIMARY WORKSPACE (lg:col-span-9) ── */}
      <main className="lg:col-span-9 space-y-12">
        
        {/* ── SECTION 1: EXECUTIVE INVESTMENT THESIS (HERO) ── */}
        <section id="thesis" data-section className="bg-gradient-to-br from-[#0c0e1a] to-[#060810] border border-white/10 rounded-lg p-6 lg:p-8 relative overflow-hidden shadow-2xl">
          <div className="absolute top-0 right-0 w-96 h-96 bg-blue-500/5 rounded-full filter blur-[80px] -z-10" />
          <div className="absolute bottom-0 left-0 w-96 h-96 bg-emerald-500/5 rounded-full filter blur-[80px] -z-10" />
          
          {/* Header row */}
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/5 pb-5 mb-6">
            <div className="space-y-1.5">
              <div className="flex items-center gap-3">
                <h1 className="text-4xl font-extrabold font-sans tracking-tight text-white">{symbol}</h1>
                <span className={`px-2.5 py-0.5 rounded text-[10px] font-bold font-mono border uppercase tracking-wider ${getBiasColor(bias)}`}>
                  {bias} Rating
                </span>
              </div>
              <p className="text-slate-400 text-sm font-medium">
                {stockInfo?.company_name || `${symbol} Corporation`} // Institutional Equity Dossier
              </p>
            </div>

            <div className="flex items-center gap-8 font-mono">
              <div className="text-right">
                <span className="text-[9px] text-slate-500 block uppercase font-bold tracking-wider">MARKET VALUE</span>
                <div className="flex items-baseline gap-1.5 justify-end">
                  <span className="text-3xl font-extrabold text-white">
                    {currencySymbol}{currentPrice.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </span>
                  <span className={`text-sm font-bold ${isUp ? "text-emerald-400" : "text-red-400"}`}>
                    {isUp ? "▲" : "▼"}{changePct.toFixed(2)}%
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Thesis summary block & Research Snapshot side-by-side */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            
            {/* Thesis Summary (Left) */}
            <div className="lg:col-span-8 space-y-4">
              <div className="flex items-center gap-2 text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest">
                <BookOpen size={14} className="text-[#FFBA9D]" />
                <span>Executive Thesis Summary</span>
              </div>
              <p className="text-slate-200 text-sm leading-relaxed font-light bg-slate-950/40 p-4 border border-white/5 rounded-lg whitespace-pre-line">
                {renderFormattedText(finalDecision.summary) || "Institutional multi-agent investment intelligence report. Technical, fundamental, and headline sentiment data sets compiled dynamically."}
              </p>
            </div>

            {/* Research Snapshot Card (Right - Section 1B) */}
            <div className="lg:col-span-4 bg-[#080914] border border-white/15 rounded-lg p-5 flex flex-col justify-between">
              <span className="text-[9px] font-mono text-slate-500 font-bold uppercase tracking-wider block border-b border-white/5 pb-2 mb-3">
                Research Snapshot & Sentiment
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 items-center flex-1">
                {/* Snapshot metrics */}
                <div className="space-y-3 text-xs font-mono">
                  <div className="flex justify-between border-b border-white/5 pb-1">
                    <span className="text-slate-500 font-bold uppercase">Sector</span>
                    <span className="text-white font-bold truncate max-w-[90px]" title={getSector(symbol)}>{getSector(symbol)}</span>
                  </div>
                  <div className="flex justify-between border-b border-white/5 pb-1">
                    <span className="text-slate-500 font-bold uppercase">Mkt Cap</span>
                    <span className="text-white font-bold">{stockInfo?.market_cap || fundamental.metrics?.market_cap || "N/A"}</span>
                  </div>
                  <div className="flex justify-between border-b border-white/5 pb-1">
                    <span className="text-slate-500 font-bold uppercase">Risk</span>
                    <span className={`font-bold ${risk === "HIGH" ? "text-red-400" : risk === "LOW" ? "text-emerald-400" : "text-amber-400"}`}>{risk}</span>
                  </div>
                  <div className="flex justify-between border-b border-white/5 pb-1">
                    <span className="text-slate-500 font-bold uppercase">Horizon</span>
                    <span className="text-emerald-450 text-emerald-400 font-bold">12-18M</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500 font-bold uppercase">Category</span>
                    <span className="text-[#FFBA9D] font-bold">Core</span>
                  </div>
                </div>

                {/* Sentiment Pie/Donut Chart */}
                <div className="flex flex-col items-center justify-center relative h-36">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={[
                          { name: "Positive", value: posVal, fill: "#10b981" },
                          { name: "Negative", value: negVal, fill: "#ef4444" },
                          { name: "Neutral", value: neuVal, fill: "#3b82f6" }
                        ]}
                        cx="50%"
                        cy="50%"
                        innerRadius={28}
                        outerRadius={40}
                        paddingAngle={2}
                        dataKey="value"
                      >
                        <Cell key="cell-0" />
                        <Cell key="cell-1" />
                        <Cell key="cell-2" />
                      </Pie>
                      <Tooltip 
                        contentStyle={{ backgroundColor: "#080914", borderColor: "rgba(255,255,255,0.1)", borderRadius: "6px" }}
                        itemStyle={{ color: "#fff", fontSize: "10px", fontFamily: "monospace" }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="absolute flex flex-col items-center justify-center font-mono">
                    <span className="text-[11px] font-black text-white">{posVal}%</span>
                    <span className="text-[7px] text-slate-500 font-bold uppercase tracking-wider">Bullish</span>
                  </div>
                </div>
              </div>
              
              {/* Sentiment Legend summary */}
              <div className="flex justify-between items-center border-t border-white/5 pt-2 mt-2 font-mono text-[8.5px] text-slate-400">
                <div className="flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                  <span>Bullish: {posVal}%</span>
                </div>
                <div className="flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                  <span>Neutral: {neuVal}%</span>
                </div>
                <div className="flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-red-500" />
                  <span>Bearish: {negVal}%</span>
                </div>
              </div>
            </div>

          </div>
        </section>

        {/* ── SECTION 1C: "WHY NOW?" CATALYST TRIGGER ── */}
        <section id="whynow" data-section className="border-l-4 border-amber-500/60 bg-[#16130b]/20 p-5 rounded-r-lg space-y-2">
          <div className="flex items-center gap-2 text-amber-400 font-mono text-[10px] font-bold uppercase tracking-widest">
            <Zap size={14} className="animate-pulse" />
            <span>TIMING TRIGGER: WHY ATTENTION IS REQUIRED TODAY</span>
          </div>
          <p className="text-slate-300 text-xs leading-relaxed font-light font-sans">
            Timing thresholds indicate high conviction windows. The alignment of <strong className="text-white font-medium">{technical.trend_strength ? technical.trend_strength.toLowerCase() : "moderate"}</strong> technical momentum indicators with a <strong className="text-white font-medium">{sentiment.sentiment ? sentiment.sentiment.toLowerCase() : "neutral"}</strong> sentiment feed suggests <strong className="text-white font-medium">{bias === "BULLISH" ? "opportunistic accumulation buffers" : "defensive reallocation postures"}</strong> should be considered immediately, targeting catalysts tagged under <strong className="text-white font-medium">{sentiment.catalyst_type || "Earnings & Corporate Catalysts"}</strong> timelines.
          </p>
        </section>

        {/* ── SECTION 2: PRICE ACTION COMMAND CENTER ── */}
        <section id="chart" data-section className="bg-[#0a0c16] border border-white/10 rounded-lg p-5 space-y-4">
          <div className="flex flex-wrap justify-between items-center gap-4 border-b border-white/5 pb-3">
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono text-slate-500 font-bold uppercase tracking-widest">SECTION 2 — PRICE ACTION COMMAND CENTER</span>
            </div>

            {/* Bloomberg terminal styling overlays */}
            <div className="flex flex-wrap items-center gap-4 text-xs font-mono text-slate-400">
              <div>
                <span className="text-slate-500 uppercase text-[8.5px] block font-bold">Volume</span>
                <span className="text-white font-bold">{stockInfo?.volume ? stockInfo.volume.toLocaleString() : "N/A"}</span>
              </div>
              <div className="h-6 w-px bg-white/10 hidden sm:block" />
              <div>
                <span className="text-slate-500 uppercase text-[8.5px] block font-bold">RSI (14)</span>
                <span className="text-white font-bold">{technical.rsi_interpretation ? (technical.rsi_interpretation.match(/\d+\.\d+/) || ["50.0"])[0] : "50.0"}</span>
              </div>
              <div className="h-6 w-px bg-white/10 hidden sm:block" />
              <div>
                <span className="text-slate-500 uppercase text-[8.5px] block font-bold">Support Floor</span>
                <span className="text-emerald-400 font-bold">{currencySymbol}{technical.support_level || "N/A"}</span>
              </div>
              <div className="h-6 w-px bg-white/10 hidden sm:block" />
              <div>
                <span className="text-slate-500 uppercase text-[8.5px] block font-bold">Resistance Ceiling</span>
                <span className="text-red-400 font-bold">{currencySymbol}{technical.resistance_level || "N/A"}</span>
              </div>
              <div className="h-6 w-px bg-white/10 hidden sm:block" />
              
              {/* Timeframe buttons */}
              <div className="flex border border-white/10 rounded overflow-hidden">
                {[
                  { label: "15M", value: "15m" },
                  { label: "1H", value: "1h" },
                  { label: "4H", value: "4h" },
                  { label: "1D", value: "1d" },
                  { label: "1W", value: "1w" }
                ].map((tf) => (
                  <button 
                    key={tf.value} 
                    onClick={() => setActiveTimeframe(tf.value)}
                    className={`px-2.5 py-1 text-[9px] font-mono font-bold transition-colors cursor-pointer ${
                      activeTimeframe === tf.value ? "bg-[#FFBA9D] text-black" : "bg-[#05060f] hover:bg-slate-900 text-slate-400"
                    }`}
                  >
                    {tf.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Chart centerpiece (highest prominence) */}
          <div className="relative w-full">
            <TradingViewChart 
              symbol={symbol} 
              timeframeData={stockInfo?.timeframes}
              supportPrice={technical?.support_level}
              resistancePrice={technical?.resistance_level}
              activeTimeframe={activeTimeframe}
              setActiveTimeframe={setActiveTimeframe}
            />
          </div>
        </section>

        {/* ── SECTION 3: QUICK INVESTMENT SCORECARD ── */}
        <section id="scorecard" data-section className="space-y-3">
          <span className="text-[10px] font-mono text-slate-500 font-bold uppercase tracking-widest block">SECTION 3 — QUICK SCORECARD METERS</span>
          
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            
            {/* Card 1: Final AI Market View */}
            <div className="bg-[#0b1020]/65 border border-white/10 rounded-xl p-4 flex flex-col justify-between hover:border-white/20 transition-all duration-300 relative overflow-hidden min-h-[340px]">
              <div className="flex justify-between items-start mb-3">
                <span className="text-[8.5px] font-mono font-bold text-slate-500 uppercase tracking-wider block font-sans">FINAL AI MARKET VIEW</span>
                <span className="px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 text-[7px] font-mono font-bold uppercase border border-blue-500/20">AI OPINION</span>
              </div>
              <div className="my-2">
                <div className={`text-2xl font-black font-mono tracking-wider uppercase ${
                  bias.includes("BULL") ? "text-amber-400" : bias.includes("BEAR") ? "text-red-400" : "text-slate-350"
                }`}>
                  {bias}
                </div>
                <div className="text-[10.5px] font-mono text-slate-400 mt-1 uppercase font-bold tracking-tight">
                  {confidence}% Consensus Confidence
                </div>
              </div>
              <div className="space-y-2 my-3 text-[10px] font-mono text-slate-400">
                <div className="flex justify-between items-center border-b border-white/5 pb-1">
                  <span>TECHNICAL</span>
                  <span className="text-emerald-400 font-bold">+{Math.round((technical.confidence || 70) * 0.45)}</span>
                </div>
                <div className="flex justify-between items-center border-b border-white/5 pb-1">
                  <span>FUNDAMENTAL</span>
                  <span className="text-emerald-400 font-bold">+{Math.round((fundamental.health_score || 80) * 0.45)}</span>
                </div>
                <div className="flex justify-between items-center pb-1">
                  <span>SENTIMENT</span>
                  <span className="text-emerald-400 font-bold">+{Math.round((sentiment.positive_ratio || 0.6) * 45)}</span>
                </div>
              </div>
              <div className="border-t border-white/5 pt-2">
                <div className="flex justify-between items-center text-[9px] font-mono text-slate-500 mb-2">
                  <span>CONSENSUS TREND</span>
                  <span className="text-emerald-400 font-bold flex items-center gap-0.5">▲ +83 PTS (90D)</span>
                </div>
                <div className="w-full h-8 flex items-end">
                  <svg className="w-full h-full text-emerald-400 opacity-80" viewBox="0 0 100 20" fill="none">
                    <path d="M0 16 C15 14, 25 18, 40 10 C55 3, 70 12, 100 4" stroke="currentColor" strokeWidth="1.5" />
                  </svg>
                </div>
              </div>
            </div>

            {/* Card 2: Professional Risk Assessment */}
            {(() => {
              const riskVal = risk === "HIGH" ? 78 : risk === "LOW" ? 24 : 58;
              const volatilityClass = technical.volatility >= 30 ? "bg-red-500" : "bg-amber-500";
              const newsRiskClass = sentiment.negative_ratio >= 0.3 ? "bg-red-500" : "bg-amber-500";
              return (
                <div className="bg-[#0b1020]/65 border border-white/10 rounded-xl p-4 flex flex-col justify-between hover:border-white/20 transition-all duration-300 min-h-[340px]">
                  <div className="flex justify-between items-start mb-3">
                    <span className="text-[8.5px] font-mono font-bold text-slate-500 uppercase tracking-wider block font-sans">PROFESSIONAL RISK ASSESSMENT</span>
                    <span className="px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-400 text-[7px] font-mono font-bold uppercase border border-purple-500/20">RISK ENGINE</span>
                  </div>
                  <div className="my-2 font-mono">
                    <div className="text-2xl font-black text-white">{riskVal}/100</div>
                    <div className={`text-[10px] font-black uppercase mt-1 tracking-wider ${
                      risk === "HIGH" ? "text-red-400" : risk === "LOW" ? "text-emerald-400" : "text-amber-400"
                    }`}>
                      {risk} RISK CATEGORY
                    </div>
                  </div>
                  <div className="space-y-3.5 my-3 text-[10px] font-mono text-slate-400">
                    <div>
                      <div className="flex justify-between mb-1">
                        <span>Volatility</span>
                        <span className="text-white font-bold">{technical.volatility >= 30 ? "High" : "Medium"}</span>
                      </div>
                      <div className="h-1 bg-slate-900 rounded-full overflow-hidden">
                        <div className={`h-full ${volatilityClass}`} style={{ width: technical.volatility >= 30 ? "80%" : "55%" }} />
                      </div>
                    </div>
                    <div>
                      <div className="flex justify-between mb-1">
                        <span>News Risk</span>
                        <span className="text-white font-bold">{sentiment.negative_ratio >= 0.3 ? "High" : "Medium"}</span>
                      </div>
                      <div className="h-1 bg-slate-900 rounded-full overflow-hidden">
                        <div className={`h-full ${newsRiskClass}`} style={{ width: sentiment.negative_ratio >= 0.3 ? "75%" : "50%" }} />
                      </div>
                    </div>
                    <div>
                      <div className="flex justify-between mb-1">
                        <span>Trend Stability</span>
                        <span className="text-white font-bold">{technical.trend === "Neutral" ? "Medium" : "High"}</span>
                      </div>
                      <div className="h-1 bg-slate-900 rounded-full overflow-hidden">
                        <div className="h-full bg-amber-500" style={{ width: technical.trend === "Neutral" ? "50%" : "80%" }} />
                      </div>
                    </div>
                  </div>
                  <div className="border-t border-white/5 pt-2">
                    <span className="text-[8.5px] font-mono text-slate-500 uppercase tracking-wider block mb-2 font-sans">PORTFOLIO RISK ALLOCATION</span>
                    <div className="flex h-2.5 rounded-full overflow-hidden text-[7px] font-bold text-black font-mono">
                      <div className="bg-emerald-500 flex items-center justify-center" style={{ width: "24%" }} title="Low Risk Allocation">Low 24%</div>
                      <div className="bg-amber-500 flex items-center justify-center" style={{ width: "52%" }} title="Med Risk Allocation">Med 52%</div>
                      <div className="bg-red-500 flex items-center justify-center" style={{ width: "24%" }} title="High Risk Allocation">High 24%</div>
                    </div>
                  </div>
                </div>
              );
            })()}

            {/* Card 3: Growth Rating */}
            {(() => {
              const growthScore = fundamental.growth_score || 40;
              const revenueGrowth = (fundamental.metrics?.revenue_growth_pct || fundamental.revenue_growth || 16.5).toFixed(1);
              return (
                <div className="bg-[#0b1020]/65 border border-white/10 rounded-xl p-4 flex flex-col justify-between hover:border-white/20 transition-all duration-300 min-h-[340px]">
                  <div className="flex justify-between items-start mb-3">
                    <span className="text-[8.5px] font-mono font-bold text-slate-500 uppercase tracking-wider block font-sans">GROWTH RATING</span>
                    <span className="px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 text-[7px] font-mono font-bold uppercase border border-emerald-500/20">RESEARCH</span>
                  </div>
                  <div className="my-2 font-mono">
                    <div className="text-2xl font-black text-white">{growthScore}/100</div>
                    <div className="text-[9.5px] text-slate-500 mt-1 uppercase font-bold tracking-tight">
                      Benchmark Ind Avg: 56/100
                    </div>
                  </div>
                  <div className="space-y-3.5 my-3 text-[10px] font-mono text-slate-400">
                    <div>
                      <div className="flex justify-between mb-1 items-baseline">
                        <span>GROWTH OUTLOOK</span>
                        <span className="px-1.5 py-0.2 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 text-[8px] font-black uppercase font-mono tracking-wider">GROWTH</span>
                      </div>
                      <div className={`text-[11.5px] font-bold ${growthScore >= 60 ? "text-emerald-400" : growthScore >= 40 ? "text-amber-400" : "text-red-400"}`}>
                        {growthScore >= 60 ? "▲ Above Average" : "▼ Below Average"}
                      </div>
                    </div>
                    <div>
                      <div className="flex justify-between mb-1">
                        <span>Revenue Growth</span>
                        <span className="text-white font-bold">{revenueGrowth}%</span>
                      </div>
                      <div className="h-1 bg-slate-900 rounded-full overflow-hidden">
                        <div className="h-full bg-cyan-500" style={{ width: `${Math.min(100, Math.max(10, parseFloat(revenueGrowth) * 4))}%` }} />
                      </div>
                    </div>
                    <div>
                      <div className="flex justify-between mb-1">
                        <span>Earnings Growth</span>
                        <span className="text-white font-bold">31.8%</span>
                      </div>
                      <div className="h-1 bg-slate-900 rounded-full overflow-hidden">
                        <div className="h-full bg-cyan-500" style={{ width: "31.8%" }} />
                      </div>
                    </div>
                    <div>
                      <div className="flex justify-between mb-1">
                        <span>Biz Expansion</span>
                        <span className="text-white font-bold">41%</span>
                      </div>
                      <div className="h-1 bg-slate-900 rounded-full overflow-hidden">
                        <div className="h-full bg-cyan-500" style={{ width: "41%" }} />
                      </div>
                    </div>
                  </div>
                  <div className="border-t border-white/5 pt-2">
                    <p className="text-[8.5px] leading-tight font-sans font-light text-slate-550 text-slate-500">
                      Peer-relative YoY growth performance dossier.
                    </p>
                  </div>
                </div>
              );
            })()}

            {/* Card 4: Valuation Safety */}
            {(() => {
              const valScore = fundamental.valuation_score || 60;
              const valLabel = valScore >= 70 ? "Undervalued" : valScore >= 45 ? "Fairly Valued" : "Overvalued";
              return (
                <div className="bg-[#0b1020]/65 border border-white/10 rounded-xl p-4 flex flex-col justify-between hover:border-white/20 transition-all duration-300 min-h-[340px]">
                  <div className="flex justify-between items-start mb-3">
                    <span className="text-[8.5px] font-mono font-bold text-slate-500 uppercase tracking-wider block font-sans">VALUATION SAFETY</span>
                    <span className="px-1.5 py-0.5 rounded bg-orange-500/10 text-orange-400 text-[7px] font-mono font-bold uppercase border border-orange-500/20">SAFETY</span>
                  </div>
                  <div className="my-2 font-mono">
                    <div className="text-2xl font-black text-white">{valScore}/100</div>
                    <div className="text-[9.5px] text-slate-500 mt-1 uppercase font-bold tracking-tight">
                      Benchmark Ind Avg: 55/100
                    </div>
                  </div>
                  <div className="space-y-3.5 my-3 text-[10px] font-mono text-slate-400">
                    <div>
                      <div className="flex justify-between mb-1 items-baseline">
                        <span>VALUATION QUALITY</span>
                        <span className="px-1.5 py-0.2 rounded bg-orange-500/10 text-orange-400 border border-orange-500/20 text-[8px] font-black uppercase font-mono tracking-wider">VALUE</span>
                      </div>
                      <div className="text-[11.5px] font-bold text-orange-400">
                        {valLabel}
                      </div>
                    </div>
                    <div>
                      <div className="flex justify-between mb-1">
                        <span>PE vs Industry</span>
                        <span className="text-white font-bold">40%</span>
                      </div>
                      <div className="h-1 bg-slate-900 rounded-full overflow-hidden">
                        <div className="h-full bg-orange-500" style={{ width: "40%" }} />
                      </div>
                    </div>
                    <div>
                      <div className="flex justify-between mb-1">
                        <span>Fair Value Gap</span>
                        <span className="text-white font-bold">63%</span>
                      </div>
                      <div className="h-1 bg-slate-900 rounded-full overflow-hidden">
                        <div className="h-full bg-orange-500" style={{ width: "63%" }} />
                      </div>
                    </div>
                    <div>
                      <div className="flex justify-between mb-1">
                        <span>Downside Buffer</span>
                        <span className="text-white font-bold">75%</span>
                      </div>
                      <div className="h-1 bg-slate-900 rounded-full overflow-hidden">
                        <div className="h-full bg-orange-500" style={{ width: "75%" }} />
                      </div>
                    </div>
                  </div>
                  <div className="border-t border-white/5 pt-2">
                    <p className="text-[8.5px] leading-tight font-sans font-light text-slate-550 text-slate-500">
                      Margin of safety vs peer group earnings bounds.
                    </p>
                  </div>
                </div>
              );
            })()}

            {/* Card 5: Tech Momentum */}
            {(() => {
              const momScore = technical.confidence || 70;
              const trendStr = technical.trend_strength || "Strong Momentum";
              return (
                <div className="bg-[#0b1020]/65 border border-white/10 rounded-xl p-4 flex flex-col justify-between hover:border-white/20 transition-all duration-300 min-h-[340px]">
                  <div className="flex justify-between items-start mb-3">
                    <span className="text-[8.5px] font-mono font-bold text-slate-550 uppercase tracking-wider block font-sans">TECH MOMENTUM</span>
                    <span className="px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 text-[7px] font-mono font-bold uppercase border border-blue-500/20">MOMENTUM</span>
                  </div>
                  <div className="my-2 font-mono">
                    <div className="text-2xl font-black text-white">{momScore}/100</div>
                    <div className="text-[9.5px] text-slate-500 mt-1 uppercase font-bold tracking-tight">
                      Benchmark Mkt Avg: 58/100
                    </div>
                  </div>
                  <div className="space-y-3.5 my-3 text-[10px] font-mono text-slate-400">
                    <div>
                      <div className="flex justify-between mb-1 items-baseline">
                        <span>MOMENTUM PHASE</span>
                        <span className="px-1.5 py-0.2 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20 text-[8px] font-black uppercase font-mono tracking-wider">TREND</span>
                      </div>
                      <div className="text-[11.5px] font-bold text-emerald-450 text-emerald-400">
                        ▲ {trendStr}
                      </div>
                    </div>
                    <div>
                      <div className="flex justify-between mb-1">
                        <span>Trend Strength</span>
                        <span className="text-white font-bold">65%</span>
                      </div>
                      <div className="h-1 bg-slate-900 rounded-full overflow-hidden">
                        <div className="h-full bg-blue-500" style={{ width: "65%" }} />
                      </div>
                    </div>
                    <div>
                      <div className="flex justify-between mb-1">
                        <span>RSI Position</span>
                        <span className="text-white font-bold">51%</span>
                      </div>
                      <div className="h-1 bg-slate-900 rounded-full overflow-hidden">
                        <div className="h-full bg-blue-500" style={{ width: "51%" }} />
                      </div>
                    </div>
                    <div>
                      <div className="flex justify-between mb-1">
                        <span>Acceleration</span>
                        <span className="text-white font-bold">75%</span>
                      </div>
                      <div className="h-1 bg-slate-900 rounded-full overflow-hidden">
                        <div className="h-full bg-blue-500" style={{ width: "75%" }} />
                      </div>
                    </div>
                  </div>
                  <div className="border-t border-white/5 pt-2">
                    <p className="text-[8.5px] leading-tight font-sans font-light text-slate-550 text-slate-500">
                      RSI speed and MACD histogram trend status.
                    </p>
                  </div>
                </div>
              );
            })()}
          </div>
        </section>

        {/* ── SECTION 4 & 5: TECHNICAL & FUNDAMENTAL REPORTS (INLINE DESKS) ── */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          
          {/* SECTION 4 — TECHNICAL RESEARCH DESK */}
          <section id="technical" data-section className="bg-[#0a0c16] border border-white/10 rounded-lg p-5 space-y-4">
            <div className="border-b border-white/5 pb-3 flex justify-between items-center">
              <span className="text-[10px] font-mono text-slate-500 font-bold uppercase tracking-widest block">SECTION 4 — TECHNICAL RESEARCH DESK</span>
              <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 text-[8px] font-mono font-bold uppercase border border-emerald-500/20">Active Desk</span>
            </div>

            <div className="space-y-4 font-sans text-xs">
              <div className="grid grid-cols-2 gap-4 font-mono">
                <div className="bg-slate-950/40 border border-white/5 rounded p-3">
                  <span className="text-slate-500 uppercase text-[8px] font-bold block">Trend Strength</span>
                  <span className="text-white font-bold block mt-1">{technical.trend_strength || "Moderate"}</span>
                </div>
                <div className="bg-slate-950/40 border border-white/5 rounded p-3">
                  <span className="text-slate-500 uppercase text-[8px] font-bold block">Volatility Index</span>
                  <span className="text-white font-bold block mt-1">
                    {technical.volatility ? `${technical.volatility}%` : "N/A"}
                  </span>
                </div>
              </div>

              {/* Analysis details */}
              <div className="space-y-3.5">
                <div className="space-y-1">
                  <span className="font-mono text-[8.5px] font-bold uppercase text-slate-500 tracking-wide block">RSI Interpretation</span>
                  <p className="text-slate-300 leading-relaxed font-light">{technical.rsi_interpretation || "RSI momentum sits at standard neutral levels, indicating consolidative trading range."}</p>
                </div>

                <div className="space-y-1">
                  <span className="font-mono text-[8.5px] font-bold uppercase text-slate-500 tracking-wide block">MACD Interpretation</span>
                  <p className="text-slate-300 leading-relaxed font-light">{technical.macd_interpretation || "MACD reflects flat histogram lines with signal intersections indicating sideways drift."}</p>
                </div>

                <div className="space-y-1">
                  <span className="font-mono text-[8.5px] font-bold uppercase text-slate-500 tracking-wide block">Moving Average Analysis</span>
                  <p className="text-slate-300 leading-relaxed font-light">{technical.moving_average_analysis || "Trading price floats relative to key exponential channels, testing historical support parameters."}</p>
                </div>

                {/* Timeframe block */}
                <div className="space-y-1">
                  <span className="font-mono text-[8.5px] font-bold uppercase text-slate-500 tracking-wide block">Multi-Timeframe Outlook</span>
                  <div className="grid grid-cols-5 gap-2 text-center font-mono text-[9px] pt-1">
                    {Object.entries(technical.timeframe_analysis || { "15m": "Neutral", "1h": "Neutral", "4h": "Neutral", "1d": "Neutral", "1w": "Neutral" }).map(([tf, tfTrend]) => (
                      <div key={tf} className="bg-slate-950/60 border border-white/5 p-1 rounded">
                        <span className="text-slate-500 block font-bold uppercase text-[7px]">{tf}</span>
                        <span className={`font-black ${
                          tfTrend.includes("Bull") ? "text-emerald-400" : tfTrend.includes("Bear") ? "text-red-400" : "text-amber-400"
                        }`}>{tfTrend}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="bg-[#05060c] border border-[#ffb99d]/10 rounded-lg p-3 mt-2">
                  <span className="font-mono text-[8.5px] font-bold uppercase text-[#FFBA9D] tracking-wide block mb-1">Key Technical Conclusion</span>
                  <p className="text-slate-300 leading-relaxed text-xs font-light">{technical.key_technical_conclusion || "Technical analysis signals consolidative posture."}</p>
                </div>
              </div>
            </div>
          </section>

          {/* SECTION 5 — FUNDAMENTAL QUALITY DESK */}
          <section id="fundamental" data-section className="bg-[#0a0c16] border border-white/10 rounded-lg p-5 space-y-4">
            <div className="border-b border-white/5 pb-3 flex justify-between items-center">
              <span className="text-[10px] font-mono text-slate-500 font-bold uppercase tracking-widest block">SECTION 5 — FUNDAMENTAL QUALITY DESK</span>
              <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 text-[8px] font-mono font-bold uppercase border border-emerald-500/20">Active Desk</span>
            </div>

            <div className="space-y-4 font-sans text-xs">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 font-mono">
                {[
                  { label: "Rev Growth", val: fundamental.metrics?.revenue_growth_pct ? `${fundamental.metrics.revenue_growth_pct}%` : "N/A" },
                  { label: "Net Income", val: fundamental.metrics?.net_income ? `${currencySymbol}${(fundamental.metrics.net_income / 1e9).toFixed(1)}B` : "N/A" },
                  { label: "Market Cap", val: fundamental.metrics?.market_cap || "N/A" },
                  { label: "P/E Ratio", val: fundamental.metrics?.pe_ratio ? `${fundamental.metrics.pe_ratio}x` : "N/A" }
                ].map((m, i) => (
                  <div key={i} className="bg-slate-950/40 border border-white/5 rounded p-2 text-center">
                    <span className="text-slate-500 uppercase text-[7px] font-bold block">{m.label}</span>
                    <span className="text-white font-bold block mt-1 text-xs">{m.val}</span>
                  </div>
                ))}
              </div>

              {/* Growth and Valuation text */}
              <div className="space-y-3.5">
                <div className="space-y-1">
                  <span className="font-mono text-[8.5px] font-bold uppercase text-slate-500 tracking-wide block">Growth Outlook</span>
                  <p className="text-slate-300 leading-relaxed font-light">{fundamental.growth_outlook || "Stable market expansions indicate steady growth outlook."}</p>
                </div>

                <div className="space-y-1">
                  <span className="font-mono text-[8.5px] font-bold uppercase text-slate-500 tracking-wide block">Valuation Outlook</span>
                  <p className="text-slate-300 leading-relaxed font-light">{fundamental.valuation_outlook || "Trading multiples suggest standard relative valuation metrics."}</p>
                </div>

                {/* Strengths & Weaknesses */}
                <div className="grid grid-cols-2 gap-4 border-t border-white/5 pt-3">
                  <div className="space-y-1.5">
                    <span className="font-mono text-[8px] font-bold uppercase text-slate-500 block">Solvency Strengths</span>
                    <ul className="space-y-1 text-[9.5px] text-emerald-450 text-emerald-400 font-mono">
                      {fundamental.strengths ? fundamental.strengths.slice(0, 2).map((st, i) => (
                        <li key={i} className="flex gap-1 items-start">
                          <span className="font-bold">✓</span>
                          <span className="text-slate-300 leading-tight">{st}</span>
                        </li>
                      )) : <li>Solvent metrics</li>}
                    </ul>
                  </div>

                  <div className="space-y-1.5">
                    <span className="font-mono text-[8px] font-bold uppercase text-slate-500 block">Solvency Risks</span>
                    <ul className="space-y-1 text-[9.5px] text-red-400 font-mono">
                      {fundamental.weaknesses ? fundamental.weaknesses.slice(0, 2).map((wk, i) => (
                        <li key={i} className="flex gap-1 items-start">
                          <span className="font-bold">✗</span>
                          <span className="text-slate-300 leading-tight">{wk}</span>
                        </li>
                      )) : <li>Premium pricing risks</li>}
                    </ul>
                  </div>
                </div>

                <div className="bg-[#05060c] border border-blue-500/10 rounded-lg p-3 mt-2">
                  <span className="font-mono text-[8.5px] font-bold uppercase text-cyan-400 tracking-wide block mb-1">Corporate audit commentary</span>
                  <p className="text-slate-300 leading-relaxed text-xs font-light">{fundamental.ai_commentary || "Solvency analysis suggests solid financial posture."}</p>
                </div>
              </div>
            </div>
          </section>

        </div>

        {/* ── SECTION 6: INSTITUTIONAL POSITIONING ESTIMATE ── */}
        <section id="positioning" data-section className="bg-[#0a0c16] border border-white/10 rounded-lg p-5 space-y-4">
          <div className="border-b border-white/5 pb-3">
            <span className="text-[10px] font-mono text-slate-500 font-bold uppercase tracking-widest block">SECTION 6 — INSTITUTIONAL POSITIONING ESTIMATE</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-5 text-xs font-mono">
            <div className="bg-slate-950/40 border border-white/5 rounded-lg p-4 space-y-2.5">
              <span className="text-slate-500 font-bold uppercase text-[8px] block">Foreign Institutional Sentiment (FII)</span>
              <div className="flex justify-between items-baseline">
                <span className="text-white font-extrabold text-sm">{fiiSentiment}</span>
              </div>
              <div className="h-1.5 bg-slate-900 rounded-full overflow-hidden mt-1">
                <div className={`h-full ${fiiSentiment.includes("Acc") ? "bg-emerald-500" : "bg-amber-500"}`} style={{ width: fiiSentiment.includes("Acc") ? "80%" : "50%" }} />
              </div>
            </div>

            <div className="bg-slate-950/40 border border-white/5 rounded-lg p-4 space-y-2.5">
              <span className="text-slate-500 font-bold uppercase text-[8px] block">Domestic Institutional Sentiment (DII)</span>
              <div className="flex justify-between items-baseline">
                <span className="text-white font-extrabold text-sm">{diiSentiment}</span>
              </div>
              <div className="h-1.5 bg-slate-900 rounded-full overflow-hidden mt-1">
                <div className={`h-full ${diiSentiment.includes("Strong") ? "bg-emerald-500" : "bg-amber-500"}`} style={{ width: diiSentiment.includes("Strong") ? "85%" : "60%" }} />
              </div>
            </div>

            <div className="bg-slate-950/40 border border-white/5 rounded-lg p-4 space-y-2.5">
              <span className="text-slate-500 font-bold uppercase text-[8px] block">Overall Positioning Trend</span>
              <div className="flex justify-between items-baseline">
                <span className="text-[#FFBA9D] font-extrabold text-sm">{overallTrend}</span>
              </div>
              <div className="h-1.5 bg-slate-900 rounded-full overflow-hidden mt-1">
                <div className="h-full bg-[#FFBA9D]" style={{ width: "70%" }} />
              </div>
            </div>
          </div>

          <div className="text-[10px] text-slate-500 font-mono leading-relaxed pt-1">
            *Note: Institutional positioning values are estimates derived from sub-agent data convergence and relative valuations (actual flow records are simulated).
          </div>
        </section>

        {/* ── SECTION 7: NEWS & SENTIMENT INTELLIGENCE ── */}
        <section id="sentiment" data-section className="bg-[#0a0c16] border border-white/10 rounded-lg p-5 space-y-4">
          <div className="border-b border-white/5 pb-3">
            <span className="text-[10px] font-mono text-slate-500 font-bold uppercase tracking-widest block">SECTION 7 — NEWS & SENTIMENT INTELLIGENCE</span>
          </div>

          {/* Intelligence feed cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-2 font-mono text-xs">
            <div className="bg-slate-950/40 border border-white/5 rounded-lg p-3 space-y-1">
              <span className="text-slate-500 text-[8px] font-bold uppercase block">Catalyst Type</span>
              <span className="text-white font-bold block">{sentiment.catalyst_type || "Market Narrative"}</span>
            </div>

            <div className="bg-slate-950/40 border border-white/5 rounded-lg p-3 space-y-1">
              <span className="text-slate-500 text-[8px] font-bold uppercase block">Most Important Event</span>
              <span className="text-[#FFBA9D] font-bold block truncate">{sentiment.most_important_event || "General news updates."}</span>
            </div>

            <div className="bg-slate-950/40 border border-white/5 rounded-lg p-3 space-y-1">
              <span className="text-slate-500 text-[8px] font-bold uppercase block">Market Narrative</span>
              <span className="text-white font-bold block truncate">{sentiment.market_narrative || "Consolidative consensus."}</span>
            </div>
          </div>

          {/* AI news summary */}
          <div className="bg-[#05060c] border border-white/5 rounded-lg p-4 text-xs font-sans">
            <span className="font-mono text-[8.5px] font-bold uppercase text-slate-500 tracking-wide block mb-1">AI News Summary</span>
            <p className="text-slate-350 leading-relaxed font-light">{sentiment.ai_news_summary || sentiment.summary || "No recent news digests generated."}</p>
          </div>

          {/* Real-time news feed */}
          <div className="space-y-3 font-sans text-xs">
            <span className="font-mono text-[8.5px] font-bold uppercase text-slate-500 tracking-wide block">Real-Time News Stream</span>
            
            <div className="space-y-3 max-h-[300px] overflow-y-auto pr-2">
              {sentiment.articles && sentiment.articles.length > 0 ? (
                sentiment.articles.map((art, idx) => {
                  const isPos = art.sentiment === "positive";
                  const isNeg = art.sentiment === "negative";
                  
                  return (
                    <div key={idx} className="flex justify-between items-start gap-5 py-2.5 border-b border-white/5 last:border-0 hover:bg-white/1 rounded px-1 transition-all duration-200">
                      <div className="space-y-1 w-full">
                        <a 
                          href={art.link} 
                          target="_blank" 
                          rel="noopener noreferrer" 
                          className="text-white font-bold hover:text-[#FFBA9D] leading-relaxed text-[11.5px] flex items-center gap-1"
                        >
                          <span>{art.title}</span>
                          <ExternalLink size={10} className="opacity-40 hover:opacity-100 shrink-0" />
                        </a>
                        <div className="flex items-center gap-2 text-[8.5px] text-slate-500 font-mono font-bold uppercase">
                          <span className="text-slate-400">{art.source}</span>
                          <span>•</span>
                          <span>{art.publish_time}</span>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 shrink-0 font-mono text-[9px]">
                        <span className={`px-2 py-0.5 rounded text-[9px] font-black tracking-wide ${
                          isPos ? "text-emerald-400 bg-emerald-500/10 border border-emerald-500/25" : isNeg ? "text-red-400 bg-red-500/10 border border-red-500/25" : "text-slate-400 bg-slate-800"
                        }`}>
                          {art.sentiment ? art.sentiment.toUpperCase() : "NEUTRAL"}
                        </span>
                      </div>
                    </div>
                  );
                })
              ) : (
                <p className="text-slate-500 font-mono py-2">No news items cataloged.</p>
              )}
            </div>
          </div>
        </section>

        {/* ── SECTION 8: BULL CASE VS BEAR CASE ── */}
        <section id="debate" data-section className="space-y-3">
          <span className="text-[10px] font-mono text-slate-500 font-bold uppercase tracking-widest block">SECTION 8 — DEBATE: BULL CASE VS BEAR CASE</span>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* BULL CASE */}
            <div className="bg-[#0a0c16] border border-emerald-500/20 rounded-lg p-5 space-y-4 relative">
              <div className="absolute top-0 right-0 w-24 h-24 bg-emerald-500/5 rounded-full filter blur-xl" />
              <div className="flex items-center gap-2 border-b border-white/5 pb-3">
                <TrendingUp size={16} className="text-emerald-400" />
                <h3 className="text-white font-black font-mono tracking-wider uppercase text-sm">Why Bulls Are Right</h3>
              </div>
              <ul className="space-y-3 text-xs leading-relaxed text-slate-300 font-sans font-light">
                {bullCase.map((point, idx) => (
                  <li key={idx} className="flex gap-2.5 items-start">
                    <span className="text-emerald-400 font-mono font-bold mt-0.5 shrink-0">0{idx + 1}.</span>
                    <span>{point}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* BEAR CASE */}
            <div className="bg-[#0a0c16] border border-red-500/20 rounded-lg p-5 space-y-4 relative">
              <div className="absolute top-0 right-0 w-24 h-24 bg-red-500/5 rounded-full filter blur-xl" />
              <div className="flex items-center gap-2 border-b border-white/5 pb-3">
                <TrendingDown size={16} className="text-red-400" />
                <h3 className="text-white font-black font-mono tracking-wider uppercase text-sm">Why Bears Are Right</h3>
              </div>
              <ul className="space-y-3 text-xs leading-relaxed text-slate-300 font-sans font-light">
                {bearCase.map((point, idx) => (
                  <li key={idx} className="flex gap-2.5 items-start">
                    <span className="text-red-400 font-mono font-bold mt-0.5 shrink-0">0{idx + 1}.</span>
                    <span>{point}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>

        {/* ── SECTION 9: SCENARIO PATHWAYS (SCENARIO ANALYSIS) ── */}
        <section id="scenarios" data-section className="bg-[#0a0c16] border border-white/10 rounded-lg p-5 space-y-4">
          <div className="border-b border-white/5 pb-3">
            <span className="text-[10px] font-mono text-slate-500 font-bold uppercase tracking-widest block">SECTION 9 — DYNAMIC SCENARIO PATHWAYS</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-5 font-mono text-xs">
            {/* Bull Case */}
            <div className="bg-[#050c08] border border-emerald-500/10 rounded-lg p-4 space-y-3">
              <span className="text-slate-500 font-bold block uppercase text-[8.5px]">Bull Scenario</span>
              <div className="flex justify-between items-baseline border-b border-white/5 pb-2">
                <span className="text-emerald-400 font-black text-lg">{currencySymbol}{bullTarget.toFixed(2)}</span>
                <span className="text-slate-400">{bullProb}% Probability</span>
              </div>
              <p className="text-slate-350 font-sans text-xs leading-relaxed font-light">
                **Trigger:** Accelerated enterprise rollouts, supply chains hitting yield capacity, and multiple expansions driven by sector growth.
              </p>
            </div>

            {/* Base Case */}
            <div className="bg-slate-950/40 border border-white/5 rounded-lg p-4 space-y-3">
              <span className="text-slate-500 font-bold block uppercase text-[8.5px]">Base Scenario</span>
              <div className="flex justify-between items-baseline border-b border-white/5 pb-2">
                <span className="text-white font-black text-lg">{currencySymbol}{baseTarget.toFixed(2)}</span>
                <span className="text-slate-400">{baseProb}% Probability</span>
              </div>
              <p className="text-slate-350 font-sans text-xs leading-relaxed font-light">
                **Trigger:** Continuation of stable hardware margins and client purchase volumes in key territories.
              </p>
            </div>

            {/* Bear Case */}
            <div className="bg-[#0c0505] border border-red-500/10 rounded-lg p-4 space-y-3">
              <span className="text-slate-500 font-bold block uppercase text-[8.5px]">Bear Scenario</span>
              <div className="flex justify-between items-baseline border-b border-white/5 pb-2">
                <span className="text-red-400 font-black text-lg">{currencySymbol}{bearTarget.toFixed(2)}</span>
                <span className="text-slate-400">{bearProb}% Probability</span>
              </div>
              <p className="text-slate-350 font-sans text-xs leading-relaxed font-light">
                **Trigger:** Multiple compression risks due to global trade curbstones and custom cloud ASIC market dilution.
              </p>
            </div>
          </div>
        </section>

        {/* ── SECTION 10: Simplified Capital Simulation ── */}
        <section id="simulation" data-section className="bg-[#0a0c16] border border-white/10 rounded-lg p-5 space-y-4">
          <div className="border-b border-white/5 pb-3 flex flex-wrap justify-between items-center gap-4">
            <div>
              <span className="text-[10px] font-mono text-slate-500 font-bold uppercase tracking-widest block">SECTION 10 — RETURNS CAPITAL SIMULATION</span>
            </div>
            {/* Capital buttons */}
            <div className="flex border border-white/10 rounded overflow-hidden">
              {[10000, 50000, 100000].map((amt) => (
                <button 
                  key={amt} 
                  onClick={() => setSimCapital(amt)}
                  className={`px-3 py-1 text-[9.5px] font-mono font-bold transition-colors cursor-pointer ${
                    simCapital === amt ? "bg-amber-400 text-black" : "bg-[#05060f] hover:bg-slate-900 text-slate-400"
                  }`}
                >
                  {currencySymbol}{amt.toLocaleString()}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-5 font-mono text-xs">
            <div className="border border-white/5 bg-slate-950/20 rounded p-4 text-center">
              <span className="text-slate-500 font-bold uppercase text-[8px] block mb-1">Bull Target Payout</span>
              <span className="text-emerald-400 text-xl font-bold block">{currencySymbol}{simBull.value}</span>
              <span className="text-emerald-500 text-[10px] block mt-1 font-bold">+{simBull.pct}% Return</span>
            </div>

            <div className="border border-white/5 bg-slate-950/20 rounded p-4 text-center">
              <span className="text-slate-500 font-bold uppercase text-[8px] block mb-1">Base Target Payout</span>
              <span className="text-white text-xl font-bold block">{currencySymbol}{simBase.value}</span>
              <span className="text-slate-350 text-[10px] block mt-1 font-bold">+{simBase.pct}% Return</span>
            </div>

            <div className="border border-white/5 bg-slate-950/20 rounded p-4 text-center">
              <span className="text-slate-500 font-bold uppercase text-[8px] block mb-1">Bear Target Payout</span>
              <span className="text-red-400 text-xl font-bold block">{currencySymbol}{simBear.value}</span>
              <span className="text-red-500 text-[10px] block mt-1 font-bold">{simBear.isLoss ? "" : "+"}{simBear.pct}% Return</span>
            </div>
          </div>
        </section>

        {/* ── SECTION 11: RISK REGISTER ── */}
        <section id="risks" data-section className="bg-[#0a0c16] border border-white/10 rounded-lg p-5 space-y-4">
          <div className="border-b border-white/5 pb-3">
            <span className="text-[10px] font-mono text-slate-500 font-bold uppercase tracking-widest block">SECTION 11 — RISK REGISTER MATRIX</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-xs border-collapse">
              <thead>
                <tr className="border-b border-white/10 text-slate-500 uppercase tracking-wider font-bold">
                  <th className="py-2.5 pr-4">Risk Category</th>
                  <th className="py-2.5 px-4 text-center">Severity</th>
                  <th className="py-2.5 px-4 text-center">Probability</th>
                  <th className="py-2.5 pl-4 w-[60%]">Detailed Explanation</th>
                </tr>
              </thead>
              <tbody>
                {riskRegister.map((r, i) => (
                  <tr key={i} className="border-b border-white/5 last:border-0 hover:bg-white/1">
                    <td className="py-3 pr-4 font-bold text-white whitespace-nowrap">{r.category}</td>
                    <td className="py-3 px-4 text-center">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        r.severity === "High" ? "bg-red-500/10 text-red-400 border border-red-500/20" : r.severity === "Low" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                      }`}>
                        {r.severity}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        r.probability === "High" ? "bg-red-500/10 text-red-400 border border-red-500/20" : r.probability === "Low" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                      }`}>
                        {r.probability}
                      </span>
                    </td>
                    <td className="py-3 pl-4 text-slate-300 font-sans font-light text-xs leading-normal">{r.explanation}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* ── SECTION 12: CATALYST CALENDAR ── */}
        <section id="calendar" data-section className="bg-[#0a0c16] border border-white/10 rounded-lg p-5 space-y-4">
          <div className="border-b border-white/5 pb-3">
            <span className="text-[10px] font-mono text-slate-500 font-bold uppercase tracking-widest block">SECTION 12 — CATALYST CALENDAR</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-xs border-collapse">
              <thead>
                <tr className="border-b border-white/10 text-slate-500 uppercase tracking-wider font-bold">
                  <th className="py-2.5 pr-4">Upcoming Event</th>
                  <th className="py-2.5 px-4">Expected Date</th>
                  <th className="py-2.5 px-4 text-center">Importance</th>
                  <th className="py-2.5 pl-4 w-[50%]">Potential Market Impact</th>
                </tr>
              </thead>
              <tbody>
                {catalystCalendar.map((c, i) => (
                  <tr key={i} className="border-b border-white/5 last:border-0 hover:bg-white/1">
                    <td className="py-3 pr-4 font-bold text-white whitespace-nowrap flex items-center gap-2">
                      <Calendar size={13} className="text-orange-400 shrink-0" />
                      <span>{c.event}</span>
                    </td>
                    <td className="py-3 px-4 text-slate-300 font-sans whitespace-nowrap">
                      {c.expected_date ? c.expected_date.toString() : ""}
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        c.importance === "High" ? "bg-red-500/10 text-red-400 border border-red-500/20" : c.importance === "Low" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                      }`}>
                        {c.importance}
                      </span>
                    </td>
                    <td className="py-3 pl-4 text-slate-300 font-sans font-light text-xs leading-normal">{c.potential_impact}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* ── SECTION 13: INVESTMENT CHECKLIST ── */}
        <section id="checklist" data-section className="bg-[#0a0c16] border border-white/10 rounded-lg p-5 space-y-4">
          <div className="border-b border-white/5 pb-3 flex justify-between items-center">
            <span className="text-[10px] font-mono text-slate-500 font-bold uppercase tracking-widest block">SECTION 13 — INVESTMENT CHECKLIST</span>
            <span className="font-mono text-xs font-extrabold text-[#FFBA9D]">{passedCount} / 6 Passed</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 font-sans text-xs">
            {checklistItems.map((item, idx) => (
              <div key={idx} className="flex items-start justify-between bg-slate-950/40 border border-white/5 rounded-lg p-3">
                <div className="space-y-1 pr-4">
                  <div className="font-mono font-bold text-white text-xs flex items-center gap-1.5">
                    <CheckSquare size={13} className="text-slate-400 shrink-0" />
                    <span>{item.name}</span>
                  </div>
                  <p className="text-slate-400 text-[10.5px] leading-tight font-light">{item.desc}</p>
                </div>

                <span className={`px-2.5 py-0.5 rounded font-mono text-[9px] font-black uppercase shrink-0 ${
                  item.status === "Pass" 
                    ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/25" 
                    : (item.status === "Warning" ? "bg-amber-500/15 text-amber-400 border border-amber-500/25" : "bg-red-500/15 text-red-400 border border-red-500/25")
                }`}>
                  {item.status}
                </span>
              </div>
            ))}
          </div>
        </section>

        {/* ── SECTION 14: UPGRADED DECISION BOX (DECISION BOX - THIRD PRIORITY) ── */}
        <section id="decision" data-section className="bg-gradient-to-r from-slate-950 via-[#0e1121] to-slate-950 border-2 border-[#FFBA9D]/30 rounded-lg p-6 relative shadow-2xl">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-48 h-px bg-gradient-to-r from-transparent via-[#FFBA9D] to-transparent" />
          
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
            {/* Rating Circle Gauge */}
            <div className="lg:col-span-3 flex flex-col items-center justify-center text-center">
              <span className="text-[10px] font-mono text-slate-500 font-bold uppercase tracking-wider mb-2">DECISION VERDICT</span>
              
              <div className="relative w-28 h-28 flex items-center justify-center mb-2">
                <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
                  <circle cx="50" cy="50" r="42" stroke="rgba(255,255,255,0.02)" strokeWidth="6" fill="transparent" />
                  <circle cx="50" cy="50" r="42" stroke="#ffb99d" strokeWidth="6" fill="transparent" strokeDasharray="263.8" strokeDashoffset={263.8 - (confidence / 100) * 263.8} strokeLinecap="round" />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center font-mono">
                  <span className="text-2xl font-black text-white leading-none">{confidence}%</span>
                  <span className="text-[7px] text-slate-500 font-bold uppercase tracking-wider mt-1">Concurrence</span>
                </div>
              </div>

              <span className={`text-lg font-black font-mono tracking-widest uppercase ${
                bias.includes("BULL") ? "text-emerald-400" : bias.includes("BEAR") ? "text-red-400" : "text-amber-400"
              }`}>
                {bias}
              </span>
            </div>

            {/* Upgraded Parameters */}
            <div className="lg:col-span-9 space-y-4 font-mono text-xs">
              <div className="flex items-center gap-2 border-b border-white/5 pb-2 text-xs font-bold text-[#FFBA9D] uppercase tracking-wider">
                <Award size={14} />
                <span>Investment Decision Parameters</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <span className="text-slate-500 font-bold text-[8px] uppercase">Investment Action</span>
                  <span className="text-white font-extrabold block text-sm">{getInvestmentAction()}</span>
                </div>
                <div className="space-y-1">
                  <span className="text-slate-500 font-bold text-[8px] uppercase">Suggested Horizon</span>
                  <span className="text-white font-extrabold block text-sm">12 - 18 Months</span>
                </div>
                <div className="space-y-1 border-t border-white/5 pt-2">
                  <span className="text-slate-500 font-bold text-[8px] uppercase">Primary Driver</span>
                  <span className="text-white font-bold block leading-relaxed font-sans font-light">
                    {finalDecision.key_drivers ? finalDecision.key_drivers[0] : "Catalyst integrations active."}
                  </span>
                </div>
                <div className="space-y-1 border-t border-white/5 pt-2">
                  <span className="text-slate-500 font-bold text-[8px] uppercase">Primary Risk</span>
                  <span className="text-white font-bold block leading-relaxed font-sans font-light">
                    {finalDecision.potential_risks ? finalDecision.potential_risks[0] : "Premium pricing risk."}
                  </span>
                </div>
                <div className="space-y-1 border-t border-white/5 pt-2 md:col-span-2">
                  <span className="text-slate-500 font-bold text-[8px] uppercase">Next Review Trigger</span>
                  <span className="text-white font-bold block">
                    Quarterly earnings update or key support boundary breach at {currencySymbol}{technical.support_level || "N/A"}.
                  </span>
                </div>
              </div>

              <div className="bg-slate-950/80 border border-white/5 rounded p-3 mt-2 font-sans text-xs">
                <span className="font-mono text-[8px] font-bold uppercase text-slate-500 tracking-wide block mb-1">Final Verdict Statement</span>
                <p className="text-slate-200 leading-relaxed font-light">
                  {finalDecision.summary}
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* ── SECTION 15: METHODOLOGY & DATA SOURCES (ACCORDION - LOWEST PRIORITY) ── */}
        <section id="methodology" data-section className="bg-[#0a0c16]/50 border border-white/10 rounded-lg overflow-hidden transition-all duration-300">
          <button 
            onClick={() => setTelemetryCollapsed(!telemetryCollapsed)}
            className="w-full flex items-center justify-between p-4 bg-slate-950/20 hover:bg-slate-950/40 transition font-mono text-xs font-bold text-slate-500 uppercase tracking-wider cursor-pointer"
          >
            <div className="flex items-center gap-2">
              <Database size={13} className="text-slate-550 text-slate-500" />
              <span>Research Methodology & Data Sources</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-slate-650 font-normal lowercase">(Click to expand developer telemetry)</span>
              {telemetryCollapsed ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
            </div>
          </button>

          {!telemetryCollapsed && (
            <div className="p-5 border-t border-white/5 space-y-4 font-mono text-xs text-slate-400 animate-slide-down">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="bg-slate-950/50 p-3 rounded border border-white/5">
                  <span className="text-slate-550 text-slate-500 text-[8px] font-bold block uppercase mb-1">Execution Speed</span>
                  <span className="text-white font-bold text-xs">{analysisData.system_status?.execution_time_sec ? `${analysisData.system_status.execution_time_sec} sec` : "N/A"}</span>
                </div>
                <div className="bg-slate-950/50 p-3 rounded border border-white/5">
                  <span className="text-slate-550 text-slate-500 text-[8px] font-bold block uppercase mb-1">Cache Status</span>
                  <span className="text-white font-bold text-xs">{analysisData.system_status?.cache_status || "Miss"}</span>
                </div>
                <div className="bg-slate-950/50 p-3 rounded border border-white/5">
                  <span className="text-slate-555 text-slate-500 text-[8px] font-bold block uppercase mb-1">Articles Analyzed</span>
                  <span className="text-white font-bold text-xs">{sentiment.articles?.length || 0} articles</span>
                </div>
                <div className="bg-slate-950/50 p-3 rounded border border-white/5">
                  <span className="text-slate-550 text-slate-500 text-[8px] font-bold block uppercase mb-1">Model Inference Engine</span>
                  <span className="text-white font-bold text-xs">Llama-3.3-70b-versatile (Groq)</span>
                </div>
              </div>

              <div className="bg-slate-950/80 rounded p-4 border border-white/5 space-y-2.5">
                <span className="text-slate-500 text-[8.5px] font-bold block uppercase border-b border-white/5 pb-1">Ingested Data Pipeline Sources</span>
                <ul className="space-y-1.5 text-[10px] text-slate-400 leading-relaxed">
                  <li><strong>Yahoo Finance API:</strong> Live daily OHLCV closing history, market caps, net income, PE, and provider feed streams.</li>
                  <li><strong>Google News RSS Feed:</strong> Backup XML headline feed, parsed and mapped to keywords local lexicon sentiment tags.</li>
                  <li><strong>Groq Gateway API:</strong> Llama 3.3 70B model gateway utilizing strict 10s connection limits with fallback routines.</li>
                  <li><strong>Internal Quant Engine:</strong> Deterministic technical indicators calculations (50d/200d MA crosses, RSI vectors, volatility metrics).</li>
                </ul>
              </div>
            </div>
          )}
        </section>

      </main>
    </div>
  );
}
