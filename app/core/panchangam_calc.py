# app/core/panchangam_calc.py ✅ FULL REPLACE (FAST + NO skyfield/astral)
from __future__ import annotations

from datetime import datetime, timedelta, timezone, date
from zoneinfo import ZoneInfo
from typing import Dict, Any, Tuple, Optional, List, Callable
import math
import time

from app.core.nasa_ephemeris import get_planets_ecliptic

# ---------------------------
# Constants / Names
# ---------------------------
STAR_SPAN = 360.0 / 27.0   # 13°20'
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

SAMVATSARA_60 = [
    "Prabhava","Vibhava","Shukla","Pramoda","Prajapati","Angirasa","Shrimukha","Bhava","Yuva","Dhata",
    "Ishvara","Bahudhanya","Pramathi","Vikrama","Vrisha","Chitrabhanu","Svabhanu","Tarana","Parthiva","Vyaya",
    "Sarvajit","Sarvadhari","Virodhi","Vikruti","Khara","Nandana","Vijaya","Jaya","Manmatha","Durmukhi",
    "Hemalambi","Vilambi","Vikari","Sharvari","Plava","Shubhakritu","Shobhakritu","Krodhi","Vishvavasu","Parabhava",
    "Plavanga","Kilaka","Saumya","Sadharana","Virodhikritu","Paridhavi","Pramadicha","Ananda","Rakshasa","Nala",
    "Pingala","Kalayukti","Siddharthi","Raudra","Durmati","Dundubhi","Rudhirodgari","Raktakshi","Krodhana","Akshaya"
]

SAMVATSARA_60_TE = [
    "ప్రభవ","విభవ","శుక్ల","ప్రమోద","ప్రజాపతి","ఆంగీరస","శ్రీముఖ","భవ","యువ","ధాత",
    "ఈశ్వర","బహుధాన్య","ప్రమాథి","విక్రమ","వృష","చిత్రభాను","స్వభాను","తారణ","పార్థివ","వ్యయ",
    "సర్వజిత్","సర్వధారి","విరోధి","వికృతి","ఖర","నందన","విజయ","జయ","మన్మథ","దుర్ముఖి",
    "హేమలంబి","విలంబి","వికారీ","శర్వరి","ప్లవ","శుభకృత్","శోభకృత్","క్రోధి","విశ్వావసు","పరాభవ",
    "ప్లవంగ","కీలక","సౌమ్య","సాధారణ","విరోధికృత్","పరిధావి","ప్రమాదిచ","ఆనంద","రాక్షస","నల",
    "పింగళ","కాళయుక్తి","సిద్ధార్థి","రౌద్ర","దుర్మతి","దుందుభి","రుధిరోద్గారి","రక్తాక్షి","క్రోధన","అక్షయ"
]

# Rahu/Yama/Gulika indices (1..8 segments)
_RAHU_IDX = {"Sunday": 8, "Monday": 2, "Tuesday": 7, "Wednesday": 5, "Thursday": 6, "Friday": 4, "Saturday": 3}
_YAMA_IDX = {"Sunday": 6, "Monday": 5, "Tuesday": 4, "Wednesday": 3, "Thursday": 2, "Friday": 1, "Saturday": 7}
_GULI_IDX = {"Sunday": 7, "Monday": 6, "Tuesday": 5, "Wednesday": 4, "Thursday": 3, "Friday": 2, "Saturday": 1}

# Durmuhurta muhurtas (day divided into 15 muhurtas)
_DUR_MUHURTA_MUHURTA_IDX: Dict[str, List[int]] = {
    "Sunday": [4],
    "Monday": [8],
    "Tuesday": [3, 8],
    "Wednesday": [7],
    "Thursday": [6],
    "Friday": [4],
    "Saturday": [2, 6],
}

# Lunar month name (Amanta, simplified by Sun rashi at prev Amavasya approx)
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

# ✅ Varjya (Nakshatra Thyajyam) ghati ranges for 27 nakshatras (each nakshatra = 60 ghatis)
# Format: (startGhati, endGhati)
_VARJYA_GHATI: List[Tuple[int, int]] = [
    (51,54), (25,28), (31,34), (41,44), (15,18), (22,25), (31,34), (21,24), (33,36),
    (31,34), (21,24), (19,22), (22,25), (21,24), (15,18), (15,18), (11,14), (15,18),
    (57,60), (25,28), (21,24), (11,14), (11,14), (19,22), (17,20), (25,28), (31,34),
]

