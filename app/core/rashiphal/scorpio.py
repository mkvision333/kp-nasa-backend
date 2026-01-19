# app/core/rashiphal/scorpio.py
from __future__ import annotations
from typing import Dict
from .meta import TransitNote

def get_transits() -> Dict[str, TransitNote]:
    base = "Scorpio native: "
    return {
        "Aries": TransitNote("Aries", 6, "Work Wins", {"Effects": base + "Competition favorable; stay disciplined."}),
        "Taurus": TransitNote("Taurus", 7, "Partnerships", {"Effects": base + "Diplomacy improves relationships."}),
        "Gemini": TransitNote("Gemini", 8, "Caution", {"Effects": base + "Avoid risky investments; stay calm."}),
        "Cancer": TransitNote("Cancer", 9, "Luck", {"Effects": base + "Spiritual travel/learning favored."}),
        "Leo": TransitNote("Leo", 10, "Career", {"Effects": base + "Recognition possible; act responsibly."}),
        "Virgo": TransitNote("Virgo", 11, "Gains", {"Effects": base + "Friends support; profits improve."}),
        "Libra": TransitNote("Libra", 12, "Rest", {"Effects": base + "Control expenses; protect sleep."}),
        "Scorpio": TransitNote("Scorpio", 1, "Self Power", {"Effects": base + "Confidence and intensity rise."}),
        "Sagittarius": TransitNote("Sagittarius", 2, "Family & Wealth", {"Effects": base + "Savings and family talks favored."}),
        "Capricorn": TransitNote("Capricorn", 3, "Communication", {"Effects": base + "Short trips and messaging success."}),
        "Aquarius": TransitNote("Aquarius", 4, "Home", {"Effects": base + "Home focus; keep peace."}),
        "Pisces": TransitNote("Pisces", 5, "Creativity", {"Effects": base + "Creative output improves."}),
    }
