# app/routes/pdf_routes.py
from __future__ import annotations

import os
from typing import Dict, Any
from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import FileResponse

from app.pdf_engine.generator import generate_pdf

router = APIRouter(prefix="/pdf", tags=["pdf"])

# temporary folder (Render safe)
TMP_DIR = "tmp/pdfs"


# -------------------------------------------------
# ✅ FREE Birth Chart PDF
# -------------------------------------------------
@router.post("/birth-chart")
def create_birth_chart_pdf(payload: Dict[str, Any] = Body(...)):
    """
    FREE Birth Chart PDF
    """
    try:
        file_path, report_id = generate_pdf(
            pdf_type="birth_chart",
            payload=payload,
            out_dir=TMP_DIR,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"PDF generation failed: {str(e)}")

    filename = os.path.basename(file_path)

    return {
        "ok": True,
        "reportId": report_id,
        "downloadUrl": f"/pdf/download/{filename}",
    }


# -------------------------------------------------
# 📥 Download Endpoint
# -------------------------------------------------
@router.get("/download/{filename}")
def download_pdf(filename: str):
    file_path = os.path.join(TMP_DIR, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="PDF not found")

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=filename,
    )