# app/core/rashiphal/engine.py
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from .meta import DailyRashiPhal, TransitNote, house_from_transit, normalize_sign

# Each module exposes: get_transits() -> Dict[moon_sign, TransitNote]
# We'll import lazily to keep startup fast.

PROVIDERS: Dict[str, Callable[[], Dict[str, TransitNote]]] = {}

def _register_default_providers():
    # Local imports to avoid circular imports / speed
    from .aries import get_transits as aries
    from .taurus import get_transits as taurus
    from .gemini import get_transits as gemini
    from .cancer import get_transits as cancer
    from .leo import get_transits as leo
    from .virgo import get_transits as virgo
    from .libra import get_transits as libra
    from .scorpio import get_transits as scorpio
    from .sagittarius import get_transits as sagittarius
    from .capricorn import get_transits as capricorn
    from .aquarius import get_transits as aquarius
    from .pisces import get_transits as pisces

    PROVIDERS.update({
        "Aries": aries,
        "Taurus": taurus,
        "Gemini": gemini,
        "Cancer": cancer,
        "Leo": leo,
        "Virgo": virgo,
        "Libra": libra,
        "Scorpio": scorpio,
        "Sagittarius": sagittarius,
        "Capricorn": capricorn,
        "Aquarius": aquarius,
        "Pisces": pisces,
    })

_register_default_providers()

def build_daily_rashiphal(
    birth_sign: str,
    moon_sign: str,
    moon_nakshatra: Optional[str] = None,
    overrides: Optional[Dict[str, Any]] = None,
) -> DailyRashiPhal:
    """
    - birth_sign: user's Janma Rashi (Moon sign)
    - moon_sign: current transit Moon sign
    - moon_nakshatra: optional, for display only
    - overrides: optional dict to override text blocks without changing modules

    overrides format examples:
      {
        "Aries": {
          "Taurus": {
            "headline": "...",
            "sections": {"Effects": "..."},
            "remedy": "..."
          }
        }
      }
    """
    b = normalize_sign(birth_sign)
    m = normalize_sign(moon_sign)
    house = house_from_transit(b, m)

    provider = PROVIDERS.get(b)
    if not provider:
        raise ValueError(f"No provider for birth sign: {b}")

    transits = provider()
    note = transits.get(m)
    if not note:
        # fallback: generic note if missing
        note = TransitNote(
            moon_sign=m,
            house=house,
            headline="General Transit Day",
            sections={
                "Effects": "Today may feel mixed. Keep actions steady and avoid impulsive decisions.",
                "Finance": "Be practical with spending. Prefer essentials over luxury purchases.",
                "Health": "Hydrate well and take short breaks to avoid mental fatigue.",
            },
            remedy="Spend a few minutes in silent prayer or mindfulness.",
        )

    # apply overrides (if any)
    if overrides:
        o_birth = overrides.get(b) if isinstance(overrides, dict) else None
        if isinstance(o_birth, dict):
            o_moon = o_birth.get(m)
            if isinstance(o_moon, dict):
                headline = o_moon.get("headline", note.headline)
                sections = dict(note.sections)
                sec_over = o_moon.get("sections")
                if isinstance(sec_over, dict):
                    sections.update({str(k): str(v) for k, v in sec_over.items()})
                remedy = o_moon.get("remedy", note.remedy)
                note = TransitNote(
                    moon_sign=note.moon_sign,
                    house=note.house,
                    headline=str(headline),
                    sections=sections,
                    remedy=str(remedy) if remedy else None,
                )

    # ensure house sync (note.house might already be correct for that birth sign)
    # but keep engine’s computed value authoritative
    note = TransitNote(
        moon_sign=note.moon_sign,
        house=house,
        headline=note.headline,
        sections=note.sections,
        remedy=note.remedy,
    )

    return DailyRashiPhal(
        birth_sign=b,
        moon_sign=m,
        moon_nakshatra=moon_nakshatra,
        house=house,
        note=note,
    )

def to_json(obj: DailyRashiPhal) -> Dict[str, Any]:
    return {
        "birthSign": obj.birth_sign,
        "moonSign": obj.moon_sign,
        "moonNakshatra": obj.moon_nakshatra,
        "houseFromBirth": obj.house,
        "headline": obj.note.headline,
        "sections": obj.note.sections,
        "remedy": obj.note.remedy,
        "disclaimer": obj.disclaimer,
    }
