from skyfield.api import load
from skyfield.framelib import ecliptic_frame
from datetime import datetime
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


# ---------------------------------------------------------
# ✅ Lahiri/KP Ayanamsa (Approx, date-based)
# NOTE: This is a practical approximation.
# Later we can calibrate by comparing with your old KP backend.
# ---------------------------------------------------------
def ayanamsa_lahiri_approx_deg(jd_ut: float) -> float:
    """
    Practical Lahiri-ish ayanamsa approximation.
    Typical value around ~24° in 2025.
    """
    T = _jd_T(jd_ut)
    # Base Lahiri at J2000 (approx): 23.85675°
    # Precession rate approx: 50.290966 arcsec/year
    years = T * 100.0
    rate_deg_per_year = 50.290966 / 3600.0
    ay = 23.85675 + (years * rate_deg_per_year)
    return _wrap360(ay)


# ---------------------------------------------------------
# ✅ Mean Lunar Node (Rahu) tropical longitude (Meeus)
# ---------------------------------------------------------
def mean_lunar_node_tropical_deg(jd_ut: float) -> float:
    T = _jd_T(jd_ut)
    # Ω = 125.04452 - 1934.136261*T + 0.0020708*T^2 + T^3/450000
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
    # seconds
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
# Formula:
# asc = atan2( sin(θ)*cosε - tanφ*sinε, cosθ )
# where θ=LST, φ=lat, ε=obliquity
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
    # 12 cusps (equal houses): 1st = asc, then +30°
    return [_wrap360(asc_sid_deg + i * 30.0) for i in range(12)]


# ---------------------------------------------------------
# ✅ Planet positions tropical (NASA) with speed
# ---------------------------------------------------------
def get_planets_ecliptic(datetime_utc_iso: str, lat: float, lng: float):
    """
    Returns ecliptic longitude/latitude for planets as seen from geocenter (Earth center),
    and approx speed in deg/day for longitude (finite difference).
    """
    _ensure_loaded()

    # Parse UTC ISO "YYYY-MM-DDTHH:MM:SSZ"
    if datetime_utc_iso.endswith("Z"):
        datetime_utc_iso = datetime_utc_iso[:-1]
    dt = datetime.fromisoformat(datetime_utc_iso)

    t = _TS.utc(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)

    earth = _EPH["earth"]
    observer = earth  # geocentric

    results = []

    # Speed approx: longitude(t+1min) - longitude(t-1min) scaled to deg/day
    t_plus = _TS.utc(dt.year, dt.month, dt.day, dt.hour, dt.minute + 1, dt.second)
    t_minus = _TS.utc(dt.year, dt.month, dt.day, dt.hour, dt.minute - 1, dt.second)

    for disp, key in PLANETS:
        body = _EPH[key]
        astrometric = observer.at(t).observe(body).apparent()

        # Ecliptic position
        ecl = astrometric.frame_latlon(ecliptic_frame)
        lon = _wrap360(ecl[1].degrees)
        lat_e = float(ecl[0].degrees)
        dist = float(astrometric.distance().au)

        # speed approx in deg/day
        ecl_p = observer.at(t_plus).observe(body).apparent().frame_latlon(ecliptic_frame)
        ecl_m = observer.at(t_minus).observe(body).apparent().frame_latlon(ecliptic_frame)
        lon_p = _wrap360(ecl_p[1].degrees)
        lon_m = _wrap360(ecl_m[1].degrees)

        d = lon_p - lon_m
        if d > 180:
            d -= 360
        if d < -180:
            d += 360

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

    # JD-UT from Skyfield
    jd_ut = float(t.ut1)  # ok for astrology pipelines
    return jd_ut, results
