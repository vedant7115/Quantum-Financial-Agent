"""Company-name fallbacks and ticker-based news search (the Render "AAPL Corp." fix).
Yahoo is mocked throughout; nothing here touches the network."""

import datetime

import pandas as pd
import pytest

from services import company_names, news_service, stock_service
from services.cache_service import TieredCache


@pytest.fixture
def cache():
    return TieredCache({"report": 300, "price": 300, "news": 1800, "fundamentals": 86400})


@pytest.fixture
def search(monkeypatch):
    """Records Yahoo search calls; set .result to a name, None, or an exception."""
    class Search:
        result, calls = None, 0

        def __call__(self, symbol, session=None):
            Search.calls += 1
            if isinstance(Search.result, Exception):
                raise Search.result
            return Search.result
    monkeypatch.setattr(company_names, "search_name", Search())
    return Search


def test_layer_a_quote_then_chart_metadata(cache, search):
    assert company_names.resolve("AAPL", {"longName": "Apple Inc."}, {}, cache) == ("Apple Inc.", "yahoo_quote")
    # Render case: info is empty but the price-history (chart) call carries the name.
    assert company_names.resolve("MSFT", {}, {"longName": "Microsoft Corporation"}, cache) == \
        ("Microsoft Corporation", "yahoo_chart")
    assert search.calls == 0


def test_layer_b_search_is_used_and_cached_for_a_day(cache, search):
    search.result = "Apple Inc."
    assert company_names.resolve("AAPL", {}, {}, cache) == ("Apple Inc.", "yahoo_search")
    assert company_names.resolve("AAPL", {}, {}, cache) == ("Apple Inc.", "yahoo_search")
    assert search.calls == 1
    assert cache.ttl_remaining("fundamentals", "name:AAPL") > 86000


def test_search_needs_an_exact_symbol_match(monkeypatch):
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"quotes": [{"symbol": "AAPU", "longname": "Direxion Daily AAPL Bull 2X"},
                               {"symbol": "AAPL", "longname": "Apple Inc."}]}
    class Session:
        def get(self, url, **kwargs):
            return Response()
    assert company_names.search_name("AAPL", Session()) == "Apple Inc."
    assert company_names.search_name("ZZZZ", Session()) is None


def test_layer_c_builtin_map_when_yahoo_fails(cache, search):
    search.result = RuntimeError("429 Too Many Requests")
    assert company_names.resolve("KO", {}, {}, cache) == ("The Coca-Cola Company", "builtin")
    assert company_names.resolve("TCS.NS", {}, {}, cache) == ("Tata Consultancy Services Limited", "builtin")
    assert company_names.resolve("RELIANCE.BO", {}, {}, cache) == ("Reliance Industries Limited", "builtin")


def test_layer_d_plain_ticker_never_corp(cache, search):
    assert company_names.resolve("ZZQX", {}, {}, cache) == ("ZZQX", "ticker")
    assert company_names.resolve("NEWCO.NS", {}, {}, cache) == ("NEWCO", "ticker")


def test_failed_lookup_is_negative_cached_for_five_minutes_only(cache, search, monkeypatch):
    now = [1_000_000.0]
    monkeypatch.setattr(company_names.time, "time", lambda: now[0])
    company_names.resolve("ZZQX", {}, {}, cache)
    company_names.resolve("ZZQX", {}, {}, cache)
    assert search.calls == 1                      # second call skipped by the negative entry
    now[0] += company_names.NEGATIVE_TTL_SECONDS + 1
    search.result = "Zzqx Holdings"
    assert company_names.resolve("ZZQX", {}, {}, cache) == ("Zzqx Holdings", "yahoo_search")
    assert search.calls == 2


def test_get_stock_data_all_layers_failed_shows_plain_ticker(monkeypatch, search):
    """Whole quote path with yfinance mocked the way Render behaves: prices work,
    info is empty, chart metadata has no name, search fails."""
    search.result = RuntimeError("blocked")
    idx = pd.bdate_range(end="2026-11-13", periods=260)
    hist = pd.DataFrame({"Close": [100 + i * 0.1 for i in range(260)], "Volume": [1000] * 260}, index=idx)

    class FastInfo:
        last_price, previous_close, market_cap, currency = 126.0, 125.9, 1e9, "USD"

    class FakeTicker:
        def __init__(self, symbol, session=None):
            self.fast_info, self.info, self.history_metadata = FastInfo(), {}, {}

        def history(self, **kwargs):
            return hist

    monkeypatch.setattr(stock_service.yf, "Ticker", FakeTicker)
    monkeypatch.setattr(stock_service, "cache", TieredCache({"report": 1, "price": 1, "news": 1, "fundamentals": 86400}))
    data = stock_service.get_stock_data("ZZQX")
    assert data["name"] == "ZZQX" and data["name_source"] == "ticker"
    assert "Corp." not in data["name"]


def test_news_query_uses_ticker_and_exchange_when_name_missing():
    assert news_service._rss_query("AAPL", "") == "AAPL stock"
    assert news_service._rss_query("RELIANCE.NS", "") == "RELIANCE NSE stock"
    assert news_service._rss_query("RELIANCE.BO", "") == "RELIANCE BSE stock"
    assert news_service._rss_query("AAPL", "Apple Inc.") == "Apple Inc. stock"


def _headline(title):
    now = datetime.datetime.now(datetime.timezone.utc)
    return news_service._article(title, "Test", "#", now)


def test_relevance_filter_keeps_ticker_headlines_without_a_name():
    rss = [_headline("AAPL shares climb after earnings"), _headline("Unrelated market wrap")]
    result = news_service.select_articles("AAPL", "", [], rss)
    assert [a["title"] for a in result["articles"]] == ["AAPL shares climb after earnings"]


def test_google_news_added_when_yahoo_headlines_are_filtered_out():
    """The live failure: Yahoo returned headlines, but none passed the filter, so
    Google News was never consulted. Now the decision is made after filtering."""
    yahoo = [_headline(f"Market wrap {i}") for i in range(6)]
    rss = [_headline("Apple unveils new chip"), _headline("Apple results beat estimates")]
    result = news_service.select_articles("AAPL", "Apple Inc.", yahoo, rss)
    assert result["total_articles"] == 2 and result["source"] == "Google News"


def test_no_news_is_reported_honestly(monkeypatch):
    monkeypatch.delenv("ALLOW_MOCK_DATA", raising=False)
    result = news_service.select_articles("ZZQX", "", [], [])
    assert result["total_articles"] == 0 and result["articles"] == []
    assert result["source"] == "No recent news available"
