"""Phase 19.7 — Assessing Authorities READ-ONLY router.

Endpoints (all authenticated — admin / sales / partner roles can read):
    GET /api/assessing-authorities                — list (active by default; admins can see drafts)
    GET /api/assessing-authorities/{code}         — full detail
    GET /api/assessing-authorities/{code}/occupations — linked occupations (paginated)

Write endpoints (POST/PATCH/DELETE) ship in Phase 19.9.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from core.auth import get_current_user
from core.database import db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/assessing-authorities", tags=["assessing-authorities"])

READ_ROLES = {"admin", "admin_owner", "super_admin", "sales", "partner"}
ADMIN_ROLES = {"admin", "admin_owner", "super_admin"}


def _is_admin(user: Dict[str, Any]) -> bool:
    role = user.get("rbac_role") or user.get("role")
    return role in ADMIN_ROLES or "*" in (user.get("permissions") or [])


def _can_read(user: Dict[str, Any]) -> bool:
    role = user.get("rbac_role") or user.get("role")
    return role in READ_ROLES or "*" in (user.get("permissions") or [])


def _strip_mongo(doc: Dict[str, Any]) -> Dict[str, Any]:
    doc.pop("_id", None)
    return doc


@router.get("")
async def list_authorities(
    country: str = Query("AU"),
    status: Optional[str] = Query(None, description="active | draft | deprecated"),
    include_drafts: bool = Query(False, description="(admin only) include draft bodies"),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not _can_read(current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    q: Dict[str, Any] = {"country": country.upper()}
    if status:
        q["status"] = status
    elif not include_drafts and not _is_admin(current_user):
        # Non-admins: only see active by default
        q["status"] = {"$ne": "deprecated"}
    cursor = db["assessing_authorities"].find(q).sort("occupation_count", -1)
    items = [_strip_mongo(doc) async for doc in cursor]
    return {"items": items, "count": len(items)}


@router.get("/{code}")
async def get_authority(
    code: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not _can_read(current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    doc = await db["assessing_authorities"].find_one({"code": code})
    if not doc:
        raise HTTPException(status_code=404, detail=f"Authority {code} not found")
    return _strip_mongo(doc)


@router.get("/{code}/occupations")
async def list_authority_occupations(
    code: str,
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not _can_read(current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    auth = await db["assessing_authorities"].find_one({"code": code}, {"id": 1, "code": 1, "full_name": 1})
    if not auth:
        raise HTTPException(status_code=404, detail=f"Authority {code} not found")
    q = {"country_code": "AU", "assessing_authority_id": auth["id"]}
    total = await db["occupation_master"].count_documents(q)
    cursor = (db["occupation_master"]
              .find(q, {"_id": 0, "occupation_id": 1, "code": 1, "title": 1,
                        "status": 1, "skillselect_tier": 1, "hierarchy": 1})
              .sort("code", 1).skip(skip).limit(limit))
    items = [d async for d in cursor]
    return {
        "authority": {"code": auth["code"], "full_name": auth.get("full_name")},
        "total": total, "skip": skip, "limit": limit,
        "items": items, "count": len(items),
    }


# ── Phase 19.9.1 — Audit Trail endpoints ──────────────────────────────────────
def _serialise_audit(d: Dict[str, Any]) -> Dict[str, Any]:
    d.pop("_id", None)
    at = d.get("at")
    if hasattr(at, "isoformat"):
        d["at"] = at.isoformat()
    return d


@router.get("/audit-trail/recent")
async def recent_authority_audit(
    limit: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Phase 19.9.1 — Recent authority write events (admin/sales/partner-read).

    Powers the "Last Authority Edit" tile on Verification Hub's Authority Health Card.
    """
    if not _can_read(current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    cursor = db["audit_logs"].find(
        {"action": {"$regex": "^authority\\."}},
        {"_id": 0},
    ).sort("at", -1).limit(limit)
    items = [_serialise_audit(d) async for d in cursor]
    return {"items": items, "count": len(items),
            "latest_at": items[0]["at"] if items else None,
            "latest_action": items[0].get("action") if items else None,
            "latest_summary": items[0].get("summary") if items else None}


@router.get("/{code}/audit-trail")
async def authority_audit_for_code(
    code: str,
    limit: int = Query(50, ge=1, le=200),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Phase 19.9.1 — Audit-trail timeline for a single authority code."""
    if not _can_read(current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    cursor = db["audit_logs"].find(
        {"action": {"$regex": "^authority\\."}, "summary.code": code},
        {"_id": 0},
    ).sort("at", -1).limit(limit)
    items = [_serialise_audit(d) async for d in cursor]
    return {"code": code, "items": items, "count": len(items)}
