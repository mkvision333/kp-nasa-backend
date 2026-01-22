from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Tuple, Callable, List, Optional
from zoneinfo import ZoneInfo
import math
import time

from skyfield.api import load, wgs84
from skyfield import almanac

from app.core.nasa_ephemeris import get_planets_ecliptic

STAR_SPAN = 360.0 / 27.0
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

# ✅ Lunar month names (Amanta, common in South India/Telangana)
# Mapping based on Sun's sidereal rashi at AMAVASYA:
# Pisces->Chaitra, Aries->Vaisakha ... Aquarius->Phalguna
LUNAR_MONTH_BY_SUN_RASHI = {
    11: "Chaitra",     # Pisces
    0:  "Vaisakha",    # Aries
    1:  "Jyeshtha",    # Taurus
    2:  "Ashadha",     # Gemini
    3:  "Shravana",    # Cancer
    4:  "Bhadrapada",  # Leo
    5:  "Ashwin",      # Virgo
    6:  "Kartika",     # Libra
    7:  "Margashirsha",# Scorpio
    8:  "Pausha",      # Sagittarius
    9:  "Magha",       # Capricorn
    10: "Phalguna",    # Aquarius
}

# ✅ 60 Samvatsara list (standard 60-year cycle)
SAMVATSARA_60 = [
    "Prabhava","Vibhava","Shukla","Pramoda","Prajapati","Angirasa","Shrimukha","Bhava","Yuva","Dhata",
    "Ishvara","Bahudhanya","Pramathi","Vikrama","Vrisha","Chitrabhanu","Svabhanu","Tarana","Parthiva","Vyaya",
    "Sarvajit","Sarvadhari","Virodhi","Vikruti","Khara","Nandana","Vijaya","Jaya","Manmatha","Durmukhi",
    "Hemalambi","Vilambi","Vikari","Sharvari","Plava","Shubhakritu","Shobhakritu","Krodhi","Vishvavasu","Parabhava",
    "Plavanga","Kilaka","Saumya","Sadharana","Virodhikritu","Paridhavi","Pramadicha","Ananda","Rakshasa","Nala",
    "Pingala","Kalayukti","Siddharthi","Raudra","Durmati","Dundubhi","Rudhirodgari","Raktakshi","Krodhana","Akshaya"
]

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

# ----------------- Result cache -----------------
_PANCH_CACHE: Dict[str, Dict[str, Any]] = {}
_PANCH_TTL_SEC = 6 * 60 * 60  # 6 hours

def _panch_key(datetimeLocal: str, tz: str, lat: float, lon: float, ayan_deg: float) -> str:
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
    mid = sunrise_utc + (sunset_utc - sunrise_utc) / 2
    span = (sunset_utc - sunrise_utc) / 15
    return mid - span / 2, mid + span / 2

def _sunrise_sunset_nextsunrise_utc(
    lat: float, lon: float, day_local_date: datetime, tz: str
) -> Tuple[datetime, datetime, datetime]:
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
        for s in sunset_list:
            if s > sunrise_today:
                sunset_today = s
                break
    if sunset_today is None:
        sunset_today = sunrise_today + timedelta(hours=12)

    return sunrise_today, sunset_today, next_sunrise

def _sun_moon_sid_at(dt_utc: datetime, lat: float, lon: float, ayan_deg: float) -> Tuple[float, float]:
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
        sun_t = float(planets[0]["lon"])
        moon_t = float(planets[1]["lon"])

    sun_s = wrap360(sun_t - float(ayan_deg))
    moon_s = wrap360(moon_t - float(ayan_deg))
    return sun_s, moon_s

def _sun_sid_lon(dt_utc: datetime, lat: float, lon: float, ayan_deg: float) -> float:
    utc_iso = dt_utc.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    _, planets = get_planets_ecliptic(utc_iso, float(lat), float(lon))
    for p in planets:
        if str(p.get("name", "")).lower() == "sun":
            return wrap360(float(p.get("lon", 0.0)) - float(ayan_deg))
    return 0.0

