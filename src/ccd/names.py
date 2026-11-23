"""District / division / BPDB-zone names.

Every source spells places differently (Chittagong / Chattogram, Bogra /
Bogura, Nawabganj / Chapainababganj ...). Everything is mapped to one
canonical English spelling here, and joins fail loudly on anything unknown.
"""

from __future__ import annotations

import re
import unicodedata

# Canonical district -> division (64 districts).
DISTRICT_DIVISION: dict[str, str] = {
    # Barishal
    "Barguna": "Barishal", "Barishal": "Barishal", "Bhola": "Barishal",
    "Jhalokati": "Barishal", "Patuakhali": "Barishal", "Pirojpur": "Barishal",
    # Chattogram
    "Bandarban": "Chattogram", "Brahmanbaria": "Chattogram",
    "Chandpur": "Chattogram", "Chattogram": "Chattogram",
    "Cumilla": "Chattogram", "Cox's Bazar": "Chattogram", "Feni": "Chattogram",
    "Khagrachhari": "Chattogram", "Lakshmipur": "Chattogram",
    "Noakhali": "Chattogram", "Rangamati": "Chattogram",
    # Dhaka
    "Dhaka": "Dhaka", "Faridpur": "Dhaka", "Gazipur": "Dhaka",
    "Gopalganj": "Dhaka", "Kishoreganj": "Dhaka", "Madaripur": "Dhaka",
    "Manikganj": "Dhaka", "Munshiganj": "Dhaka", "Narayanganj": "Dhaka",
    "Narsingdi": "Dhaka", "Rajbari": "Dhaka", "Shariatpur": "Dhaka",
    "Tangail": "Dhaka",
    # Khulna
    "Bagerhat": "Khulna", "Chuadanga": "Khulna", "Jashore": "Khulna",
    "Jhenaidah": "Khulna", "Khulna": "Khulna", "Kushtia": "Khulna",
    "Magura": "Khulna", "Meherpur": "Khulna", "Narail": "Khulna",
    "Satkhira": "Khulna",
    # Mymensingh
    "Jamalpur": "Mymensingh", "Mymensingh": "Mymensingh",
    "Netrakona": "Mymensingh", "Sherpur": "Mymensingh",
    # Rajshahi
    "Bogura": "Rajshahi", "Chapainawabganj": "Rajshahi", "Joypurhat": "Rajshahi",
    "Naogaon": "Rajshahi", "Natore": "Rajshahi", "Pabna": "Rajshahi",
    "Rajshahi": "Rajshahi", "Sirajganj": "Rajshahi",
    # Rangpur
    "Dinajpur": "Rangpur", "Gaibandha": "Rangpur", "Kurigram": "Rangpur",
    "Lalmonirhat": "Rangpur", "Nilphamari": "Rangpur", "Panchagarh": "Rangpur",
    "Rangpur": "Rangpur", "Thakurgaon": "Rangpur",
    # Sylhet
    "Habiganj": "Sylhet", "Moulvibazar": "Sylhet", "Sunamganj": "Sylhet",
    "Sylhet": "Sylhet",
}

DIVISIONS = sorted(set(DISTRICT_DIVISION.values()))

# Alternative spellings seen in DGHS, BBS, geoBoundaries and BPDB files.
_ALIASES: dict[str, str] = {
    "barisal": "Barishal", "chittagong": "Chattogram", "chattagram": "Chattogram",
    "comilla": "Cumilla", "coxsbazar": "Cox's Bazar", "coxs bazar": "Cox's Bazar",
    "brahamanbaria": "Brahmanbaria", "jessore": "Jashore", "bogra": "Bogura",
    "nawabganj": "Chapainawabganj", "chapai nawabganj": "Chapainawabganj",
    "chapainababganj": "Chapainawabganj", "chapainawabganj": "Chapainawabganj",
    "maulvibazar": "Moulvibazar", "moulvi bazar": "Moulvibazar",
    "jhalakati": "Jhalokati", "jhalokathi": "Jhalokati",
    "khagrachari": "Khagrachhari", "netrokona": "Netrakona",
    "laxmipur": "Lakshmipur", "lakshmipur": "Lakshmipur",
    "rangamati hill": "Rangamati", "rangamati": "Rangamati",
    "narshingdi": "Narsingdi", "panchagar": "Panchagarh",
}

_KEY_TO_CANON = {re.sub(r"[^a-z]", "", k.lower()): v for k, v in _ALIASES.items()}
_KEY_TO_CANON.update({re.sub(r"[^a-z]", "", k.lower()): k for k in DISTRICT_DIVISION})


def _key(name: str) -> str:
    text = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode()
    text = re.sub(r"\b(zila|district|zone)\b", "", text.lower())
    return re.sub(r"[^a-z]", "", text)


def canon_district(name: str) -> str:
    """Canonical district spelling, or raise KeyError."""
    key = _key(name)
    if key in _KEY_TO_CANON:
        return _KEY_TO_CANON[key]
    raise KeyError(f"Unknown district name: {name!r}")


def canon_division(name: str) -> str:
    key = _key(name)
    for div in DIVISIONS:
        if _key(div) == key:
            return div
    if key in {"barisal"}:
        return "Barishal"
    if key in {"chittagong", "chattagram"}:
        return "Chattogram"
    raise KeyError(f"Unknown division name: {name!r}")


# BPDB / NLDC report load shedding for nine zones. They follow the divisions,
# except that the Cumilla zone is carved out of Chattogram division. This is an
# approximation of the distribution network and is documented as such.
_CUMILLA_ZONE = {"Cumilla", "Chandpur", "Brahmanbaria", "Noakhali", "Feni", "Lakshmipur"}
BPDB_ZONES = ("Dhaka", "Chattogram", "Cumilla", "Mymensingh", "Sylhet",
              "Khulna", "Barishal", "Rajshahi", "Rangpur")


def bpdb_zone(district: str) -> str:
    d = canon_district(district)
    if d in _CUMILLA_ZONE:
        return "Cumilla"
    return DISTRICT_DIVISION[d]
