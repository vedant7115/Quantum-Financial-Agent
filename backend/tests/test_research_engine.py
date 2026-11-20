"""Engine tests. All offline: market data fetchers are replaced with synthetic series."""

import numpy as np
import pandas as pd
import pytest

from services import research_engine as engine
from conftest import make_prices


def test_pillar_score_maps_points_to_0_100():
    p = engine.Pillar("trend", "Trend")
    assert p.score is None and p.verdict() == "Not assessed"

    p.add(2, 2, "up", "")
    p.add(-1, 2, "down", "")
    # 50 + 50 * (1 / 4) = 62.5 -> 62 (banker's rounding) and "Good"
    assert p.score == 62
    assert p.verdict() == "Good"
    assert [f["tone"] for f in p.findings] == ["positive", "negative"]

    q = engine.Pillar("x", "X")
    q.add(-5, 2, "far below", "")
    assert q.score == 0  # clamped


def test_weighted_renormalises_over_missing_parts():
    # A missing part is dropped and the remaining weights are rescaled.
    assert engine._weighted([(80, 0.40), (None, 0.45), (60, 0.15)]) == pytest.approx((80 * 0.40 + 60 * 0.15) / 0.55)
    assert engine._weighted([(None, 1.0), (None, 2.0)]) is None


def test_price_pillars_separate_up_and_down_trends(uptrend, downtrend):
    _, up_trend, _, _, _ = engine.analyse_price(uptrend, None, "S&P 500", "$")
    _, dn_trend, _, _, _ = engine.analyse_price(downtrend, None, "S&P 500", "$")
    assert up_trend.score >= 75
    assert dn_trend.score <= 25

    # A sharp sell-off over the last 60 days pulls momentum below neutral.
    rng = np.random.default_rng(1)
    falls = np.exp(np.cumsum(-0.006 + rng.normal(0, 0.004, 60)))
    selloff = pd.concat([uptrend.iloc[:-60], pd.Series(uptrend.iloc[-61] * falls, index=uptrend.index[-60:])])
    facts, _, momentum, _, _ = engine.analyse_price(selloff, None, "S&P 500", "$")
    assert facts["return_1m"] < 0
    assert momentum.score < 50


def test_base_rates_need_enough_history_and_report_sample_size(uptrend):
    assert engine.base_rates(uptrend.tail(300)) is None  # below 200 + 63 + 60 days

    rates = engine.base_rates(uptrend)
    assert rates is not None
    assert rates["regime"] == "uptrend"
    assert rates["days"] >= 40 and rates["episodes"] >= 1
    assert rates["lower_quartile"] <= rates["median_return"] <= rates["upper_quartile"]


def _offline_build(monkeypatch, close, statements=None):
    """Runs research_engine.build with every network fetch replaced."""
    monkeypatch.setattr(engine, "_history",
                        lambda symbol, period: close if not symbol.startswith("^") else make_prices(0.0003, seed=3))
    monkeypatch.setattr(engine, "_statements", lambda symbol: statements or {})
    monkeypatch.setattr(engine, "_calendar", lambda symbol: {})
    stock = {"name": "Test Co", "price": float(close.iloc[-1]), "currency": "USD",
             "market_cap_raw": 1e11, "sector": "Technology"}
    return engine.build("TEST", stock, articles=[])


def test_build_without_financials_reweights_and_flags_coverage(monkeypatch, uptrend):
    report = _offline_build(monkeypatch, uptrend)
    assert report["coverage"]["financials"] is False
    assert report["fundamental_score"] is None
    # With no financials and no news, the composite is the technical score alone.
    assert report["composite"] == round(report["technical_score"])
    assert report["conflicted"] is False
    assert 0 <= report["confidence"] <= 92


def test_conflict_rule_and_confidence_cap(monkeypatch, uptrend):
    assert engine.assess_conflict(70, 30)[0] is True
    assert engine.assess_conflict(30, 70)[0] is True
    assert engine.assess_conflict(70, 55)[0] is False
    assert engine.assess_conflict(50, 30)[0] is False   # 50 is on neither side
    assert engine.assess_conflict(70, None)[0] is False

    # Strong price trend with deliberately weak fundamentals -> conflicted, capped.
    def weak_fundamentals(*args, **kwargs):
        pillars = [engine.Pillar(k, k) for k in ("quality", "growth", "valuation", "balance")]
        for p in pillars:
            p.add(-2, 2, f"weak {p.key}", "")
        facts = {"period_label": "year to Dec 2025", "metrics": [], "pe": None}
        return (facts, *pillars)

    monkeypatch.setattr(engine, "analyse_fundamentals", weak_fundamentals)
    report = _offline_build(monkeypatch, uptrend)
    assert report["technical_score"] > 50 > report["fundamental_score"]
    assert report["conflicted"] is True
    assert report["confidence"] <= engine.CONFLICT_CONFIDENCE_CAP
    assert "capped" in report["conflict_note"]
