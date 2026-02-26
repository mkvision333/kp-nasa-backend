# rashiphal/festivals_rules.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List, Literal

DecisionTime = Literal["sunrise", "pradosha", "nishitha", "solar"]

@dataclass(frozen=True)
class FestivalRule:
    key: str
    name_te: str
    name_en: str
    decision_time: DecisionTime

    # Lunar match fields (for sunrise/pradosha/nishitha rules)
    lunar_month: Optional[str] = None     # "Chaitra"..."Phalguna" (Amanta)
    paksha: Optional[str] = None          # "Shukla" or "Krishna"
    tithi: Optional[str] = None           # "Pratipada"... "Amavasya"

    # Solar rules (for Sankranti etc.)
    solar: bool = False


# ✅ IMPORTANT: Generator expects this exact name:
FESTIVAL_RULES: List[FestivalRule] = [
    # ===== Sunrise (Udaya tithi / Poorvaviddha) =====
    FestivalRule("UGADI", "ఉగాది", "Ugadi", "sunrise", "Chaitra", "Shukla", "Pratipada"),
    FestivalRule("RAMA_NAVAMI", "శ్రీరామ నవమి", "Sri Rama Navami", "sunrise", "Chaitra", "Shukla", "Navami"),
    FestivalRule("VINAYAKA_CHATURTHI", "వినాయక చవితి", "Ganesh Chaturthi", "sunrise", "Bhadrapada", "Shukla", "Chaturthi"),
    FestivalRule("NAVARATRI_START", "శరన్నవరాత్రి ప్రారంభం", "Sharad Navaratri Start", "sunrise", "Ashwayuja", "Shukla", "Pratipada"),
    FestivalRule("VIJAYADASHAMI", "విజయదశమి", "Vijayadashami", "sunrise", "Ashwayuja", "Shukla", "Dashami"),

    # ===== Pradosha (evening window) =====
    FestivalRule("DEEPAVALI", "దీపావళి", "Deepavali", "pradosha", "Ashwayuja", "Krishna", "Amavasya"),
    FestivalRule("HOLI", "హోళీ", "Holi", "pradosha", "Phalguna", "Shukla", "Purnima"),

    # ===== Nishitha (mid-night) =====
    FestivalRule("MAHA_SHIVARATRI", "మహా శివరాత్రి", "Maha Shivaratri", "nishitha", "Magha", "Krishna", "Chaturdashi"),
    FestivalRule("KRISHNA_JANMASHTAMI", "శ్రీకృష్ణ జన్మాష్టమి", "Sri Krishna Janmashtami", "nishitha", "Shravana", "Krishna", "Ashtami"),

    # ===== Solar =====
    FestivalRule("MAKARA_SANKRANTI", "మకర సంక్రాంతి", "Makara Sankranti", "solar", solar=True),
]