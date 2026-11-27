"""Statistical models.

Main model (difference-in-differences on counts):

    E[cases_dw] = exp( a_d + g_w + b * post_w * exposure_d
                       + c * post_w * pre_attack_d + log(pop_u5_d) )

  a_d     district fixed effects (rurality, health access, reporting habits)
  g_w     week fixed effects (national epidemic curve, campaign timing)
  b       does a district with 1 SD more outage during the campaign see
          relatively more cases once vaccine protection should have started?
          exp(b) is a rate ratio.
  pre_attack  susceptible depletion: districts hit hard early have fewer
          susceptible children left later.

Estimated by Poisson quasi-maximum likelihood with standard errors clustered
by district (consistent under over-dispersion). A negative-binomial fit is a
sensitivity check. With 64 clusters, wild-cluster bootstrap is a further
check worth adding before publication.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf


def _fit(formula: str, df: pd.DataFrame, family=None):
    family = family or sm.families.Poisson()
    model = smf.glm(formula, data=df, family=family, offset=df["log_pop_u5"])
    groups = pd.factorize(df["district"])[0]
    return model.fit(cov_type="cluster", cov_kwds={"groups": groups}, maxiter=200)


def _row(res, term: str, label: str) -> dict:
    b, se = res.params[term], res.bse[term]
    b, se = float(b), float(se)
    return {"model": label, "term": term, "coef": b, "se": se,
            "rate_ratio": float(np.exp(b)), "rr_low": float(np.exp(b - 1.96 * se)),
            "rr_high": float(np.exp(b + 1.96 * se)), "p": float(res.pvalues[term]), "n": int(res.nobs)}


def did(panel: pd.DataFrame, exposure: str = "outage_campaign_z", outcome: str = "suspected",
        controls: bool = True, family=None, label: str | None = None,
        district_trends: bool = False) -> dict:
    """DiD rate ratio. district_trends=True adds a separate linear time trend
    for every district (suggested by Prof. E. Rettore as an alternative to the
    conservative main estimate, given the borderline 2017-2023 pre-trend)."""
    df = panel.dropna(subset=[exposure, outcome, "log_pop_u5"]).copy()
    df["post_x_exp"] = df["post"] * df[exposure]
    rhs = "post_x_exp + C(district) + C(week)"
    if district_trends:
        df["t"] = (df["week"] - df["week"].min()).dt.days / 7.0
        df["t"] = df["t"] - df["t"].mean()
        # One trend per district except the first: the week fixed effects
        # already absorb the common national trend.
        for i, d in enumerate(sorted(df["district"].unique())[1:]):
            df[f"trend_{i}"] = (df["district"] == d) * df["t"]
            rhs += f" + trend_{i}"
    if controls:
        df["post_x_pre"] = df["post"] * df["pre_attack_z"]
        rhs += " + post_x_pre"
    res = _fit(f"{outcome} ~ {rhs}", df, family)
    return _row(res, "post_x_exp", label or f"DiD {outcome} ~ {exposure}")


def horse_race(panel: pd.DataFrame, outcome: str = "suspected") -> list[dict]:
    """Campaign-window and pre-campaign outage in one model.

    The cold-chain story predicts that only the campaign-window term matters.
    """
    df = panel.dropna(subset=["outage_campaign_z", "outage_precampaign_z", outcome]).copy()
    df["post_x_camp"] = df["post"] * df["outage_campaign_z"]
    df["post_x_precamp"] = df["post"] * df["outage_precampaign_z"]
    df["post_x_pre"] = df["post"] * df["pre_attack_z"]
    res = _fit(f"{outcome} ~ post_x_camp + post_x_precamp + post_x_pre + C(district) + C(week)", df)
    return [_row(res, "post_x_camp", "Horse race: campaign-window term"),
            _row(res, "post_x_precamp", "Horse race: pre-campaign term")]


def event_study(panel: pd.DataFrame, exposure: str = "outage_campaign_z", outcome: str = "suspected",
                ref_week: int = -1, min_week: int = -1, max_week: int = 18) -> pd.DataFrame:
    """Exposure x relative-week coefficients (reference: week before the campaign).

    Flat, near-zero coefficients before the campaign support parallel trends.
    """
    df = panel.dropna(subset=[exposure, outcome]).copy()
    df["rw"] = df["rel_week"].clip(min_week, max_week)
    terms = []
    for k in sorted(df["rw"].unique()):
        if k == ref_week:
            continue
        name = f"ex_w{k}".replace("-", "m")
        df[name] = (df["rw"] == k) * df[exposure]
        terms.append((k, name))
    df["post_x_pre"] = df["post"] * df["pre_attack_z"]
    rhs = " + ".join(n for _, n in terms) + " + post_x_pre + C(district) + C(week)"
    res = _fit(f"{outcome} ~ {rhs}", df)
    out = pd.DataFrame([{**_row(res, n, "event study"), "rel_week": k} for k, n in terms])
    ref = {"model": "event study", "term": "reference", "coef": 0.0, "se": 0.0, "rate_ratio": 1.0,
           "rr_low": 1.0, "rr_high": 1.0, "p": np.nan, "n": int(res.nobs), "rel_week": ref_week}
    return pd.concat([out, pd.DataFrame([ref])]).sort_values("rel_week").reset_index(drop=True)


def negbin_alpha(panel: pd.DataFrame, outcome: str = "suspected") -> float:
    """Rough over-dispersion estimate (NB2 alpha) from the FE Poisson residuals."""
    df = panel.dropna(subset=[outcome]).copy()
    res = smf.glm(f"{outcome} ~ C(district) + C(week)", data=df, family=sm.families.Poisson(),
                  offset=df["log_pop_u5"]).fit()
    mu = res.fittedvalues
    y = df[outcome]
    aux = ((y - mu) ** 2 - y) / mu
    return float(max(1e-6, np.sum(aux * mu) / np.sum(mu ** 2)))
