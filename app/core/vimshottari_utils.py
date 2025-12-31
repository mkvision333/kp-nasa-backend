from typing import Tuple

# Vimshottari order
ORDER = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]

DASHA_YEARS = {
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

NAKSHATRA_SPAN = 13 + 20 / 60  # 13°20′ = 13.333333...


def moon_vimshottari_info(moon_lon_sid: float) -> Tuple[str, float]:
    """
    Input: Moon nirayana longitude (0–360)
    Output:
      maha_lord (str),
      balance_years (float)
    """
    lon = moon_lon_sid % 360.0

    nak_index = int(lon // NAKSHATRA_SPAN)  # 0..26
    nak_offset = lon % NAKSHATRA_SPAN       # degrees inside nakshatra

    lord = ORDER[nak_index % 9]
    total_years = DASHA_YEARS[lord]

    elapsed_ratio = nak_offset / NAKSHATRA_SPAN
    balance_years = total_years * (1.0 - elapsed_ratio)

    return lord, balance_years
