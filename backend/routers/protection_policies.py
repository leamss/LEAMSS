"""Phase 7.1 — Protection Policy KB-managed entity.

LEAMSS USP: First Indian migration consultancy with 100% refund on skill
assessment negative outcome OR visa rejection. This module manages it as a
first-class KB entity with admin verify workflow + public read.

Endpoints under /api/protection-policies:
  GET    /                     — admin list (status filter)
  GET    /public               — public list (verified only)
  GET    /public/{policy_id}   — public single (verified only)
  GET    /{policy_id}          — admin single
  POST   /                     — admin create
  PUT    /{policy_id}          — admin edit (auto-reverts to draft)
  POST   /{policy_id}/verify   — admin verify with mandatory source_reference
  POST   /{policy_id}/hide     — soft-hide (status=hidden) — recoverable
  POST   /{policy_id}/unhide   — restore (status=draft)
  POST   /seed-default         — admin one-click seed of LEAMSS default policy
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.auth import get_current_user
from core.database import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/protection-policies", tags=["protection-policies"])

POLICIES = db["protection_policies"]
ADMIN_ROLES = {"admin", "admin_owner"}


def _is_admin(user: dict) -> bool:
    role = user.get("rbac_role") or user.get("role")
    return role in ADMIN_ROLES or "*" in (user.get("permissions") or [])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _strip(d: Optional[dict]) -> Optional[dict]:
    if d and "_id" in d:
        d.pop("_id", None)
    return d


class RefundTerms(BaseModel):
    covers: List[str] = Field(default_factory=list)        # ["professional_fees", "government_fees"]
    excludes: List[str] = Field(default_factory=list)
    claim_within_days: int = 90


class PolicyCreate(BaseModel):
    title: str = Field(..., min_length=5)
    policy_type: str = "negative_outcome_refund"           # extensible
    description_markdown: str = ""
    refund_terms: RefundTerms = RefundTerms()
    applicable_countries: List[str] = Field(default_factory=lambda: ["*"])
    applicable_visa_types: List[str] = Field(default_factory=lambda: ["*"])


class PolicyUpdate(BaseModel):
    title: Optional[str] = None
    description_markdown: Optional[str] = None
    refund_terms: Optional[RefundTerms] = None
    applicable_countries: Optional[List[str]] = None
    applicable_visa_types: Optional[List[str]] = None


class VerifyRequest(BaseModel):
    source_reference: str = Field(..., min_length=5)


@router.post("/seed-default")
async def seed_default(current_user: dict = Depends(get_current_user)):
    """One-click seed of LEAMSS' signature Protection Policy."""
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    existing = await POLICIES.find_one({"is_default_leamss": True}, {"_id": 0})
    if existing:
        return {"ok": True, "already_seeded": True, "policy": _strip(existing)}
    policy_id = f"POL-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    doc = {
        "policy_id": policy_id,
        "title": "🛡️ LEAMSS Protection Policy — 100% Refund Guarantee",
        "policy_type": "negative_outcome_refund",
        "description_markdown": (
            "## We Value Emotions\n\n"
            "LEAMSS is **India's first migration consultancy** to introduce a 100% Protection "
            "Policy that safeguards your entire investment.\n\n"
            "If your **skill assessment is negative** or your **visa is rejected** due to factors "
            "we have committed to verify upfront, we refund your **professional fees + government "
            "fees** without question.\n\n"
            "This policy is part of our promise of **complete transparency, honesty, and emotional "
            "accountability** to every client who trusts us with their dream of migration."
        ),
        "refund_terms": {
            "covers": ["professional_fees", "government_fees", "body_fees"],
            "excludes": ["english_test_fees", "medical_test_fees", "police_clearance_fees"],
            "claim_within_days": 90,
        },
        "applicable_countries": ["AU", "CA", "NZ", "UK", "USA"],
        "applicable_visa_types": ["*"],
        "version": "1.0",
        "is_default_leamss": True,
        "status": "draft",
        "verification": {"by": None, "by_name": None, "at": None, "source_reference": None},
        "created_at": _now(),
        "updated_at": _now(),
        "created_by": current_user.get("id"),
    }
    await POLICIES.insert_one(doc)
    return {"ok": True, "created": True, "policy": _strip(doc)}


