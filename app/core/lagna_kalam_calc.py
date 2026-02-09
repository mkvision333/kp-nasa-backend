# app/core/lagna_kalam_calc.py ✅ FULL REPLACE (KP-correct sunrise, CPU-safe, no Skyfield loop)
from __future__ import annotations

from datetime import datetime, timedelta, timezone, date
from zoneinfo import ZoneInfo
from typing import Dict, Any, List, Tuple
import math

from app.core.ayanamsa_exact import get_ayanamsa_deg
from app.core.panchangam_calc import _sunrise_sunset_utc_for_local_date

SIGNS_EN = [
    "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
    "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"
]

# -------------------------
# helpers
# -------------------------
def _wrap360(x: float) -> float:
    x = float(x) % 360.0
    return x if x >= 0 else x + 360.0

def _deg2rad(d: float) -> float:
    return float(d) * math.pi / 180.0

def _rad2deg(r: float) -> float:
    return float(r) * 180.0 / math.pi

def _sign_index(deg: float) -> int:
    return int(math.floor(_wrap360(deg) / 30.0)) % 12

def _deg_in_sign(deg: float) -> float:
    return _wrap360(deg) % 30.0

def _fmt_local_iso(dt_local_naive: datetime) -> str:
    return dt_local_naive.strftime("%Y-%m-%dT%H:%M:%S")

def _parse_datekey(dk: str) -> date:
    return date.fromisoformat(dk)

def _ayan_mode_normalize(ayanamsa: str) -> str:
    a = (ayanamsa or "KP_OLD").strip().upper()
    if a in ("KP", "KRISHNAMURTI"):
        return "KP_OLD"
    if a in ("KPO", "KPOLD"):
        return "KP_OLD"
    if a in ("KPN", "KPNEW", "VP291", "SENTHILATHIBAN"):
        return "KP_NEW"
    if a in ("LAHIRI", "CHITRAPAKSHA"):
        return "LAHIRI"
    return "KP_OLD"

def _local_to_utc_dt(dt_local_naive: datetime, tz: str) -> datetime:
    zone = ZoneInfo(tz)
    aware_local = dt_local_naive.replace(tzinfo=zone)
    return aware_local.astimezone(timezone.utc)

