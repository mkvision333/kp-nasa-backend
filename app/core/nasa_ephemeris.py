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
    _ensure_loaded()

    if datetime_utc_iso.endswith("Z"):
        datetime_utc_iso = datetime_utc_iso[:-1]
    dt = datetime.fromisoformat(datetime_utc_iso)

    # ✅ build proper +/- 1 minute timestamps (no minute=-1 bug)
    dt_plus = dt + timedelta(minutes=1)
    dt_minus = dt - timedelta(minutes=1)

    t = _TS.utc(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)
    t_plus = _TS.utc(dt_plus.year, dt_plus.month, dt_plus.day, dt_plus.hour, dt_plus.minute, dt_plus.second)
    t_minus = _TS.utc(dt_minus.year, dt_minus.month, dt_minus.day, dt_minus.hour, dt_minus.minute, dt_minus.second)

    earth = _EPH["earth"]
    observer = earth  # ✅ geocentric confirm

    results = []

    for disp, key in PLANETS:
        body = _EPH[key]
        astrometric = observer.at(t).observe(body).apparent()

        ecl = astrometric.frame_latlon(ecliptic_frame)
        lon = _wrap360(ecl[1].degrees)
        lat_e = float(ecl[0].degrees)
        dist = float(astrometric.distance().au)

        # speed approx (deg/day)
        ecl_p = observer.at(t_plus).observe(body).apparent().frame_latlon(ecliptic_frame)
        ecl_m = observer.at(t_minus).observe(body).apparent().frame_latlon(ecliptic_frame)
        lon_p = _wrap360(ecl_p[1].degrees)
        lon_m = _wrap360(ecl_m[1].degrees)

        d = lon_p - lon_m
        if d > 180: d -= 360
        if d < -180: d += 360

        # (difference over 2 minutes) * 720 minutes/day
        speed_lon = float((d / 2.0) * 720.0)

        results.append({
            "name": disp,
            "lon": lon,
            "lat": lat_e,
            "dist_au": dist,
            "speed_lon": speed_lon,
        })

    jd_ut = float(t.ut1)  # keep as is for now
    return jd_ut, results