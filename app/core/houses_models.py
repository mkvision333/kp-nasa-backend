# app/core/houses_models.py
from pydantic import BaseModel, Field
from typing import Dict

class PlacidusReq(BaseModel):
    jd_ut: float = Field(..., description="Julian Day UT (e.g. from nasa endpoint)")
    lat: float = Field(..., description="Latitude")
    lng: float = Field(..., description="Longitude (east positive for India)")
    ayanamsa_deg: float = Field(0.0, description="Ayanamsa degrees to convert tropical -> sidereal")

class PlacidusResp(BaseModel):
    cusps_tropical: Dict[str, float]
    cusps_sidereal: Dict[str, float]