# ✅ Day Choghadiya table (8 parts sunrise->sunset)
DAY_CHOGH: Dict[str, List[str]] = {
    "Sunday":    ["Udveg","Char","Labh","Amrit","Kaal","Shubh","Rog","Udveg"],
    "Monday":    ["Amrit","Kaal","Shubh","Rog","Udveg","Char","Labh","Amrit"],
    "Tuesday":   ["Rog","Udveg","Char","Labh","Amrit","Kaal","Shubh","Rog"],
    "Wednesday": ["Labh","Amrit","Kaal","Shubh","Rog","Udveg","Char","Labh"],
    "Thursday":  ["Shubh","Rog","Udveg","Char","Labh","Amrit","Kaal","Shubh"],
    "Friday":    ["Char","Labh","Amrit","Kaal","Shubh","Rog","Udveg","Char"],
    "Saturday":  ["Kaal","Shubh","Rog","Udveg","Char","Labh","Amrit","Kaal"],
}

# ---------------------------
# Cache (server-side)
# ---------------------------
_PANCH_CACHE: Dict[str, Dict[str, Any]] = {}
_PANCH_TTL_SEC = 6 * 60 * 60  # 6 hours

def _panch_key(datetimeLocal: str, tz: str, lat: float, lon: float, ayan_deg: float) -> str:
    try:
        d = datetime.fromisoformat(datetimeLocal).date()
    except Exception:
        d = datetime.now().date()
    return f"{d.isoformat()}|{tz}|{float(lat):.4f}|{float(lon):.4f}|{float(ayan_deg):.4f}"

def _cache_get(key: str):
    v = _PANCH_CACHE.get(key)
    if not v:
        return None
    if (time.time() - float(v.get("_ts", 0))) > _PANCH_TTL_SEC:
        _PANCH_CACHE.pop(key, None)
        return None
    return v.get("data")

def _cache_set(key: str, data: Dict[str, Any]):
    _PANCH_CACHE[key] = {"_ts": time.time(), "data": data}

# ---------------------------
# Helpers
# ---------------------------
def wrap360(x: float) -> float:
    x = float(x) % 360.0
    return x if x >= 0 else x + 360.0

def _unwrap_near(x: float, x0: float) -> float:
    d = x - x0
    if d < -180:
        return x + 360.0
    if d > 180:
        return x - 360.0
    return x

def fmt_local(dt_local: datetime) -> str:
    return dt_local.strftime("%Y-%m-%d %H:%M")

def fmt_hm(dt_local: datetime) -> str:
    return dt_local.strftime("%H:%M")

def _fmt_span(zone: ZoneInfo, a_utc: datetime, b_utc: datetime) -> Dict[str, str]:
    a = a_utc.astimezone(zone)
    b = b_utc.astimezone(zone)
    return {"start": fmt_hm(a), "end": fmt_hm(b)}

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

def _durmuhurta_spans(sunrise_utc: datetime, sunset_utc: datetime, vaara: str) -> List[Tuple[datetime, datetime]]:
    spans: List[Tuple[datetime, datetime]] = []
    idxs = _DUR_MUHURTA_MUHURTA_IDX.get(vaara, [])
    if not idxs:
        return spans
    day_len = (sunset_utc - sunrise_utc)
    muhurta = day_len / 15
    for i in idxs:
        start = sunrise_utc + muhurta * (i - 1)
        end = start + muhurta
        spans.append((start, end))
    return spans

# ---------------------------
# ✅ NOAA-style sunrise/sunset (pure python, no deps)
# FIXED: longitude sign handling to prevent date mismatch
# ---------------------------
def _julian_day(dt_utc: datetime) -> float:
    y = dt_utc.year
    m = dt_utc.month
    d = dt_utc.day + (dt_utc.hour + dt_utc.minute/60 + dt_utc.second/3600) / 24.0
    if m <= 2:
        y -= 1
        m += 12
    A = math.floor(y / 100)
    B = 2 - A + math.floor(A / 4)
    JD = math.floor(365.25 * (y + 4716)) + math.floor(30.6001 * (m + 1)) + d + B - 1524.5
    return JD

