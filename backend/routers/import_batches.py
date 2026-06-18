"""Phase 19.6 — Import Batches admin router.

Endpoints (all admin-only):
    GET  /api/import-batches                          — list newest-first
    GET  /api/import-batches/{batch_id}               — single batch detail
    POST /api/import-batches/{batch_id}/revoke        — replay-rollback (within 24h)
    POST /api/import-batches/{batch_id}/force-revoke  — override 24h window
    POST /api/import-batches/{batch_id}/finalise      — lock in (non-revocable forever)
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from core.auth import get_current_user
from core.database import db
from services import import_batch_service as ibs
from services.audit_service import log_action

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/import-batches", tags=["import-batches"])

ADMIN_ROLES = {"admin", "admin_owner", "super_admin"}


def _is_admin(user: Dict[str, Any]) -> bool:
    role = user.get("rbac_role") or user.get("role")
    return role in ADMIN_ROLES or "*" in (user.get("permissions") or [])


def _client_ip(request: Optional[Request]) -> Optional[str]:
    if not request:
        return None
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/import-batches
# ─────────────────────────────────────────────────────────────────────────────
@router.get("")
async def list_batches(
    limit: int = Query(20, ge=1, le=100),
    ingestion_path: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    items = await ibs.list_batches(db, limit=limit, ingestion_path=ingestion_path)
    return {"items": items, "count": len(items)}


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/import-batches/{batch_id}
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/{batch_id}")
async def get_batch(
    batch_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    b = await ibs.get_batch(db, batch_id)
    if not b:
        raise HTTPException(status_code=404, detail="batch not found")
    return b


class RevokeRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=500)


class ForceRevokeRequest(BaseModel):
    reason: str = Field(..., min_length=10, max_length=500)
    admin_override: bool = Field(...)


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/import-batches/{batch_id}/revoke
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/{batch_id}/revoke")
async def revoke(
    batch_id: str,
    payload: RevokeRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")

    user_id = str(current_user.get("id") or current_user.get("email") or "admin")
    batch = await ibs.get_batch(db, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="batch not found")
    if batch.get("audit_only"):
        raise HTTPException(
            status_code=400,
            detail="This batch is audit-only — granular revoke is not supported for this ingestion path. Use 'force-revoke' if absolutely necessary.",
        )
    try:
        result = await ibs.revoke_batch(db, batch_id, payload.reason, user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    await log_action(
        db, action="import_batch.revoke",
        user_id=user_id,
        user_name=current_user.get("name") or current_user.get("email"),
        severity="warn",
        ip=_client_ip(request),
        summary={
            "batch_id": batch_id, "ingestion_path": batch.get("ingestion_path"),
            "file_name": batch.get("file_name"), "reason": payload.reason,
            "before_counts": batch.get("counts"),
            "after": result,
        },
    )
    return {"ok": True, "batch_id": batch_id, **result}


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/import-batches/{batch_id}/force-revoke
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/{batch_id}/force-revoke")
async def force_revoke(
    batch_id: str,
    payload: ForceRevokeRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Override the 24h revocation window. Requires `admin_override=true` + min-10-char reason."""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    if not payload.admin_override:
        raise HTTPException(status_code=400, detail="admin_override must be true")

    user_id = str(current_user.get("id") or current_user.get("email") or "admin")
    batch = await ibs.get_batch(db, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="batch not found")
    if batch.get("status") == "revoked":
        raise HTTPException(status_code=400, detail="batch already revoked")
    if batch.get("audit_only"):
        raise HTTPException(
            status_code=400,
            detail="Audit-only batches cannot be revoked — no pre-state snapshot was captured.",
        )

    # Bypass the 24h window by flipping is_revocable temporarily
    await db["import_batches"].update_one(
        {"batch_id": batch_id},
        {"$set": {"is_revocable": True, "finalised_at": None}},
    )
    try:
        result = await ibs.revoke_batch(db, batch_id, payload.reason, user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    await log_action(
        db, action="import_batch.force_revoke",
        user_id=user_id,
        user_name=current_user.get("name") or current_user.get("email"),
        severity="critical",
        ip=_client_ip(request),
        summary={
            "batch_id": batch_id, "ingestion_path": batch.get("ingestion_path"),
            "file_name": batch.get("file_name"), "reason": payload.reason,
            "before_counts": batch.get("counts"), "after": result,
            "override": True,
        },
    )
    return {"ok": True, "batch_id": batch_id, "override": True, **result}


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/import-batches/{batch_id}/finalise
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/{batch_id}/finalise")
async def finalise(
    batch_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    user_id = str(current_user.get("id") or current_user.get("email") or "admin")
    try:
        result = await ibs.finalise_batch(db, batch_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    await log_action(
        db, action="import_batch.finalise",
        user_id=user_id,
        user_name=current_user.get("name") or current_user.get("email"),
        severity="info",
        ip=_client_ip(request),
        summary={"batch_id": batch_id, **result},
    )
    return {"ok": True, **result}
