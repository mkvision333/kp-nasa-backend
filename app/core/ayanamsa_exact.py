# app/core/ayanamsa_exact.py
"""
Ayanamsa engine (MANUAL by default, optional SwissEphemeris if available)

Supported modes:
  - "LAHIRI"   (Chitrapaksha / Swiss sid1 style anchor @ J2000 TT)
  - "KP_OLD"   (Krishnamurti table ayanamsha ~ Swiss sid5)
  - "KP_NEW"   (Krishnamurti/Senthilathiban (VP291) ~ Swiss sid45)
  - "KP"       (alias -> KP_OLD)
  - "KRISHNAMURTI" (alias -> KP_OLD)

Default behavior:
  - Uses MANUAL formulas (no pyswisseph needed)
  - If pyswisseph is installed AND env USE_SWISS_AYANAMSA=1, it will use SwissEphemeris.
"""

import os
import math
from typing import Literal, Optional

try:
    import swisseph as swe  # type: ignore
except Exception:
    swe = None


# ----------------- helpers -----------------

def _wrap360(x: float) -> float:
    x = float(x) % 360.0
    return x if x >= 0 else x + 360.0


def _deg_from_dms(d: int, m: int, s: float) -> float:
    return float(d) + float(m) / 60.0 + float(s) / 3600.0


def _jd_from_calendar(
    year: int,
    month: int,
    day: int,
    hour: int = 0,
    minute: int = 0,
    second: float = 0.0,
    calendar: Literal["gregorian", "julian"] = "gregorian",
) -> float:
    """
    Julian Day (JD) for a calendar date/time.
    - Gregorian algorithm for modern dates
    - Julian algorithm for old dates

    Returns JD (starting at noon). This is standard astronomical JD.
    """
    y = int(year)
    m = int(month)
    d = float(day) + (float(hour) + float(minute) / 60.0 + float(second) / 3600.0) / 24.0

    if m <= 2:
        y -= 1
        m += 12

    A = math.floor(y / 100.0)
    if calendar == "gregorian":
        B = 2 - A + math.floor(A / 4.0)
    else:
        B = 0

    jd = math.floor(365.25 * (y + 4716)) + math.floor(30.6001 * (m + 1)) + d + B - 1524.5
    return float(jd)


def _auto_calendar(year: int, month: int, day: int) -> Literal["gregorian", "julian"]:
    """
    Gregorian reform: 1582-10-15
    For earlier dates, use Julian calendar.
    """
    if (year, month, day) >= (1582, 10, 15):
        return "gregorian"
    return "julian"


# ----------------- MANUAL precession polynomial (IAE 1989 style) -----------------
# Swiss Ephemeris doc states:
# PN = (5029.0966 + 2.22226*T - 0.000042*T^2)*t
#    + (1.11161 - 0.000127*T)*t^2
#    - 0.000113*t^3
# where:
#   t = (Je - Js) / 36525
#   T = (Js - 2451545) / 36525
# PN in arcseconds

def _precession_arcsec_IAE1989(jd_end: float, jd_start: float) -> float:
    t = (float(jd_end) - float(jd_start)) / 36525.0
    T = (float(jd_start) - 2451545.0) / 36525.0

    PN = (
        (5029.0966 + 2.22226 * T - 0.000042 * (T * T)) * t
        + (1.11161 - 0.000127 * T) * (t * t)
        - 0.000113 * (t * t * t)
    )
    return float(PN)


# ----------------- MANUAL ayanamsa definitions -----------------

# LAHIRI anchor (Swiss doc example at J2000 TT, JD=2451545.0):
# 23°51'25.5324  (we use this as a practical anchor)
_LAHIRI_J2000_DEG = _deg_from_dms(23, 51, 25.5324)
_JD_J2000_TT = 2451545.0

# KP_OLD (Swiss doc: Krishnamurti table ayanamsha No.5)
# ayanamsha = 22.363889 at t0 = 1 Jan 1900
_KPOLD_T0_DEG = 22.363889
_JD_KPOLD_T0 = _jd_from_calendar(1900, 1, 1, 0, 0, 0.0, calendar="gregorian")  # 2415020.5

