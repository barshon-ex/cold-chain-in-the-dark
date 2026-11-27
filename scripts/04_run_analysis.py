"""Step 4 - build the panel, fit the models, draw the figures.

    python scripts/04_run_analysis.py              # real data (after steps 1-3)
    python scripts/04_run_analysis.py --synthetic  # pipeline demo, fake data

Writes results/main/ (or results/synthetic_demo/):
  estimates.csv, event_study.csv, exposures.csv, panel.csv,
  proxy_validation.csv (if BPDB zones are available), figures/*.png, SUMMARY.md
"""

import argparse
from datetime import datetime

import matplotlib
import matplotlib.ticker

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import _path  # noqa: F401
from ccd import config as C
from ccd import models, panel, synthetic
from ccd.names import bpdb_zone

ap = argparse.ArgumentParser()
ap.add_argument("--synthetic", action="store_true", help="run on fake data with a planted effect")
a = ap.parse_args()

if a.synthetic:
    out = C.RESULTS / "synthetic_demo"
    measles, ntl, pop = synthetic.make(true_rate_ratio=1.25)
    zones = None
    stamp = "SYNTHETIC DATA - pipeline demo, not a finding (planted rate ratio 1.25)"
else:
    out = C.RESULTS / "main"
    measles = pd.read_csv(C.PROCESSED / "dghs_district_daily.csv", parse_dates=["date"])
    ntl = pd.read_csv(C.PROCESSED / "ntl_district_daily.csv", parse_dates=["date"])
    pop = panel.load_population()
    zpath = C.PROCESSED / "bpdb_zone_daily.csv"
    zones = pd.read_csv(zpath) if zpath.exists() else None
    stamp = "Real data. Observational: associations, not proof of cause."
(out / "figures").mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------ panel
ex = panel.district_exposures(ntl, zones)
P = panel.build_panel(measles, ex, pop)
ex.to_csv(out / "exposures.csv", index=False)
P.to_csv(out / "panel.csv", index=False)

# ------------------------------------------------------------------ models
rows = [
    models.did(P, label="Main: campaign-window outage (Poisson FE, clustered SE)"),
    models.did(P, district_trends=True, label="Alternative: + district-specific linear trends"),
    models.did(P, controls=False, label="No susceptible-depletion control"),
    models.did(P, exposure="deep_outage_campaign_z", label="Deep-outage nights (<70% of baseline)"),
    models.did(P, exposure="hot_outage_campaign_z", label="Deep outage on hot days (>35 C)"),
    models.did(P, exposure="outage_precampaign_z", label="PLACEBO: outage before the campaign"),
]
alpha = models.negbin_alpha(P)
import statsmodels.api as sm  # noqa: E402

rows.append(models.did(P, family=sm.families.NegativeBinomial(alpha=alpha),
                       label=f"Negative binomial (alpha={alpha:.2f})"))
rows += models.horse_race(P)
if "zone_shed_campaign_z" in P and P["zone_shed_campaign_z"].notna().any():
    rows.append(models.did(P, exposure="zone_shed_campaign_z",
                           label="BPDB zone load-shed share (9 zones only)"))
if "confirmed" in P:
    rows.append(models.did(P, outcome="confirmed", label="Outcome: lab-confirmed cases"))
est = pd.DataFrame(rows)
est.to_csv(out / "estimates.csv", index=False)

es = models.event_study(P)
es.to_csv(out / "event_study.csv", index=False)

# ------------------------------------------------------------------ proxy validation
val = None
if zones is not None and len(zones):
    z = zones.copy()
    z["date"] = pd.to_datetime(z["date"])
    z["shed_share"] = z["load_shed_mw"] / z["demand_mw"].replace(0, np.nan)
    m = panel.outage_metrics(ntl)
    m["zone"] = m["district"].map(bpdb_zone)
    zn = m.groupby(["zone", "date"], as_index=False)["outage_index"].mean()
    val = zn.merge(z[["zone", "date", "shed_share"]], on=["zone", "date"])
    val.to_csv(out / "proxy_validation.csv", index=False)

# ------------------------------------------------------------------ figures
plt.rcParams.update({"figure.dpi": 150, "font.size": 9, "axes.spines.top": False,
                     "axes.spines.right": False})

fig, ax = plt.subplots(figsize=(7, 3.6))
ax.axhline(1, color="#888", lw=0.8)
ax.axvspan(0, (pd.Timestamp(C.CAMPAIGN_END) - pd.Timestamp(C.CAMPAIGN_START)).days / 7,
           color="#d9e6f2", label="campaign")
