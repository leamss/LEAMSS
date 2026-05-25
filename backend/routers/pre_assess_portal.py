"""
Pre-Assessment Client Portal Layer (Phase A addon)
--------------------------------------------------
Extends existing `pre_assessments` collection with:
  - Public share-token payment page (no auth)
  - MOCK payment → auto-create client user + magic-link login
  - Magic-link + OTP fallback login
  - Client-side "my pre-assessments" view
  - Client activity tracking (for partner visibility)
  - Portal access level: mini → expanded → full

Reuses existing /api/pre-assessment/* endpoints where possible.
"""
import os
import uuid
import secrets
import random
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr
from fastapi import APIRouter, Depends, HTTPException, Request

from core.auth import get_current_user, get_password_hash, create_access_token
from core.database import db, users_col, notifications_col
from core.integrity import compute_hash
from passlib.context import CryptContext

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pre-assess-portal", tags=["Pre-Assessment Portal"])

pre_assessments_col = db["pre_assessments"]
magic_col = db["magic_links"]
otp_col = db["otp_codes"]
activity_col = db["client_activity"]

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ======================== MODELS ========================
class GenerateLinkRequest(BaseModel):
    pa_id: str
    expires_in_days: Optional[int] = 30  # 1, 7, 30, 90, or 0 = never


class PublicMockPayRequest(BaseModel):
    token: str


class MagicLoginRequest(BaseModel):
    token: str


class OTPReq(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None


class OTPVerify(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    code: str


class ActivityLogRequest(BaseModel):
    action: str
    pa_id: Optional[str] = None
    metadata: Dict[str, Any] = {}


# ======================== HELPERS ========================
def _now() -> datetime:
    return datetime.now(timezone.utc)


def _frontend_url() -> str:
    return (os.environ.get("FRONTEND_URL")
            or os.environ.get("REACT_APP_BACKEND_URL") or "").rstrip("/")


async def _log(user_id: str, pa_id: Optional[str], action: str, metadata: Optional[Dict] = None):
    try:
        await activity_col.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "pa_id": pa_id,
            "action": action,
            "metadata": metadata or {},
            "created_at": _now(),
        })
    except Exception as e:
        logger.warning(f"activity log failed: {e}")


async def _mock_send(channel: str, to: str, subject: str, body: str):
    logger.info(f"[{channel.upper()} MOCK] to={to} | {subject} | {body[:180]}")


