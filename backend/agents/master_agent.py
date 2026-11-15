# master_agent.py
# The Master Agent acts as the final aggregator of sub-agent decisions.
# Implements mathematical confidence and risk formulas alongside Groq LLM synthesis.
# Preserves strict fallbacks to avoid failure.

import os
import json
import logging
import re
from datetime import date, datetime
from services.llm_service import query_groq


def _drop_past_catalysts(calendar: list) -> list:
    """Removes catalyst entries whose date is clearly in the past. The model has
    no calendar, so it sometimes lists events that have already happened."""
    today = date.today()
    kept = []
    for item in calendar:
        text = str(item.get("expected_date", "")) if isinstance(item, dict) else ""
        match = re.search(r"\b(20\d{2})-(\d{2})-(\d{2})\b", text)
        if match:
            try:
                if datetime.strptime(match.group(0), "%Y-%m-%d").date() < today:
                    continue
            except ValueError:
                pass
        kept.append(item)
    return kept

logger = logging.getLogger("quantum_agent.master_agent")

def analyze(technical: dict, fundamental: dict, sentiment: dict) -> dict:
    """
    Synthesizes outcomes from Technical, Fundamental, and Sentiment agents.
    
    1. Calculates Master Confidence using weights: 40% Tech, 35% Fund, 25% Sent.
    2. Calculates Master Risk Score based on agent disagreement range, 
       volatility, and news ratio uncertainty.
    3. Prompts Groq to generate the final Executive Summary, Key Drivers, and Watchlist.
       Strictly forbids direct BUY/SELL/HOLD recommendations to avoid investment advice.
       
    Falls back to mathematical aggregations on Groq errors.
    """
    # ── 1. Calculate Master Confidence (Weighted Consensus) ──
    tech_conf = technical.get("confidence", 50)
    fund_conf = fundamental.get("confidence", 50)
    sent_conf = sentiment.get("confidence", 50)
    
    # When fundamentals could not be fetched that agent is left out and the
    # remaining weights are scaled up, rather than counting it as a negative.
    fund_available = fundamental.get("data_available", True)
    if fund_available:
        w_tech, w_fund, w_sent = 0.40, 0.35, 0.25
    else:
        w_tech, w_fund, w_sent = 0.40 / 0.65, 0.0, 0.25 / 0.65

    calculated_confidence = int(
        (tech_conf * w_tech) + 
        (fund_conf * w_fund) + 
        (sent_conf * w_sent)
    )

    # ── 2. Calculate Master Risk Score (Explainable Logic) ──
    # A. Disagreement risk mapping
    def score_map(val: str) -> float:
        v = val.lower() if val else ""
        if v in {"bullish", "strong", "positive"}:
            return 1.0
        elif v in {"bearish", "weak", "negative"}:
            return -1.0
        return 0.0 # Neutral / Average

    t_score = score_map(technical.get("trend"))
    f_score = score_map(fundamental.get("fundamental"))
    s_score = score_map(sentiment.get("sentiment"))
    
    scores = [t_score, f_score, s_score] if fund_available else [t_score, s_score]
    disagreement_range = max(scores) - min(scores) # 0.0 to 2.0
    disagreement_risk = disagreement_range * 35 # 0, 35, or 70 points
    
    # B. Volatility risk mapping
    volatility = technical.get("volatility", 20.0)
    volatility_risk = 20 if volatility >= 35.0 else (10 if volatility >= 20.0 else 0)
    
    # C. News uncertainty risk mapping
    pos_ratio = sentiment.get("positive_ratio", 0.5)
    news_uncertainty = 10 if (0.4 <= pos_ratio <= 0.6 and len(sentiment.get("positive_drivers", [])) > 0) else 0
    
    # Combine
    total_risk_score = disagreement_risk + volatility_risk + news_uncertainty
    if total_risk_score >= 65:
        calculated_risk = "High"
    elif total_risk_score >= 35:
        calculated_risk = "Medium"
    else:
        calculated_risk = "Low"

    # ── 3. Rule-Based Bias Fallback ──
    weighted_score = (t_score * w_tech) + (f_score * w_fund) + (s_score * w_sent)
    if weighted_score >= 0.25:
        calculated_bias = "Bullish"
    elif weighted_score <= -0.25:
        calculated_bias = "Bearish"
    else:
        calculated_bias = "Neutral"

    # Key drivers fallback list
    rule_drivers = [
        f"Technical Agent indicates {technical.get('trend')} trend with {technical.get('trend_strength','moderate').lower()} strength.",
        (f"Fundamental Agent reports {fundamental.get('fundamental')} company metrics (Health: {fundamental.get('health_score')}/100)."
         if fund_available else
         "Company financials were unavailable, so this view rests on price action and news only."),
        f"Sentiment Agent evaluates news narrative as {sentiment.get('sentiment')}."
    ]
    
    rule_watchlist = [
        f"Monitor Support boundary at ${technical.get('support_level', 0.0):.2f} and Resistance ceiling at ${technical.get('resistance_level', 0.0):.2f}."
    ]

    distance_to_support = technical.get("distance_to_support", 5.0)
    distance_to_resistance = technical.get("distance_to_resistance", 5.0)
    
    rule_risks = []
    if volatility >= 35.0:
        rule_risks.append(f"High asset volatility ({volatility:.1f}%) creates structural correction risks.")
    if distance_to_resistance < 3.0:
        rule_risks.append(f"Approaching key overhead resistance ceiling at ${technical.get('resistance_level', 0.0):.2f}.")
    if technical.get("trend_strength") == "Weak":
        rule_risks.append("Weak technical trend direction increases market exposure risk.")
    if sentiment.get("sentiment") == "Negative":
        rule_risks.append("Bearish public news sentiment could depress buying interest.")
    if not rule_risks:
        rule_risks = ["Macroeconomic headwinds or regulatory risk changes in this sector."]

    rule_catalysts = []
    if distance_to_support < 3.0:
        rule_catalysts.append(f"Approaching historical support level at ${technical.get('support_level', 0.0):.2f} could trigger buying support.")
    if fundamental.get("growth_score", 50) >= 75:
        rule_catalysts.append("Strong YoY company revenue expansion acts as an ongoing upward valuation catalyst.")
    if not rule_catalysts:
        rule_catalysts = ["Upcoming corporate earnings release or sector product announcements."]
    
    rule_risk_register = [
        {
            "category": "Competition Risk",
            "severity": "Medium",
            "probability": "Medium",
            "explanation": "Market saturation and rival product development may compress pricing margins."
        },
        {
            "category": "Valuation Risk",
            "severity": "Medium" if fundamental.get("valuation_score", 50) >= 40 else "High",
            "probability": "Medium",
            "explanation": f"Trading at PE multiple of {fundamental.get('metrics', {}).get('pe_ratio', 'N/A')}x, subject to valuation multiple compression."
        },
        {
            "category": "Market Risk",
            "severity": "High" if volatility >= 30.0 else "Medium",
            "probability": "High" if volatility >= 20.0 else "Medium",
            "explanation": f"Annualized asset volatility stands at {volatility:.1f}%, raising structural drawdown probability."
        },
        {
            "category": "Execution Risk",
            "severity": "Medium",
            "probability": "Low",
            "explanation": "Operational and supply chain execution challenges under tight macroeconomic environments."
        },
        {
            "category": "Macro Risk",
            "severity": "Medium",
            "probability": "Medium",
            "explanation": "Global interest rate policies, inflation pressures, and capital market fluctuations."
        },
        {
            "category": "Regulatory Risk",
            "severity": "Low" if sentiment.get("sentiment") != "Negative" else "Medium",
            "probability": "Medium" if sentiment.get("sentiment") == "Negative" else "Low",
            "explanation": "Compliance, antitrust laws, or policy shifts that could impact business operations."
        }
    ]

    rule_catalyst_calendar = [
        {
            "event": "Earnings Release",
            "expected_date": "Next Quarter",
            "importance": "High",
            "potential_impact": "Verify top and bottom line expansion rates and margin sustainability."
        },
        {
            "event": "Product Launch",
            "expected_date": "Next 6 Months",
            "importance": "Medium",
            "potential_impact": "Introduction of key feature sets to bolster competitive advantages."
        },
        {
            "event": "Investor Day",
            "expected_date": "Upcoming Date",
            "importance": "Medium",
            "potential_impact": "Strategic executive updates regarding long-term revenue targets."
        },
        {
            "event": "Major Economic Event",
            "expected_date": "Ongoing",
            "importance": "High",
            "potential_impact": "Fed rate decisions and macroeconomic indicator releases affecting equity beta."
        }
    ]

    rule_bull_case = [
        f"Technical indicators highlight a {technical.get('trend')} posture with {technical.get('trend_strength','moderate').lower()} trend strength.",
        f"Fundamental metrics exhibit {fundamental.get('fundamental').lower()} financial health (Score: {fundamental.get('health_score')}/100).",
        f"Sentiment signals are predominantly {sentiment.get('sentiment').lower()} with catalysts emerging from news events."
    ]
    rule_bear_case = [
        f"Volatile market patterns (volatility: {volatility:.1f}%) could trigger sudden technical drawdowns.",
        f"Valuation multiples are pricing in a premium (PE: {fundamental.get('metrics', {}).get('pe_ratio', 'N/A')}x), risking re-rating.",
        f"Negative headlines or sector headwinds may damp near-term investor interest."
    ]
    if not fund_available:
        rule_bull_case[1] = "Company financials were unavailable; the fundamental case could not be assessed."
        rule_bear_case[1] = "Without financial data, valuation and balance-sheet risk are unknown."

    calculated_summary = (
        f"Orchestrated analysis indicates a **{calculated_bias}** market bias with "
        f"an aggregated confidence score of **{calculated_confidence}%** and a **{calculated_risk}** risk profile. "
        f"Technical momentum aligns as {technical.get('trend')}, "
        + (f"coupled with a fundamental health index of {fundamental.get('health_score')}/100 " if fund_available
           else "company financials were unavailable and are not part of this view, ")
        + f"and sentiment drivers matching {sentiment.get('sentiment')}."
    )

    if fund_available:
        fundamental_block = f"""- Solvency/Posture: {fundamental.get('fundamental')}
- Confidence: {fundamental.get('confidence')}%
- Health Score: {fundamental.get('health_score')}/100
- Valuation Score: {fundamental.get('valuation_score')}/100
- Growth Score: {fundamental.get('growth_score')}/100
- Strengths: {fundamental.get('strengths')}
- Weaknesses: {fundamental.get('weaknesses')}
- Summary: {fundamental.get('summary')}"""
    else:
        fundamental_block = """- DATA UNAVAILABLE. Company financials could not be retrieved.
- Do NOT describe the company's financial health, profitability, valuation or growth.
- State once in the summary that fundamentals were unavailable and that the view
  rests on technicals and news only."""

    # ── LLM Synthesis & Fallback orchestrator ──
    groq_api_key = os.getenv("GROQ_API_KEY")
    if groq_api_key:
        try:
            logger.info("GROQ_API_KEY detected. Prompting Groq Master Synthesis agent...")
            
            prompt = f"""
You are an institutional financial analyst. Synthesize the reports from 3 specialized sub-agents:

[TECHNICAL ANALYSIS REPORT]
- Trend Bias: {technical.get('trend')}
- Confidence: {technical.get('confidence')}%
- Support Level: ${technical.get('support_level')}
- Resistance Level: ${technical.get('resistance_level')}
- Distance to Support: {technical.get('distance_to_support')}%
- Distance to Resistance: {technical.get('distance_to_resistance')}%
- Annualized Volatility: {technical.get('volatility')}%
- Multi-Timeframe Trend Structures (SMA-20): {technical.get('timeframe_analysis')}
- Signals Triggered: {technical.get('signals')}
- Technical Risk Factors: {technical.get('risk_factors')}
- Summary: {technical.get('summary')}

[FUNDAMENTAL ANALYSIS REPORT]
{fundamental_block}

[HEADLINE SENTIMENT REPORT]
- Narrative Verdict: {sentiment.get('sentiment')}
- Confidence: {sentiment.get('confidence')}%
- Sentiment Drivers (Positive): {sentiment.get('positive_drivers')}
- Sentiment Drivers (Negative): {sentiment.get('negative_drivers')}
- Events Tagged: {sentiment.get('events')}
- Summary: {sentiment.get('summary')}

[CALCULATED CONSENSUS]
- Weighted Consensus Confidence: {calculated_confidence}%
- Evaluated Risk Classification: {calculated_risk}

Synthesize these inputs. Today's date is {date.today().isoformat()}.
CRITICAL INSTRUCTIONS:
- You must NOT provide direct investment advice.
- You must NOT recommend BUY, HOLD, or SELL. Only explain market intelligence.
- Determine the overall Market Bias as Bullish, Bearish, or Neutral.
- The risk level should be consistent with the calculated risk: {calculated_risk}.
- The confidence should be consistent with the calculated weighted confidence: {calculated_confidence}%.

Return ONLY a valid JSON object matching this structure:
{{
  "market_bias": "Bullish" | "Bearish" | "Neutral",
  "confidence": {calculated_confidence} (keep this exact value),
  "risk": "{calculated_risk}" (keep this exact value),
  "key_drivers": ["list of primary consensus drivers across technicals, fundamentals, and news"],
  "watchlist_factors": ["list of target watchlist triggers, price levels, or catalysts to monitor"],
  "potential_risks": ["list of structural risks or downside catalysts specific to this analysis"],
  "future_catalysts": ["list of upside drivers or catalyst events to monitor"],
  "summary": "comprehensive executive synthesis narrative integrating all agents (2 paragraphs)",
  "bull_case": ["list of 3 points explaining why bulls are right, using technical, fundamental, and sentiment data"],
  "bear_case": ["list of 3 points explaining why bears are right, using technical, fundamental, and sentiment data"],
  "risk_register": [
    {{
      "category": "Competition Risk" | "Valuation Risk" | "Market Risk" | "Execution Risk" | "Macro Risk" | "Regulatory Risk",
      "severity": "Low" | "Medium" | "High",
      "probability": "Low" | "Medium" | "High",
      "explanation": "Specific explanation of this risk factor for this stock."
    }}
  ],
  "catalyst_calendar": [
    {{
      "event": "Earnings Release" | "Product Launch" | "Investor Day" | "Major Economic Event" | "Industry Event",
      "expected_date": "Approximate timeframe after today's date. Only give an exact date if it appears in the inputs above; otherwise use a timeframe such as 'Next quarter'",
      "importance": "Low" | "Medium" | "High",
      "potential_impact": "Details of potential stock price impact."
    }}
  ]
}}

Return ONLY the raw JSON. Do not write markdown tags or backticks (no ```json).
"""
            llm_text = query_groq(prompt)
            llm_res = json.loads(llm_text)
            
            # Post-process catalyst calendar expected_date to ensure years align with 2026 or later
            catalyst_calendar = llm_res.get("catalyst_calendar", rule_catalyst_calendar)
            if isinstance(catalyst_calendar, list):
                catalyst_calendar = _drop_past_catalysts(catalyst_calendar)
            else:
                catalyst_calendar = rule_catalyst_calendar

            return {
                "market_bias": llm_res.get("market_bias", calculated_bias),
                "confidence": int(llm_res.get("confidence", calculated_confidence)),
                "risk": llm_res.get("risk", calculated_risk),
                "key_drivers": llm_res.get("key_drivers", rule_drivers),
                "watchlist_factors": llm_res.get("watchlist_factors", rule_watchlist),
                "potential_risks": llm_res.get("potential_risks", rule_risks),
                "future_catalysts": llm_res.get("future_catalysts", rule_catalysts),
                "summary": llm_res.get("summary", calculated_summary),
                "fallback_active": False,
                "bull_case": llm_res.get("bull_case", rule_bull_case),
                "bear_case": llm_res.get("bear_case", rule_bear_case),
                "risk_register": llm_res.get("risk_register", rule_risk_register),
                "catalyst_calendar": catalyst_calendar
            }
            
        except Exception as e:
            logger.warning(f"Groq Master Agent synthesis failed: {str(e)}. Fallback to rule engine.")
            # Fall back to standard rule engine calculations
            
    # ── Fallback Return ──
    return {
        "market_bias": calculated_bias,
        "confidence": calculated_confidence,
        "risk": calculated_risk,
        "key_drivers": rule_drivers,
        "watchlist_factors": rule_watchlist,
        "potential_risks": rule_risks,
        "future_catalysts": rule_catalysts,
        "summary": calculated_summary,
        "fallback_active": True,
        "bull_case": rule_bull_case,
        "bear_case": rule_bear_case,
        "risk_register": rule_risk_register,
        "catalyst_calendar": rule_catalyst_calendar
    }
