# main.py ✅ (FULL REPLACE)
# ✅ Updates in this version (SAFE, non-breaking):
# - ✅ ADD: kp.grahaTable planets now include:
#     - signLord
#     - nakIndex, nakName, nakLord
#     - starName (alias to nakName)
# - ✅ ADD: /api/astro/home also returns moonMeta (safe for daily screens)
# - ✅ Keeps: cache key fix, includeDasha tree build, timezone fix, sign/signName for cusps, occupies, etc.
# - ❌ Does NOT add rashiphal endpoints yet (to keep deploy stable; we'll add after files exist)

from datetime import datetime, timezone
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import hashlib
import time
import os
import json

# ✅ TimezoneFinder (SAFE import)
try:
    from timezonefinder import TimezoneFinder  # pip install timezonefinder
    _TZF = TimezoneFinder()
    _TZF_OK = True
    _TZF_ERR = ""
except Exception as _e:
    _TZF = None
    _TZF_OK = False
    _TZF_ERR = str(_e)

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
from app.core.vimshottari_tree import build_mahadasha_list_120y_9items, build_level_list

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
# ✅ Startup warm-up
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
@app.get("/health")
def health():
    return {"ok": True, "service": "kp-nasa-backend"}

@app.get("/debug/routes")
def debug_routes():
    return [r.path for r in app.routes]

# -------------------------------------------------
# ✅ Timezone API (worldwide)
# -------------------------------------------------
@app.get("/timezone")
def timezone_lookup(lat: float = Query(...), lon: float = Query(...)):
    """
    Returns IANA timezone for a lat/lon.
    Example: Europe/London, Asia/Tokyo, America/New_York
    """
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
# ✅ Editorial JSON content
# -------------------------------------------------
@app.get("/content/utilities.json")
def serve_utilities_json():
    file_path = os.path.join("content", "utilities.json")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return JSONResponse(content=data)
    except Exception as e:
        return JSONResponse(
            status_code=404,
            content={"error": "utilities.json not found", "message": str(e), "path": file_path},
        )

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
    if ayanamsa_name == "KP":
        return lahiri - 0.1015
    return lahiri

def _iso_to_dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)

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
    dtb = _bucket_datetimeLocal(datetimeLocal, 60)
    raw = f"{dtb}|{tz}|{float(lat):.5f}|{float(lon):.5f}|{ayanamsa}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()

# -----------------------------
# ✅ Sign helpers
# -----------------------------
SIGN_NAMES = [
    "", "Mesha", "Vrishabha", "Mithuna", "Karkataka", "Simha", "Kanya",
    "Tula", "Vrischika", "Dhanu", "Makara", "Kumbha", "Meena"
]

SIGN_LORD_BY_SIGN: Dict[int, str] = {
    1: "Mars",
    2: "Venus",
    3: "Mercury",
    4: "Moon",
    5: "Sun",
    6: "Mercury",
    7: "Venus",
    8: "Mars",
    9: "Jupiter",
    10: "Saturn",
    11: "Saturn",
    12: "Jupiter",
}

