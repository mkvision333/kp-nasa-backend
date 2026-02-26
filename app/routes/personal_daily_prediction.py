# app/routes/personal_daily_prediction.py ✅ NEW
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.vimshottari_tree import build_vimshottari_tree, DASHA_YEARS
from app.core.kp_significators import build_kp_significators_advanced

# You already have this file:
# app/core/kp_calc.py (you pasted)
from app.core.kp_calc import kp_star_sub, NAKSHATRA_LORDS

router = APIRouter(prefix="/api", tags=["personal_prediction"])

Gender = Literal["MALE", "FEMALE"]
Level = Literal["GOOD", "AVERAGE", "BAD"]

# -------------------- Models --------------------
class DMSIn(BaseModel):
    deg: int
    min: int
    sec: int

class BhavaCuspIn(BaseModel):
    bhava: int
    longitude: DMSIn

class GrahaRowIn(BaseModel):
    planet: str
    longitude: DMSIn
    retro: Optional[bool] = None
    starLord: Optional[str] = None
    subLord: Optional[str] = None
    subSubLord: Optional[str] = None

class NatalIn(BaseModel):
    cusps: List[BhavaCuspIn]
    planets: List[GrahaRowIn]  # must include Moon at least

class ProfileIn(BaseModel):
    name: str = Field(..., min_length=2, max_length=60)
    gender: Gender
    birthDT: str  # local ISO string
    placeName: str
    lat: float
    lon: float
    tz: str = "Asia/Kolkata"

class PredictionReq(BaseModel):
    profile: ProfileIn
    natal: NatalIn  # ✅ for now we require natal payload (your app already has these)
    dateISO: Optional[str] = None  # YYYY-MM-DD
    enableExplain: bool = False

class AreaLine(BaseModel):
    level: Level
    line: str

class PredictionOut(BaseModel):
    dateISO: str
    score: int
    verdict: Level
    bestFor: List[str]
    avoid: List[str]
    areas: Dict[str, AreaLine]
    moon: Dict[str, Optional[str]]
    dasha: Dict[str, Optional[str]]
    birthKpData: Dict[str, Any]
    fullText: str

# -------------------- Small helpers --------------------
def _norm360(x: float) -> float:
    x = x % 360.0
    return x if x >= 0 else x + 360.0

def _dms_to_abs(d: Dict[str, Any]) -> float:
    return float(d.get("deg", 0)) + float(d.get("min", 0))/60.0 + float(d.get("sec", 0))/3600.0

