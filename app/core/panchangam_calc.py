# app/core/panchangam_calc.py ✅ FULL REPLACE (FAST + STABLE + production-safe)
from __future__ import annotations

from datetime import datetime, timedelta, timezone, date
from zoneinfo import ZoneInfo
from typing import Dict, Any, Tuple, List
import math
import time

from app.core.nasa_ephemeris import get_planets_ecliptic
from app.core.ayanamsa_exact import get_ayanamsa_deg

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

# Rahu/Yama/Gulika indices (1..8 segments) - standard
_RAHU_IDX = {"Sunday": 8, "Monday": 2, "Tuesday": 7, "Wednesday": 5, "Thursday": 6, "Friday": 4, "Saturday": 3}
_YAMA_IDX = {"Sunday": 5, "Monday": 4, "Tuesday": 3, "Wednesday": 2, "Thursday": 1, "Friday": 7, "Saturday": 6}
_GULI_IDX = {"Sunday": 7, "Monday": 6, "Tuesday": 5, "Wednesday": 4, "Thursday": 3, "Friday": 2, "Saturday": 1}

# Durmuhurta muhurtas (sunrise->sunset divided into 15 muhurtas)
_DUR_MUHURTA_MUHURTA_IDX: Dict[str, List[int]] = {
    "Sunday": [4],
    "Monday": [8],
    "Tuesday": [3, 8],
    "Wednesday": [7],
    "Thursday": [6],
    "Friday": [4],
    "Saturday": [2, 6],
}

# Lunar month by Sun rashi (approx, Amanta-ish)
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

# ✅ Varjya (Nakshatra Thyajyam) ghati ranges (0..60 ghatis)
_VARJYA_GHATI: List[Tuple[int, int]] = [
    (51,54), (25,28), (31,34), (41,44), (15,18), (22,25), (31,34), (21,24), (33,36),
    (31,34), (21,24), (19,22), (22,25), (21,24), (15,18), (15,18), (11,14), (15,18),
    (57,60), (25,28), (21,24), (11,14), (11,14), (19,22), (17,20), (25,28), (31,34),
]

# ✅ Day Choghadiya sequence (sunrise->sunset 8 parts)
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
_PANCH_TTL_SEC = 12 * 60 * 60  # 12 hours

def _panch_key(datetimeLocal: str, tz: str, lat: float, lon: float, ayan_deg: float) -> str:
    # ✅ include full datetimeLocal (not just date)
    return f"{datetimeLocal}|{tz}|{float(lat):.4f}|{float(lon):.4f}|{float(ayan_deg):.6f}"

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

def unwrap_forward(v1: float, v0: float) -> float:
    d = v1 - v0
    if d < -180:
        return v1 + 360.0
    if d > 180:
        return v1 - 360.0
    return v1

def fmt_local(dt_local: datetime) -> str:
    return dt_local.strftime("%Y-%m-%d %H:%M")

def fmt_hm(dt_local: datetime) -> str:
    return dt_local.strftime("%H:%M")

def _fmt_span(zone: ZoneInfo, a_utc: datetime, b_utc: datetime) -> Dict[str, str]:
    return {"start": fmt_hm(a_utc.astimezone(zone)), "end": fmt_hm(b_utc.astimezone(zone))}

def _kala_segment(sunrise_utc: datetime, sunset_utc: datetime, seg_index_1to8: int) -> Tuple[datetime, datetime]:
    day_len = (sunset_utc - sunrise_utc)
    part = day_len / 8
    a = sunrise_utc + part * (seg_index_1to8 - 1)
    b = a + part
    return a, b

def _abhijit(sunrise_utc: datetime, sunset_utc: datetime) -> Tuple[datetime, datetime]:
    mid = sunrise_utc + (sunset_utc - sunrise_utc) / 2
    span = (sunset_utc - sunrise_utc) / 15  # 1 muhurta
    return mid - span / 2, mid + span / 2

def _durmuhurta_spans(sunrise_utc: datetime, sunset_utc: datetime, vaara: str) -> List[Tuple[datetime, datetime]]:
    idxs = _DUR_MUHURTA_MUHURTA_IDX.get(vaara, [])
    if not idxs:
        return []
    day_len = (sunset_utc - sunrise_utc)
    muhurta = day_len / 15
    out: List[Tuple[datetime, datetime]] = []
    for i in idxs:
        a = sunrise_utc + muhurta * (i - 1)
        b = a + muhurta
        out.append((a, b))
    return out

