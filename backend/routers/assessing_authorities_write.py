"""Phase 19.9 — Authority Admin WRITE endpoints.

All write endpoints are admin-only (sales/partner blocked at 403).
Every write registers a Phase 19.6 import_batch (revocable 24h) + audit log.

Endpoints:
    POST   /api/assessing-authorities                       — create new body
    PATCH  /api/assessing-authorities/{code}                — update fields
    POST   /api/assessing-authorities/{code}/verify         — flip draft → active
    POST   /api/assessing-authorities/bulk-verify           — list of codes
    POST   /api/assessing-authorities/{code}/split-laa      — special: LAA → 6 state bodies
    DELETE /api/assessing-authorities/{code}                — only if 0 linked
    POST   /api/assessing-authorities/{code}/diff-preview   — compute downstream impact
    POST   /api/assessing-authorities/migrate-occupation    — move occupation FK
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from core.auth import get_current_user
from core.database import db
from services import import_batch_service as ibs
from services.audit_service import log_action
from services.diff_audit_service import compute_diff_audit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/assessing-authorities", tags=["assessing-authorities-write"])

ADMIN_ROLES = {"admin", "admin_owner", "super_admin"}


def _is_admin(user: Dict[str, Any]) -> bool:
    role = user.get("rbac_role") or user.get("role")
    return role in ADMIN_ROLES or "*" in (user.get("permissions") or [])


def _strip_mongo(doc: Dict[str, Any]) -> Dict[str, Any]:
    if doc:
        doc.pop("_id", None)
    return doc


async def _recompute_occupation_count(db_, code: str) -> int:
    auth = await db_["assessing_authorities"].find_one({"code": code})
    if not auth:
        return 0
    n = await db_["occupation_master"].count_documents(
        {"country_code": "AU", "assessing_authority_id": auth["id"]},
    )
    await db_["assessing_authorities"].update_one(
        {"code": code}, {"$set": {"occupation_count": n}},
    )
    return n


async def _open_batch(user: Dict[str, Any], endpoint: str, file_name: str):
    fake_file = f"phase_19.9_{endpoint}_{datetime.now(timezone.utc).isoformat()}".encode()
    return await ibs.open_batch(
        db, ingestion_path=f"phase_19.9_authority_admin.{endpoint}",
        endpoint=endpoint,
        uploaded_by=str(user.get("id") or user.get("email") or "admin"),
        uploaded_by_name=str(user.get("name") or user.get("email") or "admin"),
        file_name=file_name, file_hash=ibs.file_sha256(fake_file),
        file_size_bytes=len(fake_file), target_collection="assessing_authorities",
    )


# ─── Models ──────────────────────────────────────────────────────────────────
class ProcessingModel(BaseModel):
    standard_days_min: Optional[int] = None
    standard_days_max: Optional[int] = None
    priority_days_min: Optional[int] = None
    priority_days_max: Optional[int] = None
    notes: Optional[str] = None


class FeesModel(BaseModel):
    msa_fee_aud: Optional[int] = None
    rpl_fee_aud: Optional[int] = None
    skill_review_fee_aud: Optional[int] = None
    appeal_fee_aud: Optional[int] = None
    additional_fees: Optional[List[Dict[str, Any]]] = None
    payment_methods: Optional[List[str]] = None
    currency: Optional[str] = "AUD"


class CreateAuthorityRequest(BaseModel):
    code: str = Field(..., min_length=2, max_length=15)
    full_name: str = Field(..., min_length=3, max_length=200)
    aliases: List[str] = Field(default_factory=list)
    website: Optional[str] = ""
    country: str = "AU"
    processing: Optional[ProcessingModel] = None
    fees: Optional[FeesModel] = None
    validity_period_months: Optional[int] = 36
    methodology_summary: Optional[str] = ""


class PatchAuthorityRequest(BaseModel):
    full_name: Optional[str] = None
    aliases: Optional[List[str]] = None
    website: Optional[str] = None
    processing: Optional[Dict[str, Any]] = None
    fees: Optional[Dict[str, Any]] = None
    validity_period_months: Optional[int] = None
    methodology_summary: Optional[str] = None
    documents_required_common: Optional[List[str]] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None


class BulkVerifyRequest(BaseModel):
    codes: List[str] = Field(..., min_length=1, max_length=200)


class DiffPreviewRequest(BaseModel):
    proposed_changes: Dict[str, Any] = Field(default_factory=dict)


class MigrateOccupationRequest(BaseModel):
    occupation_id: str
    new_authority_code: str
    reason: str = Field(..., min_length=3)


# ─── POST /api/assessing-authorities ────────────────────────────────────────
@router.post("")
async def create_authority(
    payload: CreateAuthorityRequest, request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    existing = await db["assessing_authorities"].find_one({"code": payload.code})
    if existing:
        raise HTTPException(status_code=409, detail=f"Authority code '{payload.code}' already exists")

    batch = await _open_batch(current_user, "create", f"create_{payload.code}")
    now = datetime.now(timezone.utc)
    doc = {
        "id": str(uuid.uuid4()),
        "code": payload.code,
        "full_name": payload.full_name,
        "aliases": payload.aliases,
        "website": payload.website,
        "country": payload.country,
        "status": "draft",
        "processing": payload.processing.model_dump() if payload.processing else {},
        "fees": payload.fees.model_dump() if payload.fees else {},
        "validity_period_months": payload.validity_period_months,
        "methodology_summary": payload.methodology_summary,
        "documents_required_common": [],
        "occupation_count": 0,
        "_seed_source": "phase_19.9_admin_create",
        "_created_by": current_user.get("id") or current_user.get("email"),
        "created_at": now, "last_updated_at": now,
    }
    await db["assessing_authorities"].insert_one(doc)
    ibs.record_create(batch, doc["id"], {"code": payload.code})
    await ibs.close_batch(db, batch, total_rows=1, status="committed")
    await log_action(db, action="authority.create",
                     user_id=str(current_user.get("id") or "admin"),
                     user_name=current_user.get("name"),
                     severity="info",
                     summary={"code": payload.code, "batch_id": batch["batch_id"]})
    return {"ok": True, "batch_id": batch["batch_id"], **_strip_mongo(doc)}


# ─── PATCH /api/assessing-authorities/{code} ────────────────────────────────
@router.patch("/{code}")
async def patch_authority(
    code: str, payload: PatchAuthorityRequest, request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    existing = await db["assessing_authorities"].find_one({"code": code})
    if not existing:
        raise HTTPException(status_code=404, detail="Authority not found")

    # Build patch with only non-null fields, merging nested dicts
    payload_dict = payload.model_dump(exclude_none=True)
    if not payload_dict:
        raise HTTPException(status_code=400, detail="No fields to patch")

    batch = await _open_batch(current_user, "patch", f"patch_{code}")
    pre_state = {k: v for k, v in existing.items() if k != "_id"}

    update_doc = {}
    for k, v in payload_dict.items():
        if k in ("processing", "fees") and isinstance(v, dict):
            current = existing.get(k) or {}
            merged = {**current, **v}
            update_doc[k] = merged
        else:
            update_doc[k] = v
    update_doc["last_updated_at"] = datetime.now(timezone.utc)
    update_doc["_last_updated_by"] = current_user.get("id") or current_user.get("email")

    await db["assessing_authorities"].update_one({"code": code}, {"$set": update_doc})
    ibs.record_update(batch, existing["id"], {"code": code}, pre_state)
    await ibs.close_batch(db, batch, total_rows=1, status="committed")
    await log_action(db, action="authority.patch",
                     user_id=str(current_user.get("id") or "admin"),
                     user_name=current_user.get("name"),
                     severity="info",
                     summary={"code": code, "fields_changed": list(payload_dict.keys()),
                              "batch_id": batch["batch_id"]})
    doc = await db["assessing_authorities"].find_one({"code": code})
    return {"ok": True, "batch_id": batch["batch_id"], **_strip_mongo(doc)}


# ─── POST /api/assessing-authorities/{code}/verify ──────────────────────────
@router.post("/{code}/verify")
async def verify_authority(
    code: str, current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    existing = await db["assessing_authorities"].find_one({"code": code})
    if not existing:
        raise HTTPException(status_code=404, detail="Authority not found")
    if existing.get("status") == "active":
        return {"ok": True, "already_active": True, "code": code}

    batch = await _open_batch(current_user, "verify", f"verify_{code}")
    pre_state = {k: v for k, v in existing.items() if k != "_id"}
    now = datetime.now(timezone.utc)
    await db["assessing_authorities"].update_one(
        {"code": code},
        {"$set": {"status": "active", "verified_at": now,
                  "verified_by": current_user.get("id") or current_user.get("email"),
                  "last_updated_at": now}},
    )
    ibs.record_update(batch, existing["id"], {"code": code}, pre_state)
    await ibs.close_batch(db, batch, total_rows=1, status="committed")
    await log_action(db, action="authority.verify",
                     user_id=str(current_user.get("id") or "admin"),
                     user_name=current_user.get("name"),
                     severity="info",
                     summary={"code": code, "batch_id": batch["batch_id"]})
    return {"ok": True, "code": code, "status": "active", "batch_id": batch["batch_id"]}


# ─── POST /api/assessing-authorities/bulk-verify ────────────────────────────
@router.post("/bulk-verify")
async def bulk_verify(
    payload: BulkVerifyRequest, current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    batch = await _open_batch(current_user, "bulk_verify", f"bulk_verify_{len(payload.codes)}_codes")
    now = datetime.now(timezone.utc)
    verified, skipped, missing = [], [], []
    for code in payload.codes:
        a = await db["assessing_authorities"].find_one({"code": code})
        if not a:
            missing.append(code); continue
        if a.get("status") == "active":
            skipped.append(code); continue
        pre = {k: v for k, v in a.items() if k != "_id"}
        await db["assessing_authorities"].update_one(
            {"code": code},
            {"$set": {"status": "active", "verified_at": now,
                      "verified_by": current_user.get("id") or current_user.get("email"),
                      "last_updated_at": now}},
        )
        ibs.record_update(batch, a["id"], {"code": code}, pre)
        verified.append(code)
    await ibs.close_batch(db, batch, total_rows=len(payload.codes), status="committed")
    await log_action(db, action="authority.bulk_verify",
                     user_id=str(current_user.get("id") or "admin"),
                     user_name=current_user.get("name"),
                     severity="warn" if missing else "info",
                     summary={"verified": verified, "skipped": skipped, "missing": missing,
                              "batch_id": batch["batch_id"]})
    return {"ok": True, "batch_id": batch["batch_id"],
            "verified_count": len(verified), "skipped_count": len(skipped),
            "missing": missing}


# ─── POST /api/assessing-authorities/{code}/split-laa ───────────────────────
_LAA_STATE_BODIES = [
    {"code": "LAA-NSW", "full_name": "NSW Legal Profession Admission Board",
     "website": "https://www.lpab.justice.nsw.gov.au/", "msa_fee_aud": 580},
    {"code": "LAA-VIC", "full_name": "Victorian Legal Admissions Board",
     "website": "https://www.lawadmissions.vic.gov.au/", "msa_fee_aud": 540},
    {"code": "LAA-QLD", "full_name": "Queensland Legal Practitioners Admissions Board",
     "website": "https://www.lpab.qld.gov.au/", "msa_fee_aud": 500},
    {"code": "LAA-SA", "full_name": "Legal Practitioners Education and Admission Council of SA",
     "website": "https://www.courts.sa.gov.au/lpeac/", "msa_fee_aud": 480},
    {"code": "LAA-WA", "full_name": "Legal Practice Board of Western Australia",
     "website": "https://www.lpbwa.org.au/", "msa_fee_aud": 460},
    {"code": "LAA-TAS", "full_name": "Tasmanian Legal Practice Board",
     "website": "https://www.lpbtas.org.au/", "msa_fee_aud": 440},
]


class SplitLAARequest(BaseModel):
    state_bodies: Optional[List[Dict[str, Any]]] = None  # admin can override defaults
    reassign_strategy: str = Field("manual", description="manual = leave occupations on umbrella; broadcast = mirror to all 6")


@router.post("/{code}/split-laa")
async def split_laa(
    code: str, payload: SplitLAARequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    if code != "LAA":
        raise HTTPException(status_code=400, detail="split-laa only valid for the LAA umbrella body")
    laa = await db["assessing_authorities"].find_one({"code": "LAA"})
    if not laa:
        raise HTTPException(status_code=404, detail="LAA umbrella body not found")

    batch = await _open_batch(current_user, "split_laa", "split_laa_to_6_state_bodies")
    now = datetime.now(timezone.utc)
    bodies_to_create = payload.state_bodies or _LAA_STATE_BODIES
    created_codes = []

    # Create each state body
    for body in bodies_to_create:
        if await db["assessing_authorities"].find_one({"code": body["code"]}):
            continue  # idempotent
        doc = {
            "id": str(uuid.uuid4()),
            "code": body["code"],
            "full_name": body["full_name"],
            "aliases": [body["code"]],
            "website": body.get("website", ""),
            "country": "AU",
            "status": "draft",
            "processing": laa.get("processing", {}),
            "fees": {**laa.get("fees", {}), "msa_fee_aud": body.get("msa_fee_aud")},
            "validity_period_months": laa.get("validity_period_months", 36),
            "methodology_summary": (
                f"State-level legal admissions authority for {body['code'].replace('LAA-','')} "
                f"— split from LAA umbrella body in Phase 19.9."
            ),
            "documents_required_common": laa.get("documents_required_common", []),
            "occupation_count": 0,
            "_seed_source": "phase_19.9_laa_split",
            "_parent_umbrella": "LAA",
            "_created_by": current_user.get("id") or current_user.get("email"),
            "created_at": now, "last_updated_at": now,
        }
        await db["assessing_authorities"].insert_one(doc)
        ibs.record_create(batch, doc["id"], {"code": body["code"]})
        created_codes.append(body["code"])

    # Mark LAA umbrella as deprecated
    pre_laa = {k: v for k, v in laa.items() if k != "_id"}
    await db["assessing_authorities"].update_one(
        {"code": "LAA"},
        {"$set": {"status": "deprecated", "last_updated_at": now,
                  "_deprecated_by_split_at": now,
                  "_deprecated_split_into": created_codes}},
    )
    ibs.record_update(batch, laa["id"], {"code": "LAA"}, pre_laa)

    await ibs.close_batch(db, batch,
                          total_rows=len(created_codes) + 1, status="committed")
    await log_action(db, action="authority.split_laa",
                     user_id=str(current_user.get("id") or "admin"),
                     user_name=current_user.get("name"),
                     severity="warn",
                     summary={"created": created_codes, "deprecated": ["LAA"],
                              "batch_id": batch["batch_id"]})
    return {"ok": True, "batch_id": batch["batch_id"],
            "created_codes": created_codes,
            "deprecated": "LAA",
            "note": ("Occupations remain linked to LAA umbrella (now deprecated). "
                     "Admin should manually reassign each occupation to the correct state body "
                     "via POST /assessing-authorities/migrate-occupation.")}


# ─── DELETE /api/assessing-authorities/{code} ────────────────────────────────
@router.delete("/{code}")
async def delete_authority(
    code: str, current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    a = await db["assessing_authorities"].find_one({"code": code})
    if not a:
        raise HTTPException(status_code=404, detail="Authority not found")
    if (a.get("occupation_count") or 0) > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete {code} — still linked to {a['occupation_count']} occupations. Migrate or revoke first.",
        )
    batch = await _open_batch(current_user, "delete", f"delete_{code}")
    pre = {k: v for k, v in a.items() if k != "_id"}
    await db["assessing_authorities"].delete_one({"code": code})
    # Use record_update with pre-state to allow revoke-restore
    ibs.record_update(batch, a["id"], {"code": code}, pre)
    await ibs.close_batch(db, batch, total_rows=1, status="committed")
    await log_action(db, action="authority.delete",
                     user_id=str(current_user.get("id") or "admin"),
                     user_name=current_user.get("name"),
                     severity="warn",
                     summary={"code": code, "batch_id": batch["batch_id"]})
    return {"ok": True, "code": code, "deleted": True, "batch_id": batch["batch_id"]}


# ─── POST /api/assessing-authorities/{code}/diff-preview ────────────────────
@router.post("/{code}/diff-preview")
async def diff_preview(
    code: str, payload: DiffPreviewRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    return await compute_diff_audit(db, code, payload.proposed_changes)


# ─── POST /api/assessing-authorities/migrate-occupation ─────────────────────
@router.post("/migrate-occupation")
async def migrate_occupation(
    payload: MigrateOccupationRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    occ = await db["occupation_master"].find_one({"occupation_id": payload.occupation_id})
    if not occ:
        raise HTTPException(status_code=404, detail="Occupation not found")
    new_auth = await db["assessing_authorities"].find_one({"code": payload.new_authority_code})
    if not new_auth:
        raise HTTPException(status_code=404, detail=f"Authority {payload.new_authority_code} not found")
    old_auth_id = occ.get("assessing_authority_id")

    batch = await _open_batch(current_user, "migrate_occ",
                              f"migrate_{payload.occupation_id}_to_{payload.new_authority_code}")
    pre = {k: v for k, v in occ.items() if k != "_id"}
    await db["occupation_master"].update_one(
        {"occupation_id": payload.occupation_id},
        {"$set": {"assessing_authority_id": new_auth["id"],
                  "_authority_migrated_at": datetime.now(timezone.utc),
                  "_authority_migration_reason": payload.reason,
                  "_authority_previous_id": old_auth_id}},
    )
    ibs.record_update(batch, payload.occupation_id,
                      {"country_code": "AU", "occupation_id": payload.occupation_id},
                      pre)
    await ibs.close_batch(db, batch, total_rows=1, status="committed")
    # Update the target collection in the batch to occupation_master (since revoke would target that)
    await db["import_batches"].update_one(
        {"batch_id": batch["batch_id"]},
        {"$set": {"target_collection": "occupation_master"}},
    )

    # Recompute occupation_count on both sides
    if old_auth_id:
        old_a = await db["assessing_authorities"].find_one({"id": old_auth_id})
        if old_a:
            await _recompute_occupation_count(db, old_a["code"])
    await _recompute_occupation_count(db, payload.new_authority_code)

    await log_action(db, action="authority.migrate_occupation",
                     user_id=str(current_user.get("id") or "admin"),
                     user_name=current_user.get("name"),
                     severity="warn",
                     summary={"occupation_id": payload.occupation_id,
                              "new_code": payload.new_authority_code,
                              "old_id": old_auth_id, "reason": payload.reason,
                              "batch_id": batch["batch_id"]})
    return {"ok": True, "batch_id": batch["batch_id"],
            "occupation_id": payload.occupation_id,
            "new_authority_code": payload.new_authority_code}
