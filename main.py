# main.py ✅ FULL REPLACE (Render-safe, no build_level_list import)
# - Removes obsolete build_level_list import (caused ImportError)
# - Exports: /api/astro/home + /api/dasha/* correct
# - HOME includeDasha uses build_vimshottari_tree(max_levels=4) (no legacy)
# - Lazy dasha endpoints use build_level_list_clipped + get_child_full_window

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
import hashlib
import time
import os
import json

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# (optional) rashiphal module (only if you created it)
try:
    from app.core.rashiphal import build_daily_rashiphal, to_json
except Exception:
    build_daily_rashiphal = None
    to_json = None

# ✅ TimezoneFinder (SAFE import)
try:
    from timezonefinder import TimezoneFinder
    _TZF = TimezoneFinder()
    _TZF_OK = True
    _TZF_ERR = ""
except Exception as _e:
    _TZF = None
    _TZF_OK = False
    _TZF_ERR = str(_e)

from app.core.models import NASAReq, NASAResp
from app.core.jd import local_to_utc_iso
from app.core.nasa_ephemeris import get_planets_ecliptic, mean_lunar_node_tropical_deg
from app.core.ayanamsa_exact import get_ayanamsa_deg
from app.core.rahu_ketu import calc_rahu_ketu
from app.core.kp_calc import kp_star_sub_sub  # legacy (kept for bhava cusps)
from app.core.houses_models import PlacidusReq, PlacidusResp
from app.core.houses_placidus import placidus_cusps, siderealize_cusps
from app.core.vimshottari_utils import moon_vimshottari_info

# ✅ IMPORTANT: NO build_level_list import!
from app.core.vimshottari_tree import (
    build_mahadasha_list_120y_9items,
    build_vimshottari_tree,
    build_level_list_clipped,
    get_child_full_window,
    DASHA_YEARS,
)

from app.core.panchangam_calc import compute_panchangam