# ---------------------------
# ✅ NOAA Solar Calculator style sunrise/sunset
# ---------------------------
def _julian_day_0h_utc(d: date) -> float:
    y = d.year
    m = d.month
    day = d.day
    if m <= 2:
        y -= 1
        m += 12
    A = math.floor(y / 100)
    B = 2 - A + math.floor(A / 4)
    JD = math.floor(365.25 * (y + 4716)) + math.floor(30.6001 * (m + 1)) + day + B - 1524.5
    return JD

def _sun_decl_and_eqtime(jd: float) -> Tuple[float, float]:
    T = (jd - 2451545.0) / 36525.0
    L0 = (280.46646 + T * (36000.76983 + T * 0.0003032)) % 360.0
    M = 357.52911 + T * (35999.05029 - 0.0001537 * T)
    Mrad = math.radians(M)
    e = 0.016708634 - T * (0.000042037 + 0.0000001267 * T)
    C = (math.sin(Mrad) * (1.914602 - T * (0.004817 + 0.000014 * T))
         + math.sin(2 * Mrad) * (0.019993 - 0.000101 * T)
         + math.sin(3 * Mrad) * 0.000289)
    true_long = L0 + C
    omega = 125.04 - 1934.136 * T
    lam = true_long - 0.00569 - 0.00478 * math.sin(math.radians(omega))
    lamr = math.radians(lam)

    eps0 = 23.0 + (26.0 + ((21.448 - T*(46.815 + T*(0.00059 - T*0.001813))))/60.0)/60.0
    eps = eps0 + 0.00256 * math.cos(math.radians(omega))
    epsr = math.radians(eps)

    sin_dec = math.sin(epsr) * math.sin(lamr)
    dec = math.asin(sin_dec)

    y = math.tan(epsr/2.0)**2
    L0r = math.radians(L0)
    Etime = 4.0 * math.degrees(
        y * math.sin(2.0*L0r)
        - 2.0*e*math.sin(Mrad)
        + 4.0*e*y*math.sin(Mrad)*math.cos(2.0*L0r)
        - 0.5*y*y*math.sin(4.0*L0r)
        - 1.25*e*e*math.sin(2.0*Mrad)
    )
    return dec, Etime

def _sunrise_sunset_utc_for_local_date(local_d: date, tz: str, lat: float, lon: float) -> Tuple[datetime, datetime]:
    zone = ZoneInfo(tz)
    local_noon = datetime(local_d.year, local_d.month, local_d.day, 12, 0, 0, tzinfo=zone)
    utc_noon = local_noon.astimezone(timezone.utc)
    jd0 = _julian_day_0h_utc(utc_noon.date())

    dec, eq_time = _sun_decl_and_eqtime(jd0)

    zenith = math.radians(90.833)
    latr = math.radians(lat)

    cos_ha = (math.cos(zenith) - math.sin(latr)*math.sin(dec)) / (math.cos(latr)*math.cos(dec))
    cos_ha = max(-1.0, min(1.0, cos_ha))
    ha = math.degrees(math.acos(cos_ha))

    solar_noon_min = 720.0 - 4.0*float(lon) - float(eq_time)
    sunrise_min = solar_noon_min - 4.0*ha
    sunset_min = solar_noon_min + 4.0*ha

    base = datetime(utc_noon.date().year, utc_noon.date().month, utc_noon.date().day, 0, 0, 0, tzinfo=timezone.utc)
    sunrise_utc = base + timedelta(minutes=float(sunrise_min))
    sunset_utc = base + timedelta(minutes=float(sunset_min))

    if sunrise_utc.astimezone(zone).date() != local_d:
        if sunrise_utc.astimezone(zone).date() < local_d:
            sunrise_utc += timedelta(days=1)
        else:
            sunrise_utc -= timedelta(days=1)

    if sunset_utc.astimezone(zone).date() != local_d:
        if sunset_utc.astimezone(zone).date() < local_d:
            sunset_utc += timedelta(days=1)
        else:
            sunset_utc -= timedelta(days=1)

    if sunset_utc <= sunrise_utc:
        local_mid = datetime(local_d.year, local_d.month, local_d.day, 0, 0, 0, tzinfo=zone)
        sunrise_utc = local_mid.replace(hour=6).astimezone(timezone.utc)
        sunset_utc = local_mid.replace(hour=18).astimezone(timezone.utc)

    return sunrise_utc, sunset_utc

