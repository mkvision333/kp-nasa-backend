# app/core/rashiphal/pisces.py
from __future__ import annotations
from typing import Dict
from .meta import TransitNote

def get_transits() -> Dict[str, TransitNote]:
    base = "Pisces native: "
    return {
        "Aries": TransitNote("Aries", 2, "Family & Wealth", {"Effects": base + "Good for savings and family talks."}),
        "Taurus": TransitNote("Taurus", 3, "Communication", {"Effects": base + "Short trips and courage improve."}),
        "Gemini": TransitNote("Gemini", 4, "Home", {"Effects": base + "Home comfort and peace."}),
        "Cancer": TransitNote("Cancer", 5, "Creativity", {"Effects": base + "Joy and creativity increase."}),
        "Leo": TransitNote("Leo", 6, "Work", {"Effects": base + "Discipline helps; watch health."}),
        "Virgo": TransitNote("Virgo", 7, "Partnership", {"Effects": base + "Diplomacy improves relationships."}),
        "Libra": TransitNote("Libra", 8, "Caution", {"Effects": base + "Avoid risks; stay alert."}),
        "Scorpio": TransitNote("Scorpio", 9, "Luck", {"Effects": base + "Learning/travel/spiritual focus."}),
        "Sagittarius": TransitNote("Sagittarius", 10, "Career", {"Effects": base + "Recognition possible; act responsibly."}),
        "Capricorn": TransitNote("Capricorn", 11, "Gains", {"Effects": base + "Networking brings profits."}),
        "Aquarius": TransitNote("Aquarius", 12, "Rest", {"Effects": base + "Control expenses; rest mind."}),
        "Pisces": TransitNote("Pisces", 1, "Self Care", {"Effects": base + "Emotional clarity; start fresh gently."}),
    }
