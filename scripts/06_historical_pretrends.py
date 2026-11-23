"""Step 6 - did high- and low-outage districts follow parallel measles
trends in the years before 2026?

    python scripts/06_historical_pretrends.py

Exposure used, in order of preference:
  1. results/main/exposures.csv            night-light outage in the campaign
                                           window (after steps 3-4)
  2. results/zone_inequality/zone_burden.csv  BPDB zone burden ratio,
                                           Sep-Nov 2026 (available now; coarse:
                                           nine zones, and not the campaign window)

Writes results/historical_pretrends/.
"""

import argparse

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

import _path  # noqa: F401
from ccd import config as C
from ccd import pretrends as T

ap = argparse.ArgumentParser()
ap.add_argument("--historical", help="path to Data.xlsx (default: download pinned copy)")
a = ap.parse_args()

out = C.RESULTS / "historical_pretrends"
out.mkdir(parents=True, exist_ok=True)

path = T.fetch_historical(C.RAW / "historical" / "district_measles_2017_2023.xlsx") \
    if not a.historical else a.historical
hist = T.load_historical(path)

nl = C.RESULTS / "main" / "exposures.csv"
if nl.exists():
    ex = pd.read_csv(nl)[["district", "outage_campaign"]].rename(columns={"outage_campaign": "exposure"})
    source = "night-light outage index, campaign window (20 Apr - 31 May 2026)"
    proxy = False
else:
    ex = T.zone_exposure(C.RESULTS / "zone_inequality" / "zone_burden.csv")
    source = ("BPDB zone load-shedding burden ratio, Sep-Nov 2026 (PROXY: nine zones, "
              "outside the campaign window; rerun after steps 3-4)")
    proxy = True

trend = T.trend_test(hist, ex)
es = T.event_study(hist, ex)
pd.DataFrame([trend]).to_csv(out / "trend_test.csv", index=False)
es.to_csv(out / "event_study.csv", index=False)

# National context: annual totals.
nat = hist.groupby("year")["cases"].sum()

plt.rcParams.update({"figure.dpi": 150, "font.size": 9, "axes.spines.top": False,
                     "axes.spines.right": False})
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.6, 3.4), gridspec_kw={"width_ratios": [1, 1.5]})
ax1.bar(nat.index, nat.values, color="#b8c7d6")
ax1.set_title("Confirmed measles cases, Bangladesh", loc="left")
ax1.set_xticks(nat.index)
ax1.tick_params(axis="x", labelsize=7)
ax2.axhline(1, color="#888", lw=0.8)
ax2.errorbar(es["year"], es["rate_ratio"], yerr=[es["rate_ratio"] - es["rr_low"], es["rr_high"] - es["rate_ratio"]],
             fmt="o", color="#1f4e79", ecolor="#7fa7c9", ms=4)
ax2.set_xticks(es["year"])
ax2.tick_params(axis="x", labelsize=7)
ax2.set_ylabel("rate ratio per +1 SD exposure")
ax2.set_title(f"High- vs low-exposure districts (ref. {es['year'].max()})", loc="left")
fig.text(0.01, 0.01, f"Exposure: {source}", fontsize=6, color="#a00" if proxy else "#555", wrap=True)
fig.tight_layout(rect=(0, 0.07, 1, 1))
fig.savefig(out / "historical_pretrends.png")
plt.close(fig)

if trend["p"] < 0.05:
    verdict = "a differential pre-2026 trend: parallel trends is in doubt"
elif trend["p"] < 0.10:
    verdict = "borderline evidence of a differential pre-2026 trend: treat as a warning, not a pass"
else:
    verdict = "no evidence of a differential pre-2026 trend"
direction = ("higher-exposure districts were trending DOWN relative to the others, so if that trend "
             "continued, the 2026 DiD is biased towards finding FEWER post-campaign cases there, i.e. "
             "against the cold-chain hypothesis; a main estimate above 1 would then be conservative"
             if trend["rate_ratio_per_year"] < 1 else
             "higher-exposure districts were trending UP relative to the others, so if that trend "
             "continued, the 2026 DiD is biased towards finding MORE post-campaign cases there, i.e. "
             "in favour of the cold-chain hypothesis; a main estimate above 1 must be read with caution")
lines = [
    "# Historical parallel-trends check",
    "",
    f"Exposure: {source}.",
    f"Data: annual confirmed measles cases, {trend['districts']} districts with any cases, {trend['years']} "
    f"(source: github.com/{T.HIST_REPO}, commit {T.HIST_COMMIT[:7]}; case-count provenance not documented there).",
    "",
    f"- Differential trend: rate ratio **{trend['rate_ratio_per_year']:.3f} per year** per +1 SD exposure "
    f"(95% CI {trend['rr_low']:.3f}-{trend['rr_high']:.3f}, p = {trend['p']:.2f}) -> {verdict}.",
    f"- Direction: {direction}.",
    "- Event study (exposure x year, reference = last year):",
    "",
    "| year | rate ratio | 95% CI |",
    "|---|---|---|",
]
lines += [f"| {r.year} | {r.rate_ratio:.2f} | {r.rr_low:.2f}-{r.rr_high:.2f} |" for r in es.itertuples()]
lines += ["", "Caveats: annual data, not weekly; 2020-21 reporting was disrupted by COVID-19; "
          "with the zone proxy, exposure varies across only nine zones, so district-clustered "
          "standard errors are optimistic. A null here supports, but does not prove, parallel trends in 2026."]
(out / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
