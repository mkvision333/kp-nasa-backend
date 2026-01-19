# app/core/rashiphal/libra.py
from __future__ import annotations
from typing import Dict
from .meta import TransitNote

def get_transits() -> Dict[str, TransitNote]:
    base = "Libra native: "
    return {
        "Aries": TransitNote("Aries", 7, "Relationships", {"Effects": base + "Good for partnerships and agreements."}),
        "Taurus": TransitNote("Taurus", 8, "Caution", {"Effects": base + "Avoid risks; keep calm and practical."}),
        "Gemini": TransitNote("Gemini", 9, "Luck", {"Effects": base + "Learning and travel favored."}),
        "Cancer": TransitNote("Cancer", 10, "Career", {"Effects": base + "Recognition possible; act steadily."}),
        "Leo": TransitNote("Leo", 11, "Gains", {"Effects": base + "Networking brings profits."}),
        "Virgo": TransitNote("Virgo", 12, "Expenses", {"Effects": base + "Control spending; rest mind."}),
        "Libra": TransitNote("Libra", 1, "Self Balance", {"Effects": base + "Confidence improves; be decisive."}),
        "Scorpio": TransitNote("Scorpio", 2, "Family & Wealth", {"Effects": base + "Good for savings; speak softly."}),
        "Sagittarius": TransitNote("Sagittarius", 3, "Communication", {"Effects": base + "Short trips; courage boosts."}),
        "Capricorn": TransitNote("Capricorn", 4, "Home", {"Effects": base + "Home matters; keep calm."}),
        "Aquarius": TransitNote("Aquarius", 5, "Creativity", {"Effects": base + "Creativity and joy increase."}),
        "Pisces": TransitNote("Pisces", 6, "Work", {"Effects": base + "Discipline helps; watch health."}),
    }
