# app/core/houses_placidus.py
"""
Placidus house cusps (TROPICAL) via pure math (NO Swiss Ephemeris).

IMPORTANT CONVENTIONS
---------------------
• Longitude: +East, -West   (India = positive)
• MC = true upper culmination (overhead point)
• This module returns TROPICAL (SAYANA) values ONLY.
• Apply ayanamsa (nirayana) ONLY in FRONTEND (MK requirement).

MK FIX NOTES
------------
1) ASC is coming 180° opposite but MC is correct:
   → DO NOT change LON_SIGN (it would affect MC too).
   → Flip ONLY ASC by +180° and rebuild ASC-opposite houses (1 & 7).
2) House orientation around MC:
   • 11th & 12th are on one side of 10th (MC)
   • 9th & 8th are on the other side
   → So we solve 11/12 from (MC - 30/-60) and 9/8 from (MC + 30/+60) as per MK fix.
3) Ayanamsa must NOT be applied in backend:
   → siderealize_cusps() intentionally disabled to prevent double-apply bugs.
"""

import math
from typing import Dict, Tuple

DEG2RAD = math.pi / 180.0
RAD2DEG = 180.0 / math.pi

# ✅ Keep India convention
LON_SIGN = +1   # +1 = India convention (recommended)

# ✅ MK: Flip ONLY ASC by 180°, keep MC as-is
FLIP_ASC_180 = True


# ----------------- helpers -----------------

def _wrap360(x: float) -> float:
    return float(x % 360.0)


def _wrap_pi(x: float) -> float:
    return (x + math.pi) % (2 * math.pi) - math.pi


# ----------------- astronomy -----------------

def mean_obliquity_deg(jd: float) -> float:
    """Mean obliquity of ecliptic (Meeus)"""
    T = (jd - 2451545.0) / 36525.0
    return (
        23.0
        + 26.0 / 60.0
        + 21.448 / 3600.0
        - (46.8150 * T) / 3600.0
        - (0.00059 * T * T) / 3600.0
        + (0.001813 * T * T * T) / 3600.0
    )


def gmst_deg(jd: float) -> float:
    """Greenwich Mean Sidereal Time (degrees)"""
    T = (jd - 2451545.0) / 36525.0
    return _wrap360(
        280.46061837
        + 360.98564736629 * (jd - 2451545.0)
        + 0.000387933 * T * T
        - (T * T * T) / 38710000.0
    )


def lst_rad(jd: float, lon_deg_east: float) -> float:
    """Local Sidereal Time (radians)"""
    lon = float(lon_deg_east) * LON_SIGN
    theta = _wrap360(gmst_deg(jd) + lon)
    return theta * DEG2RAD


# ----------------- coordinate transforms -----------------

def ecl_to_equ(lam: float, beta: float, eps: float) -> Tuple[float, float]:
    """Ecliptic → Equatorial (radians)"""
    sin_dec = math.sin(beta) * math.cos(eps) + math.cos(beta) * math.sin(eps) * math.sin(lam)
    sin_dec = max(-1.0, min(1.0, sin_dec))
    dec = math.asin(sin_dec)

    y = math.sin(lam) * math.cos(eps) - math.tan(beta) * math.sin(eps)
    x = math.cos(lam)
    ra = math.atan2(y, x) % (2 * math.pi)

    return ra, dec


# ----------------- angles -----------------

def mc_longitude_deg(theta: float) -> float:
    """
    TRUE astrological MC (tropical)
    NOTE: obliquity ε is NOT used here
    """
    lam = math.atan2(math.sin(theta), math.cos(theta))
    return _wrap360(lam * RAD2DEG)


def asc_longitude_deg(theta: float, eps: float, phi: float) -> float:
    """Ascendant ecliptic longitude (tropical)"""
    y = -math.cos(theta)
    x = math.sin(theta) * math.cos(eps) + math.tan(phi) * math.sin(eps)
    lam = math.atan2(y, x)
    return _wrap360(lam * RAD2DEG)


