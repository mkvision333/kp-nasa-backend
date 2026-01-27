# app/core/vimshottari_tree.py
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


def _add_days(dt: datetime, days: float) -> datetime:
    return dt + timedelta(seconds=float(days) * 86400.0)


def _days_of_years(years: float) -> float:
    return float(years) * 365.2425


def _next_lord(lord: str) -> str:
    i = ORDER.index(lord)
    return ORDER[(i + 1) % len(ORDER)]


def _make_node(level: str, lord: str, start: datetime, end: datetime) -> Dict:
    return {"level": level, "lord": lord, "start": _iso(start), "end": _iso(end)}


def _attach_children(node: Dict, key: str, children: List[Dict]) -> Dict:
    if children:
        node[key] = children
    return node


# ------------------------------------------------------------
# ✅ NEW: FAST LAZY BUILD HELPERS (AstroSage-style)
# ------------------------------------------------------------
def _parse_iso_utc(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)


def build_level_list(level: str, start_utc: datetime, end_utc: datetime, start_lord: str) -> List[Dict]:
    """
    ✅ Builds ONLY ONE LEVEL (9 items) within [start_utc, end_utc]
    NOTE: This helper is for "within a given window" rendering.
    It divides ONLY the given window length (parent_days) by 120 ratios.
    """
    if start_lord not in ORDER:
        raise ValueError(f"Invalid lord: {start_lord}")

    if start_utc.tzinfo is None:
        start_utc = start_utc.replace(tzinfo=timezone.utc)
    if end_utc.tzinfo is None:
        end_utc = end_utc.replace(tzinfo=timezone.utc)

    if end_utc <= start_utc:
        return []

    parent_days = (end_utc - start_utc).total_seconds() / 86400.0

    out: List[Dict] = []
    cur_start = start_utc
    lord = start_lord

    for idx in range(len(ORDER)):
        yrs = float(DASHA_YEARS[lord])
        sub_days = parent_days * (yrs / 120.0)
        cur_end = _add_days(cur_start, sub_days)

        if idx == len(ORDER) - 1 or cur_end > end_utc:
            cur_end = end_utc

        out.append(_make_node(level, lord, cur_start, cur_end))

        cur_start = cur_end
        lord = _next_lord(lord)

        if cur_start >= end_utc:
            break

    return out


def build_mahadasha_list_120y_9items(start_utc: datetime, maha_lord: str, maha_balance_years: Optional[float] = None) -> List[Dict]:
    """
    ✅ FAST: returns ONLY 9 Mahadashas covering ~120 years
    First MD uses maha_balance_years (remaining), then full MDs in ORDER.
    NO children.
    """
    if maha_lord not in ORDER:
        raise ValueError(f"Invalid maha lord: {maha_lord}")

    if start_utc.tzinfo is None:
        start_utc = start_utc.replace(tzinfo=timezone.utc)

    first_total = float(DASHA_YEARS[maha_lord])
    if maha_balance_years is None:
        first_years = first_total
    else:
        first_years = float(maha_balance_years)
        if first_years < 0:
            first_years = 0.0
        if first_years > first_total:
            first_years = first_total

    out: List[Dict] = []
    cur_start = start_utc

    first_days = _days_of_years(first_years)
    first_end = _add_days(cur_start, first_days)
    out.append(_make_node("mahadasha", maha_lord, cur_start, first_end))
    cur_start = first_end

    lord = _next_lord(maha_lord)
    for _ in range(8):
        yrs = float(DASHA_YEARS[lord])
        days = _days_of_years(yrs)
        end = _add_days(cur_start, days)
        out.append(_make_node("mahadasha", lord, cur_start, end))
        cur_start = end
        lord = _next_lord(lord)

    return out


# ------------------------------------------------------------
# ✅ CORE FIX: CLIP CHILD PERIODS BASED ON FULL PARENT, NOT "REMAINING"
# ------------------------------------------------------------
def _ensure_utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def _intersect(a0: datetime, a1: datetime, b0: datetime, b1: datetime) -> Optional[Tuple[datetime, datetime]]:
    if a1 <= a0 or b1 <= b0:
        return None
    s = a0 if a0 >= b0 else b0
    e = a1 if a1 <= b1 else b1
    if e <= s:
        return None
    return (s, e)


