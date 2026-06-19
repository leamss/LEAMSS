"""Phase 20.3 — Pre-Assessment Fee Policies CRUD router.

Endpoints:
  GET    /api/pre-assessment-fee-policies         — list all (admin/sales-read)
  GET    /api/pre-assessment-fee-policies/resolve — resolve fee for product/country/visa
  POST   /api/pre-assessment-fee-policies         — create (admin)
  PATCH  /api/pre-assessment-fee-policies/{id}    — update (admin)
  DELETE /api/pre-assessment-fee-policies/{id}    — soft-delete (status="deprecated")
  POST   /api/pre-assessment-fee-policies/seed    — seed initial 6 policies (admin idempotent)

All writes register Phase 19.6 import_batches (revocable 24h).
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from core.auth import get_current_user
from core.database import db
from services import import_batch_service as ibs
from services.audit_service import log_action
from services.pre_assessment_fee_resolver import (
    COLLECTION, HARDCODED_SAFETY_NET_INR, resolve_pre_assessment_fee,
)
from services.fee_policy_diff_service import (
    DEFAULT_LOOKBACK_DAYS, apply_retroactive, compute_diff,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pre-assessment-fee-policies", tags=["pre-assessment-fee"])

ADMIN_ROLES = {"admin", "admin_owner", "super_admin"}
READ_ROLES = {"admin", "admin_owner", "super_admin", "sales", "case_manager", "partner"}


def _is_admin(user: Dict[str, Any]) -> bool:
    role = user.get("rbac_role") or user.get("role")
    return role in ADMIN_ROLES or "*" in (user.get("permissions") or [])


def _can_read(user: Dict[str, Any]) -> bool:
    role = user.get("rbac_role") or user.get("role")
    return role in READ_ROLES or "*" in (user.get("permissions") or [])


class PolicyCreate(BaseModel):
    country_code: str = Field(..., min_length=2, max_length=10,
                              description="AU/CA/NZ/UK/USA or GLOBAL")
    visa_category: str = Field(..., min_length=2, max_length=40,
                               description="PR/Work/Study/Tourist/.../ANY")
    fee_inr: int = Field(..., ge=0, le=1_000_000)
    currency: str = Field(default="INR", max_length=5)
    effective_from: Optional[datetime] = None
    effective_until: Optional[datetime] = None
    policy_name: str = Field(..., min_length=3, max_length=200)
    rationale: str = Field(default="", max_length=1000)


class PolicyUpdate(BaseModel):
    fee_inr: Optional[int] = Field(None, ge=0, le=1_000_000)
    effective_from: Optional[datetime] = None
    effective_until: Optional[datetime] = None
    policy_name: Optional[str] = Field(None, min_length=3, max_length=200)
    rationale: Optional[str] = Field(None, max_length=1000)
    status: Optional[str] = Field(None, pattern=r"^(active|deprecated|draft)$")


class DiffPreviewRequest(BaseModel):
    """Body for POST /{policy_id}/diff-preview — what would change?"""
    fee_inr: Optional[int] = Field(None, ge=0, le=1_000_000)
    lookback_days: int = Field(default=DEFAULT_LOOKBACK_DAYS, ge=1, le=365)


class RetroactiveApplyRequest(BaseModel):
    """Body for POST /{policy_id}/apply-retroactive — update existing PAs."""
    reason: str = Field(..., min_length=10, max_length=500,
                        description="Mandatory reason (min 10 chars) for audit trail")
    affect_unpaid_only: bool = Field(
        default=True,
        description="If True, only PAs in stages: new, payment_pending. Recommended for safety.",
    )
    lookback_days: int = Field(default=DEFAULT_LOOKBACK_DAYS, ge=1, le=365)


def _serialise(doc: Dict[str, Any]) -> Dict[str, Any]:
    doc.pop("_id", None)
    for k in ("effective_from", "effective_until", "created_at", "updated_at"):
        if isinstance(doc.get(k), datetime):
            doc[k] = doc[k].isoformat()
    return doc


@router.get("")
async def list_policies(
    include_deprecated: bool = False,
    country: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not _can_read(current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    q: Dict[str, Any] = {}
    if not include_deprecated:
        q["status"] = {"$ne": "deprecated"}
    if country:
        q["country_code"] = country.upper()
    items = []
    async for d in db[COLLECTION].find(q).sort([("country_code", 1), ("visa_category", 1)]):
        items.append(_serialise(d))
    return {"items": items, "count": len(items), "safety_net_inr": HARDCODED_SAFETY_NET_INR}


@router.get("/resolve")
async def resolve(
    product_id: Optional[str] = None,
    country: Optional[str] = None,
    visa_category: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not _can_read(current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    if not product_id and not (country and visa_category):
        raise HTTPException(status_code=400,
                            detail="Provide product_id OR (country + visa_category)")
    return await resolve_pre_assessment_fee(db, product_id, country, visa_category)


@router.post("")
async def create_policy(
    payload: PolicyCreate, current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")

    user_id = str(current_user.get("id") or current_user.get("email") or "admin")
    user_name = str(current_user.get("name") or current_user.get("email") or "admin")

    now = datetime.now(timezone.utc)
    doc = {
        "id": str(uuid.uuid4()),
        "country_code": payload.country_code.upper(),
        "visa_category": payload.visa_category.upper(),
        "fee_inr": int(payload.fee_inr),
        "currency": payload.currency.upper(),
        "policy_name": payload.policy_name,
        "rationale": payload.rationale,
        "effective_from": payload.effective_from or now,
        "effective_until": payload.effective_until,
        "status": "active",
        "created_by": user_id, "created_by_name": user_name, "created_at": now,
        "updated_at": now,
    }

    body_bytes = f"{doc['country_code']}_{doc['visa_category']}_{doc['fee_inr']}".encode()
    batch = await ibs.open_batch(
        db, ingestion_path="phase_20.3_fee_policy.create",
        endpoint="POST /api/pre-assessment-fee-policies",
        uploaded_by=user_id, uploaded_by_name=user_name,
        file_name=f"policy_{doc['country_code']}_{doc['visa_category']}",
        file_hash=ibs.file_sha256(body_bytes),
        file_size_bytes=len(body_bytes), target_collection=COLLECTION,
    )
    await db[COLLECTION].insert_one(doc)
    ibs.record_create(batch, doc["id"], doc)
    await ibs.close_batch(db, batch, total_rows=1, status="committed")
    await log_action(db, action="fee_policy.create",
                     user_id=user_id, user_name=user_name, severity="info",
                     summary={"policy_id": doc["id"], "country": doc["country_code"],
                              "visa": doc["visa_category"], "fee_inr": doc["fee_inr"],
                              "batch_id": batch["batch_id"]})
    return {"ok": True, "batch_id": batch["batch_id"], **_serialise(doc)}


@router.patch("/{policy_id}")
async def update_policy(
    policy_id: str, payload: PolicyUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    existing = await db[COLLECTION].find_one({"id": policy_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Policy not found")
    updates = {k: v for k, v in payload.dict().items() if v is not None}
    if not updates:
        return {"ok": True, "no_change": True}

    user_id = str(current_user.get("id") or current_user.get("email") or "admin")
    user_name = str(current_user.get("name") or current_user.get("email") or "admin")

    updates["updated_at"] = datetime.now(timezone.utc)
    updates["updated_by"] = user_id

    body_bytes = f"patch_{policy_id}".encode()
    batch = await ibs.open_batch(
        db, ingestion_path="phase_20.3_fee_policy.patch",
        endpoint=f"PATCH /api/pre-assessment-fee-policies/{policy_id}",
        uploaded_by=user_id, uploaded_by_name=user_name,
        file_name=f"policy_patch_{policy_id}", file_hash=ibs.file_sha256(body_bytes),
        file_size_bytes=len(body_bytes), target_collection=COLLECTION,
    )
    pre_state = {k: existing.get(k) for k in updates.keys()}
    await db[COLLECTION].update_one({"id": policy_id}, {"$set": updates})
    ibs.record_update(batch, policy_id, {k: v for k, v in updates.items() if k != "updated_at"}, pre_state)
    await ibs.close_batch(db, batch, total_rows=1, status="committed")
    await log_action(db, action="fee_policy.patch",
                     user_id=user_id, user_name=user_name, severity="info",
                     summary={"policy_id": policy_id, "fields": list(updates.keys()),
                              "batch_id": batch["batch_id"]})
    new_doc = await db[COLLECTION].find_one({"id": policy_id})
    return {"ok": True, "batch_id": batch["batch_id"], **_serialise(new_doc)}


@router.delete("/{policy_id}")
async def delete_policy(
    policy_id: str, current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    existing = await db[COLLECTION].find_one({"id": policy_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Policy not found")
    await db[COLLECTION].update_one({"id": policy_id}, {"$set": {
        "status": "deprecated",
        "deprecated_at": datetime.now(timezone.utc),
        "deprecated_by": str(current_user.get("id") or "admin"),
    }})
    return {"ok": True, "id": policy_id, "status": "deprecated"}


@router.post("/seed")
async def seed_initial_policies(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Idempotent seed of 6 initial policies (Sir's brochure-based defaults)."""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    from seeds.pre_assessment_fee_policies import SEED_POLICIES
    user_id = str(current_user.get("id") or "admin")
    now = datetime.now(timezone.utc)
    created = []
    skipped = []
    for sp in SEED_POLICIES:
        existing = await db[COLLECTION].find_one({
            "country_code": sp["country_code"], "visa_category": sp["visa_category"],
            "status": {"$ne": "deprecated"},
        })
        if existing:
            skipped.append(f"{sp['country_code']}/{sp['visa_category']}")
            continue
        doc = {
            "id": str(uuid.uuid4()),
            **sp,
            "currency": "INR",
            "effective_from": now,
            "effective_until": None,
            "status": "active",
            "created_by": user_id, "created_by_name": "system_seed",
            "created_at": now, "updated_at": now,
        }
        await db[COLLECTION].insert_one(doc)
        created.append(f"{sp['country_code']}/{sp['visa_category']} @ ₹{sp['fee_inr']}")
    return {"ok": True, "created": created, "skipped_existing": skipped,
            "count_created": len(created), "count_skipped": len(skipped)}


