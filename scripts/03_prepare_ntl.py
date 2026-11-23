"""Step 3 - combine the Earth Engine exports into one table.

Run gee/export_district_ntl_temperature.js in the Earth Engine code editor,
download every ntl_tmax_district_*.csv from Google Drive into data/raw/gee/,
then:

    python scripts/03_prepare_ntl.py
"""

import pandas as pd

import _path  # noqa: F401
from ccd import config as C
from ccd.panel import load_ntl

files = sorted((C.RAW / "gee").glob("ntl_tmax_district_*.csv"))
if not files:
    raise SystemExit("No GEE exports found in data/raw/gee/ - see the docstring.")

frames = []
for f in files:
    frames.append(load_ntl(f))
ntl = pd.concat(frames).drop_duplicates(["date", "district"]).sort_values(["district", "date"])
out = C.PROCESSED / "ntl_district_daily.csv"
ntl.to_csv(out, index=False)

usable = (ntl["good_frac"] >= 0.3).mean()
print(f"wrote {out}: {len(ntl)} district-nights, {ntl['district'].nunique()} districts, "
      f"{ntl['date'].min():%Y-%m-%d} to {ntl['date'].max():%Y-%m-%d}; "
      f"{usable:.0%} of nights usable (>=30% cloud-free lit pixels)")
