# app/core/vimshottari_tree.py  ✅ FULL REPLACE
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

DASHA_YEARS: Dict[str, float] = {
    "Ketu": 7,
    "Venus": 20,
    "Sun": 6,
    "Moon": 10,
    "Mars": 7,
    "Rahu": 18,
    "Jupiter": 16,
    "Saturn": 19,
    "Mercury": 17,
}

ORDER: List[str] = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]

LEVEL_CHILD_KEY = {
    "mahadasha": "bhukti",
    "bhukti": "antara",
    "antara": "sukshma",
    "sukshma": "prana",
}

LEVEL_NEXT = {
    "mahadasha": "bhukti",
    "bhukti": "antara",
    "antara": "sukshma",
    "sukshma": "prana",
    "prana": None,
}


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_iso_utc(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)


def _add_days(dt: datetime, days: float) -> datetime:
    return dt + timedelta(seconds=float(days) * 86400.0)


def _days_of_years(years: float) -> float:
    return float(years) * 365.2425


def _ensure_utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def _next_lord(lord: str) -> str:
    i = ORDER.index(lord)
    return ORDER[(i + 1) % len(ORDER)]


def _make_node(level: str, lord: str, start: datetime, end: datetime) -> Dict:
    return {"level": level, "lord": lord, "start": _iso(start), "end": _iso(end)}


def _attach_children(node: Dict, key: str, children: List[Dict]) -> Dict:
    if children:
        node[key] = children
    return node


def _intersect(a0: datetime, a1: datetime, b0: datetime, b1: datetime) -> Optional[Tuple[datetime, datetime]]:
    if a1 <= a0 or b1 <= b0:
        return None
    s = a0 if a0 >= b0 else b0
    e = a1 if a1 <= b1 else b1
    if e <= s:
        return None
    return (s, e)


# ------------------------------------------------------------
# ✅ 1) Build ONE LEVEL schedule on FULL parent duration (120-ratio),
#    then CLIP to [clip_start, clip_end]
# ------------------------------------------------------------
def build_level_list_clipped(
    level: str,
    parent_lord: str,
    parent_full_start: datetime,
    parent_full_end: datetime,
    clip_start: datetime,
    clip_end: datetime,
) -> List[Dict]:
    """
    ✅ ELAPSED-AWARE:
    We build child sub-periods using FULL parent duration (parent_full_start -> parent_full_end),
    then clip to [clip_start, clip_end].
    This automatically drops already-passed children when clip_start is mid-way.
    """
    if parent_lord not in ORDER:
        raise ValueError(f"Invalid lord: {parent_lord}")

    parent_full_start = _ensure_utc(parent_full_start)
    parent_full_end = _ensure_utc(parent_full_end)
    clip_start = _ensure_utc(clip_start)
    clip_end = _ensure_utc(clip_end)

    if parent_full_end <= parent_full_start or clip_end <= clip_start:
        return []

    win = _intersect(clip_start, clip_end, parent_full_start, parent_full_end)
    if not win:
        return []
    win_start, win_end = win

    parent_full_days = (parent_full_end - parent_full_start).total_seconds() / 86400.0
    out: List[Dict] = []

    cur_full_start = parent_full_start
    lord = parent_lord

    for idx in range(len(ORDER)):
        yrs = float(DASHA_YEARS[lord])
        seg_full_days = parent_full_days * (yrs / 120.0)
        seg_full_end = _add_days(cur_full_start, seg_full_days)

        if idx == len(ORDER) - 1 or seg_full_end > parent_full_end:
            seg_full_end = parent_full_end

        seg_clip = _intersect(cur_full_start, seg_full_end, win_start, win_end)
        if seg_clip:
            s, e = seg_clip
            out.append(_make_node(level, lord, s, e))

        cur_full_start = seg_full_end
        lord = _next_lord(lord)

        if cur_full_start >= parent_full_end or cur_full_start >= win_end:
            break

    return out


