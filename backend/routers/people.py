"""Phase 4D — Unified People Management.

ONE place for all user/vendor lifecycle: internal employees, external partners,
internal vendors (CM/sales auto-created from vendor master), external vendors.

This router does NOT create a third source of truth — it stitches the existing
`users` and `vendors` collections together with a unified API surface.

Endpoints:
  GET    /api/people                          — unified list with filters
  GET    /api/people/{id}                     — full profile (user-side + linked vendor-side)
  POST   /api/people                          — Add Person wizard (smart routing by person_type)
  PATCH  /api/people/{id}                     — update role, permissions, status
  POST   /api/people/{id}/deactivate          — soft-disable
  POST   /api/people/{id}/reactivate
  POST   /api/people/{id}/reset-password      — admin force reset (sets temp password)
  GET    /api/people/stats                    — counts by type/role/status
"""
import uuid
import secrets
import os
import mimetypes
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import FileResponse

from core.auth import get_current_user, get_password_hash, validate_password_strength
from core.database import db, users_col

router = APIRouter(prefix="/people", tags=["Phase 4D - Unified People Management"])

vendors_col = db["vendors"]

# Phase 4D+ — Onboarding document storage
ONBOARDING_DIR = Path("/app/uploads/people_documents")
ONBOARDING_DIR.mkdir(parents=True, exist_ok=True)
MAX_DOC_SIZE = 10 * 1024 * 1024  # 10 MB per document
ALLOWED_DOC_MIME = {
    "application/pdf", "image/jpeg", "image/jpg", "image/png", "image/webp",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
# Recommended document checklist per person type — used by frontend to show required items
RECOMMENDED_DOCS = {
    "employee_internal": [
        {"key": "pan_card", "label": "PAN Card", "required": True},
        {"key": "aadhaar_card", "label": "Aadhaar Card", "required": True},
        {"key": "resume", "label": "Resume / CV", "required": True},
        {"key": "education_cert", "label": "Education Certificate", "required": False},
        {"key": "previous_offer_letter", "label": "Previous Offer Letter", "required": False},
        {"key": "experience_letter", "label": "Experience Letter", "required": False},
        {"key": "bank_passbook", "label": "Bank Passbook / Cancelled Cheque", "required": True},
        {"key": "photo", "label": "Passport Photo", "required": False},
    ],
    "partner_external": [
        {"key": "pan_card", "label": "PAN Card", "required": True},
        {"key": "aadhaar_card", "label": "Aadhaar Card", "required": True},
        {"key": "gst_cert", "label": "GST Certificate", "required": False},
        {"key": "bank_passbook", "label": "Bank Passbook / Cancelled Cheque", "required": True},
        {"key": "partnership_agreement", "label": "Partnership Agreement", "required": True},
        {"key": "business_card", "label": "Business Card / Letterhead", "required": False},
    ],
    "vendor_internal": [
        {"key": "pan_card", "label": "PAN Card", "required": True},
        {"key": "aadhaar_card", "label": "Aadhaar Card", "required": True},
        {"key": "resume", "label": "Resume / CV", "required": False},
        {"key": "bank_passbook", "label": "Bank Passbook / Cancelled Cheque", "required": True},
        {"key": "service_agreement", "label": "Service Agreement", "required": True},
    ],
    "vendor_external": [
        {"key": "pan_card", "label": "PAN Card", "required": True},
        {"key": "gst_cert", "label": "GST Certificate", "required": True},
        {"key": "bank_passbook", "label": "Bank Passbook / Cancelled Cheque", "required": True},
        {"key": "service_agreement", "label": "Service Agreement", "required": True},
        {"key": "company_registration", "label": "Company Registration / Incorporation", "required": False},
    ],
}


def _is_admin(u: dict) -> bool:
    return u.get("role") in ("admin", "admin_owner") or u.get("rbac_role") in ("admin", "admin_owner")


def _is_hr(u: dict) -> bool:
    if _is_admin(u):
        return True
    return u.get("rbac_role") in ("hr_manager", "hr_admin") or "hr.user_manage.any" in (u.get("permissions") or [])


def _iso(v):
    if isinstance(v, datetime):
        return v.isoformat()
    return v


def _clean(d: dict) -> dict:
    if not d:
        return d
    d.pop("_id", None)
    for k in ("created_at", "updated_at", "joined_at", "password_changed_at", "last_login_at", "deactivated_at", "reactivated_at"):
        v = d.get(k)
        if isinstance(v, datetime):
            d[k] = v.isoformat()
    return d


# ──────────────────────────────────────────────────────────────
# Person Type derivation
# ──────────────────────────────────────────────────────────────
INTERNAL_ROLES = {
    "admin", "admin_owner", "case_manager", "sales_executive", "sr_sales_executive",
    "sales_manager", "sales_head", "operations", "hr_manager", "hr_admin",
    "marketing", "it_admin", "accountant", "case_officer",
}
EXTERNAL_USER_ROLES = {"partner", "client", "vendor"}


def _person_type(user: Optional[dict], vendor: Optional[dict]) -> str:
    """Compute person_type for the unified view."""
    if vendor and vendor.get("vendor_type") == "internal":
        return "vendor_internal"
    if vendor and vendor.get("vendor_type") == "external":
        return "vendor_external"
    if user:
        role = user.get("rbac_role") or user.get("role")
        if role in INTERNAL_ROLES:
            return "employee_internal"
        if role == "partner":
            return "partner_external"
        if role == "client":
            return "client"
        if role == "vendor":
            return "vendor_external"
    return "unknown"


# ──────────────────────────────────────────────────────────────
# GET /people — unified list
# ──────────────────────────────────────────────────────────────
@router.get("")
async def list_people(
    person_type: Optional[str] = Query(None, description="employee_internal | partner_external | vendor_internal | vendor_external | client"),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None, description="email / name / vendor_code"),
    role: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    if not _is_hr(current_user):
        raise HTTPException(status_code=403, detail="Admin or HR role required")

    # Build vendor index keyed by user_id and email for fast joining
    vendors = await vendors_col.find({}, {"_id": 0}).to_list(2000)
    vendor_by_user = {v["user_id"]: v for v in vendors if v.get("user_id")}
    vendor_by_email = {v["email"].lower(): v for v in vendors if v.get("email")}

    # Pull all users
    users = await users_col.find({}, {"_id": 0, "password": 0}).to_list(5000)

    people: List[Dict[str, Any]] = []
    seen_emails = set()
    for u in users:
        email = (u.get("email") or "").lower()
        vendor = vendor_by_user.get(u["id"]) or vendor_by_email.get(email)
        ptype = _person_type(u, vendor)
        people.append({
            "id": u["id"],
            "kind": "user",
            "person_type": ptype,
            "name": u.get("name"),
            "email": u.get("email"),
            "mobile": u.get("mobile") or "",
            "role": u.get("rbac_role") or u.get("role"),
            "user_type": u.get("user_type") or ("internal" if ptype.startswith("employee") else "external"),
            "department": u.get("department"),
            "status": u.get("status", "active"),
            "permissions_count": len(u.get("permissions") or []),
            "vendor_id": vendor.get("id") if vendor else None,
            "vendor_code": vendor.get("vendor_code") if vendor else None,
            "vendor_category": vendor.get("category") if vendor else None,
            "auto_created_from_vendor": u.get("auto_created_from_vendor", False),
            "created_at": _iso(u.get("created_at")),
            "last_login_at": _iso(u.get("last_login_at")),
            "must_change_password_on_next_login": u.get("must_change_password_on_next_login", False),
        })
        if email:
            seen_emails.add(email)

    # Add vendors that don't have linked users yet
    for v in vendors:
        email = (v.get("email") or "").lower()
        if email in seen_emails:
            continue
        if v.get("user_id"):
            # User existed but was deleted — skip orphan link
            continue
        ptype = _person_type(None, v)
        people.append({
            "id": v["id"],
            "kind": "vendor",
            "person_type": ptype,
            "name": v.get("name"),
            "email": v.get("email"),
            "mobile": v.get("phone") or "",
            "role": v.get("category"),
            "user_type": v.get("vendor_type"),
            "department": None,
            "status": v.get("status", "active"),
            "permissions_count": 0,
            "vendor_id": v["id"],
            "vendor_code": v.get("vendor_code"),
            "vendor_category": v.get("category"),
            "auto_created_from_vendor": False,
            "created_at": _iso(v.get("created_at")),
            "last_login_at": None,
            "must_change_password_on_next_login": False,
        })

    # Apply filters
    if person_type:
        people = [p for p in people if p["person_type"] == person_type]
    if status:
        people = [p for p in people if p["status"] == status]
    if role:
        people = [p for p in people if p["role"] == role]
    if department:
        people = [p for p in people if (p.get("department") or "").lower() == department.lower()]
    if search:
        s = search.lower()
        people = [p for p in people if
                  s in (p.get("name") or "").lower() or
                  s in (p.get("email") or "").lower() or
                  s in (p.get("vendor_code") or "").lower() or
                  s in (p.get("mobile") or "").lower()]

    return {"people": people, "count": len(people)}


# ──────────────────────────────────────────────────────────────
# GET /people/stats
# ──────────────────────────────────────────────────────────────
@router.get("/stats")
async def stats(current_user: dict = Depends(get_current_user)):
    if not _is_hr(current_user):
        raise HTTPException(status_code=403, detail="Admin or HR role required")
    full = await list_people(
        person_type=None, status=None, search=None,
        role=None, department=None,
        current_user=current_user,
    )
    people = full["people"]
    by_type: Dict[str, int] = {}
    by_status: Dict[str, int] = {}
    by_role: Dict[str, int] = {}
    for p in people:
        by_type[p["person_type"]] = by_type.get(p["person_type"], 0) + 1
        by_status[p["status"]] = by_status.get(p["status"], 0) + 1
        if p.get("role"):
            by_role[p["role"]] = by_role.get(p["role"], 0) + 1
    return {
        "total": len(people),
        "by_type": by_type,
        "by_status": by_status,
        "by_role": dict(sorted(by_role.items(), key=lambda x: x[1], reverse=True)),
    }


# ──────────────────────────────────────────────────────────────
# GET /people/{id} — full profile
# ──────────────────────────────────────────────────────────────
@router.get("/{person_id}")
async def get_person(person_id: str, current_user: dict = Depends(get_current_user)):
    if not _is_hr(current_user):
        raise HTTPException(status_code=403, detail="Admin or HR role required")
    user = await users_col.find_one({"id": person_id}, {"_id": 0, "password": 0})
    vendor = None
    if user:
        vendor = await vendors_col.find_one({"user_id": user["id"]}, {"_id": 0}) or \
                 await vendors_col.find_one({"email": user["email"].lower()}, {"_id": 0})
    else:
        vendor = await vendors_col.find_one({"id": person_id}, {"_id": 0})
        if vendor and vendor.get("user_id"):
            user = await users_col.find_one({"id": vendor["user_id"]}, {"_id": 0, "password": 0})

    if not user and not vendor:
        raise HTTPException(status_code=404, detail="Person not found")

    return {
        "user": _clean(user) if user else None,
        "vendor": _clean(vendor) if vendor else None,
        "person_type": _person_type(user, vendor),
    }


# ──────────────────────────────────────────────────────────────
# POST /people — Add Person wizard
# ──────────────────────────────────────────────────────────────
class OnboardingDetails(BaseModel):
    designation: Optional[str] = None
    date_of_joining: Optional[str] = None  # ISO date
    dob: Optional[str] = None  # ISO date
    gender: Optional[str] = None  # male / female / other
    blood_group: Optional[str] = None
    # Address
    current_address: Optional[str] = None
    permanent_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    # Emergency Contact
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relation: Optional[str] = None
    # KYC / Identity
    pan_number: Optional[str] = None
    aadhaar_number: Optional[str] = None
    gst_number: Optional[str] = None
    # Bank
    bank_account_number: Optional[str] = None
    bank_ifsc: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account_holder_name: Optional[str] = None
    # Misc
    notes: Optional[str] = None


class AddPersonRequest(BaseModel):
    person_type: str = Field(..., description="employee_internal | partner_external | vendor_internal | vendor_external")
    name: str
    email: EmailStr
    mobile: Optional[str] = ""
    # employee_internal fields
    role: Optional[str] = None  # rbac_role
    department: Optional[str] = None
    # vendor fields
    vendor_category: Optional[str] = None
    specialization: Optional[List[str]] = None
    # Auto-generate password OR use provided
    custom_password: Optional[str] = None
    send_invite: bool = True
    # Phase 4D+ — Onboarding / KYC details
    onboarding: Optional[OnboardingDetails] = None


@router.post("")
async def add_person(req: AddPersonRequest, current_user: dict = Depends(get_current_user)):
    if not _is_hr(current_user):
        raise HTTPException(status_code=403, detail="Admin or HR role required")

    # Check duplicate email
    existing_user = await users_col.find_one({"email": req.email.lower()}, {"_id": 0, "id": 1})
    existing_vendor = await vendors_col.find_one({"email": req.email.lower()}, {"_id": 0, "id": 1})
    if existing_user or existing_vendor:
        raise HTTPException(status_code=409, detail=f"A person with email '{req.email}' already exists.")

    now = datetime.now(timezone.utc)
    temp_password = req.custom_password or f"Welcome@{secrets.token_urlsafe(6)}"
    if req.custom_password:
        ok, msg = validate_password_strength(req.custom_password)
        if not ok:
            raise HTTPException(status_code=400, detail=msg)

    result: Dict[str, Any] = {"ok": True, "temp_password": temp_password}

    # Build the onboarding payload once, attach to whichever entity we create
    onboarding_payload = req.onboarding.model_dump(exclude_none=True) if req.onboarding else {}
    if onboarding_payload:
        onboarding_payload["captured_at"] = now
        onboarding_payload["captured_by"] = current_user["id"]

    if req.person_type == "employee_internal":
        if not req.role:
            raise HTTPException(status_code=400, detail="role is required for employee_internal")
        if req.role not in INTERNAL_ROLES:
            raise HTTPException(status_code=400, detail=f"Invalid internal role '{req.role}'. Allowed: {sorted(INTERNAL_ROLES)}")
        user_doc = {
                "id": str(uuid.uuid4()),
                "name": req.name.strip(),
                "email": req.email.lower(),
                "mobile": req.mobile or "",
                "password": get_password_hash(temp_password),
                "role": req.role,
                "rbac_role": req.role,
                "user_type": "internal",
                "department": req.department,
                "permissions": [],
                "ui_modules": [],
                "status": "active",
                "must_change_password_on_next_login": True,
                "onboarding": onboarding_payload,
                "documents": [],
                "created_at": now,
                "created_by": current_user["id"],
            }
        await users_col.insert_one(user_doc)
        result["person_id"] = user_doc["id"]
        result["kind"] = "user"

    elif req.person_type == "partner_external":
        user_doc = {
            "id": str(uuid.uuid4()),
            "name": req.name.strip(),
            "email": req.email.lower(),
            "mobile": req.mobile or "",
            "password": get_password_hash(temp_password),
            "role": "partner",
            "rbac_role": "partner",
            "user_type": "external",
            "department": None,
            "permissions": [],
            "ui_modules": [],
            "status": "active",
            "must_change_password_on_next_login": True,
            "onboarding": onboarding_payload,
            "documents": [],
            "created_at": now,
            "created_by": current_user["id"],
        }
        await users_col.insert_one(user_doc)
        result["person_id"] = user_doc["id"]
        result["kind"] = "user"

    elif req.person_type in ("vendor_internal", "vendor_external"):
        if not req.vendor_category:
            raise HTTPException(status_code=400, detail="vendor_category is required for vendors")
        cat = await db["vendor_categories"].find_one({"key": req.vendor_category}, {"_id": 0, "key": 1, "is_internal": 1, "default_payment_type": 1, "name": 1})
        if not cat:
            raise HTTPException(status_code=400, detail=f"Unknown vendor category '{req.vendor_category}'")

        # Generate vendor code (same logic as vendors.py)
        last_v = await vendors_col.find_one({}, sort=[("vendor_code", -1)], projection={"_id": 0, "vendor_code": 1})
        try:
            n = int((last_v or {}).get("vendor_code", "VND0000").replace("VND", "")) + 1 if last_v else 1
        except (ValueError, AttributeError):
            n = 1
        vendor_code = f"VND{n:04d}"

        vendor_doc = {
            "id": str(uuid.uuid4()),
            "vendor_code": vendor_code,
            "name": req.name.strip(),
            "email": req.email.lower(),
            "phone": req.mobile or "",
            "category": req.vendor_category,
            "specialization": req.specialization or [],
            "vendor_type": "internal" if req.person_type == "vendor_internal" else "external",
            "default_payment_terms": {"payment_type": cat.get("default_payment_type") or "flat", "default_amount": 0, "currency": "INR"},
            "bank_details": {
                "account_holder": (onboarding_payload.get("bank_account_holder_name") or req.name.strip()),
                "account_number": onboarding_payload.get("bank_account_number", ""),
                "ifsc": onboarding_payload.get("bank_ifsc", ""),
                "bank_name": onboarding_payload.get("bank_name", ""),
            } if onboarding_payload else {},
            "pan_number": onboarding_payload.get("pan_number", "") if onboarding_payload else "",
            "gst_number": onboarding_payload.get("gst_number", "") if onboarding_payload else "",
            "tds_applicable": False,
            "tds_rate": 0,
            "performance": {"total_cases_handled": 0, "total_paid_lifetime": 0.0, "rating": 0.0},
            "status": "active",
            "joined_at": now,
            "last_payment_at": None,
            "can_login": True,
            "portal_credentials_sent": False,
            "notes": onboarding_payload.get("notes", "") if onboarding_payload else "",
            "onboarding": onboarding_payload,
            "documents": [],
            "created_at": now,
            "updated_at": now,
            "created_by": current_user["id"],
        }
        # For internal vendor categories that map to internal roles, also create a user
        ROLE_MAP = {"case_manager": "case_manager", "sales_commission": "sales_executive"}
        target_role = ROLE_MAP.get(req.vendor_category)
        if req.person_type == "vendor_internal" and target_role:
            user_doc = {
                "id": str(uuid.uuid4()),
                "name": req.name.strip(),
                "email": req.email.lower(),
                "mobile": req.mobile or "",
                "password": get_password_hash(temp_password),
                "role": target_role,
                "rbac_role": target_role,
                "user_type": "internal",
                "department": req.department,
                "permissions": [],
                "ui_modules": [],
                "status": "active",
                "must_change_password_on_next_login": True,
                "auto_created_from_vendor": True,
                "onboarding": onboarding_payload,
                "documents": [],
                "created_at": now,
                "created_by": current_user["id"],
            }
            await users_col.insert_one(user_doc)
            vendor_doc["user_id"] = user_doc["id"]
            result["linked_user_id"] = user_doc["id"]
            result["linked_user_role"] = target_role
        else:
            vendor_doc["user_id"] = None
            # External vendors don't get a user account until they accept the invite

        await vendors_col.insert_one(vendor_doc)
        result["person_id"] = vendor_doc["id"]
        result["vendor_code"] = vendor_code
        result["kind"] = "vendor"

    else:
        raise HTTPException(status_code=400, detail=f"Invalid person_type '{req.person_type}'")

    return result


# ──────────────────────────────────────────────────────────────
# PATCH /people/{id} — update role / department / permissions / status
# ──────────────────────────────────────────────────────────────
class PatchPersonRequest(BaseModel):
    name: Optional[str] = None
    mobile: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    status: Optional[str] = None
    permissions: Optional[List[str]] = None
    ui_modules: Optional[List[str]] = None


@router.patch("/{person_id}")
async def patch_person(person_id: str, req: PatchPersonRequest, current_user: dict = Depends(get_current_user)):
    if not _is_hr(current_user):
        raise HTTPException(status_code=403, detail="Admin or HR role required")
    # Try users first
    user = await users_col.find_one({"id": person_id}, {"_id": 0, "id": 1})
    if user:
        update: Dict[str, Any] = {k: v for k, v in req.model_dump(exclude_unset=True).items() if v is not None}
        if "role" in update:
            update["rbac_role"] = update["role"]
        if update:
            update["updated_at"] = datetime.now(timezone.utc)
            await users_col.update_one({"id": person_id}, {"$set": update})
        return {"ok": True, "kind": "user"}
    vendor = await vendors_col.find_one({"id": person_id}, {"_id": 0, "id": 1})
    if vendor:
        update_v: Dict[str, Any] = {}
        d = req.model_dump(exclude_unset=True)
        if "name" in d and d["name"]:
            update_v["name"] = d["name"]
        if "mobile" in d and d["mobile"] is not None:
            update_v["phone"] = d["mobile"]
        if "status" in d and d["status"]:
            update_v["status"] = d["status"]
        if update_v:
            update_v["updated_at"] = datetime.now(timezone.utc)
            await vendors_col.update_one({"id": person_id}, {"$set": update_v})
        return {"ok": True, "kind": "vendor"}
    raise HTTPException(status_code=404, detail="Person not found")


@router.post("/{person_id}/deactivate")
async def deactivate(person_id: str, current_user: dict = Depends(get_current_user)):
    if not _is_hr(current_user):
        raise HTTPException(status_code=403, detail="Admin or HR role required")
    now = datetime.now(timezone.utc)
    updates = {"$set": {"status": "inactive", "deactivated_at": now, "deactivated_by": current_user["id"]}}
    r1 = await users_col.update_one({"id": person_id}, updates)
    r2 = await vendors_col.update_one({"id": person_id}, updates)
    # Also disable linked records
    v = await vendors_col.find_one({"user_id": person_id}, {"_id": 0, "id": 1})
    if v:
        await vendors_col.update_one({"id": v["id"]}, updates)
    if r1.modified_count == 0 and r2.modified_count == 0:
        raise HTTPException(status_code=404, detail="Person not found")
    return {"ok": True}


@router.post("/{person_id}/reactivate")
async def reactivate(person_id: str, current_user: dict = Depends(get_current_user)):
    if not _is_hr(current_user):
        raise HTTPException(status_code=403, detail="Admin or HR role required")
    now = datetime.now(timezone.utc)
    updates = {"$set": {"status": "active", "reactivated_at": now, "reactivated_by": current_user["id"]}}
    r1 = await users_col.update_one({"id": person_id}, updates)
    r2 = await vendors_col.update_one({"id": person_id}, updates)
    v = await vendors_col.find_one({"user_id": person_id}, {"_id": 0, "id": 1})
    if v:
        await vendors_col.update_one({"id": v["id"]}, updates)
    if r1.modified_count == 0 and r2.modified_count == 0:
        raise HTTPException(status_code=404, detail="Person not found")
    return {"ok": True}


@router.post("/{person_id}/reset-password")
async def reset_password(person_id: str, current_user: dict = Depends(get_current_user)):
    if not _is_hr(current_user):
        raise HTTPException(status_code=403, detail="Admin or HR role required")
    user = await users_col.find_one({"id": person_id}, {"_id": 0, "id": 1, "email": 1})
    if not user:
        raise HTTPException(status_code=404, detail="User not found (vendor-only profiles cannot have password reset)")
    temp_password = f"Reset@{secrets.token_urlsafe(6)}"
    now = datetime.now(timezone.utc)
    await users_col.update_one(
        {"id": person_id},
        {"$set": {
            "password": get_password_hash(temp_password),
            "must_change_password_on_next_login": True,
            "password_changed_at": now,
            "password_reset_by": current_user["id"],
        }}
    )
    return {"ok": True, "temp_password": temp_password, "email": user["email"]}



# ──────────────────────────────────────────────────────────────
# Phase 4D+ — Onboarding Documents (KYC, bank, agreements)
# ──────────────────────────────────────────────────────────────
async def _fetch_person_entity(person_id: str):
    """Returns (collection_name, document) for whichever entity owns this person_id."""
    user = await users_col.find_one({"id": person_id}, {"_id": 0})
    if user:
        return "users", user
    vendor = await vendors_col.find_one({"id": person_id}, {"_id": 0})
    if vendor:
        return "vendors", vendor
    return None, None


def _collection_for(name: str):
    return users_col if name == "users" else vendors_col


@router.get("/document-checklist/{person_type}")
async def document_checklist(person_type: str, current_user: dict = Depends(get_current_user)):
    """Return the recommended document checklist for a given person_type.
    Frontend uses this to render the required-doc summary in the wizard / detail drawer.
    """
    if not _is_hr(current_user):
        raise HTTPException(status_code=403, detail="Admin or HR role required")
    return {"items": RECOMMENDED_DOCS.get(person_type, [])}


@router.get("/{person_id}/documents")
async def list_documents(person_id: str, current_user: dict = Depends(get_current_user)):
    if not _is_hr(current_user):
        raise HTTPException(status_code=403, detail="Admin or HR role required")
    col_name, entity = await _fetch_person_entity(person_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Person not found")
    docs = entity.get("documents") or []
    # Strip file system paths from response
    items = []
    for d in docs:
        items.append({
            "id": d.get("id"),
            "doc_type": d.get("doc_type"),
            "doc_label": d.get("doc_label"),
            "file_name": d.get("file_name"),
            "mime_type": d.get("mime_type"),
            "size_bytes": d.get("size_bytes"),
            "uploaded_at": _iso(d.get("uploaded_at")),
            "uploaded_by": d.get("uploaded_by"),
            "verified": d.get("verified", False),
            "notes": d.get("notes", ""),
        })
    return {"items": items, "count": len(items)}


@router.post("/{person_id}/documents")
async def upload_document(
    person_id: str,
    doc_type: str = Form(...),
    doc_label: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    if not _is_hr(current_user):
        raise HTTPException(status_code=403, detail="Admin or HR role required")
    col_name, entity = await _fetch_person_entity(person_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Person not found")

    content = await file.read()
    if len(content) > MAX_DOC_SIZE:
        raise HTTPException(status_code=413, detail=f"File too large (max {MAX_DOC_SIZE // (1024*1024)} MB)")
    mime = (file.content_type or "").lower()
    if mime not in ALLOWED_DOC_MIME:
        # Try to guess from extension as fallback
        guessed, _ = mimetypes.guess_type(file.filename or "")
        if guessed not in ALLOWED_DOC_MIME:
            raise HTTPException(status_code=415, detail=f"Unsupported file type: {file.content_type}. Allowed: PDF, JPG, PNG, WEBP, DOC/DOCX")
        mime = guessed

    person_dir = ONBOARDING_DIR / person_id
    person_dir.mkdir(parents=True, exist_ok=True)
    doc_id = str(uuid.uuid4())
    safe_name = "".join(c if c.isalnum() or c in ('.', '-', '_') else '_' for c in (file.filename or "doc"))
    stored_name = f"{doc_id}__{safe_name}"
    file_path = person_dir / stored_name
    file_path.write_bytes(content)

    now = datetime.now(timezone.utc)
    doc_entry = {
        "id": doc_id,
        "doc_type": doc_type,
        "doc_label": doc_label or doc_type,
        "file_name": file.filename or stored_name,
        "stored_path": str(file_path),
        "mime_type": mime,
        "size_bytes": len(content),
        "notes": notes or "",
        "verified": False,
        "uploaded_at": now,
        "uploaded_by": current_user["id"],
    }
    col = _collection_for(col_name)
    await col.update_one({"id": person_id}, {"$push": {"documents": doc_entry}, "$set": {"updated_at": now}})

    return {
        "ok": True,
        "id": doc_id,
        "doc_type": doc_type,
        "doc_label": doc_label or doc_type,
        "file_name": file.filename,
        "mime_type": mime,
        "size_bytes": len(content),
        "uploaded_at": now.isoformat(),
    }


@router.get("/{person_id}/documents/{doc_id}/download")
async def download_document(person_id: str, doc_id: str, current_user: dict = Depends(get_current_user)):
    if not _is_hr(current_user):
        raise HTTPException(status_code=403, detail="Admin or HR role required")
    col_name, entity = await _fetch_person_entity(person_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Person not found")
    doc = next((d for d in (entity.get("documents") or []) if d.get("id") == doc_id), None)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    path = doc.get("stored_path")
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File missing on disk")
    return FileResponse(
        path,
        media_type=doc.get("mime_type") or "application/octet-stream",
        filename=doc.get("file_name") or "document",
    )


@router.delete("/{person_id}/documents/{doc_id}")
async def delete_document(person_id: str, doc_id: str, current_user: dict = Depends(get_current_user)):
    if not _is_hr(current_user):
        raise HTTPException(status_code=403, detail="Admin or HR role required")
    col_name, entity = await _fetch_person_entity(person_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Person not found")
    doc = next((d for d in (entity.get("documents") or []) if d.get("id") == doc_id), None)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    # Best-effort file delete
    path = doc.get("stored_path")
    if path and os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass
    col = _collection_for(col_name)
    await col.update_one({"id": person_id}, {"$pull": {"documents": {"id": doc_id}}, "$set": {"updated_at": datetime.now(timezone.utc)}})
    return {"ok": True}


@router.post("/{person_id}/documents/{doc_id}/verify")
async def verify_document(person_id: str, doc_id: str, current_user: dict = Depends(get_current_user)):
    if not _is_hr(current_user):
        raise HTTPException(status_code=403, detail="Admin or HR role required")
    col_name, entity = await _fetch_person_entity(person_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Person not found")
    docs = entity.get("documents") or []
    found = False
    for d in docs:
        if d.get("id") == doc_id:
            d["verified"] = True
            d["verified_by"] = current_user["id"]
            d["verified_at"] = datetime.now(timezone.utc)
            found = True
            break
    if not found:
        raise HTTPException(status_code=404, detail="Document not found")
    col = _collection_for(col_name)
    await col.update_one({"id": person_id}, {"$set": {"documents": docs, "updated_at": datetime.now(timezone.utc)}})
    return {"ok": True}
