# app/core/rashiphal/taurus.py
from __future__ import annotations
from typing import Dict
from .meta import TransitNote

def get_transits() -> Dict[str, TransitNote]:
    # TODO: Replace placeholders with your full English content (Taurus birth sign).
    # For now: generic but functional.
    base = "Taurus native: "
    return {
        "Aries": TransitNote("Aries", 12, "Spending & Reflection", {"Effects": base + "Expenses may rise; prefer rest and planning."}),
        "Taurus": TransitNote("Taurus", 1, "Self Focus & Fresh Start", {"Effects": base + "Confidence improves; good day to begin personal goals."}),
        "Gemini": TransitNote("Gemini", 2, "Family & Savings", {"Effects": base + "Focus on family talks and financial discipline."}),
        "Cancer": TransitNote("Cancer", 3, "Short Trips & Courage", {"Effects": base + "Good for networking and small travels."}),
        "Leo": TransitNote("Leo", 4, "Home & Comfort", {"Effects": base + "Home matters and property planning favored."}),
        "Virgo": TransitNote("Virgo", 5, "Creativity & Children", {"Effects": base + "Creative output improves; learn and teach."}),
        "Libra": TransitNote("Libra", 6, "Work & Health", {"Effects": base + "Stay organized; avoid overwork."}),
        "Scorpio": TransitNote("Scorpio", 7, "Partnerships", {"Effects": base + "Be diplomatic; agreements need clarity."}),
        "Sagittarius": TransitNote("Sagittarius", 8, "Sudden Changes", {"Effects": base + "Avoid risky decisions; keep calm."}),
        "Capricorn": TransitNote("Capricorn", 9, "Luck & Guidance", {"Effects": base + "Seek mentors; travel/learning favored."}),
        "Aquarius": TransitNote("Aquarius", 10, "Career & Recognition", {"Effects": base + "Professional growth possible; act responsibly."}),
        "Pisces": TransitNote("Pisces", 11, "Gains & Friends", {"Effects": base + "Networking brings gains; plan future goals."}),
    }
