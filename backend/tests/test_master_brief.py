"""LLM output validation and the one-retry rule. Groq is never called: the client is replaced."""

import asyncio
import json

import pytest
from pydantic import ValidationError

import prompts
from agents import master_agent
from conftest import make_prices
from services import research_engine as engine

EVIDENCE = "Operating margin of 33.0%; Price is 39.3 times earnings; Free cash flow yield of 2.7%"

GOOD = {
    "summary": "The evidence leans positive. Operating margin of 33.0% and a price of 39.3 times earnings "
               "frame the picture.\n\nThe tension is valuation against quality.",
    "key_drivers": ["Operating margin of 33.0%", "Price is 39.3 times earnings"],
    "bull_case": ["Margins are high at 33.0%.", "Cash generation supports the business."],
    "bear_case": ["At 39.3 times earnings the price is demanding.", "Free cash flow yield is only 2.7%."],
    "risk_register": [{"category": "Valuation risk", "severity": "High", "probability": "Medium",
                       "explanation": "The shares trade at 39.3 times earnings."}],
}


def test_check_brief_accepts_valid_and_rejects_bad_output():
    assert master_agent.check_brief(json.dumps(GOOD), EVIDENCE).key_drivers[0].startswith("Operating")

    with pytest.raises(ValidationError):  # not JSON at all
        master_agent.check_brief("Sure! Here is the brief:", EVIDENCE)

    # Several points packed into one string are split into items, not rejected.
    packed = dict(GOOD, bull_case=["Margins are high at 33.0%.\nCash generation supports the business."])
    assert len(master_agent.check_brief(json.dumps(packed), EVIDENCE).bull_case) == 2

    bad_level = json.loads(json.dumps(GOOD))
    bad_level["risk_register"][0]["severity"] = "Severe"
    with pytest.raises(ValidationError):
        master_agent.check_brief(json.dumps(bad_level), EVIDENCE)

    advice = dict(GOOD, summary=GOOD["summary"] + " We recommend investors buy the stock now.")
    with pytest.raises(master_agent.BriefRejected):
        master_agent.check_brief(json.dumps(advice), EVIDENCE)

    invented = dict(GOOD, bull_case=["Revenue will reach 412.5 next year.", "Margins rise to 47.8.", "Price hits 905."])
    with pytest.raises(master_agent.BriefRejected):
        master_agent.check_brief(json.dumps(invented), EVIDENCE)


@pytest.fixture
def research(monkeypatch):
    monkeypatch.setattr(engine, "_history", lambda s, p: make_prices(0.0012) if not s.startswith("^") else make_prices(0.0003, seed=3))
    monkeypatch.setattr(engine, "_statements", lambda s: {})
    monkeypatch.setattr(engine, "_calendar", lambda s: {})
    return engine.build("TEST", {"name": "Test Co", "price": 300.0, "currency": "USD"}, articles=[])


def test_retry_once_then_fall_back_to_rules(groq, research):
    sentiment = {"positive_drivers": [], "negative_drivers": []}

    # Invalid twice -> rule-written brief; both calls' tokens are counted.
    groq.answers = ["not json", '{"summary": "x"}']
    out = asyncio.run(master_agent.analyze({}, {}, sentiment, research))
    assert len(groq.prompts) == 2
    assert "previous answer was rejected" in groq.prompts[1]
    assert out["fallback_active"] is True and out["llm"]["outcome"] == "rule"
    assert out["llm"]["tokens"]["total"] == 2 * groq.TOTAL_TOKENS
    assert out["llm"]["prompt_version"] == prompts.active_version()

    # Invalid then valid -> accepted on the retry. Built from the real evidence so the number check passes.
    evidence = master_agent._evidence_text(research, sentiment)
    composite = str(research["composite"])
    valid = dict(GOOD,
                 summary=f"The evidence scores {composite}/100 overall. " + "Price trend leads the picture. " * 3,
                 key_drivers=[f"Overall score {composite}/100", "Price trend is strong"],
                 bull_case=["The price trend is firm.", "Momentum is supportive."],
                 bear_case=["Financials were not assessed.", "News flow was not assessed."],
                 risk_register=[{"category": "Market risk", "severity": "Low", "probability": "Low",
                                 "explanation": "The price trend has been steady."}])
    assert master_agent.check_brief(json.dumps(valid), evidence)
    groq.reset(answers=["{}", json.dumps(valid)])
    out = asyncio.run(master_agent.analyze({}, {}, sentiment, research))
    assert out["llm"]["outcome"] == "ai_after_retry"
    assert out["fallback_active"] is False
    assert out["summary"].startswith("The evidence scores")