# ---------------------------
# NASA lon -> sidereal (memoized per request)
# ---------------------------
def _make_nasa_fetcher(lat: float, lon: float, ayan_deg: float):
    memo: Dict[str, Tuple[float, float]] = {}

    def sun_moon_sid(dt_utc: datetime) -> Tuple[float, float]:
        k = dt_utc.replace(second=0, microsecond=0, tzinfo=timezone.utc).isoformat()
        if k in memo:
            return memo[k]

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
        memo[k] = (sun_s, moon_s)
        return memo[k]

    return sun_moon_sid

# ---------------------------
# Solar meta
# ---------------------------
def _sun_rashi(sun_sid: float) -> int:
    return int(math.floor(wrap360(sun_sid) / 30.0)) % 12

def _ayana_from_sun_rashi(r: int) -> str:
    return "Uttarayana" if r in (9, 10, 11, 0, 1, 2) else "Dakshinayana"

def _ritu_from_sun_rashi(r: int) -> str:
    if r in (11, 0):  return "Vasanta"
    if r in (1, 2):   return "Grishma"
    if r in (3, 4):   return "Varsha"
    if r in (5, 6):   return "Sharad"
    if r in (7, 8):   return "Hemanta"
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

_SAMVATSARA_VIKRAMA_OFFSET = -3

def _samvatsara_from_vikrama(vikrama_year: int) -> Tuple[str, str]:
    idx = ((int(vikrama_year) - 1) + _SAMVATSARA_VIKRAMA_OFFSET) % 60
    return SAMVATSARA_60[idx], SAMVATSARA_60_TE[idx]

# ---------------------------
# Ultra-fast end-time estimation
# ---------------------------
def _estimate_crossing_time(
    t0: datetime, v0: float,
    t1: datetime, v1: float,
    target: float
) -> datetime:
    dt = (t1 - t0).total_seconds()
    if dt <= 0:
        return t1
    dv = (v1 - v0)
    if abs(dv) < 1e-12:
        return t1
    frac = (target - v0) / dv
    frac = max(0.0, min(1.0, float(frac)))
    return t0 + timedelta(seconds=dt * frac)

def _refine_once(fetch_sid, t_est: datetime, target_fn, target: float, t0: datetime, t1: datetime) -> datetime:
    a = max(t0, t_est - timedelta(hours=2))
    b = min(t1, t_est + timedelta(hours=2))
    va = target_fn(fetch_sid, a)
    vb = target_fn(fetch_sid, b)
    vb = unwrap_forward(vb, va)
    if (target < min(va, vb)) or (target > max(va, vb)):
        return t_est
    return _estimate_crossing_time(a, va, b, vb, target)

# ---------------------------
# ✅ Amavasya finder (stable)  <-- NEW
# ---------------------------
def _unwrap_near(v: float, ref: float) -> float:
    """Shift v by ±360 so it's closest to ref."""
    v = float(v)
    ref = float(ref)
    while (v - ref) > 180.0:
        v -= 360.0
    while (v - ref) < -180.0:
        v += 360.0
    return v

def _phase_unwrapped(fetch_sid, t_utc: datetime, ref: float, force_dir: str | None = None) -> float:
    """Moon-Sun phase in degrees, unwrapped near ref."""
    s, m = fetch_sid(t_utc)
    raw = wrap360(m - s)  # 0..360
    v = _unwrap_near(raw, ref)
    if force_dir == "back" and v > ref:
        v -= 360.0
    if force_dir == "forward" and v < ref:
        v += 360.0
    return v

