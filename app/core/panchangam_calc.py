from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Tuple, Callable, List, Optional
from zoneinfo import ZoneInfo
import math
import time

# -------------------------
# ✅ Skyfield OPTIONAL import
# -------------------------
_SF_OK = True
_SF_ERR = ""
try:
    from skyfield.api import load, wgs84  # type: ignore
    from skyfield import almanac  # type: ignore
except Exception as e:
    _SF_OK = False
    _SF_ERR = str(e)
    load = None
    wgs84 = None
    almanac = None

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

# ✅ Lunar month names (Amanta, common South India)
# Mapping based on Sun's sidereal rashi at AMAVASYA:
# Pisces->Chaitra, Aries->Vaisakha ... Aquarius->Phalguna
LUNAR_MONTH_BY_SUN_RASHI = {
    11: "Chaitra",      # Pisces
    0:  "Vaisakha",     # Aries
    1:  "Jyeshtha",     # Taurus
    2:  "Ashadha",      # Gemini
    3:  "Shravana",     # Cancer
    4:  "Bhadrapada",   # Leo
    5:  "Ashwin",       # Virgo
    6:  "Kartika",      # Libra
    7:  "Margashirsha", # Scorpio
    8:  "Pausha",       # Sagittarius
    9:  "Magha",        # Capricorn
    10: "Phalguna",     # Aquarius
}

# ✅ 60 Samvatsara list
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
    """
    Try to load Skyfield ephemeris.
    If fails, caller will fallback to approx sunrise/sunset.
    """
    global _TS, _EPH, _SF_OK, _SF_ERR
    if not _SF_OK:
        raise RuntimeError(_SF_ERR or "Skyfield not available")

    if _TS is None:
        _TS = load.timescale()
    if _EPH is None:
        # Smaller & commonly used; de440s might download larger and cause delays.
        _EPH = load("de421.bsp")
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

def _fmt_span_local(zone: ZoneInfo, a_local: datetime, b_local: datetime) -> Dict[str, str]:
    return {"start": fmt_hm(a_local.astimezone(zone)), "end": fmt_hm(b_local.astimezone(zone))}

# Rahu/Yama/Gulika indices (1..8 segments)
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

def _sunrise_sunset_utc(
    lat: float, lon: float, day_local_date: datetime, tz: str
) -> Tuple[datetime, datetime]:
    """
    Returns sunrise_utc and sunset_utc for the given local date.
    If Skyfield fails, returns approx 06:00 / 18:00 local converted to UTC.
    """
    zone = ZoneInfo(tz)
    local_midnight = datetime(day_local_date.year, day_local_date.month, day_local_date.day, 0, 0, 0, tzinfo=zone)

    # Skyfield path
    try:
        ts, eph = _sf_loaded()
        topos = wgs84.latlon(latitude_degrees=float(lat), longitude_degrees=float(lon))
        f = almanac.sunrise_sunset(eph, topos)

        t0_utc = local_midnight.astimezone(timezone.utc)
        t1_utc = (local_midnight + timedelta(days=2)).astimezone(timezone.utc)

        t0 = ts.from_datetime(t0_utc)
        t1 = ts.from_datetime(t1_utc)
        times, events = almanac.find_discrete(t0, t1, f)

        target_date = local_midnight.date()
        sunrise_list: List[datetime] = []
        sunset_list: List[datetime] = []

        for ti, ev in zip(times, events):
            dt = ti.utc_datetime().replace(tzinfo=timezone.utc)
            if bool(ev) is True:
                sunrise_list.append(dt)
            else:
                sunset_list.append(dt)

        sunrise_today = None
        for s in sunrise_list:
            if s.astimezone(zone).date() == target_date:
                sunrise_today = s
                break

        sunset_today = None
        for s in sunset_list:
            if s.astimezone(zone).date() == target_date:
                sunset_today = s
                break

        if sunrise_today and sunset_today:
            return sunrise_today, sunset_today

        raise RuntimeError("Skyfield could not locate sunrise/sunset for date")

    except Exception:
        # Fallback approximate (never crash/hang)
        approx_sunrise_local = local_midnight.replace(hour=6, minute=0)
        approx_sunset_local = local_midnight.replace(hour=18, minute=0)
        return approx_sunrise_local.astimezone(timezone.utc), approx_sunset_local.astimezone(timezone.utc)

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
    if d < -180:
        return x + 360.0
    if d > 180:
        return x - 360.0
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
    # Uttarayana: Capricorn..Gemini
    return "Uttarayana" if sun_rashi in (9, 10, 11, 0, 1, 2) else "Dakshinayana"

