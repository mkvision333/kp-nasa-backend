# app/core/ruling_planets.py
from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional

WEEKDAY_LORD = {
    0: "Moon",
    1: "Mars",
    2: "Mercury",
    3: "Jupiter",
    4: "Venus",
    5: "Saturn",
    6: "Sun",
}

SIGN_LORD = [
    "Mars",    # Aries
    "Venus",   # Taurus
    "Mercury", # Gemini
    "Moon",    # Cancer
    "Sun",     # Leo
    "Mercury", # Virgo
    "Venus",   # Libra
    "Mars",    # Scorpio
    "Jupiter", # Sagittarius
    "Saturn",  # Capricorn
    "Saturn",  # Aquarius
    "Jupiter", # Pisces
]

def _safe_fromiso(s: str) -> Optional[datetime]:
    """
    Handles:
    - 'YYYY-MM-DDTHH:MM'
    - 'YYYY-MM-DDTHH:MM:SS'
    - with milliseconds
    - with 'Z'
    - with timezone offset
    """
    try:
        st = str(s or "").strip()
        if not st:
            return None
        # if endswith Z => convert for fromisoformat
        if st.endswith("Z"):
            st = st[:-1] + "+00:00"
        return datetime.fromisoformat(st)
    except Exception:
        return None

def _sign_index(abs_deg: float) -> int:
    x = float(abs_deg) % 360.0
    return int(x // 30.0)

def _dms_to_abs_deg(dms: Dict[str, Any]) -> float:
    deg = float(dms.get("deg", 0) or 0)
    minute = float(dms.get("min", 0) or 0)
    sec = float(dms.get("sec", 0) or 0)
    return (deg + minute / 60.0 + sec / 3600.0) % 360.0

def compute_ruling_planets(
    datetimeLocal: str,
    kundali_planets: List[Dict[str, Any]],
    bhava_cusps: List[Dict[str, Any]],
    kp_bhava_table: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "dayLord": None,
        "moonSignLord": None,
        "ascSignLord": None,
        "ascStarLord": None,
    }

    # 1) Day Lord
    dt = _safe_fromiso(datetimeLocal)
    if dt is not None:
        out["dayLord"] = WEEKDAY_LORD.get(dt.weekday())

    # 2) Moon Sign Lord
    moon_abs = None
    for row in (kundali_planets or []):
        if row.get("planet") == "Moon":
            moon_abs = _dms_to_abs_deg(row.get("longitude") or {})
            break
    if moon_abs is not None:
        out["moonSignLord"] = SIGN_LORD[_sign_index(moon_abs)]

    # 3) Asc Sign Lord
    asc_abs = None
    for b in (bhava_cusps or []):
        if int(b.get("bhava", 0) or 0) == 1:
            asc_abs = _dms_to_abs_deg(b.get("longitude") or {})
            break
    if asc_abs is not None:
        out["ascSignLord"] = SIGN_LORD[_sign_index(asc_abs)]

    # 4) Asc Star Lord (may be None if backend didn't fill kp_bhava_table)
    asc_star = None
    for b in (kp_bhava_table or []):
        if int(b.get("bhava", 0) or 0) == 1:
            asc_star = b.get("starLord") or None
            break
    out["ascStarLord"] = asc_star

    return out
