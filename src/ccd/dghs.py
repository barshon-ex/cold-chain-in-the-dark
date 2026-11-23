"""District-level daily measles counts from the DGHS monitoring platform.

https://measles.dghs.gov.bd is where district civil-surgeon offices and
hospitals submit their daily figures. Its public dashboard reads JSON from
``/api/reports/summary?outbreakId=measles-2026&date=YYYY-MM-DD[&division=X]``.
Without ``division`` it returns the eight divisions; with one, that
division's districts.

The endpoint and its quirks were documented by Kath Sherratt in
github.com/kathsherratt/measles-bgd (MIT). Known platform quirks:
  * the platform launched on 26 April; 15 March to 7 April was back-filled
    onto 7 April and 2-5 April are empty, so the study starts after 10 April;
  * from June, a published day never changes (late reports count on the day
    they arrive).

Every raw response is saved, so the tidy step can be rerun without refetching.
"""

from __future__ import annotations

import json
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from .names import DIVISIONS, canon_district, canon_division

BASE = "https://measles.dghs.gov.bd/api/reports/summary"
OUTBREAK = "measles-2026"
# The platform spells Barishal "Barisal".
PLATFORM_DIVISIONS = ["Barisal" if d == "Barishal" else d for d in DIVISIONS]

MEASURES = {
    "suspected24h": "suspected",
    "confirmed24h": "confirmed",
    "suspectedDeath24h": "suspected_deaths",
    "confirmedDeath24h": "confirmed_deaths",
    "admitted24h": "admitted",
    "discharged24h": "discharged",
    "serumSent24h": "serum_sent",
}


def fetch(start: date, end: date, raw_dir: Path, pause_s: float = 1.0) -> None:
    """Download one JSON per (date, division). Skips files already on disk."""
    import requests

    raw_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers["User-Agent"] = "cold-chain-in-the-dark (research; github)"
    day = start
    while day <= end:
        for division in PLATFORM_DIVISIONS:
            path = raw_dir / f"{day.isoformat()}_{division}.json"
            if path.exists():
                continue
            params = {"outbreakId": OUTBREAK, "date": day.isoformat(), "division": division}
            for attempt in range(4):
                try:
                    resp = session.get(BASE, params=params, timeout=60)
                    resp.raise_for_status()
                    path.write_text(resp.text, encoding="utf-8")
                    break
                except Exception as exc:  # network errors: retry with backoff
                    wait = 2 ** (attempt + 1)
                    print(f"  ! {day} {division}: {exc}; retry in {wait}s")
                    time.sleep(wait)
            time.sleep(pause_s)
        print(f"fetched {day}")
        day += timedelta(days=1)


def tidy(raw_dir: Path) -> pd.DataFrame:
    """Raw JSON files -> long table: date, division, district, measure, value."""
    rows = []
    for path in sorted(raw_dir.glob("*.json")):
        day, division = path.stem.split("_", 1)
        payload = json.loads(path.read_text(encoding="utf-8"))
        for place, values in (payload.get("breakdown") or {}).items():
            for field, value in values.items():
                if field not in MEASURES:
                    continue
                rows.append({
                    "date": day,
                    "division": canon_division(division),
                    "district": canon_district(place),
                    "measure": MEASURES[field],
                    "value": float(value or 0),
                })
    df = pd.DataFrame(rows, columns=["date", "division", "district", "measure", "value"])
    df["date"] = pd.to_datetime(df["date"])
    return df


def to_wide(long: pd.DataFrame) -> pd.DataFrame:
    """One row per district-day, one column per measure."""
    wide = (long.pivot_table(index=["date", "division", "district"], columns="measure",
                             values="value", aggfunc="sum")
                .reset_index())
    wide.columns.name = None
    return wide
