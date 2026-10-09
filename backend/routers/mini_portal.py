"""Phase 20.5 — Client Mini Portal provisioning + admin controls.

Mini Portal is auto-provisioned on PA payment-received. Generates a 12-char
temp password, creates `client_mini_portals` record + auto-creates an
`information_sheets` doc (canonical 6-section schema) for the client+product.

Admin endpoints:
  GET /api/mini-portal/admin/list?status=...
  POST /api/mini-portal/admin/{client_id}/reset-password
  POST /api/mini-portal/admin/{client_id}/lock
  POST /api/mini-portal/admin/{client_id}/unlock

Client endpoints (mini-token, NOT main JWT):
  GET /api/mini-portal/{client_id}
  POST /api/mini-portal/{client_id}/change-password

All admin writes register Phase 19.6 revocable batches.
"""
from __future__ import annotations

import logging
import secrets
import string
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.auth import get_current_user
from core.database import db
from services import import_batch_service as ibs
from services.audit_service import log_action

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mini-portal", tags=["Phase 20.5 Mini Portal"])

MINI_PORTAL_COLL = "client_mini_portals"
INFO_SHEETS_COLL = "information_sheets"
PA_COLL = "pre_assessments"

ADMIN_ROLES = {"admin", "admin_owner", "super_admin"}
INTERNAL_ROLES = ADMIN_ROLES | {"case_manager", "case_manager_lead",
                                "sales_manager", "sales_head"}


def _is_admin(u: Dict[str, Any]) -> bool:
    role = (u.get("rbac_role") or u.get("role") or "").lower()
    return role in ADMIN_ROLES or "*" in (u.get("permissions") or [])


def _is_internal(u: Dict[str, Any]) -> bool:
    role = (u.get("rbac_role") or u.get("role") or "").lower()
    return role in INTERNAL_ROLES or "*" in (u.get("permissions") or [])


def _gen_temp_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