# ======================== PARTNER: GENERATE PUBLIC LINK ========================
@router.post("/generate-public-link")
async def generate_public_link(data: GenerateLinkRequest, current_user: dict = Depends(get_current_user)):
    """Smart link generator. Returns the right link for the PA's current stage:

      • Fee NOT paid (new / payment_pending)         → public ₹5,100 payment link (share-token)
      • Fee paid + Proposal sent + not yet accepted  → magic link to client MiniPortal (pay proposal fee)
      • Already in case_created / refund states      → magic link to portal (read-only view)

    `expires_in_days`: 1, 7, 30, 90, or 0 = never expires.
    """
    pa = await pre_assessments_col.find_one({"id": data.pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Pre-assessment not found")

    # Phase 4A-aligned auth: admin OR (owner with pa.share.own permission).
    # Ownership = partner_id (legacy / sales-exec PAs use this) OR created_by_user_id (Phase 4A field).
    is_admin = (
        current_user.get("role") in ("admin", "admin_owner")
        or current_user.get("rbac_role") in ("admin", "admin_owner")
    )
    is_owner = (
        pa.get("partner_id") == current_user["id"]
        or pa.get("created_by_user_id") == current_user["id"]
    )
    has_share_perm = "pa.share.own" in (current_user.get("permissions") or [])
    if not is_admin and not (is_owner and has_share_perm):
        creator_msg = ""
        if not is_owner:
            creator_msg = " This PA was created by another user — only the creator or an admin can share it."
        raise HTTPException(status_code=403, detail=f"Not allowed to share this pre-assessment.{creator_msg}")

    # Validate expiry
    days = data.expires_in_days if data.expires_in_days is not None else 30
    if days not in (0, 1, 7, 30, 90):
        raise HTTPException(status_code=400, detail="expires_in_days must be 0 (never), 1, 7, 30, or 90")

    # Phase 4D — Express + Token mode special case:
    # PA starts at stage="approved" (auto-approved for Token mode) but client hasn't paid the
    # token yet. We must NOT treat this as "fee_paid" — the partner needs the public BRANCH-A
    # link so the client can pay the small token amount via the public payment portal.
    is_express_token_unpaid = (
        pa.get("sale_type") == "express"
        and (pa.get("express_mode") or "direct") == "token"
        and not pa.get("express_token_paid", False)
    )
    fee_paid = (not is_express_token_unpaid) and (
        pa.get("fee_payment_status") == "paid" or pa.get("stage") in (
            "payment_received", "documents_submitted", "partner_review", "under_review",
            "approved", "proposal_sent", "proposal_paid", "awaiting_final_approval", "case_created",
        )
    )
    has_user = bool(pa.get("client_user_id"))

    base = _frontend_url()

    # ----------- BRANCH A: Fee not yet paid → public share-token link -----------
    if not fee_paid:
        token = pa.get("share_token") or secrets.token_urlsafe(22)
        expires_at = None if days == 0 else _now() + timedelta(days=days)
        await pre_assessments_col.update_one({"id": data.pa_id}, {"$set": {
            "share_token": token,
            "share_expires_at": expires_at,
            "share_active": True,
            "updated_at": _now(),
        }})
        public_url = f"{base}/pre-assess/{token}" if base else f"/pre-assess/{token}"
        # Phase 4D — Express + Token mode link semantics
        is_express = pa.get("sale_type") == "express"
        mode = pa.get("express_mode") or "direct"
        if is_express and mode == "token":
            link_type = "express_token_payment"
            amount = float(pa.get("express_token_amount") or 0)
            amount_label = f"₹{int(amount):,}"
            purpose = "express_token_payment"
        elif is_express and mode == "direct":
            link_type = "express_direct_preview"
            amount = 0
            amount_label = "Free (Express)"
            purpose = "express_direct_preview"
        else:
            link_type = "public_pa_fee"
            amount = 5100
            amount_label = "₹5,100"
            purpose = "pre_assessment_fee"
        await _log(current_user["id"], data.pa_id, "share_link_generated", {
            "type": link_type, "expires_in_days": days,
        })
        return {
            "token": token,
            "public_url": public_url,
            "link_type": link_type,
            "amount": amount,
            "amount_label": amount_label,
            "purpose": purpose,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "expires_in_days": days,
            "client_name": pa.get("client_name"),
            "client_email": pa.get("client_email"),
            "client_mobile": pa.get("client_mobile"),
        }

    # ----------- BRANCH B: Fee paid → magic link to MiniPortal -----------
    if not has_user:
        raise HTTPException(status_code=400, detail="Client account not linked yet — wait for client to complete payment")

    minutes = 60 * 24 * days if days > 0 else 60 * 24 * 365 * 5  # "never" = 5 years
    magic_token = secrets.token_urlsafe(22)
    await magic_col.insert_one({
        "id": str(uuid.uuid4()),
        "token": magic_token,
        "user_id": pa["client_user_id"],
        "expires_at": _now() + timedelta(minutes=minutes),
        "used": False,
        "is_preview": False,  # real client login, not preview
        "issued_by": current_user["id"],
        "issued_for_pa": data.pa_id,
        "created_at": _now(),
    })
    portal_url = f"{base}/magic/{magic_token}" if base else f"/magic/{magic_token}"

    proposal_pending = pa.get("stage") == "proposal_sent" and pa.get("proposal_status") in (None, "sent", "accepted")
    purpose = "proposal_fee_payment" if proposal_pending else "view_portal"
    amount = int(pa.get("proposal_fee") or 0) if proposal_pending else 0
    amount_label = (
        f"₹{amount:,.0f}" if proposal_pending and amount > 0 else "—"
    )

    await _log(current_user["id"], data.pa_id, "share_link_generated", {
        "type": "magic_portal", "purpose": purpose, "expires_in_days": days,
    })
    return {
        "token": magic_token,
        "public_url": portal_url,
        "link_type": "magic_portal",
        "amount": amount,
        "amount_label": amount_label,
        "purpose": purpose,
        "expires_at": (_now() + timedelta(minutes=minutes)).isoformat(),
        "expires_in_days": days,
        "client_name": pa.get("client_name"),
        "client_email": pa.get("client_email"),
        "client_mobile": pa.get("client_mobile"),
        "proposal_fee": pa.get("proposal_fee"),
    }


# ======================== PARTNER: PREVIEW AS CLIENT ========================
@router.post("/partner/preview-magic/{pa_id}")
async def partner_preview_magic(pa_id: str, current_user: dict = Depends(get_current_user)):
    """Partner-only: generate a short-lived magic link to preview the client portal/MiniPortal.
    Useful for demos / support. Works only on PAs where client has paid.
    """
    # Phase 4A-aligned: admin OR ownership (partner_id/created_by_user_id)
    is_admin = (current_user.get("role") in ("admin", "admin_owner") or current_user.get("rbac_role") in ("admin", "admin_owner"))
    is_owner = (pa_id is not None)  # ownership check happens below after PA fetch
    if not is_admin and current_user.get("role") not in ("partner", "sales_executive", "sr_sales_executive", "sales_manager", "sales_head"):
        raise HTTPException(status_code=403, detail="Sales / partners / admins only")

    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Pre-assessment not found")
    # Ownership: admin can preview any PA; everyone else must own it via partner_id or created_by_user_id
    if not is_admin:
        owns = pa.get("partner_id") == current_user["id"] or pa.get("created_by_user_id") == current_user["id"]
        if not owns:
            raise HTTPException(status_code=403, detail="Not your pre-assessment")

    # Must have a client user linked
    client_user = None
    if pa.get("client_user_id"):
        client_user = await users_col.find_one({"id": pa["client_user_id"]}, {"_id": 0})
    if not client_user and pa.get("client_email"):
        client_user = await users_col.find_one({"email": pa["client_email"].lower()}, {"_id": 0})
    if not client_user:
        raise HTTPException(status_code=400, detail="Client has not paid yet — share public payment link first")

    magic_token = secrets.token_urlsafe(22)
    await magic_col.insert_one({
        "id": str(uuid.uuid4()),
        "token": magic_token,
        "user_id": client_user["id"],
        "expires_at": _now() + timedelta(minutes=30),  # short-lived for preview
        "used": False,
        "is_preview": True,
        "issued_by": current_user["id"],
        "created_at": _now(),
    })
    base = _frontend_url()
    portal_url = f"{base}/magic/{magic_token}" if base else f"/magic/{magic_token}"
    await _log(current_user["id"], pa_id, "partner_preview_as_client", {})
    return {"portal_url": portal_url, "expires_in_minutes": 30}


# ======================== PUBLIC: VIEW LINK ========================
@router.get("/public/{token}")
async def public_view(token: str, request: Request):
    pa = await pre_assessments_col.find_one(
        {"share_token": token},
        {"_id": 0, "partner_id": 0, "admin_notes": 0},
    )
    if not pa or not pa.get("share_active"):
        raise HTTPException(status_code=404, detail="Link not found or deactivated")

    exp = pa.get("share_expires_at")
    if isinstance(exp, datetime):
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < _now():
            raise HTTPException(status_code=410, detail="Link expired")

    # Track click + last access
    await pre_assessments_col.update_one(
        {"share_token": token},
        {
            "$inc": {"share_click_count": 1},
            "$set": {
                "share_last_accessed_at": _now(),
                "share_last_accessed_ip": (request.client.host if request and request.client else None),
                "share_last_accessed_ua": (request.headers.get("user-agent", "")[:120] if request else ""),
            },
        },
    )

    for k in ("created_at", "updated_at", "share_expires_at"):
        if isinstance(pa.get(k), datetime):
            pa[k] = pa[k].isoformat()
    return pa


@router.post("/public/mock-pay")
async def public_mock_pay(data: PublicMockPayRequest):
    """Mock payment for testing. Creates client user + magic link. Sets stage=payment_received."""
    pa = await pre_assessments_col.find_one({"share_token": data.token}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Link not found")

    # Phase 4D — Express+Token PAs auto-start at stage="approved" (admin auto-approval).
    # Don't let that fool us into thinking the token has already been paid.
    is_express_token = pa.get("sale_type") == "express" and (pa.get("express_mode") or "direct") == "token"
    if is_express_token:
        already_paid = bool(pa.get("express_token_paid"))
    else:
        already_paid = pa.get("fee_payment_status") == "paid" or pa.get("stage") in (
            "payment_received", "documents_submitted", "under_review",
            "approved", "rejected", "proposal_sent", "proposal_paid", "case_created",
        )

    # Ensure user exists
    existing = await users_col.find_one({"email": pa["client_email"]}, {"_id": 0})
    if existing:
        user = existing
    else:
        user_id = str(uuid.uuid4())
        temp_pw = secrets.token_urlsafe(10)
        user = {
            "id": user_id,
            "name": pa.get("client_name", ""),
            "email": pa["client_email"].lower(),
            "phone": pa.get("client_mobile", ""),
            "password_hash": get_password_hash(temp_pw),
            "role": "client",
            "status": "active",
            "source": "pre_assessment_portal",
            "partner_id": pa.get("partner_id"),
            "created_at": _now(),
            "updated_at": _now(),
        }
        await users_col.insert_one(user)
        await _mock_send("email", user["email"], "Your LEAMSS client portal",
            f"Welcome {user['name']}! Your account is ready.")

    if not already_paid:
        # Phase 4D — Express + Token mode payment flow
        if is_express_token:
            update = {
                "express_token_paid": True,
                "express_token_paid_at": _now(),
                "express_token_payment_ref": f"TOKEN-{secrets.token_hex(8)}",
                "client_user_id": user["id"],
                "stage": "express_token_paid",  # Awaiting admin review of token payment + docs
                "updated_at": _now(),
            }
        else:
            update = {
                "stage": "payment_received",
                "fee_payment_status": "paid",
                "fee_paid_at": _now(),
                "fee_payment_ref": f"MOCK-{secrets.token_hex(8)}",
                "client_user_id": user["id"],
                "updated_at": _now(),
            }
        await pre_assessments_col.update_one(
            {"share_token": data.token},
            {"$set": update},
        )
        # Notify partner + admin (admin gets a fresh review queue entry for Express token PAs)
        notif_msg = (
            f"Token of ₹{int(pa.get('express_token_amount') or 0):,} received for {pa.get('client_name')}. Review payment & documents."
            if is_express_token else
            f"Pre-assessment fee paid by {pa.get('client_name')}. Review and approve."
        )
        if pa.get("partner_id"):
            await notifications_col.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": pa["partner_id"],
                "title": "Express token received — review pending" if is_express_token else "Pre-assessment payment received",
                "message": notif_msg,
                "type": "payment", "read": False,
                "link": "/partner?tab=pre-assessment",
                "created_at": _now(),
            })

    # Issue fresh magic link
    magic_token = secrets.token_urlsafe(22)
    await magic_col.insert_one({
        "id": str(uuid.uuid4()),
        "token": magic_token,
        "user_id": user["id"],
        "expires_at": _now() + timedelta(hours=72),
        "used": False,
        "created_at": _now(),
    })
    base = _frontend_url()
    portal_link = f"{base}/magic/{magic_token}" if base else f"/magic/{magic_token}"

    await _mock_send("email", user["email"], "Upload your pre-assessment documents",
        f"Click to access your portal (valid 72h): {portal_link}")

    await _log(user["id"], pa["id"], "pre_assess_paid", {"amount": 5100})

    return {
        "ok": True,
        "already_paid": already_paid,
        "pa_id": pa["id"],
        "magic_link": portal_link,
        "user_email": user["email"],
    }


# ======================== MAGIC + OTP LOGIN ========================
@router.post("/magic-login")
async def magic_login(data: MagicLoginRequest, request: Request):
    doc = await magic_col.find_one({"token": data.token}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Invalid login link")
    if doc.get("revoked"):
        raise HTTPException(status_code=410, detail="Link revoked by admin")
    if doc.get("used"):
        raise HTTPException(status_code=410, detail="Link already used — request a fresh one")
    exp = doc.get("expires_at")
    if isinstance(exp, datetime):
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < _now():
            raise HTTPException(status_code=410, detail="Link expired")

    user = await users_col.find_one({"id": doc["user_id"]}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await magic_col.update_one({"token": data.token}, {"$set": {
        "used": True,
        "used_at": _now(),
        "used_ip": (request.client.host if request and request.client else None),
        "used_ua": (request.headers.get("user-agent", "")[:120] if request else ""),
    }})
    jwt_token = create_access_token({"sub": user["id"], "email": user["email"], "role": user["role"]})
    await _log(user["id"], None, "magic_login")
    return {"token": jwt_token, "user": user}


@router.post("/otp/request")
async def otp_request(data: OTPReq):
    if not data.email and not data.phone:
        raise HTTPException(status_code=400, detail="email or phone required")
    q: Dict[str, Any] = {}
    if data.email:
        q["email"] = data.email.lower()
    else:
        q["phone"] = data.phone
    user = await users_col.find_one(q, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=404, detail="No account found — complete payment first")

    code = f"{random.randint(100000, 999999)}"
    await otp_col.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "email": user.get("email"),
        "phone": user.get("phone"),
        "code_hash": get_password_hash(code),
        "expires_at": _now() + timedelta(minutes=10),
        "consumed": False,
        "created_at": _now(),
    })
    channel = "email" if data.email else "whatsapp"
    await _mock_send(channel, data.email or data.phone or "", "Your OTP", f"Code: {code} (valid 10 min)")
    masked = (data.email or data.phone or "")[:3] + "***"
    return {"sent": True, "channel": channel, "masked": masked}


@router.post("/otp/verify")
async def otp_verify(data: OTPVerify):
    if not data.email and not data.phone:
        raise HTTPException(status_code=400, detail="email or phone required")
    q: Dict[str, Any] = {"consumed": False}
    if data.email:
        q["email"] = data.email.lower()
    else:
        q["phone"] = data.phone
    candidates = await otp_col.find(q).sort("created_at", -1).to_list(5)
    match = None
    for c in candidates:
        exp = c.get("expires_at")
        if isinstance(exp, datetime):
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if exp < _now():
                continue
        try:
            if _pwd.verify(data.code, c["code_hash"]):
                match = c
                break
        except Exception:
            continue
    if not match:
        raise HTTPException(status_code=401, detail="Invalid or expired OTP")
    await otp_col.update_one({"_id": match["_id"]}, {"$set": {"consumed": True, "consumed_at": _now()}})
    user = await users_col.find_one({"id": match["user_id"]}, {"_id": 0, "password_hash": 0})
    jwt_token = create_access_token({"sub": user["id"], "email": user["email"], "role": user["role"]})
    await _log(user["id"], None, "otp_login")
    return {"token": jwt_token, "user": user}


# ======================== CLIENT PORTAL VIEWS ========================
@router.get("/client/my-assessments")
async def client_my_assessments(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "client":
        raise HTTPException(status_code=403, detail="Client only")
    # Match by either email OR explicit client_user_id
    q = {"$or": [
        {"client_email": current_user.get("email", "").lower()},
        {"client_user_id": current_user["id"]},
    ]}
    items = await pre_assessments_col.find(q, {"_id": 0, "partner_id": 0}).sort("created_at", -1).to_list(50)
    for it in items:
        for k in ("created_at", "updated_at", "fee_paid_at", "share_expires_at"):
            if isinstance(it.get(k), datetime):
                it[k] = it[k].isoformat()
    return {"assessments": items, "total": len(items)}


@router.post("/client/submit/{pa_id}")
async def client_submit_for_review(pa_id: str, current_user: dict = Depends(get_current_user)):
    """Client marks their uploaded documents as ready for partner review.
    Transitions stage: payment_received -> documents_submitted.
    """
    if current_user.get("role") != "client":
        raise HTTPException(status_code=403, detail="Client only")

    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa or (pa.get("client_email", "").lower() != current_user.get("email", "").lower()
                  and pa.get("client_user_id") != current_user["id"]):
        raise HTTPException(status_code=404, detail="Pre-assessment not found")

    if pa.get("stage") not in ("payment_received",):
        raise HTTPException(status_code=400, detail=f"Cannot submit at stage: {pa.get('stage')}")

    # Verify at least 1 doc uploaded
    docs_count = await db["pre_assessment_documents"].count_documents({"pre_assessment_id": pa_id})
    if docs_count == 0:
        raise HTTPException(status_code=400, detail="Please upload at least one document before submitting")

    # NEW FLOW: Client submits → Partner reviews → Partner forwards → Admin reviews
    await pre_assessments_col.update_one({"id": pa_id}, {"$set": {
        "stage": "partner_review",
        "client_submitted_at": _now(),
        "updated_at": _now(),
    }})

    # Notify partner — ACTION REQUIRED
    if pa.get("partner_id"):
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": pa["partner_id"],
            "title": "Action needed: Review client documents",
            "message": f"{pa.get('client_name')} has uploaded {docs_count} document(s). Review & forward to Admin.",
            "type": "pre_assess_partner_review",
            "read": False,
            "link": "/partner?tab=pre-assessment",
            "created_at": _now(),
        })

    await _log(current_user["id"], pa_id, "client_submitted_for_review", {"documents_count": docs_count})

    return {"ok": True, "stage": "partner_review", "documents_count": docs_count}


