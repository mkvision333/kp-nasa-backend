# app/core/rashiphal/meta.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# Canonical order (0..11)
SIGNS: List[str] = [
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
]

SIGN_INDEX: Dict[str, int] = {s.lower(): i for i, s in enumerate(SIGNS)}

# Optional: for UI labels
SIGN_ALIASES: Dict[str, str] = {
    "mesha": "Aries",
    "vrishabha": "Taurus",
    "mithuna": "Gemini",
    "karkataka": "Cancer",
    "simha": "Leo",
    "kanya": "Virgo",
    "tula": "Libra",
    "vrischika": "Scorpio",
    "dhanus": "Sagittarius",
    "makara": "Capricorn",
    "kumbha": "Aquarius",
    "meena": "Pisces",
}

def normalize_sign(sign: str) -> str:
    if not sign:
        raise ValueError("sign is required")
    s = sign.strip().lower()
    if s in SIGN_INDEX:
        return SIGNS[SIGN_INDEX[s]]
    if s in SIGN_ALIASES:
        return SIGN_ALIASES[s]
    # try title-case direct match
    t = sign.strip().title()
    if t in SIGNS:
        return t
    raise ValueError(f"Unknown sign: {sign}")

def sign_index(sign: str) -> int:
    return SIGN_INDEX[normalize_sign(sign).lower()]

def house_from_transit(birth_sign: str, moon_sign: str) -> int:
    """House number from birth sign using sign-to-sign counting."""
    b = sign_index(birth_sign)
    m = sign_index(moon_sign)
    return ((m - b) % 12) + 1

@dataclass(frozen=True)
class TransitNote:
    moon_sign: str                 # e.g. "Taurus"
    house: int                     # 1..12 from birth sign
    headline: str                  # short "Theme"
    sections: Dict[str, str]       # "Effects", "Finance", "Health", etc.
    remedy: Optional[str] = None   # optional remedy line

@dataclass(frozen=True)
class DailyRashiPhal:
    birth_sign: str
    moon_sign: str
    moon_nakshatra: Optional[str]
    house: int
    note: TransitNote
    disclaimer: str = (
        "Note: This guidance is a traditional transit-based reading and should be used as a reference only."
    )