ax.errorbar(es["rel_week"], es["rate_ratio"],
            yerr=[es["rate_ratio"] - es["rr_low"], es["rr_high"] - es["rate_ratio"]],
            fmt="o", ms=3.5, color="#1f4e79", ecolor="#7fa7c9", capsize=0)
ax.set_xlabel("weeks since nationwide campaign start (20 April 2026)")
ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
ax.set_ylabel("rate ratio per +1 SD outage")
ax.set_title("Event study: cases in high- vs low-outage districts", loc="left")
ax.legend(frameon=False, loc="upper left")
fig.text(0.01, 0.01, stamp, fontsize=6.5, color="#a00" if a.synthetic else "#555")
fig.tight_layout(rect=(0, 0.04, 1, 1))
fig.savefig(out / "figures" / "event_study.png")
plt.close(fig)

fig, ax = plt.subplots(figsize=(6.5, 3.6))
show = est.iloc[::-1]
y = np.arange(len(show))
ax.axvline(1, color="#888", lw=0.8)
ax.errorbar(show["rate_ratio"], y, xerr=[show["rate_ratio"] - show["rr_low"],
                                         show["rr_high"] - show["rate_ratio"]],
            fmt="o", color="#1f4e79", ecolor="#7fa7c9", ms=4)
ax.set_yticks(y, show["model"], fontsize=7)
ax.set_xlabel("post-campaign rate ratio per +1 SD exposure (95% CI)")
ax.set_title("Main estimate and robustness checks", loc="left")
fig.text(0.01, 0.01, stamp, fontsize=6.5, color="#a00" if a.synthetic else "#555")
fig.tight_layout(rect=(0, 0.04, 1, 1))
fig.savefig(out / "figures" / "estimates.png")
plt.close(fig)

if val is not None and len(val):
    fig, ax = plt.subplots(figsize=(4.2, 3.6))
    ax.scatter(val["shed_share"], val["outage_index"], s=6, alpha=0.4, color="#1f4e79")
    r = val[["shed_share", "outage_index"]].corr(method="spearman").iloc[0, 1]
    ax.set_xlabel("BPDB zone load-shed share (evening peak)")
    ax.set_ylabel("night-light outage index (01:30)")
    ax.set_title(f"Proxy validation, Spearman r = {r:.2f}", loc="left")
    fig.tight_layout()
    fig.savefig(out / "figures" / "proxy_validation.png")
    plt.close(fig)

# ------------------------------------------------------------------ summary
main = est.iloc[0]
plac = est[est["model"].str.startswith("PLACEBO")].iloc[0]
tr = est[est["model"].str.startswith("Alternative: + district")].iloc[0]
hr_c = est[est["model"] == "Horse race: campaign-window term"].iloc[0]
hr_p = est[est["model"] == "Horse race: pre-campaign term"].iloc[0]
lines = [
    f"# Results ({'SYNTHETIC DEMO' if a.synthetic else 'real data'})",
    "",
    f"_Generated {datetime.now():%Y-%m-%d %H:%M}. {stamp}_",
    "",
    f"- Panel: {P['district'].nunique()} districts x {P['week'].nunique()} weeks "
    f"({P['week'].min():%d %b} to {P['week'].max():%d %b %Y}), {int(P['suspected'].sum()):,} suspected cases.",
    f"- Main estimate: rate ratio **{main.rate_ratio:.2f}** (95% CI {main.rr_low:.2f}-{main.rr_high:.2f}, "
    f"p = {main.p:.3f}) per +1 SD of campaign-window outage.",
    f"- Alternative with district-specific linear trends: **{tr.rate_ratio:.2f}** "
    f"({tr.rr_low:.2f}-{tr.rr_high:.2f}, p = {tr.p:.3f}).",
    f"- Placebo (outage before the campaign): {plac.rate_ratio:.2f} ({plac.rr_low:.2f}-{plac.rr_high:.2f}). "
    "Outages before and during the campaign are correlated (both track rurality), so the placebo alone "
    "cannot separate the stories.",
    f"- Horse race (both in one model): campaign-window {hr_c.rate_ratio:.2f} ({hr_c.rr_low:.2f}-{hr_c.rr_high:.2f}), "
    f"pre-campaign {hr_p.rate_ratio:.2f} ({hr_p.rr_low:.2f}-{hr_p.rr_high:.2f}). "
    "The cold-chain reading needs the campaign-window term above 1 and the pre-campaign term near 1.",
    "",
    "See estimates.csv for every model and figures/ for plots. Read docs/pre_analysis_plan.md "
    "before interpreting anything.",
]
(out / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