def _unwrap_near(x: float, x0: float) -> float:
    d = x - x0
    if d < -180: return x + 360.0
    if d > 180: return x - 360.0
    return x

def _bin_search_time(fn: Callable[[datetime], float], target: float, t0: datetime, t1: datetime, iters: int = 44) -> datetime:
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

def _approx_shaka_year(dt_local: datetime) -> int:
    y = dt_local.year
    if (dt_local.month > 3) or (dt_local.month == 3 and dt_local.day >= 22):
        return y - 78
    return y - 79

def _approx_vikrama_year(dt_local: datetime) -> int:
    y = dt_local.year
    if (dt_local.month > 4) or (dt_local.month == 4 and dt_local.day >= 14):
        return y + 57
    return y + 56

def _samvatsara_from_vikrama(vikrama_year: int) -> str:
    idx = (vikrama_year - 1) % 60
    return SAMVATSARA_60[idx]

def _ayanam_from_sun_rashi(sun_rashi: int) -> str:
    # Uttarayana: Makara..Mithuna (Capricorn..Gemini)
    # indices: Capricorn9 Aquarius10 Pisces11 Aries0 Taurus1 Gemini2
    return "Uttarayana" if sun_rashi in (9, 10, 11, 0, 1, 2) else "Dakshinayana"

def _ritu_from_sun_rashi(sun_rashi: int) -> str:
    # Solar ritu mapping (common practical)
    if sun_rashi in (0, 1):  # Aries, Taurus
        return "Vasanta"
    if sun_rashi in (2, 3):  # Gemini, Cancer
        return "Grishma"
    if sun_rashi in (4, 5):  # Leo, Virgo
        return "Varsha"
    if sun_rashi in (6, 7):  # Libra, Scorpio
        return "Sharad"
    if sun_rashi in (8, 9):  # Sagittarius, Capricorn
        return "Hemanta"
    return "Shishira"        # Aquarius, Pisces

# ---------- Amavasya finder (for Adhika/Kshaya + lunar month name) ----------
def _phase_unwrapped(dt_utc: datetime, lat: float, lon: float, ayan_deg: float, ref: float) -> float:
    s, m = _sun_moon_sid_at(dt_utc, lat, lon, ayan_deg)
    d = wrap360(m - s)  # 0..360
    return _unwrap_near(d, ref)

def _find_prev_next_amavasya(sunrise_utc: datetime, lat: float, lon: float, ayan_deg: float) -> Tuple[datetime, datetime]:
    """
    Finds previous and next Amavasya around sunrise_utc.
    We scan ~40 days window and detect crossings of 0° phase (multiples of 360 in unwrapped phase).
    """
    start = sunrise_utc - timedelta(days=40)
    end = sunrise_utc + timedelta(days=40)

    step = timedelta(hours=6)

    # initialize ref
    s0, m0 = _sun_moon_sid_at(start, lat, lon, ayan_deg)
    ref = wrap360(m0 - s0)  # 0..360
    prev_t = start
    prev_u = ref

    crossings: List[datetime] = []

    t = start + step
    while t <= end:
        u = _phase_unwrapped(t, lat, lon, ayan_deg, prev_u)

        # Detect if we crossed an exact multiple of 360 (Amavasya) between prev_u and u
        # We look for boundary at k*360 near the interval.
        lo = min(prev_u, u)
        hi = max(prev_u, u)
        k0 = math.floor(lo / 360.0)
        k1 = math.floor(hi / 360.0)

        if k1 != k0:
            # We crossed at least one multiple
            for k in range(int(k0) + 1, int(k1) + 1):
                target = 360.0 * k

                def fn(tt: datetime) -> float:
                    return _phase_unwrapped(tt, lat, lon, ayan_deg, prev_u)

                tt = _bin_search_time(fn, target, prev_t, t)
                crossings.append(tt)

        prev_t = t
        prev_u = u
        t += step

    # pick prev/next around sunrise
    crossings = sorted(crossings)
    prev_am = None
    next_am = None
    for c in crossings:
        if c <= sunrise_utc:
            prev_am = c
        elif c > sunrise_utc and next_am is None:
            next_am = c
            break

    # fallback (rare): if not found, approximate
    if prev_am is None:
        prev_am = sunrise_utc - timedelta(days=15)
    if next_am is None:
        next_am = sunrise_utc + timedelta(days=15)

    return prev_am, next_am