@router.get("/")
async def list_policies(status: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    q: Dict[str, Any] = {}
    if status:
        q["status"] = status
    docs = await POLICIES.find(q, {"_id": 0}).sort("created_at", -1).to_list(100)
    return {"items": docs, "count": len(docs)}


@router.get("/public")
async def list_public():
    docs = await POLICIES.find(
        {"status": "verified"},
        {"_id": 0, "policy_id": 1, "title": 1, "description_markdown": 1,
         "refund_terms": 1, "applicable_countries": 1, "applicable_visa_types": 1,
         "version": 1, "updated_at": 1, "is_default_leamss": 1},
    ).sort("created_at", -1).to_list(100)
    return {"items": docs, "count": len(docs)}


@router.get("/public/{policy_id}")
async def get_public(policy_id: str):
    doc = await POLICIES.find_one(
        {"policy_id": policy_id, "status": "verified"},
        {"_id": 0},
    )
    if not doc:
        raise HTTPException(404, "Policy not found or not yet published")
    return doc


@router.get("/{policy_id}")
async def get_policy(policy_id: str, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    doc = await POLICIES.find_one({"policy_id": policy_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Policy not found")
    return doc


@router.post("/")
async def create_policy(payload: PolicyCreate, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    policy_id = f"POL-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    doc = {
        "policy_id": policy_id,
        **payload.model_dump(),
        "refund_terms": payload.refund_terms.model_dump(),
        "version": "1.0",
        "is_default_leamss": False,
        "status": "draft",
        "verification": {"by": None, "by_name": None, "at": None, "source_reference": None},
        "created_at": _now(),
        "updated_at": _now(),
        "created_by": current_user.get("id"),
    }
    await POLICIES.insert_one(doc)
    return _strip(doc)


@router.put("/{policy_id}")
async def update_policy(policy_id: str, payload: PolicyUpdate, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    existing = await POLICIES.find_one({"policy_id": policy_id}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "Policy not found")
    update: Dict[str, Any] = {"updated_at": _now()}
    pd = payload.model_dump(exclude_none=True)
    if "refund_terms" in pd and pd["refund_terms"]:
        pd["refund_terms"] = payload.refund_terms.model_dump()
    update.update(pd)
    # Any edit reverts to draft (admin must re-verify)
    update["status"] = "draft"
    update["verification"] = {"by": None, "by_name": None, "at": None, "source_reference": None}
    await POLICIES.update_one({"policy_id": policy_id}, {"$set": update})
    refreshed = await POLICIES.find_one({"policy_id": policy_id}, {"_id": 0})
    return refreshed


@router.post("/{policy_id}/verify")
async def verify_policy(policy_id: str, req: VerifyRequest, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    existing = await POLICIES.find_one({"policy_id": policy_id}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "Policy not found")
    await POLICIES.update_one(
        {"policy_id": policy_id},
        {"$set": {
            "status": "verified",
            "verification": {
                "by": current_user.get("id"),
                "by_name": current_user.get("name") or current_user.get("email"),
                "at": _now(),
                "source_reference": req.source_reference,
            },
            "updated_at": _now(),
        }},
    )
    refreshed = await POLICIES.find_one({"policy_id": policy_id}, {"_id": 0})
    return refreshed


@router.post("/{policy_id}/hide")
async def hide_policy(policy_id: str, current_user: dict = Depends(get_current_user)):
    """Soft-hide (NOT delete) — Sir's directive. Recoverable via /unhide."""
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    r = await POLICIES.update_one(
        {"policy_id": policy_id},
        {"$set": {"status": "hidden", "hidden_at": _now(), "updated_at": _now()}},
    )
    if r.matched_count == 0:
        raise HTTPException(404, "Policy not found")
    return {"ok": True, "hidden": policy_id}


@router.post("/{policy_id}/unhide")
async def unhide_policy(policy_id: str, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    r = await POLICIES.update_one(
        {"policy_id": policy_id},
        {"$set": {"status": "draft", "updated_at": _now()}, "$unset": {"hidden_at": ""}},
    )
    if r.matched_count == 0:
        raise HTTPException(404, "Policy not found")
    return {"ok": True, "restored": policy_id}
