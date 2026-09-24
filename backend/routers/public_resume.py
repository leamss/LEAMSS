"""Public (no-auth) resume upload for Pre-Assessment and Sales Assessment clients.

A client receives a secure per-record link (``/upload-resume/{token}``) by WhatsApp/email.
They open it, upload their resume, and it is securely attached to their assessment / lead record
in the cockpit and pre-assessments pipeline — no login required.
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


async def _resolve_target(token: str):
    """Resolve token against bulk ROWS, sales_assessments, and pre_assessments."""
    # 1. Bulk pre-assessment rows
    row = await ROWS.find_one({"$or": [{"resume_token": token}, {"id": token}]})
    if row:
        return {"kind": "bulk_row", "doc": row}

    # 2. Sales assessments (CRM / Cockpit)
    sa = await db["sales_assessments"].find_one({"$or": [{"resume_token": token}, {"share_token": token}, {"id": token}]})
    if sa:
        return {"kind": "sales_assessment", "doc": sa}

    # 3. Pre-assessments
    pa = await db["pre_assessments"].find_one({"$or": [
        {"resume_token": token},
        {"share_token": token},
        {"id": token},
        {"source_smart_sales_assessment_id": token}
    ]})
    if pa:
        return {"kind": "pre_assessment", "doc": pa}

    raise HTTPException(status_code=404, detail="This upload link is invalid or has expired.")


@router.get("/{token}")
async def resume_upload_info(token: str):
    target = await _resolve_target(token)
    kind = target["kind"]
    doc = target["doc"]

    if kind == "bulk_row":
        p = doc.get("parsed") or {}
        batch = await BATCHES.find_one({"id": doc.get("batch_id")}, {"_id": 0, "name": 1})
        return {
            "client_name": p.get("name") or doc.get("name") or "Applicant",
            "already_uploaded": bool(p.get("resume_file_id")),
            "status": doc.get("status"),
            "batch_name": (batch or {}).get("name"),
        }
    elif kind == "sales_assessment":
        has_file = bool(
            doc.get("resume_file_id")
            or (doc.get("profile_snapshot") or {}).get("resume_file_id")
            or (doc.get("profile_snapshot") or {}).get("primary_applicant", {}).get("resume_file_id")
        )
        return {
            "client_name": doc.get("client_name") or "Applicant",
            "already_uploaded": has_file,
            "status": doc.get("status") or "active",
            "batch_name": None,
        }
    else:  # pre_assessment
        has_file = bool(doc.get("resume_file_id"))
        return {
            "client_name": doc.get("client_name") or "Applicant",
            "already_uploaded": has_file,
            "status": doc.get("status") or "active",
            "batch_name": None,
        }


@router.post("/{token}")
async def resume_upload_submit(token: str, file: UploadFile = File(...)):
    target = await _resolve_target(token)
    kind = target["kind"]
    doc = target["doc"]

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="The file is empty. Please choose your resume file.")
    if len(content) > MAX_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 15 MB).")

    # Store into GridFS
    file_id = await _resume_gridfs.upload_from_stream(
        file.filename or f"resume-{token}",
        io.BytesIO(content),
        metadata={
            "contentType": file.content_type or "application/octet-stream",
            "token": token,
            "doc_id": doc.get("id"),
            "kind": kind,
            "public": True,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    now = datetime.now(timezone.utc)
    file_id_str = str(file_id)

    if kind == "bulk_row":
        p = dict(doc.get("parsed") or {})
        if p.get("resume_file_id"):
            try:
                await _resume_gridfs.delete(ObjectId(p["resume_file_id"]))
            except Exception:
                pass
        p["resume_file_id"] = file_id_str
        p["resume_filename"] = file.filename
        p["resume_uploaded"] = True

        text, err = await extract_text_smart(file.filename or "upload.pdf", content)
        if err or not text:
            await ROWS.update_one({"id": doc["id"]}, {"$set": {
                "parsed": p, "status": "needs_ai", "ai_error": err or "Could not read the uploaded file",
                "resume_uploaded_at": now,
            }})
            return {"ok": True, "message": "Thank you! Your resume was received. Our team will review it shortly."}

        res = await _enrich_from_text(p, text)
        await ROWS.update_one({"id": doc["id"]}, {"$set": {
            "status": res["status"], "parsed": res["parsed"],
            "errors": res.get("errors", []), "ai_error": res.get("ai_error"),
            "resume_uploaded_at": now,
        }})
        return {"ok": True, "message": "Thank you! Your resume was received successfully. "
                                       "Our team will prepare your personalised Pre-Assessment report."}

    elif kind == "sales_assessment":
        doc_id = doc.get("id")
        await db["sales_assessments"].update_one(
            {"id": doc_id},
            {"$set": {
                "resume_file_id": file_id_str,
                "resume_filename": file.filename,
                "resume_uploaded": True,
                "resume_uploaded_at": now,
                "profile_snapshot.resume_file_id": file_id_str,
                "profile_snapshot.resume_filename": file.filename,
                "profile_snapshot.primary_applicant.resume_file_id": file_id_str,
                "profile_snapshot.primary_applicant.resume_filename": file.filename,
                "updated_at": now,
            }}
        )
        # Also sync to linked pre_assessments if any
        await db["pre_assessments"].update_many(
            {"$or": [{"id": doc_id}, {"source_smart_sales_assessment_id": doc_id}]},
            {"$set": {
                "resume_file_id": file_id_str,
                "resume_filename": file.filename,
                "resume_uploaded": True,
                "resume_uploaded_at": now,
                "updated_at": now,
            }}
        )
        return {
            "ok": True,
            "message": "Thank you! Your resume was received successfully. Our team will review your profile and proceed with your Pre-Assessment.",
            "resume_file_id": file_id_str,
            "resume_filename": file.filename,
        }

    else:  # pre_assessment
        doc_id = doc.get("id")
        await db["pre_assessments"].update_one(
            {"id": doc_id},
            {"$set": {
                "resume_file_id": file_id_str,
                "resume_filename": file.filename,
                "resume_uploaded": True,
                "resume_uploaded_at": now,
                "updated_at": now,
            }}
        )
        # Also sync to linked sales_assessments if any
        src_id = doc.get("source_smart_sales_assessment_id") or doc_id
        await db["sales_assessments"].update_many(
            {"$or": [{"id": doc_id}, {"id": src_id}]},
            {"$set": {
                "resume_file_id": file_id_str,
                "resume_filename": file.filename,
                "resume_uploaded": True,
                "resume_uploaded_at": now,
                "profile_snapshot.resume_file_id": file_id_str,
                "profile_snapshot.resume_filename": file.filename,
                "profile_snapshot.primary_applicant.resume_file_id": file_id_str,
                "profile_snapshot.primary_applicant.resume_filename": file.filename,
                "updated_at": now,
            }}
        )
        return {
            "ok": True,
            "message": "Thank you! Your resume was received successfully. Our team will review your profile and proceed with your Pre-Assessment.",
            "resume_file_id": file_id_str,
            "resume_filename": file.filename,
        }
