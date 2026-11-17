# technical_agent.py
# Reads the price evidence (trend, momentum and stability pillars) produced by
# services/research_engine.py and reports it in the Technical section's shape.
# Scores are calculated, never written by a language model.

SCORE_WORDS = {"trend": "trend", "momentum": "momentum", "stability": "stability"}


def _pillar(research: dict, key: str) -> dict:
    return next((p for p in research["scorecard"] if p["key"] == key), {"score": None, "verdict": "Not assessed"})


def _titles(research: dict, keys, tone=None) -> list:
    return [f["title"] for f in research["findings"]
            if f["pillar"] in keys and (tone is None or f["tone"] == tone)]


def analyze(stock_data: dict, research: dict) -> dict:
    price = research["price"]
    sym = research["currency_symbol"]
    last = price["last"]
    score = research["technical_score"]
    trend_p, momentum_p = _pillar(research, "trend"), _pillar(research, "momentum")

    if score is None:
        trend, strength = "Neutral", "Weak"
    else:
        trend = "Bullish" if score >= 60 else ("Bearish" if score <= 40 else "Neutral")
        distance = abs(score - 50)
        strength = "Strong" if distance >= 30 else ("Moderate" if distance >= 12 else "Weak")

    support, resistance = price["low_3m"], price["high_3m"]
    to_support = round((last - support) / last * 100, 2) if last else 0.0
    to_resistance = round((resistance - last) / last * 100, 2) if last else 0.0

    def label(ret):
        if ret is None:
            return "No data"
        return "Rising" if ret > 3 else ("Falling" if ret < -3 else "Flat")

    ma200 = price.get("ma200")
    ma50 = price.get("ma50")
    summary = (
        f"Trend scores {trend_p['score']}/100 ({trend_p['verdict'].lower()}) and momentum "
        f"{momentum_p['score']}/100 ({momentum_p['verdict'].lower()}). "
        + (f"The price is {sym}{last:,.2f} against a 200-day average of {sym}{ma200:,.2f}. " if ma200 else "")
        + (f"Over one year the stock returned {price['return_1y']:+.1f}% "
           f"against {price['benchmark_return_1y']:+.1f}% for the {price['benchmark']}."
           if price.get("return_1y") is not None and price.get("benchmark_return_1y") is not None else "")
    ).strip()

    rsi = price["rsi"]
    return {
        "trend": trend,
        "confidence": int(score if score is not None else 50),
        "score": score,
        "reason": summary,
        "summary": summary,
        "trend_strength": strength,
        "support": support,
        "resistance": resistance,
        "support_level": support,
        "resistance_level": resistance,
        "distance_to_support": to_support,
        "distance_to_resistance": to_resistance,
        "volatility": price["volatility"] if price["volatility"] is not None else stock_data.get("volatility", 0.0),
        "signals": _titles(research, ("trend", "momentum")),
        "risk_factors": _titles(research, ("stability",), "negative"),
        "timeframe_analysis": {
            "1 month": label(price["return_1m"]), "3 months": label(price["return_3m"]),
            "6 months": label(price["return_6m"]), "1 year": label(price["return_1y"]),
        },
        "rsi_interpretation": next((f["title"] + ". " + f["detail"] for f in research["findings"]
                                    if f["pillar"] == "momentum" and f["title"].startswith("RSI")), ""),
        "macd_interpretation": next((f["title"] + ". " + f["detail"] for f in research["findings"]
                                     if f["title"].startswith("MACD")), ""),
        "moving_average_analysis": (f"50-day average {sym}{ma50:,.2f}, 200-day average {sym}{ma200:,.2f}."
                                    if (ma50 and ma200) else ""),
        "key_technical_conclusion": summary,
        "fallback_active": False,
    }