# -------------------------------------------------
# App
# -------------------------------------------------
app = FastAPI(title="KP NASA Backend", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


# -------------------------------------------------
# Helpers
# -------------------------------------------------
def _add_days(dt: datetime, days: float) -> datetime:
    return dt + timedelta(days=float(days))

def norm360(x: float) -> float:
    x = float(x) % 360.0
    return x if x >= 0 else x + 360.0

def _abs_to_dms(abs_deg: float) -> Dict[str, int]:
    a = norm360(float(abs_deg))
    total_sec = int(round(a * 3600.0)) % int(360 * 3600)
    deg = total_sec // 3600
    rem = total_sec % 3600
    minute = rem // 60
    sec = rem % 60
    return {"deg": int(deg), "min": int(minute), "sec": int(sec)}

def _iso_to_dt(s: str) -> datetime:
    return datetime.fromisoformat(str(s).replace("Z", "+00:00")).astimezone(timezone.utc)

def _parse_iso_utc(s: str) -> datetime:
    return _iso_to_dt(s)

def _years_between_iso(start_iso: str, end_iso: str) -> float:
    s = _parse_iso_utc(start_iso)
    e = _parse_iso_utc(end_iso)
    days = (e - s).total_seconds() / 86400.0
    return float(days) / 365.2425

def _bucket_datetimeLocal(dt_local: str, bucket_sec: int = 60) -> str:
    try:
        dt = datetime.fromisoformat(dt_local)
        ts = int(dt.timestamp())
        ts2 = ts - (ts % bucket_sec)
        return datetime.fromtimestamp(ts2).isoformat()
    except Exception:
        return dt_local

def normalize_ayanamsa_name(v: Optional[str]) -> str:
    s = str(v or "KP").strip().upper()
    if s in ["LAHIRI", "L"]:
        return "LAHIRI"
    return "KP"

def pick_ayanamsa_deg(jd_ut: float, ayanamsa_name: str) -> float:
    if ayanamsa_name == "LAHIRI":
        return float(get_ayanamsa_deg(jd_ut, "LAHIRI"))
    return float(get_ayanamsa_deg(jd_ut, "KP"))

def _make_key(datetimeLocal: str, tz: str, lat: float, lon: float, ayanamsa: str) -> str:
    dtb = _bucket_datetimeLocal(datetimeLocal, 60)
    raw = f"{dtb}|{tz}|{float(lat):.5f}|{float(lon):.5f}|{ayanamsa}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


# -----------------------------
# Sign helpers
# -----------------------------
SIGN_NAMES = ["", "Mesha","Vrishabha","Mithuna","Karkataka","Simha","Kanya","Tula","Vrischika","Dhanu","Makara","Kumbha","Meena"]
SIGN_LORD_BY_SIGN: Dict[int, str] = {1:"Mars",2:"Venus",3:"Mercury",4:"Moon",5:"Sun",6:"Mercury",7:"Venus",8:"Mars",9:"Jupiter",10:"Saturn",11:"Saturn",12:"Jupiter"}

def sign_from_lon_deg(lon: float) -> int:
    d = norm360(float(lon))
    return int(d // 30) + 1

def house_from_lon_and_cusps(lon: float, cusps_sid_by_house: Dict[int, float]) -> int:
    lon = norm360(float(lon))
    cusp = {int(k): norm360(float(v)) for k, v in cusps_sid_by_house.items()}
    for h in range(1, 12):
        a, b = cusp[h], cusp[h + 1]
        if a <= b:
            if a <= lon < b: return h
        else:
            if lon >= a or lon < b: return h
    a, b = cusp[12], cusp[1]
    if a <= b:
        if a <= lon < b: return 12
    else:
        if lon >= a or lon < b: return 12
    return 12


# -----------------------------
# Nakshatra helpers
# -----------------------------
NAK_NAMES = ["Ashwini","Bharani","Krittika","Rohini","Mrigashirsha","Ardra","Punarvasu","Pushya","Ashlesha","Magha","Purva Phalguni","Uttara Phalguni","Hasta","Chitra","Swati","Vishakha","Anuradha","Jyeshtha","Mula","Purva Ashadha","Uttara Ashadha","Shravana","Dhanishta","Shatabhisha","Purva Bhadrapada","Uttara Bhadrapada","Revati"]
NAK_LORDS = ["Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury","Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury","Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury"]
NAK_SPAN = 360.0 / 27.0

VIM_ORDER = ["Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury"]
VIM_YEARS = {"Ketu":7,"Venus":20,"Sun":6,"Moon":10,"Mars":7,"Rahu":18,"Jupiter":16,"Saturn":19,"Mercury":17}

def _cycle_from(lord: str) -> List[str]:
    lord = str(lord or "").strip()
    if lord not in VIM_ORDER:
        return VIM_ORDER[:]
    i = VIM_ORDER.index(lord)
    return VIM_ORDER[i:] + VIM_ORDER[:i]

def kp_star_sub_sub_v2(lon_sid: float):
    x = norm360(float(lon_sid))
    nak_index = int(x // NAK_SPAN)
    nak_index = max(0, min(26, nak_index))
    nak_name = NAK_NAMES[nak_index]
    star_lord = NAK_LORDS[nak_index]

    nak_start = nak_index * NAK_SPAN
    offset = x - nak_start

    seq1 = _cycle_from(star_lord)
    rem = offset
    sub_lord = seq1[0]
    sub_span = NAK_SPAN
    for L in seq1:
        seg = NAK_SPAN * (VIM_YEARS[L] / 120.0)
        if rem < seg:
            sub_lord = L
            sub_span = seg
            break
        rem -= seg

    seq2 = _cycle_from(sub_lord)
    rem2 = rem
    subsub_lord = seq2[0]
    for L in seq2:
        seg2 = sub_span * (VIM_YEARS[L] / 120.0)
        if rem2 < seg2:
            subsub_lord = L
            break
        rem2 -= seg2

    return star_lord, sub_lord, subsub_lord, nak_index, nak_name

def _build_moon_meta(planets_tropical: List[Dict[str, Any]], ayan_deg: float) -> Optional[Dict[str, Any]]:
    try:
        moon_trop = None
        for p in planets_tropical or []:
            if str(p.get("name", "")).strip().lower() == "moon":
                moon_trop = float(p.get("lon", 0.0)) % 360.0
                break
        if moon_trop is None:
            return None
        moon_sid = norm360(float(moon_trop) - float(ayan_deg))
        rashi_idx0 = max(0, min(11, int(moon_sid // 30.0)))
        return {
            "moonLonTropicalDeg": float(moon_trop),
            "moonLonSiderealDeg": float(moon_sid),
            "moonRashiIndex": int(rashi_idx0),
            "moonRashiName": str(SIGN_NAMES[rashi_idx0 + 1]),
            "nakIndex": int(moon_sid // NAK_SPAN),
            "nakName": str(NAK_NAMES[int(moon_sid // NAK_SPAN)]),
            "nakLord": str(NAK_LORDS[int(moon_sid // NAK_SPAN)]),
        }
    except Exception:
        return None


# -------------------------------------------------
# In-memory cache
# -------------------------------------------------
_SESSION: Dict[str, Dict[str, Any]] = {}
_CACHE: Dict[str, Dict[str, Any]] = {}
TTL_SEC = 6 * 60 * 60

def _gc():
    now = time.time()
    dead = [k for k, v in _SESSION.items() if now - float(v.get("_ts", now)) > TTL_SEC]
    for k in dead: _SESSION.pop(k, None)
    dead2 = [k for k, v in _CACHE.items() if now - float(v.get("_ts", now)) > TTL_SEC]
    for k in dead2: _CACHE.pop(k, None)

def _cache_get(key: str):
    _gc()
    v = _CACHE.get(key)
    return v.get("data") if v else None

def _cache_set(key: str, data: Any):
    _gc()
    _CACHE[key] = {"_ts": time.time(), "data": data}


# -------------------------------------------------
# Startup warm-up (safe)
# -------------------------------------------------
@app.on_event("startup")
def _startup_warm():
    try:
        utc_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        get_planets_ecliptic(utc_iso, 0.0, 0.0)
        kp_star_sub_sub(0.0)
        print("[STARTUP] warm ok", flush=True)
    except Exception as e:
        print(f"[STARTUP] warm fail: {e}", flush=True)


# -------------------------------------------------
# Health / Debug
# -------------------------------------------------
@app.get("/")
def root():
    return {"ok": True, "service": "kp-nasa-backend"}

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.get("/health")
def health():
    return {"ok": True, "service": "kp-nasa-backend"}

@app.get("/debug/routes")
def debug_routes():
    return [r.path for r in app.routes]


# -------------------------------------------------
# Timezone API
# -------------------------------------------------
@app.get("/timezone")
def timezone_lookup(lat: float = Query(...), lon: float = Query(...)):
    if not _TZF_OK:
        return {"tz": "UTC", "ok": False, "message": f"timezonefinder missing: {_TZF_ERR}"}
    try:
        tz = _TZF.timezone_at(lat=float(lat), lng=float(lon))
        if not tz:
            tz = _TZF.closest_timezone_at(lat=float(lat), lng=float(lon))
        return {"tz": tz or "UTC", "ok": True}
    except Exception as e:
        return {"tz": "UTC", "ok": False, "message": str(e)}


# -------------------------------------------------
# Editorial JSON content
# -------------------------------------------------
@app.get("/content/utilities.json")
def serve_utilities_json():
    file_path = os.path.join("content", "utilities.json")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return JSONResponse(content=data)
    except Exception as e:
        return JSONResponse(status_code=404, content={"error": "utilities.json not found", "message": str(e), "path": file_path})


# -------------------------------------------------
# NASA API (cached)
# -------------------------------------------------
@app.post("/api/astro/nasa", response_model=NASAResp)
def nasa_positions(req: NASAReq):
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
        star, sub, subsub = kp_star_sub_sub(lon)  # legacy (tropical here)
        if p["name"] == "Moon":
            moon_lon = lon
        enriched.append({**p, "starLord": star, "subLord": sub, "subSubLord": subsub})

    if moon_lon is not None:
        rahu_lon, ketu_lon = calc_rahu_ketu(moon_lon)
        r_star, r_sub, r_ss = kp_star_sub_sub(rahu_lon)
        k_star, k_sub, k_ss = kp_star_sub_sub(ketu_lon)
        enriched.append({"name":"Rahu","lon":rahu_lon,"lat":0.0,"dist_au":0.0,"speed_lon":-0.053,"starLord":r_star,"subLord":r_sub,"subSubLord":r_ss})
        enriched.append({"name":"Ketu","lon":ketu_lon,"lat":0.0,"dist_au":0.0,"speed_lon":-0.053,"starLord":k_star,"subLord":k_sub,"subSubLord":k_ss})

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
# Panchangam API
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
    return compute_panchangam(datetimeLocal=req.datetimeLocal, tz=req.tz, lat=req.lat, lon=req.lon, ayan_deg=float(ayan))


# -------------------------------------------------
# HOME API (cached)
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

def _safe_bool(v: Any, default: bool = False) -> bool:
    try:
        if v is None:
            return default
        return bool(v)
    except Exception:
        return default

@app.post("/api/astro/home")
def astro_home(req: HomeReq):
    ayan_name = normalize_ayanamsa_name(req.ayanamsa)

    base_key = _make_key(req.datetimeLocal, req.tz, req.lat, req.lon, ayan_name)
    key = base_key + f"|D{int(_safe_bool(req.includeDasha, False))}|OP{int(_safe_bool(req.outerPlanets, False))}|NM{int(_safe_bool(req.nodeMode, True))}|H{int(_safe_bool(req.horaryOn, False))}|HN{int(req.horaryNumber or 1)}"

    cached = _cache_get(f"home:{key}")
    if cached:
        return cached

    utc_iso = local_to_utc_iso(req.datetimeLocal, req.tz)
    jd_ut, planets = get_planets_ecliptic(utc_iso, req.lat, req.lon)
    ayan = pick_ayanamsa_deg(jd_ut, ayan_name)

    moon_meta = _build_moon_meta(planets_tropical=planets, ayan_deg=float(ayan))

    cusps_trop = placidus_cusps(jd_ut, req.lat, req.lon)
    cusps_sid: Dict[str, Any] = {}
    for k, v in cusps_trop.items():
        try:
            cusps_sid[k] = norm360(float(v) - float(ayan))
        except Exception:
            cusps_sid[k] = v

    cusps_sid_map: Dict[int, float] = {i: float(cusps_sid.get(f"house{i}", 0.0)) for i in range(1, 13)}

    kundali_planets: List[Dict[str, Any]] = []
    kp_graha_table: List[Dict[str, Any]] = []

    for p in planets:
        name = p["name"]
        lon_sid = norm360(float(p["lon"]) - float(ayan))
        dms = _abs_to_dms(lon_sid)

        g_sign = sign_from_lon_deg(lon_sid)
        g_sign_name = SIGN_NAMES[g_sign]
        g_sign_lord = SIGN_LORD_BY_SIGN.get(g_sign, "")
        g_house = house_from_lon_and_cusps(lon_sid, cusps_sid_map)

        starL, subL, subsubL, nak_idx, nak_name = kp_star_sub_sub_v2(lon_sid)
        nak_lord = NAK_LORDS[int(nak_idx)]

        kundali_planets.append({"planet": name, "longitude": dms, "retro": float(p.get("speed_lon", 0.0)) < 0})
        kp_graha_table.append({
            "planet": name, "longitude": dms, "retro": float(p.get("speed_lon", 0.0)) < 0,
            "sign": g_sign, "signName": g_sign_name, "signLord": g_sign_lord,
            "house": g_house,
            "starLord": starL or "", "subLord": subL or "", "subSubLord": subsubL or "",
            "nakIndex": int(nak_idx), "nakName": nak_name, "nakLord": nak_lord, "starName": nak_name,
            "signifies": [], "star_signifies": [], "occupies": [g_house],
        })

    # mean node sidereal
    rahu_trop = float(mean_lunar_node_tropical_deg(jd_ut))
    ketu_trop = norm360(rahu_trop + 180.0)
    rahu_sid = norm360(rahu_trop - float(ayan))
    ketu_sid = norm360(ketu_trop - float(ayan))

    for name, lon in [("Rahu", rahu_sid), ("Ketu", ketu_sid)]:
        dms = _abs_to_dms(lon)
        g_sign = sign_from_lon_deg(lon)
        g_sign_name = SIGN_NAMES[g_sign]
        g_sign_lord = SIGN_LORD_BY_SIGN.get(g_sign, "")
        g_house = house_from_lon_and_cusps(lon, cusps_sid_map)

        starL, subL, subsubL, nak_idx, nak_name = kp_star_sub_sub_v2(lon)
        nak_lord = NAK_LORDS[int(nak_idx)]

        kundali_planets.append({"planet": name, "longitude": dms, "retro": True})
        kp_graha_table.append({
            "planet": name, "longitude": dms, "retro": True,
            "sign": g_sign, "signName": g_sign_name, "signLord": g_sign_lord,
            "house": g_house,
            "starLord": starL or "", "subLord": subL or "", "subSubLord": subsubL or "",
            "nakIndex": int(nak_idx), "nakName": nak_name, "nakLord": nak_lord, "starName": nak_name,
            "signifies": [], "star_signifies": [], "occupies": [g_house],
        })

    # bhava tables (kept legacy kp_star_sub_sub)
    bhava_cusps: List[Dict[str, Any]] = []
    kp_bhava_table: List[Dict[str, Any]] = []
    for i in range(1, 13):
        lon_sid = float(cusps_sid.get(f"house{i}", 0.0))
        dms = _abs_to_dms(lon_sid)
        sgn = sign_from_lon_deg(lon_sid)
        sgn_lord = SIGN_LORD_BY_SIGN.get(sgn, "")
        c_star, c_sub, c_ss = kp_star_sub_sub(lon_sid)
        bhava_cusps.append({"bhava": i, "longitude": dms, "sign": sgn, "signName": SIGN_NAMES[sgn], "signLord": sgn_lord})
        kp_bhava_table.append({"bhava": i, "longitude": dms, "sign": sgn, "signName": SIGN_NAMES[sgn], "signLord": sgn_lord, "starLord": c_star or "", "subLord": c_sub or "", "subSubLord": c_ss or ""})

    # includeDasha (SAFE: no legacy build_level_list)
    dasha_payload = None
    vim_payload = None
    if _safe_bool(req.includeDasha, False):
        try:
            # compute moon sidereal
            moon_trop = None
            for p in planets:
                if str(p.get("name", "")).strip().lower() == "moon":
                    moon_trop = float(p.get("lon", 0.0)) % 360.0
                    break
            if moon_trop is None:
                raise ValueError("Moon not found")
            moon_sid = norm360(moon_trop - float(ayan))
            maha_lord, balance_years = moon_vimshottari_info(moon_sid)
            start_utc = _parse_iso_utc(utc_iso)
            tree = build_vimshottari_tree(start_utc=start_utc, maha_lord=str(maha_lord), maha_balance_years=float(balance_years), max_levels=4)
            dasha_payload = {"tree": tree, "meta": {"utc_iso": utc_iso, "jd_ut": jd_ut}}
            vim_payload = dasha_payload
        except Exception as e:
            dasha_payload = {"tree": [], "error": str(e)}
            vim_payload = dasha_payload

    resp = {
        "meta": {
            "source": "kp-nasa-backend", "utc_iso": utc_iso, "jd_ut": jd_ut, "tz": req.tz, "lat": req.lat, "lon": req.lon,
            "ayanamsa": ayan_name, "ayanamsaValueDeg": float(ayan), "includeDasha": bool(_safe_bool(req.includeDasha, False)),
        },
        "ayanamsa": {"value": float(ayan), "name": ayan_name},
        "ayanamsaValueDeg": float(ayan),
        "moonMeta": moon_meta,
        "panchangam": None,
        "kundali": {"planets": kundali_planets, "bhavaCusps": bhava_cusps},
        "kp": {"ayanamsa": float(ayan), "grahaTable": kp_graha_table, "bhavaTable": kp_bhava_table},
        "dasha": dasha_payload,
        "vimshottari": vim_payload,
        "rulingPlanets": None,
    }

    _cache_set(f"home:{key}", resp)
    return resp


# -------------------------------------------------
# LAZY DASHA APIs (elapsed-aware / clipped)
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

    key = _make_key(req.datetimeLocal, req.tz, req.lat, req.lon, ayan_name)
    ses = {"_ts": time.time(), "key": key, "utc_iso": utc_iso, "jd_ut": jd_ut, "ayanamsa": ayan_name, "ayan_deg": float(ayan), "moon_sid": float(moon_sid), "maha_lord": str(maha_lord), "balance_years": float(max(0.0, balance_years)), "start_utc": _parse_iso_utc(utc_iso)}
    _SESSION[key] = ses
    return ses

@app.post("/api/dasha/maha")
def dasha_maha(req: DashaBaseReq):
    ayan_name = normalize_ayanamsa_name(req.ayanamsa)
    key = _make_key(req.datetimeLocal, req.tz, req.lat, req.lon, ayan_name)

    cached = _cache_get(f"maha:{key}")
    if cached:
        return cached

    ses = _SESSION.get(key) or _ensure_session(req)
    maha_list = build_mahadasha_list_120y_9items(start_utc=ses["start_utc"], maha_lord=ses["maha_lord"], maha_balance_years=ses["balance_years"])
    out = {"meta": {"key": key, "utc_iso": ses["utc_iso"], "jd_ut": ses["jd_ut"], "ayanamsa": ses["ayanamsa"], "ayanamsaValueDeg": ses["ayan_deg"]}, "maha": maha_list}
    _cache_set(f"maha:{key}", out)
    return out

@app.post("/api/dasha/bhukti")
def dasha_bhukti(req: DashaLevelReq):
    cached = _cache_get(f"bh2:{req.key}:{req.mahaLord}:{req.start}:{req.end}")
    if cached:
        return cached
    maha = str(req.mahaLord or "").strip()
    if not maha:
        raise HTTPException(status_code=400, detail="mahaLord required")
    rem_years = _years_between_iso(req.start, req.end)
    tree = build_vimshottari_tree(start_utc=_parse_iso_utc(req.start), maha_lord=maha, maha_balance_years=rem_years, max_levels=2)
    bh = (tree[0] or {}).get("bhukti", []) if tree else []
    out = {"bhukti": bh}
    _cache_set(f"bh2:{req.key}:{maha}:{req.start}:{req.end}", out)
    return out

@app.post("/api/dasha/antara")
def dasha_antara(req: DashaLevelReq):
    try:
        cached = _cache_get(f"an2:{req.key}:{req.mahaLord}:{req.bhuktiLord}:{req.start}:{req.end}")
        if cached:
            return cached

        maha = str(req.mahaLord or "").strip()
        bh = str(req.bhuktiLord or "").strip()
        if not maha:
            raise ValueError("mahaLord required")
        if not bh:
            raise ValueError("bhuktiLord required")

        rem_years = _years_between_iso(req.start, req.end)
        md_total_years = float(DASHA_YEARS.get(maha, 0.0))
        md_total_days = md_total_years * 365.2425
        md_rem_days = max(0.0, rem_years * 365.2425)
        md_elapsed_days = max(0.0, md_total_days - md_rem_days)

        md_clip_start = _parse_iso_utc(req.start)
        md_clip_end = _parse_iso_utc(req.end)
        md_full_start = _add_days(md_clip_start, -md_elapsed_days)
        md_full_end = _add_days(md_full_start, md_total_days)

        bh_full = get_child_full_window(maha, md_full_start, md_full_end, bh, md_clip_start, md_clip_end)
        if not bh_full:
            out = {"antara": []}
            _cache_set(f"an2:{req.key}:{maha}:{bh}:{req.start}:{req.end}", out)
            return out

        bh_full_start, bh_full_end = bh_full
        an = build_level_list_clipped(level="antara", parent_lord=bh, parent_full_start=bh_full_start, parent_full_end=bh_full_end, clip_start=md_clip_start, clip_end=md_clip_end)
        out = {"antara": an}
        _cache_set(f"an2:{req.key}:{maha}:{bh}:{req.start}:{req.end}", out)
        return out

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"antara error: {e}")

@app.post("/api/dasha/sukshma")
def dasha_sukshma(req: DashaLevelReq):
    try:
        cached = _cache_get(f"su2:{req.key}:{req.mahaLord}:{req.bhuktiLord}:{req.antaraLord}:{req.start}:{req.end}")
        if cached:
            return cached

        maha = str(req.mahaLord or "").strip()
        bh = str(req.bhuktiLord or "").strip()
        an = str(req.antaraLord or "").strip()
        if not maha:
            raise ValueError("mahaLord required")
        if not bh:
            raise ValueError("bhuktiLord required")
        if not an:
            raise ValueError("antaraLord required")

        rem_years = _years_between_iso(req.start, req.end)
        md_total_years = float(DASHA_YEARS.get(maha, 0.0))
        md_total_days = md_total_years * 365.2425
        md_rem_days = max(0.0, rem_years * 365.2425)
        md_elapsed_days = max(0.0, md_total_days - md_rem_days)

        md_clip_start = _parse_iso_utc(req.start)
        md_clip_end = _parse_iso_utc(req.end)
        md_full_start = _add_days(md_clip_start, -md_elapsed_days)
        md_full_end = _add_days(md_full_start, md_total_days)

        bh_full = get_child_full_window(maha, md_full_start, md_full_end, bh, md_clip_start, md_clip_end)
        if not bh_full:
            out = {"sukshma": []}
            _cache_set(f"su2:{req.key}:{maha}:{bh}:{an}:{req.start}:{req.end}", out)
            return out
        bh_full_start, bh_full_end = bh_full

        an_full = get_child_full_window(bh, bh_full_start, bh_full_end, an, md_clip_start, md_clip_end)
        if not an_full:
            out = {"sukshma": []}
            _cache_set(f"su2:{req.key}:{maha}:{bh}:{an}:{req.start}:{req.end}", out)
            return out
        an_full_start, an_full_end = an_full

        su = build_level_list_clipped(level="sukshma", parent_lord=an, parent_full_start=an_full_start, parent_full_end=an_full_end, clip_start=md_clip_start, clip_end=md_clip_end)
        out = {"sukshma": su}
        _cache_set(f"su2:{req.key}:{maha}:{bh}:{an}:{req.start}:{req.end}", out)
        return out

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"sukshma error: {e}")

@app.post("/api/dasha/prana")
def dasha_prana(req: DashaLevelReq):
    try:
        cached = _cache_get(f"pr2:{req.key}:{req.mahaLord}:{req.bhuktiLord}:{req.antaraLord}:{req.sukshmaLord}:{req.start}:{req.end}")
        if cached:
            return cached

        maha = str(req.mahaLord or "").strip()
        bh = str(req.bhuktiLord or "").strip()
        an = str(req.antaraLord or "").strip()
        su = str(req.sukshmaLord or "").strip()
        if not maha:
            raise ValueError("mahaLord required")
        if not bh:
            raise ValueError("bhuktiLord required")
        if not an:
            raise ValueError("antaraLord required")
        if not su:
            raise ValueError("sukshmaLord required")

        rem_years = _years_between_iso(req.start, req.end)
        md_total_years = float(DASHA_YEARS.get(maha, 0.0))
        md_total_days = md_total_years * 365.2425
        md_rem_days = max(0.0, rem_years * 365.2425)
        md_elapsed_days = max(0.0, md_total_days - md_rem_days)

        md_clip_start = _parse_iso_utc(req.start)
        md_clip_end = _parse_iso_utc(req.end)
        md_full_start = _add_days(md_clip_start, -md_elapsed_days)
        md_full_end = _add_days(md_full_start, md_total_days)

        bh_full = get_child_full_window(maha, md_full_start, md_full_end, bh, md_clip_start, md_clip_end)
        if not bh_full:
            out = {"prana": []}
            _cache_set(f"pr2:{req.key}:{maha}:{bh}:{an}:{su}:{req.start}:{req.end}", out)
            return out
        bh_full_start, bh_full_end = bh_full

        an_full = get_child_full_window(bh, bh_full_start, bh_full_end, an, md_clip_start, md_clip_end)
        if not an_full:
            out = {"prana": []}
            _cache_set(f"pr2:{req.key}:{maha}:{bh}:{an}:{su}:{req.start}:{req.end}", out)
            return out
        an_full_start, an_full_end = an_full

        su_full = get_child_full_window(an, an_full_start, an_full_end, su, md_clip_start, md_clip_end)
        if not su_full:
            out = {"prana": []}
            _cache_set(f"pr2:{req.key}:{maha}:{bh}:{an}:{su}:{req.start}:{req.end}", out)
            return out
        su_full_start, su_full_end = su_full

        pr = build_level_list_clipped(level="prana", parent_lord=su, parent_full_start=su_full_start, parent_full_end=su_full_end, clip_start=md_clip_start, clip_end=md_clip_end)
        out = {"prana": pr}
        _cache_set(f"pr2:{req.key}:{maha}:{bh}:{an}:{su}:{req.start}:{req.end}", out)
        return out

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"prana error: {e}")