def _sun_rashi_at(dt_utc: datetime, lat: float, lon: float, ayan_deg: float) -> int:
    sun_lon = _sun_sid_lon(dt_utc, lat, lon, ayan_deg)
    return int(math.floor(sun_lon / 30.0)) % 12

def _normalize_rashi_jump(a: int, b: int) -> int:
    """Return forward jump count from a to b in modulo-12 (0..11)."""
    return (b - a) % 12

# ----------------- Main compute -----------------
def compute_panchangam(datetimeLocal: str, tz: str, lat: float, lon: float, ayan_deg: float) -> Dict[str, Any]:
    key = _panch_key(datetimeLocal, tz, float(lat), float(lon), float(ayan_deg))
    hit = _panch_cache_get(key)
    if hit:
        return hit

    zone = ZoneInfo(tz)
    dt_local = datetime.fromisoformat(datetimeLocal).replace(tzinfo=zone)

    sunrise_utc, sunset_utc, _next_sunrise_utc = _sunrise_sunset_nextsunrise_utc(lat, lon, dt_local, tz)
    sunrise_local = sunrise_utc.astimezone(zone)
    sunset_local = sunset_utc.astimezone(zone)

    vaara = VAARA_EN[sunrise_local.weekday()]

    # Kala blocks
    rahu_a, rahu_b = _kala_segment(sunrise_utc, sunset_utc, _RAHU_IDX.get(vaara, 2))
    yama_a, yama_b = _kala_segment(sunrise_utc, sunset_utc, _YAMA_IDX.get(vaara, 5))
    guli_a, guli_b = _kala_segment(sunrise_utc, sunset_utc, _GULI_IDX.get(vaara, 6))
    abhi_a, abhi_b = _abhijit(sunrise_utc, sunset_utc)

    # Sun/Moon at sunrise
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

    # ---- Tithi ----
    tithi_idx = int(math.floor(d0 / TITHI_SPAN)) + 1
    tithi_name = TITHI_NAMES[(tithi_idx - 1) % 30]
    tithi_target = (math.floor(d0 / TITHI_SPAN) + 1) * TITHI_SPAN
    tithi_end_utc = _bin_search_time(delta_unwrapped, tithi_target, sunrise_utc, sunrise_utc + timedelta(days=1))
    tithi_end_local = tithi_end_utc.astimezone(zone)

    paksha = "Shukla" if 1 <= tithi_idx <= 15 else "Krishna"

    # ---- Nakshatra (NO Pada in output) ----
    nak_idx = int(math.floor(moon0 / STAR_SPAN)) + 1
    nak_name = NAKSHATRA_NAMES[(nak_idx - 1) % 27]
    nak_target = (math.floor(moon0 / STAR_SPAN) + 1) * STAR_SPAN
    nak_end_utc = _bin_search_time(moon_unwrapped, nak_target, sunrise_utc, sunrise_utc + timedelta(days=1))
    nak_end_local = nak_end_utc.astimezone(zone)

    # ---- Yoga ----
    yoga_idx = int(math.floor(y0 / STAR_SPAN)) + 1
    yoga_name = YOGA_NAMES[(yoga_idx - 1) % 27]
    yoga_target = (math.floor(y0 / STAR_SPAN) + 1) * STAR_SPAN
    yoga_end_utc = _bin_search_time(yoga_unwrapped, yoga_target, sunrise_utc, sunrise_utc + timedelta(days=1))
    yoga_end_local = yoga_end_utc.astimezone(zone)

    # ---- Karana ----
    kar_idx = int(math.floor(d0 / KARANA_SPAN)) + 1
    if kar_idx == 1:
        kar_name = "Kimstughna"
    elif kar_idx >= 58:
        kar_name = SPECIAL_LAST[kar_idx - 58]
    else:
        rep = ["Bava","Balava","Kaulava","Taitila","Garaja","Vanija","Vishti"]
        kar_name = rep[(kar_idx - 2) % 7]
    kar_target = (math.floor(d0 / KARANA_SPAN) + 1) * KARANA_SPAN
    kar_end_utc = _bin_search_time(delta_unwrapped, kar_target, sunrise_utc, sunrise_utc + timedelta(days=1))
    kar_end_local = kar_end_utc.astimezone(zone)

    # ---- Ritu + Ayana (solar, based on Sun sidereal rashi at sunrise) ----
    sun_rashi_today = _sun_rashi_at(sunrise_utc, lat, lon, ayan_deg)
    ritu = _ritu_from_sun_rashi(sun_rashi_today)
    ayana = _ayanam_from_sun_rashi(sun_rashi_today)

    # ---- Lunar Masa + Adhika/Kshaya (using Amavasya & Sun rashi) ----
    prev_am, next_am = _find_prev_next_amavasya(sunrise_utc, lat, lon, ayan_deg)
    sun_rashi_prev_am = _sun_rashi_at(prev_am, lat, lon, ayan_deg)
    sun_rashi_next_am = _sun_rashi_at(next_am, lat, lon, ayan_deg)

    masa_name = LUNAR_MONTH_BY_SUN_RASHI.get(sun_rashi_prev_am, "—")

    # Adhika if Sun rashi SAME at consecutive Amavasya (2 new moons in same solar month)
    adhika_masa = (sun_rashi_prev_am == sun_rashi_next_am)

    # Kshaya if Sun rashi jumps by 2 or more between consecutive Amavasya (rare)
    jump = _normalize_rashi_jump(sun_rashi_prev_am, sun_rashi_next_am)
    kshaya_masa = (jump >= 2)

    # ---- Years ----
    shaka = _approx_shaka_year(sunrise_local)
    vikrama = _approx_vikrama_year(sunrise_local)
    samvatsara = _samvatsara_from_vikrama(vikrama)

    out: Dict[str, Any] = {
        "sunrise_local": fmt_local(sunrise_local),
        "sunset_local": fmt_local(sunset_local),
        "vaara": vaara,

        "paksha": paksha,

        # ✅ new
        "masa_name": masa_name,
        "adhika_masa": bool(adhika_masa),
        "kshaya_masa": bool(kshaya_masa),
        "ritu": ritu,
        "ayana": ayana,

        "shaka_year": str(shaka),
        "vikrama_year": str(vikrama),
        "samvatsara": samvatsara,

        "rahu_kalam": _fmt_span(zone, rahu_a, rahu_b),
        "yamaganda": _fmt_span(zone, yama_a, yama_b),
        "gulika": _fmt_span(zone, guli_a, guli_b),
        "abhijit": _fmt_span(zone, abhi_a, abhi_b),

        "tithi": {"name": tithi_name, "end_local": fmt_local(tithi_end_local), "end_hms": fmt_hm(tithi_end_local)},
        "nakshatra": {"name": nak_name, "end_local": fmt_local(nak_end_local), "end_hms": fmt_hm(nak_end_local)},
        "yoga": {"name": yoga_name, "end_local": fmt_local(yoga_end_local), "end_hms": fmt_hm(yoga_end_local)},
        "karana": {"name": kar_name, "end_local": fmt_local(kar_end_local), "end_hms": fmt_hm(kar_end_local)},
    }

    _panch_cache_set(key, out)
    return out