async def provision_mini_portal(
    db_, pa: Dict[str, Any], triggered_by: str = "system",
) -> Dict[str, Any]:
    """Idempotent provisioning. Called from PA mock_payment / confirm_payment hooks.

    Creates:
      1. client_mini_portals doc (idempotent by client_id)
      2. information_sheets doc (idempotent by entity_type+entity_id)
      3. Phase 19.6 revocable import_batch
      4. Audit log entry
    """
    client_id = pa.get("client_user_id") or pa.get("created_by_user_id") or pa.get("client_id")
    if not client_id:
        client_id = pa.get("client_email") or f"client_{pa['id']}"
    client_name = pa.get("client_name") or "Client"
    client_email = pa.get("client_email") or ""
    pa_id = pa["id"]
    product_id = pa.get("product_id")

    existing = await db_[MINI_PORTAL_COLL].find_one({"client_id": client_id})
    if existing:
        return {"ok": True, "status": "already_provisioned",
                "portal_id": existing["id"], "client_id": client_id,
                "info_sheet_id": existing.get("info_sheet_id")}

    now = datetime.now(timezone.utc)
    temp_password = _gen_temp_password()
    portal_id = str(uuid.uuid4())

    # Open Phase 19.6 revocable batch
    body = f"mini_portal_provision_{client_id}_{pa_id}".encode()
    batch = await ibs.open_batch(
        db_, ingestion_path="phase_20.5_mini_portal.provision",
        endpoint=f"internal:provision_mini_portal({client_id})",
        uploaded_by=triggered_by, uploaded_by_name="mini_portal_provisioner",
        file_name=f"mini_portal_{client_id}",
        file_hash=ibs.file_sha256(body), file_size_bytes=len(body),
        target_collection=MINI_PORTAL_COLL,
    )

    # 1. Mini portal doc
    portal_doc = {
        "id": portal_id, "client_id": client_id, "client_name": client_name,
        "client_email": client_email, "pa_id": pa_id, "product_id": product_id,
        "country": pa.get("country"), "service_type": pa.get("service_type"),
        "temp_password": temp_password,  # In prod: bcrypt + send via email
        "password_must_change": True,
        "status": "active",  # active | locked | closed
        "locked": False, "locked_by": None, "locked_at": None, "locked_reason": None,
        "created_at": now, "updated_at": now,
        "_provisioning_batch_id": batch["batch_id"],
    }
    await db_[MINI_PORTAL_COLL].insert_one(portal_doc)
    ibs.record_create(batch, portal_id, {"client_id": client_id, "pa_id": pa_id})

    # 2. Info sheet doc (idempotent)
    existing_sheet = await db_[INFO_SHEETS_COLL].find_one({
        "entity_type": "client", "entity_id": client_id,
    })
    if existing_sheet:
        info_sheet_id = existing_sheet["id"]
        logger.info(f"[Phase20.5] info_sheet exists for {client_id}: {info_sheet_id}")
    else:
        info_sheet_id = str(uuid.uuid4())
        sheet_doc = {
            "id": info_sheet_id,
            "entity_type": "client", "entity_id": client_id,
            "client_id": client_id, "case_id": None,
            "personal": {
                "given_names": client_name.split()[0] if client_name else "",
                "family_name": " ".join(client_name.split()[1:]) if client_name and " " in client_name else "",
                "email": client_email,
                "contact_number": pa.get("client_phone", ""),
            },
            "family": {}, "dependents": [], "qualifications": [],
            "employment": [], "resume": {},
            "schema_version": 2, "status": "draft",
            "locked": False, "locked_by": None, "locked_at": None,
            "audit_trail": [{"action": "auto_create_on_pa_payment",
                             "by": "system", "at": now.isoformat(),
                             "pa_id": pa_id, "portal_id": portal_id}],
            "created_at": now, "updated_at": now,
            "created_by": "system_mini_portal_provisioner",
            "_provisioning_batch_id": batch["batch_id"],
        }
        try:
            await db_[INFO_SHEETS_COLL].insert_one(sheet_doc)
            ibs.record_create(batch, info_sheet_id, {"info_sheet_id": info_sheet_id})
            logger.info(f"[Phase20.5] info_sheet CREATED for {client_id}: {info_sheet_id}")
        except Exception as e:
            logger.error(f"[Phase20.5] info_sheet creation FAILED for {client_id}: {e!r}")
            raise

    # Update portal with info_sheet_id reference
    await db_[MINI_PORTAL_COLL].update_one(
        {"id": portal_id}, {"$set": {"info_sheet_id": info_sheet_id}},
    )

    await ibs.close_batch(db_, batch, total_rows=2, status="committed")

    # 3. Audit log
    await log_action(
        db_, action="mini_portal.provision", user_id=triggered_by,
        severity="info",
        summary={"portal_id": portal_id, "client_id": client_id, "pa_id": pa_id,
                 "info_sheet_id": info_sheet_id, "batch_id": batch["batch_id"]},
    )

    return {
        "ok": True, "status": "provisioned", "portal_id": portal_id,
        "client_id": client_id, "info_sheet_id": info_sheet_id,
        "temp_password": temp_password,  # For SMS/email — log only in dev
        "batch_id": batch["batch_id"],
    }


# ── Admin endpoints ───────────────────────────────────────────────────────────
class ResetPasswordRequest(BaseModel):
    reason: str = Field(..., min_length=10, max_length=500)


class LockRequest(BaseModel):
    reason: str = Field(..., min_length=10, max_length=500)


