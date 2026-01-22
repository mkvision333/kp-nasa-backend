# app/core/panchangam_calc.py ✅ FULL REPLACE
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Tuple, Callable
from zoneinfo import ZoneInfo
import math
import time

from skyfield.api import load, wgs84
from skyfield import almanac

from app.core.nasa_ephemeris import get_planets_ecliptic

STAR_SPAN = 360.0 / 27.0  # 13°20'
TITHI_SPAN = 12.0
KARANA_SPAN = 6.0

VAARA_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

TITHI_NAMES = [
    "Shukla Pratipada","Shukla Dwitiya","Shukla Tritiya","Shukla Chaturthi","Shukla Panchami",
    "Shukla Shashthi","Shukla Saptami","Shukla Ashtami","Shukla Navami","Shukla Dashami",
    "Shukla Ekadashi","Shukla Dwadashi","Shukla Trayodashi","Shukla Chaturdashi","Purnima",
    "Krishna Pratipada","Krishna Dwitiya","Krishna Tritiya","Krishna Chaturthi","Krishna Panchami",
    "Krishna Shashthi","Krishna Saptami","Krishna Ashtami","Krishna Navami","Krishna Dashami",
    "Krishna Ekadashi","Krishna Dwadashi","Krishna Trayodashi","Krishna Chaturdashi","Amavasya",
]

NAKSHATRA_NAMES = [
    "Ashwini","Bharani","Krittika","Rohini","Mrigashira","Ardra","Punarvasu","Pushya","Ashlesha",
    "Magha","Purva Phalguni","Uttara Phalguni","Hasta","Chitra","Swati","Vishakha","Anuradha","Jyeshtha",
    "Mula","Purva Ashadha","Uttara Ashadha","Shravana","Dhanishta","Shatabhisha",
    "Purva Bhadrapada","Uttara Bhadrapada","Revati",
]

YOGA_NAMES = [
    "Vishkumbha","Priti","Ayushman","Saubhagya","Shobhana","Atiganda","Sukarman","Dhriti","Shoola",
    "Ganda","Vriddhi","Dhruva","Vyaghata","Harshana","Vajra","Siddhi","Vyatipata","Variyana",
    "Parigha","Shiva","Siddha","Sadhya","Shubha","Shukla","Brahma","Indra","Vaidhriti",
]

SPECIAL_LAST = ["Shakuni", "Chatushpada", "Naga"]

# ----------------- Skyfield cache -----------------
_TS = None
_EPH = None

def _sf_loaded():
    global _TS, _EPH
    if _TS is None:
        _TS = load.timescale()
    if _EPH is None:
        _EPH = load("de440s.bsp")
    return _TS, _EPH

# ----------------- Panchangam result cache -----------------
_PANCH_CACHE: Dict[str, Dict[str, Any]] = {}
_PANCH_TTL_SEC = 6 * 60 * 60  # 6 hours

def _panch_key(datetimeLocal: str, tz: str, lat: float, lon: float, ayan_deg: float) -> str:
    # cache per local date
    try:
        d = datetime.fromisoformat(datetimeLocal).date()
    except Exception:
        d = datetime.now().date()
    return f"{d.isoformat()}|{tz}|{float(lat):.4f}|{float(lon):.4f}|{float(ayan_deg):.4f}"

def _panch_cache_get(key: str):
    v = _PANCH_CACHE.get(key)
    if not v:
        return None
    if (time.time() - float(v.get("_ts", 0))) > _PANCH_TTL_SEC:
        _PANCH_CACHE.pop(key, None)
        return None
    return v.get("data")

def _panch_cache_set(key: str, data: Dict[str, Any]):
    _PANCH_CACHE[key] = {"_ts": time.time(), "data": data}

# ----------------- Helpers -----------------
def wrap360(x: float) -> float:
    x = float(x) % 360.0
    return x if x >= 0 else x + 360.0

def fmt_local(dt_local: datetime) -> str:
    return dt_local.strftime("%Y-%m-%d %H:%M")

