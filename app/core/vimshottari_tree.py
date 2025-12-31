# app/core/vimshottari_tree.py
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

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
    # expects Z
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)


def build_level_list(
    level: str,
    start_utc: datetime,
    end_utc: datetime,
    start_lord: str,
) -> List[Dict]:
    """
    ✅ Builds ONLY ONE LEVEL (9 items) within [start_utc, end_utc]
    Formula: sub_days = parent_days * (lord_years / 120)
    Sequence starts from start_lord and follows ORDER.
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

        # force exact end on last item
        if idx == len(ORDER) - 1 or cur_end > end_utc:
            cur_end = end_utc

        out.append(_make_node(level, lord, cur_start, cur_end))

        cur_start = cur_end
        lord = _next_lord(lord)

        if cur_start >= end_utc:
            break

    return out


def build_mahadasha_list_120y_9items(
    start_utc: datetime,
    maha_lord: str,
    maha_balance_years: Optional[float] = None,
) -> List[Dict]:
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

    # 1) first remaining
    first_days = _days_of_years(first_years)
    first_end = _add_days(cur_start, first_days)
    out.append(_make_node("mahadasha", maha_lord, cur_start, first_end))
    cur_start = first_end

    # 2) remaining 8 full MDs
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
# ✅ EXISTING FUNCTIONS (UNCHANGED) - keep compatibility
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
    Returns: [maha_node]
    """
    if maha_lord not in ORDER:
        raise ValueError(f"Invalid maha lord: {maha_lord}")

    if start_utc.tzinfo is None:
        start_utc = start_utc.replace(tzinfo=timezone.utc)

    maha_total_years = float(DASHA_YEARS[maha_lord])
    if maha_balance_years is None:
        maha_years = maha_total_years
    else:
        maha_years = float(maha_balance_years)
        if maha_years < 0:
            maha_years = 0.0
        if maha_years > maha_total_years:
            maha_years = maha_total_years

    maha_days = _days_of_years(maha_years)

    maha_start = start_utc
    maha_end = _add_days(maha_start, maha_days)
    maha_node = _make_node("mahadasha", maha_lord, maha_start, maha_end)

    if max_levels <= 1:
        return [maha_node]

    bhukti_nodes: List[Dict] = []
    cur_start = maha_start
    ad_lord = maha_lord

    for idx in range(len(ORDER)):
        ad_years = DASHA_YEARS[ad_lord]
        ad_days = maha_days * (ad_years / 120.0)
        cur_end = _add_days(cur_start, ad_days)

        if idx == len(ORDER) - 1:
            cur_end = maha_end

        bh = _make_node("bhukti", ad_lord, cur_start, cur_end)

        if max_levels > 2:
            antara_nodes: List[Dict] = []
            cur2_start = cur_start
            pd_lord = ad_lord

            for jdx in range(len(ORDER)):
                pd_years = DASHA_YEARS[pd_lord]
                pd_days = ad_days * (pd_years / 120.0)
                cur2_end = _add_days(cur2_start, pd_days)

                if jdx == len(ORDER) - 1:
                    cur2_end = cur_end

                an = _make_node("antara", pd_lord, cur2_start, cur2_end)

                if max_levels > 3:
                    suk_nodes: List[Dict] = []
                    cur3_start = cur2_start
                    sd_lord = pd_lord

                    for kdx in range(len(ORDER)):
                        sd_years = DASHA_YEARS[sd_lord]
                        sd_days = pd_days * (sd_years / 120.0)
                        cur3_end = _add_days(cur3_start, sd_days)

                        if kdx == len(ORDER) - 1:
                            cur3_end = cur2_end

                        su = _make_node("sukshma", sd_lord, cur3_start, cur3_end)

                        if max_levels > 4:
                            pr_nodes: List[Dict] = []
                            cur4_start = cur3_start
                            pr_lord = sd_lord

                            for mdx in range(len(ORDER)):
                                pr_years = DASHA_YEARS[pr_lord]
                                pr_days = sd_days * (pr_years / 120.0)
                                cur4_end = _add_days(cur4_start, pr_days)

                                if mdx == len(ORDER) - 1:
                                    cur4_end = cur3_end

                                pr = _make_node("prana", pr_lord, cur4_start, cur4_end)
                                pr_nodes.append(pr)
                                cur4_start = cur4_end
                                pr_lord = _next_lord(pr_lord)

                            _attach_children(su, "prana", pr_nodes)

                        suk_nodes.append(su)
                        cur3_start = cur3_end
                        sd_lord = _next_lord(sd_lord)

                    _attach_children(an, "sukshma", suk_nodes)

                antara_nodes.append(an)
                cur2_start = cur2_end
                pd_lord = _next_lord(pd_lord)

            _attach_children(bh, "antara", antara_nodes)

        bhukti_nodes.append(bh)
        cur_start = cur_end
        ad_lord = _next_lord(ad_lord)

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
    """
    if maha_lord not in ORDER:
        raise ValueError(f"Invalid maha lord: {maha_lord}")

    if start_utc.tzinfo is None:
        start_utc = start_utc.replace(tzinfo=timezone.utc)

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

    def _append_md(md_lord: str, md_years: float):
        nonlocal cur_start, used_years, out
        if md_years <= 0:
            return
        one = build_vimshottari_tree(
            start_utc=cur_start,
            maha_lord=md_lord,
            maha_balance_years=md_years,
            max_levels=max_levels,
        )
        md_node = one[0] if one else None
        if not md_node:
            return

        out.append(md_node)

        end_iso = md_node.get("end")
        if isinstance(end_iso, str) and end_iso:
            cur_start = datetime.fromisoformat(end_iso.replace("Z", "+00:00")).astimezone(timezone.utc)
        else:
            cur_start = _add_days(cur_start, _days_of_years(md_years))

        used_years += md_years

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
