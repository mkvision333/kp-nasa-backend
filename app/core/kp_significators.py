# app/core/kp_significators.py ✅ NEW
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import math

# ---------------------------
# Types (close to your TS)
# ---------------------------
@dataclass
class DMS:
    deg: int
    min: int
    sec: int

@dataclass
class BhavaCusp:
    bhava: int
    longitude: DMS

@dataclass
class KPGrahaRow:
    planet: str
    longitude: DMS
    retro: Optional[bool] = None
    starLord: Optional[str] = None
    subLord: Optional[str] = None
    subSubLord: Optional[str] = None

# ---------------------------
# Helpers
# ---------------------------
def norm360(v: float) -> float:
    x = v % 360.0
    return x if x >= 0 else x + 360.0

def dms_to_abs(x: DMS) -> float:
    return float(x.deg) + float(x.min)/60.0 + float(x.sec)/3600.0

def sign_index_1to12(abs_lon: float) -> int:
    return int(math.floor(norm360(abs_lon) / 30.0)) + 1

def uniq_nums(xs: List[int]) -> List[int]:
    return sorted(list({int(x) for x in xs if isinstance(x, (int, float))}))

def uniq_str(xs: List[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for x in xs:
        s = str(x or "").strip()
        if not s:
            continue
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out

def sign_lord(sign: int) -> str:
    # classical sign lords (no Rahu/Ketu ownership here)
    if sign == 1:  return "Mars"
    if sign == 2:  return "Venus"
    if sign == 3:  return "Mercury"
    if sign == 4:  return "Moon"
    if sign == 5:  return "Sun"
    if sign == 6:  return "Mercury"
    if sign == 7:  return "Venus"
    if sign == 8:  return "Mars"
    if sign == 9:  return "Jupiter"
    if sign == 10: return "Saturn"
    if sign == 11: return "Saturn"
    if sign == 12: return "Jupiter"
    return ""

def in_arc(lon: float, start: float, end: float) -> bool:
    L = norm360(lon); S = norm360(start); E = norm360(end)
    if S <= E:
        return (L >= S) and (L < E)
    return (L >= S) or (L < E)

def house_of_longitude(abs_lon: float, cusps: List[BhavaCusp]) -> int:
    c = sorted(cusps, key=lambda x: x.bhava)
    arr = [{"bhava": x.bhava, "abs": norm360(dms_to_abs(x.longitude))} for x in c]
    for i in range(12):
        cur = arr[i]
        nxt = arr[(i + 1) % 12]
        if in_arc(abs_lon, cur["abs"], nxt["abs"]):
            return int(cur["bhava"])
    return 1

def is_chaya(p: str) -> bool:
    p = str(p or "").strip()
    return p in ("Rahu", "Ketu")

def ang_diff_deg(a: float, b: float) -> float:
    x = abs(norm360(a) - norm360(b))
    return min(x, 360.0 - x)

def aspect_offsets(p: str) -> List[int]:
    p = str(p or "").strip()
    if p == "Mars": return [4, 7, 8]
    if p == "Jupiter": return [5, 7, 9]
    if p == "Saturn": return [3, 7, 10]
    if is_chaya(p): return [7]
    return [7]  # Sun, Moon, Mercury, Venus

def aspects_houses_of_planet(p: str, occ_house: Dict[str, int]) -> List[int]:
    h = occ_house.get(p)
    if not h:
        return []
    return uniq_nums([((h + off - 1) % 12) + 1 for off in aspect_offsets(p)])

# ---------------------------
# Main: build KP significators (ABCD only)
# ---------------------------
def build_kp_significators_advanced(
    graha_table: List[Dict[str, Any]],
    bhava_cusps: List[Dict[str, Any]],
    *,
    chaya_orb_deg: float = 15.0,
    enable_explain: bool = False,
) -> Dict[str, Any]:
    """
    Input payloads can be dict-style from API (not dataclasses),
    matching your frontend shapes:
      graha_table: [{planet, longitude:{deg,min,sec}, starLord, subLord, ...}]
      bhava_cusps: [{bhava, longitude:{deg,min,sec}}]
    Output:
      { planetSigs: [...], houseSigs: [...], explain: {byPlanet, byBhava} }
    """
    # normalize cusps
    cusps: List[BhavaCusp] = []
    for c in (bhava_cusps or []):
        lon = c.get("longitude") or {}
        cusps.append(BhavaCusp(
            bhava=int(c.get("bhava") or 1),
            longitude=DMS(int(lon.get("deg") or 0), int(lon.get("min") or 0), int(lon.get("sec") or 0)),
        ))

    # normalize grahas
    grahas: List[KPGrahaRow] = []
    for g in (graha_table or []):
        lon = g.get("longitude") or {}
        grahas.append(KPGrahaRow(
            planet=str(g.get("planet") or "").strip(),
            longitude=DMS(int(lon.get("deg") or 0), int(lon.get("min") or 0), int(lon.get("sec") or 0)),
            retro=bool(g.get("retro")) if g.get("retro") is not None else None,
            starLord=str(g.get("starLord") or "").strip() or None,
            subLord=str(g.get("subLord") or "").strip() or None,
            subSubLord=str(g.get("subSubLord") or "").strip() or None,
        ))

    explain = {"byPlanet": {}, "byBhava": {}}

    def addP(p: str, line: str):
        if not enable_explain:
            return
        explain["byPlanet"].setdefault(p, [])
        explain["byPlanet"][p].append(line)

    # 1) owned houses from cusps (classic)
    owned_by: Dict[str, List[int]] = {}
    for c in cusps:
        cusp_abs = norm360(dms_to_abs(c.longitude))
        s = sign_index_1to12(cusp_abs)
        lord = sign_lord(s)
        if not lord:
            continue
        owned_by.setdefault(lord, [])
        owned_by[lord].append(int(c.bhava))
    for k in list(owned_by.keys()):
        owned_by[k] = uniq_nums(owned_by[k])

    def get_owns_classic(p: str) -> List[int]:
        return list(owned_by.get(p, []))

    # 2) abs, sign, house, star/sub
    abs_by: Dict[str, float] = {}
    sign_of: Dict[str, int] = {}
    occ_house: Dict[str, int] = {}
    star_of: Dict[str, str] = {}
    sub_of: Dict[str, str] = {}

    for g in grahas:
        if not g.planet:
            continue
        abs_lon = norm360(dms_to_abs(g.longitude))
        abs_by[g.planet] = abs_lon
        sign_of[g.planet] = sign_index_1to12(abs_lon)
        occ_house[g.planet] = house_of_longitude(abs_lon, cusps)
        star_of[g.planet] = (g.starLord or "").strip()
        sub_of[g.planet] = (g.subLord or "").strip()

    def get_owns_effective(p: str) -> List[int]:
        p = str(p or "").strip()
        if not is_chaya(p):
            return get_owns_classic(p)
        s = sign_of.get(p, 1)
        sl = sign_lord(s)
        return get_owns_classic(sl) if sl else []

    def conjuncts_within_orb(p: str) -> List[str]:
        a = abs_by.get(p)
        if a is None:
            return []
        res: List[str] = []
        for g in grahas:
            if g.planet == p:
                continue
            b = abs_by.get(g.planet)
            if b is None:
                continue
            if ang_diff_deg(a, b) <= float(chaya_orb_deg):
                res.append(g.planet)
        return sorted(uniq_str(res))

    def aspectors_of_planet(p: str) -> List[str]:
        p_house = occ_house.get(p)
        if not p_house:
            return []
        aspectors: List[str] = []
        for q in grahas:
            if q.planet == p:
                continue
            q_asps = aspects_houses_of_planet(q.planet, occ_house)
            if p_house in q_asps:
                aspectors.append(q.planet)
        return sorted(uniq_str(aspectors))

    # 3) ABCD only significators per planet
    abcd_sig: Dict[str, List[int]] = {}

    for g in grahas:
        p = g.planet
        if not p:
            continue
        star = star_of.get(p, "")

        A = [occ_house[star]] if (star and occ_house.get(star)) else []
        B = [occ_house[p]] if occ_house.get(p) else []
        C = get_owns_effective(star) if star else []
        D = get_owns_effective(p)

        abcd_sig[p] = uniq_nums(A + B + C + D)

        addP(p, f"Planet {p} -> OccHouse {occ_house.get(p,'-')}, Sign {sign_of.get(p,'-')}, StarLord {star or '-'}, SubLord {sub_of.get(p,'-')}")
        addP(p, f"Grade A Strongest: {p} in {star or '-'} star -> {star or '-'} occupies -> {','.join(map(str,A)) if A else '-'}")
        addP(p, f"Grade B Strong: {p} occupies -> {','.join(map(str,B)) if B else '-'}")
        addP(p, f"Grade C Weak: StarLord {star or '-'} owns -> {','.join(map(str,C)) if C else '-'}")
        addP(p, f"Grade D Weakest: {p}{' as SignLord' if is_chaya(p) else ''} owns -> {','.join(map(str,D)) if D else '-'}")
        addP(p, f"ABCD Houses display only -> {','.join(map(str,abcd_sig[p])) if abcd_sig[p] else '-'}")

    # 4) Grade E (display-only explain)
    for g in grahas:
        p = g.planet
        if not p or p not in abcd_sig:
            continue
        conj = conjuncts_within_orb(p)
        asp = aspectors_of_planet(p)

        conjH = uniq_nums([h for cp in conj for h in (abcd_sig.get(cp, []) or [])])
        aspH = uniq_nums([h for ap in asp for h in (abcd_sig.get(ap, []) or [])])
        E = uniq_nums(conjH + aspH)
        E = [h for h in E if h not in (abcd_sig.get(p, []) or [])]

        addP(p, f"Grade E More Weak: Conj({', '.join(conj) if conj else '-'}) + Aspect({', '.join(asp) if asp else '-'}) -> EXTRA houses -> {','.join(map(str,E)) if E else '-'}")

    # 5) PlanetSig array
    planet_sigs: List[Dict[str, Any]] = []
    for g in grahas:
        p = g.planet
        if not p:
            continue
        planet_sigs.append({
            "planet": p,
            "sign": sign_of.get(p, 1),
            "houseOccupied": occ_house.get(p, 1),
            "owns": get_owns_effective(p),
            "starHouses": [],  # kept for compatibility
            "significators": abcd_sig.get(p, []),  # ABCD only
            "starLord": star_of.get(p, "") or None,
            "subLord": sub_of.get(p, "") or None,
        })

    # 6) Bhava -> Planets mapping (ABCD only)
    house_map: Dict[int, List[str]] = {i: [] for i in range(1, 13)}
    for ps in planet_sigs:
        for h in (ps.get("significators") or []):
            if 1 <= int(h) <= 12:
                house_map[int(h)].append(ps["planet"])

    house_sigs: List[Dict[str, Any]] = []
    for bhava in range(1, 13):
        house_sigs.append({"bhava": bhava, "planets": sorted(uniq_str(house_map[bhava]))})

    if enable_explain:
        for k in list(explain["byPlanet"].keys()):
            explain["byPlanet"][k] = uniq_str(explain["byPlanet"][k])

    return {"planetSigs": planet_sigs, "houseSigs": house_sigs, "explain": explain}