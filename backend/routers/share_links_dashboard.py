"""Active Share Links — Admin compliance dashboard.

Lists every share-link issued across PAs (both public share-tokens and magic-portal links)
with metadata: issuer, expiry, click/use count, last access info, status.
Admin can revoke any link with one click.
"""
import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from core.database import db
from routers.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/share-links", tags=["Share Links Dashboard"])

pa_col = db["pre_assessments"]
magic_col = db["magic_links"]
users_col = db["users"]


def _admin_only(u):
    if u.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only — Share Links dashboard is restricted")


def _now():
    return datetime.now(timezone.utc)


def _iso(v):
    if isinstance(v, datetime):
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.isoformat()
    return v


def _link_status(exp, revoked, used=False, share_active=True):
    """Derive a single status string for UI."""
    if revoked:
        return "revoked"
    if used:
        return "consumed"
    if not share_active:
        return "deactivated"
    if exp:
        if isinstance(exp, str):
            try:
                exp = datetime.fromisoformat(exp.replace("Z", "+00:00"))
            except Exception:
                exp = None
        if isinstance(exp, datetime):
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if exp < _now():
                return "expired"
    return "active"


@router.get("/")
async def list_share_links(
    status: Optional[str] = Query(None, description="active | expired | revoked | consumed | deactivated"),
    link_type: Optional[str] = Query(None, description="public_pa_fee | magic_portal"),
    search: Optional[str] = Query(None, description="search by PA number / client name / email"),
    current_user: dict = Depends(get_current_user),
):
    """List all share-links (both public share-tokens and magic links) with metadata."""
    _admin_only(current_user)

    rows: List[dict] = []
    needle = (search or "").strip().lower()

    # 1. Public share-tokens on PAs
    if link_type in (None, "public_pa_fee"):
        async for pa in pa_col.find(
            {"share_token": {"$exists": True, "$ne": None}},
            {
                "_id": 0, "id": 1, "pa_number": 1, "client_name": 1, "client_email": 1,
                "partner_id": 1, "partner_name": 1, "share_token": 1, "share_expires_at": 1,
                "share_active": 1, "share_click_count": 1, "share_last_accessed_at": 1,
                "share_last_accessed_ip": 1, "share_last_accessed_ua": 1,
                "stage": 1, "fee_payment_status": 1, "updated_at": 1,
            },
        ):
            hay = f"{pa.get('pa_number','')} {pa.get('client_name','')} {pa.get('client_email','')}".lower()
            if needle and needle not in hay:
                continue
            st = _link_status(
                pa.get("share_expires_at"),
                revoked=False,
                share_active=pa.get("share_active", True),
            )
            if status and st != status:
                continue
            rows.append({
                "type": "public_pa_fee",
                "token": pa.get("share_token"),
                "token_prefix": (pa.get("share_token") or "")[:10] + "…",
                "pa_id": pa.get("id"),
                "pa_number": pa.get("pa_number"),
                "client_name": pa.get("client_name"),
                "client_email": pa.get("client_email"),
                "partner_name": pa.get("partner_name"),
                "purpose": "pre_assessment_fee",
                "amount_label": "₹5,100",
                "issued_at": _iso(pa.get("updated_at")),
                "expires_at": _iso(pa.get("share_expires_at")),
                "status": st,
                "access_count": pa.get("share_click_count", 0),
                "last_accessed_at": _iso(pa.get("share_last_accessed_at")),
                "last_accessed_ip": pa.get("share_last_accessed_ip"),
                "last_accessed_ua": pa.get("share_last_accessed_ua"),
            })

    # 2. Magic links
    if link_type in (None, "magic_portal"):
        async for m in magic_col.find({}, {"_id": 0}):
            # Lookup the linked PA (best-effort)
            issued_for_pa = m.get("issued_for_pa")
            pa = None
            if issued_for_pa:
                pa = await pa_col.find_one(
                    {"id": issued_for_pa},
                    {"_id": 0, "pa_number": 1, "client_name": 1, "client_email": 1, "partner_name": 1, "stage": 1, "proposal_fee": 1},
                )
            else:
                # Fallback: lookup user → first PA owned
                pa = await pa_col.find_one(
                    {"client_user_id": m.get("user_id")},
                    {"_id": 0, "pa_number": 1, "client_name": 1, "client_email": 1, "partner_name": 1, "stage": 1, "proposal_fee": 1},
                )
            pa = pa or {}

            hay = f"{pa.get('pa_number','')} {pa.get('client_name','')} {pa.get('client_email','')}".lower()
            if needle and needle not in hay:
                continue

            st = _link_status(
                m.get("expires_at"),
                revoked=m.get("revoked", False),
                used=m.get("used", False),
            )
            if status and st != status:
                continue

            stage = pa.get("stage")
            purpose = (
                "preview_only" if m.get("is_preview")
                else "proposal_fee_payment" if stage == "proposal_sent"
                else "view_portal"
            )
            amt = pa.get("proposal_fee") if purpose == "proposal_fee_payment" else 0
            amt_label = (
                f"₹{int(amt or 0):,}" if purpose == "proposal_fee_payment" and amt
                else "Preview" if purpose == "preview_only"
                else "View"
            )
            rows.append({
                "type": "magic_portal",
                "token": m.get("token"),
                "token_prefix": (m.get("token") or "")[:10] + "…",
                "magic_id": m.get("id"),
                "pa_id": issued_for_pa,
                "pa_number": pa.get("pa_number"),
                "client_name": pa.get("client_name"),
                "client_email": pa.get("client_email"),
                "partner_name": pa.get("partner_name"),
                "purpose": purpose,
                "amount_label": amt_label,
                "issued_by": m.get("issued_by"),
                "is_preview": m.get("is_preview", False),
                "issued_at": _iso(m.get("created_at")),
                "expires_at": _iso(m.get("expires_at")),
                "status": st,
                "access_count": 1 if m.get("used") else 0,
                "used_at": _iso(m.get("used_at")),
                "last_accessed_at": _iso(m.get("used_at")),
                "last_accessed_ip": m.get("used_ip"),
                "last_accessed_ua": m.get("used_ua"),
                "revoked_at": _iso(m.get("revoked_at")),
            })

    # Sort newest first
    rows.sort(key=lambda r: r.get("issued_at") or "", reverse=True)

    # Stats
    stats = {"active": 0, "expired": 0, "revoked": 0, "consumed": 0, "deactivated": 0, "total": len(rows)}
    for r in rows:
        stats[r["status"]] = stats.get(r["status"], 0) + 1

    # Suspicious heuristics: high click count without conversion, multiple IPs (we only store last_ip so just flag clicks>=5)
    for r in rows:
        r["suspicious"] = bool(r.get("access_count", 0) >= 5 and r["status"] == "active")

    return {"count": len(rows), "stats": stats, "items": rows}


