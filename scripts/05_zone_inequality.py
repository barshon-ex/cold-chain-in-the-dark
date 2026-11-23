"""Who carried the load shedding? Zone-level inequality, BPDB evening peak.

Runs on real data now: data/external/bpdb_zone_evening_peak_2026-09-04_2026-11-21.csv
(parsed from BPDB/NLDC daily reports by github.com/sunrisesineast/bangladesh-grid,
MIT). After step 2 it also runs on your own March-September download:

    python scripts/05_zone_inequality.py
    python scripts/05_zone_inequality.py --input data/processed/bpdb_zone_daily.csv

Writes results/zone_inequality/.
"""

import argparse

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import _path  # noqa: F401
from ccd import config as C

ap = argparse.ArgumentParser()
ap.add_argument("--input", default=str(C.EXTERNAL / "bpdb_zone_evening_peak_2026-09-04_2026-11-21.csv"))
a = ap.parse_args()

z = pd.read_csv(a.input, parse_dates=["date"])
out = C.RESULTS / "zone_inequality"
out.mkdir(parents=True, exist_ok=True)

span = f"{z['date'].min():%d %b} - {z['date'].max():%d %b %Y}"
days = z["date"].nunique()
shed_days = z.groupby("date")["load_shed_mw"].sum().gt(0)

# Per zone: share of national demand vs share of national load shedding.
g = z.groupby("zone").agg(demand_mw=("demand_mw", "sum"), shed_mw=("load_shed_mw", "sum"),
                          days_with_shed=("load_shed_mw", lambda s: int((s > 0).sum())))
g["share_of_demand"] = g["demand_mw"] / g["demand_mw"].sum()
g["share_of_shedding"] = g["shed_mw"] / g["shed_mw"].sum()
g["burden_ratio"] = g["share_of_shedding"] / g["share_of_demand"]  # 1 = fair share
g["mean_shed_pct_of_own_demand"] = g["shed_mw"] / g["demand_mw"] * 100
g = g.sort_values("burden_ratio", ascending=False)
g.round(4).to_csv(out / "zone_burden.csv")

# Concentration: Gini of shedding relative to demand (0 = proportional).
def concentration_gini(share_shed, share_dem):
    order = np.argsort(share_shed / share_dem)
    x = np.concatenate([[0], np.cumsum(share_dem.to_numpy()[order])])
    y = np.concatenate([[0], np.cumsum(share_shed.to_numpy()[order])])
    return 1 - np.sum((x[1:] - x[:-1]) * (y[1:] + y[:-1]))

gini = concentration_gini(g["share_of_shedding"], g["share_of_demand"])

# Daily national picture.
daily = z.groupby("date").agg(shed=("load_shed_mw", "sum"), demand=("demand_mw", "sum"))
dhaka = z[z["zone"] == "Dhaka"].set_index("date")["load_shed_mw"]
daily["dhaka_share_of_shed"] = (dhaka / daily["shed"]).where(daily["shed"] > 0)
daily.to_csv(out / "daily_national.csv")

# ------------------------------------------------------------------ figures
plt.rcParams.update({"figure.dpi": 150, "font.size": 9, "axes.spines.top": False,
                     "axes.spines.right": False})
fig, ax = plt.subplots(figsize=(6.4, 3.8))
y = np.arange(len(g))
ax.barh(y + 0.2, g["share_of_demand"] * 100, height=0.4, color="#b8c7d6", label="share of demand")
ax.barh(y - 0.2, g["share_of_shedding"] * 100, height=0.4, color="#c0392b", label="share of load shedding")
ax.set_yticks(y, g.index)
ax.invert_yaxis()
ax.set_xlabel("% of national total, evening peak")
ax.set_title(f"Who carried the load shedding? BPDB zones, {span}", loc="left")
ax.legend(frameon=False, loc="upper right")
fig.text(0.01, 0.01, "Source: BPDB/NLDC daily reports via github.com/sunrisesineast/bangladesh-grid.\n"
         "Zones approximate divisions; Cumilla zone is carved out of Chattogram division.",
         fontsize=6, color="#555")
fig.tight_layout(rect=(0, 0.07, 1, 1))
fig.savefig(out / "zone_burden.png")
plt.close(fig)

fig, ax = plt.subplots(figsize=(6.4, 3.2))
piv = z.pivot_table(index="date", columns="zone", values="load_shed_mw", aggfunc="sum").fillna(0)
piv = piv[g.index[::-1]]
ax.stackplot(piv.index, piv.T.to_numpy(), labels=piv.columns,
             colors=plt.cm.tab10(np.linspace(0, 1, len(piv.columns))))
ax.set_ylabel("load shed at evening peak, MW")
ax.set_title("Daily evening-peak load shedding by zone", loc="left")
ax.legend(frameon=False, fontsize=6.5, ncol=3, loc="upper right")
fig.tight_layout()
fig.savefig(out / "zone_daily_stack.png")
plt.close(fig)

# ------------------------------------------------------------------ summary
top = g.iloc[0]
dh = g.loc["Dhaka"]
lines = [
    f"# Who carried the load shedding? ({span})",
    "",
    f"Real data: {days} daily BPDB/NLDC reports, nine zones, evening peak. "
    f"National load shedding occurred on {int(shed_days.sum())} of {days} days.",
    "",
    f"- Dhaka zone: {dh.share_of_demand:.0%} of demand, {dh.share_of_shedding:.0%} of load shedding "
    f"(burden ratio {dh.burden_ratio:.2f}; 1.00 = proportional).",
    f"- Heaviest relative burden: {g.index[0]} - {top.share_of_demand:.0%} of demand but "
    f"{top.share_of_shedding:.0%} of shedding (ratio {top.burden_ratio:.2f}).",
    f"- Concentration index (0 = shedding proportional to demand, 1 = all on one zone): {gini:.2f}.",
    "",
    "| zone | share of demand | share of shedding | burden ratio | days with shedding |",
    "|---|---|---|---|---|",
]
for name, r in g.iterrows():
    lines.append(f"| {name} | {r.share_of_demand:.1%} | {r.share_of_shedding:.1%} | "
                 f"{r.burden_ratio:.2f} | {int(r.days_with_shed)}/{days} |")
lines += ["", "Limitations: one value per zone per day (evening peak only); zones are not districts; "
          "a zone's internal split between towns and villages is not visible here - that is what the "
          "night-light proxy in step 3 is for."]
(out / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
