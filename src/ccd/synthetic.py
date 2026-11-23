"""Synthetic data with a known answer, for tests and the pipeline demo.

NOTHING HERE IS REAL DATA. It exists so that (1) the tests can check that the
models recover an effect we planted, and (2) the whole pipeline can be run
end to end before the real downloads are done. Outputs made from it are
written under results/synthetic_demo/ and stamped SYNTHETIC.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C
from .names import DISTRICT_DIVISION


def make(true_rate_ratio: float = 1.25, seed: int = 7):
    """Return (measles_daily, ntl_daily, population) with a planted effect.

    true_rate_ratio: multiplicative change in post-campaign cases per 1 SD of
    campaign-window outage. 1.0 = no effect.
    """
    rng = np.random.default_rng(seed)
    districts = sorted(DISTRICT_DIVISION)
    n = len(districts)
    rural = rng.uniform(0, 1, n)                     # latent rurality
    pop_u5 = rng.integers(80_000, 1_200_000, n)

    # Night lights: rural districts darker during the campaign, plus noise.
    days = pd.date_range("2026-03-01", "2026-09-30", freq="D")
    camp = (days >= pd.Timestamp(C.CAMPAIGN_START)) & (days <= pd.Timestamp(C.CAMPAIGN_END))
    outage_level = 0.10 + 0.25 * rural + rng.normal(0, 0.05, n)
    ntl_rows = []
    for i, d in enumerate(districts):
        base = 1 - outage_level[i] * (0.6 + 0.8 * camp) + rng.normal(0, 0.08, len(days))
        ntl_rows.append(pd.DataFrame({
            "date": days, "district": d, "ntl_ratio": np.clip(base, 0, 1.5),
            "dark_share": np.clip(1 - base, 0, 1), "good_frac": rng.uniform(0.2, 1, len(days)),
            "tmax_c": 31 + 4 * np.sin(np.arange(len(days)) / 30) + rng.normal(0, 1.5, len(days)),
        }))
    ntl = pd.concat(ntl_rows, ignore_index=True)

    # Exposure as the pipeline will measure it (z-scored campaign-window mean).
    camp_mean = 1 - ntl[(ntl.date >= pd.Timestamp(C.CAMPAIGN_START)) &
                        (ntl.date <= pd.Timestamp(C.CAMPAIGN_END)) &
                        (ntl.good_frac >= 0.3)].groupby("district")["ntl_ratio"].mean().clip(0, 1)
    z = ((camp_mean - camp_mean.mean()) / camp_mean.std(ddof=0)).reindex(districts).to_numpy()

    # Cases: national epidemic curve x district level x planted post effect.
    mdays = pd.date_range("2026-04-10", "2026-09-30", freq="D")
    t = np.arange(len(mdays))
    curve = 60 * np.exp(-((t - 40) / 25) ** 2) + 8
    protected = mdays >= pd.Timestamp(C.CAMPAIGN_END) + pd.Timedelta(weeks=C.PROTECTION_LAG_WEEKS)
    rows = []
    for i, d in enumerate(districts):
        level = np.exp(rng.normal(0, 0.4) + 0.5 * rural[i])
        lam = curve * level * pop_u5[i] / 500_000
        lam = lam * np.where(protected, true_rate_ratio ** z[i], 1.0)
        # over-dispersed counts (gamma-Poisson)
        lam = lam * rng.gamma(5, 1 / 5, len(mdays))
        rows.append(pd.DataFrame({"date": mdays, "district": d, "division": DISTRICT_DIVISION[d],
                                  "suspected": rng.poisson(lam)}))
    measles = pd.concat(rows, ignore_index=True)
    pop = pd.DataFrame({"district": districts, "pop_total": pop_u5 * 9, "pop_u5": pop_u5})
    return measles, ntl, pop