def fmt_hm(dt_local: datetime) -> str:
    return dt_local.strftime("%H:%M")

def _fmt_span(zone: ZoneInfo, a_utc: datetime, b_utc: datetime) -> Dict[str, str]:
    a = a_utc.astimezone(zone)
    b = b_utc.astimezone(zone)
    return {"start": fmt_hm(a), "end": fmt_hm(b)}

# indices are 1..8 segments in daytime
_RAHU_IDX = {"Sunday": 8, "Monday": 2, "Tuesday": 7, "Wednesday": 5, "Thursday": 6, "Friday": 4, "Saturday": 3}
_YAMA_IDX = {"Sunday": 6, "Monday": 5, "Tuesday": 4, "Wednesday": 3, "Thursday": 2, "Friday": 1, "Saturday": 7}
_GULI_IDX = {"Sunday": 7, "Monday": 6, "Tuesday": 5, "Wednesday": 4, "Thursday": 3, "Friday": 2, "Saturday": 1}

def _kala_segment(sunrise_utc: datetime, sunset_utc: datetime, seg_index_1to8: int) -> Tuple[datetime, datetime]:
    day_len = (sunset_utc - sunrise_utc)
    part = day_len / 8
    a = sunrise_utc + part * (seg_index_1to8 - 1)
    b = a + part
    return a, b

def _abhijit(sunrise_utc: datetime, sunset_utc: datetime) -> Tuple[datetime, datetime]:
    # Practical Abhijit: around mid-day; use 1/15 of day length
    mid = sunrise_utc + (sunset_utc - sunrise_utc) / 2
    span = (sunset_utc - sunrise_utc) / 15
    return mid - span / 2, mid + span / 2

def _sunrise_sunset_nextsunrise_utc(
    lat: float, lon: float, day_local_date: datetime, tz: str
) -> Tuple[datetime, datetime, datetime]:
    """
    Returns (sunrise_utc, sunset_utc, next_sunrise_utc) for the given local date.
    """
    zone = ZoneInfo(tz)

    local_midnight = datetime(day_local_date.year, day_local_date.month, day_local_date.day, 0, 0, 0, tzinfo=zone)
    t0_utc = local_midnight.astimezone(timezone.utc)
    t1_utc = (local_midnight + timedelta(days=2)).astimezone(timezone.utc)

    ts, eph = _sf_loaded()

    topos = wgs84.latlon(latitude_degrees=float(lat), longitude_degrees=float(lon))
    f = almanac.sunrise_sunset(eph, topos)

    t0 = ts.from_datetime(t0_utc)
    t1 = ts.from_datetime(t1_utc)

    times, events = almanac.find_discrete(t0, t1, f)

    sunrise_list = []
    sunset_list = []
    for ti, ev in zip(times, events):
        dt = ti.utc_datetime().replace(tzinfo=timezone.utc)
        if bool(ev) is True:
            sunrise_list.append(dt)
        else:
            sunset_list.append(dt)

    # fallback
    if len(sunrise_list) < 2 or len(sunset_list) < 1:
        approx_sunrise = local_midnight.replace(hour=6).astimezone(timezone.utc)
        approx_sunset = local_midnight.replace(hour=18).astimezone(timezone.utc)
        approx_next = (local_midnight + timedelta(days=1)).replace(hour=6).astimezone(timezone.utc)
        return approx_sunrise, approx_sunset, approx_next

    target_date = local_midnight.date()

    sunrise_today = None
    next_sunrise = None
    for i in range(len(sunrise_list) - 1):
        a_loc = sunrise_list[i].astimezone(zone)
        if a_loc.date() == target_date:
            sunrise_today = sunrise_list[i]
            next_sunrise = sunrise_list[i + 1]
            break
    if sunrise_today is None:
        sunrise_today, next_sunrise = sunrise_list[0], sunrise_list[1]

    sunset_today = None
    for s in sunset_list:
        s_loc = s.astimezone(zone)
        if s_loc.date() == target_date:
            sunset_today = s
            break
    if sunset_today is None:
        # first sunset after sunrise
        for s in sunset_list:
            if s > sunrise_today:
                sunset_today = s
                break
    if sunset_today is None:
        sunset_today = sunrise_today + timedelta(hours=12)

    return sunrise_today, sunset_today, next_sunrise

