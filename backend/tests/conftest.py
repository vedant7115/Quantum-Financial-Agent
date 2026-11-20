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
