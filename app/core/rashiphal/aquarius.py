# app/core/rashiphal/aquarius.py
from __future__ import annotations
from typing import Dict
from .meta import TransitNote

def get_transits() -> Dict[str, TransitNote]:
    base = "Aquarius native: "
    return {
        "Aries": TransitNote("Aries", 3, "Courage", {"Effects": base + "Short trips and communication improve."}),
        "Taurus": TransitNote("Taurus", 4, "Home", {"Effects": base + "Home comfort and peace."}),
        "Gemini": TransitNote("Gemini", 5, "Creativity", {"Effects": base + "Joy and creativity increase."}),
        "Cancer": TransitNote("Cancer", 6, "Work", {"Effects": base + "Competition favorable; stay disciplined."}),
        "Leo": TransitNote("Leo", 7, "Partnership", {"Effects": base + "Agreements favored; be diplomatic."}),
        "Virgo": TransitNote("Virgo", 8, "Caution", {"Effects": base + "Avoid risky moves; stay alert."}),
        "Libra": TransitNote("Libra", 9, "Luck", {"Effects": base + "Learning/travel/spiritual focus."}),
        "Scorpio": TransitNote("Scorpio", 10, "Career", {"Effects": base + "Recognition possible; act responsibly."}),
        "Sagittarius": TransitNote("Sagittarius", 11, "Gains", {"Effects": base + "Networking brings profits."}),
        "Capricorn": TransitNote("Capricorn", 12, "Rest", {"Effects": base + "Control expenses; rest mind."}),
        "Aquarius": TransitNote("Aquarius", 1, "Self Vision", {"Effects": base + "New ideas; start fresh."}),
        "Pisces": TransitNote("Pisces", 2, "Family & Wealth", {"Effects": base + "Savings and family harmony."}),
    }
