import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Shield, 
  TrendingUp, 
  Landmark, 
  Newspaper, 
  ShieldAlert, 
  X, 
  CheckCircle2, 
  ArrowRight,
  Database,
  Layers,
  FileText,
  Users,
  Bell,
  Activity,
  ArrowUpRight,
  Globe,
  Clock,
  LayoutGrid,
  Scale
} from "lucide-react";

// Interactive Stock Data for Sample Preview (Exactly mapped to the screenshot parameters)
const STOCK_DATA = {
  AAPL: {
    symbol: "AAPL",
    companyName: "Apple Inc.",
    verdict: "BUY",
    verdictStyle: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
    conviction: 77,
    risk: "LOW",
    riskStyle: "text-emerald-450 text-emerald-400",
    price: "$182.50",
    support: "$292",
    resistance: "$315",
    change: "+12.3%",
    changeStyle: "text-emerald-400",
    drivers: [
      "Revenue Growth +16% YoY",
      "Trading Above 200 DMA",
      "Positive News Momentum"
    ],
    risks: [
      "Premium Valuation",
      "Product Concentration"
    ]
  },
  TSLA: {
    symbol: "TSLA",
    companyName: "Tesla Motors",
    verdict: "HOLD",
    verdictStyle: "text-amber-400 bg-amber-500/10 border-amber-500/20",
    conviction: 62,
    risk: "HIGH",
    riskStyle: "text-red-400",
    price: "$224.50",
    support: "$210",
    resistance: "$245",
    change: "-3.4%",
    changeStyle: "text-red-400",
    drivers: [
      "Operating Margin Growth +8%",
      "Volume Production Beat",
      "High Volatility Index Channel"
    ],
    risks: [
      "Regulatory Valuation Multiple",
      "Supply Chain Contraction"
    ]
  },
  "RELIANCE.NS": {
    symbol: "RELIANCE.NS",
    companyName: "Reliance Industries",
    verdict: "BUY",
    verdictStyle: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
    conviction: 85,
    risk: "LOW",
    riskStyle: "text-emerald-400",
    price: "₹2,450.15",
    support: "₹2,380",
    resistance: "₹2,550",
    change: "+15.6%",
    changeStyle: "text-emerald-400",
    drivers: [
      "Strong Support near 200 SMA",
      "Refining Margin Optimization",
      "Robust Retail Solvency Rating"
    ],
    risks: [
      "High Capex Drag",
      "Tariff Restructuring"
    ]
  },
  "INFY.NS": {
    symbol: "INFY.NS",
    companyName: "Infosys Ltd.",
    verdict: "HOLD",
    verdictStyle: "text-amber-400 bg-amber-500/10 border-amber-500/20",
    conviction: 58,
    risk: "MEDIUM",
    riskStyle: "text-amber-400",
    price: "₹1,420.30",
    support: "₹1,380",
    resistance: "₹1,480",
    change: "+2.1%",
    changeStyle: "text-emerald-400",
    drivers: [
      "Steady Solvency Ratios",
      "Expansion in Cloud Segments",
      "Lexicon Matching Bullishness"
    ],
    risks: [
      "High Attrition Margins",
      "Macro IT Spends Cooling"
    ]
  }
};