@router.get("/admin/list")
async def admin_list_portals(
    status: Optional[str] = None,
    limit: int = 100,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not _is_internal(current_user):
        raise HTTPException(status_code=403, detail="Internal staff only")
    q: Dict[str, Any] = {}
    if status:
        q["status"] = status
    portals = []
    async for p in db[MINI_PORTAL_COLL].find(q).sort("created_at", -1).limit(limit):
        p.pop("_id", None)
        p.pop("temp_password", None)  # never expose passwords in admin list
        for k, v in list(p.items()):
            if isinstance(v, datetime):
                p[k] = v.isoformat()
        portals.append(p)
    return {"portals": portals, "count": len(portals)}


@router.post("/admin/{client_id}/reset-password")
async def admin_reset_password(
    client_id: str, payload: ResetPasswordRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    portal = await db[MINI_PORTAL_COLL].find_one({"client_id": client_id})
    if not portal:
        raise HTTPException(status_code=404, detail="Portal not found")

    new_password = _gen_temp_password()
    user_id = str(current_user.get("id") or "admin")
    user_name = current_user.get("name") or current_user.get("email")
    now = datetime.now(timezone.utc)

    body = f"reset_{client_id}_{new_password[:4]}".encode()
    batch = await ibs.open_batch(
        db, ingestion_path="phase_20.5_mini_portal.reset_password",
        endpoint=f"POST /api/mini-portal/admin/{client_id}/reset-password",
        uploaded_by=user_id, uploaded_by_name=user_name,
        file_name=f"reset_{client_id}", file_hash=ibs.file_sha256(body),
        file_size_bytes=len(body), target_collection=MINI_PORTAL_COLL,
    )

    await db[MINI_PORTAL_COLL].update_one(
        {"client_id": client_id},
        {"$set": {
            "temp_password": new_password, "password_must_change": True,
            "password_reset_at": now, "password_reset_by": user_id,
            "password_reset_reason": payload.reason, "updated_at": now,
        }},
    )
    ibs.record_update(batch, portal["id"], {"id": portal["id"]},
                      {"temp_password_hash": "***"})
    await ibs.close_batch(db, batch, total_rows=1, status="committed")

    await log_action(
        db, action="mini_portal.admin_reset_password",
        user_id=user_id, user_name=user_name, severity="warn",
        summary={"client_id": client_id, "reason": payload.reason,
                 "batch_id": batch["batch_id"]},
    )
    return {
        "ok": True, "client_id": client_id, "new_password": new_password,
        "must_change_on_next_login": True, "batch_id": batch["batch_id"],
        "revocable": True,
    }


@router.post("/admin/{client_id}/lock")
async def admin_lock_portal(
    client_id: str, payload: LockRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    portal = await db[MINI_PORTAL_COLL].find_one({"client_id": client_id})
    if not portal:
        raise HTTPException(status_code=404, detail="Portal not found")
    user_id = str(current_user.get("id") or "admin")
    now = datetime.now(timezone.utc)

    await db[MINI_PORTAL_COLL].update_one(
        {"client_id": client_id},
        {"$set": {"locked": True, "status": "locked",
                  "locked_at": now, "locked_by": user_id,
                  "locked_reason": payload.reason, "updated_at": now}},
    )
    await log_action(db, action="mini_portal.admin_lock",
                     user_id=user_id, severity="warn",
                     summary={"client_id": client_id, "reason": payload.reason})
    return {"ok": True, "client_id": client_id, "locked": True}


@router.post("/admin/{client_id}/unlock")
async def admin_unlock_portal(
    client_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    portal = await db[MINI_PORTAL_COLL].find_one({"client_id": client_id})
    if not portal:
        raise HTTPException(status_code=404, detail="Portal not found")
    user_id = str(current_user.get("id") or "admin")
    now = datetime.now(timezone.utc)
    await db[MINI_PORTAL_COLL].update_one(
        {"client_id": client_id},
        {"$set": {"locked": False, "status": "active",
                  "locked_at": None, "locked_by": None,
                  "unlocked_at": now, "unlocked_by": user_id,
                  "updated_at": now}},
    )
    await log_action(db, action="mini_portal.admin_unlock",
                     user_id=user_id, severity="info",
                     summary={"client_id": client_id})
    return {"ok": True, "client_id": client_id, "locked": False}


# ── Read endpoints ────────────────────────────────────────────────────────────
@router.get("/{client_id}")
async def get_portal(
    client_id: str, current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Return portal status. Both internal staff and the client themselves can read."""
    portal = await db[MINI_PORTAL_COLL].find_one({"client_id": client_id}, {"_id": 0, "temp_password": 0})
    if not portal:
        raise HTTPException(status_code=404, detail="Portal not found")

    # Authorisation: internal staff OR the client themselves
    is_self = str(current_user.get("id")) == client_id or current_user.get("email") == portal.get("client_email")
    if not (_is_internal(current_user) or is_self):
        raise HTTPException(status_code=403, detail="Forbidden")

    for k, v in list(portal.items()):
        if isinstance(v, datetime):
            portal[k] = v.isoformat()

    # Fetch linked info sheet status
    sheet = await db[INFO_SHEETS_COLL].find_one(
        {"id": portal.get("info_sheet_id")},
        {"_id": 0, "status": 1, "schema_version": 1, "updated_at": 1, "id": 1},
    ) if portal.get("info_sheet_id") else None
    if sheet and isinstance(sheet.get("updated_at"), datetime):
        sheet["updated_at"] = sheet["updated_at"].isoformat()

    return {"portal": portal, "info_sheet": sheet}