# ============== PARTNER: FORWARD TO ADMIN ==============
class PartnerForwardRequest(BaseModel):
    remarks: Optional[str] = ""


@router.post("/partner/forward-to-admin/{pa_id}")
async def partner_forward_to_admin(pa_id: str, data: PartnerForwardRequest, current_user: dict = Depends(get_current_user)):
    """Partner reviews client's uploaded documents and forwards to Admin for 1st approval."""
    is_admin = (current_user.get("role") in ("admin", "admin_owner") or current_user.get("rbac_role") in ("admin", "admin_owner"))
    if not is_admin and current_user.get("role") not in ("partner", "sales_executive", "sr_sales_executive", "sales_manager", "sales_head"):
        raise HTTPException(status_code=403, detail="Sales / partners / admins only")

    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Pre-assessment not found")
    if not is_admin:
        owns = pa.get("partner_id") == current_user["id"] or pa.get("created_by_user_id") == current_user["id"]
        if not owns:
            raise HTTPException(status_code=403, detail="Not your pre-assessment")
    if pa.get("stage") != "partner_review":
        raise HTTPException(status_code=400, detail=f"Cannot forward at stage: {pa.get('stage')}")

    await pre_assessments_col.update_one({"id": pa_id}, {"$set": {
        "stage": "documents_submitted",
        "partner_remarks": data.remarks or "",
        "partner_forwarded_at": _now(),
        "submitted_at": _now(),
        "updated_at": _now(),
    }})

    # Notify admins
    admins = await users_col.find({"role": "admin", "status": "active"}, {"_id": 0, "id": 1}).to_list(50)
    for admin in admins:
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": admin["id"],
            "title": "Pre-Assessment ready for review",
            "message": f"{pa.get('client_name')} ({pa.get('country')} - {pa.get('service_type')}) forwarded by {current_user.get('name', 'Partner')}",
            "type": "pre_assessment_review", "read": False,
            "link": "/admin?tab=pre-assessments",
            "created_at": _now(),
        })

    await _log(current_user["id"], pa_id, "partner_forwarded_to_admin", {"remarks": data.remarks or ""})
    return {"ok": True, "stage": "documents_submitted"}


