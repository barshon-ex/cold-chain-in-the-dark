"""Zone-wise evening-peak load shedding from the BPDB daily-generation archive.

The archive (https://misc.bpdb.gov.bd/daily-generation-archive) lists one
"Page 1" PDF per day, about ten days per listing page, newest first. We walk
the listing pages backwards until we pass the start date, download each PDF
once into data/raw/bpdb/, and parse it with the vendored NLDC parser.

Run this on your own computer: the BPDB site presents an incomplete TLS
chain, so `pip install truststore` is used to read the OS certificate store.
"""

from __future__ import annotations

import time
from datetime import date
from pathlib import Path

import pandas as pd

from .bpdb_parser import ARCHIVE_URL, parse_archive_entries, parse_pdf
from .names import BPDB_ZONES


def _session():
    import requests

    try:  # BPDB serves an incomplete certificate chain
        import truststore

        truststore.inject_into_ssl()
    except Exception:
        pass
    s = requests.Session()
    s.headers["User-Agent"] = "cold-chain-in-the-dark (research)"
    return s


def fetch(start: date, end: date, raw_dir: Path, max_pages: int = 80, pause_s: float = 0.5) -> None:
    raw_dir.mkdir(parents=True, exist_ok=True)
    session = _session()
    for page in range(1, max_pages + 1):
        url = ARCHIVE_URL if page == 1 else f"{ARCHIVE_URL}?page={page}"
        html = session.get(url, timeout=60).text
        entries = parse_archive_entries(html, ARCHIVE_URL)
        if not entries:
            print(f"page {page}: no entries, stopping")
            break
        for e in entries:
            if not (start <= e.listing_date <= end):
                continue
            path = raw_dir / f"{e.listing_date.isoformat()}_{Path(e.pdf_url).name}"
            if path.exists():
                continue
            resp = session.get(e.pdf_url, timeout=90)
            if resp.ok:
                path.write_bytes(resp.content)
            time.sleep(pause_s)
        oldest = min(e.listing_date for e in entries)
        print(f"page {page}: oldest listing {oldest}")
        if oldest < start:
            break


def tidy(raw_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """PDFs -> (zone table, list of files that failed to parse)."""
    rows, failed = [], []
    for path in sorted(raw_dir.glob("*.pdf")):
        try:
            rep = parse_pdf(path.read_bytes(), path.name)
        except Exception as exc:
            failed.append({"file": path.name, "error": str(exc)})
            continue
        for z in rep.zones:
            rows.append({
                "date": rep.date.isoformat(),
                "zone": z.zone,
                "load_shed_mw": z.load_shed_mw,
                "demand_mw": z.demand_mw,
                "national_evening_shed_mw": rep.evening_peak.load_shed_mw,
                "unserved_gwh": rep.energy.unserved_gwh,
                "source_pdf": rep.source_pdf,
            })
    df = pd.DataFrame(rows).drop_duplicates(["date", "zone"], keep="last")
    unknown = set(df["zone"]) - set(BPDB_ZONES) if len(df) else set()
    if unknown:
        raise ValueError(f"unexpected zone names: {unknown}")
    return df.sort_values(["date", "zone"]), pd.DataFrame(failed)
