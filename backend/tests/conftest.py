import json
import os
import sys

import numpy as np
import pandas as pd
import pytest

# Tests import the backend modules the same way main.py does.
BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)


def make_prices(daily_drift: float, days: int = 1300, start: float = 100.0, seed: int = 7) -> pd.Series:
    """A synthetic daily close series: steady drift plus small random noise."""
    rng = np.random.default_rng(seed)
    steps = daily_drift + rng.normal(0, 0.008, days)
    index = pd.bdate_range(end="2026-11-13", periods=days)
    return pd.Series(start * np.exp(np.cumsum(steps)), index=index)


@pytest.fixture
def uptrend():
    return make_prices(0.0012)


@pytest.fixture
def downtrend():
    return make_prices(-0.0012)


# ── Mocked Groq ──────────────────────────────────────────────────────────────

import httpx  # noqa: E402

from services import llm_service, usage_service  # noqa: E402


class FakeGroq:
    """Answers Groq chat requests from a script. `answers` are message contents
    (returned with HTTP 200); `responses` overrides with full (status, headers, body)
    tuples per call, consumed in order before `answers`."""

    TOTAL_TOKENS = 150

    def __init__(self):
        self.reset()

    def reset(self, answers=None, responses=None, by_model=None):
        self.answers = list(answers or [])
        self.responses = list(responses or [])
        self.by_model = dict(by_model or {})   # model -> list of (status, headers, body)
        self.prompts, self.models = [], []

    def handler(self, request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        model = payload["model"]
        self.models.append(model)
        self.prompts.append(payload["messages"][0]["content"])
        if self.by_model.get(model):
            status, headers, body = self.by_model[model].pop(0)
            return httpx.Response(status, headers=headers, json=body)
        if self.responses:
            status, headers, body = self.responses.pop(0)
            return httpx.Response(status, headers=headers, json=body)
        content = self.answers.pop(0) if self.answers else "{}"
        return httpx.Response(200, headers={"x-ratelimit-remaining-tokens": "7000",
                                            "x-ratelimit-reset-tokens": "7.5s"},
                              json=ok_body(content, self.TOTAL_TOKENS))


def ok_body(content: str, total: int = 150) -> dict:
    return {"choices": [{"message": {"content": content}}],
            "usage": {"prompt_tokens": total - 50, "completion_tokens": 50, "total_tokens": total}}


@pytest.fixture
def groq(monkeypatch):
    fake = FakeGroq()
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setattr(llm_service, "_transport", httpx.MockTransport(fake.handler))
    sleeps = []

    async def no_sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr(llm_service, "_sleep", no_sleep)
    fake.sleeps = sleeps
    llm_service.rate_limits.reset()
    usage_service.reset()
    yield fake
    llm_service.rate_limits.reset()
