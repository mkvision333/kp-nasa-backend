# app/core/rashiphal/capricorn.py
from __future__ import annotations
from typing import Dict
from .meta import TransitNote

def get_transits() -> Dict[str, TransitNote]:
    base = "Capricorn native: "
    return {
        "Aries": TransitNote("Aries", 4, "Home Focus", {"Effects": base + "Home matters; stay calm and steady."}),
        "Taurus": TransitNote("Taurus", 5, "Creativity", {"Effects": base + "Creativity and joy improve."}),
        "Gemini": TransitNote("Gemini", 6, "Work", {"Effects": base + "Competition favorable; health routine."}),
        "Cancer": TransitNote("Cancer", 7, "Partnerships", {"Effects": base + "Diplomacy improves relationships."}),
        "Leo": TransitNote("Leo", 8, "Caution", {"Effects": base + "Avoid risks; stay alert."}),
        "Virgo": TransitNote("Virgo", 9, "Luck", {"Effects": base + "Learning and guidance favored."}),
        "Libra": TransitNote("Libra", 10, "Career", {"Effects": base + "Recognition possible; act responsibly."}),
        "Scorpio": TransitNote("Scorpio", 11, "Gains", {"Effects": base + "Friends support; profits improve."}),
        "Sagittarius": TransitNote("Sagittarius", 12, "Expenses", {"Effects": base + "Control spending; rest well."}),
        "Capricorn": TransitNote("Capricorn", 1, "Self Discipline", {"Effects": base + "Strong focus; start new routines."}),
        "Aquarius": TransitNote("Aquarius", 2, "Family & Wealth", {"Effects": base + "Savings and family harmony."}),
        "Pisces": TransitNote("Pisces", 3, "Communication", {"Effects": base + "Short trips and communication wins."}),
    }
