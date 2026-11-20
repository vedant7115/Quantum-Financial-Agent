# master_agent.py
# Turns the calculated evidence into the written research view.
#
# The stance, confidence and risk level are calculated in research_engine.py and
# are final. The language model's only job is to explain them: it receives the
# findings with their numbers and may not introduce figures, dates or events of
# its own. Its answer must match the Brief schema below and pass two guardrails
# (no advice wording, no numbers missing from the evidence). A failed answer is
# retried once with the reason attached; if that also fails, no model answers,
# or the overall LLM deadline passes, a rule-written version of the same
# evidence is used instead.
#
# The prompt text lives in prompts/ (versioned); PROMPT_VERSION selects it.

import asyncio
import logging
import os
import re
from typing import List, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError, field_validator
from typing_extensions import Annotated

import prompts
from core.context import prompt_version_var, span
from services import llm_service, usage_service

logger = logging.getLogger("quantum_agent.master_agent")

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
        parts.append("Mixed signals: " + research["conflict_note"])
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


def build_prompt(research: dict, evidence: str, version: str) -> str:
    stance = {"Bullish": "leans positive", "Bearish": "leans negative", "Neutral": "is mixed"}[research["bias"]]
    return prompts.render(
        version, conflicted=bool(research.get("conflicted")),
        name=research.get("name"), evidence=evidence, stance=stance, composite=research["composite"],
        confidence=research["confidence"], risk=research["risk"], categories=str(RISK_CATEGORIES))


def _mixed_signals(summary: str, research: dict) -> str:
    """A conflicted report always says "Mixed signals", whatever the model wrote."""
    if research.get("conflicted") and "mixed signals" not in summary.lower():
        return f"Mixed signals: {research.get('conflict_note', '')}\n\n{summary}".strip()
    return summary


def _calls(records) -> list:
    return [{"model": r.model, "fallback_step": r.step, "attempt": r.attempt, "status": r.status,
             "latency_ms": r.latency_ms, "total_tokens": r.total_tokens, "error": r.error[:160]}
            for r in records]


def _llm_block(version: str) -> dict:
    return {"model": None, "prompt_version": version, "outcome": "rule",
            "tokens": {"prompt": 0, "completion": 0, "total": 0}, "latency_ms": 0.0,
            "fallback_used": False, "fallback_step": None, "deadline_exceeded": False,
            "attempts": [], "rejections": []}


async def analyze(technical: dict, fundamental: dict, sentiment: dict, research: dict,
                  deadline_at: float = None) -> dict:
    """The final decision. Bias, confidence and risk come from research; the model
    only writes the text. The returned "llm" block (model, prompt version, tokens,
    latency, fallback, attempts, outcome) goes into the logs, the trace and the response."""
    loop = asyncio.get_running_loop()
    if deadline_at is None:
        deadline_at = loop.time() + float(os.getenv("LLM_DEADLINE_SECONDS", "30"))
    current = prompt_version_var.get()
    version = current if current in prompts.PROMPT_VERSIONS else prompts.active_version()
    view = _rule_view(research, sentiment)
    llm = _llm_block(version)

    if os.getenv("GROQ_API_KEY"):
        evidence = _evidence_text(research, sentiment)
        prompt = build_prompt(research, evidence, version)
        # One retry: if an answer fails validation, ask once more with the reason
        # attached. A transport failure is not retried here, because generate()
        # has already worked through the whole model chain.
        for attempt in range(2):
            text = prompt
            if attempt:
                text += (f"\n\nYour previous answer was rejected: {llm['rejections'][-1]}. "
                         "Return a corrected JSON object that follows every rule.")
            brief = None
            with span(f"llm.generate#{attempt + 1}") as sp:
                try:
                    result = await llm_service.generate(text, deadline_at=deadline_at)
                except llm_service.AllModelsFailed as err:
                    llm["attempts"].extend(_calls(err.calls))
                    llm["deadline_exceeded"] = err.deadline_exceeded
                    llm["rejections"].append(f"no model answered: {err}")
                    sp.update(status="error", calls=len(err.calls))
                    break
                except Exception as err:
                    llm["rejections"].append(f"LLM call failed: {str(err)[:160]}")
                    sp.update(status="error")
                    break
                llm["attempts"].extend(_calls(result.calls))
                for key, src in (("prompt", "prompt_tokens"), ("completion", "completion_tokens"),
                                 ("total", "total_tokens")):
                    llm["tokens"][key] += result.usage.get(src, 0)
                llm["latency_ms"] = round(llm["latency_ms"] + result.latency_ms, 1)
                llm["model"], llm["fallback_step"] = result.model, result.fallback_step
                llm["fallback_used"] = llm["fallback_used"] or result.fallback_used
                sp.update(model=result.model, fallback_step=result.fallback_step,
                          total_tokens=result.usage.get("total_tokens"), latency_ms=result.latency_ms)
                try:
                    brief = check_brief(result.content, evidence)
                except ValidationError as err:
                    errors = err.errors()
                    first = errors[0] if errors else {}
                    where = ".".join(str(x) for x in first.get("loc", ())) or "JSON"
                    llm["rejections"].append(f"invalid output at {where}: {first.get('msg', 'parse error')}")
                    sp.update(status="rejected")
                except BriefRejected as err:
                    llm["rejections"].append(str(err))
                    sp.update(status="rejected")
            if brief is None:
                continue
            data = brief.model_dump()
            for field in ("summary", "key_drivers", "bull_case", "bear_case", "risk_register"):
                view[field] = data[field]
            llm["outcome"] = "ai" if attempt == 0 else "ai_after_retry"
            break

    view["summary"] = _mixed_signals(view["summary"], research)
    usage_service.record_brief(llm["outcome"], llm["fallback_used"], llm["deadline_exceeded"])
    logger.info("brief", extra={"event": {
        "type": "brief", "outcome": llm["outcome"], "model": llm["model"], "fallback_step": llm["fallback_step"],
        "prompt_tokens": llm["tokens"]["prompt"], "completion_tokens": llm["tokens"]["completion"],
        "total_tokens": llm["tokens"]["total"], "latency_ms": llm["latency_ms"],
        "calls": len(llm["attempts"]), "rejections": llm["rejections"]}})

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
        "fallback_active": llm["outcome"] == "rule",
        "bull_case": view["bull_case"],
        "bear_case": view["bear_case"],
        "risk_register": view["risk_register"],
        "catalyst_calendar": research["calendar"],
        "llm": llm,
    }
