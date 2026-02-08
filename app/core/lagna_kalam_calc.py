# app/core/lagna_kalam_calc.py ✅ FULL REPLACE (export-safe)
from __future__ import annotations

from datetime import datetime, timedelta, timezone, date
from zoneinfo import ZoneInfo
from typing import Dict, Any, List, Tuple
import math

from app.core.nasa_ephemeris import get_planets_ecliptic
from app.core.ayanamsa_exact import get_ayanamsa_deg
from app.core.houses_placidus import placidus_cusps
from app.core.panchangam_calc import _sunrise_sunset_utc_for_local_date

SIGNS_EN = [
    "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
    "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"
]

def _wrap360(x: float) -> float:
    x = float(x) % 360.0
    return x if x >= 0 else x + 360.0

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

def _local_to_utc_iso(dt_local_naive: datetime, tz: str) -> str:
    zone = ZoneInfo(tz)
    aware_local = dt_local_naive.replace(tzinfo=zone)
    aware_utc = aware_local.astimezone(timezone.utc)
    return aware_utc.isoformat().replace("+00:00", "Z")

def _jd_ut_for_local(dt_local_naive: datetime, tz: str, lat: float, lon: float) -> float:
    utc_iso = _local_to_utc_iso(dt_local_naive, tz)
    jd_ut, _ = get_planets_ecliptic(utc_iso, float(lat), float(lon))
    return float(jd_ut)

def _asc_sidereal_deg(dt_local_naive: datetime, tz: str, lat: float, lon: float, ay_mode: str) -> float:
    jd_ut = _jd_ut_for_local(dt_local_naive, tz, lat, lon)
    cusps = placidus_cusps(jd_ut, float(lat), float(lon))  # tropical
    asc_trop = float(cusps["asc"])
    ay_deg = float(get_ayanamsa_deg(jd_ut, ay_mode))
    return _wrap360(asc_trop - ay_deg)

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

def _forward_dist_to(target: float, x: float) -> float:
    return (_wrap360(target - x) + 360.0) % 360.0

def _find_crossing_time(
    target_deg: float,
    t_left: datetime,
    t_right: datetime,
    tz: str,
    lat: float,
    lon: float,
    ay_mode: str,
    max_iter: int = 40
) -> datetime:
    target = _wrap360(target_deg)

    for _ in range(max_iter):
        if (t_right - t_left).total_seconds() <= 1:
            return t_left

        mid = t_left + (t_right - t_left) / 2

        aL = _asc_sidereal_deg(t_left, tz, lat, lon, ay_mode)
        aM = _asc_sidereal_deg(mid, tz, lat, lon, ay_mode)

        dL = _forward_dist_to(target, aL)
        dM = _forward_dist_to(target, aM)

        if dM < dL:
            t_left = mid
        else:
            t_right = mid

    return t_left

# ✅ IMPORTANT: This is the symbol your route imports
def compute_lagna_kalam(dateKey: str, tz: str, lat: float, lon: float, ayanamsa: str) -> Dict[str, Any]:
    """
    Lagna Kalam: sunrise -> next sunrise
    Show exact sign boundary crossings based on ASC (sidereal).
    """
    ay_mode = _ayan_mode_normalize(ayanamsa)
    sunrise_local, next_sunrise_local = _sunrise_nextsunrise_local(dateKey, tz, lat, lon)

    asc0 = _asc_sidereal_deg(sunrise_local, tz, lat, lon, ay_mode)
    cur_sign = _sign_index(asc0)
    cur_start = sunrise_local
    cur_start_deg_in = _deg_in_sign(asc0)

    items: List[Dict[str, Any]] = []

    for i in range(12):
        boundary = ((cur_sign + 1) * 30) % 360.0

        # bracket search (scan forward in 20-min steps)
        tA = cur_start
        tB = min(cur_start + timedelta(minutes=20), next_sunrise_local)

        aA = _asc_sidereal_deg(tA, tz, lat, lon, ay_mode)
        dA = _forward_dist_to(boundary, aA)

        found = False
        while tB <= next_sunrise_local:
            aB = _asc_sidereal_deg(tB, tz, lat, lon, ay_mode)
            dB = _forward_dist_to(boundary, aB)

            # when distance starts decreasing, we're approaching the boundary
            if dB < dA:
                found = True
                break

            tA = tB
            dA = dB
            tB = min(tB + timedelta(minutes=20), next_sunrise_local)

            if tA >= next_sunrise_local:
                break

        if found and tA < next_sunrise_local:
            end_time = _find_crossing_time(boundary, tA, tB, tz, lat, lon, ay_mode)
        else:
            end_time = next_sunrise_local

        asc_end = _asc_sidereal_deg(end_time, tz, lat, lon, ay_mode)
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

        # next sign
        cur_start = end_time
        cur_sign = (cur_sign + 1) % 12
        cur_start_deg_in = 0.0

    return {
        "sunrise_local": _fmt_local_iso(sunrise_local),
        "next_sunrise_local": _fmt_local_iso(next_sunrise_local),
        "items": items,
    }
