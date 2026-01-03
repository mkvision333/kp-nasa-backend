# main.py ✅ (FULL REPLACE) — Faster first tap: startup warm + 1-min bucket cache + home/nasa caching
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import hashlib
import time

# ✅ Editorial JSON (INLINE, no download)
import os
import json
from fastapi.responses import JSONResponse

from app.core.models import NASAReq, NASAResp
from app.core.jd import local_to_utc_iso
from app.core.nasa_ephemeris import (
    get_planets_ecliptic,
    ayanamsa_lahiri_approx_deg,
    mean_lunar_node_tropical_deg,
)

from app.core.rahu_ketu import calc_rahu_ketu
from app.core.kp_calc import kp_star_sub_sub

from app.core.houses_models import PlacidusReq, PlacidusResp
from app.core.houses_placidus import placidus_cusps, siderealize_cusps

from app.core.vimshottari_utils import moon_vimshottari_info
from app.core.vimshottari_tree import (
    build_mahadasha_list_120y_9items,
    build_level_list,
)

# ✅ Panchangam calc (LAZY endpoint only)
from app.core.panchangam_calc import compute_panchangam


# -------------------------------------------------
# App
# -------------------------------------------------
app = FastAPI(title="KP NASA Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------
# ✅ Startup warm-up (reduces first tap 60s)
# -------------------------------------------------
@app.on_event("startup")
def _startup_warm():
    try:
        utc_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        # warm skyfield / ephemeris kernel
        get_planets_ecliptic(utc_iso, 0.0, 0.0)
        # warm KP table calc
        kp_star_sub_sub(0.0)
        print("[STARTUP] warm ok", flush=True)
    except Exception as e:
        print(f"[STARTUP] warm fail: {e}", flush=True)

# -------------------------------------------------
# Health / Debug
# -------------------------------------------------
@app.get("/health")
def health():
    return {"ok": True, "service": "kp-nasa-backend"}

@app.get("/debug/routes")
def debug_routes():
    return [r.path for r in app.routes]

# -------------------------------------------------
# ✅ Editorial JSON content (Utilities) — INLINE JSON (no download)
# -------------------------------------------------
@app.get("/content/utilities.json")
def serve_utilities_json():
    file_path = os.path.join("content", "utilities.json")
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return JSONResponse(content=data)

# -------------------------------------------------
# Utilities
# -------------------------------------------------
def norm360(x: float) -> float:
    x = x % 360.0
    return x if x >= 0 else x + 360.0

def _abs_to_dms(abs_deg: float) -> Dict[str, int]:
    a = abs_deg % 360.0
    deg = int(a)
    mfloat = (a - deg) * 60.0
    minute = int(mfloat)
    sec = int(round((mfloat - minute) * 60.0))
    if sec >= 60:
        sec -= 60
        minute += 1
    if minute >= 60:
        minute -= 60
        deg += 1
    deg = deg % 360
    return {"deg": deg, "min": minute, "sec": sec}

def normalize_ayanamsa_name(v: Optional[str]) -> str:
    s = str(v or "KP").strip().upper()
    if s in ["LAHIRI", "L"]:
        return "LAHIRI"
    return "KP"

def pick_ayanamsa_deg(jd_ut: float, ayanamsa_name: str) -> float:
    lahiri = float(ayanamsa_lahiri_approx_deg(jd_ut))
    # KP = Lahiri - 0.1015 (your existing rule)
    if ayanamsa_name == "KP":
        return lahiri - 0.1015
    return lahiri

def _iso_to_dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)

# ✅ NEW: bucket datetimeLocal (NOW taps within 1 minute share same cache key)
def _bucket_datetimeLocal(dt_local: str, bucket_sec: int = 60) -> str:
    try:
        dt = datetime.fromisoformat(dt_local)
        ts = int(dt.timestamp())
        ts2 = ts - (ts % bucket_sec)
        dt2 = datetime.fromtimestamp(ts2)
        return dt2.isoformat()
    except Exception:
        return dt_local

def _make_key(datetimeLocal: str, tz: str, lat: float, lon: float, ayanamsa: str) -> str:
    dtb = _bucket_datetimeLocal(datetimeLocal, 60)  # ✅ 1-minute bucket
    raw = f"{dtb}|{tz}|{float(lat):.5f}|{float(lon):.5f}|{ayanamsa}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()

# -------------------------------------------------
# In-memory cache (simple, later Redis)
# -------------------------------------------------
_SESSION: Dict[str, Dict[str, Any]] = {}
_CACHE: Dict[str, Dict[str, Any]] = {}
TTL_SEC = 6 * 60 * 60  # 6 hours

