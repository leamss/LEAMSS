"""Public (no-auth) resume upload for Bulk Pre-Assessment clients.

A client receives a secure per-record link (``/upload-resume/{token}``) by email.
They open it, upload their resume, and it is attached to their bulk row + the AI
re-runs to detect their ANZSCO occupation — no login required.
"""
from __future__ import annotations

import io
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, File, HTTPException, UploadFile

from core.database import db
from routers.bulk_assessments import (
    ROWS, BATCHES, _resume_gridfs, _enrich_from_text,
)
from core.resume_extractor import extract_text_smart

router = APIRouter(prefix="/public/resume-upload", tags=["public-resume"])

MAX_BYTES = 15 * 1024 * 1024


async def _row_for_token(token: str):
    row = await ROWS.find_one({"resume_token": token})
    if not row:
        raise HTTPException(status_code=404, detail="This upload link is invalid or has expired.")
    return row


@router.get("/{token}")
async def resume_upload_info(token: str):
    row = await _row_for_token(token)
    p = row.get("parsed") or {}
    batch = await BATCHES.find_one({"id": row.get("batch_id")}, {"_id": 0, "name": 1})
    return {
        "client_name": p.get("name") or "Applicant",
        "already_uploaded": bool(p.get("resume_file_id")),
        "status": row.get("status"),
        "batch_name": (batch or {}).get("name"),
    }


@router.post("/{token}")
async def resume_upload_submit(token: str, file: UploadFile = File(...)):
    row = await _row_for_token(token)
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="The file is empty. Please choose your resume file.")
    if len(content) > MAX_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 15 MB).")

    p = dict(row.get("parsed") or {})
    if p.get("resume_file_id"):
        try:
            await _resume_gridfs.delete(ObjectId(p["resume_file_id"]))
        except Exception:
            pass
    file_id = await _resume_gridfs.upload_from_stream(
        file.filename or f"resume-{token}", io.BytesIO(content),
        metadata={"contentType": file.content_type or "application/octet-stream", "row_id": row["id"], "public": True},
    )
    p["resume_file_id"] = str(file_id)
    p["resume_filename"] = file.filename
    p["resume_uploaded"] = True
    now = datetime.now(timezone.utc)

    text, err = await extract_text_smart(file.filename or "upload.pdf", content)
    if err or not text:
        await ROWS.update_one({"id": row["id"]}, {"$set": {
            "parsed": p, "status": "needs_ai", "ai_error": err or "Could not read the uploaded file",
            "resume_uploaded_at": now,
        }})
        return {"ok": True, "message": "Thank you! Your resume was received. Our team will review it shortly."}

    res = await _enrich_from_text(p, text)
    await ROWS.update_one({"id": row["id"]}, {"$set": {
        "status": res["status"], "parsed": res["parsed"],
        "errors": res.get("errors", []), "ai_error": res.get("ai_error"),
        "resume_uploaded_at": now,
    }})
    return {"ok": True, "message": "Thank you! Your resume was received successfully. "
                                   "Our team will prepare your personalised Pre-Assessment report."}
