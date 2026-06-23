"""Option 2 — Public Proposal Link.

Sales/admin generates a JWT-signed short URL → client opens in browser → reviews
proposal + accepts/declines without login. Triggers existing Phase 20.8 flow.

Industry: +18-25% conversion uplift vs login-required.

Endpoints (admin/sales auth required for generate/revoke):
  POST  /api/proposals/{id}/generate-public-link
  POST  /api/proposals/{id}/revoke-public-link
Public (no auth, token-based):
  GET   /api/proposals/public/view?t=<token>
  POST  /api/proposals/public/accept?t=<token>
  POST  /api/proposals/public/decline?t=<token>  body: {reason}
  GET   /api/proposals/public/pdf?t=<token>
"""
from __future__ import annotations

import os
import secrets
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional

import jwt
from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field

from core.auth import get_current_user
from core.database import db
from services.audit_service import log_action

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/proposals", tags=["Option 2 Public Proposal Link"])

PROP_COLL = "proposals"
DENYLIST_COLL = "proposal_link_denylist"

# Separate secret (falls back to JWT_SECRET if not set)
PROPOSAL_LINK_SECRET = os.environ.get("PROPOSAL_LINK_SECRET") or os.environ.get(
    "JWT_SECRET", "dev_proposal_link_secret_change_me"
)
LINK_PURPOSE = "proposal_view"
LINK_TTL_DAYS = 30
ADMIN_ROLES = {"admin", "admin_owner", "super_admin", "case_manager",
               "case_manager_lead", "sales", "sales_executive",
               "sr_sales_executive", "sales_manager", "sales_head", "partner"}


def _is_authorised(user: Dict[str, Any]) -> bool:
    role = (user.get("rbac_role") or user.get("role") or "").lower()
    return role in ADMIN_ROLES or "*" in (user.get("permissions") or [])


def _public_base() -> str:
    return (os.environ.get("PUBLIC_SITE_URL")
            or os.environ.get("REACT_APP_BACKEND_URL")
            or "https://app.leamss.com").rstrip("/")


def _make_link_token(proposal_id: str, client_id: str) -> Dict[str, Any]:
    """Sign a JWT token for public proposal viewing (30d TTL)."""
    now = datetime.now(timezone.utc)
    exp = now + timedelta(days=LINK_TTL_DAYS)
    token_id = secrets.token_urlsafe(12)
    payload = {
        "purpose": LINK_PURPOSE,
        "proposal_id": proposal_id,
        "client_id": client_id,
        "nonce": secrets.token_hex(8),
        "token_id": token_id,
        "iat": int(now.timestamp()),
        "exp": exp,
    }
    token = jwt.encode(payload, PROPOSAL_LINK_SECRET, algorithm="HS256")
    return {"token": token, "token_id": token_id, "expires_at": exp.isoformat()}


async def _validate_token(token: str) -> Dict[str, Any]:
    """Decode + check denylist. Raises HTTPException on any failure."""
    if not token:
        raise HTTPException(401, "Invalid link. Contact sales for a new link.")
    try:
        payload = jwt.decode(token, PROPOSAL_LINK_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "This link has expired. Contact sales for a new link.")
    except jwt.DecodeError:
        raise HTTPException(401, "Invalid link. Contact sales for a new link.")
    if payload.get("purpose") != LINK_PURPOSE:
        raise HTTPException(401, "Invalid link purpose")
    denied = await db[DENYLIST_COLL].find_one({"token_id": payload.get("token_id")})
    if denied:
        raise HTTPException(401, "This link has been revoked. Contact sales for a new link.")
    return payload


