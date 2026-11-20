# news_service.py
# Fetches real, recent headlines for a stock (Yahoo Finance, then Google News RSS)
# and tags each one positive / negative / neutral from its wording.
# If nothing is found the list is empty. Headlines are never invented.

import asyncio
import datetime
import logging
import os
import random
import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

import httpx
import yfinance as yf

logger = logging.getLogger("quantum_agent.news_service")

MAX_ARTICLES = 10
MAX_AGE_DAYS = 30

POSITIVE_WORDS = {
    "beat", "beats", "surge", "surges", "surged", "soar", "soars", "soared", "jump", "jumps", "jumped",
    "rally", "rallies", "rallied", "upgrade", "upgrades", "upgraded", "outperform", "gain", "gains",
    "rise", "rises", "rose", "climb", "climbs", "climbed", "strong", "bullish", "wins", "win", "raises",
    "raised", "boost", "boosts", "boosted", "tops", "topped", "growth", "expands", "expansion", "buyback",
    "approval", "approved", "exceeds", "rebound", "rebounds", "breakout", "profitable", "milestone",
}
NEGATIVE_WORDS = {
    "miss", "misses", "missed", "fall", "falls", "fell", "plunge", "plunges", "plunged", "plummet",
    "plummets", "drop", "drops", "dropped", "slump", "slumps", "slide", "slides", "slid", "tumble",
    "tumbles", "tumbled", "sink", "sinks", "cut", "cuts", "downgrade", "downgrades", "downgraded",
    "probe", "investigation", "lawsuit", "sued", "sues", "fraud", "recall", "recalls", "decline",
    "declines", "declined", "weak", "weakness", "loss", "losses", "layoff", "layoffs", "bearish", "warns",
    "warning", "slashes", "slashed", "lowers", "lowered", "halts", "halted", "delay", "delays", "delayed",
    "fined", "penalty", "default", "bankruptcy", "selloff", "crash", "crashes", "underperform", "resigns",
    "disruption", "shortfall", "concerns", "fears",
}
# Phrases decide the tone on their own: single words inside them mislead
# ("price target cut" contains no negative verb about the company itself).
POSITIVE_PHRASES = ("record high", "all-time high", "price target raised", "raises price target", "raises target",
                    "beats estimates", "beats expectations", "raises guidance", "raises forecast", "strong buy")
NEGATIVE_PHRASES = ("record low", "price target cut", "cuts price target", "cuts target", "lowers price target",
                    "misses estimates", "misses expectations", "cuts guidance", "lowers guidance", "cuts forecast",
                    "sell-off", "profit warning", "falls short", "under pressure")


def tag_sentiment(title: str) -> str:
    """Classifies a headline's tone from its wording."""
    text = title.lower()
    score = sum(2 for p in POSITIVE_PHRASES if p in text) - sum(2 for p in NEGATIVE_PHRASES if p in text)
    words = re.findall(r"[a-z]+", text)
    score += sum(1 for w in words if w in POSITIVE_WORDS) - sum(1 for w in words if w in NEGATIVE_WORDS)
    return "positive" if score > 0 else ("negative" if score < 0 else "neutral")


# Automated filing notices ("X LLC buys 4,554 shares of ...") say nothing about the
# business and would otherwise drown out real coverage.
NOISE = re.compile(
    r"shares? (of .+ )?(bought|sold|acquired|purchased) by"
    r"|(buys|sells|acquires|purchases|trims|boosts|cuts) [0-9,]+ shares"
    r"|stock (bought|sold|acquired|position) by"
    r"|(boosts|raises|increases|decreases|trims|lowers|reduces|cuts|grows) (its )?(stock )?(position|stake|holdings)"
    r"|(stake|position|holdings) in "
    r"|form (4|144|13f) "
    r"|(share|stock) price|option chain|quote (and|&) history|outlook for the week|live nse| overview$"
    r"|stocks? to watch|top stock picks", re.I)

GENERIC_NAME_WORDS = {"the", "inc", "ltd", "limited", "corp", "corporation", "company", "co", "plc", "group", "holdings",
                      "industries", "bank", "of", "and", "india", "international", "enterprises"}


def _relevant_terms(symbol: str, company_name: str) -> list:
    """Words a headline must contain to be about this company."""
    terms = [symbol.split(".")[0].lower()]
    for word in re.findall(r"[A-Za-z]{3,}", company_name or ""):
        if word.lower() not in GENERIC_NAME_WORDS:
            terms.append(word.lower())
            break
    return terms


def _article(title, source, link, published: datetime.datetime | None) -> dict:
    return {
        "title": title.strip(),
        "sentiment": tag_sentiment(title),
        "source": source or "News",
        "link": link or "#",
        "publish_time": published.strftime("%a, %d %b %Y %H:%M:%S GMT") if published else "",
        "published": published.isoformat() if published else None,
    }


