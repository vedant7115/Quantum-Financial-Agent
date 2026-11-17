# sentiment_agent.py
# Summarises the tone of real, recent headlines. With no headlines it says so;
# it never fills the gap with generic drivers.

EVENT_KEYWORDS = {
    "Earnings": ["earnings", "revenue", "quarterly", "profit", "eps", "results", "guidance"],
    "Analyst rating": ["upgrade", "downgrade", "price target", "rating", "initiates", "outperform", "underperform"],
    "Regulatory or legal": ["probe", "lawsuit", "regulator", "sec ", "sebi", "investigation", "court", "antitrust", "fine"],
    "Deal": ["partnership", "merger", "acquisition", "acquire", "stake", "deal", "joint venture"],
    "Product": ["launch", "unveils", "introduces", "new product", "release"],
    "Management": ["ceo", "cfo", "resigns", "appoints", "steps down", "chairman"],
    "Capital return": ["dividend", "buyback", "bonus issue", "split"],
}


def analyze(news_data: dict) -> dict:
    articles = news_data.get("articles", [])
    if not articles:
        text = "No recent headlines were found, so news tone is not part of this view."
        return {
            "sentiment": "Neutral", "confidence": 0, "reason": text, "summary": text,
            "positive_drivers": [], "negative_drivers": [], "positive_ratio": 0.0, "negative_ratio": 0.0,
            "events": [], "fallback_active": False, "catalyst_type": "", "most_important_event": "",
            "market_narrative": text, "ai_news_summary": text,
        }

    total = len(articles)
    positive = [a["title"] for a in articles if a.get("sentiment") == "positive"]
    negative = [a["title"] for a in articles if a.get("sentiment") == "negative"]
    pos_ratio, neg_ratio = len(positive) / total, len(negative) / total
    net = pos_ratio - neg_ratio

    events = [name for name, words in EVENT_KEYWORDS.items()
              if any(w in a["title"].lower() for a in articles for w in words)]

    if net >= 0.25:
        sentiment = "Positive"
    elif net <= -0.25:
        sentiment = "Negative"
    else:
        sentiment = "Neutral"
    # More headlines and a clearer lean both make the reading more dependable.
    confidence = int(min(90, 35 + min(total, 10) * 3 + abs(net) * 35))
    neutral = total - len(positive) - len(negative)
    summary = (f"Of {total} recent headlines, {len(positive)} read positive, {len(negative)} negative "
               f"and {neutral} neutral." + (f" Recurring themes: {', '.join(events[:3]).lower()}." if events else ""))

    lead = (positive or negative or [articles[0]["title"]])[0] if sentiment != "Negative" else (negative or positive)[0]
    return {
        "sentiment": sentiment, "confidence": confidence, "reason": summary, "summary": summary,
        "positive_drivers": positive[:3], "negative_drivers": negative[:3],
        "positive_ratio": round(pos_ratio, 2), "negative_ratio": round(neg_ratio, 2),
        "events": events, "fallback_active": False,
        "catalyst_type": events[0] if events else "",
        "most_important_event": lead,
        "market_narrative": summary, "ai_news_summary": summary,
    }
