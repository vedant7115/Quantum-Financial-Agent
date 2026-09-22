# technical_agent.py
# Technical Analysis Agent combining code mathematical indicators 
# with Groq LLM logic and robust local engine fallbacks.

import os
import json
import logging
from services.llm_service import query_groq

logger = logging.getLogger("quantum_agent.technical_agent")

def calculate_timeframe_trends(timeframe_data: dict) -> dict:
    """Calculates SMA-20 trend direction across multiple timeframes."""
    trends = {}
    tf_list = ["15m", "1h", "4h", "1d", "1w"]
    
    if not timeframe_data:
        return {tf: "Neutral" for tf in tf_list}
        
    for tf in tf_list:
        prices = timeframe_data.get(tf, [])
        if len(prices) >= 20:
            # 20-period SMA
            sma_20 = sum(prices[-20:]) / 20.0
            last_price = prices[-1]
            
            # Simple SMA comparison
            if last_price > sma_20:
                if last_price > sma_20 * 1.02:
                    trends[tf] = "Strong Bullish"
                else:
                    trends[tf] = "Bullish"
            elif last_price < sma_20:
                if last_price < sma_20 * 0.98:
                    trends[tf] = "Strong Bearish"
                else:
                    trends[tf] = "Bearish"
            else:
                trends[tf] = "Neutral"
        elif len(prices) > 0:
            # Fallback for shorter arrays (compare to first element or mean)
            last_price = prices[-1]
            first_price = prices[0]
            if last_price > first_price:
                trends[tf] = "Bullish"
            elif last_price < first_price:
                trends[tf] = "Bearish"
            else:
                trends[tf] = "Neutral"
        else:
            trends[tf] = "Neutral"
            
    return trends