def _gc():
    now = time.time()
    dead = [k for k, v in _SESSION.items() if now - float(v.get("_ts", now)) > TTL_SEC]
    for k in dead:
        _SESSION.pop(k, None)
    dead2 = [k for k, v in _CACHE.items() if now - float(v.get("_ts", now)) > TTL_SEC]
    for k in dead2:
        _CACHE.pop(k, None)

def _cache_get(key: str):
    _gc()
    v = _CACHE.get(key)
    return v.get("data") if v else None

def _cache_set(key: str, data: Any):
    _gc()
    _CACHE[key] = {"_ts": time.time(), "data": data}

# -------------------------------------------------
# NASA API (✅ cached)
# -------------------------------------------------
@app.post("/api/astro/nasa", response_model=NASAResp)
def nasa_positions(req: NASAReq):
    # ✅ safe ayanamsa key (NASAReq may not have ayanamsa field)
    ayan_name = normalize_ayanamsa_name(getattr(req, "ayanamsa", "KP"))
    key = _make_key(req.datetimeLocal, req.tz, req.lat, req.lng, ayan_name)

    cached = _cache_get(f"nasa:{key}")
    if cached:
        return cached

    utc_iso = local_to_utc_iso(req.datetimeLocal, req.tz)
    jd_ut, planets = get_planets_ecliptic(utc_iso, req.lat, req.lng)

    enriched = []
    moon_lon = None

    for p in planets:
        lon = float(p["lon"])
        star, sub, subsub = kp_star_sub_sub(lon)

        if p["name"] == "Moon":
            moon_lon = lon

        enriched.append({
            **p,
            "starLord": star,
            "subLord": sub,
            "subSubLord": subsub,
        })

    # NOTE: keep your existing logic
    if moon_lon is not None:
        rahu_lon, ketu_lon = calc_rahu_ketu(moon_lon)

        r_star, r_sub, r_ss = kp_star_sub_sub(rahu_lon)
        k_star, k_sub, k_ss = kp_star_sub_sub(ketu_lon)

        enriched.append({
            "name": "Rahu",
            "lon": rahu_lon,
            "lat": 0.0,
            "dist_au": 0.0,
            "speed_lon": -0.053,
            "starLord": r_star,
            "subLord": r_sub,
            "subSubLord": r_ss,
        })

        enriched.append({
            "name": "Ketu",
            "lon": ketu_lon,
            "lat": 0.0,
            "dist_au": 0.0,
            "speed_lon": -0.053,
            "starLord": k_star,
            "subLord": k_sub,
            "subSubLord": k_ss,
        })

    out = {"jd_ut": jd_ut, "utc_iso": utc_iso, "planets": enriched}
    _cache_set(f"nasa:{key}", out)
    return out

# -------------------------------------------------
# Placidus API
# -------------------------------------------------
@app.post("/api/astro/placidus", response_model=PlacidusResp)
def placidus_houses(req: PlacidusReq):
    cusps_trop = placidus_cusps(req.jd_ut, req.lat, req.lng)
    cusps_sid = siderealize_cusps(cusps_trop, req.ayanamsa_deg)
    return {"cusps_tropical": cusps_trop, "cusps_sidereal": cusps_sid}

# -------------------------------------------------
# ✅ LAZY Panchangam API (ON demand)
# -------------------------------------------------
class PanchangamReq(BaseModel):
    datetimeLocal: str
    tz: str
    lat: float
    lon: float
    ayanamsa: Optional[str] = "KP"

@app.post("/api/astro/panchangam")
def astro_panchangam(req: PanchangamReq):
    utc_iso = local_to_utc_iso(req.datetimeLocal, req.tz)
    jd_ut, _ = get_planets_ecliptic(utc_iso, req.lat, req.lon)

    ayan_name = normalize_ayanamsa_name(req.ayanamsa)
    ayan = pick_ayanamsa_deg(jd_ut, ayan_name)

    return compute_panchangam(
        datetimeLocal=req.datetimeLocal,
        tz=req.tz,
        lat=req.lat,
        lon=req.lon,
        ayan_deg=float(ayan),
    )

# -------------------------------------------------
# HOME API (✅ cached)
# -------------------------------------------------
class HomeReq(BaseModel):
    datetimeLocal: str
    tz: str
    lat: float
    lon: float
    ayanamsa: Optional[str] = "KP"
    outerPlanets: Optional[bool] = False
    nodeMode: Optional[bool] = True
    horaryOn: Optional[bool] = False
    horaryNumber: Optional[int] = 1
    includeDasha: Optional[bool] = False

