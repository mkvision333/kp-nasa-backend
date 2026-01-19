# app/core/rashiphal/gemini.py
from __future__ import annotations
from typing import Dict
from .meta import TransitNote

def get_transits() -> Dict[str, TransitNote]:
    base = "Gemini native: "
    return {
        "Aries": TransitNote("Aries", 11, "Gains & Support", {"Effects": base + "Good for profits, friends, and networking."}),
        "Taurus": TransitNote("Taurus", 12, "Low Energy, Rest", {"Effects": base + "Take rest; control expenses and sleep well."}),
        "Gemini": TransitNote("Gemini", 1, "Confidence & Plans", {"Effects": base + "High activity; start new plans."}),
        "Cancer": TransitNote("Cancer", 2, "Family & Savings", {"Effects": base + "Family focus; improve finances."}),
        "Leo": TransitNote("Leo", 3, "Courage & Travel", {"Effects": base + "Short trips and communication success."}),
        "Virgo": TransitNote("Virgo", 4, "Home Matters", {"Effects": base + "Home/vehicle focus; keep calm."}),
        "Libra": TransitNote("Libra", 5, "Creativity", {"Effects": base + "Fun, creativity, romance improves."}),
        "Scorpio": TransitNote("Scorpio", 6, "Work Wins", {"Effects": base + "Competition favorable; stay disciplined."}),
        "Sagittarius": TransitNote("Sagittarius", 7, "Partnerships", {"Effects": base + "Good for agreements; listen well."}),
        "Capricorn": TransitNote("Capricorn", 8, "Sudden Turns", {"Effects": base + "Avoid risks; keep focus."}),
        "Aquarius": TransitNote("Aquarius", 9, "Luck & Learning", {"Effects": base + "Good for higher learning and guidance."}),
        "Pisces": TransitNote("Pisces", 10, "Career Growth", {"Effects": base + "Recognition possible; act responsibly."}),
    }
