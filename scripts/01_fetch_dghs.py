"""Step 1 - district-level daily measles counts from the DGHS platform.

    python scripts/01_fetch_dghs.py                     # 10 Apr to 30 Sep 2026
    python scripts/01_fetch_dghs.py --from 2026-09-01   # incremental

About 8 requests per day of data, throttled to ~1/s: the full window takes
around 30-60 minutes. Safe to stop and restart: files already downloaded are
skipped.
"""

import argparse
from datetime import date

import _path  # noqa: F401
from ccd import config as C
from ccd import dghs

ap = argparse.ArgumentParser()
ap.add_argument("--from", dest="start", default="2026-04-10")
ap.add_argument("--to", dest="end", default="2026-09-30")
ap.add_argument("--tidy-only", action="store_true", help="skip downloading, rebuild the CSV")
a = ap.parse_args()

raw = C.RAW / "dghs"
if not a.tidy_only:
    dghs.fetch(date.fromisoformat(a.start), date.fromisoformat(a.end), raw)

long = dghs.tidy(raw)
wide = dghs.to_wide(long)
C.PROCESSED.mkdir(parents=True, exist_ok=True)
out = C.PROCESSED / "dghs_district_daily.csv"
wide.to_csv(out, index=False)
print(f"wrote {out}: {len(wide)} district-days, {wide['district'].nunique()} districts, "
      f"{wide['date'].min():%Y-%m-%d} to {wide['date'].max():%Y-%m-%d}")