def _datetime_utc_to_jd(dt_utc: datetime) -> float:
    """UTC datetime -> Julian Day (UT). FAST math (no skyfield)."""
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
    dt_utc = dt_utc.astimezone(timezone.utc)

    y = dt_utc.year
    m = dt_utc.month
    D = dt_utc.day

    frac = (dt_utc.hour + (dt_utc.minute + (dt_utc.second + dt_utc.microsecond / 1e6) / 60.0) / 60.0) / 24.0
    d = D + frac

    if m <= 2:
        y -= 1
        m += 12

    A = y // 100
    B = 2 - A + (A // 4)
    jd = int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + B - 1524.5
    return float(jd)

def _jd_ut_for_local(dt_local_naive: datetime, tz: str) -> float:
    utc_dt = _local_to_utc_dt(dt_local_naive, tz)
    return _datetime_utc_to_jd(utc_dt)

# -------------------------
# FAST Ascendant (no placidus)
# -------------------------
def _mean_obliquity_deg(jd: float) -> float:
    T = (jd - 2451545.0) / 36525.0
    eps_arcsec = 84381.448 - 46.8150 * T - 0.00059 * (T ** 2) + 0.001813 * (T ** 3)
    return eps_arcsec / 3600.0

def _gmst_deg(jd: float) -> float:
    T = (jd - 2451545.0) / 36525.0
    gmst = 280.46061837 + 360.98564736629 * (jd - 2451545.0) + 0.000387933 * T * T - (T ** 3) / 38710000.0
    return _wrap360(gmst)

def _asc_tropical_deg(jd: float, lat: float, lon: float) -> float:
    """
    Tropical Asc from Local Sidereal Time.
    lon east positive ✅ (India positive)
    """
    eps = _deg2rad(_mean_obliquity_deg(jd))
    phi = _deg2rad(float(lat))

    lst = _wrap360(_gmst_deg(jd) + float(lon))
    theta = _deg2rad(lst)

    # quadrant-safe
    y = math.cos(theta)
    x = math.sin(theta) * math.cos(eps) - math.tan(phi) * math.sin(eps)

    asc = math.atan2(y, x)
    asc_deg = _wrap360(_rad2deg(asc) + 180.0)
    return asc_deg

def _asc_sidereal_deg(dt_local_naive: datetime, tz: str, lat: float, lon: float, ay_deg: float) -> float:
    jd = _jd_ut_for_local(dt_local_naive, tz)
    asc_trop = _asc_tropical_deg(jd, float(lat), float(lon))
    return _wrap360(asc_trop - float(ay_deg))

# -------------------------
# sunrise helpers (KP correct)
# -------------------------
def _sunrise_nextsunrise_local(dateKey: str, tz: str, lat: float, lon: float) -> Tuple[datetime, datetime]:
    zone = ZoneInfo(tz)
    d0 = _parse_datekey(dateKey)
    sunrise_utc, _ = _sunrise_sunset_utc_for_local_date(d0, tz, float(lat), float(lon))
    next_sunrise_utc, _ = _sunrise_sunset_utc_for_local_date(d0 + timedelta(days=1), tz, float(lat), float(lon))

    sunrise_local = sunrise_utc.astimezone(zone).replace(tzinfo=None)
    next_sunrise_local = next_sunrise_utc.astimezone(zone).replace(tzinfo=None)

    if next_sunrise_local <= sunrise_local:
        next_sunrise_local = sunrise_local + timedelta(hours=24)
    return sunrise_local, next_sunrise_local

def _find_crossing_time_by_signchange(
    cur_sign: int,
    t_left: datetime,
    t_right: datetime,
    tz: str,
    lat: float,
    lon: float,
    ay_deg: float,
    max_iter: int = 34
) -> datetime:
    # ensure bracket
    aL = _asc_sidereal_deg(t_left, tz, lat, lon, ay_deg)
    aR = _asc_sidereal_deg(t_right, tz, lat, lon, ay_deg)

    if _sign_index(aL) != cur_sign:
        return t_left
    if _sign_index(aR) == cur_sign:
        return t_right

    for _ in range(max_iter):
        if (t_right - t_left).total_seconds() <= 1:
            return t_right
        mid = t_left + (t_right - t_left) / 2
        aM = _asc_sidereal_deg(mid, tz, lat, lon, ay_deg)
        if _sign_index(aM) == cur_sign:
            t_left = mid
        else:
            t_right = mid
    return t_right

# ✅ route imports this
def compute_lagna_kalam(dateKey: str, tz: str, lat: float, lon: float, ayanamsa: str) -> Dict[str, Any]:
    """
    KP-correct Lagna Kalam:
    - Start at SUNRISE local (accurate from your panchangam calc)
    - Asc computed FAST via sidereal-time formula
    - Ayanamsa computed once per request
    - Step scan + binary refinement (no minute loop, no CPU hang)
    """
    ay_mode = _ayan_mode_normalize(ayanamsa)
    sunrise_local, next_sunrise_local = _sunrise_nextsunrise_local(dateKey, tz, lat, lon)

    # ✅ ayanamsa once
    jd0 = _jd_ut_for_local(sunrise_local, tz)
    ay_deg = float(get_ayanamsa_deg(jd0, ay_mode))

    asc0 = _asc_sidereal_deg(sunrise_local, tz, float(lat), float(lon), ay_deg)
    cur_sign = _sign_index(asc0)
    cur_start = sunrise_local
    cur_start_deg_in = _deg_in_sign(asc0)

    items: List[Dict[str, Any]] = []

    STEP_MIN = 5  # fast + reliable
    for i in range(12):
        tA = cur_start
        tB = min(cur_start + timedelta(minutes=STEP_MIN), next_sunrise_local)
        found = False

        while tB <= next_sunrise_local:
            aB = _asc_sidereal_deg(tB, tz, float(lat), float(lon), ay_deg)
            if _sign_index(aB) != cur_sign:
                found = True
                break
            tA = tB
            tB = min(tB + timedelta(minutes=STEP_MIN), next_sunrise_local)
            if tA >= next_sunrise_local:
                break

        if found and tA < next_sunrise_local:
            end_time = _find_crossing_time_by_signchange(cur_sign, tA, tB, tz, float(lat), float(lon), ay_deg)
        else:
            end_time = next_sunrise_local

        asc_end = _asc_sidereal_deg(end_time, tz, float(lat), float(lon), ay_deg)
        end_deg_in = _deg_in_sign(asc_end)
        dur_min = int(round((end_time - cur_start).total_seconds() / 60.0))

        items.append({
            "idx": i + 1,
            "sign": SIGNS_EN[cur_sign],
            "start_local": _fmt_local_iso(cur_start),
            "end_local": _fmt_local_iso(end_time),
            "start_deg_in_sign": round(float(cur_start_deg_in), 4),
            "end_deg_in_sign": round(float(end_deg_in), 4),
            "duration_min": int(dur_min),
        })

        if end_time >= next_sunrise_local:
            break

        cur_start = end_time
        cur_sign = (cur_sign + 1) % 12
        cur_start_deg_in = 0.0

    return {
        "sunrise_local": _fmt_local_iso(sunrise_local),
        "next_sunrise_local": _fmt_local_iso(next_sunrise_local),
        "items": items,
    }