def _sunrise_sunset_utc_for_local_date(local_d: date, tz: str, lat: float, lon: float) -> Tuple[datetime, datetime]:
    zone = ZoneInfo(tz)

    local_noon = datetime(local_d.year, local_d.month, local_d.day, 12, 0, 0, tzinfo=zone)
    dt_utc = local_noon.astimezone(timezone.utc)
    JD = _julian_day(dt_utc)
    n = JD - 2451545.0

    L = (280.460 + 0.9856474 * n) % 360.0
    g = math.radians((357.528 + 0.9856003 * n) % 360.0)

    lam = math.radians((L + 1.915 * math.sin(g) + 0.020 * math.sin(2 * g)) % 360.0)
    eps = math.radians(23.439 - 0.0000004 * n)

    sin_dec = math.sin(eps) * math.sin(lam)
    dec = math.asin(sin_dec)

    y = math.tan(eps / 2) ** 2
    Lrad = math.radians(L)
    eq_time = 4 * math.degrees(
        y * math.sin(2 * Lrad)
        - 2 * 0.0167 * math.sin(g)
        + 4 * 0.0167 * y * math.sin(g) * math.cos(2 * Lrad)
        - 0.5 * y * y * math.sin(4 * Lrad)
        - 1.25 * 0.0167 * 0.0167 * math.sin(2 * g)
    )

    zenith = math.radians(90.833)
    latr = math.radians(lat)

    cos_ha = (math.cos(zenith) - math.sin(latr) * math.sin(dec)) / (math.cos(latr) * math.cos(dec))
    cos_ha = max(-1.0, min(1.0, cos_ha))
    ha = math.degrees(math.acos(cos_ha))

    # ✅ FIX: NOAA formula in this form expects West-positive longitude.
    lon_west = -float(lon)

    solar_noon_min = (720 - 4 * lon_west - eq_time)
    sunrise_min = solar_noon_min - 4 * ha
    sunset_min = solar_noon_min + 4 * ha

    def mins_to_dt_utc(base_utc: datetime, minutes: float) -> datetime:
        base_day = datetime(base_utc.year, base_utc.month, base_utc.day, 0, 0, 0, tzinfo=timezone.utc)
        return base_day + timedelta(minutes=float(minutes))

    sunrise_utc = mins_to_dt_utc(dt_utc, sunrise_min)
    sunset_utc = mins_to_dt_utc(dt_utc, sunset_min)

    # ensure intended local date
    if sunrise_utc.astimezone(zone).date() != local_d:
        sunrise_utc += timedelta(days=1) if sunrise_utc.astimezone(zone).date() < local_d else timedelta(days=-1)
    if sunset_utc.astimezone(zone).date() != local_d:
        sunset_utc += timedelta(days=1) if sunset_utc.astimezone(zone).date() < local_d else timedelta(days=-1)

    if sunset_utc <= sunrise_utc:
        local_mid = datetime(local_d.year, local_d.month, local_d.day, 0, 0, 0, tzinfo=zone)
        sunrise_utc = local_mid.replace(hour=6).astimezone(timezone.utc)
        sunset_utc = local_mid.replace(hour=18).astimezone(timezone.utc)

    return sunrise_utc, sunset_utc

# ---------------------------
# NASA lon -> sidereal
# ---------------------------
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
        sun_t = float(planets[0].get("lon", 0.0))
        moon_t = float(planets[1].get("lon", 0.0))

    sun_s = wrap360(sun_t - float(ayan_deg))
    moon_s = wrap360(moon_t - float(ayan_deg))
    return sun_s, moon_s

