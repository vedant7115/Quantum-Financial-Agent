# master_agent.py
# Turns the calculated evidence into the written research view.
#
# The stance, confidence and risk level are calculated in research_engine.py and
# are final. The language model's only job is to explain them: it receives the
# findings with their numbers and may not introduce figures, dates or events of
# its own. Its answer must match the Brief schema below and pass two checks
# (no advice wording, no numbers missing from the evidence). A failed answer is
# retried once with the reason attached; if that also fails, or no model is
# available, a plain rule-written version of the same evidence is used instead.

import logging
import os
import re
from typing import List, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError, field_validator
from typing_extensions import Annotated

from services.llm_service import query_groq_with_meta

logger = logging.getLogger("quantum_agent.master_agent")

# Bump this whenever the prompt text or the expected JSON shape changes. It is
# logged and returned with every report so a brief can be traced to its prompt.
PROMPT_VERSION = "v2.0"

ADVICE_PATTERN = re.compile(
    r"\b(strong buy|buy rating|sell rating|we recommend|should (buy|sell|hold)|"
    r"(buy|sell|accumulate|exit) (the stock|now|this stock)|target price|price target of)\b", re.I)

RISK_CATEGORIES = ["Valuation risk", "Market risk", "Business risk", "Financial risk", "News and event risk"]

Line = Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=600)]
Level = Literal["Low", "Medium", "High"]


class RiskItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    category: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=60)]
    severity: Level
    probability: Level
    explanation: Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=600)]


class Brief(BaseModel):
    """The shape the model must return. Anything else is rejected."""
    model_config = ConfigDict(extra="ignore")
    summary: Annotated[str, StringConstraints(strip_whitespace=True, min_length=80, max_length=3000)]
    key_drivers: List[Line] = Field(min_length=2, max_length=6)
    bull_case: List[Line] = Field(min_length=2, max_length=5)
    bear_case: List[Line] = Field(min_length=2, max_length=5)
    risk_register: List[RiskItem] = Field(min_length=1, max_length=6)

    @field_validator("key_drivers", "bull_case", "bear_case", mode="before")
    @classmethod
    def one_point_per_item(cls, value):
        """Some models put several points in one string separated by line breaks.
        Split those into separate items; the wording itself is not changed."""
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, list):
            return value
        items = []
        for item in value:
            if isinstance(item, str):
                items.extend(p.strip(" -*•\t") for p in item.splitlines() if p.strip(" -*•\t"))
            else:
                items.append(item)
        return items


class BriefRejected(ValueError):
    """The model answered in the right shape, but the answer broke a rule."""


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