# KP_NEW (Swiss doc: Krishnamurti/Senthilathiban (VP291) No.45)
# ayanamsha = 0 at t0 = 21 March 291 CE, 4:02:45 UT
_JD_KPNEW_T0 = _jd_from_calendar(291, 3, 21, 4, 2, 45.0, calendar=_auto_calendar(291, 3, 21))
_KPNEW_T0_DEG = 0.0


def get_ayanamsa_deg_manual(jd_ut: float, mode: str = "KP_OLD") -> float:
    """
    Manual ayanamsa (no SwissEphemeris).
    Uses IAE1989-style precession polynomial + documented anchors.
    """
    m = (mode or "KP_OLD").strip().upper()

    if m in ("KP", "KRISHNAMURTI", "KP_OLD", "KPO", "KPOLD"):
        pn_arcsec = _precession_arcsec_IAE1989(jd_ut, _JD_KPOLD_T0)
        return _wrap360(_KPOLD_T0_DEG + pn_arcsec / 3600.0)

    if m in ("KP_NEW", "KPN", "KPNEW", "VP291", "SENTHILATHIBAN"):
        pn_arcsec = _precession_arcsec_IAE1989(jd_ut, _JD_KPNEW_T0)
        return _wrap360(_KPNEW_T0_DEG + pn_arcsec / 3600.0)

    if m in ("LAHIRI", "CHITRAPAKSHA"):
        pn_arcsec = _precession_arcsec_IAE1989(jd_ut, _JD_J2000_TT)
        return _wrap360(_LAHIRI_J2000_DEG + pn_arcsec / 3600.0)

    raise ValueError(f"Unknown ayanamsa mode: {mode}")


# ----------------- SWISS (optional exact) -----------------

def get_ayanamsa_deg_swiss(jd_ut: float, mode: str = "KP_OLD") -> float:
    """
    Exact ayanamsa from Swiss Ephemeris (UT-based).
    Requires pyswisseph and ephemeris files correctly set.
    """
    if swe is None:
        raise RuntimeError("Swiss Ephemeris not available. Install 'pyswisseph'.")

    m = (mode or "KP_OLD").strip().upper()

    if m in ("LAHIRI", "CHITRAPAKSHA"):
        swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)

    elif m in ("KP", "KRISHNAMURTI", "KP_OLD", "KPO", "KPOLD"):
        # Swiss: Krishnamurti ayanamsha derived from table (sid 5)
        sid = getattr(swe, "SIDM_KRISHNAMURTI", None)
        if sid is None:
            raise RuntimeError("This swisseph build lacks SIDM_KRISHNAMURTI.")
        swe.set_sid_mode(sid, 0, 0)

    elif m in ("KP_NEW", "KPN", "KPNEW", "VP291", "SENTHILATHIBAN"):
        # Swiss: Krishnamurti/Senthilathiban (derived from zero ayanamsha year 291) (sid 45)
        sid = getattr(swe, "SIDM_KRISHNAMURTI_VP291", None)
        if sid is None:
            # fallback: some builds might not expose the constant; try numeric if present
            # (do not crash; prefer clear error)
            raise RuntimeError("This swisseph build lacks SIDM_KRISHNAMURTI_VP291.")
        swe.set_sid_mode(sid, 0, 0)

    else:
        raise ValueError(f"Unknown ayanamsa mode: {mode}")

    ay = float(swe.get_ayanamsa_ut(jd_ut))
    return _wrap360(ay)


# ----------------- public API -----------------

def get_ayanamsa_deg(jd_ut: float, mode: str = "KP_OLD") -> float:
    """
    Public function used by the rest of the backend.

    Default: MANUAL engine (no Swiss dependency).
    If you want Swiss exact in dev/testing, set:
      USE_SWISS_AYANAMSA=1
    """
    use_swiss = os.getenv("USE_SWISS_AYANAMSA", "").strip() in ("1", "true", "TRUE", "yes", "YES")

    if use_swiss:
        # if Swiss missing, fall back to manual automatically
        try:
            return get_ayanamsa_deg_swiss(jd_ut, mode)
        except Exception:
            return get_ayanamsa_deg_manual(jd_ut, mode)

    return get_ayanamsa_deg_manual(jd_ut, mode)
