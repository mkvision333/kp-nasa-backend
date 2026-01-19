# app/core/nasa_ephemeris.py  ✅ FULL REPLACE
# ✅ Fixes:
# - Robust UTC ISO parsing (handles "Z" and offsets safely)
# - Robust t_plus/t_minus using timedelta (no minute rollover bugs)
# - Keeps planets GEOCENTRIC (earth.at(t)) as you want
# - Uses apparent() + ecliptic_frame (standard astrology-style)
# - Stable speed calculation (deg/day) without affecting lon output

try:
    from skyfield.api import load
except Exception as e:
    print("❌ Skyfield import failed:", e)
    raise

from skyfield.framelib import ecliptic_frame
from datetime import datetime, timezone, timedelta
import math

# Global cache (loads once)
_EPH = None
_TS = None

DE_FILE = "de440s.bsp"

PLANETS = [
    ("Sun", "sun"),
    ("Moon", "moon"),
    ("Mercury", "mercury"),
    ("Venus", "venus"),
    ("Mars", "mars barycenter"),
    ("Jupiter", "jupiter barycenter"),
    ("Saturn", "saturn barycenter"),
    ("Uranus", "uranus barycenter"),
    ("Neptune", "neptune barycenter"),
    ("Pluto", "pluto barycenter"),
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


def _jd_T(jd: float) -> float:
    # Julian centuries from J2000.0
    return (jd - 2451545.0) / 36525.0


def _parse_utc_iso(datetime_utc_iso: str) -> datetime:
    """
    Accepts:
      - "YYYY-MM-DDTHH:MM:SSZ"
      - "YYYY-MM-DDTHH:MM:SS+00:00"
      - or naive string (treated as UTC)
    Returns timezone-aware UTC datetime.
    """
    s = (datetime_utc_iso or "").strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)

    if dt.tzinfo is None:
        # treat as UTC
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    # remove microseconds for consistent reproducibility (optional)
    return dt.replace(microsecond=0)


# ---------------------------------------------------------
# ✅ Lahiri/KP Ayanamsa (Approx, date-based)
# ---------------------------------------------------------
def ayanamsa_lahiri_approx_deg(jd_ut: float) -> float:
    """
    Practical Lahiri-ish ayanamsa approximation.
    Typical value around ~24° in 2025.
    """
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
# ✅ Obliquity of the ecliptic (mean) in degrees (Meeus)
# ---------------------------------------------------------
def mean_obliquity_deg(jd_ut: float) -> float:
    T = _jd_T(jd_ut)
    eps0 = 84381.448 - 46.8150 * T - 0.00059 * (T * T) + 0.001813 * (T * T * T)
    return eps0 / 3600.0


# ---------------------------------------------------------
# ✅ Greenwich mean sidereal time (deg) + local sidereal
# ---------------------------------------------------------
def gmst_deg(jd_ut: float) -> float:
    T = _jd_T(jd_ut)
    gmst = (
        280.46061837
        + 360.98564736629 * (jd_ut - 2451545.0)
        + 0.000387933 * (T * T)
        - (T * T * T) / 38710000.0
    )
    return _wrap360(gmst)


def lst_deg(jd_ut: float, lon_deg_east: float) -> float:
    return _wrap360(gmst_deg(jd_ut) + lon_deg_east)


# ---------------------------------------------------------
# ✅ Ascendant tropical longitude (deg)
# ---------------------------------------------------------
def ascendant_tropical_deg(jd_ut: float, lat_deg: float, lon_deg_east: float) -> float:
    theta = math.radians(lst_deg(jd_ut, lon_deg_east))
    phi = math.radians(lat_deg)
    eps = math.radians(mean_obliquity_deg(jd_ut))

    num = math.sin(theta) * math.cos(eps) - math.tan(phi) * math.sin(eps)
    den = math.cos(theta)
    asc = math.degrees(math.atan2(num, den))
    return _wrap360(asc)


def equal_house_cusps_sidereal(asc_sid_deg: float) -> list:
    return [_wrap360(asc_sid_deg + i * 30.0) for i in range(12)]


def _signed_lon_diff(a: float, b: float) -> float:
    """
    Signed smallest difference a-b in degrees, in [-180, +180]
    """
    d = (a - b) % 360.0
    if d > 180.0:
        d -= 360.0
    return d


# ---------------------------------------------------------
# ✅ Planet positions tropical (Skyfield/JPL) with speed
# ---------------------------------------------------------
def get_planets_ecliptic(datetime_utc_iso: str, lat: float, lng: float):
    """
    Returns ecliptic longitude/latitude for planets as seen from GEOCENTER (Earth center),
    and approx speed in deg/day for longitude (finite difference).
    lat/lng kept for backward compatibility (not used for planets).
    """
    _ensure_loaded()

    dt = _parse_utc_iso(datetime_utc_iso)

    # Create skyfield time safely
    t = _TS.from_datetime(dt)

    earth = _EPH["earth"]
    observer = earth  # ✅ GEOCENTER

    # Speed approx using ±60 seconds (stable, no rollovers)
    dt_plus = dt + timedelta(seconds=60)
    dt_minus = dt - timedelta(seconds=60)
    t_plus = _TS.from_datetime(dt_plus)
    t_minus = _TS.from_datetime(dt_minus)

    results = []

    for disp, key in PLANETS:
        body = _EPH[key]

        # Apparent geocentric position
        ast = observer.at(t).observe(body).apparent()
        ecl = ast.frame_latlon(ecliptic_frame)
        lon = _wrap360(ecl[1].degrees)
        lat_e = float(ecl[0].degrees)
        dist = float(ast.distance().au)

        # Speed (deg/day) using ±60 sec
        ast_p = observer.at(t_plus).observe(body).apparent()
        ast_m = observer.at(t_minus).observe(body).apparent()
        lon_p = _wrap360(ast_p.frame_latlon(ecliptic_frame)[1].degrees)
        lon_m = _wrap360(ast_m.frame_latlon(ecliptic_frame)[1].degrees)

        # delta over 120 seconds
        d = _signed_lon_diff(lon_p, lon_m)  # degrees over 120 sec
        # Convert to deg/day: (deg / 120sec) * 86400sec/day
        speed_lon = float(d * (86400.0 / 120.0))

        results.append(
            {
                "name": disp,
                "lon": float(lon),
                "lat": lat_e,
                "dist_au": dist,
                "speed_lon": speed_lon,
            }
        )

    # JD-UT (use UT1 close to UT; stable for your Meeus formulas)
    jd_ut = float(t.ut1)
    return jd_ut, results
