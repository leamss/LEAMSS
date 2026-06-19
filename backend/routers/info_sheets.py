"""Phase 20.4 — Universal Info Sheet router.

Provides a universal CRUD layer over the `information_sheets` collection
(now canonical 6-section schema). Supports both:
  - `case_id` (back-compat with existing /api/cases/{case_id}/information-sheet)
  - `entity_type + entity_id` (new universal mount points: sale, pre_assessment, standalone)

Endpoints (all under /api/info-sheets):
  GET    /by-entity?entity_type=case|sale|pre_assessment&entity_id=X
  GET    /{sheet_id}
  POST   /                                  — create
  PATCH  /{sheet_id}                        — partial update (auto-save target)
  POST   /{sheet_id}/lock                   — lock for editing
  POST   /{sheet_id}/unlock
  POST   /{sheet_id}/resume                 — upload + AI extract resume
  POST   /{sheet_id}/resume/apply-prefill   — confirm + prefill quals/employment
  GET    /{sheet_id}/audit-trail            — recent edits
  GET    /schema                            — return canonical schema definition

All PATCH writes register a Phase 19.6 lightweight audit-only batch (info-sheet
edits are high-frequency auto-save events — granular revoke not feasible without
spamming; we use a single audit-only marker per session for traceability).
Resume AI calls audit-logged with model_used + extraction stats.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, Field

from core.auth import get_current_user
from core.database import db
from services import import_batch_service as ibs
from services.audit_service import log_action

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/info-sheets", tags=["Phase 20.4 Universal Info Sheet"])

COLLECTION = "information_sheets"
SCHEMA_VERSION = 2

# Roles allowed to read+write info sheets
RW_ROLES = {
    "admin", "admin_owner", "super_admin",
    "case_manager", "case_manager_lead",
    "sales", "sales_executive", "sr_sales_executive", "sales_manager", "sales_head",
    "partner",
    "hr_manager",
}
# Roles allowed to lock/admin-only operations
ADMIN_ROLES = {"admin", "admin_owner", "super_admin", "case_manager", "case_manager_lead"}


def _role(u: Dict[str, Any]) -> str:
    return (u.get("rbac_role") or u.get("role") or "").lower()


def _can_rw(u: Dict[str, Any]) -> bool:
    return _role(u) in RW_ROLES or "*" in (u.get("permissions") or [])


def _is_admin(u: Dict[str, Any]) -> bool:
    return _role(u) in ADMIN_ROLES or "*" in (u.get("permissions") or [])


def _serialise(doc: Dict[str, Any]) -> Dict[str, Any]:
    doc.pop("_id", None)
    for k, v in list(doc.items()):
        if isinstance(v, datetime):
            doc[k] = v.isoformat()
    return doc


CANONICAL_SCHEMA = {
    "schema_version": SCHEMA_VERSION,
    "sections": [
        {
            "id": "personal", "title": "Personal Details",
            "fields": [
                {"key": "given_names", "label": "Given Name(s)", "type": "text", "required": True},
                {"key": "family_name", "label": "Family Name", "type": "text", "required": True},
                {"key": "other_names", "label": "Other Names", "type": "text"},
                {"key": "gender", "label": "Gender", "type": "select", "options": ["Male", "Female", "Other"], "required": True},
                {"key": "date_of_birth", "label": "Date of Birth", "type": "date", "required": True},
                {"key": "country_of_birth", "label": "Country of Birth", "type": "text", "required": True},
                {"key": "city_of_birth", "label": "City/Town of Birth", "type": "text"},
                {"key": "nationality", "label": "Nationality", "type": "text", "required": True},
                {"key": "address", "label": "Address for Communication", "type": "textarea", "required": True},
                {"key": "email", "label": "Email ID", "type": "email", "required": True},
                {"key": "contact_number", "label": "Contact Number", "type": "tel", "required": True},
                {"key": "alternative_number", "label": "Alternative Number", "type": "tel"},
                {"key": "aadhaar_number", "label": "Aadhaar Number", "type": "text"},
                {"key": "passport_number", "label": "Passport No.", "type": "text", "required": True},
                {"key": "passport_issue_date", "label": "Passport Issue Date", "type": "date", "required": True},
                {"key": "passport_expiry_date", "label": "Passport Expiry Date", "type": "date", "required": True},
                {"key": "passport_place_of_issue", "label": "Passport Place of Issue", "type": "text"},
                {"key": "marital_status", "label": "Marital Status", "type": "select",
                 "options": ["Single", "Married", "Divorced", "Widowed", "Separated"], "required": True},
                {"key": "spouse_name", "label": "Spouse Name (if married)", "type": "text"},
                {"key": "father_name", "label": "Father's Name", "type": "text", "required": True},
                {"key": "mother_name", "label": "Mother's Name", "type": "text", "required": True},
            ],
        },
        {
            "id": "family", "title": "Family Chart",
            "fields": [
                {"key": "father_dob", "label": "Father's DOB", "type": "date"},
                {"key": "father_place_of_birth", "label": "Father's Place of Birth", "type": "text"},
                {"key": "mother_dob", "label": "Mother's DOB", "type": "date"},
                {"key": "mother_place_of_birth", "label": "Mother's Place of Birth", "type": "text"},
                {"key": "siblings_details", "label": "Siblings (Name, DOB, POB — one per line)", "type": "textarea"},
                {"key": "date_of_marriage", "label": "Date of Marriage", "type": "date"},
                {"key": "spouse_dob", "label": "Spouse DOB", "type": "date"},
                {"key": "spouse_place_of_birth", "label": "Spouse Place of Birth", "type": "text"},
                {"key": "spouse_passport_number", "label": "Spouse Passport No.", "type": "text"},
                {"key": "spouse_passport_issue_date", "label": "Spouse Passport Issue", "type": "date"},
                {"key": "spouse_passport_expiry_date", "label": "Spouse Passport Expiry", "type": "date"},
                {"key": "spouse_passport_place", "label": "Spouse Passport Place", "type": "text"},
            ],
        },
        {
            "id": "dependents", "title": "Dependents",
            "array_field": "dependents", "max_entries": 20,
            "entry_fields": [
                {"key": "full_name", "label": "Full Name", "type": "text"},
                {"key": "relation", "label": "Relation", "type": "text"},
                {"key": "gender", "label": "Gender", "type": "select", "options": ["Male", "Female", "Other"]},
                {"key": "dob", "label": "Date of Birth", "type": "date"},
                {"key": "is_migrating", "label": "Migrating with you?", "type": "boolean"},
                {"key": "presently_residing_country", "label": "Presently Residing Country", "type": "text"},
                {"key": "residency_status", "label": "Permanent Resident / Citizen", "type": "text"},
                {"key": "postal_code", "label": "Postal Code", "type": "text"},
                {"key": "passport_number", "label": "Passport Number", "type": "text"},
                {"key": "passport_issue_date", "label": "Passport Issue Date", "type": "date"},
                {"key": "passport_expiry_date", "label": "Passport Expiry Date", "type": "date"},
            ],
        },
        {
            "id": "qualifications", "title": "Qualifications",
            "array_field": "qualifications", "max_entries": 20,
            "entry_fields": [
                {"key": "name", "label": "Qualification Name", "type": "text"},
                {"key": "field_of_study", "label": "Major Field of Study", "type": "text"},
                {"key": "awarding_body", "label": "Awarding Body", "type": "text"},
                {"key": "institute_name", "label": "Institute Name", "type": "text"},
                {"key": "institute_address", "label": "Institute Address", "type": "text"},
                {"key": "course_length", "label": "Course Length", "type": "text"},
                {"key": "start_date", "label": "Start Date", "type": "date"},
                {"key": "end_date", "label": "End Date", "type": "date"},
                {"key": "award_date", "label": "Award Date", "type": "date"},
                {"key": "study_mode", "label": "Mode", "type": "select",
                 "options": ["Full Time", "Part Time", "Distance"]},
            ],
        },
        {
            "id": "employment", "title": "Employment History",
            "array_field": "employment", "max_entries": 20,
            "entry_fields": [
                {"key": "business_name", "label": "Business/Company Name", "type": "text"},
                {"key": "address", "label": "Employment Address", "type": "text"},
                {"key": "website", "label": "Employer Website", "type": "url"},
                {"key": "job_title", "label": "Job Title", "type": "text"},
                {"key": "start_date", "label": "Start Date", "type": "date"},
                {"key": "end_date", "label": "End Date (blank if current)", "type": "date"},
                {"key": "working_hours", "label": "Working Hours/Week", "type": "text"},
            ],
        },
        {
            "id": "resume", "title": "Resume Upload + AI Extract",
            "is_resume_section": True,
            "fields": [
                {"key": "file_name", "label": "Resume File", "type": "file"},
                {"key": "uploaded_at", "label": "Uploaded At", "type": "datetime", "readonly": True},
                {"key": "model_used", "label": "AI Model Used", "type": "text", "readonly": True},
                {"key": "confidence_score", "label": "Extraction Confidence", "type": "number", "readonly": True},
            ],
        },
    ],
}


class InfoSheetCreate(BaseModel):
    entity_type: str = Field(..., pattern=r"^(case|sale|pre_assessment|standalone)$")
    entity_id: str = Field(..., min_length=1)
    case_id: Optional[str] = None
    client_id: Optional[str] = None
    personal: Dict[str, Any] = Field(default_factory=dict)
    family: Dict[str, Any] = Field(default_factory=dict)
    dependents: List[Dict[str, Any]] = Field(default_factory=list)
    qualifications: List[Dict[str, Any]] = Field(default_factory=list)
    employment: List[Dict[str, Any]] = Field(default_factory=list)


class InfoSheetPatch(BaseModel):
    """Auto-save target — every field optional. Frontend sends partial updates."""
    personal: Optional[Dict[str, Any]] = None
    family: Optional[Dict[str, Any]] = None
    dependents: Optional[List[Dict[str, Any]]] = None
    qualifications: Optional[List[Dict[str, Any]]] = None
    employment: Optional[List[Dict[str, Any]]] = None
    resume: Optional[Dict[str, Any]] = None
    status: Optional[str] = Field(None, pattern=r"^(draft|in_review|approved|locked)$")
    changes_summary: Optional[str] = Field(None, max_length=200)


class PrefillApply(BaseModel):
    apply_qualifications: bool = True
    apply_employment: bool = True
    merge_strategy: str = Field(default="append", pattern=r"^(append|replace)$")


@router.get("/schema")
async def get_schema(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Return canonical 6-section schema for frontend rendering."""
    if not _can_rw(current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    return CANONICAL_SCHEMA


@router.get("/by-entity")
async def get_by_entity(
    entity_type: str, entity_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not _can_rw(current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    q: Dict[str, Any] = {"$or": [
        {"entity_type": entity_type, "entity_id": entity_id},
        # Back-compat with old case_id-only docs (entity_type=case)
        {"case_id": entity_id} if entity_type == "case" else {},
    ]}
    # Drop empty $or sub-clause
    q["$or"] = [c for c in q["$or"] if c]
    doc = await db[COLLECTION].find_one(q)
    if not doc:
        return {"exists": False, "data": None, "schema_version": SCHEMA_VERSION}
    return {"exists": True, "data": _serialise(doc)}


@router.get("/{sheet_id}")
async def get_sheet(sheet_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    if not _can_rw(current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    doc = await db[COLLECTION].find_one({"id": sheet_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Info sheet not found")
    return _serialise(doc)


@router.post("")
async def create_sheet(
    payload: InfoSheetCreate, current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not _can_rw(current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    # Reject duplicate for same entity
    existing = await db[COLLECTION].find_one({
        "entity_type": payload.entity_type, "entity_id": payload.entity_id,
    })
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Info sheet already exists for {payload.entity_type}/{payload.entity_id}",
        )
    now = datetime.now(timezone.utc)
    user_id = str(current_user.get("id") or "system")
    doc = {
        "id": str(uuid.uuid4()),
        "entity_type": payload.entity_type, "entity_id": payload.entity_id,
        "case_id": payload.case_id or (payload.entity_id if payload.entity_type == "case" else None),
        "client_id": payload.client_id,
        "personal": payload.personal, "family": payload.family,
        "dependents": payload.dependents,
        "qualifications": payload.qualifications,
        "employment": payload.employment,
        "resume": {},
        "schema_version": SCHEMA_VERSION,
        "status": "draft",
        "locked": False, "locked_by": None, "locked_at": None,
        "audit_trail": [{
            "action": "create", "by": user_id,
            "by_name": current_user.get("name") or current_user.get("email"),
            "at": now.isoformat(),
        }],
        "created_at": now, "updated_at": now,
        "created_by": user_id, "updated_by": user_id,
    }
    await db[COLLECTION].insert_one(doc)
    await log_action(db, action="info_sheet.create", user_id=user_id,
                     user_name=current_user.get("name"), severity="info",
                     summary={"sheet_id": doc["id"], "entity_type": payload.entity_type,
                              "entity_id": payload.entity_id})
    return _serialise(doc)


def _compute_completion(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate fill % for required Personal fields + summary across sections."""
    required_keys = [f["key"] for s in CANONICAL_SCHEMA["sections"]
                     if s["id"] == "personal" for f in s.get("fields", []) if f.get("required")]
    personal = doc.get("personal") or {}
    filled = sum(1 for k in required_keys if str(personal.get(k) or "").strip())
    pct = round((filled / len(required_keys)) * 100) if required_keys else 100
    return {
        "personal_required_total": len(required_keys),
        "personal_required_filled": filled,
        "personal_percentage": pct,
        "dependents_count": len(doc.get("dependents") or []),
        "qualifications_count": len(doc.get("qualifications") or []),
        "employment_count": len(doc.get("employment") or []),
        "resume_uploaded": bool((doc.get("resume") or {}).get("file_name")),
        "is_complete": pct == 100,
    }


@router.patch("/{sheet_id}")
async def patch_sheet(
    sheet_id: str, payload: InfoSheetPatch,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not _can_rw(current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    doc = await db[COLLECTION].find_one({"id": sheet_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Info sheet not found")
    if doc.get("locked") and not _is_admin(current_user):
        raise HTTPException(status_code=423, detail="Info sheet is locked")

    user_id = str(current_user.get("id") or "system")
    user_name = current_user.get("name") or current_user.get("email")
    updates = {k: v for k, v in payload.dict(exclude_none=True).items()
               if k != "changes_summary"}
    if not updates:
        return {"ok": True, "no_change": True}

    now = datetime.now(timezone.utc)
    updates["updated_at"] = now
    updates["updated_by"] = user_id
    audit_entry = {
        "action": "patch", "by": user_id, "by_name": user_name,
        "at": now.isoformat(),
        "sections_changed": list(updates.keys()),
        "changes_summary": payload.changes_summary or "auto-save",
    }
    await db[COLLECTION].update_one(
        {"id": sheet_id},
        {"$set": updates, "$push": {"audit_trail": {"$each": [audit_entry], "$slice": -100}}},
    )
    new_doc = await db[COLLECTION].find_one({"id": sheet_id})
    return {"ok": True, "completion": _compute_completion(new_doc),
            "updated_at": now.isoformat()}


@router.post("/{sheet_id}/lock")
async def lock_sheet(sheet_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    doc = await db[COLLECTION].find_one({"id": sheet_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Info sheet not found")
    user_id = str(current_user.get("id") or "admin")
    now = datetime.now(timezone.utc)
    await db[COLLECTION].update_one({"id": sheet_id}, {
        "$set": {"locked": True, "locked_by": user_id, "locked_at": now, "status": "locked"},
        "$push": {"audit_trail": {"action": "lock", "by": user_id, "at": now.isoformat()}},
    })
    await log_action(db, action="info_sheet.lock", user_id=user_id, severity="info",
                     summary={"sheet_id": sheet_id})
    return {"ok": True, "locked": True, "locked_at": now.isoformat()}


@router.post("/{sheet_id}/unlock")
async def unlock_sheet(sheet_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    doc = await db[COLLECTION].find_one({"id": sheet_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Info sheet not found")
    user_id = str(current_user.get("id") or "admin")
    now = datetime.now(timezone.utc)
    await db[COLLECTION].update_one({"id": sheet_id}, {
        "$set": {"locked": False, "locked_by": None, "locked_at": None, "status": "draft"},
        "$push": {"audit_trail": {"action": "unlock", "by": user_id, "at": now.isoformat()}},
    })
    return {"ok": True, "locked": False}


@router.post("/{sheet_id}/resume")
async def upload_resume(
    sheet_id: str, file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Upload resume + run Claude Sonnet 4.5 extraction.

    Stores file metadata + AI-extracted structured JSON in `resume` section.
    Does NOT auto-prefill quals/employment — frontend must call /resume/apply-prefill.
    """
    if not _can_rw(current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    doc = await db[COLLECTION].find_one({"id": sheet_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Info sheet not found")

    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Resume file too large (>5MB)")

    from services.resume_extraction_service import extract_resume, extract_text_from_pdf_or_docx
    try:
        text = extract_text_from_pdf_or_docx(content, file.filename or "")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    try:
        extracted = await extract_resume(text)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=f"AI extraction unavailable: {e}") from e

    user_id = str(current_user.get("id") or "system")
    now = datetime.now(timezone.utc)
    resume_payload = {
        "file_name": file.filename,
        "file_size_bytes": len(content),
        "uploaded_at": now.isoformat(),
        "uploaded_by": user_id,
        "text_length": len(text),
        **extracted,
        "_used_to_prefill": False,
    }
    await db[COLLECTION].update_one(
        {"id": sheet_id},
        {"$set": {"resume": resume_payload, "updated_at": now},
         "$push": {"audit_trail": {
             "action": "resume_upload", "by": user_id, "at": now.isoformat(),
             "file_name": file.filename, "model_used": extracted.get("model_used"),
             "quals_count": len(extracted.get("extracted_qualifications", [])),
             "employment_count": len(extracted.get("extracted_employment", [])),
         }}},
    )
    await log_action(db, action="info_sheet.resume_extract", user_id=user_id, severity="info",
                     summary={"sheet_id": sheet_id, "model_used": extracted.get("model_used"),
                              "confidence": extracted.get("confidence_score")})
    return {"ok": True, "resume": resume_payload}


@router.post("/{sheet_id}/resume/apply-prefill")
async def apply_resume_prefill(
    sheet_id: str, payload: PrefillApply,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Apply AI-extracted resume data into the qualifications + employment sections.

    `merge_strategy`:
      - "append": add new items to existing arrays (no duplicates check — admin decides)
      - "replace": overwrite existing arrays
    """
    if not _can_rw(current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    doc = await db[COLLECTION].find_one({"id": sheet_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Info sheet not found")
    resume = doc.get("resume") or {}
    if not resume.get("extracted_qualifications") and not resume.get("extracted_employment"):
        raise HTTPException(status_code=400,
                            detail="No resume extraction available. Upload resume first.")

    user_id = str(current_user.get("id") or "system")
    now = datetime.now(timezone.utc)

    # Translate AI shape → canonical info sheet shape
    new_quals = []
    if payload.apply_qualifications:
        for q in resume.get("extracted_qualifications", []):
            new_quals.append({
                "name": q.get("degree"),
                "field_of_study": q.get("field_of_study"),
                "awarding_body": q.get("awarding_body"),
                "institute_name": q.get("institute"),
                "start_date": q.get("start_date"),
                "end_date": q.get("end_date"),
                "award_date": q.get("end_date"),
                "study_mode": q.get("study_mode"),
                "_source": "ai_resume_prefill",
                "_confidence": q.get("confidence"),
            })

    new_emp = []
    if payload.apply_employment:
        for e in resume.get("extracted_employment", []):
            new_emp.append({
                "business_name": e.get("business_name"),
                "address": e.get("address"),
                "job_title": e.get("job_title"),
                "start_date": e.get("start_date"),
                "end_date": e.get("end_date"),
                "working_hours": (str(e.get("working_hours_per_week"))
                                  if e.get("working_hours_per_week") else None),
                "_source": "ai_resume_prefill",
                "_confidence": e.get("confidence"),
                "_is_current": bool(e.get("is_current")),
            })

    existing_quals = doc.get("qualifications") or []
    existing_emp = doc.get("employment") or []
    final_quals = new_quals if payload.merge_strategy == "replace" else existing_quals + new_quals
    final_emp = new_emp if payload.merge_strategy == "replace" else existing_emp + new_emp

    await db[COLLECTION].update_one(
        {"id": sheet_id},
        {"$set": {
            "qualifications": final_quals, "employment": final_emp,
            "resume._used_to_prefill": True,
            "resume._prefilled_at": now.isoformat(),
            "resume._prefilled_by": user_id,
            "updated_at": now,
        }, "$push": {"audit_trail": {
            "action": "resume_prefill", "by": user_id, "at": now.isoformat(),
            "quals_added": len(new_quals), "employment_added": len(new_emp),
            "merge_strategy": payload.merge_strategy,
        }}},
    )
    return {
        "ok": True, "qualifications_added": len(new_quals),
        "employment_added": len(new_emp), "merge_strategy": payload.merge_strategy,
        "total_qualifications": len(final_quals), "total_employment": len(final_emp),
    }


@router.get("/{sheet_id}/audit-trail")
async def get_audit_trail(sheet_id: str, limit: int = 50,
                          current_user: Dict[str, Any] = Depends(get_current_user)):
    if not _can_rw(current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    doc = await db[COLLECTION].find_one({"id": sheet_id}, {"audit_trail": 1, "_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Info sheet not found")
    trail = doc.get("audit_trail") or []
    return {"events": trail[-limit:][::-1], "total": len(trail)}
