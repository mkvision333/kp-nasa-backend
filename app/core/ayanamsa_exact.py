# app/core/ayanamsa_exact.py
import math

try:
    import swisseph as swe
except Exception:
    swe = None


def _wrap360(x: float) -> float:
    x = float(x) % 360.0
    return x if x >= 0 else x + 360.0


def get_ayanamsa_deg(jd_ut: float, mode: str = "KP") -> float:
    """
    EXACT ayanamsa from Swiss Ephemeris (UT-based).

    mode:
      - "KP"      => swe.SIDM_KRISHNAMURTI
      - "LAHIRI"  => swe.SIDM_LAHIRI

    Returns degrees in [0..360)
    """
    if swe is None:
        raise RuntimeError("Swiss Ephemeris not available. Install 'pyswisseph'.")

    m = (mode or "KP").strip().upper()

    if m in ("KP", "KRISHNAMURTI"):
        sid = getattr(swe, "SIDM_KRISHNAMURTI", None)
        if sid is None:
            raise RuntimeError("This swisseph build lacks SIDM_KRISHNAMURTI.")
        swe.set_sid_mode(sid, 0, 0)
    elif m in ("LAHIRI", "CHITRAPAKSHA"):
        swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
    else:
        raise ValueError(f"Unknown ayanamsa mode: {mode}")

    ay = float(swe.get_ayanamsa_ut(jd_ut))
    return _wrap360(ay)
