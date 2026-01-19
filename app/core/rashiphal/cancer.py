# app/core/rashiphal/cancer.py
from __future__ import annotations
from typing import Dict
from .meta import TransitNote

def get_transits() -> Dict[str, TransitNote]:
    base = "Cancer native: "
    return {
        "Aries": TransitNote("Aries", 10, "Career Focus", {"Effects": base + "Responsibilities rise; work steadily."}),
        "Taurus": TransitNote("Taurus", 11, "Gains", {"Effects": base + "Friends and profits improve."}),
        "Gemini": TransitNote("Gemini", 12, "Rest", {"Effects": base + "Control expenses; protect sleep."}),
        "Cancer": TransitNote("Cancer", 1, "Emotional Strength", {"Effects": base + "Good for self-care and starting fresh."}),
        "Leo": TransitNote("Leo", 2, "Family & Money", {"Effects": base + "Good for savings and family harmony."}),
        "Virgo": TransitNote("Virgo", 3, "Communication", {"Effects": base + "Short trips and learning favored."}),
        "Libra": TransitNote("Libra", 4, "Home Peace", {"Effects": base + "Home matters improve; stay calm."}),
        "Scorpio": TransitNote("Scorpio", 5, "Creativity", {"Effects": base + "Joy through creativity/children."}),
        "Sagittarius": TransitNote("Sagittarius", 6, "Work & Health", {"Effects": base + "Be disciplined; avoid overwork."}),
        "Capricorn": TransitNote("Capricorn", 7, "Partnership", {"Effects": base + "Diplomacy helps relationships."}),
        "Aquarius": TransitNote("Aquarius", 8, "Sudden Changes", {"Effects": base + "Avoid risky choices; stay alert."}),
        "Pisces": TransitNote("Pisces", 9, "Luck", {"Effects": base + "Travel/learning/spiritual focus."}),
    }
