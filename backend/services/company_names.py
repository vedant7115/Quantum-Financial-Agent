# company_names.py
# Finds a stock's company name with layered fallbacks.
#
# Why this exists: on Render, Yahoo's quoteSummary endpoint (what ticker.info
# reads; it needs a cookie and "crumb") comes back empty for cloud IPs, while the
# chart endpoint (price history), fast_info and the statements endpoints still
# work. Before this module the name fell back to "<TICKER> Corp.", and the news
# filter, which looks for a word from the name, then dropped most headlines.
#
# Layers, first hit wins:
#   a. "yahoo_quote" / "yahoo_chart": ticker.info, then the metadata of the price
#      history call already made (the chart endpoint works from Render).
#   b. "yahoo_search": Yahoo's public search endpoint, exact symbol match.
#   c. "builtin": a small map of common US and Indian tickers.
#   d. "ticker": the plain ticker. Never "<TICKER> Corp.".
#
# Caching (fundamentals tier): a name found by a or b is kept for the tier's TTL
# (24 h by default). When a and b both fail, a short negative entry (5 minutes)
# stops repeated search calls without pinning the failure for a day.

import logging
import time

import requests

logger = logging.getLogger("quantum_agent.company_names")

NEGATIVE_TTL_SECONDS = 300
SEARCH_URL = "https://query2.finance.yahoo.com/v1/finance/search"
SEARCH_TIMEOUT = 4.0
_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

# Keyed by the base ticker; Indian names apply to both .NS and .BO listings.
BUILTIN_US = {
    "AAPL": "Apple Inc.", "MSFT": "Microsoft Corporation", "GOOGL": "Alphabet Inc.", "GOOG": "Alphabet Inc.",
    "AMZN": "Amazon.com, Inc.", "NVDA": "NVIDIA Corporation", "META": "Meta Platforms, Inc.",
    "TSLA": "Tesla, Inc.", "BRK-B": "Berkshire Hathaway Inc.", "JPM": "JPMorgan Chase & Co.",
    "V": "Visa Inc.", "MA": "Mastercard Incorporated", "UNH": "UnitedHealth Group Incorporated",
    "XOM": "Exxon Mobil Corporation", "JNJ": "Johnson & Johnson", "WMT": "Walmart Inc.",
    "PG": "The Procter & Gamble Company", "KO": "The Coca-Cola Company", "PEP": "PepsiCo, Inc.",
    "DIS": "The Walt Disney Company", "NFLX": "Netflix, Inc.", "AMD": "Advanced Micro Devices, Inc.",
    "INTC": "Intel Corporation", "ORCL": "Oracle Corporation", "CRM": "Salesforce, Inc.",
    "ADBE": "Adobe Inc.", "AVGO": "Broadcom Inc.", "COST": "Costco Wholesale Corporation",
    "BAC": "Bank of America Corporation", "HD": "The Home Depot, Inc.",
}
BUILTIN_INDIA = {
    "RELIANCE": "Reliance Industries Limited", "TCS": "Tata Consultancy Services Limited",
    "INFY": "Infosys Limited", "HDFCBANK": "HDFC Bank Limited", "ICICIBANK": "ICICI Bank Limited",
    "SBIN": "State Bank of India", "BHARTIARTL": "Bharti Airtel Limited", "ITC": "ITC Limited",
    "LICI": "Life Insurance Corporation of India", "HINDUNILVR": "Hindustan Unilever Limited",
    "LT": "Larsen & Toubro Limited", "BAJFINANCE": "Bajaj Finance Limited", "WIPRO": "Wipro Limited",
    "KOTAKBANK": "Kotak Mahindra Bank Limited", "AXISBANK": "Axis Bank Limited",
    "MARUTI": "Maruti Suzuki India Limited", "SUNPHARMA": "Sun Pharmaceutical Industries Limited",
    "TATAMOTORS": "Tata Motors Limited", "TATASTEEL": "Tata Steel Limited", "HCLTECH": "HCL Technologies Limited",
    "ASIANPAINT": "Asian Paints Limited", "ADANIENT": "Adani Enterprises Limited",
}


def base_ticker(symbol: str) -> str:
    return symbol.upper().split(".")[0]


def builtin_name(symbol: str):
    symbol = symbol.upper()
    if symbol.endswith((".NS", ".BO")):
        return BUILTIN_INDIA.get(base_ticker(symbol))
    if "." in symbol:
        return None
    return BUILTIN_US.get(symbol)


def _clean(value):
    return value.strip() if isinstance(value, str) and value.strip() else None


def from_quote(info: dict, history_metadata: dict):
    """Layer a: the data get_stock_data already fetched. Returns (name, source)."""
    name = _clean((info or {}).get("longName")) or _clean((info or {}).get("shortName"))
    if name:
        return name, "yahoo_quote"
    name = _clean((history_metadata or {}).get("longName")) or _clean((history_metadata or {}).get("shortName"))
    if name:
        return name, "yahoo_chart"
    return None, None


def search_name(symbol: str, session=None):
    """Layer b: Yahoo's search endpoint; only an exact symbol match counts."""
    getter = session or requests
    response = getter.get(SEARCH_URL, params={"q": symbol, "quotesCount": 5, "newsCount": 0},
                          headers=_HEADERS, timeout=SEARCH_TIMEOUT)
    response.raise_for_status()
    for quote in response.json().get("quotes", []) or []:
        if (quote.get("symbol") or "").upper() == symbol.upper():
            return _clean(quote.get("longname")) or _clean(quote.get("shortname"))
    return None


def resolve(symbol: str, info: dict = None, history_metadata: dict = None, cache=None) -> tuple:
    """Returns (display_name, source). display_name is never "<TICKER> Corp."."""
    symbol = symbol.upper()
    key = f"name:{symbol}"

    name, source = from_quote(info, history_metadata)
    if name:
        if cache is not None:
            cache.set("fundamentals", key, {"name": name, "source": source})
        return name, source

    cached = cache.get("fundamentals", key, count=False) if cache is not None else None
    if cached:
        if cached.get("name"):
            return cached["name"], cached["source"]
        if cached.get("retry_after", 0) > time.time():
            return _offline(symbol)

    try:
        name = search_name(symbol)
    except Exception as err:
        logger.warning(f"Yahoo search lookup failed for {symbol}: {err}")
        name = None
    if name:
        if cache is not None:
            cache.set("fundamentals", key, {"name": name, "source": "yahoo_search"})
        return name, "yahoo_search"

    if cache is not None:
        cache.set("fundamentals", key, {"name": None, "retry_after": time.time() + NEGATIVE_TTL_SECONDS})
    return _offline(symbol)


def _offline(symbol: str) -> tuple:
    """Layers c and d: no network."""
    name = builtin_name(symbol)
    return (name, "builtin") if name else (base_ticker(symbol) if symbol.endswith((".NS", ".BO")) else symbol, "ticker")