def _binary_crossing(fetch_sid, t_lo: datetime, p_lo: float, t_hi: datetime, p_hi: float, target: float) -> datetime:
    """Assumes p_lo <= target <= p_hi."""
    lo_t, hi_t = t_lo, t_hi
    lo_p, hi_p = p_lo, p_hi
    for _ in range(40):
        if (hi_t - lo_t).total_seconds() <= 1:
            return hi_t
        mid = lo_t + (hi_t - lo_t) / 2
        p_mid = _phase_unwrapped(fetch_sid, mid, (lo_p + hi_p) / 2.0)
        if p_mid < target:
            lo_t, lo_p = mid, p_mid
        else:
            hi_t, hi_p = mid, p_mid
    return hi_t

def _find_last_next_amavasya(fetch_sid, t0: datetime) -> tuple[datetime, datetime]:
    """
    Find last & next amavasya around t0 using phase(Moon-Sun) crossing.
    last: phase crosses 0 going backward
    next: phase crosses 360 going forward
    """
    s0, m0 = fetch_sid(t0)
    p0 = wrap360(m0 - s0)  # 0..360

    # --- last amavasya (target 0) ---
    t_hi = t0
    p_hi = float(p0)
    found_last = False
    for d in range(1, 40):
        t_lo = t0 - timedelta(days=d)
        p_lo = _phase_unwrapped(fetch_sid, t_lo, p_hi, force_dir="back")
        if p_lo <= 0.0 <= p_hi:
            found_last = True
            last_am = _binary_crossing(fetch_sid, t_lo, p_lo, t_hi, p_hi, target=0.0)
            break
        t_hi, p_hi = t_lo, p_lo

    if not found_last:
        last_am = t0 - timedelta(days=15)

    # --- next amavasya (target 360) ---
    t_lo2 = t0
    p_lo2 = float(p0)
    found_next = False
    for d in range(1, 40):
        t_hi2 = t0 + timedelta(days=d)
        p_hi2 = _phase_unwrapped(fetch_sid, t_hi2, p_lo2, force_dir="forward")
        if p_lo2 <= 360.0 <= p_hi2:
            found_next = True
            next_am = _binary_crossing(fetch_sid, t_lo2, p_lo2, t_hi2, p_hi2, target=360.0)
            break
        t_lo2, p_lo2 = t_hi2, p_hi2

    if not found_next:
        next_am = t0 + timedelta(days=15)

    return last_am, next_am

# ---------------------------
# ✅ Adhika / Nija Masa detection (Amavasya->Amavasya)
# ---------------------------
def _masa_name_from_sun_sid(sun_sid: float) -> str:
    return LUNAR_MONTH_BY_SUN_RASHI.get(_sun_rashi(sun_sid), "—")

def _detect_adhika_kshaya(fetch_sid, prev_am_utc: datetime, next_am_utc: datetime) -> Tuple[bool, bool]:
    """
    Returns: (adhika_masa, kshaya_masa)
    ✅ Rule:
      - Adhika: rashi(prev_am) == rashi(next_am)
      - Kshaya: not computed here (rare) => False
    """
    sun_a, _ = fetch_sid(prev_am_utc)
    sun_b, _ = fetch_sid(next_am_utc)
    rA = _sun_rashi(sun_a)
    rB = _sun_rashi(sun_b)
    adhika = (rA == rB)
    kshaya = False
    return adhika, kshaya

