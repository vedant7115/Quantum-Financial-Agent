// Header.jsx — Top navigation bar
// Displays the QUANTUM AGENT logo and nav links.

import React from "react";

// Navigation page options
const NAV_ITEMS = ["Home", "Dashboard", "Architecture"];

function Header({ currentPage, setCurrentPage }) {
  return (
    <header className="border-b border-white/5 bg-[#060816]/85 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">

        {/* ── Logo ───────────────────────────────────────────────────────── */}
        <div className="flex items-center gap-3 cursor-pointer" onClick={() => setCurrentPage("Home")}>
          <img 
            src="/LOGO.jpeg" 
            alt="Quantum Logo" 
            className="w-9 h-9 rounded-lg object-contain shadow-lg"
          />

          <div>
            <h1 className="font-bold text-lg tracking-wider text-white" style={{ fontFamily: "'General Sans', sans-serif" }}>
              QUANTUM
            </h1>
            <p className="text-[10px] text-slate-500 font-semibold uppercase tracking-wide -mt-0.5">Financial Intelligence</p>
          </div>
        </div>

        {/* ── Navigation Links ────────────────────────────────────────────── */}
        <nav className="flex items-center gap-1.5">
          {NAV_ITEMS.map((page) => (
            <button
              key={page}
              onClick={() => setCurrentPage(page)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold tracking-wide transition-all duration-200 ${
                currentPage === page
                  ? "bg-blue-600/10 text-blue-400 border border-blue-500/20"
                  : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
              }`}
            >
              {page}
            </button>
          ))}
        </nav>
      </div>
    </header>
  );
}

export default Header;
