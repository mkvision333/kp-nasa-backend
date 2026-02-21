# backend/routes/pdf_routes.py
from __future__ import annotations

import os
from typing import Dict, Any
from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import FileResponse

from pdf_engine.generator import generate_pdf

router = APIRouter(prefix="/pdf", tags=["pdf"])

TMP_DIR = "tmp/pdfs"


@router.post("/simple-birth-chart")
def create_simple_birth_chart_pdf(payload: Dict[str, Any] = Body(...)):
    """
    FREE: generates and returns a download URL.
    """
    try:
        file_path, report_id = generate_pdf("simple_birth_chart", payload, out_dir=TMP_DIR)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    filename = os.path.basename(file_path)
    return {
        "ok": True,
        "reportId": report_id,
        "downloadUrl": f"/pdf/download/{filename}",
    }


@router.get("/download/{filename}")
def download_pdf(filename: str):
    file_path = os.path.join(TMP_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="PDF not found")
    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=filename,
    )