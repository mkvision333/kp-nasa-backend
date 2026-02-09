# app/core/lagna_kalam_calc.py ✅ FULL REPLACE (fast + correct, sign-change bracket)
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

# -----------------------------
# Basics
# -----------------------------
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
    if a in ("KPO", "KPOLD", "KP_OLD"):
        return "KP_OLD"
    if a in ("KPN", "KPNEW", "KP_NEW", "VP291", "SENTHILATHIBAN"):
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
    """
    ASC (tropical) from placidus -> subtract ayanamsa -> sidereal ASC
    """
    jd_ut = _jd_ut_for_local(dt_local_naive, tz, lat, lon)
    cusps = placidus_cusps(jd_ut, float(lat), float(lon))  # tropical
    # NOTE: your houses_placidus returns keys: "asc" (as used in main.py)
    asc_trop = float(cusps["asc"])
    ay_deg = float(get_ayanamsa_deg(jd_ut, ay_mode))
    return _wrap360(asc_trop - ay_deg)

def _sunrise_nextsunrise_local(dateKey: str, tz: str, lat: float, lon: float) -> Tuple[datetime, datetime]:
    """
    KP-style day boundary: sunrise -> next sunrise (local times, naive)
    """
    zone = ZoneInfo(tz)
    d0 = _parse_datekey(dateKey)

    sunrise_utc, _ = _sunrise_sunset_utc_for_local_date(d0, tz, float(lat), float(lon))
    next_sunrise_utc, _ = _sunrise_sunset_utc_for_local_date(d0 + timedelta(days=1), tz, float(lat), float(lon))

    sunrise_local = sunrise_utc.astimezone(zone).replace(tzinfo=None)
    next_sunrise_local = next_sunrise_utc.astimezone(zone).replace(tzinfo=None)

    # safety
    if next_sunrise_local <= sunrise_local:
        next_sunrise_local = sunrise_local + timedelta(hours=24)

    return sunrise_local, next_sunrise_local

def _binary_find_crossing_by_sign(
    t_left: datetime,
    t_right: datetime,
    tz: str,
    lat: float,
    lon: float,
    ay_mode: str,
    sign_left: int,
    max_iter: int = 18,
) -> datetime:
    """
    Find earliest time when sign != sign_left within [t_left, t_right]
    Assumes sign changes inside interval.
    18 iters ~ sub-second to few seconds depending on interval.
    """
    lo = t_left
    hi = t_right
    for _ in range(max_iter):
        if (hi - lo).total_seconds() <= 1:
            break
        mid = lo + (hi - lo) / 2
        s_mid = _sign_index(_asc_sidereal_deg(mid, tz, lat, lon, ay_mode))
        if s_mid == sign_left:
            lo = mid
        else:
            hi = mid
    return hi

# ✅ IMPORTANT: This is the symbol your route imports
def compute_lagna_kalam(dateKey: str, tz: str, lat: float, lon: float, ayanamsa: str) -> Dict[str, Any]:
    """
    Lagna Kalam (KP style):
      - Window: sunrise -> next sunrise (local)
      - Lagna boundaries by ASC sidereal sign changes (0°..30°)
      - Fast: coarse step + binary refine (no CPU hang)
    """
    ay_mode = _ayan_mode_normalize(ayanamsa)

    sunrise_local, next_sunrise_local = _sunrise_nextsunrise_local(dateKey, tz, lat, lon)

    # Start at sunrise
    t0 = sunrise_local
    asc0 = _asc_sidereal_deg(t0, tz, lat, lon, ay_mode)
    sign0 = _sign_index(asc0)
    start_deg_in = _deg_in_sign(asc0)

    items: List[Dict[str, Any]] = []

    cur_start = t0
    cur_sign = sign0
    cur_start_deg_in = start_deg_in

    # Coarse scan step: 10 minutes (fast). If needed can reduce to 5.
    STEP_MIN = 10

    # safety cap
    max_items = 14  # sometimes you may see 13 due to boundary near sunrise
    safety_loops = 0

    while cur_start < next_sunrise_local and len(items) < max_items:
        safety_loops += 1
        if safety_loops > 40:
            break

        # scan forward until sign changes or end
        t_prev = cur_start
        s_prev = cur_sign

        t_scan = min(cur_start + timedelta(minutes=STEP_MIN), next_sunrise_local)
        s_scan = _sign_index(_asc_sidereal_deg(t_scan, tz, lat, lon, ay_mode))

        # If already changed within first step, bracket is [cur_start, t_scan]
        while s_scan == s_prev and t_scan < next_sunrise_local:
            t_prev = t_scan
            t_scan = min(t_scan + timedelta(minutes=STEP_MIN), next_sunrise_local)
            s_scan = _sign_index(_asc_sidereal_deg(t_scan, tz, lat, lon, ay_mode))

        if s_scan == s_prev:
            # no change until next sunrise
            end_time = next_sunrise_local
        else:
            # bracket found: [t_prev, t_scan] contains crossing
            end_time = _binary_find_crossing_by_sign(
                t_left=t_prev,
                t_right=t_scan,
                tz=tz,
                lat=float(lat),
                lon=float(lon),
                ay_mode=ay_mode,
                sign_left=s_prev,
            )

        # Ensure progress (avoid zero duration due to rounding edge)
        if end_time <= cur_start:
            end_time = min(cur_start + timedelta(seconds=1), next_sunrise_local)

        asc_end = _asc_sidereal_deg(end_time, tz, lat, lon, ay_mode)
        end_deg_in = _deg_in_sign(asc_end)
        dur_min = int(round((end_time - cur_start).total_seconds() / 60.0))

        items.append({
            "idx": len(items) + 1,
            "sign": SIGNS_EN[cur_sign],
            "start_local": _fmt_local_iso(cur_start),
            "end_local": _fmt_local_iso(end_time),
            "start_deg_in_sign": round(float(cur_start_deg_in), 4),
            "end_deg_in_sign": round(float(end_deg_in), 4),
            "duration_min": int(dur_min),
        })

        if end_time >= next_sunrise_local:
            break

        # move to next sign
        cur_start = end_time
        cur_sign = _sign_index(_asc_sidereal_deg(cur_start, tz, lat, lon, ay_mode))
        cur_start_deg_in = _deg_in_sign(_asc_sidereal_deg(cur_start, tz, lat, lon, ay_mode))

    return {
        "sunrise_local": _fmt_local_iso(sunrise_local),
        "next_sunrise_local": _fmt_local_iso(next_sunrise_local),
        "items": items,
    }