function LandingPage({ onStartResearch, onViewArchitecture }) {
  const [activeModal, setActiveModal] = useState(null); // 'technical', 'fundamental', 'sentiment'
  const [activePreview, setActivePreview] = useState("AAPL");
  const [newsSentimentProgress, setNewsSentimentProgress] = useState(74);

  // Subtle animate progress bar to feel alive
  useEffect(() => {
    const interval = setInterval(() => {
      setNewsSentimentProgress(prev => {
        const delta = Math.floor(Math.random() * 5) - 2;
        const next = prev + delta;
        return Math.min(Math.max(next, 70), 80);
      });
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleScroll = (id) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  const currentStock = STOCK_DATA[activePreview];

  return (
    <div className="relative min-h-screen bg-[#05060f] text-[#f3f4f6] font-sans overflow-x-hidden">
      
      {/* ── BACKGROUND: SUBTLE CHARCOAL PHOTO OVERLAY (No glowing patterns) ── */}
      <div className="absolute inset-0 z-0 pointer-events-none overflow-hidden h-[1050px]">
        <img 
          src="/landing_page_background.jpg" 
          alt="Financial Analysis Graphic Backdrop" 
          className="w-full h-full object-cover opacity-25 mix-blend-luminosity filter saturate-50"
        />
        {/* Spotlight overlay vignette (Deep charcoal overlay ensuring text readability) */}
        <div 
          className="absolute inset-0 z-10" 
          style={{
            background: "radial-gradient(circle at 50% 25%, rgba(5, 6, 15, 0.2) 0%, rgba(5, 6, 15, 0.85) 60%, rgba(5, 6, 15, 1) 100%)"
          }}
        />
        <div className="absolute inset-0 financial-grid opacity-[0.03] z-15" />
      </div>

      {/* ── STICKY NAVIGATION HEADER (Flat matte layout, thin borders) ── */}
      <header className="fixed top-0 left-0 right-0 z-50 border-b border-white/5 bg-[#05060f]/80 backdrop-blur-md">
        <div className="max-w-[1400px] mx-auto px-8 py-5 flex items-center justify-between">
          {/* Logo */}
          <div 
            className="flex items-center gap-2.5 cursor-pointer" 
            onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
          >
            <img 
              src="/LOGO.jpeg" 
              alt="Quantum Logo" 
              className="w-7 h-7 rounded-lg object-contain"
            />
            <span className="font-bold text-[15px] tracking-wider text-white uppercase" style={{ fontFamily: "'General Sans', sans-serif" }}>
              QUANTUM
            </span>
          </div>
          
          {/* Navigation Links */}
          <nav className="hidden md:flex items-center gap-8 text-[11px] font-medium text-slate-400">
            <button onClick={() => handleScroll("why-traditional")} className="hover:text-white transition cursor-pointer">Product</button>
            <button onClick={() => handleScroll("framework")} className="hover:text-white transition cursor-pointer">Framework</button>
            <button onClick={() => handleScroll("deliverables")} className="hover:text-white transition cursor-pointer">Deliverables</button>
            <button onClick={() => handleScroll("markets")} className="hover:text-white transition cursor-pointer">Markets</button>
            <button onClick={() => handleScroll("why-trust")} className="hover:text-white transition cursor-pointer">Why Trust Us</button>
            <button onClick={() => onViewArchitecture()} className="hover:text-white transition cursor-pointer">Architecture</button>
          </nav>
          
          {/* Actions */}
          <div className="flex items-center gap-5">
            <button 
              onClick={() => onStartResearch()} 
              className="text-[11px] font-medium text-slate-400 hover:text-white transition cursor-pointer"
            >
              Sign In
            </button>
            <button 
              onClick={() => onStartResearch()} 
              className="px-5 py-2.5 rounded bg-[#FFBA9D] text-black font-semibold text-[11px] hover:bg-[#ffa382] transition-all duration-150 cursor-pointer"
            >
              Start Research
            </button>
          </div>
        </div>
      </header>

      {/* ── HERO SECTION (Flat design, high contrast text) ── */}
      <section className="max-w-[1400px] mx-auto px-8 pt-44 pb-16 relative z-20 flex flex-col items-center text-center">
        {/* Main Headline */}
        <h1 
          className="text-5xl sm:text-6xl md:text-7xl font-black tracking-tight leading-[1.08] text-white max-w-6xl" 
          style={{ fontFamily: "'General Sans', sans-serif" }}
        >
          From Market Noise To <br className="hidden sm:block" />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-orange-400 via-[#FFBA9D] to-amber-400">
            Conviction.
          </span>
        </h1>

        {/* Subheading */}
        <p className="text-slate-300 text-sm sm:text-base md:text-lg leading-relaxed max-w-4xl mt-6 font-normal">
          Generate complete equity research reports by combining technical structure, company fundamentals, news intelligence, and catalyst tracking into a single investment brief.
        </p>

        {/* Metric Badges (From Screenshot 1 - simple horizontal list with small icons) */}
        <div className="flex flex-wrap justify-center gap-x-8 gap-y-3 mt-8 text-[10px] font-mono text-slate-500 font-bold uppercase tracking-wider">
          <span className="flex items-center gap-2">
            <Shield size={11} className="text-[#FFBA9D]" /> 4 Specialized Research Engines
          </span>
          <span className="flex items-center gap-2">
            <Database size={11} className="text-[#FFBA9D]" /> 100+ Financial Indicators
          </span>
          <span className="flex items-center gap-2">
            <Newspaper size={11} className="text-[#FFBA9D]" /> Real-Time News Monitoring
          </span>
          <span className="flex items-center gap-2">
            <Globe size={11} className="text-[#FFBA9D]" /> US & Indian Market Coverage
          </span>
        </div>

        {/* Hero CTAs */}
        <div className="flex items-center justify-center gap-4 mt-8">
          <button 
            onClick={() => onStartResearch()} 
            className="px-6 py-3 rounded bg-white text-black font-semibold text-sm hover:bg-slate-200 transition-all duration-150 cursor-pointer"
          >
            Start Research
          </button>
          <button 
            onClick={() => handleScroll("sample-preview")}
            className="px-6 py-3 rounded border border-white/20 text-white font-semibold text-sm hover:bg-white/5 transition-all duration-150 cursor-pointer"
          >
            View Sample Report
          </button>
        </div>
      </section>

      {/* ── EXACT REPLICA DASHBOARD PREVIEW WIDGET (From Screenshot 1) ── */}
      <section id="sample-preview" className="max-w-[1400px] mx-auto px-8 pb-28 relative z-20">
        
        {/* Flat Capsule Ticker Selector */}
        <div className="flex justify-center gap-1.5 mb-6 font-mono text-[10px] font-bold">
          {Object.keys(STOCK_DATA).map((tab) => (
            <button
              key={tab}
              onClick={() => setActivePreview(tab)}
              className={`px-3 py-1.5 rounded transition-all duration-150 cursor-pointer ${
                activePreview === tab
                  ? "bg-white text-black font-black"
                  : "bg-[#0c0e1a] text-slate-500 border border-white/5 hover:text-slate-350"
              }`}
            >
              {tab.replace(".NS", "")}
            </button>
          ))}
        </div>

        {/* Dashboard Frame (Flat border, solid dark background) */}
        <div className="w-full bg-[#0a0c16] border border-white/10 rounded p-6">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
            
            {/* Left Column splits into Ticker card & Technical levels */}
            <div className="lg:col-span-5 flex flex-col gap-4">
              
              {/* Ticker Card */}
              <div className="bg-[#0e101f]/75 border border-white/5 rounded p-4 flex flex-col justify-between h-[160px]">
                <div className="flex items-center justify-between">
                  <span className="text-[9px] font-mono text-slate-500 font-bold uppercase tracking-wider">TICKER</span>
                  <span className={`text-[9px] font-mono font-black px-2 py-0.5 rounded border ${currentStock.verdictStyle}`}>
                    {currentStock.verdict}
                  </span>
                </div>
                <h3 className="text-white text-xl font-bold font-mono tracking-wide mt-1.5">
                  {currentStock.companyName} <span className="text-slate-500 font-normal">({currentStock.symbol})</span>
                </h3>
                <div className="grid grid-cols-2 gap-4 border-t border-white/5 pt-3 mt-3 font-mono text-[10px]">
                  <div>
                    <span className="text-slate-500 block uppercase font-bold text-[8.5px]">Conviction</span>
                    <span className="text-white font-bold text-xs mt-0.5 block">{currentStock.conviction}%</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block uppercase font-bold text-[8.5px]">Risk Profile</span>
                    <span className={`font-bold text-xs mt-0.5 block ${currentStock.riskStyle}`}>{currentStock.risk}</span>
                  </div>
                </div>
              </div>

              {/* Technical Levels Card */}
              <div className="bg-[#0e101f]/75 border border-white/5 rounded p-4 flex flex-col justify-between h-[110px] font-mono text-[10px]">
                <span className="text-[#FFBA9D] font-bold text-[8.5px] uppercase tracking-wider block">TECHNICAL LEVELS</span>
                <div className="space-y-2.5 mt-2.5">
                  <div className="flex justify-between border-b border-white/5 pb-1.5">
                    <span className="text-slate-500">Resistance</span>
                    <span className="text-white font-bold">{currentStock.resistance}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Support</span>
                    <span className="text-white font-bold">{currentStock.support}</span>
                  </div>
                </div>
              </div>

            </div>

            {/* Right Column: Executive Summary & Downside Risks */}
            <div className="lg:col-span-7 bg-[#0e101f]/75 border border-white/5 rounded p-5 flex flex-col justify-between min-h-[286px]">
              
              <div className="space-y-4">
                <span className="text-[9px] font-mono text-slate-500 font-bold uppercase tracking-wider block text-center">EXECUTIVE SUMMARY</span>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
                  
                  {/* Left Column: Verdict change + Drivers */}
                  <div className="space-y-3">
                    <div className={`text-2xl font-mono font-black ${currentStock.changeStyle}`}>
                      {currentStock.change}
                    </div>
                    <ul className="space-y-2 text-[10.5px] font-light text-slate-300">
                      {currentStock.drivers.map((drv, idx) => (
                        <li key={idx} className="flex gap-2 items-start leading-relaxed">
                          <span className="text-emerald-400 shrink-0">•</span>
                          <span>{drv}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Right Column: Risk Factors */}
                  <div className="space-y-3">
                    <span className="text-slate-500 font-mono font-bold text-[8.5px] uppercase tracking-wider block">RISK FACTORS</span>
                    <ul className="space-y-2 text-[10.5px] font-light text-slate-350">
                      {currentStock.risks.map((rsk, idx) => (
                        <li key={idx} className="flex gap-2 items-start leading-relaxed">
                          <span className="text-red-400 shrink-0">•</span>
                          <span>{rsk}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                </div>
              </div>

              {/* Bottom disclaimer & open action */}
              <div className="border-t border-white/5 pt-4 mt-5 flex justify-between items-center text-[8.5px] font-mono text-slate-500">
                <div className="flex items-center gap-2">
                  <Shield size={11} className="text-slate-400" />
                  <span>This report was generated using the Multi-Agent Consensus Protocol v2.0</span>
                </div>
                <button 
                  onClick={() => onStartResearch(currentStock.symbol)}
                  className="text-[#FFBA9D] hover:text-[#ffa382] font-black uppercase tracking-wider cursor-pointer"
                >
                  OPEN DETAILED PIPELINE →
                </button>
              </div>

            </div>

          </div>
        </div>
      </section>

      {/* ── SECTION 2: WHY TRADITIONAL RESEARCH IS BROKEN (From Screenshot 1) ── */}
      <section id="why-traditional" className="bg-[#070812] border-y border-white/5 py-24 relative z-20">
        <div className="max-w-[1400px] mx-auto px-8">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 mb-16 items-start">
            <div className="lg:col-span-5 space-y-3">
              <span className="section-label block mb-2">THE RESEARCH GAP</span>
              <h2 className="text-4xl font-bold tracking-tight text-white leading-tight">
                Why Traditional Research Is Broken
              </h2>
            </div>
            <p className="lg:col-span-7 text-slate-200 text-sm sm:text-base md:text-lg leading-relaxed pt-1 lg:pt-6">
              In a market moving at the speed of light, old-guard analysts are lagging behind by days. We solve the fragmentation of the modern investor's workflow.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Card 1 */}
            <div className="bg-[#0c0d18] border border-white/5 rounded p-6 space-y-4 hover:border-white/10 transition-all duration-200">
              <div className="w-8 h-8 rounded border border-white/10 flex items-center justify-center text-[#FFBA9D]">
                <Clock size={14} />
              </div>
              <h3 className="text-white font-black text-xl sm:text-2xl mb-3">Structural Latency</h3>
              <p className="text-slate-300 text-sm leading-relaxed">
                Traditional reports take 48+ hours to publish. In that time, the market has already priced in the move. Quantum updates in real-time as data hits the wire.
              </p>
            </div>

            {/* Card 2 */}
            <div className="bg-[#0c0d18] border border-white/5 rounded p-6 space-y-4 hover:border-white/10 transition-all duration-200">
              <div className="w-8 h-8 rounded border border-white/10 flex items-center justify-center text-[#FFBA9D]">
                <LayoutGrid size={14} />
              </div>
              <h3 className="text-white font-black text-xl sm:text-2xl mb-3">Workflow Fragmentation</h3>
              <p className="text-slate-300 text-sm leading-relaxed">
                Switching between Bloomberg, TradingView, and SEC filings creates mental fatigue. We unify technicals, fundamentals, and catalysts in a single view.
              </p>
            </div>

            {/* Card 3 */}
            <div className="bg-[#0c0d18] border border-white/5 rounded p-6 space-y-4 hover:border-white/10 transition-all duration-200">
              <div className="w-8 h-8 rounded border border-white/10 flex items-center justify-center text-[#FFBA9D]">
                <Scale size={14} />
              </div>
              <h3 className="text-white font-black text-xl sm:text-2xl mb-3">Institutional Bias</h3>
              <p className="text-slate-300 text-sm leading-relaxed">
                Sell-side reports are often conflicted by investment banking relationships. Our AI agents are objective, data-driven, and incentivized only for accuracy.
              </p>
            </div>

          </div>
        </div>
      </section>

      {/* ── SECTION 3: WHAT EVERY REPORT COVERS / LAYERS 01-03 (From Screenshot 2) ── */}
      <section id="framework" className="max-w-[1400px] mx-auto px-8 py-28 relative z-20">
        <div className="text-center mb-16 space-y-3">
          <span className="section-label block mb-2">RESEARCH FRAMEWORK</span>
          <h2 className="text-4xl font-bold tracking-tight text-white mt-1.5" style={{ fontFamily: "'General Sans', sans-serif" }}>
            What Every Research Report Covers
          </h2>
          <p className="text-slate-300 text-sm sm:text-base mt-2 max-w-2xl mx-auto font-light">
            Each report combines multiple independent research layers before generating a final market brief.
          </p>
        </div>

        {/* Layers Grid */}
        <div className="flex flex-col gap-6">
          
          {/* Layer 01 and 02 side-by-side */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            
            {/* Layer 01 */}
            <div 
              onClick={() => setActiveModal("technical")}
              className="bg-[#0c0d18] border border-white/5 rounded p-8 flex flex-col justify-between min-h-[320px] hover:border-white/10 transition-all duration-200 cursor-pointer"
            >
              <div>
                <div className="flex items-center justify-between border-b border-white/5 pb-3.5 mb-4 text-[10.5px] font-mono text-slate-500 font-bold uppercase tracking-wider">
                  <span>LAYER 01</span>
                  <span className="flex items-center gap-1 text-white"><TrendingUp size={11} /> Technical Structure Analysis</span>
                </div>
                <p className="text-slate-300 text-sm leading-relaxed mb-6">
                  Identifies trend direction, momentum shifts, support and resistance zones, volatility expansion, and multi-timeframe market structure.
                </p>
                
                {/* 2-column grid layout inside Card 1 */}
                <div className="grid grid-cols-2 gap-6 font-mono text-[10.5px] sm:text-xs">
                  
                  {/* Left Column: Metrics Table */}
                  <div className="space-y-2 text-slate-350">
                    <div className="flex justify-between py-1 border-b border-white/5">
                      <span className="text-slate-500">RSI</span>
                      <span className="text-white font-bold">MOMENTUM CHECK</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-white/5">
                      <span className="text-slate-500">MACD</span>
                      <span className="text-white font-bold">CONVERGENCE</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-white/5">
                      <span className="text-slate-500">TREND STRENGTH</span>
                      <span className="text-white font-bold">ADX VALIDATION</span>
                    </div>
                    <div className="flex justify-between py-1">
                      <span className="text-slate-500">MARKET STRUCTURE</span>
                      <span className="text-white font-bold font-mono">MULTI-TF SIGNALS</span>
                    </div>
                  </div>

                  {/* Right Column: Mini S&R Map Box */}
                  <div className="bg-slate-950/60 border border-white/5 rounded p-3 flex flex-col justify-between relative h-[105px]">
                    <svg className="w-full h-10 text-orange-400 opacity-60" viewBox="0 0 100 30" fill="none">
                      <path d="M0 20 C15 15, 30 25, 45 10 C60 5, 75 18, 100 8" stroke="#FFBA9D" strokeWidth="1" />
                      <line x1="0" y1="12" x2="100" y2="12" stroke="rgba(255,255,255,0.08)" strokeDasharray="2 2" />
                    </svg>
                    <div className="text-[7.5px] text-slate-500 font-bold uppercase tracking-wider leading-relaxed">
                      <span className="text-orange-400">ANALYSIS DEPTH //</span><br />
                      SUPPORT & RESISTANCE MAPPING
                    </div>
                  </div>

                </div>

              </div>
              
              <div className="flex justify-between items-center text-[8.5px] font-mono text-[#FFBA9D] font-bold border-t border-white/5 pt-4 mt-6">
                <span>SUPPORT & RESISTANCE MAPPING</span>
                <span>EXPAND DETAILS →</span>
              </div>
            </div>

            {/* Layer 02 */}
            <div 
              onClick={() => setActiveModal("sentiment")}
              className="bg-[#0c0d18] border border-white/5 rounded p-8 flex flex-col justify-between min-h-[320px] hover:border-white/10 transition-all duration-200 cursor-pointer"
            >
              <div>
                <div className="flex items-center justify-between border-b border-white/5 pb-3.5 mb-4 text-[10.5px] font-mono text-slate-500 font-bold uppercase tracking-wider">
                  <span>LAYER 02</span>
                  <span className="flex items-center gap-1 text-white"><Newspaper size={11} /> News & Narrative Intelligence</span>
                </div>
                
                {/* 2-column grid layout inside Card 2 */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  
                  {/* Left Column: Description */}
                  <p className="text-slate-300 text-sm leading-relaxed">
                    Monitors breaking news, analyst commentary, market narratives, earnings events, and catalysts that influence investor sentiment.
                  </p>

                  {/* Right Column: Sentiment progress + boxes */}
                  <div className="space-y-2.5 font-mono text-[9px]">
                    
                    {/* Sentiment Bar */}
                    <div>
                      <div className="flex justify-between text-slate-500 text-[8px] font-bold mb-1">
                        <span>NEWS SENTIMENT</span>
                        <span className="text-emerald-400">{newsSentimentProgress}% POSITIVE</span>
                      </div>
                      <div className="h-1 bg-slate-900 rounded-full overflow-hidden">
                        <motion.div 
                          className="h-full bg-emerald-500" 
                          initial={{ width: "74%" }}
                          animate={{ width: `${newsSentimentProgress}%` }}
                          transition={{ duration: 0.6 }}
                        />
                      </div>
                    </div>

                    {/* Catalyst Boxes */}
                    <div className="bg-slate-950/60 border border-white/5 rounded px-2.5 py-1.5 flex flex-col">
                      <span className="text-slate-500 text-[7px] font-bold">CATALYST DETECTION</span>
                      <span className="text-white text-[8px] font-bold truncate">Earnings Call Volatility</span>
                    </div>

                    <div className="bg-slate-950/60 border border-white/5 rounded px-2.5 py-1.5 flex flex-col">
                      <span className="text-slate-500 text-[7px] font-bold">ANALYST COVERAGE</span>
                      <span className="text-white text-[8px] font-bold truncate">3 New Bullish Revisions</span>
                    </div>

                  </div>

                </div>

              </div>

              {/* Bottom risk badges */}
              <div className="border-t border-white/5 pt-4 mt-6 flex flex-wrap justify-between items-center gap-2 text-[8px] font-mono font-bold text-slate-500">
                <span className="uppercase text-slate-500">RISK EVENTS DETECTED:</span>
                <div className="flex gap-1">
                  <span className="px-1.5 py-0.5 border border-red-500/20 bg-red-500/5 text-red-400 rounded">FOMC BRIEF</span>
                  <span className="px-1.5 py-0.5 border border-red-500/20 bg-red-500/5 text-red-400 rounded">MACRO SHIFT</span>
                </div>
              </div>
            </div>

          </div>

          {/* Layer 03 - Full Width */}
          <div 
            onClick={() => setActiveModal("fundamental")}
            className="bg-[#0c0d18] border border-white/5 rounded p-8 hover:border-white/10 transition-all duration-200 cursor-pointer"
          >
            <div className="flex items-center justify-between border-b border-white/5 pb-3.5 mb-4 text-[10.5px] font-mono text-slate-500 font-bold uppercase tracking-wider">
              <span>LAYER 03</span>
              <span className="flex items-center gap-1 text-white"><Landmark size={11} /> Fundamental Quality Assessment</span>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
              
              {/* Left Column: text */}
              <p className="lg:col-span-4 text-slate-300 text-sm leading-relaxed">
                Evaluates company growth, profitability, valuation, financial health, and long-term business performance compared to sector averages.
              </p>

              {/* Right Column: 5 horizontal vertical-indicators boxes */}
              <div className="lg:col-span-8 grid grid-cols-2 sm:grid-cols-5 gap-3 text-[9px] font-mono text-slate-400">
                
                {/* 1 */}
                <div className="bg-slate-950/60 border border-white/5 rounded p-2.5 flex items-stretch gap-2.5">
                  <div className="w-1 rounded bg-emerald-500" />
                  <div>
                    <span className="text-[7.5px] text-slate-500 font-bold block">GROWTH</span>
                    <span className="text-white font-bold block mt-0.5">Revenue Growth</span>
                    <span className="text-[8px] text-slate-500 block mt-0.5">8.45% YoY</span>
                  </div>
                </div>

                {/* 2 */}
                <div className="bg-slate-950/60 border border-white/5 rounded p-2.5 flex items-stretch gap-2.5">
                  <div className="w-1 rounded bg-[#FFBA9D]" />
                  <div>
                    <span className="text-[7.5px] text-slate-500 font-bold block">VALUATION</span>
                    <span className="text-white font-bold block mt-0.5">Price/Earnings</span>
                    <span className="text-[8px] text-[#FFBA9D] block mt-0.5">DCF Model</span>
                  </div>
                </div>

                {/* 3 */}
                <div className="bg-slate-950/60 border border-white/5 rounded p-2.5 flex items-stretch gap-2.5">
                  <div className="w-1 rounded bg-emerald-500" />
                  <div>
                    <span className="text-[7.5px] text-slate-500 font-bold block">PROFITABILITY</span>
                    <span className="text-white font-bold block mt-0.5">Operating Margin</span>
                    <span className="text-[8px] text-slate-500 block mt-0.5">EBITDA Analysis</span>
                  </div>
                </div>

                {/* 4 */}
                <div className="bg-slate-950/60 border border-white/5 rounded p-2.5 flex items-stretch gap-2.5">
                  <div className="w-1 rounded bg-emerald-500" />
                  <div>
                    <span className="text-[7.5px] text-slate-500 font-bold block">HEALTH</span>
                    <span className="text-white font-bold block mt-0.5">Financial Strength</span>
                    <span className="text-[8px] text-slate-500 block mt-0.5">Solvency Check</span>
                  </div>
                </div>

                {/* 5 */}
                <div className="bg-slate-950/60 border border-white/5 rounded p-2.5 flex items-stretch gap-2.5">
                  <div className="w-1 rounded bg-[#FFBA9D]" />
                  <div>
                    <span className="text-[7.5px] text-slate-500 font-bold block">MOAT</span>
                    <span className="text-white font-bold block mt-0.5">Competitive Pos.</span>
                    <span className="text-[8px] text-[#FFBA9D] block mt-0.5">Sector Benchmark</span>
                  </div>
                </div>

              </div>

            </div>
          </div>

        </div>
      </section>

      {/* ── SECTION 4: DELIVERABLES / WHAT YOU'LL RECEIVE (From Screenshot 2) ── */}
      <section id="deliverables" className="bg-[#070812] border-y border-white/5 py-24 relative z-20">
        <div className="max-w-[1400px] mx-auto px-8">
          <div className="text-center mb-16 space-y-3">
            <span className="section-label block mb-2">Deliverables</span>
            <h2 className="text-4xl font-bold tracking-tight text-white mt-1.5" style={{ fontFamily: "'General Sans', sans-serif" }}>
              What You'll Receive
            </h2>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* Card 1 */}
            <div className="bg-[#0c0d18] border border-white/5 rounded p-6 hover:border-white/10 transition duration-150">
              <div className="w-6 h-6 rounded border border-white/15 flex items-center justify-center mb-4 text-[#FFBA9D] font-mono text-[10px] font-bold">1</div>
              <h3 className="text-white font-black text-lg mb-2">Technical Snapshot</h3>
              <p className="text-slate-300 text-sm leading-relaxed">
                Trend analysis, RSI, MACD, support and resistance levels.
              </p>
            </div>

            {/* Card 2 */}
            <div className="bg-[#0c0d18] border border-white/5 rounded p-6 hover:border-white/10 transition duration-150">
              <div className="w-6 h-6 rounded border border-white/15 flex items-center justify-center mb-4 text-[#FFBA9D] font-mono text-[10px] font-bold">2</div>
              <h3 className="text-white font-black text-lg mb-2">Fundamental Snapshot</h3>
              <p className="text-slate-300 text-sm leading-relaxed">
                Growth, valuation, earnings, and profitability metrics.
              </p>
            </div>

            {/* Card 3 */}
            <div className="bg-[#0c0d18] border border-white/5 rounded p-6 hover:border-white/10 transition duration-150">
              <div className="w-6 h-6 rounded border border-white/15 flex items-center justify-center mb-4 text-[#FFBA9D] font-mono text-[10px] font-bold">3</div>
              <h3 className="text-white font-black text-lg mb-2">Sentiment Snapshot</h3>
              <p className="text-slate-300 text-sm leading-relaxed">
                News flow, market catalysts, and analyst signal tracking.
              </p>
            </div>

            {/* Card 4 */}
            <div className="bg-[#0c0d18] border border-orange-500/20 rounded p-6 hover:border-orange-500/35 transition duration-150 relative overflow-hidden">
              <div className="absolute right-0 top-0 text-[7.5px] font-mono bg-[#FFBA9D] text-black px-2 py-0.5 uppercase tracking-wider font-black">
                CORE OUTPUT
              </div>
              <div className="w-6 h-6 rounded border border-[#FFBA9D]/30 flex items-center justify-center mb-4 text-[#FFBA9D] font-mono text-[10px] font-bold">4</div>
              <h3 className="text-white font-black text-lg mb-2">Executive Summary</h3>
              <p className="text-slate-200 text-sm leading-relaxed">
                 confidence score, key drivers, and risks.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ── SECTION 5: SUPPORTED MARKET COVERAGE (From Screenshot 2) ── */}
      <section id="markets" className="max-w-[1400px] mx-auto px-8 py-28 relative z-20">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          
          <div className="lg:col-span-5 space-y-4">
            <span className="section-label block mb-2">Coverage</span>
            <h2 className="text-4xl font-bold text-white tracking-tight leading-tight">
              Supported Market Coverage
            </h2>
            <p className="text-slate-300 text-sm sm:text-base leading-relaxed">
              Our systems maintain real-time data feeds across major global exchanges to ensure report accuracy.
            </p>
          </div>

          <div className="lg:col-span-7 grid grid-cols-1 sm:grid-cols-2 gap-4">
            
            {/* US Card */}
            <div className="bg-[#0c0d18] border border-white/5 rounded p-6 space-y-4">
              <span className="font-mono text-xs sm:text-sm text-white font-bold uppercase tracking-wider block">US Equities</span>
              <div className="flex flex-col gap-2 font-mono text-xs sm:text-sm text-slate-300">
                <span className="px-4 py-2.5 bg-[#05060f] rounded border border-white/5 flex items-center gap-2">
                  <span className="text-[#FFBA9D]">•</span> NASDAQ
                </span>
                <span className="px-4 py-2.5 bg-[#05060f] rounded border border-white/5 flex items-center gap-2">
                  <span className="text-[#FFBA9D]">•</span> NYSE
                </span>
                <span className="px-4 py-2.5 bg-[#05060f] rounded border border-white/5 flex items-center gap-2">
                  <span className="text-[#FFBA9D]">•</span> S&P 500
                </span>
              </div>
            </div>

            {/* Indian Card */}
            <div className="bg-[#0c0d18] border border-white/5 rounded p-6 space-y-4">
              <span className="font-mono text-xs sm:text-sm text-white font-bold uppercase tracking-wider block">Indian Equities</span>
              <div className="flex flex-col gap-2 font-mono text-xs sm:text-sm text-slate-300">
                <span className="px-4 py-2.5 bg-[#05060f] rounded border border-white/5 flex items-center gap-2">
                  <span className="text-[#FFBA9D]">•</span> NSE
                </span>
                <span className="px-4 py-2.5 bg-[#05060f] rounded border border-white/5 flex items-center gap-2">
                  <span className="text-[#FFBA9D]">•</span> BSE
                </span>
                <span className="px-3 py-2 bg-[#05060f] rounded border border-white/5 flex items-center gap-2">
                  <span className="text-[#FFBA9D]">•</span> LARGE & MID CAP
                </span>
              </div>
            </div>

          </div>

        </div>
      </section>

      {/* ── SECTION 6: WHY TRUST THE RESEARCH (From Screenshot 2) ── */}
      <section id="why-trust" className="bg-[#070812] border-y border-white/5 py-24 relative z-20">
        <div className="max-w-[1400px] mx-auto px-8 space-y-20">
          <div className="text-center">
            <span className="section-label block mb-2">Trust & Validation</span>
            <h2 className="text-4xl font-bold tracking-tight text-white" style={{ fontFamily: "'General Sans', sans-serif" }}>
              Why Trust The Research
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 text-center">
            {/* 1 */}
            <div className="flex flex-col items-center space-y-4 px-4">
              <div className="w-8 h-8 rounded-full bg-[#FFBA9D]/10 flex items-center justify-center text-[#FFBA9D]">
                <CheckCircle2 size={15} />
              </div>
              <h4 className="text-white font-black text-base sm:text-lg">Independent Signal Validation</h4>
              <p className="text-slate-300 leading-relaxed text-sm">
                Every technical alert or catalyst news item is evaluated against local databases and confirmed by multiple mathematical checks.
              </p>
            </div>
            
            {/* 2 */}
            <div className="flex flex-col items-center space-y-4 px-4">
              <div className="w-8 h-8 rounded-full bg-[#FFBA9D]/10 flex items-center justify-center text-[#FFBA9D]">
                <Layers size={15} />
              </div>
              <h4 className="text-white font-black text-base sm:text-lg">Multiple Research Layers</h4>
              <p className="text-slate-300 leading-relaxed text-sm">
                Never rely on one factor. By evaluating technicals, fundamentals, and news co-dependently, we avoid single-metric blind spots.
              </p>
            </div>

            {/* 3 */}
            <div className="flex flex-col items-center space-y-4 px-4">
              <div className="w-8 h-8 rounded-full bg-[#FFBA9D]/10 flex items-center justify-center text-[#FFBA9D]">
                <FileText size={15} />
              </div>
              <h4 className="text-white font-black text-base sm:text-lg">Explainable Conclusions</h4>
              <p className="text-slate-300 leading-relaxed text-sm">
                Every rating or consensus decision displays its specific mathematical drivers and downside risk flags so you can double check.
              </p>
            </div>

            {/* 4 */}
            <div className="flex flex-col items-center space-y-4 px-4 mt-6 md:mt-0">
              <div className="w-8 h-8 rounded-full bg-[#FFBA9D]/10 flex items-center justify-center text-[#FFBA9D]">
                <Activity size={15} />
              </div>
              <h4 className="text-white font-black text-base sm:text-lg">Transparent Confidence Scores</h4>
              <p className="text-slate-300 leading-relaxed text-sm">
                Reports display the exact mathematical alignment between the AI research engines, revealing the true level of consensus.
              </p>
            </div>

            {/* 5 */}
            <div className="flex flex-col items-center space-y-4 px-4 mt-6 md:mt-0">
              <div className="w-8 h-8 rounded-full bg-[#FFBA9D]/10 flex items-center justify-center text-[#FFBA9D]">
                <Database size={15} />
              </div>
              <h4 className="text-white font-black text-base sm:text-lg">Real Market Data Sources</h4>
              <p className="text-slate-300 leading-relaxed text-sm">
                Direct integration with verified Yahoo Finance aggregates, local SEC databases, and raw RSS news feeds.
              </p>
            </div>

            {/* 6 */}
            <div className="flex flex-col items-center space-y-4 px-4 mt-6 md:mt-0">
              <div className="w-8 h-8 rounded-full bg-[#FFBA9D]/10 flex items-center justify-center text-[#FFBA9D]">
                <ShieldAlert size={15} />
              </div>
              <h4 className="text-white font-black text-base sm:text-lg">Risk-Aware Recommendations</h4>
              <p className="text-slate-300 leading-relaxed text-sm">
                We prioritize reporting downside risks, financial solvency checks, and structural variance warnings over plain upside targets.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ── SECTION 7: FINAL CTA (From Screenshot 2 & 3) ── */}
      <section className="max-w-[1400px] mx-auto px-8 py-32 relative z-20 text-center space-y-10">
        <div className="space-y-4">
          <span className="section-label block mb-2">GET STARTED</span>
          <h2 className="text-4xl font-bold tracking-tight text-white leading-tight">
            Ready To Research Smarter?
          </h2>
          <p className="text-slate-300 text-sm sm:text-base max-w-2xl mx-auto leading-relaxed">
            Generate a complete market brief in seconds and understand what matters before making a decision.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <button 
            onClick={() => onStartResearch()}
            className="px-8 py-3.5 bg-[#FFBA9D] text-black font-semibold rounded hover:bg-[#ffa382] transition-all duration-150 text-sm w-full sm:w-auto cursor-pointer"
          >
            Start Research
          </button>
          <button 
            onClick={() => handleScroll("sample-preview")}
            className="px-8 py-3.5 border border-white/20 text-white font-semibold rounded hover:bg-[#0c0d18] transition-all duration-150 text-sm w-full sm:w-auto cursor-pointer"
          >
            View Sample Analysis
          </button>
        </div>

        {/* Decorative Wave lines mimicking bottom visual */}
        <div className="pt-8 opacity-20 max-w-md mx-auto">
          <svg className="w-full h-8 text-[#FFBA9D]" viewBox="0 0 100 20" fill="none">
            <path d="M0 10 Q25 0, 50 10 T100 10" stroke="currentColor" strokeWidth="1" />
            <path d="M0 13 Q25 5, 50 13 T100 13" stroke="currentColor" strokeWidth="0.5" opacity="0.5" />
          </svg>
        </div>
      </section>

      {/* ── FOOTER & STATUS (From Screenshot 2 & 3) ── */}
      <footer className="border-t border-white/5 py-16 relative z-20 bg-[#05060f] font-mono text-[10px]">
        <div className="max-w-[1400px] mx-auto px-8 grid grid-cols-1 md:grid-cols-4 gap-12">
          
          {/* Logo & details */}
          <div className="space-y-4 font-sans">
            <div className="flex items-center gap-2.5">
              <img 
                src="/LOGO.jpeg" 
                alt="Quantum Logo" 
                className="w-6 h-6 rounded-md object-contain"
              />
              <span className="font-bold text-sm text-white uppercase tracking-wider">QUANTUM</span>
            </div>
            <p className="text-slate-500 text-[11px] leading-relaxed">
              Independent, multi-agent financial intelligence and synthesis engine for modern investors.
            </p>
          </div>

          {/* Research */}
          <div>
            <h4 className="text-white font-bold uppercase tracking-wider mb-4">Research</h4>
            <ul className="space-y-2.5 text-slate-500">
              <li><button onClick={() => handleScroll("sample-preview")} className="hover:text-white transition">US Equities</button></li>
              <li><button onClick={() => handleScroll("sample-preview")} className="hover:text-white transition">Indian Markets</button></li>
              <li><button onClick={() => handleScroll("framework")} className="hover:text-white transition">Framework Coverage</button></li>
            </ul>
          </div>

          {/* Resources */}
          <div>
            <h4 className="text-white font-bold uppercase tracking-wider mb-4">Resources</h4>
            <ul className="space-y-2.5 text-slate-500">
              <li><button onClick={() => onViewArchitecture()} className="hover:text-white transition">Methodology</button></li>
              <li><button onClick={() => handleScroll("why-trust")} className="hover:text-white transition">Compliance</button></li>
              <li><button onClick={() => handleScroll("why-traditional")} className="hover:text-white transition">Support</button></li>
            </ul>
          </div>

          {/* System Status / Copyright */}
          <div className="space-y-5">
            <h4 className="text-white font-bold uppercase tracking-wider">System Status</h4>
            <div className="flex items-center gap-2 text-emerald-400 font-bold uppercase tracking-wider">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <span>All Data Feeds Active</span>
            </div>
            <p className="text-slate-600 text-[9px] font-sans leading-relaxed">
              © 2026 QUANTUM AI Financial Intelligence. Built for Capgemini Agentic AI Buildathon. For demo purposes only.
            </p>
          </div>

        </div>
      </footer>

      {/* ── MODALS (Screen 2 Details) ── */}
      <AnimatePresence>
        {activeModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            {/* Overlay */}
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setActiveModal(null)}
              className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm"
            />

            {/* Modal Box */}
            <motion.div 
              initial={{ opacity: 0, scale: 0.96, y: 12 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.96, y: 12 }}
              transition={{ type: "spring", duration: 0.35 }}
              className="bg-[#0c0d18] border border-white/10 rounded p-6 w-full max-w-lg relative z-10 shadow-2xl space-y-5"
            >
              {/* Close */}
              <button 
                onClick={() => setActiveModal(null)}
                className="absolute top-4 right-4 text-slate-500 hover:text-white p-1 rounded hover:bg-white/5 transition cursor-pointer"
              >
                <X size={15} />
              </button>

              {activeModal === "technical" && (
                <div className="space-y-4">
                  <div className="flex items-center gap-2">
                    <TrendingUp size={18} className="text-[#FFBA9D]" />
                    <div>
                      <h3 className="text-white font-bold text-sm">Technical Structure Layer</h3>
                      <p className="text-[8.5px] text-slate-500 uppercase tracking-widest font-mono">QUANT VARIABLES</p>
                    </div>
                  </div>
                  <p className="text-slate-350 text-xs leading-relaxed font-light">
                    Audits historical volatility channels and moving averages. Re-sampling hourly data allows co-processors to compute rolling support levels and RSI boundaries.
                  </p>
                  <div className="bg-[#05060f] rounded border border-white/5 p-4 flex flex-col justify-between font-mono text-[9px] text-slate-400">
                    <div className="flex items-center justify-between border-b border-white/5 pb-2 mb-3">
                      <span>SMA INTERACTIVE CROSSOVER MODEL</span>
                      <span className="text-[#FFBA9D] font-bold">MONITORING</span>
                    </div>
                    <div className="w-full h-24 flex items-end justify-between px-2 pb-2 border-b border-slate-800">
                      <svg className="w-full h-full text-[#FFBA9D]" viewBox="0 0 100 30" fill="none">
                        <path d="M0 25 L15 20 L30 22 L45 15 L60 18 L75 8 L90 12 L100 4" stroke="currentColor" strokeWidth="1" />
                        <line x1="0" y1="20" x2="100" y2="20" stroke="rgba(255,255,255,0.06)" strokeDasharray="2 2" />
                      </svg>
                    </div>
                    <div className="flex justify-between items-center mt-2.5">
                      <span>RSI: 62.4</span>
                      <span>Support: $292.00</span>
                      <span>Resistance: $315.00</span>
                    </div>
                  </div>
                </div>
              )}

              {activeModal === "fundamental" && (
                <div className="space-y-4">
                  <div className="flex items-center gap-2">
                    <Landmark size={18} className="text-[#FFBA9D]" />
                    <div>
                      <h3 className="text-white font-bold text-sm">Fundamental Analysis Layer</h3>
                      <p className="text-[8.5px] text-slate-500 uppercase tracking-widest font-mono">BALANCE SHEET FILES</p>
                    </div>
                  </div>
                  <p className="text-slate-350 text-xs leading-relaxed font-light">
                    Aggregates YoY compound revenue and net growth metrics to determine safety ratings, checking standard valuation multiples against historical industry averages.
                  </p>
                  <div className="bg-[#05060f] rounded border border-white/5 p-4 flex flex-col justify-between font-mono text-[9px] text-slate-400 font-bold">
                    <div className="flex items-center justify-between border-b border-white/5 pb-2 mb-3">
                      <span className="text-slate-500 font-mono">YOY NET MARGIN ANALYSIS</span>
                      <span className="text-[#FFBA9D]">HEALTH: 88/100</span>
                    </div>
                    <div className="flex justify-around items-end h-20 border-b border-slate-800 pb-1">
                      <div className="flex flex-col items-center gap-1 font-normal">
                        <div className="w-5 bg-slate-800 rounded-t h-8" />
                        <span className="text-[7.5px] text-slate-500">2023</span>
                      </div>
                      <div className="flex flex-col items-center gap-1 font-normal">
                        <div className="w-5 bg-slate-800 rounded-t h-12" />
                        <span className="text-[7.5px] text-slate-500">2024</span>
                      </div>
                      <div className="flex flex-col items-center gap-1 font-normal">
                        <div className="w-5 bg-orange-500/50 rounded-t h-16" />
                        <span className="text-[7.5px] text-slate-500">2025</span>
                      </div>
                      <div className="flex flex-col items-center gap-1 font-normal font-mono">
                        <div className="w-5 bg-[#FFBA9D] rounded-t h-20" />
                        <span className="text-[7.5px] text-[#FFBA9D]">2026(E)</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {activeModal === "sentiment" && (
                <div className="space-y-4">
                  <div className="flex items-center gap-2">
                    <Newspaper size={18} className="text-[#FFBA9D]" />
                    <div>
                      <h3 className="text-white font-bold text-sm">News Intelligence Layer</h3>
                      <p className="text-[8.5px] text-slate-500 uppercase tracking-widest font-mono">SENTIMENT INDICES</p>
                    </div>
                  </div>
                  <p className="text-slate-350 text-xs leading-relaxed font-light">
                    Aggregates headlines from Google News search index, filtering catalysts and tagging positive/negative ratios using a specialized lexicon dictionary model.
                  </p>
                  <div className="bg-[#05060f] rounded border border-white/5 p-4 flex flex-col justify-between font-mono text-[9px] text-slate-400 space-y-2.5">
                    <div className="flex items-center justify-between border-b border-white/5 pb-2">
                      <span className="text-slate-500">REAL-TIME NEWS HARVESTER</span>
                      <span className="text-[#FFBA9D]">ACTIVE SCAN</span>
                    </div>
                    <div className="space-y-1.5 font-sans">
                      <div className="bg-[#0c0d18] p-2 rounded border border-white/5 flex justify-between items-center text-[9.5px]">
                        <span className="text-white truncate max-w-[200px]">Enterprise announces global software deal...</span>
                        <span className="text-[7.5px] text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded font-mono font-bold shrink-0">Positive</span>
                      </div>
                      <div className="bg-[#0c0d18] p-2 rounded border border-white/5 flex justify-between items-center text-[9.5px]">
                        <span className="text-white truncate max-w-[200px]">Analysts issue warning on rate valuations...</span>
                        <span className="text-[7.5px] text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded font-mono font-bold shrink-0">Neutral</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default LandingPage;