def _sun_moon_sid_at(dt_utc: datetime, lat: float, lon: float, ayan_deg: float) -> Tuple[float, float]:
    """
    Uses get_planets_ecliptic() tropical lon and converts to sidereal by subtracting ayan_deg.
    """
    utc_iso = dt_utc.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    _, planets = get_planets_ecliptic(utc_iso, float(lat), float(lon))

    sun_t = None
    moon_t = None
    for p in planets:
        nm = str(p.get("name", "")).lower()
        if nm == "sun":
            sun_t = float(p.get("lon", 0.0))
        elif nm == "moon":
            moon_t = float(p.get("lon", 0.0))

    if sun_t is None or moon_t is None:
        # fallback
        sun_t = float(planets[0]["lon"])
        moon_t = float(planets[1]["lon"])

    sun_s = wrap360(sun_t - float(ayan_deg))
    moon_s = wrap360(moon_t - float(ayan_deg))
    return sun_s, moon_s

def _unwrap_near(x: float, x0: float) -> float:
    d = x - x0
    if d < -180:
        return x + 360.0
    if d > 180:
        return x - 360.0
    return x

def _bin_search_time(
    fn: Callable[[datetime], float],
    target: float,
    t0: datetime,
    t1: datetime,
    iters: int = 44,
) -> datetime:
    a = t0
    b = t1
    fa0 = fn(a)
    fb0 = fn(b)
    if not ((fa0 <= target <= fb0) or (fb0 <= target <= fa0)):
        return b

    for _ in range(iters):
        mid = a + (b - a) / 2
        fm = fn(mid)
        if fm < target:
            a = mid
        else:
            b = mid
    return b