def _ritu_from_sun_rashi(sun_rashi: int) -> str:
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
    start = sunrise_utc - timedelta(days=40)
    end = sunrise_utc + timedelta(days=40)
    step = timedelta(hours=6)

    s0, m0 = _sun_moon_sid_at(start, lat, lon, ayan_deg)
    ref = wrap360(m0 - s0)
    prev_t = start
    prev_u = ref

    crossings: List[datetime] = []

    t = start + step
    while t <= end:
        u = _phase_unwrapped(t, lat, lon, ayan_deg, prev_u)

        lo = min(prev_u, u)
        hi = max(prev_u, u)
        k0 = math.floor(lo / 360.0)
        k1 = math.floor(hi / 360.0)

        if k1 != k0:
            for k in range(int(k0) + 1, int(k1) + 1):
                target = 360.0 * k

                def fn(tt: datetime) -> float:
                    return _phase_unwrapped(tt, lat, lon, ayan_deg, prev_u)

                tt = _bin_search_time(fn, target, prev_t, t)
                crossings.append(tt)

        prev_t = t
        prev_u = u
        t += step

    crossings = sorted(crossings)
    prev_am = None
    next_am = None
    for c in crossings:
        if c <= sunrise_utc:
            prev_am = c
        elif c > sunrise_utc and next_am is None:
            next_am = c
            break

    if prev_am is None:
        prev_am = sunrise_utc - timedelta(days=15)
    if next_am is None:
        next_am = sunrise_utc + timedelta(days=15)

    return prev_am, next_am

def _sun_rashi_at(dt_utc: datetime, lat: float, lon: float, ayan_deg: float) -> int:
    sun_lon = _sun_sid_lon(dt_utc, lat, lon, ayan_deg)
    return int(math.floor(sun_lon / 30.0)) % 12

def _normalize_rashi_jump(a: int, b: int) -> int:
    return (b - a) % 12

# -------------------------
# ✅ Durmuhurtham (Drik style)
# day_length / 15 = muhurta length
# weekday mapping (muhurta index)
# Tuesday & Saturday have TWO durmuhurta
# -------------------------
_DUR_MUHURTA_MUHURTA_IDX: Dict[str, List[int]] = {
    "Sunday": [4],
    "Monday": [8],
    "Tuesday": [3, 8],
    "Wednesday": [7],
    "Thursday": [6],
    "Friday": [4],
    "Saturday": [2, 6],
}

def _durmuhurta_spans(sunrise_utc: datetime, sunset_utc: datetime, vaara: str) -> List[Tuple[datetime, datetime]]:
    spans: List[Tuple[datetime, datetime]] = []
    idxs = _DUR_MUHURTA_MUHURTA_IDX.get(vaara, [])
    if not idxs:
        return spans

    day_len = (sunset_utc - sunrise_utc)
    muhurta = day_len / 15  # variable muhurta
    for i in idxs:
        start = sunrise_utc + muhurta * (i - 1)
        end = start + muhurta
        spans.append((start, end))
    return spans

# -------------------------
# ✅ Varjya / Amrita / Shubha (safe approximation)
# Uses current Nakshatra window(s) within Panchang-day.
# We compute nakshatra end(s) already; derive start by back-calculating
# nak start using moon longitude within nak.
# Then create proportional windows.
# -------------------------
def _nak_start_from_moon_lon(moon_sid: float, nak_idx0: int) -> float:
    return nak_idx0 * STAR_SPAN

def _clamp_span_to_day(a: datetime, b: datetime, day_start: datetime, day_end: datetime) -> Optional[Tuple[datetime, datetime]]:
    aa = max(a, day_start)
    bb = min(b, day_end)
    if bb <= aa:
        return None
    return aa, bb

def _make_proportional_windows(
    day_start_utc: datetime,
    day_end_utc: datetime,
    nak_start_utc: datetime,
    nak_end_utc: datetime,
) -> Tuple[List[Tuple[datetime, datetime]], List[Tuple[datetime, datetime]], List[Tuple[datetime, datetime]]]:
    """
    Returns (amrita, shubha, varjya) spans.
    - varjya: around 0.62..0.72 of nak duration (≈ later half)
    - amrita: around 0.18..0.30 of nak duration (≈ earlier)
    - shubha: two small windows (0.36..0.44 and 0.80..0.88)
    """
    dur = (nak_end_utc - nak_start_utc)
    if dur.total_seconds() <= 0:
        return [], [], []

    def seg(a: float, b: float) -> Tuple[datetime, datetime]:
        return nak_start_utc + dur * a, nak_start_utc + dur * b

    am1 = seg(0.18, 0.30)
    sh1 = seg(0.36, 0.44)
    sh2 = seg(0.80, 0.88)
    vz1 = seg(0.62, 0.72)

    amrita: List[Tuple[datetime, datetime]] = []
    shubha: List[Tuple[datetime, datetime]] = []
    varjya: List[Tuple[datetime, datetime]] = []

    for (a, b) in [am1]:
        c = _clamp_span_to_day(a, b, day_start_utc, day_end_utc)
        if c:
            amrita.append(c)

    for (a, b) in [sh1, sh2]:
        c = _clamp_span_to_day(a, b, day_start_utc, day_end_utc)
        if c:
            shubha.append(c)

    for (a, b) in [vz1]:
        c = _clamp_span_to_day(a, b, day_start_utc, day_end_utc)
        if c:
            varjya.append(c)

    return amrita, shubha, varjya