@app.post("/api/astro/home")
def astro_home(req: HomeReq):
    ayan_name = normalize_ayanamsa_name(req.ayanamsa)
    key = _make_key(req.datetimeLocal, req.tz, req.lat, req.lon, ayan_name)

    cached = _cache_get(f"home:{key}")
    if cached:
        return cached

    utc_iso = local_to_utc_iso(req.datetimeLocal, req.tz)
    jd_ut, planets = get_planets_ecliptic(utc_iso, req.lat, req.lon)

    ayan = pick_ayanamsa_deg(jd_ut, ayan_name)

    kundali_planets: List[Dict[str, Any]] = []
    kp_graha_table: List[Dict[str, Any]] = []

    for p in planets:
        name = p["name"]
        lon_sid = norm360(float(p["lon"]) - ayan)
        dms = _abs_to_dms(lon_sid)

        kundali_planets.append({
            "planet": name,
            "longitude": dms,
            "retro": float(p.get("speed_lon", 0.0)) < 0,
        })

        # keep table but empty KP lords here (frontend/other endpoint can enrich)
        kp_graha_table.append({
            "planet": name,
            "longitude": dms,
            "retro": float(p.get("speed_lon", 0.0)) < 0,
            "starLord": "",
            "subLord": "",
            "subSubLord": "",
            "signifies": [],
            "star_signifies": [],
            "occupies": [],
        })

    rahu_trop = float(mean_lunar_node_tropical_deg(jd_ut))
    ketu_trop = norm360(rahu_trop + 180.0)

    rahu_sid = norm360(rahu_trop - ayan)
    ketu_sid = norm360(ketu_trop - ayan)

    for name, lon in [("Rahu", rahu_sid), ("Ketu", ketu_sid)]:
        dms = _abs_to_dms(lon)
        kundali_planets.append({"planet": name, "longitude": dms, "retro": True})
        kp_graha_table.append({
            "planet": name,
            "longitude": dms,
            "retro": True,
            "starLord": "",
            "subLord": "",
            "subSubLord": "",
            "signifies": [],
            "star_signifies": [],
            "occupies": [],
        })

    cusps_trop = placidus_cusps(jd_ut, req.lat, req.lon)

    cusps_sid: Dict[str, Any] = {}
    for k, v in cusps_trop.items():
        try:
            cusps_sid[k] = norm360(float(v) - float(ayan))
        except Exception:
            cusps_sid[k] = v

    bhava_cusps = []
    kp_bhava_table = []

    for i in range(1, 13):
        house_key = f"house{i}"
        lon_sid = float(cusps_sid[house_key])
        dms = _abs_to_dms(lon_sid)

        bhava_cusps.append({"bhava": i, "longitude": dms})
        kp_bhava_table.append({
            "bhava": i,
            "longitude": dms,
            "starLord": "",
            "subLord": "",
            "subSubLord": "",
        })

    resp = {
        "meta": {
            "source": "kp-nasa-backend",
            "utc_iso": utc_iso,
            "jd_ut": jd_ut,
            "tz": req.tz,
            "lat": req.lat,
            "lon": req.lon,
            "ayanamsa": ayan_name,
            "ayanamsaValueDeg": float(ayan),
        },
        "ayanamsa": {"value": float(ayan), "name": ayan_name},
        "ayanamsaValueDeg": float(ayan),
        "panchangam": None,
        "kundali": {"planets": kundali_planets, "bhavaCusps": bhava_cusps},
        "kp": {"ayanamsa": float(ayan), "grahaTable": kp_graha_table, "bhavaTable": kp_bhava_table},
        "dasha": None,
        "vimshottari": None,
        "rulingPlanets": None,
    }

    _cache_set(f"home:{key}", resp)
    return resp

# -------------------------------------------------
# LAZY DASHA APIs
# -------------------------------------------------
class DashaBaseReq(BaseModel):
    datetimeLocal: str
    tz: str
    lat: float
    lon: float
    ayanamsa: Optional[str] = "KP"

class DashaLevelReq(BaseModel):
    key: str
    start: str
    end: str
    mahaLord: Optional[str] = None
    bhuktiLord: Optional[str] = None
    antaraLord: Optional[str] = None
    sukshmaLord: Optional[str] = None