# ── Diff-Preview Bundle (Phase 20.3+) ─────────────────────────────────────────
@router.post("/{policy_id}/diff-preview")
async def diff_preview(
    policy_id: str, payload: DiffPreviewRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Compute downstream impact of proposed policy change.

    Returns count of affected PAs + breakdown (unpaid/paid) + sample.
    Modal shown by frontend ONLY when `requires_diff_modal=True`
    (i.e. when fee_inr actually changes — Sir's tactical default #4).
    """
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    try:
        diff = await compute_diff(
            db, policy_id,
            proposed_changes={k: v for k, v in payload.dict().items() if v is not None and k != "lookback_days"},
            lookback_days=payload.lookback_days,
        )
        return {"ok": True, **diff}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/{policy_id}/apply-retroactive")
async def apply_retroactive_endpoint(
    policy_id: str, payload: RetroactiveApplyRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Apply this policy's CURRENT fee_inr to existing PAs.

    Requires:
      - reason (min 10 chars, audit-logged)
      - affect_unpaid_only (default True — safety first; paid PAs untouched)

    Registers a Phase 19.6 revocable batch (24h undo window).
    """
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    user_id = str(current_user.get("id") or current_user.get("email") or "admin")
    user_name = str(current_user.get("name") or current_user.get("email") or "admin")
    try:
        result = await apply_retroactive(
            db, policy_id,
            reason=payload.reason,
            affect_unpaid_only=payload.affect_unpaid_only,
            user_id=user_id, user_name=user_name,
            lookback_days=payload.lookback_days,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
