# backend/pdf_engine/generator.py ✅ FULL REPLACE
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Tuple

from app.pdf_engine.templates.birth_chart import build_birth_chart_pdf


def ensure_dir(p: str) -> None:
    os.makedirs(p, exist_ok=True)


def generate_pdf(
    pdf_type: str,
    payload: Dict[str, Any],
    out_dir: str = "/tmp/pdfs",
) -> Tuple[str, str]:
    """
    Returns (file_path, report_id)
    Render safe: /tmp/pdfs
    """
    ensure_dir(out_dir)
    report_id = f"{pdf_type.upper()}-{uuid.uuid4().hex[:10].upper()}"
    filename = f"{pdf_type}_{report_id}.pdf"
    file_path = os.path.join(out_dir, filename)

    meta = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "reportId": report_id,
        "pdfType": pdf_type,
        "txId": payload.get("txId") or "",
        "userName": payload.get("userName") or "",
    }

    if pdf_type == "birth_chart":
        build_birth_chart_pdf(file_path=file_path, data=payload, meta=meta)
        return file_path, report_id

    raise ValueError(f"Unknown pdf_type: {pdf_type}")