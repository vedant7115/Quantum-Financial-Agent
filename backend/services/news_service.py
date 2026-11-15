# news_service.py
# This service fetches real stock-related news articles using yfinance or public RSS fallback.
# Each article is scanned and tagged with a heuristic sentiment score.

import yfinance as yf
import xml.etree.ElementTree as ET
import httpx
import os
import random
import logging

logger = logging.getLogger("quantum_agent.news_service")

# Heuristic Sentiment Vocabularies
POSITIVE_WORDS = {
    "beat", "beats", "surges", "surge", "upgrades", "upgrade", "growth", "highs", "record", 
    "partnership", "alliance", "dividend", "outperform", "gain", "gains", "rise", "rises", 
    "success", "positive", "strong", "bullish", "profit", "profitable", "wins", "acquisition",
    "expansion", "expanding", "buy", "exceeds"
}

# Negatives
NEGATIVE_WORDS = {
    "miss", "misses", "falls", "fall", "plummets", "plummet", "drop", "drops", "cuts", "cut", 
    "probe", "investigation", "lawsuit", "suit", "regulator", "regulatory", "declines", 
    "decline", "weakness", "weak", "down", "negative", "loss", "losses", "layoffs", "layoff", 
    "sell", "bearish", "restructuring", "disruption", "disruptions", "inflation", "warns"
}

# Fallback Mock News Headlines
MOCK_POSITIVE = [
    "{sym} beats earnings expectations by wide margin",
    "{sym} announces major partnership deal with industry leaders",
    "{sym} stock surges after record quarterly revenue",
    "Analysts upgrade {sym} to 'Strong Buy' rating",
    "{sym} expands into new international markets",
    "{sym} CEO announces aggressive growth strategy",
    "Institutional investors increase stake in {sym}"
]

MOCK_NEGATIVE = [
    "{sym} misses revenue targets for the recent quarter",
    "Regulatory probe launched against {sym} operations",
    "{sym} faces temporary supply chain disruptions",
    "Key executives leave {sym} amid internal restructuring",
    "{sym} lowers full-year growth guidance"
]

MOCK_NEUTRAL = [
    "{sym} holds annual investor day meeting",
    "{sym} announces upcoming product launch event",
    "Analysts maintain neutral weight rating on {sym}",
    "{sym} files standard SEC quarterly report"
]

def tag_sentiment(title: str) -> str:
    """Classifies a title's sentiment using keyword matching."""
    words = title.lower().replace("-", " ").replace(":", " ").split()
    pos_count = sum(1 for w in words if w in POSITIVE_WORDS)
    neg_count = sum(1 for w in words if w in NEGATIVE_WORDS)
    
    if pos_count > neg_count:
        return "positive"
    elif neg_count > pos_count:
        return "negative"
    return "neutral"

def fetch_rss_news(symbol: str) -> list:
    """
    Fallback news harvester. Queries the public Google News RSS feed, 
    parses items, and extracts headlines, publisher sources, and publication dates.
    """
    url = f"https://news.google.com/rss/search?q={symbol}+stock&hl=en-US&gl=US&ceid=US:en"
    try:
        logger.info(f"YFinance news empty. Querying Google News RSS feed: {url}")

        response = httpx.get(url, timeout=8.0)
        response.raise_for_status()
        
        # Parse XML from response bytes
        root = ET.fromstring(response.content)
        articles = []
        
        # Extract items
        for item in root.findall(".//item"):
            title = item.find("title")
            link = item.find("link")
            pub_date = item.find("pubDate")
            source_tag = item.find("source")
            
            title_text = title.text if title is not None else ""
            link_text = link.text if link is not None else "#"
            pub_text = pub_date.text if pub_date is not None else "Recent Date"
            
            # Extract source name
            source_name = "Google News"
            if source_tag is not None and source_tag.text:
                source_name = source_tag.text
            elif "bloomberg" in link_text.lower():
                source_name = "Bloomberg"
            elif "reuters" in link_text.lower():
                source_name = "Reuters"
            elif "marketwatch" in link_text.lower():
                source_name = "MarketWatch"
                
            # Clean title suffix (Google News titles end with " - Publisher")
            if title_text and source_name:
                suffix = f" - {source_name}"
                if title_text.endswith(suffix):
                    title_text = title_text[:-len(suffix)].strip()
                
            if title_text:
                articles.append({
                    "title": title_text,
                    "sentiment": tag_sentiment(title_text),
                    "source": source_name,
                    "link": link_text,
                    "publish_time": pub_text
                })
        logger.info(f"Successfully loaded {len(articles)} articles from public XML stream.")
        return articles
        
    except Exception as e:
        logger.error(f"Failed to query public RSS news feed: {str(e)}")
        return []

