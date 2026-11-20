# research_engine.py
# The evidence layer. Everything here is computed from real price history and the
# company's reported financial statements; nothing is estimated by a language model.
#
# It produces eight scored "pillars" (trend, momentum, stability, quality, growth,
# valuation, balance sheet, news), each backed by findings that quote the number
# behind them, plus historical base rates for the stock's current trend regime.
# The agents turn these into the report, and the LLM is only allowed to explain them.

import logging
import math
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime

import numpy as np
import pandas as pd
import yfinance as yf

logger = logging.getLogger("quantum_agent.research_engine")

HORIZON_DAYS = 63  # about three months of trading days
CURRENCY_SYMBOLS = {"USD": "$", "INR": "₹", "EUR": "€", "GBP": "£", "JPY": "¥"}

REGIMES = {
    "uptrend": "Uptrend: price above its 200-day average, with the 50-day above the 200-day",
    "pullback": "Pullback: price has slipped below its 200-day average while the 50-day is still above it",
    "recovering": "Recovery attempt: price is back above its 200-day average, but the 50-day is still below it",
    "downtrend": "Downtrend: price below its 200-day average, with the 50-day below the 200-day",
}


# ── small helpers ────────────────────────────────────────────────────────────

def _f(value):
    """float, or None for missing / NaN / infinite values."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return None if (math.isnan(number) or math.isinf(number)) else number


def _r(value, digits=1):
    return None if value is None else round(value, digits)


def _ratio(a, b):
    if a is None or b is None or b == 0:
        return None
    return a / b


def _growth(new, old):
    """Percent change, only when the base is positive (growth off a loss is meaningless)."""
    if new is None or old is None or old <= 0:
        return None
    return (new / old - 1) * 100


def currency_symbol(code: str) -> str:
    return CURRENCY_SYMBOLS.get((code or "").upper(), f"{code} " if code else "")


def format_money(value, currency: str) -> str:
    if value is None:
        return "n/a"
    sym = currency_symbol(currency)
    sign = "-" if value < 0 else ""
    v = abs(value)
    if (currency or "").upper() == "INR":
        crore = v / 1e7
        if crore >= 1e5:
            return f"{sign}{sym}{crore / 1e5:.2f} lakh Cr"
        return f"{sign}{sym}{crore:,.0f} Cr"
    if v >= 1e12:
        return f"{sign}{sym}{v / 1e12:.2f}T"
    if v >= 1e9:
        return f"{sign}{sym}{v / 1e9:.2f}B"
    return f"{sign}{sym}{v / 1e6:.1f}M"


def benchmark_for(symbol: str):
    if symbol.endswith(".NS"):
        return "^NSEI", "Nifty 50"
    if symbol.endswith(".BO"):
        return "^BSESN", "Sensex"
    return "^GSPC", "S&P 500"


class Pillar:
    """A scored group of checks. Each check adds or removes points and records a
    finding that states the number behind it. Score is 0-100, 50 = neutral."""

    def __init__(self, key: str, label: str):
        self.key = key
        self.label = label
        self.points = 0.0
        self.max_points = 0.0
        self.findings = []
        self.note = ""

    def add(self, points: float, max_points: float, title: str, detail: str):
        self.points += points
        self.max_points += max_points
        tone = "positive" if points > 0 else ("negative" if points < 0 else "neutral")
        self.findings.append({"pillar": self.key, "tone": tone, "title": title, "detail": detail,
                              "weight": abs(points)})

    @property
    def score(self):
        if self.max_points == 0:
            return None
        return int(round(max(0, min(100, 50 + 50 * self.points / self.max_points))))

    def verdict(self, words=("Strong", "Good", "Mixed", "Soft", "Weak")) -> str:
        s = self.score
        if s is None:
            return "Not assessed"
        if s >= 75:
            return words[0]
        if s >= 60:
            return words[1]
        if s >= 40:
            return words[2]
        if s >= 25:
            return words[3]
        return words[4]

    def as_dict(self, words=("Strong", "Good", "Mixed", "Soft", "Weak")) -> dict:
        return {"key": self.key, "label": self.label, "score": self.score,
                "verdict": self.verdict(words), "note": self.note}


def _band(value, bands, default):
    """bands: [(threshold, points), ...] checked in order with value >= threshold."""
    for threshold, points in bands:
        if value >= threshold:
            return points
    return default


# ── data fetching ────────────────────────────────────────────────────────────

def _history(symbol: str, period: str) -> pd.Series:
    try:
        hist = yf.Ticker(symbol).history(period=period, interval="1d")
        return hist["Close"].dropna() if not hist.empty else pd.Series(dtype=float)
    except Exception as err:
        logger.warning(f"History fetch failed for {symbol} ({period}): {err}")
        return pd.Series(dtype=float)


def _clean_statement(df, anchor_rows):
    """Newest period first, dropping periods the provider left empty."""
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return None
    df = df[sorted(df.columns, reverse=True)]
    anchor = next((r for r in anchor_rows if r in df.index), None)
    if anchor:
        df = df.loc[:, df.loc[anchor].notna()]
    else:
        df = df.dropna(axis=1, how="all")
    return None if df.empty else df


def _statements(symbol: str) -> dict:
    ticker = yf.Ticker(symbol)
    out = {}
    for name, attr, anchors in (
        ("income", "income_stmt", ["Total Revenue", "Net Income"]),
        ("balance", "balance_sheet", ["Total Assets", "Stockholders Equity"]),
        ("cashflow", "cashflow", ["Operating Cash Flow", "Free Cash Flow"]),
        ("quarterly", "quarterly_income_stmt", ["Total Revenue", "Net Income"]),
    ):
        try:
            out[name] = _clean_statement(getattr(ticker, attr), anchors)
        except Exception as err:
            logger.warning(f"{attr} unavailable for {symbol}: {err}")
            out[name] = None
    return out


def _calendar(symbol: str) -> dict:
    """Next earnings and ex-dividend dates as published by the exchange feed."""
    try:
        cal = yf.Ticker(symbol).calendar or {}
    except Exception as err:
        logger.info(f"Calendar unavailable for {symbol}: {err}")
        return {}
    events = {}
    earnings = cal.get("Earnings Date")
    if isinstance(earnings, (list, tuple)) and earnings:
        earnings = earnings[0]
    for key, value in (("earnings", earnings), ("ex_dividend", cal.get("Ex-Dividend Date"))):
        if isinstance(value, datetime):
            value = value.date()
        if isinstance(value, date) and value >= date.today():
            events[key] = value.isoformat()
    return events


def _val(df, names, col=0):
    if df is None or col >= df.shape[1]:
        return None
    for name in names:
        if name in df.index:
            value = _f(df.iloc[:, col].get(name))
            if value is not None:
                return value
    return None


# ── price analysis ───────────────────────────────────────────────────────────

def _rsi(close: pd.Series, period: int = 14) -> float:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    return float((100 - 100 / (1 + gain / (loss + 1e-9))).iloc[-1])


def _regime_series(close: pd.Series) -> pd.Series:
    ma50 = close.rolling(50).mean()
    ma200 = close.rolling(200).mean()
    above = close > ma200
    stacked = ma50 > ma200
    regime = pd.Series(index=close.index, dtype=object)
    regime[above & stacked] = "uptrend"
    regime[~above & stacked] = "pullback"
    regime[above & ~stacked] = "recovering"
    regime[~above & ~stacked] = "downtrend"
    regime[ma200.isna()] = None
    return regime


def base_rates(close: pd.Series) -> dict:
    """What this stock did over the next three months, historically, from days that
    looked like today. A base rate, not a forecast."""
    if len(close) < 200 + HORIZON_DAYS + 60:
        return None
    regime = _regime_series(close)
    current = regime.iloc[-1]
    if current is None:
        return None
    forward = (close.shift(-HORIZON_DAYS) / close - 1) * 100
    frame = pd.DataFrame({"regime": regime, "forward": forward}).dropna()
    same = frame[frame["regime"] == current]["forward"]
    if len(same) < 40:
        return None
    # Count separate stretches spent in this regime: consecutive days are not
    # independent observations, so this is the honest sample size.
    in_regime = (regime == current).astype(int)
    episodes = int(((in_regime.diff() == 1).sum()) + (1 if in_regime.iloc[0] == 1 else 0))
    years = round((close.index[-1] - close.index[0]).days / 365.25, 1)
    return {
        "regime": current,
        "regime_label": REGIMES[current],
        "horizon_days": HORIZON_DAYS,
        "years": years,
        "days": int(len(same)),
        "episodes": episodes,
        "median_return": _r(float(same.median())),
        "positive_rate": _r(float((same > 0).mean() * 100), 0),
        "lower_quartile": _r(float(same.quantile(0.25))),
        "upper_quartile": _r(float(same.quantile(0.75))),
        "worst": _r(float(same.min())),
        "best": _r(float(same.max())),
        "baseline_median": _r(float(frame["forward"].median())),
        "baseline_positive_rate": _r(float((frame["forward"] > 0).mean() * 100), 0),
    }


def analyse_price(close: pd.Series, bench: pd.Series, bench_name: str, sym: str):
    """Returns (price facts, trend pillar, momentum pillar, stability pillar)."""
    last = float(close.iloc[-1])

    def ret(series, n):
        return float(series.iloc[-1] / series.iloc[-1 - n] - 1) * 100 if len(series) > n else None

    year = close.tail(252)
    high, low = float(year.max()), float(year.min())
    returns = close.pct_change().dropna()
    ma50_s, ma200_s = close.rolling(50).mean(), close.rolling(200).mean()
    ma50, ma200 = _f(ma50_s.iloc[-1]), _f(ma200_s.iloc[-1])
    slope200 = _f(ma200_s.iloc[-1] / ma200_s.iloc[-22] - 1) if len(close) >= 222 else None
    ema12, ema26 = close.ewm(span=12, adjust=False).mean(), close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    macd_hist = float((macd_line - macd_line.ewm(span=9, adjust=False).mean()).iloc[-1])
    rsi = _rsi(close)
    vol = float(returns.tail(60).std() * np.sqrt(252) * 100) if len(returns) >= 60 else None
    max_dd = float((year / year.cummax() - 1).min() * 100)
    from_high = (last / high - 1) * 100
    quarter = close.tail(63)

    beta = rel_3m = rel_1y = bench_1y = None
    if bench is not None and len(bench) > 70:
        b_ret = bench.pct_change().dropna()
        # Compare by calendar date so different exchange timezones still line up.
        a = returns.copy(); a.index = [d.date() for d in a.index]
        b = b_ret.copy(); b.index = [d.date() for d in b.index]
        joined = pd.concat([a, b], axis=1, join="inner").tail(252).dropna()
        if len(joined) > 120 and joined.iloc[:, 1].var() > 0:
            beta = float(joined.iloc[:, 0].cov(joined.iloc[:, 1]) / joined.iloc[:, 1].var())
        bench_1y, bench_3m = ret(bench, 252), ret(bench, 63)
        r1y, r3m = ret(close, 252), ret(close, 63)
        rel_1y = r1y - bench_1y if (r1y is not None and bench_1y is not None) else None
        rel_3m = r3m - bench_3m if (r3m is not None and bench_3m is not None) else None

    facts = {
        "last": round(last, 2),
        "return_1m": _r(ret(close, 21)), "return_3m": _r(ret(close, 63)),
        "return_6m": _r(ret(close, 126)), "return_1y": _r(ret(close, 252)),
        "high_52w": round(high, 2), "low_52w": round(low, 2),
        "range_position": _r((last - low) / (high - low) * 100, 0) if high > low else None,
        "from_high": _r(from_high), "max_drawdown_1y": _r(max_dd),
        "volatility": _r(vol), "beta": _r(beta, 2), "rsi": _r(rsi),
        "ma50": _r(ma50, 2), "ma200": _r(ma200, 2),
        "low_3m": round(float(quarter.min()), 2), "high_3m": round(float(quarter.max()), 2),
        "benchmark": bench_name, "benchmark_return_1y": _r(bench_1y),
        "relative_1y": _r(rel_1y), "relative_3m": _r(rel_3m),
    }

    # Trend
    trend = Pillar("trend", "Trend")
    if ma200:
        gap = (last / ma200 - 1) * 100
        trend.add(2 if gap > 0 else -2, 2,
                  f"Price is {abs(gap):.1f}% {'above' if gap > 0 else 'below'} its 200-day average",
                  "The 200-day average is the most widely watched line between a long-term uptrend and downtrend.")
        if ma50:
            up = ma50 > ma200
            trend.add(2 if up else -2, 2,
                      f"50-day average is {'above' if up else 'below'} the 200-day average",
                      "Medium-term direction is " + ("stronger" if up else "weaker") + " than the long-term direction.")
        if slope200 is not None:
            pts = 1 if slope200 > 0.005 else (-1 if slope200 < -0.005 else 0)
            word = "rising" if pts > 0 else ("falling" if pts < 0 else "flat")
            trend.add(pts, 1, f"200-day average is {word} ({slope200 * 100:+.1f}% over the last month)",
                      "A rising long-term average means the underlying trend is still being built up, not just held.")
    if ma50:
        gap50 = (last / ma50 - 1) * 100
        trend.add(1 if gap50 > 0 else -1, 1,
                  f"Price is {abs(gap50):.1f}% {'above' if gap50 > 0 else 'below'} its 50-day average",
                  "Short-term position relative to the last ten weeks of trading.")
    r6 = facts["return_6m"]
    if r6 is not None:
        pts = _band(r6, [(10, 2), (3, 1), (-3, 0), (-10, -1)], -2)
        trend.add(pts, 2, f"{r6:+.1f}% over the last six months", "Six-month price change.")

    # Momentum
    momentum = Pillar("momentum", "Momentum")
    if rsi >= 70:
        momentum.add(-1, 2, f"RSI at {rsi:.0f}: stretched",
                     "Readings above 70 mean the recent rise has been fast. Strong, but more prone to a pause.")
    elif rsi >= 55:
        momentum.add(2, 2, f"RSI at {rsi:.0f}: buyers in control", "Between 55 and 70 is firm momentum without being stretched.")
    elif rsi >= 45:
        momentum.add(0, 2, f"RSI at {rsi:.0f}: balanced", "Neither buyers nor sellers have the upper hand.")
    elif rsi >= 30:
        momentum.add(-2, 2, f"RSI at {rsi:.0f}: sellers in control", "Between 30 and 45 is persistent selling pressure.")
    else:
        momentum.add(-1, 2, f"RSI at {rsi:.0f}: oversold",
                     "Below 30 is heavy selling. Weak, though sharp bounces often start from here.")
    momentum.add(1 if macd_hist > 0 else -1, 1,
                 f"MACD is {'above' if macd_hist > 0 else 'below'} its signal line",
                 "Short-term momentum is " + ("improving." if macd_hist > 0 else "fading."))
    r1 = facts["return_1m"]
    if r1 is not None:
        momentum.add(1 if r1 > 3 else (-1 if r1 < -3 else 0), 1, f"{r1:+.1f}% over the last month", "One-month price change.")
    if rel_3m is not None:
        pts = 2 if rel_3m > 5 else (-2 if rel_3m < -5 else 0)
        word = "ahead of" if rel_3m > 0 else "behind"
        momentum.add(pts, 2, f"{abs(rel_3m):.1f} points {word} the {bench_name} over three months",
                     "Relative strength: is the stock beating the market, or just moving with it?")

    # Stability (higher score = calmer)
    stability = Pillar("stability", "Stability")
    if vol is not None:
        pts = 2 if vol < 20 else (1 if vol < 30 else (-1 if vol < 45 else -2))
        stability.add(pts, 2, f"Volatility of {vol:.0f}% a year",
                      "Annualised from the last 60 trading days. Large, steady companies usually sit between 15% and 30%.")
    pts = 2 if max_dd > -15 else (0 if max_dd > -25 else (-1 if max_dd > -40 else -2))
    stability.add(pts, 2, f"Largest fall in the past year: {max_dd:.0f}%",
                  "Peak-to-trough decline. This is what holding the stock through its worst stretch felt like.")
    pts = 1 if from_high > -5 else (0 if from_high > -20 else -2)
    stability.add(pts, 2, f"{abs(from_high):.0f}% below its 52-week high" if from_high < -0.5 else "At its 52-week high",
                  f"52-week range: {low:,.2f} to {high:,.2f}.")
    if beta is not None:
        pts = 1 if beta < 0.8 else (0 if beta <= 1.3 else -1)
        stability.add(pts, 1, f"Beta of {beta:.2f} against the {bench_name}",
                      "Above 1 means it has moved more than the market; below 1, less.")

    chart_src = close.tail(252)
    chart = {
        "dates": [d.strftime("%Y-%m-%d") for d in chart_src.index],
        "close": [round(float(v), 2) for v in chart_src],
        "ma50": [_r(_f(v), 2) for v in ma50_s.tail(252)],
        "ma200": [_r(_f(v), 2) for v in ma200_s.tail(252)],
    }
    return facts, trend, momentum, stability, chart


# ── fundamentals ─────────────────────────────────────────────────────────────

def analyse_fundamentals(statements: dict, price: float, market_cap, currency: str,
                         sector: str, financial_currency: str, info_pe):
    """Returns (facts or None, quality, growth, valuation, balance pillars)."""
    quality, growth = Pillar("quality", "Profitability"), Pillar("growth", "Growth")
    valuation, balance = Pillar("valuation", "Valuation"), Pillar("balance", "Balance sheet")
    inc, bs, cf, qt = (statements.get(k) for k in ("income", "balance", "cashflow", "quarterly"))
    if inc is None:
        return None, quality, growth, valuation, balance

    revenue, revenue_prev = _val(inc, ["Total Revenue"]), _val(inc, ["Total Revenue"], 1)
    revenue_3y = _val(inc, ["Total Revenue"], 3)
    net_income = _val(inc, ["Net Income", "Net Income Common Stockholders"])
    op_income, op_income_prev = _val(inc, ["Operating Income"]), _val(inc, ["Operating Income"], 1)
    gross = _val(inc, ["Gross Profit"])
    ebitda = _val(inc, ["EBITDA", "Normalized EBITDA"])
    ebit = _val(inc, ["EBIT"]) or op_income
    interest = _val(inc, ["Interest Expense"])
    eps, eps_prev = _val(inc, ["Diluted EPS", "Basic EPS"]), _val(inc, ["Diluted EPS", "Basic EPS"], 1)
    shares, shares_prev = _val(inc, ["Diluted Average Shares"]), _val(inc, ["Diluted Average Shares"], 1)

    equity, equity_prev = _val(bs, ["Stockholders Equity"]), _val(bs, ["Stockholders Equity"], 1)
    debt = _val(bs, ["Total Debt"])
    cash = _val(bs, ["Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents"])
    cur_assets, cur_liab = _val(bs, ["Current Assets"]), _val(bs, ["Current Liabilities"])
    fcf = _val(cf, ["Free Cash Flow"])

    is_financial = "financial" in (sector or "").lower() or (op_income is None and cur_assets is None)
    period = inc.columns[0]
    period_label = f"year to {period.strftime('%b %Y')}"

    op_margin = _ratio(op_income, revenue)
    op_margin_prev = _ratio(op_income_prev, revenue_prev)
    net_margin = _ratio(net_income, revenue)
    avg_equity = (equity + equity_prev) / 2 if (equity and equity_prev) else equity
    roe = _ratio(net_income, avg_equity) if (avg_equity and avg_equity > 0) else None
    rev_yoy = _growth(revenue, revenue_prev)
    rev_cagr = ((revenue / revenue_3y) ** (1 / 3) - 1) * 100 if (revenue and revenue_3y and revenue_3y > 0 and revenue > 0) else None
    eps_yoy = _growth(eps, eps_prev)
    share_change = _growth(shares, shares_prev)
    net_debt = (debt - (cash or 0)) if debt is not None else None

    # Latest quarter against the same quarter a year earlier.
    q_rev_yoy = q_label = None
    eps_ttm = None
    if qt is not None:
        q0 = qt.columns[0]
        for i, col in enumerate(qt.columns[1:], start=1):
            if 350 <= (q0 - col).days <= 380:
                q_rev_yoy = _growth(_val(qt, ["Total Revenue"]), _val(qt, ["Total Revenue"], i))
                q_label = f"quarter to {q0.strftime('%b %Y')}"
                break
        if qt.shape[1] >= 4 and 260 <= (q0 - qt.columns[3]).days <= 290 and q0 > period:
            parts = [_val(qt, ["Diluted EPS", "Basic EPS"], i) for i in range(4)]
            if all(p is not None for p in parts):
                eps_ttm = sum(parts)

    # Valuation mixes the share price with reported figures, so both must be in
    # the same currency (they are not for some foreign listings).
    same_currency = not financial_currency or not currency or financial_currency.upper() == currency.upper()
    pe = ps = ev_ebitda = fcf_yield = peg = None
    if same_currency:
        eps_for_pe = eps_ttm if eps_ttm is not None else eps
        if eps_for_pe is not None and price:
            pe = price / eps_for_pe if eps_for_pe > 0 else -1.0
        elif info_pe:
            pe = float(info_pe)
        if market_cap:
            ps = _ratio(market_cap, revenue)
            fcf_yield = _ratio(fcf, market_cap)
            if ebitda and ebitda > 0 and net_debt is not None and not is_financial:
                ev_ebitda = (market_cap + net_debt) / ebitda
        if pe and pe > 0 and eps_yoy and 2 <= eps_yoy <= 150:
            peg = pe / eps_yoy

    # Profitability
    if op_margin is not None and not is_financial:
        m = op_margin * 100
        quality.add(_band(m, [(25, 2), (12, 1), (5, 0), (0, -1)], -2), 2, f"Operating margin of {m:.1f}%",
                    "Operating profit per 100 of sales. Shows pricing power and cost control before interest and tax.")
        if op_margin_prev is not None:
            delta = (op_margin - op_margin_prev) * 100
            quality.add(1 if delta > 1.5 else (-1 if delta < -1.5 else 0), 1,
                        f"Operating margin {'widened' if delta > 0 else 'narrowed'} by {abs(delta):.1f} points on the year",
                        "Widening margins mean profit is growing faster than sales.")
    elif net_margin is not None:
        m = net_margin * 100
        quality.add(_band(m, [(20, 2), (10, 1), (4, 0), (0, -1)], -2), 2, f"Net margin of {m:.1f}%",
                    "Profit after all costs per 100 of revenue.")
    if roe is not None:
        r = roe * 100
        quality.add(_band(r, [(20, 2), (12, 1), (6, 0), (0, -1)], -2), 2, f"Return on equity of {r:.1f}%",
                    "Profit earned on shareholders' money. Above 15% sustained is the mark of a strong business.")
    if fcf is not None and net_income and not is_financial:
        if net_income > 0:
            conv = fcf / net_income
            pts = -2 if fcf < 0 else _band(conv, [(0.9, 2), (0.6, 1), (0.3, 0)], -1)
            quality.add(pts, 2, f"{conv * 100:.0f}% of reported profit arrived as free cash" if fcf >= 0 else "Free cash flow is negative",
                        "Profit that turns into cash is higher-quality profit. Free cash flow is cash left after running and investing in the business.")
        elif fcf < 0:
            quality.add(-2, 2, "Loss-making and burning cash", "Both reported profit and free cash flow are negative.")

    # Growth
    if rev_yoy is not None:
        growth.add(_band(rev_yoy, [(20, 2), (8, 1), (0, 0), (-5, -1)], -2), 2,
                   f"Revenue {'grew' if rev_yoy >= 0 else 'fell'} {abs(rev_yoy):.1f}% in the latest year", f"Annual revenue, {period_label}.")
    if rev_cagr is not None:
        growth.add(_band(rev_cagr, [(15, 2), (7, 1), (0, 0)], -1), 2,
                   f"Revenue compounded at {rev_cagr:.1f}% a year over three years",
                   "A multi-year rate smooths out one-off good or bad years.")
    if eps_yoy is not None:
        growth.add(_band(eps_yoy, [(20, 2), (5, 1), (-5, 0), (-20, -1)], -2), 2,
                   f"Earnings per share {'rose' if eps_yoy >= 0 else 'fell'} {abs(eps_yoy):.1f}%", f"Diluted EPS, {period_label}.")
    elif eps is not None and eps_prev is not None and eps_prev <= 0:
        growth.add(1 if eps > 0 else -1, 2, "Turned profitable" if eps > 0 else "Still loss-making",
                   "Earnings per share compared with a loss the year before.")
    if q_rev_yoy is not None:
        growth.add(1 if q_rev_yoy >= 10 else (-1 if q_rev_yoy < 0 else 0), 1,
                   f"Latest quarter revenue {q_rev_yoy:+.1f}% on a year earlier", f"Most recent reported {q_label}.")

    # Valuation (higher score = cheaper)
    if pe is not None:
        if pe <= 0:
            valuation.add(-2, 2, "No earnings to value the shares on", "The company reported a loss, so a price-to-earnings ratio does not apply.")
        elif pe < 500:
            valuation.add(_band(-pe, [(-12, 2), (-20, 1), (-30, 0), (-45, -1)], -2), 2, f"Price is {pe:.1f} times earnings",
                          "What you pay for each 1 of annual profit. Long-run market averages sit around 15 to 25.")
    if peg is not None:
        valuation.add(_band(-peg, [(-1, 2), (-2, 1), (-3, 0)], -1), 2, f"P/E is {peg:.1f} times the earnings growth rate",
                      "A high P/E can be reasonable if earnings are growing fast. Below 1 is cheap for the growth; above 3 is expensive.")
    if fcf_yield is not None and not is_financial:
        y = fcf_yield * 100
        valuation.add(_band(y, [(6, 2), (3.5, 1), (1.5, 0), (0, -1)], -2), 2, f"Free cash flow yield of {y:.1f}%",
                      "Free cash generated each year as a share of what the whole company costs to buy.")
    if not same_currency:
        valuation.note = f"Not assessed: the company reports in {financial_currency} but the shares trade in {currency}."
    elif valuation.max_points:
        valuation.note = "Judged on absolute levels, not against sector peers."

    # Balance sheet
    if is_financial:
        balance.note = "Not scored for banks and lenders: borrowing is their business, so the usual debt tests do not apply."
    else:
        if net_debt is not None and ebitda and ebitda > 0:
            if net_debt <= 0:
                balance.add(2, 2, "More cash than debt", f"Net cash of {format_money(-net_debt, financial_currency or currency)}.")
            else:
                lev = net_debt / ebitda
                balance.add(_band(-lev, [(-1.5, 1), (-3, 0), (-4.5, -1)], -2), 2, f"Net debt is {lev:.1f} times annual EBITDA",
                            "How many years of operating profit it would take to repay debt. Under 2 is comfortable; above 4 is heavy.")
        if interest and ebit is not None and abs(interest) > 0:
            cover = ebit / abs(interest)
            balance.add(_band(cover, [(10, 2), (4, 1), (2, 0), (1, -1)], -2), 2, f"Operating profit covers interest {cover:.1f} times",
                        "The cushion between what the business earns and what its lenders are owed each year.")
        if cur_assets and cur_liab:
            cr = cur_assets / cur_liab
            balance.add(1 if cr >= 1.5 else (0 if cr >= 1 else -1), 1, f"Current ratio of {cr:.2f}",
                        "Assets due within a year against bills due within a year. Below 1 means relying on fresh cash or credit.")

    fin_cur = financial_currency or currency
    pct = lambda v: None if v is None else f"{v * 100:.1f}%"
    metrics = [
        ("Revenue", format_money(revenue, fin_cur)), ("Net profit", format_money(net_income, fin_cur)),
        ("Revenue growth", None if rev_yoy is None else f"{rev_yoy:+.1f}%"),
        ("EPS growth", None if eps_yoy is None else f"{eps_yoy:+.1f}%"),
        ("Operating margin", None if is_financial else pct(op_margin)), ("Net margin", pct(net_margin)),
        ("Return on equity", pct(roe)),
        ("Free cash flow", None if (fcf is None or is_financial) else format_money(fcf, fin_cur)),
        ("P/E", None if (pe is None or pe <= 0 or pe >= 500) else f"{pe:.1f}x"),
        ("EV / EBITDA", None if ev_ebitda is None else f"{ev_ebitda:.1f}x"),
        ("Price / sales", None if ps is None else f"{ps:.1f}x"),
        ("Net debt", None if (net_debt is None or is_financial) else (format_money(net_debt, fin_cur) if net_debt > 0 else "Net cash")),
        ("Share count", None if share_change is None else f"{share_change:+.1f}%"),
    ]
    history = []
    for i in range(min(inc.shape[1], 5) - 1, -1, -1):
        rev_i, ni_i = _val(inc, ["Total Revenue"], i), _val(inc, ["Net Income"], i)
        if rev_i is not None:
            history.append({"period": inc.columns[i].strftime("%Y"), "revenue": rev_i, "net_income": ni_i})

    facts = {
        "period_label": period_label, "currency": fin_cur, "is_financial": is_financial,
        "metrics": [{"label": label, "value": value} for label, value in metrics if value and value != "n/a"],
        "history": history,
        "pe": _r(pe) if (pe and 0 < pe < 500) else None,
        "revenue_growth": _r(rev_yoy), "eps_growth": _r(eps_yoy),
        "revenue": revenue, "net_income": net_income,
    }
    return facts, quality, growth, valuation, balance


# ── assembly ─────────────────────────────────────────────────────────────────

def _news_pillar(articles: list) -> Pillar:
    news = Pillar("news", "News flow")
    total = len(articles)
    if not total:
        news.note = "No recent headlines found."
        return news
    pos = sum(1 for a in articles if a.get("sentiment") == "positive")
    neg = sum(1 for a in articles if a.get("sentiment") == "negative")
    net = (pos - neg) / total
    news.add(round(net * 2 * min(1, total / 5), 2), 2,
             f"{pos} positive, {neg} negative, {total - pos - neg} neutral of {total} recent headlines",
             "Tone of recent coverage, judged from headline wording. A weak signal on its own.")
    return news


def _weighted(parts):
    """parts: [(score or None, weight)] -> weighted mean of what is available."""
    live = [(s, w) for s, w in parts if s is not None]
    if not live:
        return None
    return sum(s * w for s, w in live) / sum(w for _, w in live)


# When price behaviour and the business point in opposite directions, the overall
# score sits near the middle for a reason that a single number hides. Such reports
# are flagged and their confidence is capped.
CONFLICT_CONFIDENCE_CAP = 60


def assess_conflict(technical_score, fundamental_score):
    """(conflicted, note). Conflicted when both scores exist and fall on opposite
    sides of 50; a score of exactly 50 is on neither side."""
    if technical_score is None or fundamental_score is None:
        return False, ""
    t, f = float(technical_score), float(fundamental_score)
    if (t > 50 and f < 50) or (t < 50 and f > 50):
        price_side, business_side = ("positive", "negative") if t > 50 else ("negative", "positive")
        return True, (f"Price evidence is {price_side} ({t:.0f}/100) while the business evidence is "
                      f"{business_side} ({f:.0f}/100); confidence is capped at {CONFLICT_CONFIDENCE_CAP}%.")
    return False, ""


def build(symbol: str, stock_data: dict, articles: list) -> dict:
    """Runs the full evidence pass for one symbol."""
    bench_symbol, bench_name = benchmark_for(symbol)
    with ThreadPoolExecutor(max_workers=4) as pool:
        f_close = pool.submit(_history, symbol, "5y")
        f_bench = pool.submit(_history, bench_symbol, "2y")
        f_stmt = pool.submit(_statements, symbol)
        f_cal = pool.submit(_calendar, symbol)
        close, bench, statements, events = f_close.result(), f_bench.result(), f_stmt.result(), f_cal.result()

    if len(close) < 30:
        raise ValueError(f"Not enough price history for {symbol}")

    currency = stock_data.get("currency") or ("INR" if symbol.endswith((".NS", ".BO")) else "USD")
    facts, trend, momentum, stability, chart = analyse_price(close, bench if len(bench) else None, bench_name, symbol)
    fund_facts, quality, growth, valuation, balance = analyse_fundamentals(
        statements, stock_data.get("price") or facts["last"], stock_data.get("market_cap_raw"), currency,
        stock_data.get("sector"), stock_data.get("financial_currency"), stock_data.get("pe_ratio"))
    news = _news_pillar(articles)

    pillars = [trend, momentum, stability, quality, growth, valuation, balance, news]
    technical_score = _weighted([(trend.score, 0.65), (momentum.score, 0.35)])
    fundamental_score = _weighted([(quality.score, 0.3), (growth.score, 0.3), (valuation.score, 0.25), (balance.score, 0.15)])
    composite = _weighted([(technical_score, 0.40), (fundamental_score, 0.45), (news.score, 0.15)])

    # Confidence is about the evidence, not about the direction: how much data we
    # had, how far the pillars agree, and how far the result is from a coin toss.
    scored = [p.score for p in pillars if p.score is not None and p.key != "stability"]
    coverage = len([p for p in pillars if p.score is not None]) / len(pillars)
    spread = float(np.std(scored)) if len(scored) > 1 else 30.0
    agreement = max(0.0, 1 - spread / 30)
    conviction = min(1.0, abs(composite - 50) / 25)
    confidence = int(round(min(92, 30 + 30 * coverage + 20 * agreement + 20 * conviction)))
    conflicted, conflict_note = assess_conflict(technical_score, fundamental_score)
    if conflicted:
        confidence = min(confidence, CONFLICT_CONFIDENCE_CAP)

    risk_points = _weighted([(100 - stability.score if stability.score is not None else None, 0.7),
                             (100 - balance.score if balance.score is not None else None, 0.3)])
    risk = "High" if risk_points >= 60 else ("Medium" if risk_points >= 40 else "Low")
    bias = "Bullish" if composite >= 60 else ("Bearish" if composite <= 40 else "Neutral")

    findings = [f for p in pillars for f in p.findings]
    def top(tone):
        """Heaviest findings first, at most two per pillar so one theme cannot crowd out the rest."""
        picked, per_pillar = [], {}
        for f in sorted([f for f in findings if f["tone"] == tone], key=lambda f: -f["weight"]):
            if per_pillar.get(f["pillar"], 0) < 2:
                picked.append(f)
                per_pillar[f["pillar"]] = per_pillar.get(f["pillar"], 0) + 1
        return picked

    strengths, concerns = top("positive"), top("negative")

    sym_cur = currency_symbol(currency)
    watch = []
    if facts["ma200"]:
        side = "below" if facts["last"] > facts["ma200"] else "above"
        watch.append(f"A close {side} the 200-day average at {sym_cur}{facts['ma200']:,.2f} would change the long-term trend reading.")
    watch.append(f"The three-month range is {sym_cur}{facts['low_3m']:,.2f} to {sym_cur}{facts['high_3m']:,.2f}; a break of either end is the next signal.")
    if events.get("earnings"):
        watch.append(f"Next earnings are scheduled for {events['earnings']}; growth and margin figures there will update this view.")
    if fund_facts and fund_facts.get("pe") and fund_facts["pe"] > 30:
        watch.append(f"At {fund_facts['pe']:.0f} times earnings the price assumes continued growth; a slowdown would matter more than usual.")

    calendar = []
    if events.get("earnings"):
        calendar.append({"event": "Earnings release", "expected_date": events["earnings"], "importance": "High",
                         "potential_impact": "Updates revenue, margin and earnings growth, the inputs behind the fundamental scores."})
    if events.get("ex_dividend"):
        calendar.append({"event": "Ex-dividend date", "expected_date": events["ex_dividend"], "importance": "Low",
                         "potential_impact": "Shares bought on or after this date do not receive the upcoming dividend."})

    words_cheap = ("Cheap", "Reasonable", "Fair", "Full", "Expensive")
    words_calm = ("Calm", "Steady", "Average", "Choppy", "Volatile")
    scorecard = []
    for p in pillars:
        words = words_cheap if p.key == "valuation" else (words_calm if p.key == "stability" else ("Strong", "Good", "Mixed", "Soft", "Weak"))
        scorecard.append(p.as_dict(words))

    return {
        "as_of": close.index[-1].strftime("%Y-%m-%d"),
        "name": stock_data.get("name"), "sector": stock_data.get("sector"), "industry": stock_data.get("industry"),
        "currency": currency, "currency_symbol": sym_cur,
        "market_cap": format_money(stock_data.get("market_cap_raw"), currency) if stock_data.get("market_cap_raw") else None,
        "composite": int(round(composite)), "technical_score": _r(technical_score, 0), "fundamental_score": _r(fundamental_score, 0),
        "bias": bias, "confidence": confidence, "risk": risk,
        "conflicted": conflicted, "conflict_note": conflict_note,
        "scorecard": scorecard,
        "findings": [{k: v for k, v in f.items() if k != "weight"} for f in findings],
        "strengths": [{k: v for k, v in f.items() if k != "weight"} for f in strengths[:5]],
        "concerns": [{k: v for k, v in f.items() if k != "weight"} for f in concerns[:5]],
        "price": facts, "chart": chart,
        "base_rates": base_rates(close),
        "fundamentals": fund_facts,
        "watch": watch, "calendar": calendar,
        "coverage": {"prices": True, "financials": fund_facts is not None, "headlines": len(articles),
                     "benchmark": facts["beta"] is not None, "earnings_date": bool(events.get("earnings"))},
    }