@router.get("/client/portal-access/{pa_id}")
async def client_portal_access(pa_id: str, current_user: dict = Depends(get_current_user)):
    """Returns current portal access level for a pre-assessment (mini/expanded/full)."""
    if current_user.get("role") != "client":
        raise HTTPException(status_code=403, detail="Client only")
    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0, "partner_id": 0})
    if not pa or (pa.get("client_email", "").lower() != current_user.get("email", "").lower()
                  and pa.get("client_user_id") != current_user["id"]):
        raise HTTPException(status_code=404, detail="Not found")

    stage = pa.get("stage", "new")
    access_level = "none"
    if stage in ("payment_received", "partner_review", "documents_submitted", "under_review", "rejected", "refund_initiated", "refunded"):
        access_level = "mini"  # can upload docs only (view-only after submission)
    elif stage in ("approved", "proposal_sent"):
        access_level = "expanded"  # can explore tools, proposal, pay service fee
    elif stage in ("proposal_paid", "awaiting_final_approval", "case_created"):
        access_level = "full"  # full portal

    return {
        "pa_id": pa_id,
        "stage": stage,
        "access_level": access_level,
        "can_upload_docs": stage == "payment_received",
        "can_submit_for_review": stage == "payment_received",
        "can_view_proposal": stage in ("proposal_sent", "proposal_paid", "case_created"),
        "can_pay_service_fee": stage == "proposal_sent",
    }


