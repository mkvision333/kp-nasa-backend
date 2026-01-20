# app/core/nasa_ephemeris.py  ✅ FULL REPLACE
#
# ✅ FIXES:
# 1) Render-safe Skyfield loader directory: /tmp/skyfield (avoids permission/caching 500 errors)
# 2) Uses PLANET CENTERS (NOT barycenters) to avoid arcminute drifts
# 3) Robust ephemeris loading:
#    - Tries de440s.bsp first (your choice)
#    - Falls back to de421.bsp if de440s missing/unavailable (still stable, prevents 500)
# 4) Safe UTC parsing for "Z" timestamps
# 5) Speed computation uses datetime +/- timedelta (no minute overflow bugs)
#
# NOTE:
# - Accuracy depends on ephemeris file used (de440s best).
# - If you want EXACT match with a specific professional tool,
#   we can later align flags (apparent vs astrometric, nutation) after logs.

from skyfield.api import Loader
from skyfield.framelib import ecliptic_frame
from datetime import datetime, timezone, timedelta
import os
import math

# ---------------------------------------------------------
# ✅ Skyfield loader (Render-friendly)
# ---------------------------------------------------------
# Render allows writing to /tmp. Use it for Skyfield cache.
_SKY_DIR = os.environ.get("SKYFIELD_DIR", "/tmp/skyfield")
load = Loader(_SKY_DIR)

_EPH = None
_TS = None

# Prefer de440s (smaller than full de440, still very good)
DE_FILE = os.environ.get("JPL_DE_FILE", "de440s.bsp")

# ✅ Use planet centers (NOT barycenters) to avoid drift
PLANETS = [
    ("Sun", "sun"),
    ("Moon", "moon"),
    ("Mercury", "mercury"),
    ("Venus", "venus"),
    ("Mars", "mars"),
    ("Jupiter", "jupiter"),
    ("Saturn", "saturn"),
    ("Uranus", "uranus"),
    ("Neptune", "neptune"),
    ("Pluto", "pluto"),
]


def _ensure_loaded():
    global _EPH, _TS
    if _TS is None:
        _TS = load.timescale()

    if _EPH is None:
        # ✅ Try preferred file first, fallback to de421 to prevent 500
        try:
            _EPH = load(DE_FILE)
        except Exception:
            _EPH = load("de421.bsp")


def _wrap360(x: float) -> float:
    x = float(x) % 360.0
    return x if x >= 0 else x + 360.0


def _jd_T(jd: float) -> float:
    return (jd - 2451545.0) / 36525.0


# ---------------------------------------------------------
# ✅ Lahiri/KP Ayanamsa (Approx, date-based)
# ---------------------------------------------------------
def ayanamsa_lahiri_approx_deg(jd_ut: float) -> float:
    T = _jd_T(jd_ut)
    years = T * 100.0
    rate_deg_per_year = 50.290966 / 3600.0
    ay = 23.85675 + (years * rate_deg_per_year)
    return _wrap360(ay)


# ---------------------------------------------------------
# ✅ Mean Lunar Node (Rahu) tropical longitude (Meeus)
# ---------------------------------------------------------
def mean_lunar_node_tropical_deg(jd_ut: float) -> float:
    T = _jd_T(jd_ut)
    Om = (
        125.04452
        - 1934.136261 * T
        + 0.0020708 * (T * T)
        + (T * T * T) / 450000.0
    )
    return _wrap360(Om)


# ---------------------------------------------------------
# ✅ Planet positions tropical (geocentric) with speed
# ---------------------------------------------------------
def get_planets_ecliptic(datetime_utc_iso: str, lat: float, lng: float):
    """
    Returns geocentric apparent ecliptic longitude/latitude for planets
    and approximate speed_lon in deg/day.

    Input datetime_utc_iso examples:
      "2026-01-19T03:30:00Z"
      "2026-01-19T03:30:00"
    """
    _ensure_loaded()

    s = (datetime_utc_iso or "").strip()
    if s.endswith("Z"):
        s = s[:-1]

    # parse
    dt = datetime.fromisoformat(s)
    # force UTC if naive
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    # Skyfield time
    t = _TS.utc(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)

    # ✅ speed calc with timedelta (no overflow)
    dt_plus = dt + timedelta(minutes=1)
    dt_minus = dt - timedelta(minutes=1)
    t_plus = _TS.utc(dt_plus.year, dt_plus.month, dt_plus.day, dt_plus.hour, dt_plus.minute, dt_plus.second)
    t_minus = _TS.utc(dt_minus.year, dt_minus.month, dt_minus.day, dt_minus.hour, dt_minus.minute, dt_minus.second)

    earth = _EPH["earth"]
    observer = earth  # geocentric

    results = []

    for disp, key in PLANETS:
        body = _EPH[key]

        # apparent position (includes light-time + aberration)
        astrometric = observer.at(t).observe(body).apparent()

        # ecliptic coords
        ecl = astrometric.frame_latlon(ecliptic_frame)
        lon = _wrap360(ecl[1].degrees)
        lat_e = float(ecl[0].degrees)
        dist = float(astrometric.distance().au)

        # speed approximation (deg/day)
        ecl_p = observer.at(t_plus).observe(body).apparent().frame_latlon(ecliptic_frame)
        ecl_m = observer.at(t_minus).observe(body).apparent().frame_latlon(ecliptic_frame)
        lon_p = _wrap360(ecl_p[1].degrees)
        lon_m = _wrap360(ecl_m[1].degrees)

        d = lon_p - lon_m
        if d > 180:
            d -= 360
        if d < -180:
            d += 360

        # over 2 minutes => scale to day (1440 minutes)
        speed_lon = float((d / 2.0) * 1440.0)

        results.append(
            {
                "name": disp,
                "lon": lon,
                "lat": lat_e,
                "dist_au": dist,
                "speed_lon": speed_lon,
            }
        )

    # Use TT JD for internal stability; UT1 requires IERS tables (can drift if not loaded)
    # For astrology pipelines, JD(TT) is fine as a continuous time tag.
    jd_tt = float(t.tt)
    return jd_tt, results