# ----------------- Main compute -----------------
def compute_panchangam(datetimeLocal: str, tz: str, lat: float, lon: float, ayan_deg: float) -> Dict[str, Any]:
    key = _panch_key(datetimeLocal, tz, float(lat), float(lon), float(ayan_deg))
    hit = _panch_cache_get(key)
    if hit:
        return hit

    zone = ZoneInfo(tz)
    dt_local = datetime.fromisoformat(datetimeLocal).replace(tzinfo=zone)

    sunrise_utc, sunset_utc = _sunrise_sunset_utc(lat, lon, dt_local, tz)
    sunrise_local = sunrise_utc.astimezone(zone)
    sunset_local = sunset_utc.astimezone(zone)

    # Panchang-day boundaries (sunrise..next sunrise) — for our windows keep within sunrise..sunset for simplicity
    day_start_utc = sunrise_utc
    day_end_utc = sunset_utc  # (UI wants daytime blocks; night blocks still possible via varjya calc if needed)

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
    nak_idx = int(math.floor(moon0 / STAR_SPAN)) + 1  # 1..27
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

    # ---- Lunar Masa + Adhika/Kshaya ----
    prev_am, next_am = _find_prev_next_amavasya(sunrise_utc, lat, lon, ayan_deg)
    sun_rashi_prev_am = _sun_rashi_at(prev_am, lat, lon, ayan_deg)
    sun_rashi_next_am = _sun_rashi_at(next_am, lat, lon, ayan_deg)

    masa_name = LUNAR_MONTH_BY_SUN_RASHI.get(sun_rashi_prev_am, "—")
    adhika_masa = (sun_rashi_prev_am == sun_rashi_next_am)
    jump = _normalize_rashi_jump(sun_rashi_prev_am, sun_rashi_next_am)
    kshaya_masa = (jump >= 2)

    # ---- Years ----
    shaka = _approx_shaka_year(sunrise_local)
    vikrama = _approx_vikrama_year(sunrise_local)
    samvatsara = _samvatsara_from_vikrama(vikrama)

    # ---- Durmuhurtham ----
    durm_spans = _durmuhurta_spans(sunrise_utc, sunset_utc, vaara)
    durmuhurtha_list = [_fmt_span(zone, a, b) for (a, b) in durm_spans]

    # ---- Varjya + Amrita + Shubha (safe approximation) ----
    # Estimate nakshatra start time:
    # fraction within nak at sunrise = (moon0 - nak_start_lon)/STAR_SPAN
    nak_idx0 = (nak_idx - 1) % 27
    nak_start_lon = _nak_start_from_moon_lon(moon0, nak_idx0)
    frac = (wrap360(moon0 - nak_start_lon)) / STAR_SPAN  # 0..1
    nak_start_utc = sunrise_utc - (nak_end_utc - sunrise_utc) * (frac / max(1e-9, (1.0 - frac))) if frac < 0.999 else sunrise_utc

    # If math went weird, clamp
    if nak_start_utc > sunrise_utc:
        nak_start_utc = sunrise_utc

    amrita_sp, shubha_sp, varjya_sp = _make_proportional_windows(day_start_utc, day_end_utc, nak_start_utc, nak_end_utc)

    amrita_ghadiya = [_fmt_span(zone, a, b) for (a, b) in amrita_sp]
    shubha_ghadiya = [_fmt_span(zone, a, b) for (a, b) in shubha_sp]
    varjya_kaal = [_fmt_span(zone, a, b) for (a, b) in varjya_sp]

    out: Dict[str, Any] = {
        # core
        "sunrise_local": fmt_local(sunrise_local),
        "sunset_local": fmt_local(sunset_local),
        "vaara": vaara,
        "paksha": paksha,

        # masa + year + season
        "masa_name": masa_name,
        "adhika_masa": bool(adhika_masa),
        "kshaya_masa": bool(kshaya_masa),
        "ritu": ritu,
        "ayana": ayana,
        "shaka_year": str(shaka),
        "vikrama_year": str(vikrama),
        "samvatsara": samvatsara,

        # inauspicious (you want RED in app)
        "rahu_kalam": _fmt_span(zone, rahu_a, rahu_b),
        "yamaganda": _fmt_span(zone, yama_a, yama_b),
        "gulika": _fmt_span(zone, guli_a, guli_b),
        "durmuhurtha": durmuhurtha_list,
        "varjya_kaal": varjya_kaal,

        # auspicious (you want SHINE GREEN in app)
        "abhijit": _fmt_span(zone, abhi_a, abhi_b),
        "amrita_ghadiya": amrita_ghadiya,
        "shubha_ghadiya": shubha_ghadiya,

        # panchanga anga end times
        "tithi": {"name": tithi_name, "end_local": fmt_local(tithi_end_local), "end_hms": fmt_hm(tithi_end_local)},
        "nakshatra": {"name": nak_name, "end_local": fmt_local(nak_end_local), "end_hms": fmt_hm(nak_end_local)},
        "yoga": {"name": yoga_name, "end_local": fmt_local(yoga_end_local), "end_hms": fmt_hm(yoga_end_local)},
        "karana": {"name": kar_name, "end_local": fmt_local(kar_end_local), "end_hms": fmt_hm(kar_end_local)},

        # debug hint (optional)
        "sf_ok": bool(_SF_OK),
    }

    _panch_cache_set(key, out)
    return out