# ======================== CLIENT: PROPOSAL ACCEPT + MAIN FEE MOCK PAY ========================
@router.post("/client/accept-proposal/{pa_id}")
async def client_accept_proposal(pa_id: str, current_user: dict = Depends(get_current_user)):
    """Client accepts the sales proposal. Marks proposal as accepted (ready for main payment)."""
    if current_user.get("role") != "client":
        raise HTTPException(status_code=403, detail="Client only")
    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa or (pa.get("client_email", "").lower() != current_user.get("email", "").lower()
                  and pa.get("client_user_id") != current_user["id"]):
        raise HTTPException(status_code=404, detail="Not found")
    if pa.get("stage") != "proposal_sent":
        raise HTTPException(status_code=400, detail=f"Cannot accept at stage: {pa.get('stage')}")

    await pre_assessments_col.update_one({"id": pa_id}, {"$set": {
        "proposal_status": "accepted",
        "proposal_accepted_at": _now(),
        "updated_at": _now(),
    }})
    await _log(current_user["id"], pa_id, "proposal_accepted", {})
    return {"ok": True, "proposal_status": "accepted"}


@router.post("/client/proposal-consent/{pa_id}")
async def client_proposal_consent(pa_id: str, current_user: dict = Depends(get_current_user)):
    """Client confirms they've reviewed the proposal + T&C before payment. Records timestamp
    AND triggers a (MOCK) consent-summary email with a legal Reference ID for paper-trail."""
    if current_user.get("role") != "client":
        raise HTTPException(status_code=403, detail="Client only")
    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa or (pa.get("client_email", "").lower() != current_user.get("email", "").lower()
                  and pa.get("client_user_id") != current_user["id"]):
        raise HTTPException(status_code=404, detail="Not found")
    if pa.get("stage") != "proposal_sent":
        raise HTTPException(status_code=400, detail=f"Cannot give consent at stage: {pa.get('stage')}")

    now = _now()
    reference_id = f"CON-{(pa.get('pa_number') or pa_id[:8]).upper()}-{now.strftime('%y%m%d%H%M')}"

    await pre_assessments_col.update_one({"id": pa_id}, {"$set": {
        "proposal_consent_given": True,
        "proposal_consent_at": now,
        "proposal_consent_reference_id": reference_id,
        "updated_at": now,
    }})
    await _log(current_user["id"], pa_id, "proposal_consent_given", {"reference_id": reference_id})

    # Build consent summary payload (MOCK email persisted for records)
    upsells = pa.get("proposal_upsells") or []
    summary = {
        "id": str(uuid.uuid4()),
        "reference_id": reference_id,
        "pre_assessment_id": pa_id,
        "pa_number": pa.get("pa_number"),
        "channel": "email",
        "to_email": pa.get("client_email"),
        "to_name": pa.get("client_name"),
        "partner_name": pa.get("partner_name"),
        "subject": f"Your proposal consent summary — {reference_id}",
        "body_snapshot": {
            "base_fee": float(pa.get("proposal_base_fee") or 0),
            "promo_code": pa.get("proposal_promo_code"),
            "promo_discount": float(pa.get("proposal_promo_discount") or 0),
            "custom_discount": float(pa.get("proposal_additional_discount") or 0),
            "upsells": [{"name": u.get("name"), "amount": float(u.get("amount") or 0)} for u in upsells],
            "upsell_total": float(pa.get("proposal_upsell_total") or 0),
            "final_amount": float(pa.get("proposal_fee") or 0),
            "consent_at": now.isoformat(),
            "country": pa.get("country"),
            "service_type": pa.get("service_type"),
        },
        "mode": "mock",
        "created_at": now,
    }
    summary["integrity_hash"] = compute_hash("consent", summary)
    await db["proposal_consent_emails"].insert_one(summary)
    summary.pop("_id", None)
    summary["created_at"] = summary["created_at"].isoformat()

    # In-app notification to client for confirmation
    await notifications_col.insert_one({
        "id": str(uuid.uuid4()), "user_id": current_user["id"],
        "title": "Consent Summary Emailed",
        "message": f"Consent summary sent to {pa.get('client_email')}. Reference: {reference_id}",
        "type": "consent_summary", "read": False,
        "created_at": now,
    })
    # Partner notification
    if pa.get("partner_id"):
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()), "user_id": pa["partner_id"],
            "title": "Client Signed Consent",
            "message": f"{pa.get('client_name')} accepted the proposal. Reference: {reference_id}",
            "type": "consent_summary", "read": False,
            "created_at": now,
        })

    return {"ok": True, "consent_given": True, "reference_id": reference_id, "summary": summary}


