# app/core/rahu_ketu.py

def calc_rahu_ketu(moon_lon: float):
    """
    Mean Rahu–Ketu (180° apart)
    Input: Moon longitude (nirayana)
    """
    rahu = moon_lon % 360.0
    ketu = (rahu + 180.0) % 360.0
    return rahu, ketu