def sign_from_lon_deg(lon: float) -> int:
    d = norm360(float(lon))
    return int(d // 30) + 1  # 1..12

def house_from_lon_and_cusps(lon: float, cusps_sid_by_house: Dict[int, float]) -> int:
    """
    cusps_sid_by_house: {1:deg,2:deg,...,12:deg} sidereal
    returns occupied house 1..12 (cusp segment logic)
    """
    lon = norm360(float(lon))
    cusp = {int(k): norm360(float(v)) for k, v in cusps_sid_by_house.items()}

    for h in range(1, 12):
        a = cusp[h]
        b = cusp[h + 1]
        if a <= b:
            if a <= lon < b:
                return h
        else:
            if lon >= a or lon < b:
                return h

    a = cusp[12]
    b = cusp[1]
    if a <= b:
        if a <= lon < b:
            return 12
    else:
        if lon >= a or lon < b:
            return 12
    return 12

# -----------------------------
# ✅ Nakshatra helpers (NEW)
# -----------------------------
NAK_NAMES = [
    "Ashwini","Bharani","Krittika","Rohini","Mrigashirsha","Ardra","Punarvasu","Pushya","Ashlesha",
    "Magha","Purva Phalguni","Uttara Phalguni","Hasta","Chitra","Swati","Vishakha","Anuradha","Jyeshtha",
    "Mula","Purva Ashadha","Uttara Ashadha","Shravana","Dhanishta","Shatabhisha","Purva Bhadrapada","Uttara Bhadrapada","Revati"
]
NAK_LORDS = [
    "Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury",
    "Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury",
    "Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury"
]

def nakshatra_from_lon_sid(lon_sid: float):
    x = norm360(float(lon_sid))
    idx = int(x // (360.0 / 27.0))  # 0..26
    idx = max(0, min(26, idx))
    return idx, NAK_NAMES[idx], NAK_LORDS[idx]

def _build_moon_meta(planets_tropical: List[Dict[str, Any]], ayan_deg: float) -> Optional[Dict[str, Any]]:
    """
    SAFE: returns moonMeta or None
    moonMeta includes sidereal lon, rashiIndex(0..11), rashiName, nakIndex(0..26), nakName, nakLord
    """
    try:
        moon_trop = None
        for p in planets_tropical or []:
            if str(p.get("name", "")).strip().lower() == "moon":
                moon_trop = float(p.get("lon", 0.0)) % 360.0
                break
        if moon_trop is None:
            return None

        moon_sid = norm360(float(moon_trop) - float(ayan_deg))

        rashi_idx0 = int(moon_sid // 30.0)
        rashi_idx0 = max(0, min(11, rashi_idx0))
        rashi_name = SIGN_NAMES[rashi_idx0 + 1]

        nak_idx, nak_name, nak_lord = nakshatra_from_lon_sid(moon_sid)

        return {
            "moonLonTropicalDeg": float(moon_trop),
            "moonLonSiderealDeg": float(moon_sid),

            "moonRashiIndex": int(rashi_idx0),   # 0..11
            "moonRashiName": str(rashi_name),

            "nakIndex": int(nak_idx),            # 0..26
            "nakName": str(nak_name),
            "nakLord": str(nak_lord),
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
        star, sub, subsub = kp_star_sub_sub(lon)

        if p["name"] == "Moon":
            moon_lon = lon

        enriched.append({**p, "starLord": star, "subLord": sub, "subSubLord": subsub})

    if moon_lon is not None:
        rahu_lon, ketu_lon = calc_rahu_ketu(moon_lon)
        r_star, r_sub, r_ss = kp_star_sub_sub(rahu_lon)
        k_star, k_sub, k_ss = kp_star_sub_sub(ketu_lon)

        enriched.append({
            "name": "Rahu", "lon": rahu_lon, "lat": 0.0, "dist_au": 0.0, "speed_lon": -0.053,
            "starLord": r_star, "subLord": r_sub, "subSubLord": r_ss
        })
        enriched.append({
            "name": "Ketu", "lon": ketu_lon, "lat": 0.0, "dist_au": 0.0, "speed_lon": -0.053,
            "starLord": k_star, "subLord": k_sub, "subSubLord": k_ss
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

    return compute_panchangam(
        datetimeLocal=req.datetimeLocal,
        tz=req.tz,
        lat=req.lat,
        lon=req.lon,
        ayan_deg=float(ayan),
    )

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

def _build_home_dasha_tree_upto_sukshma(
    utc_iso: str,
    jd_ut: float,
    planets_tropical: List[Dict[str, Any]],
    ayan_deg: float,
) -> Dict[str, Any]:
    moon_trop = None
    for p in planets_tropical or []:
        if str(p.get("name", "")).strip().lower() == "moon":
            moon_trop = float(p.get("lon", 0.0)) % 360.0
            break
    if moon_trop is None:
        return {"tree": []}

    moon_sid = norm360(float(moon_trop) - float(ayan_deg))
    maha_lord, balance_years = moon_vimshottari_info(moon_sid)
    balance_years = max(0.0, float(balance_years))

    start_utc = datetime.fromisoformat(utc_iso.replace("Z", "+00:00")).astimezone(timezone.utc)

    maha_list = build_mahadasha_list_120y_9items(
        start_utc=start_utc,
        maha_lord=str(maha_lord),
        maha_balance_years=float(balance_years),
    ) or []

    maha_nodes: List[Dict[str, Any]] = []
    for md in maha_list:
        md_lord = str(md.get("lord") or md.get("planet") or md.get("name") or md.get("key") or "").strip()
        md_start = str(md.get("start") or md.get("from") or "").strip()
        md_end = str(md.get("end") or md.get("to") or "").strip()

        node_md: Dict[str, Any] = {"lord": md_lord, "start": md_start, "end": md_end, "bhukti": []}

        try:
            b_list = build_level_list("bhukti", _iso_to_dt(md_start), _iso_to_dt(md_end), md_lord) or []
        except Exception:
            b_list = []

        bhukti_nodes: List[Dict[str, Any]] = []
        for b in b_list:
            b_lord = str(b.get("lord") or b.get("planet") or b.get("name") or b.get("key") or "").strip()
            b_start = str(b.get("start") or b.get("from") or "").strip()
            b_end = str(b.get("end") or b.get("to") or "").strip()
            node_b: Dict[str, Any] = {"lord": b_lord, "start": b_start, "end": b_end, "antara": []}

            try:
                a_list = build_level_list("antara", _iso_to_dt(b_start), _iso_to_dt(b_end), b_lord) or []
            except Exception:
                a_list = []

            antara_nodes: List[Dict[str, Any]] = []
            for a in a_list:
                a_lord = str(a.get("lord") or a.get("planet") or a.get("name") or a.get("key") or "").strip()
                a_start = str(a.get("start") or a.get("from") or "").strip()
                a_end = str(a.get("end") or a.get("to") or "").strip()
                node_a: Dict[str, Any] = {"lord": a_lord, "start": a_start, "end": a_end, "sukshma": []}

                try:
                    s_list = build_level_list("sukshma", _iso_to_dt(a_start), _iso_to_dt(a_end), a_lord) or []
                except Exception:
                    s_list = []

                suk_nodes: List[Dict[str, Any]] = []
                for s in s_list:
                    s_lord = str(s.get("lord") or s.get("planet") or s.get("name") or s.get("key") or "").strip()
                    s_start = str(s.get("start") or s.get("from") or "").strip()
                    s_end = str(s.get("end") or s.get("to") or "").strip()
                    suk_nodes.append({"lord": s_lord, "start": s_start, "end": s_end})

                node_a["sukshma"] = suk_nodes
                antara_nodes.append(node_a)

            node_b["antara"] = antara_nodes
            bhukti_nodes.append(node_b)

        node_md["bhukti"] = bhukti_nodes
        maha_nodes.append(node_md)

    return {
        "tree": maha_nodes,
        "meta": {"utc_iso": utc_iso, "jd_ut": jd_ut},
        "note": "Built in HOME includeDasha=True (Mahadasha→Bhukti→Antara→Sukshma)",
    }

@app.post("/api/astro/home")
def astro_home(req: HomeReq):
    ayan_name = normalize_ayanamsa_name(req.ayanamsa)

    base_key = _make_key(req.datetimeLocal, req.tz, req.lat, req.lon, ayan_name)
    key = (
        base_key
        + f"|D{int(_safe_bool(req.includeDasha, False))}"
        + f"|OP{int(_safe_bool(req.outerPlanets, False))}"
        + f"|NM{int(_safe_bool(req.nodeMode, True))}"
        + f"|H{int(_safe_bool(req.horaryOn, False))}"
        + f"|HN{int(req.horaryNumber or 1)}"
    )

    cached = _cache_get(f"home:{key}")
    if cached:
        return cached

    utc_iso = local_to_utc_iso(req.datetimeLocal, req.tz)
    jd_ut, planets = get_planets_ecliptic(utc_iso, req.lat, req.lon)
    ayan = pick_ayanamsa_deg(jd_ut, ayan_name)

    # ✅ moonMeta for daily usage
    moon_meta = _build_moon_meta(planets_tropical=planets, ayan_deg=float(ayan))

    # --- cusps (trop -> sidereal) ---
    cusps_trop = placidus_cusps(jd_ut, req.lat, req.lon)
    cusps_sid: Dict[str, Any] = {}
    for k, v in cusps_trop.items():
        try:
            cusps_sid[k] = norm360(float(v) - float(ayan))
        except Exception:
            cusps_sid[k] = v

    cusps_sid_map: Dict[int, float] = {}
    for i in range(1, 13):
        cusps_sid_map[i] = float(cusps_sid.get(f"house{i}", 0.0))

    kundali_planets: List[Dict[str, Any]] = []
    kp_graha_table: List[Dict[str, Any]] = []

    # --- planets (sidereal longitudes) ---
    for p in planets:
        name = p["name"]
        lon_sid = norm360(float(p["lon"]) - ayan)
        dms = _abs_to_dms(lon_sid)

        g_sign = sign_from_lon_deg(lon_sid)
        g_sign_name = SIGN_NAMES[g_sign]
        g_sign_lord = SIGN_LORD_BY_SIGN.get(g_sign, "")
        g_house = house_from_lon_and_cusps(lon_sid, cusps_sid_map)

        star, sub, subsub = kp_star_sub_sub(lon_sid)
        nak_idx, nak_name, nak_lord = nakshatra_from_lon_sid(lon_sid)

        kundali_planets.append({
            "planet": name,
            "longitude": dms,
            "retro": float(p.get("speed_lon", 0.0)) < 0
        })

        kp_graha_table.append({
            "planet": name,
            "longitude": dms,
            "retro": float(p.get("speed_lon", 0.0)) < 0,

            "sign": g_sign,
            "signName": g_sign_name,
            "signLord": g_sign_lord,
            "house": g_house,

            "starLord": star or "",
            "subLord": sub or "",
            "subSubLord": subsub or "",

            "nakIndex": int(nak_idx),
            "nakName": nak_name,
            "nakLord": nak_lord,
            "starName": nak_name,  # alias

            "signifies": [],
            "star_signifies": [],
            "occupies": [g_house],
        })

    # --- Rahu/Ketu (mean node) sidereal ---
    rahu_trop = float(mean_lunar_node_tropical_deg(jd_ut))
    ketu_trop = norm360(rahu_trop + 180.0)
    rahu_sid = norm360(rahu_trop - ayan)
    ketu_sid = norm360(ketu_trop - ayan)

    for name, lon in [("Rahu", rahu_sid), ("Ketu", ketu_sid)]:
        dms = _abs_to_dms(lon)

        g_sign = sign_from_lon_deg(lon)
        g_sign_name = SIGN_NAMES[g_sign]
        g_sign_lord = SIGN_LORD_BY_SIGN.get(g_sign, "")
        g_house = house_from_lon_and_cusps(lon, cusps_sid_map)

        star, sub, subsub = kp_star_sub_sub(lon)
        nak_idx, nak_name, nak_lord = nakshatra_from_lon_sid(lon)

        kundali_planets.append({"planet": name, "longitude": dms, "retro": True})
        kp_graha_table.append({
            "planet": name,
            "longitude": dms,
            "retro": True,

            "sign": g_sign,
            "signName": g_sign_name,
            "signLord": g_sign_lord,
            "house": g_house,

            "starLord": star or "",
            "subLord": sub or "",
            "subSubLord": subsub or "",

            "nakIndex": int(nak_idx),
            "nakName": nak_name,
            "nakLord": nak_lord,
            "starName": nak_name,

            "signifies": [],
            "star_signifies": [],
            "occupies": [g_house],
        })

    # --- bhava cusps tables (untouched) ---
    bhava_cusps: List[Dict[str, Any]] = []
    kp_bhava_table: List[Dict[str, Any]] = []

    for i in range(1, 13):
        house_key = f"house{i}"
        lon_sid = float(cusps_sid.get(house_key, 0.0))
        dms = _abs_to_dms(lon_sid)

        sgn = sign_from_lon_deg(lon_sid)
        sgn_lord = SIGN_LORD_BY_SIGN.get(sgn, "")

        c_star, c_sub, c_ss = kp_star_sub_sub(lon_sid)

        bhava_cusps.append({
            "bhava": i,
            "longitude": dms,
            "sign": sgn,
            "signName": SIGN_NAMES[sgn],
            "signLord": sgn_lord,
        })

        kp_bhava_table.append({
            "bhava": i,
            "longitude": dms,
            "sign": sgn,
            "signName": SIGN_NAMES[sgn],
            "signLord": sgn_lord,
            "starLord": c_star or "",
            "subLord": c_sub or "",
            "subSubLord": c_ss or "",
        })

    # ✅ If includeDasha=True, build tree
    dasha_payload = None
    vim_payload = None
    if _safe_bool(req.includeDasha, False):
        try:
            dasha_payload = _build_home_dasha_tree_upto_sukshma(
                utc_iso=utc_iso,
                jd_ut=jd_ut,
                planets_tropical=planets,
                ayan_deg=float(ayan),
            )
            vim_payload = dasha_payload
        except Exception as e:
            dasha_payload = {"tree": [], "error": str(e)}
            vim_payload = dasha_payload

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
            "includeDasha": bool(_safe_bool(req.includeDasha, False)),
        },
        "ayanamsa": {"value": float(ayan), "name": ayan_name},
        "ayanamsaValueDeg": float(ayan),

        # ✅ daily screens use this (no extra endpoint needed)
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
# LAZY DASHA APIs (unchanged)
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

    ses = _SESSION.get(key) or _ensure_session(req)

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
