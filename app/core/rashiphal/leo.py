# app/core/rashiphal/leo.py
from __future__ import annotations
from typing import Dict
from .meta import TransitNote

def get_transits() -> Dict[str, TransitNote]:
    base = "Leo native: "
    return {
        "Aries": TransitNote("Aries", 9, "Luck & Dharma", {"Effects": base + "Good for travel, mentors, blessings."}),
        "Taurus": TransitNote("Taurus", 10, "Career", {"Effects": base + "Recognition possible; avoid ego clashes."}),
        "Gemini": TransitNote("Gemini", 11, "Gains", {"Effects": base + "Profits via network and friends."}),
        "Cancer": TransitNote("Cancer", 12, "Rest", {"Effects": base + "Expenses rise; sleep and eye-care."}),
        "Leo": TransitNote("Leo", 1, "Self Power", {"Effects": base + "Confidence and leadership high."}),
        "Virgo": TransitNote("Virgo", 2, "Family & Wealth", {"Effects": base + "Savings and valuables favored."}),
        "Libra": TransitNote("Libra", 3, "Communication", {"Effects": base + "Short trips and courage improve."}),
        "Scorpio": TransitNote("Scorpio", 4, "Home", {"Effects": base + "Home focus; be calm with family."}),
        "Sagittarius": TransitNote("Sagittarius", 5, "Creativity", {"Effects": base + "Joy, romance, and creativity increase."}),
        "Capricorn": TransitNote("Capricorn", 6, "Work Wins", {"Effects": base + "Competition favorable; health routine."}),
        "Aquarius": TransitNote("Aquarius", 7, "Partnerships", {"Effects": base + "Agreements good; stay diplomatic."}),
        "Pisces": TransitNote("Pisces", 8, "Sudden Turns", {"Effects": base + "Avoid risks; focus on safety."}),
    }
