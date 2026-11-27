"""Tests run on synthetic data only (see ccd/synthetic.py)."""

import math

import pytest

from ccd import models, panel, synthetic
from ccd.names import DISTRICT_DIVISION, bpdb_zone, canon_district


def test_names_cover_all_64_districts():
    assert len(DISTRICT_DIVISION) == 64
    assert len(set(DISTRICT_DIVISION.values())) == 8


@pytest.mark.parametrize("raw,canon", [
    ("Chittagong", "Chattogram"), ("Comilla", "Cumilla"), ("Bogra", "Bogura"),
    ("Jessore", "Jashore"), ("Nawabganj", "Chapainawabganj"), ("Cox's Bazar", "Cox's Bazar"),
    ("COXS BAZAR", "Cox's Bazar"), ("Maulvibazar", "Moulvibazar"), ("Brahamanbaria", "Brahmanbaria"),
    ("Barisal", "Barishal"), ("Dhaka District", "Dhaka"),
])
def test_alias_resolution(raw, canon):
    assert canon_district(raw) == canon


def test_unknown_name_fails_loudly():
    with pytest.raises(KeyError):
        canon_district("Atlantis")


def test_zone_mapping():
    assert bpdb_zone("Feni") == "Cumilla"
    assert bpdb_zone("Cox's Bazar") == "Chattogram"
    assert bpdb_zone("Gazipur") == "Dhaka"


def test_population_file_has_all_districts():
    pop = panel.load_population()
    assert len(pop) == 64 and pop["pop_u5"].gt(0).all()


def _panel(rr):
    measles, ntl, pop = synthetic.make(true_rate_ratio=rr, seed=3)
    ex = panel.district_exposures(ntl)
    return panel.build_panel(measles, ex, pop)


def test_did_recovers_planted_effect():
    p = _panel(1.30)
    est = models.did(p)
    assert est["rr_low"] < 1.30 < est["rr_high"] or math.isclose(est["rate_ratio"], 1.30, rel_tol=0.08)
    assert est["rr_low"] > 1.0  # effect detected


def test_did_null_when_no_effect():
    p = _panel(1.00)
    est = models.did(p)
    assert est["rr_low"] < 1.0 < est["rr_high"]


def test_event_study_has_reference_week():
    es = models.event_study(_panel(1.2))
    assert (es["term"] == "reference").sum() == 1


def test_district_trends_variant_recovers_effect():
    p = _panel(1.30)
    est = models.did(p, district_trends=True)
    assert est["rr_low"] > 1.0 and abs(est["rate_ratio"] - 1.30) < 0.12
