"""Phase 6.9.5 — Country Template · Editable Points Engine.

Replaces hardcoded points calculation logic with admin-editable templates per country.

Each country = configurable factor list + pass mark + visa subclasses.
The calculator reads templates first, falls back to legacy rules for any country
without a template (zero-regression migration).

Endpoints:
  GET  /api/country-templates                       — list all
  GET  /api/country-templates/{country_code}        — get template
  PUT  /api/country-templates/{country_code}        — admin updates
  POST /api/country-templates                       — admin creates new country
  POST /api/country-templates/{country_code}/verify — admin marks verified
  DELETE /api/country-templates/{country_code}      — admin removes (only if status=draft)

Schema (per template document):
  country_code, country_name, flag, is_active, classification_system,
  factors: [
    { factor_id, factor_name, factor_type ('range'|'select'|'boolean'),
      options: [{label, condition, points}],
      is_additional_factor: bool, is_core: bool, display_order: int, notes }
  ],
  pass_mark, visa_subclasses: [{subclass, name, min_points, processing_months}],
  partner_rules: {none, competent_english, skilled_partner, australian_pr_citizen},
  notes, status, verification{}, created_by, created_at, updated_at
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.auth import get_current_user
from core.database import db

router = APIRouter(prefix="/country-templates", tags=["country-templates"])

COUNTRY_TEMPLATES = db["country_templates"]
ADMIN_ROLES = {"admin", "admin_owner"}
VALID_STATUSES = {"verified", "draft", "outdated", "superseded"}


def _is_admin(user: dict) -> bool:
    role = user.get("rbac_role") or user.get("role")
    return role in ADMIN_ROLES or "*" in (user.get("permissions") or [])


def _strip(d: dict) -> dict:
    if d and "_id" in d:
        d.pop("_id", None)
    return d


# ─────────────────────────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────────────────────────
class FactorOption(BaseModel):
    label: str
    condition: Optional[str] = ""  # "age in [18,24]" — human-readable; engine still uses code paths
    points: int = 0


class Factor(BaseModel):
    factor_id: Optional[str] = None
    factor_name: str
    factor_type: str = "range"  # range | select | boolean
    options: List[FactorOption] = []
    is_additional_factor: bool = False
    is_core: bool = True
    display_order: int = 0
    notes: Optional[str] = ""


class VisaSubclass(BaseModel):
    subclass: str
    name: Optional[str] = ""
    min_points: Optional[int] = None
    processing_months: Optional[str] = ""


class PartnerRules(BaseModel):
    no_partner_or_australian_pr: int = 10
    skilled_partner: int = 10
    competent_english_partner: int = 5
    none: int = 0


class TemplateCreate(BaseModel):
    country_code: str = Field(..., min_length=2, max_length=3)
    country_name: str
    flag: Optional[str] = ""
    is_active: bool = True
    classification_system: str = "ANZSCO"
    factors: List[Factor] = []
    pass_mark: int = 65
    visa_subclasses: List[VisaSubclass] = []
    partner_rules: Optional[PartnerRules] = None
    notes: Optional[str] = ""


class TemplateUpdate(BaseModel):
    country_name: Optional[str] = None
    flag: Optional[str] = None
    is_active: Optional[bool] = None
    classification_system: Optional[str] = None
    factors: Optional[List[Factor]] = None
    pass_mark: Optional[int] = None
    visa_subclasses: Optional[List[VisaSubclass]] = None
    partner_rules: Optional[PartnerRules] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class VerifyRequest(BaseModel):
    source_reference: str
    review_notes: Optional[str] = ""


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────
@router.get("")
async def list_templates(current_user: dict = Depends(get_current_user)):
    items = []
    async for d in COUNTRY_TEMPLATES.find({"status": {"$ne": "superseded"}}, {"_id": 0}).sort("country_code", 1):
        items.append(_strip(d))
    return {"items": items, "count": len(items)}


@router.get("/{country_code}")
async def get_template(country_code: str, current_user: dict = Depends(get_current_user)):
    doc = await COUNTRY_TEMPLATES.find_one({"country_code": country_code.upper()}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Country template not found")
    return _strip(doc)


@router.post("")
async def create_template(req: TemplateCreate, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    cc = req.country_code.upper()
    existing = await COUNTRY_TEMPLATES.find_one({"country_code": cc})
    if existing and existing.get("status") != "superseded":
        raise HTTPException(status_code=409, detail=f"Template for {cc} already exists")
    if existing and existing.get("status") == "superseded":
        # Allow recreation by hard-deleting the soft-deleted stale doc first
        await COUNTRY_TEMPLATES.delete_one({"country_code": cc})
    now = datetime.now(timezone.utc)
    # Generate factor_ids where missing
    factors = []
    for f in req.factors:
        fd = f.model_dump()
        if not fd.get("factor_id"):
            fd["factor_id"] = str(uuid.uuid4())
        factors.append(fd)
    doc = {
        "country_code": cc,
        "country_name": req.country_name,
        "flag": req.flag,
        "is_active": req.is_active,
        "classification_system": req.classification_system,
        "factors": factors,
        "pass_mark": req.pass_mark,
        "visa_subclasses": [v.model_dump() for v in req.visa_subclasses],
        "partner_rules": (req.partner_rules.model_dump() if req.partner_rules else PartnerRules().model_dump()),
        "notes": req.notes,
        "status": "draft",
        "verification": {
            "verified_by": None, "verified_at": None,
            "source_reference": "", "review_notes": "",
        },
        "created_by": current_user["id"],
        "created_at": now,
        "updated_at": now,
        "last_reviewed_at": None,
    }
    await COUNTRY_TEMPLATES.insert_one(doc)
    return _strip(doc)


@router.put("/{country_code}")
async def update_template(country_code: str, req: TemplateUpdate, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    cc = country_code.upper()
    existing = await COUNTRY_TEMPLATES.find_one({"country_code": cc})
    if not existing:
        raise HTTPException(status_code=404, detail="Template not found")
    if req.status and req.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Use {VALID_STATUSES}")
    update_doc = req.model_dump(exclude_unset=True)
    # Convert factors back to dicts + assign ids where missing
    if "factors" in update_doc:
        factors = []
        for f in update_doc["factors"]:
            if not f.get("factor_id"):
                f["factor_id"] = str(uuid.uuid4())
            factors.append(f)
        update_doc["factors"] = factors
    update_doc["updated_at"] = datetime.now(timezone.utc)
    # Any non-status edit reverts status to draft (admin must re-verify)
    if "status" not in update_doc and any(k in update_doc for k in ("factors", "pass_mark", "visa_subclasses", "partner_rules", "classification_system")):
        update_doc["status"] = "draft"
    await COUNTRY_TEMPLATES.update_one({"country_code": cc}, {"$set": update_doc})
    refreshed = await COUNTRY_TEMPLATES.find_one({"country_code": cc}, {"_id": 0})
    return _strip(refreshed)


@router.post("/{country_code}/verify")
async def verify_template(country_code: str, req: VerifyRequest, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    cc = country_code.upper()
    existing = await COUNTRY_TEMPLATES.find_one({"country_code": cc})
    if not existing:
        raise HTTPException(status_code=404, detail="Template not found")
    now = datetime.now(timezone.utc)
    await COUNTRY_TEMPLATES.update_one(
        {"country_code": cc},
        {"$set": {
            "status": "verified",
            "verification.verified_by": current_user["id"],
            "verification.verified_at": now,
            "verification.source_reference": req.source_reference,
            "verification.review_notes": req.review_notes or "",
            "last_reviewed_at": now,
            "updated_at": now,
        }},
    )
    refreshed = await COUNTRY_TEMPLATES.find_one({"country_code": cc}, {"_id": 0})
    return _strip(refreshed)


@router.delete("/{country_code}")
async def delete_template(country_code: str, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    cc = country_code.upper()
    existing = await COUNTRY_TEMPLATES.find_one({"country_code": cc})
    if not existing:
        raise HTTPException(status_code=404, detail="Template not found")
    # Soft-delete to 'superseded' (admin can recreate later); only when not verified
    if existing.get("status") == "verified":
        raise HTTPException(status_code=400, detail="Cannot delete a verified template. Mark superseded explicitly via PUT.")
    await COUNTRY_TEMPLATES.update_one(
        {"country_code": cc},
        {"$set": {"status": "superseded", "updated_at": datetime.now(timezone.utc)}},
    )
    return {"ok": True, "country_code": cc, "status": "superseded"}