# ------------------------------------------------------------
# ✅ 2) Given parent's FULL window, find a child's FULL window (start,end)
#    even if node.start is mid-way inside that child segment.
# ------------------------------------------------------------
def get_child_full_window(
    parent_lord: str,
    parent_full_start: datetime,
    parent_full_end: datetime,
    child_lord: str,
    child_clip_start: datetime,
    child_clip_end: datetime,
) -> Optional[Tuple[datetime, datetime]]:
    """
    Finds the FULL segment window of child_lord inside the parent's FULL schedule,
    but matches only the segment that intersects the child's clip window.
    """
    if parent_lord not in ORDER or child_lord not in ORDER:
        return None

    parent_full_start = _ensure_utc(parent_full_start)
    parent_full_end = _ensure_utc(parent_full_end)
    child_clip_start = _ensure_utc(child_clip_start)
    child_clip_end = _ensure_utc(child_clip_end)

    if parent_full_end <= parent_full_start or child_clip_end <= child_clip_start:
        return None

    parent_full_days = (parent_full_end - parent_full_start).total_seconds() / 86400.0
    cur_full_start = parent_full_start
    lord = parent_lord

    for idx in range(len(ORDER)):
        yrs = float(DASHA_YEARS[lord])
        seg_full_days = parent_full_days * (yrs / 120.0)
        seg_full_end = _add_days(cur_full_start, seg_full_days)
        if idx == len(ORDER) - 1 or seg_full_end > parent_full_end:
            seg_full_end = parent_full_end

        if lord == child_lord:
            # Must intersect with child's clip window, else it's the "other" same-lord segment (rare but safe)
            if _intersect(cur_full_start, seg_full_end, child_clip_start, child_clip_end):
                return (cur_full_start, seg_full_end)

        cur_full_start = seg_full_end
        lord = _next_lord(lord)

        if cur_full_start >= parent_full_end:
            break

    return None


# ------------------------------------------------------------
# ✅ 3) FAST Mahadasha list (same as you already had)
# ------------------------------------------------------------
def build_mahadasha_list_120y_9items(
    start_utc: datetime,
    maha_lord: str,
    maha_balance_years: Optional[float] = None,
) -> List[Dict]:
    if maha_lord not in ORDER:
        raise ValueError(f"Invalid maha lord: {maha_lord}")

    start_utc = _ensure_utc(start_utc)

    first_total = float(DASHA_YEARS[maha_lord])
    first_years = first_total if maha_balance_years is None else float(maha_balance_years)
    if first_years < 0:
        first_years = 0.0
    if first_years > first_total:
        first_years = first_total

    out: List[Dict] = []
    cur_start = start_utc

    first_end = _add_days(cur_start, _days_of_years(first_years))
    out.append(_make_node("mahadasha", maha_lord, cur_start, first_end))
    cur_start = first_end

    lord = _next_lord(maha_lord)
    for _ in range(8):
        yrs = float(DASHA_YEARS[lord])
        end = _add_days(cur_start, _days_of_years(yrs))
        out.append(_make_node("mahadasha", lord, cur_start, end))
        cur_start = end
        lord = _next_lord(lord)

    return out


# ------------------------------------------------------------
# ✅ 4) FULL tree builder for FIRST MD (remaining window) with recursion (already correct)
# ------------------------------------------------------------
def _build_clipped_level(
    level: str,
    parent_lord: str,
    parent_full_start: datetime,
    parent_full_days: float,
    clip_start: datetime,
    clip_end: datetime,
    max_levels: int,
) -> List[Dict]:
    if parent_lord not in ORDER:
        raise ValueError(f"Invalid lord: {parent_lord}")

    parent_full_start = _ensure_utc(parent_full_start)
    clip_start = _ensure_utc(clip_start)
    clip_end = _ensure_utc(clip_end)

    if clip_end <= clip_start:
        return []

    parent_full_end = _add_days(parent_full_start, parent_full_days)
    window = _intersect(clip_start, clip_end, parent_full_start, parent_full_end)
    if not window:
        return []
    win_start, win_end = window

    out: List[Dict] = []
    cur_full_start = parent_full_start
    lord = parent_lord

    for idx in range(len(ORDER)):
        yrs = float(DASHA_YEARS[lord])
        seg_full_days = parent_full_days * (yrs / 120.0)
        seg_full_end = _add_days(cur_full_start, seg_full_days)

        if idx == len(ORDER) - 1 or seg_full_end > parent_full_end:
            seg_full_end = parent_full_end

        seg_clip = _intersect(cur_full_start, seg_full_end, win_start, win_end)
        if seg_clip:
            seg_start, seg_end = seg_clip
            node = _make_node(level, lord, seg_start, seg_end)

            if max_levels > 1:
                next_level = LEVEL_NEXT.get(level)
                if next_level:
                    child_key = LEVEL_CHILD_KEY[level]
                    child_full_start = cur_full_start
                    child_full_days = (seg_full_end - cur_full_start).total_seconds() / 86400.0
                    children = _build_clipped_level(
                        level=next_level,
                        parent_lord=lord,
                        parent_full_start=child_full_start,
                        parent_full_days=child_full_days,
                        clip_start=seg_start,
                        clip_end=seg_end,
                        max_levels=max_levels - 1,
                    )
                    _attach_children(node, child_key, children)

            out.append(node)

        cur_full_start = seg_full_end
        lord = _next_lord(lord)

        if cur_full_start >= parent_full_end or cur_full_start >= win_end:
            break

    return out