def get_news(symbol: str) -> dict:
    """
    Fetches news from yfinance Ticker endpoint.
    If empty, automatically falls back to RSS parser, and finally mock headlines.
    """
    symbol = symbol.upper().strip()
    
    # Auto-resolve NSE suffix
    resolved_symbol = symbol
    if "." not in symbol and symbol in {"RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN"}:
        resolved_symbol = f"{symbol}.NS"
        
    articles = []
    source_label = "Yahoo Finance (Real-Time)"
    
    try:
        ticker = yf.Ticker(resolved_symbol)
        raw_news = ticker.news
        
        if raw_news:
            for article in raw_news:
                title = article.get("title", "")
                if not title:
                    continue
                
                # Format publish time from unix int to readable string
                import datetime
                unix_time = article.get("providerPublishTime", 0)
                if unix_time:
                    dt = datetime.datetime.fromtimestamp(unix_time, datetime.timezone.utc)
                    pub_str = dt.strftime("%a, %d %b %Y %H:%M:%S GMT")
                else:
                    pub_str = "Recent Date"

                articles.append({
                    "title": title,
                    "sentiment": tag_sentiment(title),
                    "source": article.get("publisher", "Financial News"),
                    "link": article.get("link", "#"),
                    "publish_time": pub_str
                })
            logger.info(f"Loaded {len(articles)} articles from yfinance Ticker.")
            
    except Exception as e:
        logger.warning(f"yfinance news scraper encountered error: {str(e)}. Switching to RSS.")
        
    # Trigger XML feed query if yfinance returns empty
    if not articles:
        articles = fetch_rss_news(resolved_symbol)
        source_label = "Google News RSS (XML Fallback)"
        
    # No real news found. Report that honestly: an empty list, never invented
    # headlines. Mock headlines exist only for offline development.
    if not articles:
        if os.getenv("ALLOW_MOCK_DATA", "false").lower() == "true":
            mock_data = get_mock_news(symbol)
            articles = mock_data["articles"]
            source_label = mock_data["source"]
        else:
            source_label = "No recent news available"
        
    return {
        "symbol": resolved_symbol,
        "total_articles": len(articles[:8]),
        "articles": articles[:8],
        "source": source_label
    }

def get_mock_news(symbol: str) -> dict:
    """Generates mock headlines fallback."""
    articles = []
    
    # Pick a random selection
    chosen_pos = random.sample(MOCK_POSITIVE, 2)
    chosen_neg = random.sample(MOCK_NEGATIVE, 1)
    chosen_neu = random.sample(MOCK_NEUTRAL, 1)
    
    import datetime
    now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    
    for headline in chosen_pos:
        articles.append({
            "title": headline.format(sym=symbol),
            "sentiment": "positive",
            "source": "Mock News Engine",
            "link": "#",
            "publish_time": now_str
        })
        
    for headline in chosen_neg:
        articles.append({
            "title": headline.format(sym=symbol),
            "sentiment": "negative",
            "source": "Mock News Engine",
            "link": "#",
            "publish_time": now_str
        })
        
    for headline in chosen_neu:
        articles.append({
            "title": headline.format(sym=symbol),
            "sentiment": "neutral",
            "source": "Mock News Engine",
            "link": "#",
            "publish_time": now_str
        })
        
    random.shuffle(articles)
    
    return {
        "symbol": symbol,
        "total_articles": len(articles),
        "articles": articles,
        "source": "Mock News Engine (Fallback)"
    }
