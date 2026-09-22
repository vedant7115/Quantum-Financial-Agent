# fundamental_agent.py
# The Fundamental Agent evaluates company financials, ratios, and growth.
# Incorporates Groq LLM reasoning with a deterministic fallback engine.

import os
import json
import logging
from services.llm_service import query_groq

logger = logging.getLogger("quantum_agent.fundamental_agent")

def analyze(stock_data: dict) -> dict:
    """
    Evaluates company balance sheet, earnings metrics, and multipliers.
    Attempts to prompt Groq to generate explainable financial summaries,
    strengths, weaknesses, health indices, and growth commentary.
    
    Falls back to mathematical scoring rules if Groq fails or key is missing.
    """
    pe_ratio = stock_data.get("pe_ratio")
    rev_growth = stock_data.get("revenue_growth", 0.0)
    earn_growth = stock_data.get("earnings_growth", 0.0)
    total_rev = stock_data.get("total_revenue", 0.0)
    net_inc = stock_data.get("net_income", 0.0)
    market_cap = stock_data.get("market_cap", "N/A")
    symbol = stock_data.get("symbol", "Ticker")
    
    reasons = []
    
    # ── Calculated Core (Fallback Metrics) ──
    # Health Index (0-100)
    health_points = 0
    if total_rev > 0:
        margin = (net_inc / total_rev) * 100
        if margin >= 20.0:
            health_points += 40
            reasons.append("high double-digit profit margins")
        elif margin >= 8.0:
            health_points += 25
            reasons.append("stable profit margins")
        elif margin > 0:
            health_points += 15
            reasons.append("thin but positive profit margins")
        else:
            health_points -= 10
            reasons.append("negative margins indicating unprofitability")
    else:
        if net_inc > 0:
            health_points += 25
            reasons.append("positive earnings performance")
        else:
            health_points -= 5
            reasons.append("deficit in net income")

    if "T" in market_cap:
        health_points += 50
    elif "B" in market_cap:
        try:
            val_b = float(market_cap.replace("$", "").replace("B", "").strip())
            health_points += 45 if val_b >= 100.0 else 35
        except ValueError:
            health_points += 30
    else:
        health_points += 15
        reasons.append("higher capital vulnerability as a small-cap")
        
    calculated_health = min(100, max(0, health_points))
    
    # Valuation Index (0-100)
    if pe_ratio is None or pe_ratio <= 0.0:
        calculated_valuation = 15
        reasons.append("unprofitable or lack of valuation multiplier")
    elif pe_ratio < 12.0:
        calculated_valuation = 95
        reasons.append("highly attractive valuation multiple")
    elif pe_ratio <= 22.0:
        calculated_valuation = 80
        reasons.append("fair value PE valuation")
    elif pe_ratio <= 35.0:
        calculated_valuation = 55
        reasons.append("moderate valuation premium")
    elif pe_ratio <= 60.0:
        calculated_valuation = 35
        reasons.append("elevated premium valuation")
    else:
        calculated_valuation = 15
        reasons.append("highly expensive earnings multiple")
        
    # Growth Index (0-100)
    avg_growth = (rev_growth + earn_growth) / 2
    if avg_growth >= 25.0:
        calculated_growth = 95
        reasons.append("hyper-growth profile")
    elif avg_growth >= 12.0:
        calculated_growth = 80
        reasons.append("strong top and bottom line expansion")
    elif avg_growth >= 4.0:
        calculated_growth = 55
        reasons.append("moderate organic growth")
    elif avg_growth >= 0.0:
        calculated_growth = 40
        reasons.append("sluggish capital growth")
    else:
        calculated_growth = 15
        reasons.append("negative contracting growth")
        
    # Consolidated Overall Verdict
    cons_score = int(calculated_health * 0.4 + calculated_valuation * 0.3 + calculated_growth * 0.3)
    
    if cons_score >= 70:
        calculated_fundamental = "Strong"
        calculated_confidence = min(98, cons_score)
        calculated_reason = f"Excellent fundamental posture led by {reasons[0] if reasons else 'stable balance sheet'}."
    elif cons_score >= 45:
        calculated_fundamental = "Average"
        calculated_confidence = 65
        calculated_reason = f"Mixed fundamentals with {reasons[0] if reasons else 'stable metrics'}."
    else:
        calculated_fundamental = "Weak"
        calculated_confidence = min(90, 100 - cons_score)
        calculated_reason = f"Deficient fundamental metrics characterized by {reasons[-1] if reasons else 'valuation pressures'}."

    # Rules fallback list builders
    rule_strengths = [r for r in reasons if "margin" in r or "growth" in r or "value" in r] or ["Capital preservation structure"]
    rule_weaknesses = [r for r in reasons if "negative" in r or "deficit" in r or "expensive" in r] or ["Valuation premium risk"]

    raw_metrics = {
        "pe_ratio": pe_ratio,
        "revenue_growth_pct": rev_growth,
        "earnings_growth_pct": earn_growth,
        "market_cap": market_cap,
        "total_revenue": total_rev,
        "net_income": net_inc
    }

    # ── LLM Orchestration & Fallback check ──
    enable_subagent_llm = os.getenv("ENABLE_SUBAGENT_LLM", "false").lower() == "true"
    groq_api_key = os.getenv("GROQ_API_KEY")
    if groq_api_key and enable_subagent_llm:
        try:
            logger.info("GROQ_API_KEY detected. Prompting Groq fundamental analysis agent...")
            
            prompt = f"""
You are an expert fundamental analyst. Analyze the corporate finance records for {symbol}:
Market Capitalization: {market_cap}
Total Revenue: ${total_rev:,.2f}
Net Income: ${net_inc:,.2f}
P/E Ratio: {pe_ratio if pe_ratio else 'N/A'}x
Year-over-Year Revenue Growth: {rev_growth:.1f}%
Year-over-Year Earnings Growth: {earn_growth:.1f}%

Calculate institutional indexes and audit details.
Return ONLY a valid JSON object matching this structure:
{{
  "health_score": 0-100 (integer representing financial health and solvency),
  "valuation_score": 0-100 (integer representing valuation attractiveness/safety),
  "growth_score": 0-100 (integer representing growth momentum),
  "summary": "financial health summary, growth analysis, and valuation commentary (1-2 paragraphs)",
  "strengths": ["list of company financial strengths (e.g. attractive P/E, strong cashflow)"],
  "weaknesses": ["list of corporate weaknesses/risks (e.g. high debt, slow growth)"],
  "growth_outlook": "explain the company's growth outlook and trajectory for investors",
  "valuation_outlook": "explain the company's valuation outlook, PE multiple rationale, and pricing safety",
  "ai_commentary": "overall institutional investment analysis of corporate fundamental quality (1 paragraph)"
}}

Return ONLY the raw JSON. Do not write markdown tags or backticks (no ```json).
"""
            llm_text = query_groq(prompt)
            llm_res = json.loads(llm_text)
            
            # Map LLM score back to fundamental rating
            health = int(llm_res.get("health_score", calculated_health))
            val = int(llm_res.get("valuation_score", calculated_valuation))
            gro = int(llm_res.get("growth_score", calculated_growth))
            
            avg_score = int(health * 0.4 + val * 0.3 + gro * 0.3)
            
            if avg_score >= 70:
                fundamental = "Strong"
                confidence = min(98, avg_score)
            elif avg_score >= 45:
                fundamental = "Average"
                confidence = 65
            else:
                fundamental = "Weak"
                confidence = min(90, 100 - avg_score)
                
            return {
                "fundamental": fundamental,
                "confidence": confidence,
                "reason": llm_res.get("summary", calculated_reason),
                "summary": llm_res.get("summary", calculated_reason),
                "health_score": health,
                "valuation_score": val,
                "growth_score": gro,
                "strengths": llm_res.get("strengths", rule_strengths),
                "weaknesses": llm_res.get("weaknesses", rule_weaknesses),
                "metrics": raw_metrics,
                "fallback_active": False,
                "growth_outlook": llm_res.get("growth_outlook", f"YoY revenue growth stands at {rev_growth:.1f}% and earnings expansion at {earn_growth:.1f}%."),
                "valuation_outlook": llm_res.get("valuation_outlook", f"The trailing P/E ratio is at {pe_ratio if pe_ratio else 'N/A'}x, representing {fundamental.lower()} value pricing."),
                "ai_commentary": llm_res.get("ai_commentary", f"Fundamental posture is evaluated as {fundamental.lower()} with health index at {health}/100 and growth index at {gro}/100.")
            }
            
        except Exception as e:
            logger.warning(f"Groq Fundamental Agent reasoning failed: {str(e)}. Fallback to rule engine.")
            # Fall back to local calculation below
            
    # ── Fallback Return ──
    return {
        "fundamental": calculated_fundamental,
        "confidence": calculated_confidence,
        "reason": calculated_reason,
        "summary": calculated_reason,
        "health_score": calculated_health,
        "valuation_score": calculated_valuation,
        "growth_score": calculated_growth,
        "strengths": rule_strengths,
        "weaknesses": rule_weaknesses,
        "metrics": raw_metrics,
        "fallback_active": True,
        "growth_outlook": f"YoY revenue growth stands at {rev_growth:.1f}% and earnings expansion at {earn_growth:.1f}%.",
        "valuation_outlook": f"The trailing P/E ratio is at {pe_ratio if pe_ratio else 'N/A'}x, representing {calculated_fundamental.lower()} value pricing.",
        "ai_commentary": f"Fundamental posture is evaluated as {calculated_fundamental.lower()} with health index at {calculated_health}/100 and growth index at {calculated_growth}/100."
    }
