# app/core/lagna_kalam_calc.py ✅ FULL REPLACE (fast + sign-change bracket)
from __future__ import annotations

from datetime import datetime, timedelta, timezone, date
from zoneinfo import ZoneInfo
from typing import Dict, Any, List, Tuple
import math

from app.core.ayanamsa_exact import get_ayanamsa_deg
from app.core.houses_placidus import placidus_cusps
from app.core.panchangam_calc import _sunrise_sunset_utc_for_local_date

SIGNS_EN = [
    "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
    "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"
]

# -----------------------------
# Helpers
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
    if a in ("KPO", "KPOLD"):
        return "KP_OLD"
    if a in ("KPN", "KPNEW", "VP291", "SENTHILATHIBAN"):
        return "KP_NEW"
    if a in ("LAHIRI", "CHITRAPAKSHA"):
        return "LAHIRI"
    return "KP_OLD"

def _local_to_utc(dt_local_naive: datetime, tz: str) -> datetime:
    zone = ZoneInfo(tz)
    aware_local = dt_local_naive.replace(tzinfo=zone)
    return aware_local.astimezone(timezone.utc)

def _utc_to_jd_ut(dt_utc: datetime) -> float:
    """
    Fast Julian Day (UT) from UTC datetime (no NASA call).
    """
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
    dt_utc = dt_utc.astimezone(timezone.utc)

    y = dt_utc.year
    m = dt_utc.month
    D = dt_utc.day

    frac_day = (
        dt_utc.hour +
        (dt_utc.minute + (dt_utc.second + dt_utc.microsecond / 1e6) / 60.0) / 60.0
    ) / 24.0

    d = D + frac_day

    if m <= 2:
        y -= 1
        m += 12

    A = y // 100
    B = 2 - A + (A // 4)
    jd = int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + B - 1524.5
    return float(jd)

def _asc_sidereal_deg(dt_local_naive: datetime, tz: str, lat: float, lon: float, ay_mode: str) -> float:
    """
    ASC sidereal deg = ASC tropical (placidus) - ayanamsa
    """
    dt_utc = _local_to_utc(dt_local_naive, tz)
    jd_ut = _utc_to_jd_ut(dt_utc)

    cusps = placidus_cusps(float(jd_ut), float(lat), float(lon))  # tropical
    asc_trop = float(cusps["asc"])

    ay_deg = float(get_ayanamsa_deg(float(jd_ut), ay_mode))
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

def _binary_search_sign_change(
    cur_sign: int,
    left: datetime,
    right: datetime,
    tz: str,
    lat: float,
    lon: float,
    ay_mode: str,
    iters: int = 22,  # ~sub-second
) -> datetime:
    """
    Find earliest time in (left,right] where sign != cur_sign.
    Assumes sign(left)==cur_sign and sign(right)!=cur_sign.
    """
    lo = left
    hi = right
    for _ in range(iters):
        if (hi - lo).total_seconds() <= 1:
            break
        mid = lo + (hi - lo) / 2
        s = _sign_index(_asc_sidereal_deg(mid, tz, lat, lon, ay_mode))
        if s == cur_sign:
            lo = mid
        else:
            hi = mid
    return hi

# -----------------------------
# Main API
# -----------------------------
def compute_lagna_kalam(dateKey: str, tz: str, lat: float, lon: float, ayanamsa: str) -> Dict[str, Any]:
    """
    Lagna Kalam: sunrise -> next sunrise
    Correct: uses ASC sidereal sign changes. Fast: no NASA calls inside loop.
    """
    ay_mode = _ayan_mode_normalize(ayanamsa)
    sunrise_local, next_sunrise_local = _sunrise_nextsunrise_local(dateKey, tz, lat, lon)

    # start
    cur_start = sunrise_local
    asc0 = _asc_sidereal_deg(cur_start, tz, lat, lon, ay_mode)
    cur_sign = _sign_index(asc0)
    cur_start_deg_in = _deg_in_sign(asc0)

    items: List[Dict[str, Any]] = []

    # coarse scan step (tune for speed/accuracy)
    STEP_MIN = 10

    # safety: avoid infinite loops
    max_segments = 14  # sometimes can repeat if edge cases; keep safe

    for idx in range(1, max_segments + 1):
        if cur_start >= next_sunrise_local:
            break

        # find next sign change by scanning forward
        prev_t = cur_start
        t = min(cur_start + timedelta(minutes=STEP_MIN), next_sunrise_local)

        # If already at end
        if t <= cur_start:
            t = next_sunrise_local

        while t <= next_sunrise_local:
            s = _sign_index(_asc_sidereal_deg(t, tz, lat, lon, ay_mode))
            if s != cur_sign:
                # bracket found: prev_t (same sign) -> t (new sign)
                break
            prev_t = t
            t = min(t + timedelta(minutes=STEP_MIN), next_sunrise_local)

            if prev_t >= next_sunrise_local:
                break

        if t >= next_sunrise_local:
            end_time = next_sunrise_local
        else:
            # ensure bracket correctness
            s_left = _sign_index(_asc_sidereal_deg(prev_t, tz, lat, lon, ay_mode))
            s_right = _sign_index(_asc_sidereal_deg(t, tz, lat, lon, ay_mode))
            if s_left != cur_sign or s_right == cur_sign:
                # fallback: if bracket weird, just end at next_sunrise to avoid 0m spam
                end_time = next_sunrise_local
            else:
                end_time = _binary_search_sign_change(cur_sign, prev_t, t, tz, lat, lon, ay_mode)

        # prevent zero-duration rows
        if end_time <= cur_start:
            end_time = min(cur_start + timedelta(minutes=1), next_sunrise_local)

        # end degrees (compute at end_time, but to represent "end within sign", use near-end time if possible)
        probe = end_time - timedelta(seconds=1)
        if probe < cur_start:
            probe = cur_start
        asc_end = _asc_sidereal_deg(probe, tz, lat, lon, ay_mode)
        end_deg_in = _deg_in_sign(asc_end)

        dur_min = int(round((end_time - cur_start).total_seconds() / 60.0))

        items.append({
            "idx": idx,
            "sign": SIGNS_EN[cur_sign],
            "start_local": _fmt_local_iso(cur_start),
            "end_local": _fmt_local_iso(end_time),
            "start_deg_in_sign": round(float(cur_start_deg_in), 4),
            "end_deg_in_sign": round(float(end_deg_in), 4),
            "duration_min": int(dur_min),
        })

        if end_time >= next_sunrise_local:
            break

        # move to next segment
        cur_start = end_time
        asc_next = _asc_sidereal_deg(cur_start, tz, lat, lon, ay_mode)
        cur_sign = _sign_index(asc_next)
        cur_start_deg_in = _deg_in_sign(asc_next)

    return {
        "sunrise_local": _fmt_local_iso(sunrise_local),
        "next_sunrise_local": _fmt_local_iso(next_sunrise_local),
        "items": items,
    }