def _from_yahoo(symbol: str) -> list:
    articles = []
    for item in yf.Ticker(symbol).news or []:
        content = item.get("content") if isinstance(item.get("content"), dict) else None
        published = None
        if content:  # yfinance 1.x shape
            title = content.get("title", "")
            source = (content.get("provider") or {}).get("displayName")
            link = ((content.get("clickThroughUrl") or {}).get("url")
                    or (content.get("canonicalUrl") or {}).get("url"))
            try:
                published = datetime.datetime.fromisoformat((content.get("pubDate") or "").replace("Z", "+00:00"))
            except ValueError:
                published = None
        else:  # older shape
            title, source, link = item.get("title", ""), item.get("publisher"), item.get("link")
            if item.get("providerPublishTime"):
                published = datetime.datetime.fromtimestamp(item["providerPublishTime"], datetime.timezone.utc)
        if title:
            articles.append(_article(title, source, link, published))
    return articles


def _rss_url(symbol: str, company_name: str) -> str:
    india = symbol.endswith((".NS", ".BO"))
    term = company_name or symbol.split(".")[0]
    locale = "hl=en-IN&gl=IN&ceid=IN:en" if india else "hl=en-US&gl=US&ceid=US:en"
    return f"https://news.google.com/rss/search?q={quote_plus(term + ' stock')}+when:14d&{locale}"


def _parse_rss(content: bytes) -> list:
    root = ET.fromstring(content)
    articles = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        source = (item.findtext("source") or "").strip() or "Google News"
        if title.endswith(f" - {source}"):
            title = title[: -len(source) - 3].strip()
        try:
            published = parsedate_to_datetime(item.findtext("pubDate") or "")
        except (TypeError, ValueError):
            published = None
        if title:
            articles.append(_article(title, source, item.findtext("link"), published))
    return articles


async def fetch_rss_news_async(symbol: str, company_name: str = "") -> list:
    """Google News RSS search for the company, without blocking the event loop."""
    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            response = await client.get(_rss_url(symbol, company_name))
            response.raise_for_status()
        return _parse_rss(response.content)
    except Exception as err:
        logger.warning(f"Google News RSS failed for {symbol}: {err}")
        return []


async def _yahoo_async(symbol: str) -> list:
    try:
        return await asyncio.to_thread(_from_yahoo, symbol)
    except Exception as err:
        logger.warning(f"Yahoo news unavailable for {symbol}: {err}")
        return []


def select_articles(symbol: str, company_name: str, yahoo: list, rss: list) -> dict:
    """Merges, filters and orders headlines: Google News is used only when Yahoo has
    fewer than four; noise and unrelated headlines are dropped; newest first."""
    articles, source_label = list(yahoo), "Yahoo Finance"
    if len(articles) < 4 and rss:
        articles, source_label = articles + rss, ("Yahoo Finance and Google News" if articles else "Google News")

    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=MAX_AGE_DAYS)
    terms = _relevant_terms(symbol, company_name)
    seen, fresh = set(), []
    for a in articles:
        lowered = a["title"].lower()
        key = re.sub(r"[^a-z0-9]", "", lowered)[:60]
        if key in seen or NOISE.search(lowered) or not any(t in lowered for t in terms):
            continue
        seen.add(key)
        when = datetime.datetime.fromisoformat(a["published"]) if a["published"] else None
        if when and when.tzinfo is None:
            when = when.replace(tzinfo=datetime.timezone.utc)
        if when is None or when >= cutoff:
            fresh.append((when or cutoff, a))
    fresh.sort(key=lambda pair: pair[0], reverse=True)
    articles = [a for _, a in fresh[:MAX_ARTICLES]]

    if not articles:
        if os.getenv("ALLOW_MOCK_DATA", "false").lower() == "true":
            return get_mock_news(symbol)
        source_label = "No recent news available"
    return {"symbol": symbol, "total_articles": len(articles), "articles": articles, "source": source_label}


async def fetch_news(symbol: str, company_name: str = "") -> dict:
    """Recent headlines for a symbol. Yahoo (in a thread) and Google News RSS (async
    HTTP) are fetched at the same time."""
    symbol = symbol.upper().strip()
    yahoo, rss = await asyncio.gather(_yahoo_async(symbol), fetch_rss_news_async(symbol, company_name))
    return select_articles(symbol, company_name, yahoo, rss)


def get_news(symbol: str, company_name: str = "") -> dict:
    """Synchronous wrapper for scripts. Do not call from inside a running event loop."""
    return asyncio.run(fetch_news(symbol, company_name))


def get_mock_news(symbol: str) -> dict:
    """Offline development only (ALLOW_MOCK_DATA=true). Clearly labelled as mock."""
    samples = [
        ("{sym} beats earnings expectations", "positive"), ("{sym} expands into new markets", "positive"),
        ("{sym} lowers full-year guidance", "negative"), ("{sym} holds annual investor day", "neutral"),
    ]
    now = datetime.datetime.now(datetime.timezone.utc)
    articles = [dict(_article(text.format(sym=symbol), "Mock News Engine", "#", now), sentiment=tone)
                for text, tone in random.sample(samples, len(samples))]
    return {"symbol": symbol, "total_articles": len(articles), "articles": articles, "source": "Mock News Engine (Fallback)"}