def build_vimshottari_tree(
    start_utc: datetime,
    maha_lord: str,
    maha_balance_years: Optional[float] = None,
    max_levels: int = 5,
) -> List[Dict]:
    if maha_lord not in ORDER:
        raise ValueError(f"Invalid maha lord: {maha_lord}")

    start_utc = _ensure_utc(start_utc)

    maha_total_years = float(DASHA_YEARS[maha_lord])
    maha_remaining_years = maha_total_years if maha_balance_years is None else float(maha_balance_years)
    if maha_remaining_years < 0:
        maha_remaining_years = 0.0
    if maha_remaining_years > maha_total_years:
        maha_remaining_years = maha_total_years

    full_days = _days_of_years(maha_total_years)
    rem_days = _days_of_years(maha_remaining_years)
    elapsed_days = max(0.0, full_days - rem_days)

    full_start = _add_days(start_utc, -elapsed_days)
    maha_start = start_utc
    maha_end = _add_days(maha_start, rem_days)

    maha_node = _make_node("mahadasha", maha_lord, maha_start, maha_end)
    if max_levels <= 1 or maha_end <= maha_start:
        return [maha_node]

    bhukti_nodes = _build_clipped_level(
        level="bhukti",
        parent_lord=maha_lord,
        parent_full_start=full_start,
        parent_full_days=full_days,
        clip_start=maha_start,
        clip_end=maha_end,
        max_levels=max_levels - 1,
    )
    _attach_children(maha_node, "bhukti", bhukti_nodes)
    return [maha_node]