async def _fetch_proposal(proposal_id: str) -> Dict[str, Any]:
    p = await db[PROP_COLL].find_one({"id": proposal_id}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Proposal not found")
    return p


# ─── ADMIN/SALES — Generate link ─────────────────────────────────────────────
@router.post("/{proposal_id}/generate-public-link")
async def generate_public_link(
    proposal_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not _is_authorised(current_user):
        raise HTTPException(403, "Admin/sales only")
    p = await _fetch_proposal(proposal_id)
    if p.get("status") in ("accepted", "declined"):
        raise HTTPException(409, f"Cannot generate link — proposal already {p['status']}")

    tok = _make_link_token(proposal_id, p.get("client_id", ""))
    public_url = f"{_public_base()}/proposal/view?t={tok['token']}"

    # Persist token_id on proposal record for management
    history = p.get("public_link_history") or []
    history.append({
        "token_id": tok["token_id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": current_user.get("id"),
        "expires_at": tok["expires_at"],
    })
    await db[PROP_COLL].update_one(
        {"id": proposal_id},
        {"$set": {"public_link_history": history,
                  "active_public_token_id": tok["token_id"]}},
    )
    await log_action(
        db, action="proposal.public_link.generated",
        user_id=str(current_user.get("id")), severity="info",
        summary={"proposal_id": proposal_id, "token_id": tok["token_id"]},
    )
    return {
        "ok": True, "proposal_id": proposal_id,
        "public_url": public_url, "token_id": tok["token_id"],
        "expires_at": tok["expires_at"],
    }


@router.post("/{proposal_id}/revoke-public-link")
async def revoke_public_link(
    proposal_id: str, token_id: Optional[str] = Query(default=None),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not _is_authorised(current_user):
        raise HTTPException(403, "Admin/sales only")
    p = await _fetch_proposal(proposal_id)
    tid = token_id or p.get("active_public_token_id")
    if not tid:
        raise HTTPException(404, "No active public link to revoke")
    await db[DENYLIST_COLL].insert_one({
        "token_id": tid,
        "proposal_id": proposal_id,
        "revoked_at": datetime.now(timezone.utc),
        "revoked_by": current_user.get("id"),
    })
    await db[PROP_COLL].update_one(
        {"id": proposal_id},
        {"$set": {"active_public_token_id": None}},
    )
    await log_action(
        db, action="proposal.public_link.revoked",
        user_id=str(current_user.get("id")), severity="info",
        summary={"proposal_id": proposal_id, "token_id": tid},
    )
    return {"ok": True, "revoked_token_id": tid}


# ─── PUBLIC ENDPOINTS (no auth) ──────────────────────────────────────────────
@router.get("/public/view")
async def public_view(t: str = Query(..., min_length=20)):
    payload = await _validate_token(t)
    p = await _fetch_proposal(payload["proposal_id"])
    # Increment view count + first_viewed_at
    upd = {"$inc": {"public_view_count": 1}}
    if not p.get("first_publicly_viewed_at"):
        upd["$set"] = {"first_publicly_viewed_at": datetime.now(timezone.utc).isoformat()}
    await db[PROP_COLL].update_one({"id": p["id"]}, upd)

    # Strip sensitive fields, ISO-format datetimes
    for k, v in list(p.items()):
        if isinstance(v, datetime):
            p[k] = v.isoformat()
    p.pop("public_link_history", None)
    p.pop("active_public_token_id", None)
    return {
        "_public_view": True,
        "proposal": p,
        "pdf_url": f"/api/proposals/public/pdf?t={t}",
        "accept_url": f"/api/proposals/public/accept?t={t}",
        "decline_url": f"/api/proposals/public/decline?t={t}",
    }


@router.post("/public/accept")
async def public_accept(t: str = Query(..., min_length=20)):
    payload = await _validate_token(t)
    p = await _fetch_proposal(payload["proposal_id"])
    if p.get("status") == "accepted":
        return {"ok": True, "already_accepted": True,
                "accepted_at": (p.get("accepted_at") or "").__str__()[:19]}
    if p.get("status") not in ("sent",):
        raise HTTPException(409, f"Cannot accept — current status: {p.get('status')}")
    now = datetime.now(timezone.utc)
    await db[PROP_COLL].update_one(
        {"id": p["id"]},
        {"$set": {"status": "accepted", "accepted_at": now,
                  "accepted_by": "client_public_link",
                  "accepted_via": "public_link",
                  "accepted_token_id": payload.get("token_id")}},
    )
    await log_action(
        db, action="proposal.accepted_via_public_link",
        user_id=p.get("client_id", "unknown"), severity="info",
        summary={"proposal_id": p["id"], "token_id": payload.get("token_id")},
    )
    return {"ok": True, "status": "accepted",
            "redirect_url": "/client-portal/login"}


@router.post("/public/decline")
async def public_decline(
    t: str = Query(..., min_length=20),
    body: Dict[str, Any] = Body(...),
):
    reason = (body.get("reason") or "").strip()
    if len(reason) < 10:
        raise HTTPException(400, "Please provide a reason (minimum 10 characters)")
    payload = await _validate_token(t)
    p = await _fetch_proposal(payload["proposal_id"])
    if p.get("status") == "declined":
        return {"ok": True, "already_declined": True}
    if p.get("status") not in ("sent",):
        raise HTTPException(409, f"Cannot decline — current status: {p.get('status')}")
    now = datetime.now(timezone.utc)
    await db[PROP_COLL].update_one(
        {"id": p["id"]},
        {"$set": {"status": "declined", "declined_at": now,
                  "declined_by": "client_public_link",
                  "declined_via": "public_link",
                  "declined_reason": reason[:500],
                  "declined_token_id": payload.get("token_id")}},
    )
    await log_action(
        db, action="proposal.declined_via_public_link",
        user_id=p.get("client_id", "unknown"), severity="info",
        summary={"proposal_id": p["id"], "token_id": payload.get("token_id"),
                 "reason_len": len(reason)},
    )
    return {"ok": True, "status": "declined"}


@router.get("/public/pdf")
async def public_pdf(t: str = Query(..., min_length=20)):
    payload = await _validate_token(t)
    # Reuse existing PDF generator
    from routers.proposals import _render_proposal_html  # local import to avoid cycle
    p = await _fetch_proposal(payload["proposal_id"])
    html = _render_proposal_html(p)
    try:
        from weasyprint import HTML
        pdf_bytes = HTML(string=html).write_pdf()
        return Response(
            content=pdf_bytes, media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="proposal_{p["id"][:8]}.pdf"'},
        )
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[Option2 public_pdf] WeasyPrint unavailable: {e!r} — returning HTML")
        return Response(content=html, media_type="text/html")
