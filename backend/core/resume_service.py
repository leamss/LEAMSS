"""Centralized Resume Management & Synchronization Service.

Handles secure GridFS storage, streaming, metadata extraction,
and seamless persistence across Leads, Pre-Assessments, Converted Clients,
and Case Manager records.
"""
from __future__ import annotations

import io
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple
from urllib.parse import unquote, quote, urlsplit, urlunsplit

from bson import ObjectId
import httpx
from motor.motor_asyncio import AsyncIOMotorGridFSBucket

from core.database import db

logger = logging.getLogger(__name__)

RESUME_BUCKETS = ("bulk_resumes", "resume_files", "assessment_reports", "fs", "resumes", "lead_resumes")
MAX_RESUME_BYTES = 15 * 1024 * 1024  # 15 MB limit


def normalize_content_type(filename: str, provided_type: Optional[str] = None) -> str:
    fn = (filename or "").lower()
    if fn.endswith(".pdf"):
        return "application/pdf"
    if fn.endswith(".docx"):
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if fn.endswith(".doc"):
        return "application/msword"
    if fn.endswith(".txt"):
        return "text/plain"
    if fn.endswith(".png"):
        return "image/png"
    if fn.endswith(".jpg") or fn.endswith(".jpeg"):
        return "image/jpeg"
    return provided_type or "application/octet-stream"


async def fetch_resume_from_external_or_path(url_or_path: str) -> Optional[Tuple[bytes, str, str]]:
    """Fetches resume bytes from an external HTTP/HTTPS URL or local filesystem path."""
    raw = str(url_or_path or "").strip()
    if not raw or raw.lower() in ("none", "null", "undefined", ""):
        return None

    # 1. Local filesystem path check
    candidate_paths = [
        raw,
        raw.lstrip("/"),
        os.path.join(os.getcwd(), raw.lstrip("/")),
        os.path.join(os.getcwd(), "backend", raw.lstrip("/")),
        os.path.join(os.getcwd(), "uploads", raw.lstrip("/")),
        os.path.join(os.getcwd(), "backend", "uploads", raw.lstrip("/")),
    ]
    for cp in candidate_paths:
        try:
            if os.path.isfile(cp) and os.path.getsize(cp) > 0:
                with open(cp, "rb") as f:
                    content = f.read()
                filename = os.path.basename(cp)
                content_type = normalize_content_type(filename)
                return content, filename, content_type
        except Exception:
            pass

    # 2. External HTTP/HTTPS URL
    urls_to_try = []
    if raw.startswith("http://") or raw.startswith("https://"):
        urls_to_try.append(raw)
    else:
        # Relative path — try prefixing with official domain
        clean_rel = raw.lstrip("/")
        urls_to_try.append(f"https://leamss.com/{clean_rel}")
        if not clean_rel.startswith("public/"):
            urls_to_try.append(f"https://leamss.com/public/{clean_rel}")
        else:
            urls_to_try.append(f"https://leamss.com/{clean_rel[len('public/'):]}")

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; LEAMSS-CRM/3.0; +https://leamss.com)",
        "Accept": "*/*",
    }

    async with httpx.AsyncClient(timeout=20.0, verify=False, follow_redirects=True, headers=headers) as client:
        for u in urls_to_try:
            try:
                split = urlsplit(u)
                encoded_path = quote(unquote(split.path), safe="/:@!$&'()*+,;=-_.~")
                fetch_url = urlunsplit((split.scheme, split.netloc, encoded_path, split.query, split.fragment))

                resp = await client.get(fetch_url)
                if resp.status_code == 200 and len(resp.content) > 0:
                    raw_filename = unquote(split.path.split("/")[-1].split("?")[0]) or "candidate_resume.pdf"
                    content_type = normalize_content_type(raw_filename, resp.headers.get("content-type"))
                    return resp.content, raw_filename, content_type
            except Exception as e:
                logger.warning(f"Error fetching external resume from {u}: {e}")
                continue

    return None


