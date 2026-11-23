"""Interactive dashboard.

    streamlit run app/dashboard.py

Shows real results where they exist; otherwise the synthetic demo, clearly
labelled.
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ccd import config as C  # noqa: E402

st.set_page_config(page_title="Cold Chain in the Dark", layout="wide")
st.title("Cold Chain in the Dark")
st.caption("Did Bangladesh's 2026 power cuts weaken its measles vaccination campaign? "
           "An observational study with open data.")

tab_zone, tab_main, tab_dist = st.tabs(["Who carried the load shedding", "Main results", "District explorer"])

# ------------------------------------------------------------ zone inequality
with tab_zone:
    zdir = C.RESULTS / "zone_inequality"
    if (zdir / "zone_burden.csv").exists():
        g = pd.read_csv(zdir / "zone_burden.csv", index_col=0)
        st.markdown((zdir / "SUMMARY.md").read_text(encoding="utf-8").split("|")[0])
        st.bar_chart(g[["share_of_demand", "share_of_shedding"]] * 100, horizontal=True,
                     y_label="% of national total", stack=False)
        daily = pd.read_csv(zdir / "daily_national.csv", parse_dates=["date"]).set_index("date")
        st.subheader("National evening-peak load shedding (MW)")
        st.line_chart(daily["shed"])
    else:
        st.info("Run `python scripts/05_zone_inequality.py` first.")

# ------------------------------------------------------------ main results
with tab_main:
    real = C.RESULTS / "main"
    demo = C.RESULTS / "synthetic_demo"
    folder = real if (real / "estimates.csv").exists() else demo
    if folder == demo:
        st.error("Showing the SYNTHETIC demo: fake data with a planted effect. "
                 "Run steps 1-4 to see real results.")
    if (folder / "estimates.csv").exists():
        st.markdown((folder / "SUMMARY.md").read_text(encoding="utf-8"))
        est = pd.read_csv(folder / "estimates.csv")
        st.dataframe(est[["model", "rate_ratio", "rr_low", "rr_high", "p", "n"]].round(3),
                     hide_index=True, width="stretch")
        for fig in ["event_study.png", "estimates.png", "proxy_validation.png"]:
            if (folder / "figures" / fig).exists():
                st.image(str(folder / "figures" / fig))
    else:
        st.info("Run `python scripts/04_run_analysis.py --synthetic` for the demo.")

# ------------------------------------------------------------ district explorer
with tab_dist:
    folder = real if (real / "panel.csv").exists() else demo
    if (folder / "panel.csv").exists():
        if folder == demo:
            st.error("SYNTHETIC demo data.")
        P = pd.read_csv(folder / "panel.csv", parse_dates=["week"])
        ex = pd.read_csv(folder / "exposures.csv").set_index("district")
        d = st.selectbox("District", sorted(P["district"].unique()))
        c1, c2 = st.columns([2, 1])
        with c1:
            s = P[P["district"] == d].set_index("week")
            s = s.assign(per_100k_u5=s["suspected"] / s["pop_u5"] * 1e5)
            st.subheader(f"{d}: weekly suspected cases per 100,000 children under 5")
            st.line_chart(s["per_100k_u5"])
        with c2:
            st.subheader("Exposure during the campaign")
            st.metric("Outage index", f"{ex.loc[d, 'outage_campaign']:.3f}")
            st.metric("Deep-outage nights", f"{ex.loc[d, 'deep_outage_campaign']:.0%}")
            rank = ex["outage_campaign"].rank(ascending=False)[d]
            st.caption(f"Rank {int(rank)} of {len(ex)} districts (1 = most outage).")
        st.subheader("All districts, ranked by campaign-window outage")
        st.bar_chart(ex["outage_campaign"].sort_values(ascending=False))