# ---------------------------
# MAIN
# ---------------------------
def compute_panchangam(datetimeLocal: str, tz: str, lat: float, lon: float, ayan_deg: float) -> Dict[str, Any]:
    key = _panch_key(datetimeLocal, tz, float(lat), float(lon), float(ayan_deg))
    hit = _cache_get(key)
    if hit:
        return hit

    zone = ZoneInfo(tz)

    try:
        dt = datetime.fromisoformat(datetimeLocal.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt_local = dt.replace(tzinfo=zone)
        else:
            dt_local = dt.astimezone(zone)
    except Exception:
        dt_local = datetime.now(tz=zone)

    local_d = dt_local.date()

    sunrise_utc, sunset_utc = _sunrise_sunset_utc_for_local_date(
        local_d, tz, float(lat), float(lon)
    )
    next_sunrise_utc, _ = _sunrise_sunset_utc_for_local_date(
        local_d + timedelta(days=1), tz, float(lat), float(lon)
    )

    sunrise_local = sunrise_utc.astimezone(zone)
    sunset_local = sunset_utc.astimezone(zone)
    next_sunrise_local = next_sunrise_utc.astimezone(zone)

    vaara = VAARA_EN[local_d.weekday()]
    # Kala blocks
    rahu_a, rahu_b = _kala_segment(sunrise_utc, sunset_utc, _RAHU_IDX.get(vaara, 2))
    yama_a, yama_b = _kala_segment(sunrise_utc, sunset_utc, _YAMA_IDX.get(vaara, 5))
    guli_a, guli_b = _kala_segment(sunrise_utc, sunset_utc, _GULI_IDX.get(vaara, 6))
    abhi_a, abhi_b = _abhijit(sunrise_utc, sunset_utc)

    # Durmuhurtha
    durm_spans = _durmuhurta_spans(sunrise_utc, sunset_utc, vaara)
    durmuhurtha_list = [_fmt_span(zone, a, b) for (a, b) in durm_spans]

    # Choghadiya -> Amrita/Shubha windows
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

    note_extra = ""
    try:
        fetch_sid = _make_nasa_fetcher(float(lat), float(lon), float(ayan_deg))

        # 2 anchor points: sunrise and next sunrise (24h)
        sun0, moon0 = fetch_sid(sunrise_utc)
        sun1, moon1 = fetch_sid(next_sunrise_utc)

        # unwrap continuous over 24h
        sun1u = unwrap_forward(sun1, sun0)
        moon1u = unwrap_forward(moon1, moon0)

        # derived angles at sunrise and +24h
        d0 = wrap360(moon0 - sun0)  # Moon-Sun angle (0..360)
        d1 = wrap360(moon1 - sun1)
        d1u = unwrap_forward(d1, d0)

        y0 = wrap360(moon0 + sun0)
        y1 = wrap360(moon1 + sun1)
        y1u = unwrap_forward(y1, y0)

        # ---- Tithi ----
        tithi_idx = int(math.floor(d0 / TITHI_SPAN)) + 1
        tithi_name = TITHI_NAMES[(tithi_idx - 1) % 30]
        paksha = "Shukla" if 1 <= tithi_idx <= 15 else "Krishna"
        tithi_target = (math.floor(d0 / TITHI_SPAN) + 1) * TITHI_SPAN
        if tithi_target <= d0:
            tithi_target += TITHI_SPAN

        tithi_end_utc = _estimate_crossing_time(sunrise_utc, d0, next_sunrise_utc, d1u, tithi_target)

        def tithi_fn(fetch, t):
            s, m = fetch(t)
            d = wrap360(m - s)
            return unwrap_forward(d, d0)

        tithi_end_utc = _refine_once(fetch_sid, tithi_end_utc, tithi_fn, tithi_target, sunrise_utc, next_sunrise_utc)
        tithi_end_local = tithi_end_utc.astimezone(zone)

        # ---- Nakshatra ----
        nak_idx_1 = int(math.floor(moon0 / STAR_SPAN)) + 1
        nak_name = NAKSHATRA_NAMES[(nak_idx_1 - 1) % 27]
        nak_target = (math.floor(moon0 / STAR_SPAN) + 1) * STAR_SPAN
        if nak_target <= moon0:
            nak_target += STAR_SPAN

        nak_end_utc = _estimate_crossing_time(sunrise_utc, moon0, next_sunrise_utc, moon1u, nak_target)

        def moon_fn(fetch, t):
            _, m = fetch(t)
            return unwrap_forward(m, moon0)

        nak_end_utc = _refine_once(fetch_sid, nak_end_utc, moon_fn, nak_target, sunrise_utc, next_sunrise_utc)
        nak_end_local = nak_end_utc.astimezone(zone)

        # ---- Yoga ----
        yoga_idx = int(math.floor(y0 / STAR_SPAN)) + 1
        yoga_name = YOGA_NAMES[(yoga_idx - 1) % 27]
        yoga_target = (math.floor(y0 / STAR_SPAN) + 1) * STAR_SPAN
        if yoga_target <= y0:
            yoga_target += STAR_SPAN

        yoga_end_utc = _estimate_crossing_time(sunrise_utc, y0, next_sunrise_utc, y1u, yoga_target)

        def yoga_fn(fetch, t):
            s, m = fetch(t)
            y = wrap360(m + s)
            return unwrap_forward(y, y0)

        yoga_end_utc = _refine_once(fetch_sid, yoga_end_utc, yoga_fn, yoga_target, sunrise_utc, next_sunrise_utc)
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
        if kar_target <= d0:
            kar_target += KARANA_SPAN

        kar_end_utc = _estimate_crossing_time(sunrise_utc, d0, next_sunrise_utc, d1u, kar_target)
        kar_end_utc = _refine_once(fetch_sid, kar_end_utc, tithi_fn, kar_target, sunrise_utc, next_sunrise_utc)
        kar_end_local = kar_end_utc.astimezone(zone)

        # ---- Varjya from Nakshatra duration ----
        nak_start_boundary = math.floor(moon0 / STAR_SPAN) * STAR_SPAN
        prev_sunrise_utc = sunrise_utc - timedelta(days=1)
        _, moon_prev = fetch_sid(prev_sunrise_utc)
        m_prev = moon_prev
        m_cur = moon0
        m_cur_u = unwrap_forward(m_cur, m_prev)

        nak_start_utc = sunrise_utc
        if nak_start_boundary <= m_cur_u and nak_start_boundary >= m_prev:
            nak_start_utc = _estimate_crossing_time(prev_sunrise_utc, m_prev, sunrise_utc, m_cur_u, nak_start_boundary)

        nak_dur = (nak_end_utc - nak_start_utc)
        varjya_sp: List[Tuple[datetime, datetime]] = []
        if nak_dur.total_seconds() > 0:
            g0, g1 = _VARJYA_GHATI[(nak_idx_1 - 1) % 27]
            a = nak_start_utc + nak_dur * (g0 / 60.0)
            b = nak_start_utc + nak_dur * (g1 / 60.0)
            if b > a:
                varjya_sp.append((a, b))

        varjya_list = [_fmt_span(zone, a, b) for (a, b) in varjya_sp]

        # ---- Solar meta ----
        sun_r = _sun_rashi(sun0)
        ritu = _ritu_from_sun_rashi(sun_r)
        ayana = _ayana_from_sun_rashi(sun_r)

        # ----------------------------
        # ✅ Masa + Adhika/Nija (STABLE by real Amavasya bounds)
        # ----------------------------
        last_am_utc, next_am_utc = _find_last_next_amavasya(fetch_sid, sunrise_utc)

        sun_last_am, _ = fetch_sid(last_am_utc)
        sun_next_am, _ = fetch_sid(next_am_utc)

        masa_name = _masa_name_from_sun_sid(sun_last_am)
        next_masa_name = _masa_name_from_sun_sid(sun_next_am)

        adhika_masa = (masa_name == next_masa_name)

        # previous lunation (for NIJA detection)
        prevprev_am_utc, _ = _find_last_next_amavasya(fetch_sid, last_am_utc - timedelta(hours=1))
        sun_prevprev_am, _ = fetch_sid(prevprev_am_utc)
        prev_masa_name = _masa_name_from_sun_sid(sun_prevprev_am)

        # If previous lunation was adhika and current repeats same masa_name, mark NIJA
        prev_adhika, _ = _detect_adhika_kshaya(fetch_sid, prevprev_am_utc, last_am_utc)
        nija_masa = (not adhika_masa) and prev_adhika and (prev_masa_name == masa_name)

        # (kshaya not computed)
        kshaya_masa = False

        if kshaya_masa:
            masa_type = "KSHAYA"
            masa_display = f"{masa_name} (Kshaya)"
        elif adhika_masa:
            masa_type = "ADHIKA"
            masa_display = f"{masa_name} (Adhika)"
        elif nija_masa:
            masa_type = "NIJA"
            masa_display = f"{masa_name} (Nija)"
        else:
            masa_type = "NORMAL"
            masa_display = masa_name

        shaka = _approx_shaka_year(sunrise_local)
        vikrama = _approx_vikrama_year(sunrise_local)
        samv_en, samv_te = _samvatsara_from_vikrama(vikrama)

        out: Dict[str, Any] = {
            "sunrise_local": fmt_local(sunrise_local),
            "sunset_local": fmt_local(sunset_local),
            "next_sunrise_local": fmt_local(next_sunrise_local),
            "vaara": vaara,

            "masa_name": masa_name,
            "masa_type": masa_type,          # ADHIKA/NIJA/NORMAL/KSHAYA
            "masa_display": masa_display,    # pre-formatted
            "adhika_masa": bool(adhika_masa),
            "nija_masa": bool(nija_masa),
            "kshaya_masa": bool(kshaya_masa),

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
            "abhijit": _fmt_span(zone, abhi_a, abhi_b),
            "durmuhurtha": durmuhurtha_list,

            "varjya": varjya_list,
            "varjya_kaal": varjya_list,

            "amrita_ghadiya": amrita_ghadiya,
            "shubha_ghadiya": shubha_ghadiya,

            "tithi": {"name": tithi_name, "end_local": fmt_local(tithi_end_local), "end_hms": fmt_hm(tithi_end_local)},
            "nakshatra": {"name": nak_name, "end_local": fmt_local(nak_end_local), "end_hms": fmt_hm(nak_end_local)},
            "yoga": {"name": yoga_name, "end_local": fmt_local(yoga_end_local), "end_hms": fmt_hm(yoga_end_local)},
            "karana": {"name": kar_name, "end_local": fmt_local(kar_end_local), "end_hms": fmt_hm(kar_end_local)},
        }

        _cache_set(key, out)
        return out

    except Exception as e:
        note_extra = f"NASA/compute error: {type(e).__name__}"
        out: Dict[str, Any] = {
            "sunrise_local": fmt_local(sunrise_local),
            "sunset_local": fmt_local(sunset_local),
            "next_sunrise_local": fmt_local(next_sunrise_local),
            "vaara": vaara,

            "masa_name": "—",
            "masa_type": "NORMAL",
            "masa_display": "—",
            "adhika_masa": False,
            "nija_masa": False,
            "kshaya_masa": False,

            "rahu_kalam": _fmt_span(zone, rahu_a, rahu_b),
            "yamaganda": _fmt_span(zone, yama_a, yama_b),
            "gulika": _fmt_span(zone, guli_a, guli_b),
            "abhijit": _fmt_span(zone, abhi_a, abhi_b),
            "durmuhurtha": durmuhurtha_list,

            "varjya": [],
            "varjya_kaal": [],
            "amrita_ghadiya": amrita_ghadiya,
            "shubha_ghadiya": shubha_ghadiya,

            "tithi": {"name": "—", "end_local": "", "end_hms": ""},
            "nakshatra": {"name": "—", "end_local": "", "end_hms": ""},
            "yoga": {"name": "—", "end_local": "", "end_hms": ""},
            "karana": {"name": "—", "end_local": "", "end_hms": ""},

            "note": f"Fallback panchangam (no NASA). {note_extra}"
        }
        _cache_set(key, out)
        return out
    

def _jd_ut_from_dt(dt_utc: datetime) -> float:
    # Julian day UT (simple & sufficient here)
    # Algorithm: Fliegel–Van Flandern style
    y = dt_utc.year
    m = dt_utc.month
    d = dt_utc.day + (dt_utc.hour + dt_utc.minute/60 + dt_utc.second/3600) / 24.0
    if m <= 2:
        y -= 1
        m += 12
    A = math.floor(y / 100)
    B = 2 - A + math.floor(A / 4)
    jd = math.floor(365.25 * (y + 4716)) + math.floor(30.6001 * (m + 1)) + d + B - 1524.5
    return float(jd)

def _tithi_idx_from_sid(sun_sid: float, moon_sid: float) -> int:
    d = wrap360(moon_sid - sun_sid)
    return int(math.floor(d / TITHI_SPAN)) + 1  # 1..30

def _nak_idx_from_sid(moon_sid: float) -> int:
    return int(math.floor(wrap360(moon_sid) / STAR_SPAN)) + 1  # 1..27

def compute_day_base(local_d: date, tz: str, lat: float, lon: float, ayan_mode: str = "KP_OLD") -> Dict[str, Any]:
    """
    ✅ Batch-safe day base:
    - sunrise/pradosha/nishitha tithi+nakshatra
    - masa + adhika/nija bounds (your stable amavasya logic)
    - NO global cache use (so generation is correct)
    """
    zone = ZoneInfo(tz)

    sunrise_utc, sunset_utc = _sunrise_sunset_utc_for_local_date(local_d, tz, float(lat), float(lon))
    next_sunrise_utc, _ = _sunrise_sunset_utc_for_local_date(local_d + timedelta(days=1), tz, float(lat), float(lon))

    sunrise_local = sunrise_utc.astimezone(zone)
    sunset_local = sunset_utc.astimezone(zone)

    # decision points
    pradosha_utc = sunset_utc + timedelta(minutes=60)                 # sunset + 1h
    nishitha_utc = sunset_utc + (next_sunrise_utc - sunset_utc) / 2   # night midpoint

    # ayanamsa at sunrise UT (good enough for day; you can also do at each point)
    ayan_deg = get_ayanamsa_deg(_jd_ut_from_dt(sunrise_utc), ayan_mode)

    fetch_sid = _make_nasa_fetcher(float(lat), float(lon), float(ayan_deg))

    def snap(dt_utc: datetime) -> Dict[str, Any]:
        sun_sid, moon_sid = fetch_sid(dt_utc)
        ti = _tithi_idx_from_sid(sun_sid, moon_sid)  # 1..30
        ni = _nak_idx_from_sid(moon_sid)            # 1..27
        return {
            "tithi_idx": ti,
            "tithi_name": TITHI_NAMES[(ti - 1) % 30],
            "paksha": "Shukla" if ti <= 15 else "Krishna",
            "nak_idx": ni,
            "nak_name": NAKSHATRA_NAMES[(ni - 1) % 27],
        }

    sr = snap(sunrise_utc)
    pr = snap(pradosha_utc)
    ns = snap(nishitha_utc)

    # ✅ stable masa bounds (your amavasya finder)
    last_am_utc, next_am_utc = _find_last_next_amavasya(fetch_sid, sunrise_utc)

    sun_last_am, _ = fetch_sid(last_am_utc)
    sun_next_am, _ = fetch_sid(next_am_utc)

    masa_name = _masa_name_from_sun_sid(sun_last_am)
    next_masa_name = _masa_name_from_sun_sid(sun_next_am)

    adhika_masa = (masa_name == next_masa_name)

    # NIJA detect using previous lunation
    prevprev_am_utc, _ = _find_last_next_amavasya(fetch_sid, last_am_utc - timedelta(hours=1))
    sun_prevprev_am, _ = fetch_sid(prevprev_am_utc)
    prev_masa_name = _masa_name_from_sun_sid(sun_prevprev_am)
    prev_adhika, _ = _detect_adhika_kshaya(fetch_sid, prevprev_am_utc, last_am_utc)
    nija_masa = (not adhika_masa) and prev_adhika and (prev_masa_name == masa_name)

    kshaya_masa = False  # (rare; can be added later using ingress-count method)

    if kshaya_masa:
        masa_type = "KSHAYA"
    elif adhika_masa:
        masa_type = "ADHIKA"
    elif nija_masa:
        masa_type = "NIJA"
    else:
        masa_type = "NORMAL"

    return {
        "date": local_d.isoformat(),
        "tz": tz,
        "lat": float(lat),
        "lon": float(lon),

        "sunrise_local": fmt_local(sunrise_local),
        "sunset_local": fmt_local(sunset_local),
        "pradosha_local": fmt_local(pradosha_utc.astimezone(zone)),
        "nishitha_local": fmt_local(nishitha_utc.astimezone(zone)),

        "at_sunrise": sr,
        "at_pradosha": pr,
        "at_nishitha": ns,

        "masa_name": masa_name,
        "masa_type": masa_type,
        "adhika_masa": bool(adhika_masa),
        "nija_masa": bool(nija_masa),
        "kshaya_masa": bool(kshaya_masa),

        "amavasya_prev_utc": last_am_utc.isoformat().replace("+00:00", "Z"),
        "amavasya_next_utc": next_am_utc.isoformat().replace("+00:00", "Z"),
        "ayan_mode": ayan_mode,
        "ayan_deg": float(ayan_deg),
    }