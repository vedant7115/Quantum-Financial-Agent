# master_agent.py
# Turns the calculated evidence into the written research view.
#
# The stance, confidence and risk level are calculated in research_engine.py and
# are final. The language model's only job is to explain them: it receives the
# findings with their numbers and may not introduce figures, dates or events of
# its own. If the model is unavailable, or its answer fails the checks below, a
# plain rule-written version of the same evidence is used instead.

import json
import logging
import os
import re

from services.llm_service import query_groq

logger = logging.getLogger("quantum_agent.master_agent")

ADVICE_PATTERN = re.compile(
    r"\b(strong buy|buy rating|sell rating|we recommend|should (buy|sell|hold)|"
    r"(buy|sell|accumulate|exit) (the stock|now|this stock)|target price|price target of)\b", re.I)

RISK_CATEGORIES = ["Valuation risk", "Market risk", "Business risk", "Financial risk", "News and event risk"]


def _numbers(text: str) -> set:
    """Significant numbers in a text, normalised so 39.7, 39.70 and 40 can be compared."""
    found = set()
    for token in re.findall(r"\d[\d,]*\.?\d*", text):
        try:
            found.add(round(float(token.replace(",", "")), 1))
        except ValueError:
            continue
    return found


def _unsupported_numbers(text: str, allowed: set) -> list:
    """Numbers the model wrote that do not appear in the evidence it was given."""
    bad = []
    for n in _numbers(text):
        if n <= 12 or n in (50.0, 100.0, 200.0, 14.0, 52.0):  # small counts, list indexes, indicator names
            continue
        if any(abs(n - a) <= max(0.6, abs(a) * 0.01) for a in allowed):
            continue
        bad.append(n)
    return bad


def _evidence_text(research: dict, sentiment: dict) -> str:
    lines = []
    for p in research["scorecard"]:
        score = f"{p['score']}/100, {p['verdict']}" if p["score"] is not None else f"not assessed. {p['note']}"
        lines.append(f"[{p['label']}: {score}]")
        for f in research["findings"]:
            if f["pillar"] == p["key"]:
                lines.append(f"  ({f['tone']}) {f['title']}")
    price = research["price"]
    cur = research["currency_symbol"]
    lines.append("[Price facts]")
    lines.append(f"  Last close {cur}{price['last']}; 52-week range {cur}{price['low_52w']} to {cur}{price['high_52w']}; "
                 f"1-year return {price['return_1y']}% vs {price['benchmark']} {price['benchmark_return_1y']}%.")
    base = research.get("base_rates")
    if base:
        lines.append("[History of this stock in the same trend state]")
        lines.append(f"  {base['regime_label']}. Over {base['years']} years this covered {base['days']} trading days in "
                     f"{base['episodes']} separate stretches. Three months later the median change was {base['median_return']}% "
                     f"and {base['positive_rate']}% of cases were higher. Across all days: median {base['baseline_median']}%, "
                     f"{base['baseline_positive_rate']}% higher.")
    fund = research.get("fundamentals")
    if fund:
        lines.append(f"[Reported figures, {fund['period_label']}]")
        lines.append("  " + "; ".join(f"{m['label']} {m['value']}" for m in fund["metrics"]))
    heads = sentiment.get("positive_drivers", []) + sentiment.get("negative_drivers", [])
    if heads:
        lines.append("[Recent headlines]")
        lines.extend(f"  - {h}" for h in heads[:6])
    return "\n".join(lines)


