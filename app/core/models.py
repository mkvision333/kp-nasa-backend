from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class NASAReq(BaseModel):
    # "2025-12-28T08:30:00"
    datetimeLocal: str = Field(..., description="Local datetime ISO string")
    tz: str = Field(..., description="IANA timezone, e.g. Asia/Kolkata")

    # Hyderabad example
    lat: float = Field(..., description="Latitude")
    lng: float = Field(..., description="Longitude")

class PlanetPos(BaseModel):
    name: str
    lon: float          # ecliptic longitude (0-360)
    lat: float          # ecliptic latitude
    dist_au: float      # distance in AU
    speed_lon: float    # deg/day (approx)

class NASAResp(BaseModel):
    jd_ut: float
    utc_iso: str
    planets: List[PlanetPos]

class PlanetPos(BaseModel):
    name: str
    lon: float
    lat: float
    dist_au: float
    speed_lon: float

    starLord: Optional[str] = None
    subLord: Optional[str] = None
    subSubLord: Optional[str] = None

# app/core/models.py  (append at bottom)
from pydantic import BaseModel
from typing import Optional

class PanchItem(BaseModel):
    name: str
    end_local: Optional[str] = None
    end_hms: Optional[str] = None
    extra: Optional[str] = None

class PanchangamResp(BaseModel):
    sunrise_local: str
    next_sunrise_local: str
    vaara: str
    tithi: PanchItem
    nakshatra: PanchItem
    yoga: PanchItem
    karana: PanchItem
