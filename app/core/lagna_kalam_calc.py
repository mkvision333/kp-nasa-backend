from __future__ import annotations
from datetime import datetime, timedelta, timezone, date
from zoneinfo import ZoneInfo
from typing import Dict, Any, List, Tuple
import math

# మీ ప్రాజెక్ట్ లోని ఇతర ఫైల్స్ నుండి ఇంపోర్ట్స్
from app.core.ayanamsa_exact import get_ayanamsa_deg
from app.core.panchangam_calc import _sunrise_sunset_utc_for_local_date

SIGNS_EN = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

def _wrap360(x: float) -> float:
    return float(x % 360.0)

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

def _datetime_utc_to_jd(dt_utc: datetime) -> float:
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
    
    y, m, D = dt_utc.year, dt_utc.month, dt_utc.day
    frac = (dt_utc.hour + (dt_utc.minute + (dt_utc.second + dt_utc.microsecond / 1e6) / 60.0) / 60.0) / 24.0
    d = D + frac

    if m <= 2:
        y -= 1
        m += 12

    A = y // 100
    B = 2 - A + (A // 4)
    jd = int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + B - 1524.5
    return float(jd)

def _get_asc_at_time(dt_naive: datetime, tz_str: str, lat: float, lon: float, ay_deg: float) -> float:
    """నిర్దిష్ట సమయానికి నిరయన లగ్న డిగ్రీలను ఇస్తుంది."""
    zone = ZoneInfo(tz_str)
    utc_dt = dt_naive.replace(tzinfo=zone).astimezone(timezone.utc)
    jd = _datetime_utc_to_jd(utc_dt)
    
    # Obliquity & Sidereal Time
    T = (jd - 2451545.0) / 36525.0
    eps = _deg2rad((84381.448 - 46.8150 * T) / 3600.0)
    gmst = 280.46061837 + 360.98564736629 * (jd - 2451545.0)
    lst = _deg2rad(_wrap360(gmst + float(lon)))
    phi = _deg2rad(float(lat))

    # Ascendant Calculation
    y = math.cos(lst)
    x = -(math.sin(lst) * math.cos(eps) + math.tan(phi) * math.sin(eps))
    
    # MK Fix: 180 deg flip adjustment
    asc_trop = _rad2deg(math.atan2(y, x))
    return _wrap360(asc_trop - ay_deg)

def _find_exact_crossing(t1: datetime, t2: datetime, target_sign: int, tz: str, lat: float, lon: float, ay_deg: float) -> datetime:
    """Binary search to find exact time when Lagna changes sign."""
    for _ in range(12): # 12 iterations gives ~1 second precision
        mid = t1 + (t2 - t1) / 2
        if _sign_index(_get_asc_at_time(mid, tz, lat, lon, ay_deg)) == target_sign:
            t1 = mid
        else:
            t2 = mid
    return t2

def compute_lagna_kalam(date_str: str, tz: str, lat: float, lon: float, ayanamsa_mode: str) -> Dict[str, Any]:
    d0 = date.fromisoformat(date_str)
    zone = ZoneInfo(tz)
    
    # సూర్యోదయ సమయాలు
    sr_utc, _ = _sunrise_sunset_utc_for_local_date(d0, tz, lat, lon)
    nsr_utc, _ = _sunrise_sunset_utc_for_local_date(d0 + timedelta(days=1), tz, lat, lon)
    
    curr_t = sr_utc.astimezone(zone).replace(tzinfo=None)
    end_t_limit = nsr_utc.astimezone(zone).replace(tzinfo=None)
    
    # Ayanamsa (Calculated at sunrise for the day)
    ay_deg = get_ayanamsa_deg(_datetime_utc_to_jd(sr_utc), ayanamsa_mode)
    
    items = []
    idx = 1
    
    while curr_t < end_t_limit and idx <= 13:
        asc_now = _get_asc_at_time(curr_t, tz, lat, lon, ay_deg)
        curr_sign = _sign_index(asc_now)
        
        # 2 గంటల తర్వాత లగ్నం మారుతుందని ఒక అంచనా (Astrological average)
        # కానీ ఖచ్చితత్వం కోసం 10 నిమిషాల స్టెప్స్ తో స్కాన్
        scan_t = curr_t + timedelta(minutes=10)
        while scan_t < end_t_limit:
            if _sign_index(_get_asc_at_time(scan_t, tz, lat, lon, ay_deg)) != curr_sign:
                break
            scan_t += timedelta(minutes=10)
        
        # Binary search for exact crossing
        crossing_t = _find_exact_crossing(scan_t - timedelta(minutes=10), min(scan_t, end_t_limit), curr_sign, tz, lat, lon, ay_deg)
        
        if crossing_t > end_t_limit: crossing_t = end_t_limit

        items.append({
            "idx": idx,
            "sign": SIGNS_EN[curr_sign],
            "start_local": _fmt_local_iso(curr_t),
            "end_local": _fmt_local_iso(crossing_t),
            "duration_min": round((crossing_t - curr_t).total_seconds() / 60)
        })
        
        curr_t = crossing_t
        idx += 1
        if curr_t >= end_t_limit: break

    return {
        "date": date_str,
        "sunrise": _fmt_local_iso(sr_utc.astimezone(zone).replace(tzinfo=None)),
        "lagnas": items
    }