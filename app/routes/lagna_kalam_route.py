# app/routes/lagna_kalam_route.py ✅ NEW
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.core.lagna_kalam_calc import compute_lagna_kalam

router = APIRouter()

class LagnaKalamReq(BaseModel):
    dateKey: str          # "YYYY-MM-DD"
    tz: str
    lat: float
    lon: float
    ayanamsa: Optional[str] = "KP_OLD"   # "KP" / "KP_OLD" / "KP_NEW" / "LAHIRI"

@router.post("/api/astro/lagna_kalam")
def lagna_kalam(req: LagnaKalamReq) -> Dict[str, Any]:
    print("LAGNA ROUTE HIT:", req.model_dump(), flush=True)
    try:
        out = compute_lagna_kalam(
            dateKey=req.dateKey,
            tz=req.tz,
            lat=float(req.lat),
            lon=float(req.lon),
            ayanamsa=str(req.ayanamsa or "KP_OLD"),
        )
        print("LAGNA ROUTE DONE. type=", type(out), "keys=", (list(out.keys()) if isinstance(out, dict) else None), flush=True)
        return out
    except Exception as e:
        print("LAGNA ROUTE ERROR:", repr(e), flush=True)
        raise HTTPException(status_code=400, detail=str(e))
