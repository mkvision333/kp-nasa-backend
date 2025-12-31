# app/core/kp_calc.py
"""
KP astrology helpers
- Nirayana longitude assumed (0–360)
- Returns Star Lord, Sub Lord, Sub-Sub Lord
"""

# 27 Nakshatras (each 13°20')
NAKSHATRA_LORDS = [
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu",
    "Jupiter", "Saturn", "Mercury",
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu",
    "Jupiter", "Saturn", "Mercury",
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu",
    "Jupiter", "Saturn", "Mercury",
]

# Vimshottari Dasha order + years
DASHA_ORDER = [
    ("Ketu", 7),
    ("Venus", 20),
    ("Sun", 6),
    ("Moon", 10),
    ("Mars", 7),
    ("Rahu", 18),
    ("Jupiter", 16),
    ("Saturn", 19),
    ("Mercury", 17),
]

TOTAL_YEARS = 120.0


def _norm360(x: float) -> float:
    x = x % 360.0
    return x if x >= 0 else x + 360.0


def kp_star_sub(lon: float):
    """
    Input: nirayana longitude 0–360
    Output: (starLord, subLord)
    """
    lon = _norm360(lon)

    # ---------- STAR ----------
    star_size = 360.0 / 27.0  # 13°20'
    star_index = int(lon // star_size)
    star_lord = NAKSHATRA_LORDS[star_index]

    # position inside star
    pos_in_star = lon - (star_index * star_size)

    # ---------- SUB ----------
    # KP sub divisions proportional to Vimshottari years
    sub_span_total = star_size
    acc = 0.0
    for lord, years in DASHA_ORDER:
        span = sub_span_total * (years / TOTAL_YEARS)
        if pos_in_star <= acc + span:
            return star_lord, lord
        acc += span

    # fallback
    return star_lord, DASHA_ORDER[-1][0]


def kp_star_sub_sub(lon: float):
    """
    Returns (star, sub, subSub)
    """
    star, sub = kp_star_sub(lon)

    # ---------- SUB-SUB ----------
    lon = _norm360(lon)
    star_size = 360.0 / 27.0
    star_index = int(lon // star_size)
    pos_in_star = lon - (star_index * star_size)

    # find sub span again
    sub_span_total = star_size
    acc = 0.0
    for lord, years in DASHA_ORDER:
        span = sub_span_total * (years / TOTAL_YEARS)
        if pos_in_star <= acc + span:
            pos_in_sub = pos_in_star - acc
            sub_span = span
            break
        acc += span
    else:
        pos_in_sub = 0
        sub_span = star_size

    # divide sub into sub-subs again by Vimshottari
    acc2 = 0.0
    for lord2, years2 in DASHA_ORDER:
        span2 = sub_span * (years2 / TOTAL_YEARS)
        if pos_in_sub <= acc2 + span2:
            return star, sub, lord2
        acc2 += span2

    return star, sub, DASHA_ORDER[-1][0]