def _rule_view(research: dict, sentiment: dict) -> dict:
    """The same evidence written without a language model."""
    strengths, concerns = research["strengths"], research["concerns"]
    name = research.get("name") or "The company"
    lean = {"Bullish": "leans positive", "Bearish": "leans negative", "Neutral": "is mixed"}[research["bias"]]
    parts = [f"The evidence on {name} {lean}, scoring {research['composite']}/100 across the pillars that could be assessed."]
    if strengths:
        parts.append("In its favour: " + "; ".join(s["title"] for s in strengths[:3]) + ".")
    if concerns:
        parts.append("Against it: " + "; ".join(c["title"] for c in concerns[:3]) + ".")
    if not research["coverage"]["financials"]:
        parts.append("Company financials could not be retrieved, so this view rests on price behaviour and news only.")

    register = []
    by_pillar = {p["key"]: p for p in research["scorecard"]}

    def level(score, invert=False):
        if score is None:
            return None
        s = 100 - score if invert else score
        return "High" if s >= 65 else ("Medium" if s >= 40 else "Low")

    for category, key, text in (
        ("Valuation risk", "valuation", "valuation"), ("Market risk", "stability", "stability"),
        ("Business risk", "growth", "growth"), ("Financial risk", "balance", "balance"),
    ):
        pillar = by_pillar[key]
        if pillar["score"] is None:
            continue
        detail = [f["title"] for f in research["findings"] if f["pillar"] == key and f["tone"] != "positive"]
        if not detail:
            detail = [f["title"] for f in research["findings"] if f["pillar"] == key][:1]
        sev = level(pillar["score"], invert=True)
        register.append({"category": category, "severity": sev, "probability": sev,
                         "explanation": "; ".join(detail[:2]) + "."})

    return {
        "summary": " ".join(parts),
        "key_drivers": [f["title"] for f in (strengths[:3] + concerns[:2])],
        "bull_case": [f"{s['title']}. {s['detail']}" for s in strengths[:4]],
        "bear_case": [f"{c['title']}. {c['detail']}" for c in concerns[:4]],
        "risk_register": register,
        "potential_risks": [c["title"] for c in concerns[:4]],
        "future_catalysts": [s["title"] for s in strengths[:3]],
    }


def analyze(technical: dict, fundamental: dict, sentiment: dict, research: dict) -> dict:
    view = _rule_view(research, sentiment)
    fallback_active = True

    if os.getenv("GROQ_API_KEY"):
        evidence = _evidence_text(research, sentiment)
        stance = {"Bullish": "leans positive", "Bearish": "leans negative", "Neutral": "is mixed"}[research["bias"]]
        prompt = f"""You are writing an equity research brief for a retail investor about {research.get('name')}.
All analysis below was calculated from market data and the company's reported financial statements.

EVIDENCE
{evidence}

CALCULATED RESULT (final, do not change): the evidence {stance}; overall {research['composite']}/100;
confidence {research['confidence']}%; risk level {research['risk']}.

RULES
- Use ONLY the evidence above. Every number you write must appear in the evidence exactly.
- Do not add facts from memory: no products, executives, competitors, events, dates or forecasts that are not above.
- Never tell the reader to buy, sell or hold, and never give a target price. Explain; do not advise.
- Do not predict or imply future returns. The historical record describes the past only; say so if you mention it.
- Plain English. Short sentences. If you use a term such as RSI or free cash flow, say what it means in a few words.
- If a pillar was not assessed, say so rather than guessing.

Return ONLY a JSON object:
{{
  "summary": "Two short paragraphs separated by \\n\\n. First: what the evidence says overall and the two or three facts that matter most, with their numbers. Second: the main tension or uncertainty in the picture. Do not mention the historical record in the summary; it may be used in the cases below.",
  "key_drivers": ["3 to 5 short phrases naming the facts that drive the view, each with its number"],
  "bull_case": ["3 or 4 sentences. The strongest honest argument for the stock, each tied to a number above"],
  "bear_case": ["3 or 4 sentences. The strongest honest argument against it, each tied to a number above"],
  "risk_register": [{{"category": "one of {RISK_CATEGORIES}", "severity": "Low|Medium|High", "probability": "Low|Medium|High", "explanation": "one sentence grounded in the evidence"}}]
}}
Give 3 to 5 risk_register entries, only for risks the evidence supports."""
        try:
            llm = json.loads(query_groq(prompt))
            written = json.dumps(llm, ensure_ascii=False)
            if ADVICE_PATTERN.search(written):
                raise ValueError("model output contained investment advice wording")
            stray = _unsupported_numbers(written, _numbers(evidence))
            if len(stray) > 2:
                raise ValueError(f"model output contained numbers not in the evidence: {sorted(stray)[:6]}")
            for field in ("summary", "key_drivers", "bull_case", "bear_case", "risk_register"):
                value = llm.get(field)
                if value and isinstance(value, type(view[field])):
                    view[field] = value
            fallback_active = False
        except Exception as err:
            logger.warning(f"Synthesis model rejected or unavailable ({err}); using the rule-written view.")

    return {
        "market_bias": research["bias"],
        "confidence": research["confidence"],
        "risk": research["risk"],
        "key_drivers": view["key_drivers"],
        "watchlist_factors": research["watch"],
        "potential_risks": view["potential_risks"],
        "future_catalysts": view["future_catalysts"],
        "summary": view["summary"],
        "fallback_active": fallback_active,
        "bull_case": view["bull_case"],
        "bear_case": view["bear_case"],
        "risk_register": view["risk_register"],
        "catalyst_calendar": research["calendar"],
    }
