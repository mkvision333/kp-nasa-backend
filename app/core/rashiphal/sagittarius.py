# app/core/rashiphal/sagittarius.py
from __future__ import annotations
from typing import Dict
from .meta import TransitNote

def get_transits() -> Dict[str, TransitNote]:
    base = "Sagittarius native: "
    return {
        "Aries": TransitNote("Aries", 5, "Creativity", {"Effects": base + "Joy, creativity and romance improve."}),
        "Taurus": TransitNote("Taurus", 6, "Work", {"Effects": base + "Discipline helps; avoid overwork."}),
        "Gemini": TransitNote("Gemini", 7, "Partnerships", {"Effects": base + "Agreements favored; listen well."}),
        "Cancer": TransitNote("Cancer", 8, "Caution", {"Effects": base + "Avoid risky moves; be alert."}),
        "Leo": TransitNote("Leo", 9, "Luck", {"Effects": base + "Travel/learning/spiritual focus."}),
        "Virgo": TransitNote("Virgo", 10, "Career", {"Effects": base + "Recognition possible; act responsibly."}),
        "Libra": TransitNote("Libra", 11, "Gains", {"Effects": base + "Networking brings profits."}),
        "Scorpio": TransitNote("Scorpio", 12, "Rest", {"Effects": base + "Control spending; rest mind."}),
        "Sagittarius": TransitNote("Sagittarius", 1, "Self Growth", {"Effects": base + "Confidence rises; start fresh."}),
        "Capricorn": TransitNote("Capricorn", 2, "Family & Wealth", {"Effects": base + "Good for savings and family harmony."}),
        "Aquarius": TransitNote("Aquarius", 3, "Communication", {"Effects": base + "Short trips and courage improve."}),
        "Pisces": TransitNote("Pisces", 4, "Home", {"Effects": base + "Home comfort and peace."}),
    }
