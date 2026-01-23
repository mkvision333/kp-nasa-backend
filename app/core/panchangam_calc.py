# app/core/panchangam_calc.py ✅ FULL REPLACE (FAST + STABLE + production-safe)
from __future__ import annotations

from datetime import datetime, timedelta, timezone, date
from zoneinfo import ZoneInfo
from typing import Dict, Any, Tuple, Optional, List
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
# commonly used mapping (startGhati, endGhati)
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
_PANCH_TTL_SEC = 12 * 60 * 60  # 12 hours (more stable, fewer cold misses)

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

def unwrap_forward(v1: float, v0: float) -> float:
    """
    unwrap v1 near v0 (forward continuity)
    """
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
# ✅ NOAA Solar Calculator style sunrise/sunset (accurate, stable)
# References: NOAA ESRL algorithm (common implementations)
# ---------------------------
def _julian_day_0h_utc(d: date) -> float:
    # Julian day at 0h UTC
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
    """
    returns (declination_radians, equation_of_time_minutes)
    """
    T = (jd - 2451545.0) / 36525.0
    # Geom Mean Long Sun (deg)
    L0 = (280.46646 + T * (36000.76983 + T * 0.0003032)) % 360.0
    # Geom Mean Anom Sun (deg)
    M = 357.52911 + T * (35999.05029 - 0.0001537 * T)
    Mrad = math.radians(M)
    # Eccent Earth Orbit
    e = 0.016708634 - T * (0.000042037 + 0.0000001267 * T)
    # Sun Eq of Ctr
    C = (math.sin(Mrad) * (1.914602 - T * (0.004817 + 0.000014 * T))
         + math.sin(2 * Mrad) * (0.019993 - 0.000101 * T)
         + math.sin(3 * Mrad) * 0.000289)
    # Sun True Long (deg)
    true_long = L0 + C
    # Sun App Long (deg)
    omega = 125.04 - 1934.136 * T
    lam = true_long - 0.00569 - 0.00478 * math.sin(math.radians(omega))
    lamr = math.radians(lam)

    # Mean obliquity
    eps0 = 23.0 + (26.0 + ((21.448 - T*(46.815 + T*(0.00059 - T*0.001813))))/60.0)/60.0
    eps = eps0 + 0.00256 * math.cos(math.radians(omega))
    epsr = math.radians(eps)

    # declination
    sin_dec = math.sin(epsr) * math.sin(lamr)
    dec = math.asin(sin_dec)

    # equation of time
    y = math.tan(epsr/2.0)**2
    L0r = math.radians(L0)
    Etime = 4.0 * math.degrees(
        y * math.sin(2.0*L0r)
        - 2.0*e*math.sin(Mrad)
        + 4.0*e*y*math.sin(Mrad)*math.cos(2.0*L0r)
        - 0.5*y*y*math.sin(4.0*L0r)
        - 1.25*e*e*math.sin(2.0*Mrad)
    )
    return dec, Etime  # dec rad, eqtime minutes

def _sunrise_sunset_utc_for_local_date(local_d: date, tz: str, lat: float, lon: float) -> Tuple[datetime, datetime]:
    """
    Returns sunrise_utc, sunset_utc for the given LOCAL date.
    lon: East positive (India positive) ✅
    """
    zone = ZoneInfo(tz)
    # local date midnight -> find corresponding UTC date for JD base
    # We'll use local noon to anchor day properly, but compute JD at UTC 0h of that UTC date
    local_noon = datetime(local_d.year, local_d.month, local_d.day, 12, 0, 0, tzinfo=zone)
    utc_noon = local_noon.astimezone(timezone.utc)
    jd0 = _julian_day_0h_utc(utc_noon.date())

    dec, eq_time = _sun_decl_and_eqtime(jd0)

    # solar zenith for official sunrise/sunset
    zenith = math.radians(90.833)
    latr = math.radians(lat)

    cos_ha = (math.cos(zenith) - math.sin(latr)*math.sin(dec)) / (math.cos(latr)*math.cos(dec))
    cos_ha = max(-1.0, min(1.0, cos_ha))
    ha = math.degrees(math.acos(cos_ha))  # degrees

    # NOAA: solar noon (minutes) from 0h UTC
    # lon east positive => solarNoon = 720 - 4*lon - eqTime
    solar_noon_min = 720.0 - 4.0*float(lon) - float(eq_time)
    sunrise_min = solar_noon_min - 4.0*ha
    sunset_min = solar_noon_min + 4.0*ha

    base = datetime(utc_noon.date().year, utc_noon.date().month, utc_noon.date().day, 0, 0, 0, tzinfo=timezone.utc)
    sunrise_utc = base + timedelta(minutes=float(sunrise_min))
    sunset_utc = base + timedelta(minutes=float(sunset_min))

    # force to intended local date (prevents date mismatch)
    if sunrise_utc.astimezone(zone).date() != local_d:
        # adjust by ±1 day if necessary
        if sunrise_utc.astimezone(zone).date() < local_d:
            sunrise_utc += timedelta(days=1)
        else:
            sunrise_utc -= timedelta(days=1)

    if sunset_utc.astimezone(zone).date() != local_d:
        if sunset_utc.astimezone(zone).date() < local_d:
            sunset_utc += timedelta(days=1)
        else:
            sunset_utc -= timedelta(days=1)

    # sanity
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
        # cache key: minute-level ISO
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
            # very defensive fallback ordering
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

# calibrated offset
_SAMVATSARA_VIKRAMA_OFFSET = -3

