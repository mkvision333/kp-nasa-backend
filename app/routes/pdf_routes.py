# app/routes/pdf_routes.py ✅ FULL REPLACE
from __future__ import annotations

import os
import uuid
from typing import Dict, Any

from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import FileResponse

from app.pdf_engine.templates.birth_chart import build_birth_chart_pdf

router = APIRouter(prefix="/pdf", tags=["pdf"])

# ✅ Render/Server safe writable dir (Render supports /tmp)
TMP_DIR = "/tmp/pdfs"


@router.post("/birth-chart")
def create_birth_chart_pdf(payload: Dict[str, Any] = Body(...)):
    """
    Build Birth Chart PDF and return the PDF directly (no downloadUrl).
    """
    try:
        os.makedirs(TMP_DIR, exist_ok=True)

        # robust report id
        report_id = str(payload.get("reportId") or payload.get("id") or uuid.uuid4().hex[:10].upper())
        filename = f"BirthChart_{report_id}.pdf"
        file_path = os.path.join(TMP_DIR, filename)

        meta = {
            "title": "Birth Chart Report",
            "app": "Pro KP Astrologer",
            "reportId": report_id,
        }

        build_birth_chart_pdf(file_path=file_path, data=payload, meta=meta)

        if not os.path.exists(file_path):
            raise RuntimeError("PDF file not created")

        return FileResponse(
            file_path,
            media_type="application/pdf",
            filename=filename,
            headers={
                "Cache-Control": "no-store",
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))