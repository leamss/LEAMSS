"""Option D / X5 — Admin Client-Portal Preview.

Read-only "Client View" — lets admin / case_manager / sales preview EXACTLY what
their client sees, without needing the client's password. Eliminates support
tickets where clients ask "what does my portal look like?".

All preview endpoints are audit-logged. No write operations permitted.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from core.auth import get_current_user
from core.database import db
from services.audit_service import log_action

router = APIRouter(prefix="/admin/client-portal-preview",
                   tags=["X5 Admin Client Preview"])

ALLOWED_ROLES = {"admin", "admin_owner", "super_admin",
                  "case_manager", "case_manager_lead",
                  "sales_manager", "sales_head"}


def _is_authorised(u: Dict[str, Any]) -> bool:
    role = (u.get("rbac_role") or u.get("role") or "").lower()
    perms = u.get("permissions") or []
    return role in ALLOWED_ROLES or "*" in perms or "case.view.any" in perms


async def _require_client_portal(client_id: str) -> Dict[str, Any]:
    portal = await db["client_mini_portals"].find_one(
        {"client_id": client_id}, {"_id": 0, "password_hash": 0, "temp_password": 0},
    )
    if not portal:
        raise HTTPException(404, f"No client portal for {client_id}")
    return portal


async def _audit(user: Dict[str, Any], client_id: str, action: str):
    await log_action(
        db,
        action=f"admin.client_portal_preview.{action}",
        user_id=str(user.get("id") or "unknown"),
        user_name=user.get("name"),
        severity="info",
        summary={"client_id": client_id, "preview_mode": True},
    )


@router.get("/{client_id}/overview")
async def preview_overview(client_id: str,
                            current_user: Dict[str, Any] = Depends(get_current_user)):
    if not _is_authorised(current_user):
        raise HTTPException(403, "Admin/CM/Sales only")
    portal = await _require_client_portal(client_id)
    await _audit(current_user, client_id, "overview")

    # Mirror client-portal/overview shape but from staff context
    pa = await db["pre_assessments"].find_one(
        {"$or": [{"client_user_id": client_id},
                 {"created_by_user_id": client_id}]},
        sort=[("created_at", -1)],
    )
    sheet = await db["information_sheets"].find_one(
        {"id": portal.get("info_sheet_id")}, {"_id": 0}
    ) if portal.get("info_sheet_id") else None
    doc_count = await db["client_documents"].count_documents({"client_id": client_id})
    proposal = await db["proposals"].find_one(
        {"client_id": client_id, "status": {"$in": ["sent", "accepted", "declined"]}},
        {"_id": 0}, sort=[("created_at", -1)],
    )

    timeline = []
    paid = bool(pa and pa.get("payment_status") in ("paid", "completed"))
    timeline.append({"stage": "Pre-Assessment Paid", "status": "done" if paid else "pending"})
    sheet_done = bool(sheet and (sheet.get("personal", {}).get("given_names")))
    timeline.append({"stage": "Info Sheet Started", "status": "done" if sheet_done else "pending"})
    timeline.append({"stage": "Documents Uploaded",
                     "status": "done" if doc_count >= 3 else ("in_progress" if doc_count > 0 else "pending"),
                     "count": doc_count})
    review = await db["pa_reviews"].find_one(
        {"client_id": client_id} if client_id else None, sort=[("created_at", -1)],
    )
    review_status = (review or {}).get("status", "pending")
    timeline.append({"stage": "Under Admin Review",
                     "status": "done" if review_status == "approved" else (
                         "in_progress" if review_status == "pending" else "pending"),
                     "review_status": review_status})
    timeline.append({"stage": "Proposal Received",
                     "status": "done" if proposal else "pending"})
    accepted = bool(proposal and proposal.get("status") == "accepted")
    timeline.append({"stage": "Proposal Accepted", "status": "done" if accepted else "pending"})
    timeline.append({"stage": "Full Case Active", "status": "done" if accepted else "pending"})

    return {
        "_preview_mode": True,
        "_viewing_as": {"client_id": client_id,
                         "client_name": portal.get("client_name"),
                         "client_email": portal.get("client_email")},
        "_audit_actor": {"id": current_user.get("id"), "name": current_user.get("name")},
        "client": {"id": client_id, "name": portal.get("client_name"),
                    "email": portal.get("client_email"),
                    "product_id": portal.get("product_id")},
        "timeline": timeline,
        "summary": {
            "doc_count": doc_count,
            "has_info_sheet": sheet is not None,
            "has_proposal": proposal is not None,
            "proposal_status": (proposal or {}).get("status"),
        },
    }


@router.get("/{client_id}/info-sheet")
async def preview_info_sheet(client_id: str,
                              current_user: Dict[str, Any] = Depends(get_current_user)):
    if not _is_authorised(current_user):
        raise HTTPException(403, "Admin/CM/Sales only")
    portal = await _require_client_portal(client_id)
    await _audit(current_user, client_id, "info_sheet")
    sheet_id = portal.get("info_sheet_id")
    if not sheet_id:
        return {"_preview_mode": True, "info_sheet": None,
                "message": "No info sheet provisioned for this client yet"}
    sheet = await db["information_sheets"].find_one({"id": sheet_id}, {"_id": 0})
    if sheet:
        for k, v in list(sheet.items()):
            if isinstance(v, datetime):
                sheet[k] = v.isoformat()
    return {"_preview_mode": True, "info_sheet": sheet}


@router.get("/{client_id}/documents")
async def preview_documents(client_id: str,
                             current_user: Dict[str, Any] = Depends(get_current_user)):
    if not _is_authorised(current_user):
        raise HTTPException(403, "Admin/CM/Sales only")
    await _require_client_portal(client_id)
    await _audit(current_user, client_id, "documents")

    docs = []
    async for d in db["client_documents"].find({"client_id": client_id}, {"_id": 0}).sort("uploaded_at", -1):
        for k, v in list(d.items()):
            if isinstance(v, datetime):
                d[k] = v.isoformat()
        docs.append(d)
    cats = ["identity", "qualifications", "employment", "english_test", "other"]
    by_cat = {c: [] for c in cats}
    for d in docs:
        by_cat.setdefault(d.get("document_type", "other"), []).append(d)
    return {"_preview_mode": True, "documents": docs,
            "by_category": by_cat, "categories": cats, "total": len(docs)}


@router.get("/{client_id}/proposal")
async def preview_proposal(client_id: str,
                            current_user: Dict[str, Any] = Depends(get_current_user)):
    if not _is_authorised(current_user):
        raise HTTPException(403, "Admin/CM/Sales only")
    await _require_client_portal(client_id)
    await _audit(current_user, client_id, "proposal")
    proposal = await db["proposals"].find_one(
        {"client_id": client_id,
         "status": {"$in": ["sent", "accepted", "declined"]}},
        {"_id": 0}, sort=[("created_at", -1)],
    )
    if proposal:
        for k, v in list(proposal.items()):
            if isinstance(v, datetime):
                proposal[k] = v.isoformat()
    return {"_preview_mode": True, "proposal": proposal,
            "message": None if proposal else "No proposal sent to this client yet"}
