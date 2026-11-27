"""Run the whole study with one command.

    python scripts/run_all.py

Order:
  1. DGHS district measles data           (download, ~30-60 min the first time)
  2. BPDB zone load shedding              (download; skipped if the site fails)
  3. Earth Engine night-light exports      (needs the CSVs in data/raw/gee/;
                                           see docs/SETUP_bn.md, step 4)
  4. Main analysis incl. district trends  (results/main/)
  5. Zone inequality                      (results/zone_inequality/)
  6. Historical parallel trends           (results/historical_pretrends/)

Downloads already on disk are skipped, so it is safe to run again.
At the end it prints the numbers to report.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


def run(step: str, args: list[str], required: bool = True) -> bool:
    print(f"\n=== {step} ===", flush=True)
    code = subprocess.call([PY, *args], cwd=ROOT)
    if code != 0:
        msg = f"step failed: {step}"
        if required:
            sys.exit(msg + " - fix this before continuing (see docs/SETUP_bn.md)")
        print(msg + " - continuing without it")
        return False
    return True


run("1. DGHS district measles data", ["scripts/01_fetch_dghs.py"])
run("2. BPDB zone load shedding", ["scripts/02_fetch_bpdb.py"], required=False)

gee = sorted((ROOT / "data" / "raw" / "gee").glob("ntl_tmax_district_*.csv"))
if not gee:
    sys.exit("\nStep 3 is missing: no Earth Engine exports in data/raw/gee/.\n"
             "Run gee/export_district_ntl_temperature.js in code.earthengine.google.com,\n"
             "download the CSVs from Google Drive into data/raw/gee/, then run this again.")
run("3. Night-light outage index", ["scripts/03_prepare_ntl.py"])
run("4. Main analysis", ["scripts/04_run_analysis.py"])
zp = ROOT / "data" / "processed" / "bpdb_zone_daily.csv"
run("5. Zone inequality", ["scripts/05_zone_inequality.py"] + (["--input", str(zp)] if zp.exists() else []),
    required=False)
run("6. Historical parallel trends", ["scripts/06_historical_pretrends.py"], required=False)

print("\n" + "=" * 70)
for f in ["results/main/SUMMARY.md", "results/historical_pretrends/SUMMARY.md"]:
    p = ROOT / f
    if p.exists():
        print(p.read_text(encoding="utf-8"))
print("Figures: results/main/figures/ and results/historical_pretrends/")
