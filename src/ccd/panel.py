"""Build the district x week analysis panel.

Inputs (all tidy CSVs written by the scripts in scripts/):
  measles   district-day counts from DGHS          data/processed/dghs_district_daily.csv
  ntl       district-night light ratio + Tmax      data/processed/ntl_district_daily.csv
  zones     BPDB zone evening-peak load shedding   data/processed/bpdb_zone_daily.csv (optional)
  pop       BBS 2022 district population            data/external/population_adm2_2022.csv
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from . import config as C
from .names import DISTRICT_DIVISION, bpdb_zone, canon_district


def week_start(s: pd.Series) -> pd.Series:
    s = pd.to_datetime(s)
    return (s - pd.to_timedelta(s.dt.weekday, unit="D")).dt.normalize()


# ---------------------------------------------------------------- loaders
def load_population(path=C.EXTERNAL / "population_adm2_2022.csv") -> pd.DataFrame:
    pop = pd.read_csv(path)
    pop["district"] = pop["adm2_name"].map(canon_district)
    out = pop[["district", "t_tl", "t_00_04"]].rename(columns={"t_tl": "pop_total", "t_00_04": "pop_u5"})
    missing = set(DISTRICT_DIVISION) - set(out["district"])
    if missing:
        raise ValueError(f"population file lacks districts: {sorted(missing)}")
    return out


def load_ntl(path) -> pd.DataFrame:
    """GEE export(s) -> clean district-night table."""
    df = pd.read_csv(path)
    df["district"] = df["district"].map(canon_district)
    df["date"] = pd.to_datetime(df["date"])
    df.loc[df["tmax_c"] < -100, "tmax_c"] = np.nan  # -999 = no ERA5 that day
    return df


def outage_metrics(ntl: pd.DataFrame, min_good_frac: float = 0.3) -> pd.DataFrame:
    """Night-level outage indicators. Cloudy nights (few usable pixels) dropped."""
    d = ntl[ntl["good_frac"] >= min_good_frac].copy()
    d["outage_index"] = (1 - d["ntl_ratio"].clip(0, 1))
    d["deep_outage"] = (d["ntl_ratio"] < C.DEEP_OUTAGE_RATIO).astype(float)
    d["hot_outage"] = ((d["ntl_ratio"] < C.DEEP_OUTAGE_RATIO) & (d["tmax_c"] > C.HOT_DAY_C)).astype(float)
    return d


def window_mean(df: pd.DataFrame, col: str, start: date, end: date, by: str = "district") -> pd.Series:
    m = (df["date"] >= pd.Timestamp(start)) & (df["date"] <= pd.Timestamp(end))
    return df.loc[m].groupby(by)[col].mean()


# ---------------------------------------------------------------- exposures
def district_exposures(ntl: pd.DataFrame, zones: pd.DataFrame | None = None) -> pd.DataFrame:
    """One row per district. All exposures are z-scored across districts."""
    m = outage_metrics(ntl)
    pre_start, pre_end = date(2026, 3, 1), C.CAMPAIGN_START
    ex = pd.DataFrame({
        "outage_campaign": window_mean(m, "outage_index", C.CAMPAIGN_START, C.CAMPAIGN_END),
        "deep_outage_campaign": window_mean(m, "deep_outage", C.CAMPAIGN_START, C.CAMPAIGN_END),
        "hot_outage_campaign": window_mean(m, "hot_outage", C.CAMPAIGN_START, C.CAMPAIGN_END),
        # Same measure before any campaign vaccine was in the fridges: if this
        # predicts the outcome as well as the campaign-window measure, the
        # association is about rural disadvantage, not the cold chain.
        "outage_precampaign": window_mean(m, "outage_index", pre_start, pre_end),
        "nights_used_campaign": m[(m["date"] >= pd.Timestamp(C.CAMPAIGN_START)) &
                                  (m["date"] <= pd.Timestamp(C.CAMPAIGN_END))]
                                .groupby("district").size(),
    })
    if zones is not None and len(zones):
        z = zones.copy()
        z["date"] = pd.to_datetime(z["date"])
        z["shed_share"] = z["load_shed_mw"] / z["demand_mw"].replace(0, np.nan)
        zmean = window_mean(z, "shed_share", C.CAMPAIGN_START, C.CAMPAIGN_END, by="zone")
        ex["zone_shed_campaign"] = [zmean.get(bpdb_zone(d), np.nan) for d in ex.index]
    ex.index.name = "district"
    ex = ex.reset_index()
    for col in [c for c in ex.columns if c.endswith(("_campaign", "_precampaign")) and c != "nights_used_campaign"]:
        sd = ex[col].std(ddof=0)
        ex[col + "_z"] = (ex[col] - ex[col].mean()) / sd if sd and sd > 0 else 0.0
    return ex


# ---------------------------------------------------------------- panel
def weekly_cases(measles: pd.DataFrame) -> pd.DataFrame:
    m = measles.copy()
    m["district"] = m["district"].map(canon_district)
    m["week"] = week_start(m["date"])
    cols = [c for c in ["suspected", "confirmed", "suspected_deaths", "admitted"] if c in m]
    return m.groupby(["district", "week"], as_index=False)[cols].sum()


def build_panel(measles: pd.DataFrame, exposures: pd.DataFrame, pop: pd.DataFrame) -> pd.DataFrame:
    wk = weekly_cases(measles)
    wk = wk[(wk["week"] >= pd.Timestamp(C.STUDY_START)) & (wk["week"] <= pd.Timestamp(C.STUDY_END))]
    p = wk.merge(pop, on="district", how="left").merge(exposures, on="district", how="left")
    p["division"] = p["district"].map(DISTRICT_DIVISION)

    camp0 = pd.Timestamp(C.CAMPAIGN_START)
    protected_from = pd.Timestamp(C.CAMPAIGN_END) + pd.Timedelta(weeks=C.PROTECTION_LAG_WEEKS)
    p["post"] = (p["week"] >= protected_from).astype(int)
    p["rel_week"] = ((p["week"] - week_start(pd.Series([camp0]))[0]).dt.days // 7).astype(int)

    # Attack rate before the campaign (susceptible depletion control).
    pre = p[p["week"] < camp0].groupby("district")["suspected"].sum()
    p["pre_attack_per_1k_u5"] = p["district"].map(pre).fillna(0) / p["pop_u5"] * 1000
    sd = p.groupby("district")["pre_attack_per_1k_u5"].first().std(ddof=0)
    mu = p.groupby("district")["pre_attack_per_1k_u5"].first().mean()
    p["pre_attack_z"] = (p["pre_attack_per_1k_u5"] - mu) / sd if sd else 0.0
    p["log_pop_u5"] = np.log(p["pop_u5"])
    return p.sort_values(["district", "week"]).reset_index(drop=True)