def analyze(stock_data: dict, timeframe_data: dict = None) -> dict:
    """
    Evaluates stock variables and timeframes.
    Attempts to execute llama-3.3-70b-versatile reasoning via Groq.
    Preserves exact mathematical calculations for support, resistance, volatility, 
    and multi-timeframes.
    
    Falls back to rule-based engine if Groq fails or key is missing.
    """
    price = stock_data.get("price", 0.0)
    rsi = stock_data.get("rsi", 50.0)
    macd = stock_data.get("macd", 0.0)
    macd_signal = stock_data.get("macd_signal", 0.0)
    macd_hist = stock_data.get("macd_hist", 0.0)
    ma_50 = stock_data.get("moving_avg_50", price)
    ma_200 = stock_data.get("moving_avg_200", price)
    support = stock_data.get("support", price * 0.95)
    resistance = stock_data.get("resistance", price * 1.05)
    support_level = stock_data.get("support_level", support)
    resistance_level = stock_data.get("resistance_level", resistance)
    distance_to_support = stock_data.get("distance_to_support", 5.0)
    distance_to_resistance = stock_data.get("distance_to_resistance", 5.0)
    volatility = stock_data.get("volatility", 20.0)
    symbol = stock_data.get("symbol", "Ticker")
    
    # Expose timeframe trends
    timeframe_trends = calculate_timeframe_trends(timeframe_data)
    
    # ── Rule-Based Local Core (Fallback Base) ──
    rule_signals = []
    bullish_score = 0
    
    if price > ma_50 and price > ma_200:
        bullish_score += 40
        rule_signals.append("Price above 50d & 200d MA (Long-Term Uptrend)")
        trend_strength = "Strong" if ma_50 > ma_200 else "Moderate"
    elif price < ma_50 and price < ma_200:
        bullish_score -= 40
        rule_signals.append("Price below 50d & 200d MA (Long-Term Downtrend)")
        trend_strength = "Strong" if ma_50 < ma_200 else "Moderate"
    else:
        trend_strength = "Weak"
        rule_signals.append("Price consolidates inside moving average channels")
        
    if macd > 0:
        bullish_score += 25
        rule_signals.append("MACD histogram bullish momentum positive")
    else:
        bullish_score -= 25
        rule_signals.append("MACD histogram bearish pressure negative")
        
    if rsi >= 70:
        bullish_score -= 10
        rule_signals.append(f"RSI Overbought ({rsi})")
    elif rsi <= 30:
        bullish_score += 20
        rule_signals.append(f"RSI Oversold ({rsi})")
    else:
        rule_signals.append(f"RSI Neutral momentum ({rsi})")
        
    if distance_to_support < 2.0:
        bullish_score += 15
        rule_signals.append("Price trading near support floor")
    elif distance_to_resistance < 2.0:
        bullish_score -= 15
        rule_signals.append("Price trading near resistance ceiling")
        
    # Rule engine final verdict mapping
    if bullish_score >= 25:
        calculated_trend = "Bullish"
        calculated_confidence = int(50 + min(45, bullish_score * 0.7))
        calculated_reason = f"Bullish technical posture supported by {rule_signals[0]}."
    elif bullish_score <= -25:
        calculated_trend = "Bearish"
        calculated_confidence = int(50 + min(40, abs(bullish_score) * 0.7))
        calculated_reason = f"Bearish alignment indicators indicate {rule_signals[0]}."
    else:
        calculated_trend = "Neutral"
        calculated_confidence = 55
        calculated_reason = "Rangebound consolidation with conflicting indicators."

    # Adjust confidence if trend strength matches
    if trend_strength == "Strong" and calculated_trend != "Neutral":
        calculated_confidence = min(98, calculated_confidence + 10)
        
    rule_risk_factors = ["High market volatility" if volatility >= 35.0 else "Normal asset volatility"]
    
    # ── LLM Query & Fallback orchestrator ──
    enable_subagent_llm = os.getenv("ENABLE_SUBAGENT_LLM", "false").lower() == "true"
    groq_api_key = os.getenv("GROQ_API_KEY")
    if groq_api_key and enable_subagent_llm:
        try:
            logger.info("GROQ_API_KEY detected. Prompting Groq technical analysis agent...")
            
            prompt = f"""
You are an expert technical analyst. Evaluate the following stock technical details for {symbol}:
Current Price: ${price:.2f}
50-day Moving Average: ${ma_50:.2f}
200-day Moving Average: ${ma_200:.2f}
RSI (14): {rsi:.1f}
MACD Value: {macd:.2f} (Signal: {macd_signal:.2f}, Hist: {macd_hist:.2f})
Support Level (20d): ${support_level:.2f}
Resistance Level (20d): ${resistance_level:.2f}
Distance to Support: {distance_to_support:.2f}%
Distance to Resistance: {distance_to_resistance:.2f}%
Annualized Volatility: {volatility:.1f}%
Multi-Timeframe Trend Structures (SMA-20): {timeframe_trends}

Generate an institutional technical analysis report.
Return ONLY a valid JSON object matching this structure:
{{
  "trend": "Bullish" | "Bearish" | "Neutral",
  "confidence": 0-100 (integer representing technical conviction),
  "summary": "technical summary, trend explanation, and market structure analysis (1-2 paragraphs)",
  "signals": ["list of key technical signals triggered (e.g. Price above 50-day MA)"],
  "risk_factors": ["list of technical risk factors (e.g. RSI overbought, high volatility)"],
  "rsi_interpretation": "explain what the RSI score of {rsi:.1f} means for the investor in the current context",
  "macd_interpretation": "explain what the MACD value of {macd:.2f} (Signal: {macd_signal:.2f}) means for momentum",
  "moving_average_analysis": "analyze the price relative to the 50d MA (${ma_50:.2f}) and 200d MA (${ma_200:.2f})",
  "key_technical_conclusion": "a single paragraph summarizing the core actionable technical conclusion for the investor"
}}

Return ONLY the raw JSON. Do not write markdown tags or backticks (no ```json).
"""
            llm_text = query_groq(prompt)
            llm_res = json.loads(llm_text)
            
            # Merge LLM output with mathematical indicator calculations
            return {
                "trend": llm_res.get("trend", calculated_trend),
                "confidence": int(llm_res.get("confidence", calculated_confidence)),
                "reason": llm_res.get("summary", calculated_reason),
                "summary": llm_res.get("summary", calculated_reason),
                "trend_strength": trend_strength,
                "support": support,
                "resistance": resistance,
                "support_level": support_level,
                "resistance_level": resistance_level,
                "distance_to_support": distance_to_support,
                "distance_to_resistance": distance_to_resistance,
                "volatility": volatility,
                "signals": llm_res.get("signals", rule_signals),
                "risk_factors": llm_res.get("risk_factors", rule_risk_factors),
                "timeframe_analysis": timeframe_trends,
                "rsi_interpretation": llm_res.get("rsi_interpretation", f"RSI is at {rsi:.1f}, reflecting neutral price momentum."),
                "macd_interpretation": llm_res.get("macd_interpretation", f"MACD is at {macd:.2f} relative to signal {macd_signal:.2f}."),
                "moving_average_analysis": llm_res.get("moving_average_analysis", f"Price relative to 50d MA (${ma_50:.2f}) and 200d MA (${ma_200:.2f})."),
                "key_technical_conclusion": llm_res.get("key_technical_conclusion", f"The technical setup indicates a {calculated_trend.lower()} momentum posture."),
                "fallback_active": False
            }
            
        except Exception as e:
            logger.warning(f"Groq Technical Agent reasoning failed: {str(e)}. Falling back to local engine.")
            # Fall back to standard rule engine dictionary below
            
    # ── Fallback Return ──
    return {
        "trend": calculated_trend,
        "confidence": calculated_confidence,
        "reason": calculated_reason,
        "summary": calculated_reason,
        "trend_strength": trend_strength,
        "support": support,
        "resistance": resistance,
        "support_level": support_level,
        "resistance_level": resistance_level,
        "distance_to_support": distance_to_support,
        "distance_to_resistance": distance_to_resistance,
        "volatility": volatility,
        "signals": rule_signals,
        "risk_factors": rule_risk_factors,
        "timeframe_analysis": timeframe_trends,
        "rsi_interpretation": f"RSI stands at {rsi:.1f}, indicating neutral relative strength.",
        "macd_interpretation": f"MACD is currently {macd:.2f} with a signal line of {macd_signal:.2f}.",
        "moving_average_analysis": f"Price stands at ${price:.2f} relative to 50d MA (${ma_50:.2f}) and 200d MA (${ma_200:.2f}).",
        "key_technical_conclusion": f"Technical factors align to suggest a consolidative and primarily {calculated_trend.lower()} stance.",
        "fallback_active": True
    }

