# app/core/vimshottari_tree.py ✅ FULL REPLACE
# Guarantees exports:
# - DASHA_YEARS
# - build_mahadasha_list_120y_9items
# - build_vimshottari_tree
# - get_child_full_window
# - build_level_list_clipped
#
# ✅ IMPORTANT:
# - NO "NOW" clipping here.
# - Everything is computed relative to given clip_start..clip_end only.
# - This enables users to see past + future dashas for any chart datetime they input.

from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

DASHA_ORDER = ["Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury"]
DASHA_YEARS = {"Ketu":7.0,"Venus":20.0,"Sun":6.0,"Moon":10.0,"Mars":7.0,"Rahu":18.0,"Jupiter":16.0,"Saturn":19.0,"Mercury":17.0}
DAYS_PER_YEAR = 365.2425

def _dt_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def _cycle_from(lord: str) -> List[str]:
    lord = str(lord or "").strip()
    if lord not in DASHA_ORDER:
        return DASHA_ORDER[:]
    i = DASHA_ORDER.index(lord)
    return DASHA_ORDER[i:] + DASHA_ORDER[:i]

def _add_days(dt: datetime, days: float) -> datetime:
    return _dt_utc(dt) + timedelta(days=float(days))

def _days(years: float) -> float:
    return float(years) * DAYS_PER_YEAR

def _mk_item(lord: str, start: datetime, end: datetime) -> Dict[str, Any]:
    s = _dt_utc(start).isoformat().replace("+00:00", "Z")
    e = _dt_utc(end).isoformat().replace("+00:00", "Z")
    return {"lord": str(lord), "start": s, "end": e}

def _iso_to_dt_utc(iso: str) -> datetime:
    return datetime.fromisoformat(str(iso).replace("Z", "+00:00")).astimezone(timezone.utc)

def build_mahadasha_list_120y_9items(start_utc: datetime, maha_lord: str, maha_balance_years: float) -> List[Dict[str, Any]]:
    """
    Returns 9 MD items: (current MD balance) + next 8 MDs full lengths.
    ✅ No NOW clipping. This is purely based on input start_utc (chart datetime).
    """
    start_utc = _dt_utc(start_utc)
    maha_lord = str(maha_lord or "").strip()
    if maha_lord not in DASHA_ORDER:
        maha_lord = DASHA_ORDER[0]

    seq = _cycle_from(maha_lord)
    out: List[Dict[str, Any]] = []

    t = start_utc
    bal = max(0.0, float(maha_balance_years))
    first_end = _add_days(t, _days(bal))
    out.append(_mk_item(seq[0], t, first_end))
    t = first_end

    for L in seq[1:]:
        yrs = float(DASHA_YEARS[L])
        te = _add_days(t, _days(yrs))
        out.append(_mk_item(L, t, te))
        t = te

    return out

def _build_children(parent_lord: str, parent_start: datetime, parent_end: datetime) -> List[Dict[str, Any]]:
    """
    Build full 9-part child schedule for a given parent window (start..end).
    Child order starts from parent_lord and runs through 9 lords.
    """
    parent_lord = str(parent_lord or "").strip()
    if parent_lord not in DASHA_ORDER:
        parent_lord = DASHA_ORDER[0]

    parent_start = _dt_utc(parent_start)
    parent_end = _dt_utc(parent_end)

    total_days = (parent_end - parent_start).total_seconds() / 86400.0
    if total_days <= 0:
        return []

    seq = _cycle_from(parent_lord)
    out: List[Dict[str, Any]] = []
    t = parent_start

    for L in seq:
        seg_days = total_days * (float(DASHA_YEARS[L]) / 120.0)
        te = _add_days(t, seg_days)
        out.append(_mk_item(L, t, te))
        t = te

    if out:
        out[-1]["end"] = parent_end.isoformat().replace("+00:00", "Z")
    return out

def build_vimshottari_tree(start_utc: datetime, maha_lord: str, maha_balance_years: float, max_levels: int = 4) -> List[Dict[str, Any]]:
    """
    Returns list with ONE root MD node, but includes chained children based on max_levels.
    ✅ No NOW clipping here.
    """
    start_utc = _dt_utc(start_utc)
    maha_lord = str(maha_lord or "").strip()
    if maha_lord not in DASHA_ORDER:
        maha_lord = DASHA_ORDER[0]

    bal = max(0.0, float(maha_balance_years))
    md_end = _add_days(start_utc, _days(bal))
    root = _mk_item(maha_lord, start_utc, md_end)

    if max_levels <= 1:
        return [root]

    bh_list = _build_children(maha_lord, start_utc, md_end)
    if max_levels <= 2:
        root["bhukti"] = bh_list
        return [root]

    for bh in bh_list:
        b_s = _iso_to_dt_utc(bh["start"])
        b_e = _iso_to_dt_utc(bh["end"])
        bh["antara"] = _build_children(bh["lord"], b_s, b_e)

        if max_levels >= 4:
            for an in bh["antara"]:
                a_s = _iso_to_dt_utc(an["start"])
                a_e = _iso_to_dt_utc(an["end"])
                an["sukshma"] = _build_children(an["lord"], a_s, a_e)

                if max_levels >= 5:
                    for su in an["sukshma"]:
                        s_s = _iso_to_dt_utc(su["start"])
                        s_e = _iso_to_dt_utc(su["end"])
                        su["prana"] = _build_children(su["lord"], s_s, s_e)

    root["bhukti"] = bh_list
    return [root]

def get_child_full_window(
    parent_lord: str,
    parent_full_start: datetime,
    parent_full_end: datetime,
    child_lord: str,
    clip_start: datetime,
    clip_end: datetime
) -> Optional[Tuple[datetime, datetime]]:
    """
    Build FULL child schedule for (parent_full_start..parent_full_end) and find child_lord segment
    that overlaps clip range; return (child_segment_full_start, child_segment_full_end).
    """
    parent_full_start = _dt_utc(parent_full_start)
    parent_full_end = _dt_utc(parent_full_end)
    clip_start = _dt_utc(clip_start)
    clip_end = _dt_utc(clip_end)

    lst = _build_children(str(parent_lord), parent_full_start, parent_full_end)
    want = str(child_lord or "").strip()

    for it in lst:
        if str(it.get("lord","")).strip() != want:
            continue
        s = _iso_to_dt_utc(it["start"])
        e = _iso_to_dt_utc(it["end"])
        if e <= clip_start or s >= clip_end:
            continue
        return (s, e)

    return None

def build_level_list_clipped(
    level: str,
    parent_lord: str,
    parent_full_start: datetime,
    parent_full_end: datetime,
    clip_start: datetime,
    clip_end: datetime
) -> List[Dict[str, Any]]:
    """
    Build FULL children under parent_full window, then clip output to clip_start..clip_end.
    ✅ No NOW clipping. This allows showing past+future segments for the user-selected chart datetime.
    """
    parent_full_start = _dt_utc(parent_full_start)
    parent_full_end = _dt_utc(parent_full_end)
    clip_start = _dt_utc(clip_start)
    clip_end = _dt_utc(clip_end)

    if clip_end <= clip_start:
        return []

    full = _build_children(str(parent_lord), parent_full_start, parent_full_end)
    out: List[Dict[str, Any]] = []

    for it in full:
        s = _iso_to_dt_utc(it["start"])
        e = _iso_to_dt_utc(it["end"])
        if e <= clip_start or s >= clip_end:
            continue
        ss = max(s, clip_start)
        ee = min(e, clip_end)
        out.append(_mk_item(it["lord"], ss, ee))

    return out
