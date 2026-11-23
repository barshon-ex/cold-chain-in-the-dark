"""Historical pre-trend test on synthetic data with a known answer."""

import numpy as np
import pandas as pd

from ccd import pretrends as T
from ccd.names import DISTRICT_DIVISION


def _fake(trend_per_sd: float, seed: int = 1):
    rng = np.random.default_rng(seed)
    d = sorted(DISTRICT_DIVISION)
    exp = pd.DataFrame({"district": d, "exposure": rng.normal(0, 1, len(d))})
    z = (exp.exposure - exp.exposure.mean()) / exp.exposure.std(ddof=0)
    rows = []
    for i, name in enumerate(d):
        level = np.exp(rng.normal(3, 0.5))
        for y in range(2017, 2024):
            lam = level * np.exp(0.3 * np.sin(y)) * trend_per_sd ** (z[i] * (y - 2020))
            rows.append({"district": name, "year": y, "cases": rng.poisson(lam)})
    return pd.DataFrame(rows), exp


def test_detects_planted_differential_trend():
    hist, exp = _fake(0.85)
    r = T.trend_test(hist, exp)
    assert r["rr_high"] < 1 and abs(r["rate_ratio_per_year"] - 0.85) < 0.05


def test_null_when_trends_parallel():
    hist, exp = _fake(1.0)
    r = T.trend_test(hist, exp)
    assert r["rr_low"] < 1 < r["rr_high"]


def test_event_study_reference_year():
    hist, exp = _fake(1.0)
    es = T.event_study(hist, exp)
    assert es.loc[es.year == 2023, "rate_ratio"].item() == 1.0
