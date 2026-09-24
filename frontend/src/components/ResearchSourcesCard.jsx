import React from "react";
import { Share2, ShieldCheck, Database, Award } from "lucide-react";

export default function ResearchSourcesCard({ systemStatus, totalArticles, isFallbackActive }) {
  if (!systemStatus) return null;

  const { groq_status, execution_time_sec } = systemStatus;

  const groqLower = (groq_status || "").toLowerCase();
  const aiCalls = groqLower === "online" ? 1 : 0;
  const aiModel = groqLower === "fallback mode" ? "Heuristic Rules (Fallback)" : "OpenAI GPT-OSS-20B (Groq)";

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-6 fade-in-up" style={{ animationDelay: "0.2s" }}>
      
      {/* ── Research Sources Section (Left) ── */}
      <div className="bg-[#0a0c16] border border-white/10 rounded p-5 flex flex-col justify-between">
        <div className="space-y-4">
          <div className="flex items-center justify-between border-b border-white/5 pb-3">
            <span className="text-[10px] font-mono text-slate-500 font-bold uppercase tracking-wider">DATA ATTRIBUTION & CITATIONS</span>
            <h3 className="text-white font-black text-base mt-1 flex items-center gap-1.5 font-mono">
              <Database size={16} className="text-blue-400" /> Research Sources
            </h3>
          </div>

          <div className="space-y-2.5 font-mono text-[11px]">
            {/* Market Data */}
            <div className="flex justify-between items-center border-b border-white/5 pb-2">
              <span className="text-slate-400">Market Data Source</span>
              <div className="text-right">
                <span className="text-white font-bold block">Yahoo Finance API</span>
                <span className="text-[9px] text-emerald-400 font-bold block mt-0.5 uppercase">Status: Live (Real-time)</span>
              </div>
            </div>

            {/* News Intelligence */}
            <div className="flex justify-between items-center border-b border-white/5 pb-2">
              <span className="text-slate-400">News Feed Core</span>
              <div className="text-right">
                <span className="text-white font-bold block">Google News RSS Feed</span>
                <span className="text-[9px] text-emerald-400 font-bold block mt-0.5 uppercase">Status: Live (Scraped)</span>
              </div>
            </div>

            {/* AI Gateway */}
            <div className="flex justify-between items-center border-b border-white/5 pb-2">
              <span className="text-slate-400">AI Reasoning Engine</span>
              <div className="text-right">
                <span className="text-white font-bold block">Groq Cloud API</span>
                <span className={`text-[9px] font-bold block mt-0.5 uppercase ${groqLower === "online" ? "text-emerald-450 text-emerald-400" : "text-amber-400 animate-pulse"}`}>
                  Status: {groq_status}
                </span>
              </div>
            </div>

            {/* Technical Calculations */}
            <div className="flex justify-between items-center border-b border-white/5 pb-2">
              <span className="text-slate-400">Technical Math Engine</span>
              <div className="text-right">
                <span className="text-white font-bold block">Local Quant Processor</span>
                <span className="text-[9px] text-emerald-400 font-bold block mt-0.5 uppercase">Status: Active (Real-time)</span>
              </div>
            </div>

            {/* Consensus Agent */}
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Consensus Synthesis</span>
              <div className="text-right">
                <span className="text-white font-bold block">Quantum Master Synthesis</span>
                <span className="text-[9px] text-emerald-400 font-bold block mt-0.5 uppercase">Status: Active</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── Research Authenticity Panel (Right) ── */}
      <div className="bg-[#0a0c16] border border-white/10 rounded p-5 flex flex-col justify-between">
        <div className="space-y-4">
          <div className="flex items-center justify-between border-b border-white/5 pb-3">
            <span className="text-[10px] font-mono text-slate-500 font-bold uppercase tracking-wider">COMPLIANCE & PROCESS LOG</span>
            <h3 className="text-white font-black text-base mt-1 flex items-center gap-1.5 font-mono">
              <ShieldCheck size={16} className="text-emerald-400" /> Authenticity Audit
            </h3>
          </div>

          <div className="space-y-3 font-mono text-[11px]">
            {/* Tech Indicators */}
            <div className="flex justify-between border-b border-white/5 pb-1.5">
              <span className="text-slate-400">Technical Indicators Calculated</span>
              <span className="text-white font-bold">18</span>
            </div>

            {/* Articles Ingested */}
            <div className="flex justify-between border-b border-white/5 pb-1.5">
              <span className="text-slate-400">News Articles Analyzed</span>
              <span className="text-white font-bold">{totalArticles || 0} Articles</span>
            </div>

            {/* AI Call count */}
            <div className="flex justify-between border-b border-white/5 pb-1.5">
              <span className="text-slate-400">Groq AI Calls Executed</span>
              <span className="text-white font-bold">{aiCalls} API Queries</span>
            </div>

            {/* Model Name */}
            <div className="flex justify-between border-b border-white/5 pb-1.5">
              <span className="text-slate-400">Active Inference Model</span>
              <span className="text-white font-bold">{aiModel}</span>
            </div>

            {/* Time Elapsed */}
            <div className="flex justify-between border-b border-white/5 pb-1.5">
              <span className="text-slate-400">Execution Processing Duration</span>
              <span className="text-blue-400 font-bold">{execution_time_sec} Seconds</span>
            </div>

            {/* Data Pipeline Verification */}
            <div className="flex justify-between">
              <span className="text-slate-400">Platform Security Gate</span>
              <span className="text-emerald-450 text-emerald-400 font-bold uppercase">Rate Limited (OK)</span>
            </div>
          </div>
        </div>
      </div>

    </div>
  );
}