@router.get("/client/consent-summary/{pa_id}")
async def get_consent_summary(pa_id: str, current_user: dict = Depends(get_current_user)):
    """Fetch the archived consent summary (for both client + partner + admin)."""
    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Not found")
    role = current_user.get("role")
    if role == "client":
        if (pa.get("client_email") or "").lower() != (current_user.get("email") or "").lower() and pa.get("client_user_id") != current_user["id"]:
            raise HTTPException(status_code=403, detail="Not authorized")
    elif role in ("partner", "sales_executive", "sr_sales_executive"):
        if pa.get("partner_id") != current_user["id"]:
            raise HTTPException(status_code=403, detail="Not authorized")
    elif role not in ("admin", "case_manager"):
        raise HTTPException(status_code=403, detail="Not authorized")
    rec = await db["proposal_consent_emails"].find_one({"pre_assessment_id": pa_id}, {"_id": 0}, sort=[("created_at", -1)])
    if not rec:
        return {"exists": False}
    if hasattr(rec.get("created_at"), "isoformat"):
        rec["created_at"] = rec["created_at"].isoformat()
    return {"exists": True, "record": rec}


@router.post("/client/mock-pay-proposal/{pa_id}")
async def client_mock_pay_proposal(pa_id: str, current_user: dict = Depends(get_current_user)):
    """MOCK main-fee payment. On success, marks proposal_paid (awaits partner to upload receipt + submit final)."""
    if current_user.get("role") != "client":
        raise HTTPException(status_code=403, detail="Client only")
    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa or (pa.get("client_email", "").lower() != current_user.get("email", "").lower()
                  and pa.get("client_user_id") != current_user["id"]):
        raise HTTPException(status_code=404, detail="Not found")
    if pa.get("stage") != "proposal_sent":
        raise HTTPException(status_code=400, detail=f"Cannot pay at stage: {pa.get('stage')}")
    if not pa.get("proposal_consent_given"):
        raise HTTPException(status_code=400, detail="Please confirm the proposal consent before paying")

    await pre_assessments_col.update_one({"id": pa_id}, {"$set": {
        "stage": "proposal_paid",
        "proposal_status": "paid",
        "proposal_paid_at": _now(),
        "proposal_payment_ref": f"MOCK-{secrets.token_hex(8)}",
        "updated_at": _now(),
    }})

    # Phase 7.3.5 — Auto-upgrade attached report snapshots from teaser → full
    try:
        from core.report_tier_hook import auto_upgrade_report_tiers_for_pa
        upgrade_result = await auto_upgrade_report_tiers_for_pa(
            pa_id, "proposal_paid", payment_ref=f"MAIN_FEE_{pa_id}",
        )
        await _log(current_user["id"], pa_id, "report_tier_auto_upgrade", upgrade_result)
    except Exception as e:
        logger.exception("Tier auto-upgrade failed for PA %s: %s", pa_id, e)

    # Notify partner — PARTNER ACTION NEEDED (upload receipt + agreement)
    if pa.get("partner_id"):
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": pa["partner_id"],
            "title": "Main fee received — upload receipt & agreement",
            "message": f"{pa.get('client_name')} paid ₹{pa.get('proposal_fee', 0):,}. Upload payment receipt + agreement + any basic docs, then submit to Admin for final approval.",
            "type": "main_fee_paid_to_partner", "read": False,
            "link": "/partner?tab=pre-assessment",
            "created_at": _now(),
        })

    await _log(current_user["id"], pa_id, "main_fee_paid", {"amount": pa.get("proposal_fee", 0)})
    return {"ok": True, "stage": "proposal_paid"}