def _parse_birth_iso_local_to_utc(birth_iso: str) -> datetime:
    """
    birthDT coming as local ISO (no tz) from app.
    For MVP: treat it as UTC if tz missing.
    Better: pass birthDT with tz offset from client, or also pass tz and convert properly.
    """
    dt = datetime.fromisoformat(str(birth_iso).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def _moon_lon_from_natal(natal: NatalIn) -> float:
    for g in natal.planets:
        if g.planet.strip() == "Moon":
            return _norm360(_dms_to_abs(g.longitude.model_dump()))
    raise ValueError("Moon not found in natal.planets")

def _compute_maha_lord_and_balance_years(moon_lon_nir: float) -> Dict[str, Any]:
    """
    KP/Vimshottari: current MD lord = star lord of Moon (nakshatra lord)
    balance fraction = 1 - (position in star / star_size)
    balance years = dasha_years[lord] * balance_fraction
    """
    star_size = 360.0 / 27.0
    moon_lon = _norm360(moon_lon_nir)
    star_index = int(moon_lon // star_size)
    maha_lord = NAKSHATRA_LORDS[star_index]
    pos_in_star = moon_lon - (star_index * star_size)
    elapsed_frac = pos_in_star / star_size
    balance_frac = max(0.0, min(1.0, 1.0 - elapsed_frac))
    md_years = float(DASHA_YEARS.get(maha_lord, 7.0))
    balance_years = md_years * balance_frac
    return {"mahaLord": maha_lord, "balanceYears": balance_years}

def _pick_running_chain(tree_root: Dict[str, Any]) -> Dict[str, Optional[str]]:
    """
    tree_root already NOW-clipped so first items are current
    """
    maha = tree_root.get("lord")
    bh = None
    an = None
    su = None

    bh_list = tree_root.get("bhukti") or []
    if bh_list:
        bh = bh_list[0].get("lord")
        an_list = bh_list[0].get("antara") or []
        if an_list:
            an = an_list[0].get("lord")
            su_list = an_list[0].get("sukshma") or []
            if su_list:
                su = su_list[0].get("lord")

    return {"maha": maha, "bhukti": bh, "antara": an, "sukshma": su}

def _score_from_houses(houses: List[int], want_good: List[int], want_bad: List[int]) -> Tuple[int, Level]:
    """
    Simple scoring:
    +2 for each good house present
    -2 for each bad house present
    """
    s = 0
    hs = set(int(x) for x in (houses or []) if 1 <= int(x) <= 12)
    for h in want_good:
        if h in hs:
            s += 2
    for h in want_bad:
        if h in hs:
            s -= 2
    # map to level
    if s >= 3:
        return s, "GOOD"
    if s <= -1:
        return s, "BAD"
    return s, "AVERAGE"

def _combine_houses_for_prediction(birth_kp: Dict[str, Any], chain: Dict[str, Optional[str]], moon_star: str, moon_sub: str) -> List[int]:
    """
    We combine significator houses of:
      - maha/bhukti/antara/sukshma lords
      - Moon star lord + Moon sub lord (today)
    Using birth KP ABCD significators only.
    """
    planet_sigs = birth_kp.get("planetSigs") or []
    sig_map: Dict[str, List[int]] = {}
    for row in planet_sigs:
        p = str(row.get("planet") or "").strip()
        sig_map[p] = [int(x) for x in (row.get("significators") or [])]

    picks = []
    for k in ["maha", "bhukti", "antara", "sukshma"]:
        L = chain.get(k)
        if L:
            picks += sig_map.get(L, [])
    if moon_star:
        picks += sig_map.get(moon_star, [])
    if moon_sub:
        picks += sig_map.get(moon_sub, [])
    # uniq sorted
    return sorted(list({int(x) for x in picks if 1 <= int(x) <= 12}))

# -------------------- Route --------------------
@router.post("/personal_daily_prediction", response_model=PredictionOut)
def personal_daily_prediction(req: PredictionReq) -> PredictionOut:
    try:
        p = req.profile

        # date
        d = date.fromisoformat(req.dateISO) if req.dateISO else date.today()

        # 1) Birth KP data (store once on client)
        birth_kp = build_kp_significators_advanced(
            graha_table=[g.model_dump() for g in req.natal.planets],
            bhava_cusps=[c.model_dump() for c in req.natal.cusps],
            enable_explain=bool(req.enableExplain),
        )

        # 2) Today moon star/sub (from natal Moon lon for MVP; later you can compute "today Moon")
        # For true "today" moon, call your ephemeris and compute nirayana lon, then kp_star_sub(todayMoonLon).
        moon_lon_nir = _moon_lon_from_natal(req.natal)
        moon_star, moon_sub = kp_star_sub(moon_lon_nir)

        # 3) Dasha chain
        birth_utc = _parse_birth_iso_local_to_utc(p.birthDT)
        md = _compute_maha_lord_and_balance_years(moon_lon_nir)
        tree = build_vimshottari_tree(birth_utc, md["mahaLord"], md["balanceYears"], max_levels=4)
        if not tree:
            chain = {"maha": md["mahaLord"], "bhukti": None, "antara": None, "sukshma": None}
        else:
            chain = _pick_running_chain(tree[0])

        # 4) Combine houses -> area scoring
        key_houses = _combine_houses_for_prediction(birth_kp, chain, moon_star, moon_sub)

        # Topic mapping (simple + practical)
        topic_map = {
            "life":    {"good": [1, 9, 11], "bad": [8, 12]},
            "money":   {"good": [2, 11], "bad": [6, 12]},
            "work":    {"good": [6, 10, 11], "bad": [8, 12]},
            "career":  {"good": [10, 11], "bad": [8, 12]},
            "business":{"good": [2, 7, 11], "bad": [6, 12]},
            "mind":    {"good": [1, 4, 9], "bad": [8, 12]},
            "family":  {"good": [2, 4], "bad": [6, 12]},
            "gain":    {"good": [11, 9], "bad": [12]},
            "loss":    {"good": [1, 9], "bad": [12, 6, 8]},
        }

        areas: Dict[str, Dict[str, str]] = {}
        raw_score = 50

        for k, cfg in topic_map.items():
            s, lvl = _score_from_houses(key_houses, cfg["good"], cfg["bad"])
            raw_score += int(s) * 2  # weight
            if lvl == "GOOD":
                line = "Favorable. Use this for key actions."
            elif lvl == "BAD":
                line = "Be cautious. Avoid risky decisions."
            else:
                line = "Average. Keep things steady and simple."
            areas[k] = {"level": lvl, "line": line}

        score = max(0, min(100, raw_score))
        verdict: Level = "GOOD" if score >= 70 else "AVERAGE" if score >= 50 else "BAD"

        best_for = []
        avoid = []
        if verdict == "GOOD":
            best_for = ["Important calls", "Meetings", "Collections", "Start/Launch"]
            avoid = ["Overconfidence", "Ego clashes"]
        elif verdict == "BAD":
            best_for = ["Routine work", "Planning", "Rest"]
            avoid = ["Big investments", "Arguments", "Impulsive decisions"]
        else:
            best_for = ["Follow-ups", "Documentation", "Small progress"]
            avoid = ["Risky commitments"]

        full_text = (
            f"Date: {d.isoformat()} | Score: {score} ({verdict})\n"
            f"Moon Star/Sub: {moon_star}/{moon_sub}\n"
            f"Dasha: {chain.get('maha')}-{chain.get('bhukti')}-{chain.get('antara')}-{chain.get('sukshma')}\n"
            f"Key Houses (from running lords + moon): {', '.join(map(str, key_houses)) if key_houses else '-'}"
        )

        return PredictionOut(
            dateISO=d.isoformat(),
            score=score,
            verdict=verdict,
            bestFor=best_for,
            avoid=avoid,
            areas=areas,
            moon={"star": moon_star, "sub": moon_sub, "note": "MVP uses natal Moon lon; plug today Moon later"},
            dasha=chain,
            birthKpData=birth_kp,   # ✅ client stores once; later you can omit for daily calls
            fullText=full_text,
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"personal_daily_prediction_failed: {e}")