"""Phase 19.8 — Bulk Enrichment Admin Router.

Endpoints (all admin-only):
    GET  /api/enrichment/coverage    — per-field % filled across country
    POST /api/enrichment/preview     — dry-run delta (no DB writes)
    POST /api/enrichment/run         — actual enrichment + revocable batch
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from core.auth import get_current_user
from core.database import db
from services import enrichment_engine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/enrichment", tags=["enrichment"])

ADMIN_ROLES = {"admin", "admin_owner", "super_admin"}


def _is_admin(user: Dict[str, Any]) -> bool:
    role = user.get("rbac_role") or user.get("role")
    return role in ADMIN_ROLES or "*" in (user.get("permissions") or [])


class EnrichmentRequest(BaseModel):
    country_code: str = Field("AU")
    force: bool = Field(False, description="Bypass admin-verified field locks")
    dry_run: bool = Field(False, description="Compute deltas but do not apply")


@router.get("/coverage")
async def coverage(
    country_code: str = "AU",
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    return await enrichment_engine.compute_coverage(db, country_code.upper())


@router.post("/preview")
async def preview(
    payload: EnrichmentRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    return await enrichment_engine.run_enrichment(
        db, country_code=payload.country_code.upper(),
        force=payload.force, dry_run=True,
        user_id=str(current_user.get("id") or current_user.get("email") or "admin"),
        user_name=str(current_user.get("name") or current_user.get("email") or "admin"),
    )


@router.post("/run")
async def run(
    payload: EnrichmentRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    if payload.dry_run:
        return await enrichment_engine.run_enrichment(
            db, country_code=payload.country_code.upper(),
            force=payload.force, dry_run=True,
            user_id=str(current_user.get("id") or current_user.get("email") or "admin"),
            user_name=str(current_user.get("name") or current_user.get("email") or "admin"),
        )
    return await enrichment_engine.run_enrichment(
        db, country_code=payload.country_code.upper(),
        force=payload.force, dry_run=False,
        user_id=str(current_user.get("id") or current_user.get("email") or "admin"),
        user_name=str(current_user.get("name") or current_user.get("email") or "admin"),
    )
