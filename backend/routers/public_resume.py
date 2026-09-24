"""Public (no-auth) resume upload for Pre-Assessment and Sales Assessment clients.

A client receives a secure per-record link (``/upload-resume/{token}``) by WhatsApp/email.
They open it, upload their resume, and it is securely attached to their assessment / lead record
in the cockpit and pre-assessments pipeline — no login required.
"""
from __future__ import annotations

import io
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from core.database import db
from routers.bulk_assessments import (
    ROWS, BATCHES, _resume_gridfs, _enrich_from_text,
)
from core.resume_extractor import extract_text_smart

router = APIRouter(prefix="/public/resume-upload", tags=["public-resume"])

MAX_BYTES = 15 * 1024 * 1024


async def _resolve_target(token: str):
    """Resolve token against leads, bulk ROWS, sales_assessments, pre_assessments, and profiles."""
    token = str(token or "").strip()
    if not token or token.lower() in ("undefined", "null", "direct", "public", "sample-token", "none"):
        return {"kind": "direct", "doc": {"id": "direct", "name": "Applicant", "client_name": "Applicant"}}

    # 1. Leads (Cockpit / Website / Navratri registrations)
    lead = await db["leads"].find_one({"$or": [
        {"resume_token": token},
        {"id": token},
        {"unique_id": token},
        {"unique_id": token.upper()},
        {"phone": token},
        {"phone": token.replace(" ", "").replace("-", "")},
    ]})
    if lead:
        return {"kind": "lead", "doc": lead}

    # 2. Bulk pre-assessment rows
    row = await ROWS.find_one({"$or": [
        {"resume_token": token},
        {"id": token},
        {"lead_id": token},
    ]})
    if row:
        return {"kind": "bulk_row", "doc": row}

    # 3. Sales assessments (CRM / Cockpit)
    sa = await db["sales_assessments"].find_one({"$or": [
        {"resume_token": token},
        {"share_token": token},
        {"id": token},
        {"lead_id": token},
    ]})
    if sa:
        return {"kind": "sales_assessment", "doc": sa}

    # 4. Pre-assessments
    pa = await db["pre_assessments"].find_one({"$or": [
        {"resume_token": token},
        {"share_token": token},
        {"id": token},
        {"pa_number": token},
        {"pa_number": token.upper()},
        {"source_smart_sales_assessment_id": token},
        {"lead_id": token},
    ]})
    if pa:
        return {"kind": "pre_assessment", "doc": pa}

    # 5. Eligibility profiles
    prof = await db["client_eligibility_profiles"].find_one({"$or": [
        {"resume_token": token},
        {"share_token": token},
        {"id": token},
    ]})
    if prof:
        return {"kind": "profile", "doc": prof}

    # Fallback to direct upload instead of 404
    return {"kind": "direct", "doc": {"id": token, "name": "Applicant", "client_name": "Applicant"}}


