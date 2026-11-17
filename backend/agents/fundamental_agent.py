# fundamental_agent.py
# Reads the company-financials evidence (profitability, growth, valuation and
# balance-sheet pillars) from services/research_engine.py and reports it in the
# Fundamental section's shape. Every figure comes from reported statements.


def _pillar(research: dict, key: str) -> dict:
    return next((p for p in research["scorecard"] if p["key"] == key), {"score": None, "verdict": "Not assessed"})


FUND_PILLARS = ("quality", "growth", "valuation", "balance")


def analyze(stock_data: dict, research: dict) -> dict:
    facts = research.get("fundamentals")
    market_cap = research.get("market_cap") or stock_data.get("market_cap", "N/A")

    if not facts or research.get("fundamental_score") is None:
        unavailable = "Company financial statements could not be retrieved for this report, so fundamentals were not assessed."
        return {
            "fundamental": "Unavailable", "confidence": 0, "score": None,
            "reason": unavailable, "summary": unavailable,
            "health_score": 0, "valuation_score": 0, "growth_score": 0,
            "strengths": [], "weaknesses": [],
            "metrics": {"pe_ratio": None, "revenue_growth_pct": None, "earnings_growth_pct": None,
                        "market_cap": market_cap, "total_revenue": None, "net_income": None},
            "fallback_active": False, "data_available": False,
            "growth_outlook": "", "valuation_outlook": "", "ai_commentary": unavailable,
        }

    score = research["fundamental_score"]
    quality, growth, valuation, balance = (_pillar(research, k) for k in FUND_PILLARS)
    verdict = "Strong" if score >= 62 else ("Weak" if score <= 40 else "Average")

    def titles(tone):
        return [f["title"] for f in research["findings"] if f["pillar"] in FUND_PILLARS and f["tone"] == tone]

    def phrase(p, name):
        return f"{name} {p['score']}/100 ({p['verdict'].lower()})" if p["score"] is not None else f"{name} not assessed"

    summary = (
        f"Based on the {facts['period_label']}: " + ", ".join([
            phrase(quality, "profitability"), phrase(growth, "growth"),
            phrase(valuation, "valuation"), phrase(balance, "balance sheet"),
        ]) + "."
    )

    return {
        "fundamental": verdict,
        "confidence": int(score),
        "score": score,
        "reason": summary,
        "summary": summary,
        # health = profitability and balance sheet together
        "health_score": int(round(sum(s for s in (quality["score"], balance["score"]) if s is not None)
                                  / max(1, len([s for s in (quality["score"], balance["score"]) if s is not None])))),
        "valuation_score": int(valuation["score"] or 0),
        "growth_score": int(growth["score"] or 0),
        "strengths": titles("positive"),
        "weaknesses": titles("negative"),
        "metrics": {
            "pe_ratio": facts.get("pe"),
            "revenue_growth_pct": facts.get("revenue_growth"),
            "earnings_growth_pct": facts.get("eps_growth"),
            "market_cap": market_cap,
            "total_revenue": facts.get("revenue"),
            "net_income": facts.get("net_income"),
        },
        "fallback_active": False,
        "data_available": True,
        "growth_outlook": "; ".join(f["title"] for f in research["findings"] if f["pillar"] == "growth"),
        "valuation_outlook": "; ".join(f["title"] for f in research["findings"] if f["pillar"] == "valuation"),
        "ai_commentary": summary,
    }
