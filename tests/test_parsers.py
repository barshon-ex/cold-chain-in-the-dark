"""Format tests for the download parsers, using small hand-made fixtures."""

import json

import pandas as pd

from ccd import dghs, panel


def test_dghs_tidy_reads_platform_json(tmp_path):
    # Shape of /api/reports/summary?division=Barisal, as documented by
    # kathsherratt/measles-bgd (breakdown -> place -> measure).
    payload = {"breakdown": {"Barisal": {"suspected24h": 12, "confirmed24h": 2, "admitted24h": 5},
                             "Jhalakati": {"suspected24h": 3, "confirmed24h": 0, "admitted24h": 1}},
               "debug": {"reportCount": 7}}
    (tmp_path / "2026-05-01_Barisal.json").write_text(json.dumps(payload))
    wide = dghs.to_wide(dghs.tidy(tmp_path))
    assert set(wide["district"]) == {"Barishal", "Jhalokati"}
    assert set(wide["division"]) == {"Barishal"}
    assert wide.loc[wide.district == "Barishal", "suspected"].item() == 12


def test_gee_export_is_cleaned(tmp_path):
    f = tmp_path / "ntl_tmax_district_2026_05.csv"
    pd.DataFrame({"date": ["2026-05-01", "2026-05-01"], "district": ["Bogra", "Comilla"],
                  "ntl_ratio": [0.8, 1.0], "dark_share": [0.1, 0.0], "good_frac": [0.9, 0.1],
                  "tmax_c": [36.0, -999]}).to_csv(f, index=False)
    ntl = panel.load_ntl(f)
    assert list(ntl["district"]) == ["Bogura", "Cumilla"]
    assert ntl["tmax_c"].isna().sum() == 1
    m = panel.outage_metrics(ntl)
    assert len(m) == 1  # the cloudy night (good_frac 0.1) is dropped
    assert abs(m["outage_index"].item() - 0.2) < 1e-9