@router.get("/{token}")
async def resume_upload_info(token: str):
    target = await _resolve_target(token)
    kind = target["kind"]
    doc = target["doc"]

    if kind == "direct":
        return {
            "client_name": doc.get("name") or "Applicant",
            "already_uploaded": False,
            "status": "leads",
            "batch_name": None,
        }
    elif kind == "lead":
        has_file = bool(doc.get("resume_file_id") or doc.get("resume_url") or doc.get("resume_path"))
        return {
            "client_name": doc.get("name") or "Applicant",
            "already_uploaded": has_file,
            "status": doc.get("stage") or "leads",
            "batch_name": None,
        }
    elif kind == "bulk_row":
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
    elif kind == "profile":
        has_file = bool(doc.get("resume_file_id"))
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
async def resume_upload_submit(
    token: str,
    file: UploadFile = File(...),
    name: str = Form(None),
    phone: str = Form(None),
    email: str = Form(None),
):
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

    # Check if name or phone or email provided to link with existing lead
    if kind == "direct":
        import uuid
        matched_lead = None
        if phone:
            clean_p = phone.replace(" ", "").replace("-", "").replace("+", "")
            matched_lead = await db["leads"].find_one({"phone": {"$regex": clean_p}})
        if not matched_lead and email:
            matched_lead = await db["leads"].find_one({"email": email.strip().lower()})

        if matched_lead:
            doc_id = matched_lead.get("id")
            await db["leads"].update_one(
                {"id": doc_id},
                {"$set": {
                    "resume_file_id": file_id_str,
                    "resume_filename": file.filename,
                    "resume_url": f"/cockpit/resume/{file_id_str}",
                    "resume_path": f"/cockpit/resume/{file_id_str}",
                    "resume_uploaded": True,
                    "resume_uploaded_at": now,
                    "updated_at": now,
                }}
            )
            await db["sales_assessments"].update_many(
                {"$or": [{"lead_id": doc_id}, {"client_email": matched_lead.get("email")}]},
                {"$set": {
                    "resume_file_id": file_id_str,
                    "resume_filename": file.filename,
                    "resume_url": f"/cockpit/resume/{file_id_str}",
                    "resume_uploaded": True,
                    "resume_uploaded_at": now,
                    "profile_snapshot.resume_file_id": file_id_str,
                    "profile_snapshot.resume_filename": file.filename,
                    "updated_at": now,
                }}
            )
        else:
            new_lead_id = str(uuid.uuid4())
            await db["leads"].insert_one({
                "id": new_lead_id,
                "unique_id": f"L-{int(now.timestamp())}",
                "name": (name or "").strip() or "Applicant (Direct Upload)",
                "phone": (phone or "").strip(),
                "email": (email or "").strip().lower(),
                "resume_file_id": file_id_str,
                "resume_filename": file.filename,
                "resume_url": f"/cockpit/resume/{file_id_str}",
                "resume_path": f"/cockpit/resume/{file_id_str}",
                "resume_uploaded": True,
                "resume_uploaded_at": now,
                "stage": "leads",
                "source": "public_upload_link",
                "created_at": now,
                "updated_at": now,
            })

        return {
            "ok": True,
            "message": "Thank you! Your resume was received successfully. Our team will review your profile and proceed with your Pre-Assessment.",
            "resume_file_id": file_id_str,
            "resume_filename": file.filename,
        }

    if kind == "lead":
        doc_id = doc.get("id")
        await db["leads"].update_one(
            {"id": doc_id},
            {"$set": {
                "resume_file_id": file_id_str,
                "resume_filename": file.filename,
                "resume_url": f"/cockpit/resume/{file_id_str}",
                "resume_path": f"/cockpit/resume/{file_id_str}",
                "resume_uploaded": True,
                "resume_uploaded_at": now,
                "updated_at": now,
            }}
        )
        email = (doc.get("email") or "").strip().lower()
        match_targets = [{"lead_id": doc_id}]
        if email:
            match_targets.append({"client_email": email})
        await db["sales_assessments"].update_many(
            {"$or": match_targets},
            {"$set": {
                "resume_file_id": file_id_str,
                "resume_filename": file.filename,
                "resume_url": f"/cockpit/resume/{file_id_str}",
                "resume_uploaded": True,
                "resume_uploaded_at": now,
                "profile_snapshot.resume_file_id": file_id_str,
                "profile_snapshot.resume_filename": file.filename,
                "profile_snapshot.primary_applicant.resume_file_id": file_id_str,
                "profile_snapshot.primary_applicant.resume_filename": file.filename,
                "updated_at": now,
            }}
        )
        await db["pre_assessments"].update_many(
            {"$or": match_targets},
            {"$set": {
                "resume_file_id": file_id_str,
                "resume_filename": file.filename,
                "resume_url": f"/cockpit/resume/{file_id_str}",
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

    elif kind == "bulk_row":
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
                "resume_url": f"/cockpit/resume/{file_id_str}",
                "resume_uploaded": True,
                "resume_uploaded_at": now,
                "profile_snapshot.resume_file_id": file_id_str,
                "profile_snapshot.resume_filename": file.filename,
                "profile_snapshot.primary_applicant.resume_file_id": file_id_str,
                "profile_snapshot.primary_applicant.resume_filename": file.filename,
                "updated_at": now,
            }}
        )
        # Also sync to linked pre_assessments or leads if any
        await db["pre_assessments"].update_many(
            {"$or": [{"id": doc_id}, {"source_smart_sales_assessment_id": doc_id}]},
            {"$set": {
                "resume_file_id": file_id_str,
                "resume_filename": file.filename,
                "resume_url": f"/cockpit/resume/{file_id_str}",
                "resume_uploaded": True,
                "resume_uploaded_at": now,
                "updated_at": now,
            }}
        )
        if doc.get("lead_id"):
            await db["leads"].update_many(
                {"id": doc["lead_id"]},
                {"$set": {
                    "resume_file_id": file_id_str,
                    "resume_filename": file.filename,
                    "resume_url": f"/cockpit/resume/{file_id_str}",
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

    else:  # pre_assessment or profile
        doc_id = doc.get("id")
        await db["pre_assessments"].update_one(
            {"id": doc_id},
            {"$set": {
                "resume_file_id": file_id_str,
                "resume_filename": file.filename,
                "resume_url": f"/cockpit/resume/{file_id_str}",
                "resume_uploaded": True,
                "resume_uploaded_at": now,
                "updated_at": now,
            }}
        )
        src_id = doc.get("source_smart_sales_assessment_id") or doc_id
        await db["sales_assessments"].update_many(
            {"$or": [{"id": doc_id}, {"id": src_id}]},
            {"$set": {
                "resume_file_id": file_id_str,
                "resume_filename": file.filename,
                "resume_url": f"/cockpit/resume/{file_id_str}",
                "resume_uploaded": True,
                "resume_uploaded_at": now,
                "profile_snapshot.resume_file_id": file_id_str,
                "profile_snapshot.resume_filename": file.filename,
                "profile_snapshot.primary_applicant.resume_file_id": file_id_str,
                "profile_snapshot.primary_applicant.resume_filename": file.filename,
                "updated_at": now,
            }}
        )
        if doc.get("lead_id"):
            await db["leads"].update_many(
                {"id": doc["lead_id"]},
                {"$set": {
                    "resume_file_id": file_id_str,
                    "resume_filename": file.filename,
                    "resume_url": f"/cockpit/resume/{file_id_str}",
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