# ----------------- Main -----------------
def compute_panchangam(datetimeLocal: str, tz: str, lat: float, lon: float, ayan_deg: float) -> Dict[str, Any]:
    key = _panch_key(datetimeLocal, tz, float(lat), float(lon), float(ayan_deg))
    hit = _panch_cache_get(key)
    if hit:
        return hit

    zone = ZoneInfo(tz)

    # datetimeLocal must be local-naive like "2026-01-26T12:00:00"
    dt_local = datetime.fromisoformat(datetimeLocal).replace(tzinfo=zone)

    sunrise_utc, sunset_utc, next_sunrise_utc = _sunrise_sunset_nextsunrise_utc(lat, lon, dt_local, tz)
    sunrise_local = sunrise_utc.astimezone(zone)
    sunset_local = sunset_utc.astimezone(zone)
    next_sunrise_local = next_sunrise_utc.astimezone(zone)

    vaara = VAARA_EN[sunrise_local.weekday()]

    # kaala blocks
    rahu_a, rahu_b = _kala_segment(sunrise_utc, sunset_utc, _RAHU_IDX.get(vaara, 2))
    yama_a, yama_b = _kala_segment(sunrise_utc, sunset_utc, _YAMA_IDX.get(vaara, 5))
    guli_a, guli_b = _kala_segment(sunrise_utc, sunset_utc, _GULI_IDX.get(vaara, 6))
    abhi_a, abhi_b = _abhijit(sunrise_utc, sunset_utc)

    sun0, moon0 = _sun_moon_sid_at(sunrise_utc, lat, lon, ayan_deg)

    d0 = wrap360(moon0 - sun0)
    y0 = wrap360(moon0 + sun0)

    def delta_unwrapped(t_utc: datetime) -> float:
        s, m = _sun_moon_sid_at(t_utc, lat, lon, ayan_deg)
        d = wrap360(m - s)
        return _unwrap_near(d, d0)

    def moon_unwrapped(t_utc: datetime) -> float:
        _, m = _sun_moon_sid_at(t_utc, lat, lon, ayan_deg)
        return _unwrap_near(wrap360(m), moon0)

    def yoga_unwrapped(t_utc: datetime) -> float:
        s, m = _sun_moon_sid_at(t_utc, lat, lon, ayan_deg)
        y = wrap360(m + s)
        return _unwrap_near(y, y0)

    # ---- TITHI ----
    tithi_idx = int(math.floor(d0 / TITHI_SPAN)) + 1
    tithi_name = TITHI_NAMES[(tithi_idx - 1) % 30]
    tithi_target = (math.floor(d0 / TITHI_SPAN) + 1) * TITHI_SPAN
    tithi_end_utc = _bin_search_time(delta_unwrapped, tithi_target, sunrise_utc, next_sunrise_utc)
    tithi_end_local = tithi_end_utc.astimezone(zone)

    paksha = "Shukla" if 1 <= tithi_idx <= 15 else "Krishna"

    # ---- NAKSHATRA + PADA ----
    nak_idx = int(math.floor(moon0 / STAR_SPAN)) + 1
    nak_name = NAKSHATRA_NAMES[(nak_idx - 1) % 27]
    in_star = moon0 - math.floor(moon0 / STAR_SPAN) * STAR_SPAN
    pada = int(math.floor(in_star / (STAR_SPAN / 4.0))) + 1
    nak_target = (math.floor(moon0 / STAR_SPAN) + 1) * STAR_SPAN
    nak_end_utc = _bin_search_time(moon_unwrapped, nak_target, sunrise_utc, next_sunrise_utc)
    nak_end_local = nak_end_utc.astimezone(zone)

    # ---- YOGA ----
    yoga_idx = int(math.floor(y0 / STAR_SPAN)) + 1
    yoga_name = YOGA_NAMES[(yoga_idx - 1) % 27]
    yoga_target = (math.floor(y0 / STAR_SPAN) + 1) * STAR_SPAN
    yoga_end_utc = _bin_search_time(yoga_unwrapped, yoga_target, sunrise_utc, next_sunrise_utc)
    yoga_end_local = yoga_end_utc.astimezone(zone)

    # ---- KARANA ----
    kar_idx = int(math.floor(d0 / KARANA_SPAN)) + 1
    if kar_idx == 1:
        kar_name = "Kimstughna"
    elif kar_idx >= 58:
        kar_name = SPECIAL_LAST[kar_idx - 58]
    else:
        rep = ["Bava","Balava","Kaulava","Taitila","Garaja","Vanija","Vishti"]
        kar_name = rep[(kar_idx - 2) % 7]
    kar_target = (math.floor(d0 / KARANA_SPAN) + 1) * KARANA_SPAN
    kar_end_utc = _bin_search_time(delta_unwrapped, kar_target, sunrise_utc, next_sunrise_utc)
    kar_end_local = kar_end_utc.astimezone(zone)

    out: Dict[str, Any] = {
        "sunrise_local": fmt_local(sunrise_local),
        "sunset_local": fmt_local(sunset_local),
        "next_sunrise_local": fmt_local(next_sunrise_local),
        "vaara": vaara,

        "paksha": paksha,

        "rahu_kalam": _fmt_span(zone, rahu_a, rahu_b),
        "yamaganda": _fmt_span(zone, yama_a, yama_b),
        "gulika": _fmt_span(zone, guli_a, guli_b),
        "abhijit": _fmt_span(zone, abhi_a, abhi_b),

        "tithi": {"name": tithi_name, "end_local": fmt_local(tithi_end_local), "end_hms": fmt_hm(tithi_end_local)},
        "nakshatra": {
            "name": nak_name,
            "extra": f"Pada {pada}",
            "end_local": fmt_local(nak_end_local),
            "end_hms": fmt_hm(nak_end_local),
        },
        "yoga": {"name": yoga_name, "end_local": fmt_local(yoga_end_local), "end_hms": fmt_hm(yoga_end_local)},
        "karana": {"name": kar_name, "end_local": fmt_local(kar_end_local), "end_hms": fmt_hm(kar_end_local)},
    }

    _panch_cache_set(key, out)
    return out