class RevokeRequest(BaseModel):
    type: str  # "public_pa_fee" | "magic_portal"
    token: str
    reason: Optional[str] = None


@router.post("/revoke")
async def revoke_link(body: RevokeRequest, current_user: dict = Depends(get_current_user)):
    _admin_only(current_user)
    now = _now()

    if body.type == "public_pa_fee":
        res = await pa_col.update_one(
            {"share_token": body.token},
            {"$set": {
                "share_active": False,
                "share_revoked_at": now,
                "share_revoked_by": current_user.get("id"),
                "share_revoke_reason": body.reason,
            }},
        )
        if res.matched_count == 0:
            raise HTTPException(status_code=404, detail="Share token not found")
        return {"ok": True, "revoked_type": "public_pa_fee", "token_prefix": body.token[:10] + "…"}

    if body.type == "magic_portal":
        res = await magic_col.update_one(
            {"token": body.token},
            {"$set": {
                "revoked": True,
                "revoked_at": now,
                "revoked_by": current_user.get("id"),
                "revoke_reason": body.reason,
            }},
        )
        if res.matched_count == 0:
            raise HTTPException(status_code=404, detail="Magic token not found")
        return {"ok": True, "revoked_type": "magic_portal", "token_prefix": body.token[:10] + "…"}

    raise HTTPException(status_code=400, detail="Invalid type — must be 'public_pa_fee' or 'magic_portal'")
