# app/core/nasa_ephemeris.py  ✅ FULL REPLACE
# ✅ Fix: use PLANET CENTERS (not system barycenters) to match astrology-grade ephemerides
# ✅ Keeps: Skyfield + DE440s + geocentric apparent ecliptic lon/lat
# ✅ Improves: robust time parsing (microseconds) + speed calc using timedelta

try:
    from skyfield.api import load
except Exception as e:
    print("❌ Skyfield import failed:", e)
    raise

from skyfield.framelib import ecliptic_frame
from datetime import datetime, timedelta, timezone
import math

# Global cache (loads once)
_EPH = None
_TS = None

DE_FILE = "de440s.bsp"

# ✅ IMPORTANT:
# Use planet centers (matches what astrologers expect).
# (Barycenters can differ by arcminutes for Jupiter/Saturn etc because of satellites.)
PLANETS = [
    ("Sun", "sun"),
    ("Moon", "moon"),
    ("Mercury", "mercury"),
    ("Venus", "venus"),
    ("Mars", "mars"),         # ✅ planet center
    ("Jupiter", "jupiter"),   # ✅ planet center
    ("Saturn", "saturn"),     # ✅ planet center
    ("Uranus", "uranus"),     # ✅ planet center
    ("Neptune", "neptune"),   # ✅ planet center
    ("Pluto", "pluto"),       # ✅ planet center (DE440s supports this key)
]


def _ensure_loaded():
    global _EPH, _TS
    if _TS is None:
        _TS = load.timescale()
    if _EPH is None:
        _EPH = load(DE_FILE)


def _wrap360(x: float) -> float:
    x = float(x) % 360.0
    return x if x >= 0 else x + 360.0


def _parse_utc_iso(s: str) -> datetime:
    """
    Accepts:
      - 'YYYY-MM-DDTHH:MM:SSZ'
      - with optional fractional seconds
      - with optional timezone offset
    Returns timezone-aware UTC datetime.
    """
    s = (s or "").strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        # assume UTC if no tz provided
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def get_planets_ecliptic(datetime_utc_iso: str, lat: float, lng: float):
    """
    Returns:
      jd_ut, planets[]
    planets[] item:
      { name, lon, lat, dist_au, speed_lon }
    lon/lat are apparent geocentric ecliptic longitude/latitude of date (degrees).
    speed_lon is approx deg/day (finite difference ±60s).
    """
    _ensure_loaded()

    dt = _parse_utc_iso(datetime_utc_iso)

    # Skyfield time (supports microseconds)
    sec = dt.second + dt.microsecond / 1_000_000.0
    t = _TS.utc(dt.year, dt.month, dt.day, dt.hour, dt.minute, sec)

    # speed approx: lon(t+60s) - lon(t-60s) scaled to deg/day
    dt_plus = dt + timedelta(seconds=60)
    dt_minus = dt - timedelta(seconds=60)

    sec_p = dt_plus.second + dt_plus.microsecond / 1_000_000.0
    sec_m = dt_minus.second + dt_minus.microsecond / 1_000_000.0

    t_plus = _TS.utc(dt_plus.year, dt_plus.month, dt_plus.day, dt_plus.hour, dt_plus.minute, sec_p)
    t_minus = _TS.utc(dt_minus.year, dt_minus.month, dt_minus.day, dt_minus.hour, dt_minus.minute, sec_m)

    earth = _EPH["earth"]
    observer = earth  # geocentric

    results = []

    for disp, key in PLANETS:
        body = _EPH[key]

        # apparent() includes light-time + aberration (typical "apparent geocentric")
        ast = observer.at(t).observe(body).apparent()
        ecl = ast.frame_latlon(ecliptic_frame)

        lon = _wrap360(ecl[1].degrees)
        lat_e = float(ecl[0].degrees)
        dist = float(ast.distance().au)

        # finite difference for speed
        ast_p = observer.at(t_plus).observe(body).apparent()
        ast_m = observer.at(t_minus).observe(body).apparent()

        ecl_p = ast_p.frame_latlon(ecliptic_frame)
        ecl_m = ast_m.frame_latlon(ecliptic_frame)

        lon_p = _wrap360(ecl_p[1].degrees)
        lon_m = _wrap360(ecl_m[1].degrees)

        d = lon_p - lon_m
        if d > 180:
            d -= 360
        if d < -180:
            d += 360

        # (difference over 120 seconds) -> deg/day
        speed_lon = float((d / 120.0) * 86400.0)

        results.append(
            {
                "name": disp,
                "lon": float(lon),
                "lat": float(lat_e),
                "dist_au": float(dist),
                "speed_lon": float(speed_lon),
            }
        )

    # JD-UT (Skyfield provides multiple scales; UT1 is OK for "jd_ut" label)
    # If you use jd for precession/nutation formulas, TT is often preferred,
    # but this function is primarily for planet longitudes.
    jd_ut = float(t.ut1)
    return jd_ut, results


# ---------------------------------------------------------
# Keep your other helper functions below as-is if they exist:
# ayanamsa_lahiri_approx_deg()
# mean_lunar_node_tropical_deg()
# etc.
# ---------------------------------------------------------

def _jd_T(jd: float) -> float:
    # Julian centuries from J2000.0
    return (jd - 2451545.0) / 36525.0


def ayanamsa_lahiri_approx_deg(jd_ut: float) -> float:
    """
    Practical Lahiri-ish ayanamsa approximation.
    (You already had this; keeping it unchanged.)
    """
    T = _jd_T(jd_ut)
    years = T * 100.0
    rate_deg_per_year = 50.290966 / 3600.0
    ay = 23.85675 + (years * rate_deg_per_year)
    return _wrap360(ay)


def mean_lunar_node_tropical_deg(jd_ut: float) -> float:
    T = _jd_T(jd_ut)
    Om = (
        125.04452
        - 1934.136261 * T
        + 0.0020708 * (T * T)
        + (T * T * T) / 450000.0
    )
    return _wrap360(Om)