# ---------------------------
# Fast end-time solver (VERY few NASA calls)
# ---------------------------
def _solve_end_time_fast(
    value_fn: Callable[[datetime], float],
    v0: float,
    target: float,
    t0: datetime,
    t1: datetime,
    sample_dt: timedelta = timedelta(hours=6),
) -> datetime:
    tS = min(t0 + sample_dt, t1)
    vS = value_fn(tS)
    rate = (vS - v0) / max(1.0, (tS - t0).total_seconds())
    if abs(rate) < 1e-10:
        return t1

    est = t0 + timedelta(seconds=float((target - v0) / rate))
    if est < t0: est = t0
    if est > t1: est = t1

    vE = value_fn(est)
    tR = min(est + timedelta(hours=2), t1)
    vR = value_fn(tR)
    rate2 = (vR - vE) / max(1.0, (tR - est).total_seconds())
    if abs(rate2) < 1e-10:
        return est

    est2 = est + timedelta(seconds=float((target - vE) / rate2))
    if est2 < t0: est2 = t0
    if est2 > t1: est2 = t1
    return est2

def _solve_start_time_fast(
    value_fn: Callable[[datetime], float],
    v_at_t1: float,
    target: float,
    t0: datetime,
    t1: datetime,
    sample_dt: timedelta = timedelta(hours=6),
) -> datetime:
    """
    Solve backwards for value_fn(t)=target within [t0,t1], using 1-2 samples.
    """
    tS = max(t1 - sample_dt, t0)
    vS = value_fn(tS)
    rate = (v_at_t1 - vS) / max(1.0, (t1 - tS).total_seconds())
    if abs(rate) < 1e-10:
        return t0

    est = t1 - timedelta(seconds=float((v_at_t1 - target) / rate))
    if est < t0: est = t0
    if est > t1: est = t1

    vE = value_fn(est)
    tR = max(est - timedelta(hours=2), t0)
    vR = value_fn(tR)
    rate2 = (vE - vR) / max(1.0, (est - tR).total_seconds())
    if abs(rate2) < 1e-10:
        return est

    est2 = est - timedelta(seconds=float((vE - target) / rate2))
    if est2 < t0: est2 = t0
    if est2 > t1: est2 = t1
    return est2

# ---------------------------
# Simple meta from sun rashi
# ---------------------------
def _sun_rashi(sun_sid: float) -> int:
    return int(math.floor(wrap360(sun_sid) / 30.0)) % 12

def _ayana_from_sun_rashi(r: int) -> str:
    return "Uttarayana" if r in (9, 10, 11, 0, 1, 2) else "Dakshinayana"

def _ritu_from_sun_rashi(r: int) -> str:
    if r in (0, 1):  return "Vasanta"
    if r in (2, 3):  return "Grishma"
    if r in (4, 5):  return "Varsha"
    if r in (6, 7):  return "Sharad"
    if r in (8, 9):  return "Hemanta"
    return "Shishira"

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

# ✅ Samvatsara calibrated (keep your existing behavior)
_SAMVATSARA_VIKRAMA_OFFSET = -3

def _samvatsara_from_vikrama(vikrama_year: int) -> Tuple[str, str]:
    idx = ((int(vikrama_year) - 1) + _SAMVATSARA_VIKRAMA_OFFSET) % 60
    return SAMVATSARA_60[idx], SAMVATSARA_60_TE[idx]

