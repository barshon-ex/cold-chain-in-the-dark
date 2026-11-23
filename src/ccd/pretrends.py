"""Historical parallel-trends check.

The DGHS platform starts on 10 April 2026, about ten days before the
campaign, so the 2026 data alone cannot show whether high- and low-outage
districts were on parallel measles trends. This module uses earlier years:

    cases_dy = exp( a_d + g_y + delta * exposure_d * (year - centre) )

  a_d    district fixed effects
  g_y    year fixed effects (national epidemics, e.g. 2019-20)
  delta  does a district with +1 SD of 2026 outage exposure have a different
         measles *trend* in the years before 2026?

delta near 0 (and flat event-study coefficients) supports parallel trends.
It does not prove them for 2026: it shows that the groups did not diverge
in the past.

Historical data: annual confirmed measles cases by district, 2017-2023, from
github.com/abubokkorshiddik/District-Level-Measles-Outbreak-Bangladesh
(Data.xlsx). The repository has no license and does not document the source
of the case counts, so the file is downloaded at run time and not
redistributed, and results should be checked against WHO / DGHS figures.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

from .names import bpdb_zone, canon_district

HIST_REPO = "abubokkorshiddik/District-Level-Measles-Outbreak-Bangladesh"
HIST_COMMIT = "cf393b809b5ffea67aab20a6973bebd4b6aa7fd7"  # pinned for reproducibility
HIST_URL = f"https://raw.githubusercontent.com/{HIST_REPO}/{HIST_COMMIT}/Data.xlsx"


def fetch_historical(dest: Path) -> Path:
    import requests

    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        resp = requests.get(HIST_URL, timeout=120)
        resp.raise_for_status()
        dest.write_bytes(resp.content)
    return dest


def load_historical(path: Path) -> pd.DataFrame:
    d = pd.read_excel(path, sheet_name="Sheet1")
    d = d.rename(columns={"Year": "year", "District": "district_raw", "Measles": "cases"})
    d["district"] = d["district_raw"].map(canon_district)
    d = d[["district", "year", "cases"]].dropna()
    d["cases"] = d["cases"].astype(int)
    d["year"] = d["year"].astype(int)
    dup = d.duplicated(["district", "year"]).sum()
    if dup:
        raise ValueError(f"{dup} duplicated district-years in historical data")
    return d.sort_values(["district", "year"]).reset_index(drop=True)


def zone_exposure(zone_burden_csv: Path) -> pd.DataFrame:
    """District exposure from BPDB zone burden ratios (coarse fallback).

    Every district gets its zone's (share of shedding / share of demand).
    Only nine distinct values: use when night-light exposure is not available.
    """
    zb = pd.read_csv(zone_burden_csv, index_col=0)["burden_ratio"]
    from .names import DISTRICT_DIVISION

    rows = [{"district": d, "zone": bpdb_zone(d), "exposure": zb[bpdb_zone(d)]} for d in DISTRICT_DIVISION]
    return pd.DataFrame(rows)


def _zscore(s: pd.Series) -> pd.Series:
    sd = s.std(ddof=0)
    return (s - s.mean()) / sd if sd > 0 else s * 0


def _fit(formula, df, cluster_col="district"):
    groups = pd.factorize(df[cluster_col])[0]
    return smf.glm(formula, data=df, family=sm.families.Poisson()).fit(
        cov_type="cluster", cov_kwds={"groups": groups}, maxiter=200)


def _drop_all_zero(df: pd.DataFrame) -> pd.DataFrame:
    """Districts with zero cases in every year carry no information under
    Poisson FE (their fixed effect diverges), so they are dropped."""
    keep = df.groupby("district")["cases"].transform("sum") > 0
    return df[keep].copy()


def trend_test(hist: pd.DataFrame, exposure: pd.DataFrame, exposure_col: str = "exposure") -> dict:
    df = hist.merge(exposure[["district", exposure_col]], on="district", how="inner")
    df = _drop_all_zero(df)
    df["exp_z"] = _zscore(df.groupby("district")[exposure_col].transform("first"))
    centre = df["year"].mean()
    df["exp_x_trend"] = df["exp_z"] * (df["year"] - centre)
    res = _fit("cases ~ exp_x_trend + C(district) + C(year)", df)
    b, se = float(res.params["exp_x_trend"]), float(res.bse["exp_x_trend"])
    return {"model": "Linear differential trend, per +1 SD exposure per year",
            "coef": b, "se": se, "rate_ratio_per_year": float(np.exp(b)),
            "rr_low": float(np.exp(b - 1.96 * se)), "rr_high": float(np.exp(b + 1.96 * se)),
            "p": float(res.pvalues["exp_x_trend"]), "districts": int(df["district"].nunique()),
            "years": f"{df['year'].min()}-{df['year'].max()}", "n": int(res.nobs)}


def event_study(hist: pd.DataFrame, exposure: pd.DataFrame, exposure_col: str = "exposure",
                ref_year: int | None = None) -> pd.DataFrame:
    df = hist.merge(exposure[["district", exposure_col]], on="district", how="inner")
    df = _drop_all_zero(df)
    df["exp_z"] = _zscore(df.groupby("district")[exposure_col].transform("first"))
    ref_year = ref_year or int(df["year"].max())
    terms = []
    for y in sorted(df["year"].unique()):
        if y == ref_year:
            continue
        name = f"exp_y{y}"
        df[name] = (df["year"] == y) * df["exp_z"]
        terms.append((y, name))
    res = _fit("cases ~ " + " + ".join(n for _, n in terms) + " + C(district) + C(year)", df)
    rows = []
    for y, n in terms:
        b, se = float(res.params[n]), float(res.bse[n])
        rows.append({"year": y, "rate_ratio": float(np.exp(b)), "rr_low": float(np.exp(b - 1.96 * se)),
                     "rr_high": float(np.exp(b + 1.96 * se)), "p": float(res.pvalues[n])})
    rows.append({"year": ref_year, "rate_ratio": 1.0, "rr_low": 1.0, "rr_high": 1.0, "p": np.nan})
    return pd.DataFrame(rows).sort_values("year").reset_index(drop=True)
