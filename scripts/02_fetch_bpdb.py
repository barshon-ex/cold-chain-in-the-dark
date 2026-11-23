"""Step 2 - zone-wise evening-peak load shedding from BPDB daily reports.

    pip install truststore        # BPDB's certificate chain is incomplete
    python scripts/02_fetch_bpdb.py

Downloads the daily "Page 1" PDFs (March-September 2026) into data/raw/bpdb/
and parses the "Zone-wise Load-shed and Demand Summary" table.
Files that fail to parse are listed in data/processed/bpdb_parse_failures.csv;
check a few by hand.
"""

import argparse
from datetime import date

import _path  # noqa: F401
from ccd import bpdb
from ccd import config as C

ap = argparse.ArgumentParser()
ap.add_argument("--from", dest="start", default="2026-03-01")
ap.add_argument("--to", dest="end", default="2026-09-30")
ap.add_argument("--tidy-only", action="store_true")
a = ap.parse_args()

raw = C.RAW / "bpdb"
if not a.tidy_only:
    bpdb.fetch(date.fromisoformat(a.start), date.fromisoformat(a.end), raw)

zones, failed = bpdb.tidy(raw)
C.PROCESSED.mkdir(parents=True, exist_ok=True)
zones.to_csv(C.PROCESSED / "bpdb_zone_daily.csv", index=False)
failed.to_csv(C.PROCESSED / "bpdb_parse_failures.csv", index=False)
print(f"zones: {zones['date'].nunique()} days parsed; {len(failed)} PDFs failed")