def _build_clipped_level(
    level: str,
    parent_lord: str,
    parent_full_start: datetime,
    parent_full_days: float,
    clip_start: datetime,
    clip_end: datetime,
    max_levels: int,
) -> List[Dict]:
    """
    Build one level (9 lords in ORDER starting at parent_lord) based on FULL parent duration,
    then CLIP to [clip_start, clip_end]. For every clipped segment, optionally build children recursively.
    """
    if parent_lord not in ORDER:
        raise ValueError(f"Invalid lord: {parent_lord}")

    parent_full_start = _ensure_utc(parent_full_start)
    clip_start = _ensure_utc(clip_start)
    clip_end = _ensure_utc(clip_end)

    if clip_end <= clip_start:
        return []

    parent_full_end = _add_days(parent_full_start, parent_full_days)

    # Clamp clip window to parent full window
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

        # Make the last segment end exactly at full_end to avoid drift
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
                    child_full_days = (seg_full_end - cur_full_start).total_seconds() / 86400.0  # full, not clipped
                    children = _build_clipped_level(
                        level=next_level,
                        parent_lord=lord,  # sequence starts from THIS segment lord (classic)
                        parent_full_start=child_full_start,
                        parent_full_days=child_full_days,
                        clip_start=seg_start,  # clip to current remaining window within this segment
                        clip_end=seg_end,
                        max_levels=max_levels - 1,
                    )
                    _attach_children(node, child_key, children)

            out.append(node)

        cur_full_start = seg_full_end
        lord = _next_lord(lord)

        if cur_full_start >= parent_full_end:
            break
        if cur_full_start >= win_end:
            break

    return out


# ------------------------------------------------------------
# ✅ EXISTING FUNCTIONS (fixed internals, same signatures)
# ------------------------------------------------------------
def build_vimshottari_tree(
    start_utc: datetime,
    maha_lord: str,
    maha_balance_years: Optional[float] = None,
    max_levels: int = 5,
) -> List[Dict]:
    """
    Builds ONE Mahadasha tree with keys:
    mahadasha -> bhukti -> antara -> sukshma -> prana

    ✅ FIX:
    If maha_balance_years is given (remaining), we DO NOT restart bhukti from maha_lord.
    We build full MD (planet total years), compute elapsed = total - remaining,
    then clip bhukti/antara/sukshma/prana to the remaining window.
    """
    if maha_lord not in ORDER:
        raise ValueError(f"Invalid maha lord: {maha_lord}")

    start_utc = _ensure_utc(start_utc)

    maha_total_years = float(DASHA_YEARS[maha_lord])
    if maha_balance_years is None:
        maha_remaining_years = maha_total_years
    else:
        maha_remaining_years = float(maha_balance_years)
        if maha_remaining_years < 0:
            maha_remaining_years = 0.0
        if maha_remaining_years > maha_total_years:
            maha_remaining_years = maha_total_years

    full_days = _days_of_years(maha_total_years)
    rem_days = _days_of_years(maha_remaining_years)
    elapsed_days = max(0.0, full_days - rem_days)

    # We are given "current time" = start_utc (somewhere inside the MD)
    full_start = _add_days(start_utc, -elapsed_days)
    full_end = _add_days(full_start, full_days)

    maha_start = start_utc
    maha_end = _add_days(maha_start, rem_days)

    # Node is ONLY the remaining window (like you want in UI)
    maha_node = _make_node("mahadasha", maha_lord, maha_start, maha_end)

    if max_levels <= 1 or maha_end <= maha_start:
        return [maha_node]

    # Build bhukti based on FULL MD schedule, then clip to [maha_start, maha_end]
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


def build_vimshottari_timeline_120y(
    start_utc: datetime,
    maha_lord: str,
    maha_balance_years: Optional[float] = None,
    max_levels: int = 5,
) -> List[Dict]:
    """
    Returns LIST of Mahadasha nodes covering EXACT ~120 years from start_utc.
    First MD uses maha_balance_years (remaining), then continues full MDs in ORDER.
    Each MD includes bhukti->antara->sukshma->prana upto max_levels.

    ✅ With the new build_vimshottari_tree(), the first MD correctly clips bhuktis/antaras/etc.
    """
    if maha_lord not in ORDER:
        raise ValueError(f"Invalid maha lord: {maha_lord}")

    start_utc = _ensure_utc(start_utc)

    TOTAL_YEARS = 120.0

    first_total = float(DASHA_YEARS[maha_lord])
    if maha_balance_years is None:
        first_years = first_total
    else:
        first_years = float(maha_balance_years)
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
        if isinstance(end_iso, str) and end_iso:
            cur_start = _parse_iso_utc(end_iso)
        else:
            cur_start = _add_days(cur_start, _days_of_years(md_years_remaining))

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
    """
    ✅ BACKWARD-COMPAT wrapper name.
    Returns LIST of Mahadasha nodes covering EXACT 120 years from start_utc.
    """
    return build_vimshottari_timeline_120y(
        start_utc=start_utc,
        maha_lord=maha_lord,
        maha_balance_years=maha_balance_years,
        max_levels=max_levels,
    )