# ---------------------------
# MAIN
# ---------------------------
def compute_panchangam(datetimeLocal: str, tz: str, lat: float, lon: float, ayan_deg: float) -> Dict[str, Any]:
    key = _panch_key(datetimeLocal, tz, float(lat), float(lon), float(ayan_deg))
    hit = _cache_get(key)
    if hit:
        return hit

    zone = ZoneInfo(tz)
    dt_local = datetime.fromisoformat(datetimeLocal).replace(tzinfo=zone)
    local_d = dt_local.date()

    sunrise_utc, sunset_utc = _sunrise_sunset_utc_for_local_date(local_d, tz, float(lat), float(lon))
    next_sunrise_utc, _ = _sunrise_sunset_utc_for_local_date(local_d + timedelta(days=1), tz, float(lat), float(lon))

    sunrise_local = sunrise_utc.astimezone(zone)
    sunset_local = sunset_utc.astimezone(zone)
    next_sunrise_local = next_sunrise_utc.astimezone(zone)

    vaara = VAARA_EN[sunrise_local.weekday()]  # Monday..Sunday

    # Kala blocks
    rahu_a, rahu_b = _kala_segment(sunrise_utc, sunset_utc, _RAHU_IDX.get(vaara, 2))
    yama_a, yama_b = _kala_segment(sunrise_utc, sunset_utc, _YAMA_IDX.get(vaara, 5))
    guli_a, guli_b = _kala_segment(sunrise_utc, sunset_utc, _GULI_IDX.get(vaara, 6))
    abhi_a, abhi_b = _abhijit(sunrise_utc, sunset_utc)

    # Sun/Moon at sunrise
    sun0, moon0 = _sun_moon_sid_at(sunrise_utc, float(lat), float(lon), float(ayan_deg))
    d0 = wrap360(moon0 - sun0)
    y0 = wrap360(moon0 + sun0)

    def delta_unwrapped(t_utc: datetime) -> float:
        s, m = _sun_moon_sid_at(t_utc, float(lat), float(lon), float(ayan_deg))
        d = wrap360(m - s)
        return _unwrap_near(d, d0)

    def moon_unwrapped(t_utc: datetime) -> float:
        _, m = _sun_moon_sid_at(t_utc, float(lat), float(lon), float(ayan_deg))
        return _unwrap_near(wrap360(m), moon0)

    def yoga_unwrapped(t_utc: datetime) -> float:
        s, m = _sun_moon_sid_at(t_utc, float(lat), float(lon), float(ayan_deg))
        yy = wrap360(m + s)
        return _unwrap_near(yy, y0)

    # ---- Tithi ----
    tithi_idx = int(math.floor(d0 / TITHI_SPAN)) + 1
    tithi_name = TITHI_NAMES[(tithi_idx - 1) % 30]
    paksha = "Shukla" if 1 <= tithi_idx <= 15 else "Krishna"
    tithi_target = (math.floor(d0 / TITHI_SPAN) + 1) * TITHI_SPAN
    tithi_end_utc = _solve_end_time_fast(delta_unwrapped, d0, tithi_target, sunrise_utc, next_sunrise_utc)
    tithi_end_local = tithi_end_utc.astimezone(zone)

    # ---- Nakshatra ----
    nak_idx_1 = int(math.floor(moon0 / STAR_SPAN)) + 1
    nak_name = NAKSHATRA_NAMES[(nak_idx_1 - 1) % 27]
    nak_target = (math.floor(moon0 / STAR_SPAN) + 1) * STAR_SPAN
    nak_end_utc = _solve_end_time_fast(moon_unwrapped, moon0, nak_target, sunrise_utc, next_sunrise_utc)
    nak_end_local = nak_end_utc.astimezone(zone)

    # ---- Yoga ----
    yoga_idx = int(math.floor(y0 / STAR_SPAN)) + 1
    yoga_name = YOGA_NAMES[(yoga_idx - 1) % 27]
    yoga_target = (math.floor(y0 / STAR_SPAN) + 1) * STAR_SPAN
    yoga_end_utc = _solve_end_time_fast(yoga_unwrapped, y0, yoga_target, sunrise_utc, next_sunrise_utc)
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
    kar_end_utc = _solve_end_time_fast(delta_unwrapped, d0, kar_target, sunrise_utc, next_sunrise_utc)
    kar_end_local = kar_end_utc.astimezone(zone)

    # ---- Solar meta ----
    sun_r = _sun_rashi(sun0)
    ritu = _ritu_from_sun_rashi(sun_r)
    ayana = _ayana_from_sun_rashi(sun_r)

    # ---- Masa (simple prev amavasya approx) ----
    tS = min(sunrise_utc + timedelta(hours=6), next_sunrise_utc)
    dS = delta_unwrapped(tS)
    rate = (dS - d0) / max(1.0, (tS - sunrise_utc).total_seconds())
    if abs(rate) > 1e-10:
        prev_am_utc = sunrise_utc - timedelta(seconds=float(d0 / rate))
    else:
        prev_am_utc = sunrise_utc - timedelta(days=15)
    if prev_am_utc < sunrise_utc - timedelta(days=35):
        prev_am_utc = sunrise_utc - timedelta(days=15)

    sun_prev_am, _ = _sun_moon_sid_at(prev_am_utc, float(lat), float(lon), float(ayan_deg))
    masa_name = LUNAR_MONTH_BY_SUN_RASHI.get(_sun_rashi(sun_prev_am), "—")

    # ---- Years + samvatsara ----
    shaka = _approx_shaka_year(sunrise_local)
    vikrama = _approx_vikrama_year(sunrise_local)
    samv_en, samv_te = _samvatsara_from_vikrama(vikrama)

    # ---- Durmuhurtha ----
    durm_spans = _durmuhurta_spans(sunrise_utc, sunset_utc, vaara)
    durmuhurtha_list = [_fmt_span(zone, a, b) for (a, b) in durm_spans]

    # ---- Varjya (Nakshatra Thyajyam) ----
    # Estimate nakshatra start (backwards) so varjya becomes correct and still fast
    nak_i0 = (nak_idx_1 - 1) % 27
    nak_start_boundary = math.floor(moon0 / STAR_SPAN) * STAR_SPAN  # boundary at nak start

    t0_back = sunrise_utc - timedelta(days=1)
    nak_start_utc = _solve_start_time_fast(moon_unwrapped, moon0, nak_start_boundary, t0_back, sunrise_utc)

    nak_dur = (nak_end_utc - nak_start_utc)
    varjya_sp: List[Tuple[datetime, datetime]] = []
    if nak_dur.total_seconds() > 0:
        g0, g1 = _VARJYA_GHATI[nak_i0]
        a = nak_start_utc + nak_dur * (g0 / 60.0)
        b = nak_start_utc + nak_dur * (g1 / 60.0)
        if b > a:
            varjya_sp.append((a, b))

    varjya_list = [_fmt_span(zone, a, b) for (a, b) in varjya_sp]

    # ---- Amrita/Shubha from Day Choghadiya (8 parts sunrise->sunset) ----
    seq = DAY_CHOGH.get(vaara, DAY_CHOGH["Monday"])
    day_len = (sunset_utc - sunrise_utc)
    part = day_len / 8

    amrita_sp: List[Tuple[datetime, datetime]] = []
    shubha_sp: List[Tuple[datetime, datetime]] = []
    for i in range(8):
        nm = seq[i]
        a = sunrise_utc + part * i
        b = a + part
        if nm == "Amrit":
            amrita_sp.append((a, b))
        if nm == "Shubh":
            shubha_sp.append((a, b))

    amrita_ghadiya = [_fmt_span(zone, a, b) for (a, b) in amrita_sp]
    shubha_ghadiya = [_fmt_span(zone, a, b) for (a, b) in shubha_sp]

    out: Dict[str, Any] = {
        "sunrise_local": fmt_local(sunrise_local),
        "sunset_local": fmt_local(sunset_local),
        "next_sunrise_local": fmt_local(next_sunrise_local),
        "vaara": vaara,

        "masa_name": masa_name,
        "paksha": paksha,
        "ritu": ritu,
        "ayana": ayana,
        "shaka_year": str(shaka),
        "vikrama_year": str(vikrama),
        "samvatsara": samv_en,
        "samvatsara_te": samv_te,

        "rahu_kalam": _fmt_span(zone, rahu_a, rahu_b),
        "yamaganda": _fmt_span(zone, yama_a, yama_b),
        "gulika": _fmt_span(zone, guli_a, guli_b),
        "durmuhurtha": durmuhurtha_list,

        "varjya": varjya_list,
        "varjya_kaal": varjya_list,

        "abhijit": _fmt_span(zone, abhi_a, abhi_b),

        "amrita_ghadiya": amrita_ghadiya,
        "shubha_ghadiya": shubha_ghadiya,

        "tithi": {"name": tithi_name, "end_local": fmt_local(tithi_end_local), "end_hms": fmt_hm(tithi_end_local)},
        "nakshatra": {"name": nak_name, "end_local": fmt_local(nak_end_local), "end_hms": fmt_hm(nak_end_local)},
        "yoga": {"name": yoga_name, "end_local": fmt_local(yoga_end_local), "end_hms": fmt_hm(yoga_end_local)},
        "karana": {"name": kar_name, "end_local": fmt_local(kar_end_local), "end_hms": fmt_hm(kar_end_local)},

        "note": "Fast panchangam: NOAA sunrise/sunset (lon fix) + NASA lon; cache+few calls. Varjya via nakshatra ghatis; Amrita/Shubha via choghadiya."
    }

    _cache_set(key, out)
    return out
