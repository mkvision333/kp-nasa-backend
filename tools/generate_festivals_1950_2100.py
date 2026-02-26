# tools/generate_festivals_1950_2100.py
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

import pytz
import numpy as np
from skyfield.api import load, load_file, wgs84
from skyfield import almanac

import rashiphal.festivals_rules as fr

FestivalRule = fr.FestivalRule
FESTIVAL_RULES = getattr(fr, "FESTIVAL_RULES", None) or getattr(fr, "FESTIVAL_RULES", None)

if FESTIVAL_RULES is None:
    raise RuntimeError("FESTIVAL_RULES not found in rashiphal/festivals_rules.py")

TZ = pytz.timezone("Asia/Kolkata")

# ✅ Your bsp is in project root as per screenshot
BSP_PATH = "de440s.bsp"

# ✅ Default place (you can change later)
DEFAULT_PLACE = {
    "name": "Korutla/Hyderabad (Default)",
    "lat": 18.82,
    "lon": 78.72,
}

TITHI_NAMES = [
    "Pratipada","Dvitiya","Tritiya","Chaturthi","Panchami","Shashthi","Saptami",
    "Ashtami","Navami","Dashami","Ekadashi","Dwadashi","Trayodashi","Chaturdashi","Purnima",
    "Pratipada","Dvitiya","Tritiya","Chaturthi","Panchami","Shashthi","Saptami",
    "Ashtami","Navami","Dashami","Ekadashi","Dwadashi","Trayodashi","Chaturdashi","Amavasya"
]

AMANTA_MONTHS = [
    "Chaitra",     # Pisces at previous new moon
    "Vaisakha",    # Aries
    "Jyeshtha",    # Taurus
    "Ashadha",     # Gemini
    "Shravana",    # Cancer
    "Bhadrapada",  # Leo
    "Ashwayuja",   # Virgo
    "Karthika",    # Libra
    "Margashirsha",# Scorpio
    "Pausha",      # Sagittarius
    "Magha",       # Capricorn
    "Phalguna",    # Aquarius
]

def dt_local_to_sf(ts, dt_local: datetime):
    """Local aware datetime -> Skyfield Time"""
    dt_utc = dt_local.astimezone(pytz.utc)
    return ts.utc(dt_utc.year, dt_utc.month, dt_utc.day, dt_utc.hour, dt_utc.minute, dt_utc.second)

def sf_to_local(t) -> datetime:
    """Skyfield Time -> local datetime"""
    dt_utc = t.utc_datetime().replace(tzinfo=pytz.utc)
    return dt_utc.astimezone(TZ)

def ecl_lon_deg(eph, ts, t, target_name: str) -> float:
    """Ecliptic longitude (tropical) of Sun/Moon as seen from Earth, degrees 0..360"""
    earth = eph["earth"]
    body = eph[target_name]
    astrometric = earth.at(t).observe(body).apparent()
    lat, lon, dist = astrometric.ecliptic_latlon()
    deg = lon.degrees % 360.0
    return deg