# ============== PARTNER: SUBMIT FINAL DOCS → ADMIN 2ND APPROVAL ==============
class PartnerSubmitFinalRequest(BaseModel):
    notes: Optional[str] = ""


@router.post("/partner/submit-final/{pa_id}")
async def partner_submit_final(pa_id: str, data: PartnerSubmitFinalRequest, current_user: dict = Depends(get_current_user)):
    """Partner uploads payment receipt/agreement (via regular document upload endpoint), then
    submits the PA to Admin for final 2nd approval. Transitions proposal_paid → awaiting_final_approval."""
    is_admin = (current_user.get("role") in ("admin", "admin_owner") or current_user.get("rbac_role") in ("admin", "admin_owner"))
    if not is_admin and current_user.get("role") not in ("partner", "sales_executive", "sr_sales_executive", "sales_manager", "sales_head"):
        raise HTTPException(status_code=403, detail="Sales / partners / admins only")

    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Pre-assessment not found")
    if not is_admin:
        owns = pa.get("partner_id") == current_user["id"] or pa.get("created_by_user_id") == current_user["id"]
        if not owns:
            raise HTTPException(status_code=403, detail="Not your pre-assessment")
    if pa.get("stage") != "proposal_paid":
        raise HTTPException(status_code=400, detail=f"Cannot submit-final at stage: {pa.get('stage')}")

    # Require at least 1 doc (receipt / agreement)
    final_docs_count = await db["pre_assessment_documents"].count_documents({"pre_assessment_id": pa_id})
    # Count includes earlier client docs — that's OK. We just ensure something exists.
    if final_docs_count == 0:
        raise HTTPException(status_code=400, detail="Upload receipt/agreement before submitting")

    await pre_assessments_col.update_one({"id": pa_id}, {"$set": {
        "stage": "awaiting_final_approval",
        "partner_final_notes": data.notes or "",
        "partner_final_submitted_at": _now(),
        "updated_at": _now(),
    }})

    # Notify admins
    admins = await users_col.find({"role": "admin", "status": "active"}, {"_id": 0, "id": 1}).to_list(50)
    for admin in admins:
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": admin["id"],
            "title": "Ready for final approval — create case",
            "message": f"{pa.get('client_name')} main fee paid + partner uploaded final docs. Activate case and assign CM.",
            "type": "awaiting_final_approval", "read": False,
            "link": "/admin?tab=pre-assessments",
            "created_at": _now(),
        })

    await _log(current_user["id"], pa_id, "partner_submitted_final", {"notes": data.notes or ""})
    return {"ok": True, "stage": "awaiting_final_approval"}


# ======================== ADMIN: 2ND APPROVAL → CREATE CASE ========================
class AdminApproveFinalRequest(BaseModel):
    case_manager_id: Optional[str] = None