# ------------------------------------------------------------
# ✅ 5) NEW: Lazy-load style helpers that apply SAME elapsed logic upto prana
#    (Use these from main.py /api/dasha/bhukti|antara|sukshma|prana)
# ------------------------------------------------------------
def build_children_upto_prana_from_md(
    md_full_start: datetime,
    md_full_end: datetime,
    md_lord: str,
    clip_start: datetime,
    clip_end: datetime,
    max_levels: int = 4,
) -> List[Dict]:
    """
    Given one Mahadasha FULL window, return children lists from current time window (clip_start..clip_end)
    with elapsed-aware clipping all the way down (bhukti->antara->sukshma->prana) depending on max_levels.

    max_levels:
      1 => bhukti only
      2 => bhukti->antara
      3 => bhukti->antara->sukshma
      4 => bhukti->antara->sukshma->prana
    """
    md_full_start = _ensure_utc(md_full_start)
    md_full_end = _ensure_utc(md_full_end)
    clip_start = _ensure_utc(clip_start)
    clip_end = _ensure_utc(clip_end)

    if max_levels <= 0:
        return []

    # bhukti
    bh_list = build_level_list_clipped("bhukti", md_lord, md_full_start, md_full_end, clip_start, clip_end)
    if max_levels == 1:
        return bh_list

    # attach antara for each bhukti node
    for bh in bh_list:
        bh_lord = str(bh.get("lord") or "").strip()
        bh_s = _parse_iso_utc(str(bh.get("start")))
        bh_e = _parse_iso_utc(str(bh.get("end")))
        bh_full = get_child_full_window(md_lord, md_full_start, md_full_end, bh_lord, bh_s, bh_e)
        if not bh_full:
            continue
        bh_full_s, bh_full_e = bh_full

        an_list = build_level_list_clipped("antara", bh_lord, bh_full_s, bh_full_e, bh_s, bh_e)
        if an_list:
            bh["antara"] = an_list

        if max_levels == 2:
            continue

        # attach sukshma for each antara node
        for an in an_list:
            an_lord = str(an.get("lord") or "").strip()
            an_s = _parse_iso_utc(str(an.get("start")))
            an_e = _parse_iso_utc(str(an.get("end")))
            an_full = get_child_full_window(bh_lord, bh_full_s, bh_full_e, an_lord, an_s, an_e)
            if not an_full:
                continue
            an_full_s, an_full_e = an_full

            su_list = build_level_list_clipped("sukshma", an_lord, an_full_s, an_full_e, an_s, an_e)
            if su_list:
                an["sukshma"] = su_list

            if max_levels == 3:
                continue

            # attach prana for each sukshma node
            for su in su_list:
                su_lord = str(su.get("lord") or "").strip()
                su_s = _parse_iso_utc(str(su.get("start")))
                su_e = _parse_iso_utc(str(su.get("end")))
                su_full = get_child_full_window(an_lord, an_full_s, an_full_e, su_lord, su_s, su_e)
                if not su_full:
                    continue
                su_full_s, su_full_e = su_full

                pr_list = build_level_list_clipped("prana", su_lord, su_full_s, su_full_e, su_s, su_e)
                if pr_list:
                    su["prana"] = pr_list

    return bh_list


# ------------------------------------------------------------
# ✅ 6) 120y timeline wrapper (same)
# ------------------------------------------------------------
def build_vimshottari_timeline_120y(
    start_utc: datetime,
    maha_lord: str,
    maha_balance_years: Optional[float] = None,
    max_levels: int = 5,
) -> List[Dict]:
    if maha_lord not in ORDER:
        raise ValueError(f"Invalid maha lord: {maha_lord}")

    start_utc = _ensure_utc(start_utc)
    TOTAL_YEARS = 120.0

    first_total = float(DASHA_YEARS[maha_lord])
    first_years = first_total if maha_balance_years is None else float(maha_balance_years)
    if first_years < 0:
        first_years = 0.0
    if first_years > first_total:
        first_years = first_total

    out: List[Dict] = []
    cur_start = start_utc
    used_years = 0.0

    def _append_md(md_lord: str, md_years_remaining: float):
        nonlocal cur_start, used_years, out
        if md_years_remaining <= 0:
            return
        one = build_vimshottari_tree(
            start_utc=cur_start,
            maha_lord=md_lord,
            maha_balance_years=md_years_remaining,
            max_levels=max_levels,
        )
        md_node = one[0] if one else None
        if not md_node:
            return
        out.append(md_node)
        end_iso = md_node.get("end")
        cur_start = _parse_iso_utc(end_iso) if isinstance(end_iso, str) and end_iso else _add_days(cur_start, _days_of_years(md_years_remaining))
        used_years += md_years_remaining

    remaining = TOTAL_YEARS - used_years
    _append_md(maha_lord, min(first_years, remaining))

    next_lord = _next_lord(maha_lord)
    while used_years < TOTAL_YEARS - 1e-9:
        remaining = TOTAL_YEARS - used_years
        full_years = float(DASHA_YEARS[next_lord])
        _append_md(next_lord, min(full_years, remaining))
        next_lord = _next_lord(next_lord)

    return out


def build_vimshottari_full_120y_tree(
    start_utc: datetime,
    maha_lord: str,
    maha_balance_years: Optional[float] = None,
    max_levels: int = 5,
) -> List[Dict]:
    return build_vimshottari_timeline_120y(
        start_utc=start_utc,
        maha_lord=maha_lord,
        maha_balance_years=maha_balance_years,
        max_levels=max_levels,
    )