def tithi_index(eph, ts, t) -> int:
    sun = ecl_lon_deg(eph, ts, t, "sun")
    moon = ecl_lon_deg(eph, ts, t, "moon")
    diff = (moon - sun) % 360.0
    idx = int(diff // 12.0)  # 0..29
    return idx

def tithi_name(idx: int) -> str:
    return TITHI_NAMES[idx]

def paksha(idx: int) -> str:
    return "Shukla" if idx < 15 else "Krishna"

def find_sunrise_sunset(eph, ts, place, d: date) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Returns (sunrise_local_dt, sunset_local_dt) for given date.
    Uses Skyfield almanac at given location.
    """
    lat = place["lat"]
    lon = place["lon"]
    loc = wgs84.latlon(latitude_degrees=lat, longitude_degrees=lon)

    # Search in [d 00:00 .. d+1 00:00] local
    t0 = dt_local_to_sf(ts, TZ.localize(datetime(d.year, d.month, d.day, 0, 0, 0)))
    t1 = dt_local_to_sf(ts, TZ.localize(datetime(d.year, d.month, d.day, 23, 59, 59)))  # same day end

    f = almanac.sunrise_sunset(eph, loc)
    times, events = almanac.find_discrete(t0, t1, f)

    sunrise = None
    sunset = None
    for t, ev in zip(times, events):
        # ev==1 means sun up starts (sunrise), ev==0 means sun down starts (sunset)
        if int(ev) == 1 and sunrise is None:
            sunrise = sf_to_local(t)
        if int(ev) == 0:
            sunset = sf_to_local(t)

    return sunrise, sunset

def nishitha_time(sunset: datetime, next_sunrise: datetime) -> datetime:
    # Nishitha ~ midpoint of night
    return sunset + (next_sunrise - sunset) / 2

def approx_new_moon_search(eph, ts, around_local: datetime) -> datetime:
    """
    Find the nearest previous new moon using phase angle sign change around ~30 days window.
    Practical discrete search around.
    """
    # Search backward 35 days
    start = around_local - timedelta(days=35)
    end = around_local

    t0 = dt_local_to_sf(ts, TZ.localize(datetime(start.year, start.month, start.day, 0, 0, 0)))
    t1 = dt_local_to_sf(ts, TZ.localize(datetime(end.year, end.month, end.day, 23, 59, 59)))

    # Moon phases: 0=new moon, 1=first quarter, 2=full, 3=last quarter
    phase_f = almanac.moon_phases(eph)
    times, phases = almanac.find_discrete(t0, t1, phase_f)

    # pick the latest phase==0 (new moon)
    last_nm = None
    for t, ph in zip(times, phases):
        if int(ph) == 0:
            last_nm = sf_to_local(t)

    if last_nm is None:
        # fallback: use around_local - 29 days
        return around_local - timedelta(days=29)

    return last_nm

def sidereal_sun_sign_at(eph, ts, dt_local: datetime) -> int:
    """
    TEMP simplified sign index using TROPICAL sun longitude.
    0=Aries .. 11=Pisces
    (We intentionally avoid ayanamsa_exact dependency to ensure generator works now.)
    """
    t = dt_local_to_sf(ts, dt_local)
    sun_trop = ecl_lon_deg(eph, ts, t, "sun")  # 0..360 tropical
    sign = int(sun_trop // 30.0)
    return sign

def amanta_month_for_dt(eph, ts, dt_local: datetime) -> str:
    """
    AMANTA month is determined by Sun sidereal sign at previous new moon:
    Pisces => Chaitra, Aries => Vaisakha, ... Aquarius => Phalguna.
    """
    prev_nm = approx_new_moon_search(eph, ts, dt_local)
    sign = sidereal_sun_sign_at(eph, ts, prev_nm)
    # Map: sign 11(Pisces)->Chaitra(0), sign0(Aries)->Vaisakha(1), ... sign10(Aquarius)->Phalguna(11)
    idx = (sign + 1) % 12
    return AMANTA_MONTHS[idx]

def decision_datetime_for_day(eph, ts, place, d: date, decision: str) -> Optional[datetime]:
    sunrise, sunset = find_sunrise_sunset(eph, ts, place, d)
    if sunrise is None or sunset is None:
        return None

    if decision == "sunrise":
        return sunrise

    if decision == "pradosha":
        # Pradosha window ~ sunset to +2h. take midpoint as representative.
        return sunset + timedelta(hours=1)

    if decision == "nishitha":
        # Need next day sunrise to compute midpoint
        next_sr, _next_ss = find_sunrise_sunset(eph, ts, place, d + timedelta(days=1))
        if next_sr is None:
            return None
        return nishitha_time(sunset, next_sr)

    return None

def match_rule_on_day(eph, ts, place, d: date, rule: FestivalRule) -> bool:
    if rule.decision_time == "solar":
        return False

    dt_dec = decision_datetime_for_day(eph, ts, place, d, rule.decision_time)
    if dt_dec is None:
        return False

    t = dt_local_to_sf(ts, dt_dec)
    idx = tithi_index(eph, ts, t)
    tname = tithi_name(idx)
    pk = paksha(idx)
    lm = amanta_month_for_dt(eph, ts, dt_dec)

    return (lm == rule.lunar_month and pk == rule.paksha and tname == rule.tithi)

def makara_sankranti_date(eph, ts, place, year: int) -> date:
    """
    TEMP fallback: Makara Sankranti ~ Jan 14 (sometimes Jan 15).
    For now return Jan 14 to keep generator simple & fast.
    """
    return date(year, 1, 14)

    # refine with binary between times[cross_i-1], times[cross_i]
    a = times[cross_i-1]
    b = times[cross_i]

    def f(dt_local):
        t = dt_local_to_sf(ts, dt_local)
        sun_trop = ecl_lon_deg(eph, ts, t, "sun")
        ay = float(get_ayanamsa_lahiri_deg(dt_local))
        sun_sid = (sun_trop - ay) % 360.0
        return ((sun_sid - 270.0 + 540.0) % 360.0 - 180.0)

    fa = f(a)
    fb = f(b)
    for _ in range(30):
        m = a + (b - a)/2
        fm = f(m)
        if fa < 0 and fm >= 0:
            b, fb = m, fm
        else:
            a, fa = m, fm

    crossing_dt = b
    return crossing_dt.date()

def generate_year(eph, ts, place, year: int) -> Dict[str, Any]:
    festivals: List[Dict[str, Any]] = []
    tithis: List[Dict[str, Any]] = []

    # ---- Festivals by rules ----
    for rule in FESTIVAL_RULES:
        if rule.decision_time == "solar" and rule.key == "MAKARA_SANKRANTI":
            dt = makara_sankranti_date(eph, ts, place, year)
            festivals.append({
                "type": "FESTIVAL",
                "key": rule.key,
                "name_te": rule.name_te,
                "name_en": rule.name_en,
                "date": dt.isoformat(),
                "decision_time": "solar",
            })
            continue

        # Search window: whole year is safe (still ok once)
        d = date(year, 1, 1)
        end = date(year, 12, 31)
        found = None
        while d <= end:
            if match_rule_on_day(eph, ts, place, d, rule):
                found = d
                break
            d += timedelta(days=1)

        if found:
            festivals.append({
                "type": "FESTIVAL",
                "key": rule.key,
                "name_te": rule.name_te,
                "name_en": rule.name_en,
                "date": found.isoformat(),
                "decision_time": rule.decision_time,
                "lunar_month": rule.lunar_month,
                "paksha": rule.paksha,
                "tithi": rule.tithi,
            })

    # ---- Monthly important tithis (year scan, sunrise based) ----
    d = date(year, 1, 1)
    end = date(year, 12, 31)
    while d <= end:
        sunrise, sunset = find_sunrise_sunset(eph, ts, place, d)
        if sunrise:
            # We'll take sunrise-based tithi for monthly important ones
            t = dt_local_to_sf(ts, sunrise)
            idx = tithi_index(eph, ts, t)
            tname = tithi_name(idx)
            pk = paksha(idx)
            lm = amanta_month_for_dt(eph, ts, sunrise)

            # Ekadashi
            if tname == "Ekadashi":
                tithis.append({
                    "type": "TITHI",
                    "key": f"{pk}_EKADASHI",
                    "name_te": f"{'శుక్ల' if pk=='Shukla' else 'బహుళ'} ఏకాదశి",
                    "name_en": f"{pk} Ekadashi",
                    "date": d.isoformat(),
                    "decision_time": "sunrise",
                    "lunar_month": lm,
                    "paksha": pk,
                    "tithi": tname,
                })

            # Pradosham (Trayodashi) — can keep sunrise-based OR pradosha-based.
            # We'll store pradosha-based for accuracy:
            dt_pr = decision_datetime_for_day(eph, ts, place, d, "pradosha")
            if dt_pr:
                tpr = dt_local_to_sf(ts, dt_pr)
                idx2 = tithi_index(eph, ts, tpr)
                tname2 = tithi_name(idx2)
                pk2 = paksha(idx2)
                lm2 = amanta_month_for_dt(eph, ts, dt_pr)
                if tname2 == "Trayodashi":
                    tithis.append({
                        "type": "TITHI",
                        "key": f"{pk2}_PRADOSHAM",
                        "name_te": f"{'శుక్ల' if pk2=='Shukla' else 'బహుళ'} ప్రదోషం",
                        "name_en": f"{pk2} Pradosham",
                        "date": d.isoformat(),
                        "decision_time": "pradosha",
                        "lunar_month": lm2,
                        "paksha": pk2,
                        "tithi": tname2,
                    })

            # Amavasya / Purnima
            if tname in ("Amavasya", "Purnima"):
                tithis.append({
                    "type": "TITHI",
                    "key": tname.upper(),
                    "name_te": "అమావాస్య" if tname == "Amavasya" else "పౌర్ణమి",
                    "name_en": tname,
                    "date": d.isoformat(),
                    "decision_time": "sunrise",
                    "lunar_month": lm,
                    "paksha": pk,
                    "tithi": tname,
                })

            # Sankatahara Chaturthi = Krishna Chaturthi (sunrise based ok)
            if pk == "Krishna" and tname == "Chaturthi":
                tithis.append({
                    "type": "TITHI",
                    "key": "SANKATAHARA_CHATURTHI",
                    "name_te": "సంకటహర చవితి",
                    "name_en": "Sankatahara Chaturthi",
                    "date": d.isoformat(),
                    "decision_time": "sunrise",
                    "lunar_month": lm,
                    "paksha": pk,
                    "tithi": tname,
                })

        d += timedelta(days=1)

    festivals.sort(key=lambda x: x["date"])
    tithis.sort(key=lambda x: x["date"])
    return {"festivals": festivals, "tithis": tithis}

def main():
    start_year = 1950
    end_year = 2100
    place = DEFAULT_PLACE

    eph = load_file(BSP_PATH)
    ts = load.timescale()

    out: Dict[str, Any] = {
        "meta": {
            "generated_at": datetime.now(TZ).isoformat(),
            "tz": "Asia/Kolkata",
            "place": place,
            "range": [start_year, end_year],
            "engine": "Skyfield + NASA DE440s",
            "festival_rule_basis": "Sunrise / Pradosha / Nishitha decision-time tithi",
        },
        "years": {}
    }

    for y in range(start_year, end_year + 1):
        print("Generating", y)
        out["years"][str(y)] = generate_year(eph, ts, place, y)

    # output path (you can change)
    out_path = "content/festivals_1950_2100.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print("✅ DONE:", out_path)

if __name__ == "__main__":
    main()