def check_brief(text: str, evidence: str) -> Brief:
    """Parses and checks a model answer. Raises ValidationError (bad JSON or wrong
    shape) or BriefRejected (advice wording, or numbers not in the evidence)."""
    brief = Brief.model_validate_json(text)
    written = brief.model_dump_json()
    if ADVICE_PATTERN.search(written):
        raise BriefRejected("contains investment advice wording")
    stray = _unsupported_numbers(written, _numbers(evidence))
    if len(stray) > 2:
        raise BriefRejected(f"contains numbers not in the evidence: {sorted(stray)[:6]}")
    return brief


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
    if research.get("conflicted"):
        lines.append("[Conflict]")
        lines.append(f"  Price score {research['technical_score']}/100, business score {research['fundamental_score']}/100: "
                     "they point in opposite directions.")
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
    if research.get("conflicted"):
        parts.append(research["conflict_note"])
    if not research["coverage"]["financials"]:
        parts.append("Company financials could not be retrieved, so this view rests on price behaviour and news only.")

    register = []
    by_pillar = {p["key"]: p for p in research["scorecard"]}

    def level(score, invert=False):
        if score is None:
            return None
        s = 100 - score if invert else score
        return "High" if s >= 65 else ("Medium" if s >= 40 else "Low")

    for category, key in (
        ("Valuation risk", "valuation"), ("Market risk", "stability"),
        ("Business risk", "growth"), ("Financial risk", "balance"),
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


def _prompt(research: dict, evidence: str) -> str:
    stance = {"Bullish": "leans positive", "Bearish": "leans negative", "Neutral": "is mixed"}[research["bias"]]
    conflict = ""
    if research.get("conflicted"):
        conflict = ("\nThe price evidence and the business evidence point in opposite directions; "
                    "make that tension the centre of the second paragraph of the summary.")
    schema = (
        '{\n'
        '  "summary": "Two short paragraphs separated by \\n\\n. First: what the evidence says overall and the two or '
        'three facts that matter most, with their numbers. Second: the main tension or uncertainty in the picture. '
        'Do not mention the historical record in the summary; it may be used in the cases below.",\n'
        '  "key_drivers": ["3 to 5 separate strings, each a short phrase naming one fact that drives the view, with its number"],\n'
        '  "bull_case": ["3 or 4 separate strings, one sentence each: the strongest honest argument for the stock, each tied to a number above"],\n'
        '  "bear_case": ["3 or 4 separate strings, one sentence each: the strongest honest argument against it, each tied to a number above"],\n'
        f'  "risk_register": [{{"category": "one of {RISK_CATEGORIES}", "severity": "Low|Medium|High", '
        '"probability": "Low|Medium|High", "explanation": "one sentence grounded in the evidence"}]\n'
        '}'
    )
    return f"""You are writing an equity research brief for a retail investor about {research.get('name')}.
All analysis below was calculated from market data and the company's reported financial statements.

EVIDENCE
{evidence}

CALCULATED RESULT (final, do not change): the evidence {stance}; overall {research['composite']}/100;
confidence {research['confidence']}%; risk level {research['risk']}.{conflict}

RULES
- Use ONLY the evidence above. Every number you write must appear in the evidence exactly.
- Do not add facts from memory: no products, executives, competitors, events, dates or forecasts that are not above.
- Never tell the reader to buy, sell or hold, and never give a target price. Explain; do not advise.
- Do not predict or imply future returns. The historical record describes the past only; say so if you mention it.
- Plain English. Short sentences. If you use a term such as RSI or free cash flow, say what it means in a few words.
- If a pillar was not assessed, say so rather than guessing.

Return ONLY a JSON object:
{schema}
Give 3 to 5 risk_register entries, only for risks the evidence supports."""


def analyze(technical: dict, fundamental: dict, sentiment: dict, research: dict, request_id: str = "-") -> dict:
    """The final decision. Bias, confidence and risk come from research; the model
    only writes the text. The returned "llm" block (prompt version, model, token
    usage, attempts, outcome, rejection reasons) is logged and sent to the client."""
    view = _rule_view(research, sentiment)
    llm_meta = {"prompt_version": PROMPT_VERSION, "model": None, "outcome": "rule",
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "attempts": [], "rejections": []}

    if os.getenv("GROQ_API_KEY"):
        evidence = _evidence_text(research, sentiment)
        prompt = _prompt(research, evidence)
        # One retry: if an answer fails validation, ask once more with the reason
        # attached. A transport failure is not retried here, because
        # query_groq_with_meta has already tried every model in the chain.
        for attempt in range(2):
            text = prompt
            if attempt:
                text += (f"\n\nYour previous answer was rejected: {llm_meta['rejections'][-1]}. "
                         "Return a corrected JSON object that follows every rule.")
            try:
                result = query_groq_with_meta(text, request_id=request_id)
            except Exception as err:
                llm_meta["rejections"].append(f"no model answered: {str(err)[:160]}")
                break
            for key in llm_meta["usage"]:
                llm_meta["usage"][key] += result["usage"].get(key, 0)
            llm_meta["attempts"].extend(result["attempts"])
            llm_meta["model"] = result["model"]
            try:
                brief = check_brief(result["content"], evidence)
            except ValidationError as err:
                errors = err.errors()
                first = errors[0] if errors else {}
                where = ".".join(str(x) for x in first.get("loc", ())) or "JSON"
                llm_meta["rejections"].append(f"invalid output at {where}: {first.get('msg', 'parse error')}")
                continue
            except BriefRejected as err:
                llm_meta["rejections"].append(str(err))
                continue
            data = brief.model_dump()
            for field in ("summary", "key_drivers", "bull_case", "bear_case", "risk_register"):
                view[field] = data[field]
            llm_meta["outcome"] = "ai" if attempt == 0 else "ai_after_retry"
            break

    logger.info(f"[{request_id}] brief prompt_version={PROMPT_VERSION} outcome={llm_meta['outcome']} "
                f"model={llm_meta['model']} prompt_tokens={llm_meta['usage']['prompt_tokens']} "
                f"completion_tokens={llm_meta['usage']['completion_tokens']} "
                f"total_tokens={llm_meta['usage']['total_tokens']} calls={len(llm_meta['attempts'])} "
                f"rejections={llm_meta['rejections']}")

    return {
        "market_bias": research["bias"],
        "confidence": research["confidence"],
        "risk": research["risk"],
        "conflicted": bool(research.get("conflicted")),
        "key_drivers": view["key_drivers"],
        "watchlist_factors": research["watch"],
        "potential_risks": view["potential_risks"],
        "future_catalysts": view["future_catalysts"],
        "summary": view["summary"],
        "fallback_active": llm_meta["outcome"] == "rule",
        "bull_case": view["bull_case"],
        "bear_case": view["bear_case"],
        "risk_register": view["risk_register"],
        "catalyst_calendar": research["calendar"],
        "llm": llm_meta,
    }