@router.get("/admin/case-managers")
async def admin_list_case_managers(current_user: dict = Depends(get_current_user)):
    """List active case managers for the Assign CM dropdown on 2nd admin approval."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    cms = await users_col.find(
        {"role": "case_manager", "status": "active"},
        {"_id": 0, "id": 1, "name": 1, "email": 1},
    ).sort("name", 1).to_list(100)
    return {"case_managers": cms}


@router.post("/admin/approve-final/{pa_id}")
async def admin_approve_final(pa_id: str, data: Optional[AdminApproveFinalRequest] = None, current_user: dict = Depends(get_current_user)):
    """Admin's 2nd approval after main fee is paid. Creates the actual Case and links the client."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Pre-assessment not found")
    if pa.get("stage") not in ("proposal_paid", "awaiting_final_approval"):
        raise HTTPException(status_code=400, detail=f"Cannot finalize at stage: {pa.get('stage')}")

    cases_col = db["cases"]
    case_steps_col = db["case_steps"]
    workflow_steps_col = db["workflow_steps"]

    # Generate case_id
    count = await cases_col.count_documents({})
    case_code = f"LEAMSS-{datetime.now(timezone.utc).year}-{(count + 1):04d}"

    # Find client user
    client_user = await users_col.find_one(
        {"$or": [{"id": pa.get("client_user_id")}, {"email": pa.get("client_email", "").lower()}]},
        {"_id": 0}
    )
    client_id = client_user["id"] if client_user else pa.get("client_user_id")

    # Resolve case manager (optional)
    cm_id = (data.case_manager_id if data else None)
    cm_name = "Pending assignment"
    if cm_id:
        cm = await users_col.find_one({"id": cm_id, "role": "case_manager"}, {"_id": 0, "name": 1})
        if not cm:
            raise HTTPException(status_code=400, detail="Invalid case_manager_id")
        cm_name = cm.get("name", "Case Manager")

    case_id = str(uuid.uuid4())
    case = {
        "id": case_id,
        "case_id": case_code,
        "sale_id": pa.get("sale_id"),
        "client_id": client_id,
        "client_name": pa.get("client_name"),
        "client_email": pa.get("client_email"),
        "product_id": pa.get("product_id", ""),
        "product_name": pa.get("product_name") or f"{pa.get('country')} - {pa.get('service_type')}",
        "partner_id": pa.get("partner_id"),
        "case_manager_id": cm_id,
        "case_manager_name": cm_name,
        "status": "active",
        "current_step": "Profile Creation",
        "current_step_order": 1,
        "pre_assessment_id": pa_id,
        "created_at": _now(),
        "updated_at": _now(),
    }
    await cases_col.insert_one(case)

    # Copy workflow steps if product exists
    if pa.get("product_id"):
        steps = await workflow_steps_col.find({"product_id": pa["product_id"]}, {"_id": 0}).sort("step_order", 1).to_list(100)
        for step in steps:
            cs = {
                "id": str(uuid.uuid4()),
                "case_id": case_id,
                "step_name": step.get("step_name"),
                "step_order": step.get("step_order"),
                "status": "pending",
                "description": step.get("description", ""),
                "required_documents": step.get("required_documents", []),
                "created_at": _now(),
            }
            await case_steps_col.insert_one(cs)

    await pre_assessments_col.update_one({"id": pa_id}, {"$set": {
        "stage": "case_created",
        "case_id": case_id,
        "final_approved_by": current_user["id"],
        "final_approved_at": _now(),
        "updated_at": _now(),
    }})

    # Notify client
    if client_id:
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": client_id,
            "title": f"Case activated: {case_code}",
            "message": "Your case is now live! A case manager will be assigned shortly.",
            "type": "case_created", "read": False,
            "link": "/client", "created_at": _now(),
        })
    # Notify partner
    if pa.get("partner_id"):
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": pa["partner_id"],
            "title": f"Case created: {case_code}",
            "message": f"Case for {pa.get('client_name')} is now active.",
            "type": "case_created", "read": False,
            "created_at": _now(),
        })
    # Notify case manager if assigned
    if cm_id:
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": cm_id,
            "title": f"New case assigned: {case_code}",
            "message": f"{pa.get('client_name')} - {pa.get('country')} {pa.get('service_type')}",
            "type": "case_assigned", "read": False,
            "link": f"/cm?case={case_id}", "created_at": _now(),
        })

    await _log(current_user["id"], pa_id, "case_created", {"case_id": case_code, "case_manager_id": cm_id})

    # Phase 7.3.5 — Auto-upgrade attached report snapshots to "proposal" tier
    try:
        from core.report_tier_hook import auto_upgrade_report_tiers_for_pa
        upgrade_result = await auto_upgrade_report_tiers_for_pa(
            pa_id, "case_created", payment_ref=f"CASE_{case_code}",
        )
        await _log(current_user["id"], pa_id, "report_tier_auto_upgrade", upgrade_result)
    except Exception as e:
        logger.exception("Tier auto-upgrade to proposal failed for PA %s: %s", pa_id, e)

    # Phase 4B — Auto-recalc target achievement for the PA creator (case_created = revenue confirmed)
    try:
        from core.targets_logic import recalc_targets_for_user
        creator_id = pa.get("created_by_user_id") or pa.get("partner_id")
        if creator_id:
            await recalc_targets_for_user(creator_id, notify=True)
    except Exception as _e:
        # Never block case creation if target recalc fails
        logger.warning(f"Phase 4B recalc failed for PA {pa_id}: {_e}")

    # Phase 4C.3 — Auto-build vendor cost allocations
    try:
        from core.allocations_logic import build_allocations_for_pa
        fresh_pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
        if fresh_pa:
            alloc_doc = await build_allocations_for_pa(fresh_pa)
            if alloc_doc:
                logger.info(f"Phase 4C.3 allocations built for PA {pa_id}: {len(alloc_doc.get('allocations', []))} entries")
    except Exception as _e:
        logger.warning(f"Phase 4C.3 allocation build failed for PA {pa_id}: {_e}")

    # Phase 4C.4 — Auto-apply sales commission entry
    try:
        from core.commission_logic import apply_commission_for_pa
        fresh_pa2 = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
        if fresh_pa2:
            entry = await apply_commission_for_pa(fresh_pa2)
            if entry:
                logger.info(f"Phase 4C.4 commission entry created for PA {pa_id}: ₹{entry.get('commission_amount')}")
    except Exception as _e:
        logger.warning(f"Phase 4C.4 commission apply failed for PA {pa_id}: {_e}")

    return {"ok": True, "case_id": case_id, "case_code": case_code, "case_manager_id": cm_id, "case_manager_name": cm_name, "stage": "case_created"}


# ======================== ACTIVITY (for partner visibility) ========================
@router.post("/activity/log")
async def log_activity(data: ActivityLogRequest, current_user: dict = Depends(get_current_user)):
    await _log(current_user["id"], data.pa_id, data.action, data.metadata)
    return {"logged": True}


@router.get("/activity/pa/{pa_id}")
async def get_pa_activity(pa_id: str, current_user: dict = Depends(get_current_user)):
    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Not found")
    if current_user.get("role") == "partner" and pa.get("partner_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your assessment")
    items = await activity_col.find({"pa_id": pa_id}, {"_id": 0}).sort("created_at", -1).to_list(100)
    for it in items:
        if isinstance(it.get("created_at"), datetime):
            it["created_at"] = it["created_at"].isoformat()
    return {"activity": items, "total": len(items)}