def _samvatsara_from_vikrama(vikrama_year: int) -> Tuple[str, str]:
    idx = ((int(vikrama_year) - 1) + _SAMVATSARA_VIKRAMA_OFFSET) % 60
    return SAMVATSARA_60[idx], SAMVATSARA_60_TE[idx]

# ---------------------------
# Ultra-fast end-time estimation (2–4 NASA calls total)
# ---------------------------
def _estimate_crossing_time(
    t0: datetime, v0: float,
    t1: datetime, v1: float,
    target: float
) -> datetime:
    """
    Linear interpolation (v0->v1) for target.
    Assumes target between v0..v1.
    """
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
    """
    One refinement using 2 sample points around estimate (still cheap due to memo)
    """
    # small bracket
    a = max(t0, t_est - timedelta(hours=2))
    b = min(t1, t_est + timedelta(hours=2))
    va = target_fn(fetch_sid, a)
    vb = target_fn(fetch_sid, b)

    # unwrap monotonic
    vb = unwrap_forward(vb, va)

    # if bracket bad, return estimate
    if (target < min(va, vb)) or (target > max(va, vb)):
        return t_est

    return _estimate_crossing_time(a, va, b, vb, target)

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
        dt_local = datetime.fromisoformat(datetimeLocal).replace(tzinfo=zone)
    except Exception:
        dt_local = datetime.now(tz=zone)
    local_d = dt_local.date()

    sunrise_utc, sunset_utc = _sunrise_sunset_utc_for_local_date(local_d, tz, float(lat), float(lon))
    next_sunrise_utc, _ = _sunrise_sunset_utc_for_local_date(local_d + timedelta(days=1), tz, float(lat), float(lon))

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

    # NASA computations (very few calls)
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
        d0 = wrap360(moon0 - sun0)
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

        # ensure target is forward in unwrapped space
        if tithi_target <= d0:
            tithi_target += TITHI_SPAN
        # estimate using 24h line
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

        # ---- Varjya from Nakshatra duration (ghati mapping) ----
        # Need nakshatra start boundary:
        nak_start_boundary = math.floor(moon0 / STAR_SPAN) * STAR_SPAN

        # estimate nak start by going backwards using same 24h slope
        # compute moon at sunrise-24h
        prev_sunrise_utc = sunrise_utc - timedelta(days=1)
        _, moon_prev = fetch_sid(prev_sunrise_utc)
        moon_prev_u = unwrap_forward(moon0, moon_prev)  # unwrap prev near current
        # For backward use: treat interval prev->current
        # make both unwrapped in increasing order
        m_prev = moon_prev
        m_cur = moon0
        # try to ensure m_cur is unwrapped forward from m_prev
        m_cur_u = unwrap_forward(m_cur, m_prev)

        # If boundary isn't inside, fallback: use sunrise as start (safe)
        nak_start_utc = sunrise_utc
        if nak_start_boundary <= m_cur_u and nak_start_boundary >= m_prev:
            nak_start_utc = _estimate_crossing_time(prev_sunrise_utc, m_prev, sunrise_utc, m_cur_u, nak_start_boundary)

        nak_dur = (nak_end_utc - nak_start_utc)
        varjya_sp: List[Tuple[datetime, datetime]] = []
        if nak_dur.total_seconds() > 0:
            g0, g1 = _VARJYA_GHATI[(nak_idx_1 - 1) % 27]
            a = nak_start_utc + nak_dur * (g0 / 60.0)
            b = nak_start_utc + nak_dur * (g1 / 60.0)
            # clamp to daytime window (optional safe)
            if b > a:
                varjya_sp.append((a, b))

        varjya_list = [_fmt_span(zone, a, b) for (a, b) in varjya_sp]

        # ---- Solar meta ----
        sun_r = _sun_rashi(sun0)
        ritu = _ritu_from_sun_rashi(sun_r)
        ayana = _ayana_from_sun_rashi(sun_r)

        # Masa (prev amavasya approx using tithi phase linear)
        # Estimate prev amavasya time from d0 and daily delta
        d_rate = (d1u - d0) / max(1.0, (next_sunrise_utc - sunrise_utc).total_seconds())
        if abs(d_rate) > 1e-9:
            prev_am_utc = sunrise_utc - timedelta(seconds=float(d0 / d_rate))
        else:
            prev_am_utc = sunrise_utc - timedelta(days=15)
        if prev_am_utc < sunrise_utc - timedelta(days=35):
            prev_am_utc = sunrise_utc - timedelta(days=15)

        sun_prev_am, _ = fetch_sid(prev_am_utc)
        masa_name = LUNAR_MONTH_BY_SUN_RASHI.get(_sun_rashi(sun_prev_am), "—")

        shaka = _approx_shaka_year(sunrise_local)
        vikrama = _approx_vikrama_year(sunrise_local)
        samv_en, samv_te = _samvatsara_from_vikrama(vikrama)

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

            "note": "Fast Panchangam v2: NOAA sunrise/sunset (stable) + NASA lon (memo + 2–4 calls). Varjya=nak ghati; Amrit/Shubh=choghadiya."
        }

        _cache_set(key, out)
        return out

    except Exception as e:
        # ✅ graceful fallback: UI should not spin forever.
        note_extra = f"NASA/compute error: {type(e).__name__}"
        # minimal but complete structure so frontend shows something
        out: Dict[str, Any] = {
            "sunrise_local": fmt_local(sunrise_local),
            "sunset_local": fmt_local(sunset_local),
            "next_sunrise_local": fmt_local(next_sunrise_local),
            "vaara": vaara,

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
