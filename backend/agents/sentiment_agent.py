# sentiment_agent.py
# The Sentiment Agent evaluates news headlines for a stock ticker.
# Uses Groq LLM reasoning with a deterministic fallback lexicon loop.

import os
import json
import logging
from services.llm_service import query_groq

logger = logging.getLogger("quantum_agent.sentiment_agent")

# Key vocabulary for rule-based fallback
EVENT_KEYWORDS = {
    "Earnings Report": ["earnings", "revenue", "misses", "beats", "quarterly", "profit", "net income", "eps"],
    "Regulatory/Legal": ["probe", "lawsuit", "regulator", "sec", "regulatory", "investigation", "court", "compliance"],
    "Partnership/M&A": ["partnership", "alliance", "merger", "acquisition", "acquire", "acquires", "collaborates"],
    "Product Launch": ["launch", "unveils", "announces", "introduces", "new product", "product event"],
    "Management Change": ["ceo", "cfo", "resigns", "executive", "leaves", "restructuring", "hires"]
}

def analyze(news_data: dict) -> dict:
    """
    Evaluates news article sentiments.
    Attempts to query Groq to generate sentiment summaries, drivers, and events.
    
    Falls back to lexicon keyword matching if Groq fails or key is missing.
    """
    symbol = news_data.get("symbol", "Stock")
    articles = news_data.get("articles", [])
    
    if not articles:
        return {
            "sentiment": "Neutral",
            "confidence": 50,
            "reason": "No recent news articles found for analysis.",
            "summary": "No recent news articles found for analysis.",
            "positive_drivers": [],
            "negative_drivers": [],
            "positive_ratio": 0.0,
            "negative_ratio": 0.0,
            "events": []
        }

    # ── Rule-Based Lexicon Core (Fallback Base) ──
    pos_count = sum(1 for a in articles if a.get("sentiment") == "positive")
    neg_count = sum(1 for a in articles if a.get("sentiment") == "negative")
    neu_count = sum(1 for a in articles if a.get("sentiment") == "neutral")
    total = len(articles)
    
    pos_ratio = pos_count / total
    neg_ratio = neg_count / total
    
    # Event extraction
    extracted_events = set()
    rule_pos_drivers = []
    rule_neg_drivers = []
    
    for a in articles:
        title = a["title"]
        title_lower = title.lower()
        
        # Tag events
        for event_name, keywords in EVENT_KEYWORDS.items():
            if any(kw in title_lower for kw in keywords):
                extracted_events.add(event_name)
        
        # Extract drivers from titles
        if a.get("sentiment") == "positive":
            rule_pos_drivers.append(title)
        elif a.get("sentiment") == "negative":
            rule_neg_drivers.append(title)
            
    # Set default drivers if empty
    if not rule_pos_drivers:
        rule_pos_drivers = ["General market stabilization"]
    if not rule_neg_drivers:
        rule_neg_drivers = ["General macroeconomic headwinds"]

    # Sentiment Verdict
    if pos_ratio >= 0.55:
        calculated_sentiment = "Positive"
        calculated_confidence = int(50 + (pos_ratio * 40))
        calculated_reason = f"Predominantly positive headlines ({pos_count}/{total} positive). Themes: {', '.join(extracted_events) if extracted_events else 'general growth'}."
    elif neg_ratio > pos_ratio:
        calculated_sentiment = "Negative"
        calculated_confidence = int(50 + (neg_ratio * 40))
        calculated_reason = f"Bearish news dominates ({neg_count}/{total} negative). Concerns: {', '.join(extracted_events) if extracted_events else 'general headwinds'}."
    else:
        calculated_sentiment = "Neutral"
        calculated_confidence = 60
        calculated_reason = f"Balanced sentiment flow ({pos_count} positive, {neg_count} negative, {neu_count} neutral)."
        
    # ── LLM Orchestration & Fallback check ──
    enable_subagent_llm = os.getenv("ENABLE_SUBAGENT_LLM", "false").lower() == "true"
    groq_api_key = os.getenv("GROQ_API_KEY")
    if groq_api_key and enable_subagent_llm:
        try:
            logger.info("GROQ_API_KEY detected. Prompting Groq sentiment agent...")
            
            # Format articles for prompt
            article_list_str = "\n".join([f"- Title: {a.get('title', 'Headline')} (Source: {a.get('source', 'Financial News')}, Date: {a.get('publish_time', 'Recent')})" for a in articles])
            
            prompt = f"""
You are an expert financial analyst. Analyze these recent news articles for {symbol} and generate sentiment analysis details.
Return ONLY a valid JSON object matching this structure:
{{
  "sentiment": "Positive" | "Negative" | "Neutral",
  "confidence": 0-100 (integer representing consensus and data volume confidence),
  "summary": "narrative summary of articles, sentiment drivers, and bullish/bearish factor explanation (1-2 paragraphs)",
  "positive_drivers": ["list of primary positive/bullish drivers (e.g. strong earnings beat, upgrades)"],
  "negative_drivers": ["list of primary negative/bearish concerns (e.g. supply chain, regulatory lawsuits)"],
  "events": ["specific corporate events extracted (e.g. Earnings, Product Launch)"],
  "catalyst_type": "identify primary driver category (e.g., Earnings, Regulatory, Product Launch, Macro, M&A)",
  "most_important_event": "describe the single most important event or news story and its structural impact",
  "market_narrative": "synthesize the current consensus or psychological market narrative surrounding the stock",
  "ai_news_summary": "a premium institutional summary of recent news and sentiment flow (1 paragraph)"
}}

Articles:
{article_list_str}

Return ONLY the raw JSON. Do not write markdown tags or backticks (no ```json).
"""
            llm_text = query_groq(prompt)
            llm_res = json.loads(llm_text)
            
            return {
                "sentiment": llm_res.get("sentiment", calculated_sentiment),
                "confidence": int(llm_res.get("confidence", calculated_confidence)),
                "reason": llm_res.get("summary", calculated_reason),
                "summary": llm_res.get("summary", calculated_reason),
                "positive_drivers": llm_res.get("positive_drivers", rule_pos_drivers),
                "negative_drivers": llm_res.get("negative_drivers", rule_neg_drivers),
                "positive_ratio": round(pos_ratio, 2),
                "negative_ratio": round(neg_ratio, 2),
                "events": llm_res.get("events", list(extracted_events)),
                "fallback_active": False,
                "catalyst_type": llm_res.get("catalyst_type", list(extracted_events)[0] if extracted_events else "Macro Sentiment"),
                "most_important_event": llm_res.get("most_important_event", rule_pos_drivers[0] if rule_pos_drivers else "N/A"),
                "market_narrative": llm_res.get("market_narrative", f"Market psychology is characterized as primarily {calculated_sentiment.lower()} based on recent media flow."),
                "ai_news_summary": llm_res.get("ai_news_summary", llm_res.get("summary", calculated_reason))
            }
            
        except Exception as e:
            logger.warning(f"Groq Sentiment Agent reasoning failed: {str(e)}. Fallback to lexicon engine.")
            # Fall back to lexicon engine below
            
    # ── Fallback Return ──
    return {
        "sentiment": calculated_sentiment,
        "confidence": calculated_confidence,
        "reason": calculated_reason,
        "summary": calculated_reason,
        "positive_drivers": rule_pos_drivers[:3],
        "negative_drivers": rule_neg_drivers[:3],
        "positive_ratio": round(pos_ratio, 2),
        "negative_ratio": round(neg_ratio, 2),
        "events": list(extracted_events),
        "fallback_active": True,
        "catalyst_type": list(extracted_events)[0] if extracted_events else "Macro Sentiment",
        "most_important_event": rule_pos_drivers[0] if calculated_sentiment == "Positive" else (rule_neg_drivers[0] if calculated_sentiment == "Negative" else "General news flow stabilization."),
        "market_narrative": f"Market psychology is characterized as primarily {calculated_sentiment.lower()} based on recent media flow.",
        "ai_news_summary": f"Recent media tracking shows {pos_count} positive, {neg_count} negative, and {neu_count} neutral headlines."
    }