async def save_resume_to_gridfs(
    filename: str,
    file_bytes: bytes,
    content_type: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Tuple[str, str]:
    """Store resume bytes in GridFS 'bulk_resumes' bucket.
    Returns (file_id_str, download_url).
    """
    if len(file_bytes) > MAX_RESUME_BYTES:
        raise ValueError("File exceeds maximum allowed size of 15 MB")

    clean_content_type = normalize_content_type(filename, content_type)
    meta = dict(metadata or {})
    meta["contentType"] = clean_content_type
    meta["uploaded_at"] = datetime.now(timezone.utc).isoformat()

    bucket = AsyncIOMotorGridFSBucket(db, bucket_name="bulk_resumes")
    file_id = await bucket.upload_from_stream(
        filename or "resume.pdf",
        io.BytesIO(file_bytes),
        metadata=meta,
    )
    file_id_str = str(file_id)
    download_url = f"/cockpit/resume/{file_id_str}"
    return file_id_str, download_url


async def get_resume_bytes_and_meta(file_ref: str) -> Optional[Dict[str, Any]]:
    """Retrieve resume bytes and metadata given a GridFS ObjectId string,
    lead ID, pre_assessment ID, case ID, client ID, or external URL.
    Searches across all candidate GridFS buckets and falls back to URL fetching and caching.
    """
    clean_ref = str(file_ref or "").strip()
    if not clean_ref:
        return None

    # Strip /cockpit/resume/ or /api/cockpit/resume/ prefix if provided
    clean_ref = clean_ref.replace("/api/cockpit/resume/", "").replace("/cockpit/resume/", "")

    target_oid: Optional[ObjectId] = None
    hex_match = re.search(r"[a-fA-F0-9]{24}", clean_ref)
    if hex_match:
        try:
            target_oid = ObjectId(hex_match.group(0))
        except Exception:
            target_oid = None

    matched_entity_type = None
    matched_entity_id = None
    matched_doc = None

    # If no direct ObjectId or if lookup by entity ID is required
    if not target_oid or not ObjectId.is_valid(clean_ref):
        # 1. Check Leads
        lead_query: Dict[str, Any] = {"$or": [
            {"id": clean_ref},
            {"unique_id": clean_ref},
            {"lead_number": clean_ref},
        ]}
        if ObjectId.is_valid(clean_ref):
            lead_query["$or"].append({"_id": ObjectId(clean_ref)})
        lead = await db["leads"].find_one(lead_query)
        if lead:
            matched_entity_type = "lead"
            matched_entity_id = lead.get("id") or str(lead.get("_id"))
            matched_doc = lead
            if lead.get("resume_file_id"):
                m = re.search(r"[a-fA-F0-9]{24}", str(lead["resume_file_id"]))
                if m:
                    target_oid = ObjectId(m.group(0))

    if not target_oid and not matched_doc:
        # 2. Check Pre-Assessments
        pa = await db["pre_assessments"].find_one(
            {"$or": [{"id": clean_ref}, {"pa_number": clean_ref}]}
        )
        if pa:
            matched_entity_type = "pre_assessment"
            matched_entity_id = pa.get("id")
            matched_doc = pa
            if pa.get("resume_file_id"):
                m = re.search(r"[a-fA-F0-9]{24}", str(pa["resume_file_id"]))
                if m:
                    target_oid = ObjectId(m.group(0))

    if not target_oid and not matched_doc:
        # 3. Check Cases
        case = await db["cases"].find_one(
            {"$or": [{"id": clean_ref}, {"case_id": clean_ref}]}
        )
        if case:
            matched_entity_type = "case"
            matched_entity_id = case.get("id")
            matched_doc = case
            if case.get("resume_file_id"):
                m = re.search(r"[a-fA-F0-9]{24}", str(case["resume_file_id"]))
                if m:
                    target_oid = ObjectId(m.group(0))

    if not target_oid and not matched_doc:
        # 4. Check Users (Client)
        user = await db["users"].find_one({"id": clean_ref})
        if user:
            matched_entity_type = "user"
            matched_entity_id = user.get("id")
            matched_doc = user
            if user.get("resume_file_id"):
                m = re.search(r"[a-fA-F0-9]{24}", str(user["resume_file_id"]))
                if m:
                    target_oid = ObjectId(m.group(0))

    # Search across GridFS buckets if target_oid found
    grid_out = None
    if target_oid:
        for b_name in RESUME_BUCKETS:
            try:
                gfs = AsyncIOMotorGridFSBucket(db, bucket_name=b_name)
                grid_out = await gfs.open_download_stream(target_oid)
                if grid_out:
                    break
            except Exception:
                continue

    # If GridFS stream succeeded, return it
    if grid_out:
        raw_bytes = await grid_out.read()
        filename = grid_out.filename or f"resume_{target_oid}.pdf"
        content_type = normalize_content_type(
            filename, (grid_out.metadata or {}).get("contentType")
        )
        return {
            "filename": filename,
            "bytes": raw_bytes,
            "content_type": content_type,
            "file_id": str(target_oid),
            "length": len(raw_bytes),
            "url": f"/cockpit/resume/{target_oid}",
        }

    # If GridFS stream was not found, fallback to candidate URL/path from matched doc or clean_ref
    candidate_url = None
    if matched_doc:
        candidate_url = (
            matched_doc.get("resume_url")
            or matched_doc.get("resume_path")
            or matched_doc.get("resume_link")
            or matched_doc.get("resume")
        )
    elif clean_ref.startswith("http://") or clean_ref.startswith("https://") or "uploads/resumes" in clean_ref:
        candidate_url = clean_ref

    if candidate_url:
        fetched = await fetch_resume_from_external_or_path(candidate_url)
        if fetched:
            raw_bytes, fname, ctype = fetched
            # Cache permanently into GridFS bucket
            try:
                new_fid, download_url = await save_resume_to_gridfs(
                    filename=fname,
                    file_bytes=raw_bytes,
                    content_type=ctype,
                    metadata={
                        "source": "auto_cached_from_url",
                        "original_url": candidate_url,
                        "entity_id": matched_entity_id,
                        "entity_type": matched_entity_type,
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to cache resume to GridFS: {e}")
                new_fid = clean_ref
                download_url = f"/cockpit/resume/{clean_ref}"

            # Update MongoDB record so subsequent requests are fast GridFS hits
            if matched_entity_type == "lead" and matched_entity_id:
                await db["leads"].update_one(
                    {"$or": [{"id": matched_entity_id}, {"lead_number": matched_entity_id}]},
                    {"$set": {
                        "resume_file_id": new_fid,
                        "resume_filename": fname,
                        "resume_uploaded": True,
                        "resume_url": download_url,
                    }}
                )
            elif matched_entity_type == "pre_assessment" and matched_entity_id:
                await db["pre_assessments"].update_one(
                    {"id": matched_entity_id},
                    {"$set": {
                        "resume_file_id": new_fid,
                        "resume_filename": fname,
                        "resume_uploaded": True,
                        "resume_url": download_url,
                    }}
                )

            return {
                "filename": fname,
                "bytes": raw_bytes,
                "content_type": ctype,
                "file_id": str(new_fid),
                "length": len(raw_bytes),
                "url": download_url,
            }

    logger.warning("Could not resolve resume reference: %s", clean_ref)
    return None


async def attach_and_sync_resume(
    lead_id: str,
    file_id_str: str,
    filename: str,
    file_bytes: Optional[bytes] = None,
    uploaded_by: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Attach resume to a lead and cascade updates across:
    1. leads collection
    2. sales_assessments collection
    3. pre_assessments collection & pre_assessment_documents
    4. users collection (if converted client exists)
    5. cases collection & documents (if case exists)
    """
    now = datetime.now(timezone.utc)
    resume_url = f"/cockpit/resume/{file_id_str}"

    lead_query = {"$or": [{"id": lead_id}, {"lead_number": lead_id}, {"unique_id": lead_id}]}
    if ObjectId.is_valid(lead_id):
        lead_query["$or"].append({"_id": ObjectId(lead_id)})

    lead = await db["leads"].find_one(lead_query)
    
    # If not found directly in leads, check if lead_id is a pre-assessment ID
    target_pa = None
    target_user = None
    if not lead:
        target_pa = await db["pre_assessments"].find_one({"$or": [{"id": lead_id}, {"pa_number": lead_id}]})
        if target_pa and target_pa.get("lead_id"):
            lead = await db["leads"].find_one({"$or": [{"id": target_pa["lead_id"]}] + ([{"_id": ObjectId(target_pa["lead_id"])}] if ObjectId.is_valid(target_pa["lead_id"]) else [])})
        if not lead:
            target_user = await db["users"].find_one({"id": lead_id})
            if target_user and target_user.get("original_lead_id"):
                orig_id = target_user["original_lead_id"]
                lead = await db["leads"].find_one({"$or": [{"id": orig_id}] + ([{"_id": ObjectId(orig_id)}] if ObjectId.is_valid(orig_id) else [])})

    if not lead and not target_pa and not target_user:
        raise ValueError(f"Lead record not found for {lead_id}")

    client_email = ((lead.get("email") if lead else None) or (target_pa.get("client_email") if target_pa else None) or (target_user.get("email") if target_user else None) or "").strip().lower()
    client_phone = ((lead.get("phone") if lead else None) or (target_pa.get("client_mobile") if target_pa else None) or (target_user.get("phone") if target_user else None) or "").strip()
    client_name = ((lead.get("name") if lead else None) or (target_pa.get("client_name") if target_pa else None) or (target_user.get("name") if target_user else None) or "").strip()

    # Clean phone digits for robust regex matching across formats (+91, spaces, dashes)
    clean_digits = re.sub(r"[^\d]", "", client_phone)
    phone_10 = clean_digits[-10:] if len(clean_digits) >= 10 else clean_digits if len(clean_digits) >= 7 else None

    # Optional Smart Text Extraction to enrich lead qualifications if missing
    extracted_qualification = None
    extracted_experience = None
    if file_bytes:
        try:
            from core.resume_extractor import extract_text_smart
            extracted_text, _ = await extract_text_smart(filename, file_bytes)
            if extracted_text:
                from core.resume_extractor import parse_education_blocks, parse_experience_blocks
                ed_blocks = parse_education_blocks(extracted_text)
                if ed_blocks and lead and not lead.get("latest_qualification"):
                    extracted_qualification = ed_blocks[0].get("degree") if isinstance(ed_blocks[0], dict) else str(ed_blocks[0])
                exp_blocks = parse_experience_blocks(extracted_text)
                if exp_blocks and lead and not lead.get("total_work_experience"):
                    extracted_experience = f"{len(exp_blocks)} roles listed"
        except Exception as e:
            logger.warning("Optional smart resume text extraction skipped: %s", e)

    # 1. Update Lead (if lead found)
    update_fields: Dict[str, Any] = {
        "resume_file_id": file_id_str,
        "resume_filename": filename,
        "resume_url": resume_url,
        "resume_path": resume_url,
        "resume_uploaded": True,
        "resume_uploaded_at": now.isoformat(),
        "updated_at": now,
    }
    if lead:
        if extracted_qualification and not lead.get("latest_qualification"):
            update_fields["latest_qualification"] = extracted_qualification
        if extracted_experience and not lead.get("total_work_experience"):
            update_fields["total_work_experience"] = extracted_experience

        actual_lead_id = lead.get("id") or str(lead.get("_id"))
        leads_sync_q: List[Dict[str, Any]] = [{"id": actual_lead_id}, {"id": lead_id}]
        if lead.get("_id"):
            leads_sync_q.append({"_id": lead["_id"]})
        if lead.get("lead_number"):
            leads_sync_q.append({"lead_number": lead["lead_number"]})
        if lead.get("unique_id"):
            leads_sync_q.append({"unique_id": lead["unique_id"]})
        if client_email and "@" in client_email:
            leads_sync_q.append({"email": {"$regex": f"^{re.escape(client_email)}$", "$options": "i"}})
        if phone_10:
            leads_sync_q.extend([
                {"phone": {"$regex": re.escape(phone_10)}},
                {"whatsapp_number": {"$regex": re.escape(phone_10)}},
                {"alternate_phone": {"$regex": re.escape(phone_10)}},
                {"mobile": {"$regex": re.escape(phone_10)}},
            ])
        if client_name and len(client_name) >= 4 and client_name.lower() not in ("applicant", "unknown", "lead", "client"):
            leads_sync_q.append({"name": {"$regex": f"^{re.escape(client_name)}$", "$options": "i"}})

        await db["leads"].update_many({"$or": leads_sync_q}, {"$set": update_fields})
        
        timeline_entry = {
            "id": str(uuid.uuid4()),
            "lead_id": actual_lead_id,
            "action": "resume_uploaded",
            "activity_type": "resume_uploaded",
            "type": "resume_uploaded",
            "title": f"Resume Attached ({filename})",
            "description": f"Resume '{filename}' received and attached to lead record.",
            "user_id": (uploaded_by or {}).get("id") or "client",
            "user_name": (uploaded_by or {}).get("name") or client_name or "Applicant",
            "timestamp": now.isoformat(),
            "created_at": now.isoformat(),
        }
        await db["leads"].update_many({"$or": leads_sync_q}, {"$push": {"timeline": timeline_entry}})
    else:
        actual_lead_id = lead_id

    # 2. Cascade to Sales Assessments & CRM Deals
    match_targets: List[Dict[str, Any]] = [{"lead_id": lead_id}, {"lead_id": actual_lead_id}]
    if target_pa:
        match_targets.append({"id": target_pa.get("id")})
    if target_user:
        match_targets.append({"id": target_user.get("id")})
    if client_email:
        match_targets.extend([
            {"client_email": {"$regex": f"^{re.escape(client_email)}$", "$options": "i"}},
            {"email": {"$regex": f"^{re.escape(client_email)}$", "$options": "i"}},
        ])
    if phone_10:
        match_targets.extend([
            {"client_phone": {"$regex": re.escape(phone_10)}},
            {"phone": {"$regex": re.escape(phone_10)}},
            {"mobile": {"$regex": re.escape(phone_10)}},
        ])
    if client_name and len(client_name) >= 4 and client_name.lower() not in ("applicant", "unknown", "lead", "client"):
        match_targets.extend([
            {"client_name": {"$regex": f"^{re.escape(client_name)}$", "$options": "i"}},
            {"name": {"$regex": f"^{re.escape(client_name)}$", "$options": "i"}},
        ])

    await db["sales_assessments"].update_many(
        {"$or": match_targets},
        {"$set": {
            "resume_file_id": file_id_str,
            "resume_filename": filename,
            "resume_url": resume_url,
            "resume_uploaded": True,
            "resume_uploaded_at": now.isoformat(),
            "profile_snapshot.resume_file_id": file_id_str,
            "profile_snapshot.resume_filename": filename,
            "profile_snapshot.primary_applicant.resume_file_id": file_id_str,
            "profile_snapshot.primary_applicant.resume_filename": filename,
            "updated_at": now,
        }}
    )
    await db["crm_deals"].update_many(
        {"$or": [{"lead_id": actual_lead_id}, {"lead_id": lead_id}] + ([{"client_email": client_email}] if client_email else [])},
        {"$set": {
            "resume_file_id": file_id_str,
            "resume_filename": filename,
            "resume_url": resume_url,
            "updated_at": now,
        }}
    )

    # 3. Cascade to Pre-Assessments & insert into pre_assessment_documents
    await db["pre_assessments"].update_many(
        {"$or": match_targets},
        {"$set": {
            "resume_file_id": file_id_str,
            "resume_filename": filename,
            "resume_url": resume_url,
            "resume_path": resume_url,
            "resume_uploaded": True,
            "resume_uploaded_at": now.isoformat(),
            "updated_at": now,
        }}
    )
    # Add pre_assessment_document for any matched pre_assessment
    matched_pas = await db["pre_assessments"].find({"$or": match_targets}, {"_id": 0, "id": 1}).to_list(100)
    for pa in matched_pas:
        pa_id = pa["id"]
        existing_doc = await db["pre_assessment_documents"].find_one({
            "pre_assessment_id": pa_id,
            "doc_type": "resume",
            "file_url": resume_url,
        })
        if not existing_doc:
            await db["pre_assessment_documents"].insert_one({
                "id": str(uuid.uuid4()),
                "pre_assessment_id": pa_id,
                "name": filename,
                "doc_type": "resume",
                "file_url": resume_url,
                "file_id": file_id_str,
                "status": "uploaded",
                "uploaded_at": now,
            })

    # 4. Cascade to Converted Client in Users collection
    user_match = [{"original_lead_id": lead_id}]
    if client_email:
        user_match.append({"email": client_email})
    await db["users"].update_many(
        {"$or": user_match},
        {"$set": {
            "resume_file_id": file_id_str,
            "resume_filename": filename,
            "resume_url": resume_url,
            "resume_path": resume_url,
            "resume_uploaded": True,
            "resume_uploaded_at": now.isoformat(),
            "updated_at": now,
        }}
    )

    # 5. Cascade to Cases collection & insert into documents
    case_match = [{"lead_id": lead_id}]
    if client_email:
        case_match.append({"client_email": client_email})
    await db["cases"].update_many(
        {"$or": case_match},
        {"$set": {
            "resume_file_id": file_id_str,
            "resume_filename": filename,
            "resume_url": resume_url,
            "resume_path": resume_url,
            "resume_uploaded": True,
            "updated_at": now,
        }}
    )
    matched_cases = await db["cases"].find({"$or": case_match}, {"_id": 0, "id": 1, "case_id": 1, "client_id": 1}).to_list(100)
    for c in matched_cases:
        c_id = c.get("id") or c.get("case_id")
        existing_doc = await db["documents"].find_one({
            "case_id": c_id,
            "doc_type": "resume",
            "file_url": resume_url,
        })
        if not existing_doc:
            await db["documents"].insert_one({
                "id": str(uuid.uuid4()),
                "case_id": c_id,
                "client_id": c.get("client_id"),
                "name": filename,
                "category": "Professional",
                "doc_type": "resume",
                "file_url": resume_url,
                "file_id": file_id_str,
                "status": "approved",
                "uploaded_at": now.isoformat(),
                "created_at": now,
                "updated_at": now,
            })

    actor_id = (uploaded_by or {}).get("id") or "system"
    actor_name = (uploaded_by or {}).get("name") or "CRM Salesperson"
    try:
        from core.services import log_activity
        await log_activity(
            user_id=actor_id,
            user_name=actor_name,
            action="resume_uploaded",
            entity_type="lead",
            entity_id=lead_id,
            details=f"Resume '{filename}' uploaded (file_id={file_id_str}) and attached to lead {lead.get('name')}",
            new_value=filename,
        )
    except Exception as e:
        logger.warning("Could not log activity for resume upload: %s", e)

    return {
        "ok": True,
        "lead_id": lead_id,
        "resume_file_id": file_id_str,
        "resume_filename": filename,
        "resume_url": resume_url,
        "resume_uploaded": True,
    }