def _ensure_session(req: DashaBaseReq) -> Dict[str, Any]:
    utc_iso = local_to_utc_iso(req.datetimeLocal, req.tz)
    jd_ut, planets = get_planets_ecliptic(utc_iso, req.lat, req.lon)

    ayan_name = normalize_ayanamsa_name(req.ayanamsa)
    ayan = pick_ayanamsa_deg(jd_ut, ayan_name)

    moon_trop = None
    for p in planets:
        if str(p.get("name", "")).lower() == "moon":
            moon_trop = float(p.get("lon", 0.0)) % 360.0
            break
    if moon_trop is None:
        raise ValueError("Moon not found in NASA planets list")

    moon_sid = norm360(moon_trop - float(ayan))
    maha_lord, balance_years = moon_vimshottari_info(moon_sid)
    balance_years = max(0.0, float(balance_years))

    start_utc = datetime.fromisoformat(utc_iso.replace("Z", "+00:00")).astimezone(timezone.utc)

    key = _make_key(req.datetimeLocal, req.tz, req.lat, req.lon, ayan_name)

    ses = {
        "_ts": time.time(),
        "key": key,
        "utc_iso": utc_iso,
        "jd_ut": jd_ut,
        "ayanamsa": ayan_name,
        "ayan_deg": float(ayan),
        "moon_sid": float(moon_sid),
        "maha_lord": str(maha_lord),
        "balance_years": float(balance_years),
        "start_utc": start_utc,
    }
    _SESSION[key] = ses
    return ses

@app.post("/api/dasha/maha")
def dasha_maha(req: DashaBaseReq):
    ayan_name = normalize_ayanamsa_name(req.ayanamsa)
    key = _make_key(req.datetimeLocal, req.tz, req.lat, req.lon, ayan_name)
    cached = _cache_get(f"maha:{key}")
    if cached:
        return cached

    ses = _SESSION.get(key)
    if not ses:
        ses = _ensure_session(req)

    maha_list = build_mahadasha_list_120y_9items(
        start_utc=ses["start_utc"],
        maha_lord=ses["maha_lord"],
        maha_balance_years=ses["balance_years"],
    )

    out = {
        "meta": {
            "key": key,
            "utc_iso": ses["utc_iso"],
            "jd_ut": ses["jd_ut"],
            "ayanamsa": ses["ayanamsa"],
            "ayanamsaValueDeg": ses["ayan_deg"],
        },
        "maha": maha_list,
    }

    _cache_set(f"maha:{key}", out)
    return out

@app.post("/api/dasha/bhukti")
def dasha_bhukti(req: DashaLevelReq):
    cached = _cache_get(f"bh:{req.key}:{req.mahaLord}:{req.start}:{req.end}")
    if cached:
        return cached

    start = _iso_to_dt(req.start)
    end = _iso_to_dt(req.end)
    maha = str(req.mahaLord or "").strip()
    if not maha:
        raise ValueError("mahaLord required")

    bh = build_level_list("bhukti", start, end, maha)
    out = {"bhukti": bh}
    _cache_set(f"bh:{req.key}:{maha}:{req.start}:{req.end}", out)
    return out

@app.post("/api/dasha/antara")
def dasha_antara(req: DashaLevelReq):
    cached = _cache_get(f"an:{req.key}:{req.bhuktiLord}:{req.start}:{req.end}")
    if cached:
        return cached

    start = _iso_to_dt(req.start)
    end = _iso_to_dt(req.end)
    bh = str(req.bhuktiLord or "").strip()
    if not bh:
        raise ValueError("bhuktiLord required")

    an = build_level_list("antara", start, end, bh)
    out = {"antara": an}
    _cache_set(f"an:{req.key}:{bh}:{req.start}:{req.end}", out)
    return out

@app.post("/api/dasha/sukshma")
def dasha_sukshma(req: DashaLevelReq):
    cached = _cache_get(f"su:{req.key}:{req.antaraLord}:{req.start}:{req.end}")
    if cached:
        return cached

    start = _iso_to_dt(req.start)
    end = _iso_to_dt(req.end)
    an = str(req.antaraLord or "").strip()
    if not an:
        raise ValueError("antaraLord required")

    su = build_level_list("sukshma", start, end, an)
    out = {"sukshma": su}
    _cache_set(f"su:{req.key}:{an}:{req.start}:{req.end}", out)
    return out

@app.post("/api/dasha/prana")
def dasha_prana(req: DashaLevelReq):
    cached = _cache_get(f"pr:{req.key}:{req.sukshmaLord}:{req.start}:{req.end}")
    if cached:
        return cached

    start = _iso_to_dt(req.start)
    end = _iso_to_dt(req.end)
    su = str(req.sukshmaLord or "").strip()
    if not su:
        raise ValueError("sukshmaLord required")

    pr = build_level_list("prana", start, end, su)
    out = {"prana": pr}
    _cache_set(f"pr:{req.key}:{su}:{req.start}:{req.end}", out)
    return out