# ----------------- placidus math -----------------

def _semi_diurnal_arc(phi: float, dec: float) -> float:
    v = -math.tan(phi) * math.tan(dec)
    v = max(-1.0, min(1.0, v))
    return math.acos(v)


def _solve_cusp(theta: float, eps: float, phi: float, guess_deg: float, frac: float) -> float:
    """
    Solve Placidus cusp numerically
    """
    guess = _wrap360(guess_deg) * DEG2RAD

    def f(lam: float) -> float:
        ra, dec = ecl_to_equ(lam, 0.0, eps)
        sda = _semi_diurnal_arc(phi, dec)
        h_target = frac * sda
        h = _wrap_pi(theta - ra)
        return _wrap_pi(h - h_target)

    best = guess
    best_val = 1e9

    for k in range(-120, 121, 5):
        lam = (guess + k * DEG2RAD) % (2 * math.pi)
        v = abs(f(lam))
        if v < best_val:
            best_val = v
            best = lam

    x0 = (best - 2 * DEG2RAD) % (2 * math.pi)
    x1 = (best + 2 * DEG2RAD) % (2 * math.pi)
    y0 = f(x0)
    y1 = f(x1)

    for _ in range(40):
        den = y1 - y0
        if abs(den) < 1e-14:
            break
        x2 = (x1 - y1 * (x1 - x0) / den) % (2 * math.pi)
        y2 = f(x2)
        x0, y0 = x1, y1
        x1, y1 = x2, y2
        if abs(y1) < 1e-11:
            break

    return _wrap360(x1 * RAD2DEG)


# ----------------- public API -----------------

def placidus_cusps(jd: float, lat_deg: float, lon_deg_east: float) -> Dict[str, float]:
    """
    Returns TROPICAL (SAYANA) cusps:
    asc, mc, house1..house12

    Ayanamsa must be applied in FRONTEND only.
    """
    eps = mean_obliquity_deg(jd) * DEG2RAD
    phi = lat_deg * DEG2RAD
    theta = lst_rad(jd, lon_deg_east)

    # tropical raw
    asc = asc_longitude_deg(theta, eps, phi)
    mc = mc_longitude_deg(theta)

    # MK FIX: flip ONLY ASC by 180°, keep MC untouched
    if FLIP_ASC_180:
        asc = _wrap360(asc + 180.0)

    # ✅ MK corrected orientation around MC:
    # One side of MC: 11th, 12th (MC - 30/-60)
    h11 = _solve_cusp(theta, eps, phi, mc - 30.0, -1 / 3)
    h12 = _solve_cusp(theta, eps, phi, mc - 60.0, -2 / 3)

    # Other side of MC: 9th, 8th (MC + 30/+60)
    h9 = _solve_cusp(theta, eps, phi, mc + 30.0, +1 / 3)
    h8 = _solve_cusp(theta, eps, phi, mc + 60.0, +2 / 3)

    # Derived opposites
    h4 = _wrap360(mc + 180.0)      # IC (opposite MC)
    h5 = _wrap360(h11 + 180.0)
    h6 = _wrap360(h12 + 180.0)
    h7 = _wrap360(asc + 180.0)     # Desc (opposite ASC)
    h2 = _wrap360(h8 + 180.0)
    h3 = _wrap360(h9 + 180.0)

    return {
        "asc": asc,
        "mc": mc,
        "house1": asc,
        "house2": h2,
        "house3": h3,
        "house4": h4,
        "house5": h5,
        "house6": h6,
        "house7": h7,
        "house8": h8,
        "house9": h9,
        "house10": mc,
        "house11": h11,
        "house12": h12,
    }

def siderealize_cusps(cusps_trop: Dict[str, float], ayanamsa_deg: float) -> Dict[str, float]:
    """
    ✅ NO-OP BY DESIGN (MK requirement)

    Backend must return TROPICAL only.
    This function exists only for compatibility with older endpoint code that may still call it.
    It will NOT apply ayanamsa and will NOT crash.
    """
    return cusps_trop

