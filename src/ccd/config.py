"""Project-wide settings. Change dates here, not inside scripts."""

from __future__ import annotations

from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW = DATA / "raw"
PROCESSED = DATA / "processed"
EXTERNAL = DATA / "external"
RESULTS = ROOT / "results"

# --- Study window -----------------------------------------------------------
# DGHS platform has full district reporting from 10 April 2026.
STUDY_START = date(2026, 4, 13)  # first Monday after full reporting
STUDY_END = date(2026, 9, 27)

# Nationwide measles-rubella (MR) campaign. Start date from the DGHS / WHO
# timeline (high-risk upazilas from 5 April, nationwide from 20 April).
# VERIFY the end date against the DGHS campaign press releases before you
# report results; it is a parameter, so the analysis can be rerun.
CAMPAIGN_START = date(2026, 4, 20)
CAMPAIGN_END = date(2026, 5, 31)

# Weeks after the campaign ends before vaccine protection should show up in
# case counts (incubation 10-14 days + time to seroconvert).
PROTECTION_LAG_WEEKS = 3

# Baseline season for night lights: low demand, almost no load shedding
# (BPDB: supply is stable December to March).
NTL_BASELINE_START = date(2025, 12, 1)
NTL_BASELINE_END = date(2026, 2, 28)

# A night counts as a "deep outage" when district radiance falls below this
# share of its baseline median.
DEEP_OUTAGE_RATIO = 0.70

# A day counts as "hot" above this daily maximum 2 m temperature (deg C).
HOT_DAY_C = 35.0
