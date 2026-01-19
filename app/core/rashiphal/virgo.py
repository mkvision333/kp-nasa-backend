# app/core/rashiphal/virgo.py
from __future__ import annotations
from typing import Dict
from .meta import TransitNote

def get_transits() -> Dict[str, TransitNote]:
    base = "Virgo native: "
    return {
        "Aries": TransitNote("Aries", 8, "Transformation", {"Effects": base + "Be cautious; avoid risky moves."}),
        "Taurus": TransitNote("Taurus", 9, "Luck", {"Effects": base + "Guidance, travel, study favored."}),
        "Gemini": TransitNote("Gemini", 10, "Career", {"Effects": base + "Busy but productive; recognition possible."}),
        "Cancer": TransitNote("Cancer", 11, "Gains", {"Effects": base + "Good news via friends and networks."}),
        "Leo": TransitNote("Leo", 12, "Rest", {"Effects": base + "Control expenses; protect sleep."}),
        "Virgo": TransitNote("Virgo", 1, "Self Clarity", {"Effects": base + "Planning mindset; start new routines."}),
        "Libra": TransitNote("Libra", 2, "Family & Savings", {"Effects": base + "Budgeting and family talks favored."}),
        "Scorpio": TransitNote("Scorpio", 3, "Courage", {"Effects": base + "Short travel; communication wins."}),
        "Sagittarius": TransitNote("Sagittarius", 4, "Home", {"Effects": base + "Home comfort; property planning."}),
        "Capricorn": TransitNote("Capricorn", 5, "Creativity", {"Effects": base + "Good for creativity/children."}),
        "Aquarius": TransitNote("Aquarius", 6, "Work & Health", {"Effects": base + "Stay disciplined; avoid stress."}),
        "Pisces": TransitNote("Pisces", 7, "Partnership", {"Effects": base + "Diplomacy improves relationships."}),
    }
