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
from core.razorpay_client import get_razorpay_client, RazorpayClient, SignatureVerificationError

razorpay_client = get_razorpay_client()
razorpay = RazorpayClient

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
    include_gst: bool = False  

class PublicMockPayRequest(BaseModel):
    token: str

class PublicCreateOrderRequest(BaseModel):
    token: str

class PublicVerifyPaymentRequest(BaseModel):
    token: str
    order_id: str
    payment_id: str
    signature: str

class ProposalVerifyPaymentRequest(BaseModel):
    order_id: str
    payment_id: str
    signature: str

class ProposalInternationalClaimRequest(BaseModel):
    reference_note: Optional[str] = "" 

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

async def _create_spouse_case(pa: dict, spouse_cm_id: Optional[str]) -> tuple:
    """Creates a separate case + user account + magic-login for the spouse/partner.
    Returns (spouse_case_id, spouse_case_code) or (None, None) if no spouse_info."""
    spouse_info = pa.get("spouse_info")
    if not spouse_info or not spouse_info.get("email"):
        return None, None

    cases_col = db["cases"]
    case_steps_col = db["case_steps"]
    workflow_steps_col = db["workflow_steps"]

    spouse_email = spouse_info["email"].lower()
    spouse_user = await users_col.find_one({"email": spouse_email}, {"_id": 0})
    if not spouse_user:
        spouse_user_id = str(uuid.uuid4())
        temp_pw = secrets.token_urlsafe(10)
        spouse_user = {
            "id": spouse_user_id, "name": spouse_info.get("name", ""),
            "email": spouse_email, "phone": spouse_info.get("mobile", ""),
            "password_hash": get_password_hash(temp_pw),
            "role": "client", "status": "active",
            "source": "partner_skill_assessment_spouse",
            "partner_id": pa.get("partner_id"),
            "created_at": _now(), "updated_at": _now(),
        }
        await users_col.insert_one(spouse_user)
    spouse_id = spouse_user["id"]

    spouse_cm_name = "Pending assignment"
    if spouse_cm_id:
        spouse_cm = await users_col.find_one({"id": spouse_cm_id, "role": "case_manager"}, {"_id": 0, "name": 1})
        if spouse_cm:
            spouse_cm_name = spouse_cm.get("name", "Case Manager")

    spouse_count = await cases_col.count_documents({})
    spouse_case_code = f"LEAMSS-{datetime.now(timezone.utc).year}-{(spouse_count + 1):04d}"
    spouse_case_id = str(uuid.uuid4())
    spouse_case = {
        "id": spouse_case_id, "case_id": spouse_case_code,
        "sale_id": pa.get("sale_id"), "client_id": spouse_id,
        "linked_case_id": pa.get("case_id"), "is_partner_case": True,
        "client_name": spouse_info.get("name"), "client_email": spouse_info.get("email"),
        "product_id": pa.get("product_id", ""),
        "product_name": (pa.get("product_name") or "") + " (Partner)",
        "partner_id": pa.get("partner_id"),
        "case_manager_id": spouse_cm_id, "case_manager_name": spouse_cm_name,
        "status": "active", "current_step": "Profile Creation", "current_step_order": 1,
        "pre_assessment_id": pa.get("id"),
        "created_at": _now(), "updated_at": _now(),
    }
    await cases_col.insert_one(spouse_case)

    if pa.get("product_id"):
        steps = await workflow_steps_col.find({"product_id": pa["product_id"]}, {"_id": 0}).sort("step_order", 1).to_list(100)
        for step in steps:
            await case_steps_col.insert_one({
                "id": str(uuid.uuid4()), "case_id": spouse_case_id,
                "step_name": step.get("step_name"), "step_order": step.get("step_order"),
                "status": "pending", "description": step.get("description", ""),
                "required_documents": step.get("required_documents", []),
                "created_at": _now(),
            })

    magic_token = secrets.token_urlsafe(22)
    await magic_col.insert_one({
        "id": str(uuid.uuid4()), "token": magic_token, "user_id": spouse_id,
        "expires_at": _now() + timedelta(hours=72), "used": False, "created_at": _now(),
    })
    base = _frontend_url()
    portal_link = f"{base}/magic/{magic_token}" if base else f"/magic/{magic_token}"
    await _mock_send("email", spouse_email, "Your LEAMSS client portal",
                      f"Welcome {spouse_info.get('name')}! Access your case here: {portal_link}")

    if spouse_cm_id:
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()), "user_id": spouse_cm_id,
            "title": f"New case assigned: {spouse_case_code}",
            "message": f"{spouse_info.get('name')} — partner/spouse of {pa.get('client_name')}",
            "type": "case_assigned", "read": False,
            "link": f"/cm?case={spouse_case_id}", "created_at": _now(),
        })

    return spouse_case_id, spouse_case_code

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

        # 👇 NEW — Step-1 fee GST calculation (only for standard ₹5,100 PA link,
        # express token payments GST लावत नाहीये सध्या)
        is_express_check = pa.get("sale_type") == "express"
        base_step1_amount = 5100.0
        gst_amount = round(base_step1_amount * 0.18, 2) if (data.include_gst and not is_express_check) else 0.0
        total_step1_amount = base_step1_amount + gst_amount

        update_fields = {
            "share_token": token,
            "share_expires_at": expires_at,
            "share_active": True,
            "updated_at": _now(),
        }
        if not is_express_check:
            update_fields.update({
                "step1_gst_included": bool(data.include_gst),
                "step1_base_amount": base_step1_amount,
                "step1_gst_amount": gst_amount,
                "step1_total_amount": total_step1_amount,
            })
        # await pre_assessments_col.update_one({"id": data.pa_id}, update_fields if False else {"$set": update_fields})
        await pre_assessments_col.update_one({"id": data.pa_id}, {"$set": update_fields})
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
            amount = total_step1_amount   # 👈 आधी `5100` hardcoded होतं, आता dynamic
            amount_label = f"₹{total_step1_amount:,.0f}" + (f" (incl. 18% GST)" if gst_amount > 0 else "")
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
            "gst_included": gst_amount > 0,
            "gst_amount": gst_amount,
            "base_amount": base_step1_amount,
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
            if pa.get("step1_gst_included"):
                update["fee_amount_paid"] = pa.get("step1_total_amount", 5100)
                update["fee_gst_included"] = True
                update["fee_gst_amount"] = pa.get("step1_gst_amount", 0)
                update["fee_base_amount"] = pa.get("step1_base_amount", 5100)
            else:
                update["fee_amount_paid"] = 5100
                update["fee_gst_included"] = False
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


class PublicEnterPortalRequest(BaseModel):
    token: str

class InternationalPaymentClaimRequest(BaseModel):
    token: str
    reference_note: Optional[str] = ""  # UTR/transaction ref, if client has it

@router.get("/public/bank-details/{token}")
async def get_bank_details(token: str, country: Optional[str] = None):
    """Returns the bank account for the given `country` query param (client's choice
    from the sub-tabs). If no country is passed, falls back to the PA's destination
    country, then to a 'default' account."""
    pa = await pre_assessments_col.find_one({"share_token": token}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Link not found")

    bank_col = db["international_bank_accounts"]
    lookup_country = country or pa.get("country")

    account = await bank_col.find_one({"country": lookup_country, "active": True}, {"_id": 0})
    if not account:
        account = await bank_col.find_one({"country": "default", "active": True}, {"_id": 0})
    if not account:
        raise HTTPException(status_code=404, detail="No international bank account configured yet — contact admin")

    return account


@router.post("/public/international-payment-claim")
async def international_payment_claim(data: InternationalPaymentClaimRequest):
    """Client (paying via international wire transfer) clicks 'I've made the transfer'.
    Creates client user + magic link (same as mock-pay) but marks stage as
    'international_payment_pending' so Partner knows to manually verify before approving."""
    pa = await pre_assessments_col.find_one({"share_token": data.token}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Link not found")

    already_claimed = pa.get("stage") not in (None, "new", "payment_pending")
    if already_claimed:
        raise HTTPException(status_code=400, detail="Payment already claimed or processed for this link")

    # Ensure client user exists (same logic as mock-pay)
    existing = await users_col.find_one({"email": pa["client_email"].lower()}, {"_id": 0})
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
            "source": "international_wire_portal",
            "partner_id": pa.get("partner_id"),
            "created_at": _now(),
            "updated_at": _now(),
        }
        await users_col.insert_one(user)

    await pre_assessments_col.update_one({"share_token": data.token}, {"$set": {
        "stage": "international_payment_pending",
        "fee_payment_status": "pending_verification",  # NOT "paid" yet — partner must confirm
        "payment_method": "international_wire_transfer",
        "international_payment_claimed_at": _now(),
        "international_payment_reference_note": data.reference_note or "",
        "client_user_id": user["id"],
        "updated_at": _now(),
    }})

    # Issue magic link so client can access Mini Portal immediately (to upload proof)
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

    # Notify partner — ACTION NEEDED: verify wire transfer
    if pa.get("partner_id"):
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": pa["partner_id"],
            "title": "International payment claimed — verify manually",
            "message": f"{pa.get('client_name')} says they've sent an international wire transfer. Check your bank statement + uploaded proof, then confirm.",
            "type": "international_payment_pending", "read": False,
            "link": "/partner?tab=pre-assessment",
            "created_at": _now(),
        })

    await _log(user["id"], pa["id"], "international_payment_claimed", {"reference_note": data.reference_note or ""})

    return {"ok": True, "magic_link": portal_link, "stage": "international_payment_pending", "pa_id": pa["id"]}

@router.post("/public/create-order")
async def create_order(data: PublicCreateOrderRequest):
    """Creates a real Razorpay order for the given share-token's pre-assessment.
    Frontend calls this FIRST, gets order_id, then opens Razorpay Checkout."""
    pa = await pre_assessments_col.find_one({"share_token": data.token}, {"_id": 0})
    if not pa or not pa.get("share_active"):
        raise HTTPException(status_code=404, detail="Link not found or deactivated")

    # Same amount logic as generate_public_link's Branch A
    is_express = pa.get("sale_type") == "express"
    mode = pa.get("express_mode") or "direct"
    if is_express and mode == "token":
        amount_rupees = float(pa.get("express_token_amount") or 0)
    else:
        amount_rupees = float(pa.get("step1_total_amount") or 5100.0)

    if amount_rupees <= 0:
        raise HTTPException(status_code=400, detail="Invalid payment amount for this link")

    if not razorpay_client:
        raise HTTPException(status_code=500, detail="Razorpay is not configured on this server")

    amount_paise = int(amount_rupees * 100)  # Razorpay paise madhe ghet

    order = razorpay_client.order.create({
        "amount": amount_paise,
        "currency": "INR",
        "payment_capture": 1,
        "notes": {
            "pa_id": pa["id"],
            "share_token": data.token,
        },
    })

    await _log(pa.get("client_user_id") or "public", pa["id"], "razorpay_order_created",
               {"order_id": order["id"], "amount": amount_rupees})

    return {
        "order_id": order["id"],
        "amount": amount_paise,
        "amount_rupees": amount_rupees,
        "currency": "INR",
        "key_id": os.environ.get("RAZORPAY_KEY_ID"),
        "client_name": pa.get("client_name"),
        "client_email": pa.get("client_email"),
        "client_mobile": pa.get("client_mobile"),
    }

@router.post("/public/verify-payment")
async def verify_payment(data: PublicVerifyPaymentRequest):
    """Verifies Razorpay signature after client completes checkout, then reuses the
    exact same 'mark as paid + create user + magic link' logic as /public/mock-pay."""
    if not razorpay_client or not razorpay:
        raise HTTPException(status_code=500, detail="Razorpay is not configured on this server")
    pa = await pre_assessments_col.find_one({"share_token": data.token}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Link not found")

    # ---- Verify Razorpay signature (this proves the payment is real, not faked) ----
    try:
        razorpay_client.utility.verify_payment_signature({
            "razorpay_order_id": data.order_id,
            "razorpay_payment_id": data.payment_id,
            "razorpay_signature": data.signature,
        })
    except getattr(getattr(razorpay, "errors", None), "SignatureVerificationError", Exception):
        raise HTTPException(status_code=400, detail="Payment verification failed — signature mismatch")

    # ---- Reuse existing paid-logic (same as mock-pay) ----
    result = await public_mock_pay(PublicMockPayRequest(token=data.token))
    await pre_assessments_col.update_one({"share_token": data.token}, {"$set": {
        "razorpay_order_id": data.order_id,
        "razorpay_payment_id": data.payment_id,
        "payment_method": "razorpay_live",
        "updated_at": _now(),
    }})
    return result

@router.post("/public/enter-portal")
async def public_enter_portal(data: PublicEnterPortalRequest):
    """Express-sale clients (direct mode) never 'pay' the PA fee, so they never get
    auto-created as a user via /public/mock-pay. This endpoint lets the SAME
    /pre-assess/:token public link auto-upgrade them into a real client portal
    session once the partner has sent packages/proposal (stage progressed)."""
    pa = await pre_assessments_col.find_one({"share_token": data.token}, {"_id": 0})
    if not pa or not pa.get("share_active"):
        raise HTTPException(status_code=404, detail="Link not found or deactivated")

    ready_stages = (
        "awaiting_package_selection", "package_selected", "proposal_sent",
        "proposal_paid", "awaiting_final_approval", "case_created",
    )
    if pa.get("stage") not in ready_stages:
        raise HTTPException(status_code=400, detail="Portal not ready yet — your consultant hasn't sent packages.")

    # Ensure a client user exists (mirrors the auto-create logic in /public/mock-pay)
    existing = await users_col.find_one({"email": pa["client_email"].lower()}, {"_id": 0})
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
            "source": "express_sale_portal",
            "partner_id": pa.get("partner_id"),
            "created_at": _now(),
            "updated_at": _now(),
        }
        await users_col.insert_one(user)
        await _mock_send("email", user["email"], "Your LEAMSS client portal",
            f"Welcome {user['name']}! Your account is ready.")

    if not pa.get("client_user_id"):
        await pre_assessments_col.update_one({"id": pa["id"]}, {"$set": {
            "client_user_id": user["id"], "updated_at": _now(),
        }})

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

    await _log(user["id"], pa["id"], "express_portal_entered", {"stage": pa.get("stage")})

    return {"ok": True, "magic_link": portal_link, "stage": pa.get("stage")}

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
    user_email = (current_user.get("email") or "").lower()
    user_id = current_user.get("id")

    # Match by either email OR explicit client_user_id
    q = {"$or": [
        {"client_email": user_email},
        {"client_user_id": user_id},
    ]}
    items = await pre_assessments_col.find(q, {"_id": 0, "partner_id": 0}).sort("created_at", -1).to_list(50)
    for it in items:
        for k in ("created_at", "updated_at", "fee_paid_at", "share_expires_at"):
            if isinstance(it.get(k), datetime):
                it[k] = it[k].isoformat()
    return {"assessments": items, "total": len(items)}


def _can_access_pa_portal(pa: dict, current_user: dict) -> bool:
    if not pa:
        return False
    role = current_user.get("role")
    if role in ("admin", "super_admin"):
        return True
    if role in ("partner", "sales_executive", "sr_sales_executive"):
        return True
    user_id = current_user.get("id")
    user_email = (current_user.get("email") or "").lower()
    if pa.get("client_user_id") == user_id or (pa.get("client_email") or "").lower() == user_email:
        return True
    return False


@router.post("/client/submit/{pa_id}")
async def client_submit_for_review(pa_id: str, current_user: dict = Depends(get_current_user)):
    """Client marks their uploaded documents as ready for partner review.
    Transitions stage: payment_received -> documents_submitted.
    """
    pa = await pre_assessments_col.find_one({"$or": [{"id": pa_id}, {"pa_number": pa_id}]}, {"_id": 0})
    if not pa or not _can_access_pa_portal(pa, current_user):
        raise HTTPException(status_code=404, detail="Pre-assessment not found")

    real_pa_id = pa.get("id") or pa_id

    if pa.get("stage") not in ("payment_received", "international_payment_pending"):
        raise HTTPException(status_code=400, detail=f"Cannot submit at stage: {pa.get('stage')}")

    # Verify at least 1 doc uploaded
    docs_count = await db["pre_assessment_documents"].count_documents({
        "$or": [{"pre_assessment_id": real_pa_id}, {"pre_assessment_id": pa_id}]
    })
    if docs_count == 0:
        raise HTTPException(status_code=400, detail="Please upload at least one document before submitting")

    # NEW FLOW: Client submits → Partner reviews → Partner forwards → Admin reviews
    await pre_assessments_col.update_one({"$or": [{"id": real_pa_id}, {"pa_number": real_pa_id}]}, {"$set": {
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

    update_fields = {
        "stage": "documents_submitted",
        "partner_remarks": data.remarks or "",
        "partner_forwarded_at": _now(),
        "submitted_at": _now(),
        "updated_at": _now(),
    }
    # If this was an international wire transfer, partner forwarding = payment confirmed
    if pa.get("payment_method") == "international_wire_transfer" and pa.get("fee_payment_status") != "paid":
        update_fields["fee_payment_status"] = "paid"
        update_fields["fee_paid_at"] = _now()

    await pre_assessments_col.update_one({"id": pa_id}, {"$set": update_fields})

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
@router.post("/partner/resend-approval/{pa_id}")
async def partner_resend_approval(
    pa_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Partner resubmits a rejected Pre-Assessment / Express Sale for approval."""

    is_admin = (
        current_user.get("role") in ("admin", "admin_owner")
        or current_user.get("rbac_role") in ("admin", "admin_owner")
    )

    if not is_admin and current_user.get("role") not in (
        "partner",
        "sales_executive",
        "sr_sales_executive",
        "sales_manager",
        "sales_head",
    ):
        raise HTTPException(status_code=403, detail="Not authorized")

    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Pre-assessment not found")

    if not is_admin:
        owns = (
            pa.get("partner_id") == current_user["id"]
            or pa.get("created_by_user_id") == current_user["id"]
        )
        if not owns:
            raise HTTPException(status_code=403, detail="Not your pre-assessment")

    # -------------------------
    # EXPRESS SALE
    # -------------------------
    if pa.get("sale_type") == "express":

        if pa.get("express_sale_approval_status") != "rejected":
            raise HTTPException(
                status_code=400,
                detail="Only rejected Express Sales can be resent."
            )

        await pre_assessments_col.update_one(
            {"id": pa_id},
            {
                "$set": {
                    "express_sale_approval_status": "pending",
                    "express_sale_approval_remarks": "",
                    "updated_at": _now(),
                }
            }
        )

        admins = await users_col.find(
            {"role": "admin", "status": "active"},
            {"_id": 0, "id": 1}
        ).to_list(50)

        for admin in admins:
            await notifications_col.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": admin["id"],
                "title": "Express Sale Resubmitted",
                "message": f"{pa.get('client_name')} has resubmitted an Express Sale for approval.",
                "type": "express_sale_review",
                "read": False,
                "link": "/admin/express-approvals",
                "created_at": _now(),
            })

        await _log(
            current_user["id"],
            pa_id,
            "partner_resent_express_sale",
            {}
        )

        return {
            "ok": True,
            "message": "Express Sale resubmitted successfully.",
            "express_sale_approval_status": "pending"
        }

    # -------------------------
    # STANDARD PRE-ASSESSMENT
    # -------------------------

    if pa.get("admin_decision") != "rejected":
        raise HTTPException(
            status_code=400,
            detail="Only rejected Pre-Assessments can be resent."
        )

    await pre_assessments_col.update_one(
        {"id": pa_id},
        {
            "$set": {
                "stage": "documents_submitted",
                "admin_decision": None,
                "admin_reason": "",
                "admin_notes": "",
                "admin_reviewed_by": None,
                "admin_reviewed_at": None,
                "updated_at": _now(),
            }
        }
    )

    admins = await users_col.find(
        {"role": "admin", "status": "active"},
        {"_id": 0, "id": 1}
    ).to_list(50)

    for admin in admins:
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": admin["id"],
            "title": "Pre-Assessment Resubmitted",
            "message": f"{pa.get('client_name')} has been resubmitted for approval.",
            "type": "pre_assessment_review",
            "read": False,
            "link": "/admin?tab=pre-assessments",
            "created_at": _now(),
        })

    await _log(
        current_user["id"],
        pa_id,
        "partner_resent_for_approval",
        {}
    )

    return {
        "ok": True,
        "message": "Pre-assessment resubmitted successfully.",
        "stage": "documents_submitted"
    }
@router.get("/client/portal-access/{pa_id}")
async def client_portal_access(pa_id: str, current_user: dict = Depends(get_current_user)):
    """Returns current portal access level for a pre-assessment (mini/expanded/full)."""
    pa = await pre_assessments_col.find_one({"$or": [{"id": pa_id}, {"pa_number": pa_id}]}, {"_id": 0})
    if not pa or not _can_access_pa_portal(pa, current_user):
        raise HTTPException(status_code=404, detail="Not found")

    real_pa_id = pa.get("id") or pa_id
    stage = pa.get("stage", "new")
    access_level = "none"
    if stage in ("payment_received", "partner_review", "documents_submitted", "under_review",
                 "rejected", "refund_initiated", "refunded", "international_payment_pending"):
        access_level = "mini"
    elif stage in ("approved", "awaiting_package_selection", "package_selected", "proposal_sent"):
        access_level = "expanded"
    elif stage in ("proposal_paid", "awaiting_final_approval", "case_created"):
        access_level = "full"

    return {
        "pa_id": real_pa_id,
        "stage": stage,
        "access_level": access_level,
        "can_upload_docs": stage in ("payment_received", "international_payment_pending"),
        "can_submit_for_review": stage == "payment_received",
        "can_view_proposal": stage in ("awaiting_package_selection", "package_selected", "proposal_sent", "proposal_paid", "case_created"),
        "can_pay_service_fee": stage == "proposal_sent",
    }

class SelectPackageRequest(BaseModel):
    package_id: str


@router.post("/client/select-package/{pa_id}")
async def client_select_package(pa_id: str, data: SelectPackageRequest, current_user: dict = Depends(get_current_user)):
    """Client picks a package from the ones admin configured on the product."""
    pa = await pre_assessments_col.find_one({"$or": [{"id": pa_id}, {"pa_number": pa_id}]}, {"_id": 0})
    if not pa or not _can_access_pa_portal(pa, current_user):
        raise HTTPException(status_code=404, detail="Not found")

    real_pa_id = pa.get("id") or pa_id
    if pa.get("stage") != "awaiting_package_selection":
        raise HTTPException(status_code=400, detail=f"Cannot select package at stage: {pa.get('stage')}")

    packages = pa.get("available_packages_snapshot") or []
    selected = next((p for p in packages if p.get("id") == data.package_id), None)
    if not selected:
        raise HTTPException(status_code=400, detail="Invalid package_id")

    await pre_assessments_col.update_one({"$or": [{"id": real_pa_id}, {"pa_number": real_pa_id}]}, {"$set": {
        "stage": "package_selected",
        "selected_package_id": data.package_id,
        "selected_package_snapshot": selected,
        "package_selected_at": _now(),
        "updated_at": _now(),
    }})

    await _log(current_user["id"], pa_id, "package_selected", {"package_id": data.package_id, "package_name": selected.get("name")})

    if pa.get("partner_id"):
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": pa["partner_id"],
            "title": "Client selected a package",
            "message": f"{pa.get('client_name')} selected '{selected.get('name')}' (₹{selected.get('price', 0):,.0f}). Set up the payment method to finalize the proposal.",
            "type": "package_selected", "read": False,
            "link": "/partner?tab=pre-assessment",
            "created_at": _now(),
        })

    return {"ok": True, "stage": "package_selected", "selected_package": selected}


class ClientOccupationDecisionPortalRequest(BaseModel):
    decision: str  # "accepted" | "rejected"
    suggested_code: Optional[str] = ""
    suggested_title: Optional[str] = ""
    suggested_assessing_body: Optional[str] = ""
    notes: Optional[str] = ""


@router.post("/client/occupation-decision/{pa_id}")
@router.post("/client/{pa_id}/occupation-decision")
async def client_portal_occupation_decision(
    pa_id: str,
    data: ClientOccupationDecisionPortalRequest,
    current_user: dict = Depends(get_current_user)
):
    """Client accepts or suggests alternate occupation code from the portal."""
    if current_user.get("role") != "client":
        raise HTTPException(status_code=403, detail="Client only")
    pa = await pre_assessments_col.find_one(
        {"$or": [
            {"id": pa_id},
            {"pre_assessment_number": pa_id},
            {"custom_id": pa_id}
        ]},
        {"_id": 0}
    )
    if not pa or (pa.get("client_email", "").lower() != current_user.get("email", "").lower()
                and pa.get("client_user_id") != current_user["id"]):
        raise HTTPException(status_code=404, detail="Not found")

    real_pa_id = pa.get("id") or pa_id
    now = _now()
    if data.decision == "accepted":
        update_doc = {
            "client_occupation_review_status": "accepted",
            "client_occupation_accepted_at": now,
            "updated_at": now,
        }
        await pre_assessments_col.update_one({"id": real_pa_id}, {"$set": update_doc})

        if pa.get("case_id"):
            await cases_col.update_one(
                {"id": pa["case_id"]},
                {"$set": {"client_occupation_review_status": "accepted", "client_occupation_accepted_at": now, "updated_at": now}}
            )

        occ_desc = f"{pa.get('occupation_code')} - {pa.get('occupation_title')} ({pa.get('assessing_authority_code')})"
        if pa.get("partner_id"):
            try:
                await notifications_col.insert_one({
                    "id": str(uuid.uuid4()),
                    "user_id": pa["partner_id"],
                    "title": "Client Accepted Occupation Code",
                    "message": f"{pa.get('client_name')} confirmed and accepted occupation profile: {occ_desc}.",
                    "type": "client_accepted_occupation",
                    "read": False,
                    "created_at": now,
                })
            except Exception:
                pass

        await _log(current_user["id"], real_pa_id, "client_accepted_occupation", {"occupation": occ_desc})
        return {"ok": True, "status": "accepted", "message": "Occupation code accepted successfully"}

    elif data.decision == "rejected":
        update_doc = {
            "client_occupation_review_status": "rejected_by_client",
            "client_suggested_occupation_code": data.suggested_code or "",
            "client_suggested_occupation_title": data.suggested_title or "",
            "client_suggested_assessing_body": data.suggested_assessing_body or "",
            "client_suggested_occupation_notes": data.notes or "",
            "client_occupation_rejected_at": now,
            "updated_at": now,
        }
        await pre_assessments_col.update_one({"id": real_pa_id}, {"$set": update_doc})

        if pa.get("case_id"):
            await cases_col.update_one(
                {"id": pa["case_id"]},
                {"$set": {
                    "client_occupation_review_status": "rejected_by_client",
                    "client_suggested_occupation_code": data.suggested_code or "",
                    "client_suggested_occupation_title": data.suggested_title or "",
                    "client_suggested_occupation_notes": data.notes or "",
                    "client_occupation_rejected_at": now,
                    "updated_at": now,
                }}
            )

        if pa.get("partner_id"):
            try:
                await notifications_col.insert_one({
                    "id": str(uuid.uuid4()),
                    "user_id": pa["partner_id"],
                    "title": "Client Requested Occupation Code Change",
                    "message": f"{pa.get('client_name')} requested alternate occupation: {data.suggested_code} - {data.suggested_title}. Notes: {data.notes}",
                    "type": "client_rejected_occupation",
                    "read": False,
                    "created_at": now,
                })
            except Exception:
                pass

        await _log(current_user["id"], real_pa_id, "client_suggested_occupation", {"code": data.suggested_code, "notes": data.notes})
        return {"ok": True, "status": "rejected_by_client", "message": "Occupation suggestion submitted successfully"}

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

def _get_next_proposal_part(pa: dict):
    """Shared helper: find the next payable installment/part for a PA's proposal."""
    parts = pa.get("proposal_payment_parts") or []
    if not parts:
        parts = [{"index": 0, "label": "Full Payment", "amount": float(pa.get("proposal_fee") or 0),
                "status": "pending", "due_date": None, "trigger_condition": None}]
    next_part = next((p for p in parts if p.get("status") == "pending"), None)
    return parts, next_part


@router.post("/client/proposal/create-order/{pa_id}")
async def proposal_create_order(pa_id: str, current_user: dict = Depends(get_current_user)):
    """Creates a real Razorpay order for the NEXT pending proposal installment (domestic tab)."""
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

    parts, next_part = _get_next_proposal_part(pa)
    if not next_part:
        raise HTTPException(status_code=400, detail="No pending installment to pay")

    if not razorpay_client:
        raise HTTPException(status_code=500, detail="Razorpay is not configured on this server")

    amount_rupees = float(next_part["amount"])
    amount_paise = int(amount_rupees * 100)

    order = razorpay_client.order.create({
        "amount": amount_paise,
        "currency": "INR",
        "payment_capture": 1,
        "notes": {"pa_id": pa_id, "part_index": str(next_part["index"]), "purpose": "proposal_installment"},
    })

    await _log(current_user["id"], pa_id, "razorpay_proposal_order_created",
               {"order_id": order["id"], "amount": amount_rupees, "part": next_part["label"]})

    return {
        "order_id": order["id"],
        "amount": amount_paise,
        "amount_rupees": amount_rupees,
        "currency": "INR",
        "key_id": os.environ.get("RAZORPAY_KEY_ID"),
        "part_label": next_part["label"],
        "client_name": pa.get("client_name"),
        "client_email": pa.get("client_email"),
        "client_mobile": pa.get("client_mobile"),
    }


@router.post("/client/proposal/verify-payment/{pa_id}")
async def proposal_verify_payment(pa_id: str, data: ProposalVerifyPaymentRequest, current_user: dict = Depends(get_current_user)):
    """Verifies Razorpay signature, then reuses the SAME logic as client_mock_pay_proposal
    to mark the installment paid (avoids duplicating the part-tracking/sales-sync logic)."""
    if current_user.get("role") != "client":
        raise HTTPException(status_code=403, detail="Client only")

    if not razorpay_client or not razorpay:
        raise HTTPException(status_code=500, detail="Razorpay is not configured on this server")

    try:
        razorpay_client.utility.verify_payment_signature({
            "razorpay_order_id": data.order_id,
            "razorpay_payment_id": data.payment_id,
            "razorpay_signature": data.signature,
        })
    except getattr(getattr(razorpay, "errors", None), "SignatureVerificationError", Exception):
        raise HTTPException(status_code=400, detail="Payment verification failed — signature mismatch")

    await pre_assessments_col.update_one({"id": pa_id}, {"$set": {
        "proposal_last_razorpay_order_id": data.order_id,
        "proposal_last_razorpay_payment_id": data.payment_id,
        "proposal_payment_method": "razorpay_live",
        "updated_at": _now(),
    }})

    # Reuse the existing part-marking logic (this returns the same response shape frontend expects)
    return await client_mock_pay_proposal(pa_id, current_user)


@router.post("/client/proposal/international-claim/{pa_id}")
async def proposal_international_claim(pa_id: str, data: ProposalInternationalClaimRequest, current_user: dict = Depends(get_current_user)):
    """International wire transfer claim for a proposal installment. Marks the part as
    'pending_verification' (not fully paid) — partner must confirm before it counts as paid."""
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

    parts, next_part = _get_next_proposal_part(pa)
    if not next_part:
        raise HTTPException(status_code=400, detail="No pending installment to claim")

    for p in parts:
        if p["index"] == next_part["index"]:
            p["status"] = "pending_verification"
            p["claimed_at"] = _now().isoformat()
            p["reference_note"] = data.reference_note or ""

    await pre_assessments_col.update_one({"id": pa_id}, {"$set": {
        "proposal_payment_parts": parts,
        "proposal_payment_method": "international_wire_transfer",
        "updated_at": _now(),
    }})

    if pa.get("partner_id"):
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": pa["partner_id"],
            "title": f"International installment claimed — {next_part['label']}",
            "message": f"{pa.get('client_name')} says they've wire-transferred {next_part['label']} (₹{next_part['amount']:,.0f}). Verify and mark as paid.",
            "type": "international_installment_pending", "read": False,
            "link": "/partner?tab=pre-assessment",
            "created_at": _now(),
        })

    await _log(current_user["id"], pa_id, "proposal_international_claimed",
               {"part": next_part["label"], "reference_note": data.reference_note or ""})

    return {"ok": True, "part_claimed": next_part["label"], "status": "pending_verification"}

@router.post("/partner/proposal/confirm-installment/{pa_id}")
async def partner_confirm_proposal_installment(pa_id: str, current_user: dict = Depends(get_current_user)):
    """Partner confirms a client's claimed international wire-transfer installment.
    Marks that part 'paid' — mirrors client_mock_pay_proposal's part-completion logic
    so sales sync / notifications / stage transitions stay consistent."""
    is_admin = (current_user.get("role") in ("admin", "admin_owner") or current_user.get("rbac_role") in ("admin", "admin_owner"))
    if not is_admin and current_user.get("role") not in ("partner", "sales_executive", "sr_sales_executive", "sales_manager", "sales_head"):
        raise HTTPException(status_code=403, detail="Sales / partners / admins only")

    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Not found")
    if not is_admin:
        owns = pa.get("partner_id") == current_user["id"] or pa.get("created_by_user_id") == current_user["id"]
        if not owns:
            raise HTTPException(status_code=403, detail="Not your pre-assessment")

    parts = pa.get("proposal_payment_parts") or []
    verifying_part = next((p for p in parts if p.get("status") == "pending_verification"), None)
    if not verifying_part:
        raise HTTPException(status_code=400, detail="No installment awaiting verification")

    now = _now()
    for p in parts:
        if p["index"] == verifying_part["index"]:
            p["status"] = "paid"
            p["paid_at"] = now.isoformat()
            p["payment_ref"] = f"INTL-{secrets.token_hex(8)}"
            p["confirmed_by"] = current_user["id"]

    amount_just_paid = float(verifying_part["amount"])
    amount_paid_total = round(float(pa.get("proposal_amount_paid") or 0) + amount_just_paid, 2)
    amount_pending = round(float(pa.get("proposal_fee") or 0) - amount_paid_total, 2)
    all_paid = all(p.get("status") == "paid" for p in parts)

    # Same "does the next part need admin unlock?" logic as domestic mock-pay
    pending_unlock = False
    if not all_paid:
        remaining_locked = [p for p in parts if p.get("status") == "locked"]
        if remaining_locked:
            pending_unlock = True

    update = {
        "proposal_payment_parts": parts,
        "proposal_amount_paid": amount_paid_total,
        "proposal_amount_pending": max(0, amount_pending),
        "pending_installment_unlock": pending_unlock,
        "updated_at": now,
    }
    if all_paid:
        update.update({
            "stage": "proposal_paid",
            "proposal_status": "paid",
            "proposal_paid_at": now,
            "proposal_payment_ref": f"INTL-{secrets.token_hex(8)}",
        })
    await pre_assessments_col.update_one({"id": pa_id}, {"$set": update})

    # Sync sales_col (same as domestic mock-pay logic)
    if pa.get("sale_id"):
        sale = await db["sales"].find_one({"id": pa["sale_id"]}, {"_id": 0})
        if sale:
            new_received = round((sale.get("amount_received", 0) or 0) + amount_just_paid, 2)
            new_pending = max(0, round((sale.get("fee_amount", 0) or 0) - new_received, 2))
            new_pay_status = "paid" if new_pending <= 0 else "partial"
            rate = sale.get("commission_rate", 0) or 0
            new_commission = round(new_received * (rate / 100), 2)
            await db["sales"].update_one({"id": pa["sale_id"]}, {
                "$set": {
                    "amount_received": new_received, "pending_amount": new_pending,
                    "payment_status": new_pay_status, "commission_amount": new_commission,
                    "payment_parts": parts,
                },
                "$push": {"payment_history": {
                    "amount": amount_just_paid, "method": "international_wire_transfer",
                    "reference": verifying_part.get("payment_ref"), "date": now.isoformat(),
                    "recorded_by": current_user["id"], "part_label": verifying_part["label"],
                }},
            })

    # Notify client
    client_id = pa.get("client_user_id")
    if client_id:
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()), "user_id": client_id,
            "title": f"{verifying_part['label']} confirmed",
            "message": f"Your international transfer of ₹{amount_just_paid:,.0f} has been verified and confirmed.",
            "type": "installment_confirmed", "read": False,
            "created_at": now,
        })

    await _log(current_user["id"], pa_id, "partner_confirmed_international_installment",
               {"amount": amount_just_paid, "part": verifying_part["label"], "all_paid": all_paid})

    return {
        "ok": True,
        "stage": "proposal_paid" if all_paid else "proposal_sent",
        "part_confirmed": verifying_part["label"],
        "fully_paid": all_paid,
    }

@router.get("/client/proposal/bank-details/{pa_id}")
async def proposal_bank_details(pa_id: str, current_user: dict = Depends(get_current_user), country: Optional[str] = None):
    """Bank details for proposal-installment international payments (reuses same collection)."""
    if current_user.get("role") != "client":
        raise HTTPException(status_code=403, detail="Client only")
    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa or (pa.get("client_email", "").lower() != current_user.get("email", "").lower()
                and pa.get("client_user_id") != current_user["id"]):
        raise HTTPException(status_code=404, detail="Not found")

    bank_col = db["international_bank_accounts"]
    lookup_country = country or pa.get("country")
    account = await bank_col.find_one({"country": lookup_country, "active": True}, {"_id": 0})
    if not account:
        account = await bank_col.find_one({"country": "default", "active": True}, {"_id": 0})
    if not account:
        raise HTTPException(status_code=404, detail="No international bank account configured")
    return account

@router.post("/client/mock-pay-proposal/{pa_id}")
async def client_mock_pay_proposal(pa_id: str, current_user: dict = Depends(get_current_user)):
    """MOCK main-fee payment — pays the NEXT pending payment part (full / 50-50 / installment).
    Only moves to 'proposal_paid' once ALL parts are paid.
    """
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

    parts = pa.get("proposal_payment_parts") or []
    if not parts:
        # Legacy PA with no parts recorded — fall back to single full payment (old behaviour)
        parts = [{"index": 0, "label": "Full Payment", "amount": float(pa.get("proposal_fee") or 0),
                "status": "pending", "due_date": None, "trigger_condition": None}]

    # Find the next payable part: first one with status "pending" (skip "locked" / "paid")
    next_part = next((p for p in parts if p.get("status") == "pending"), None)
    if not next_part:
        locked = next((p for p in parts if p.get("status") == "locked"), None)
        if locked:
            raise HTTPException(status_code=400, detail=f"Next installment ({locked['label']}) is locked. Waiting on: {locked.get('trigger_condition') or 'admin approval'}.")
        raise HTTPException(status_code=400, detail="All payment parts are already paid")

    # Mark this part as paid
    now = _now()
    for p in parts:
        if p["index"] == next_part["index"]:
            p["status"] = "paid"
            p["paid_at"] = now.isoformat()
            p["payment_ref"] = f"MOCK-{secrets.token_hex(8)}"

    amount_just_paid = float(next_part["amount"])
    amount_paid_total = round(float(pa.get("proposal_amount_paid") or 0) + amount_just_paid, 2)
    amount_pending = round(float(pa.get("proposal_fee") or 0) - amount_paid_total, 2)
    all_paid = all(p.get("status") == "paid" for p in parts)

    # If this was a 50-50 / installment plan, unlock the NEXT part now that this one is paid
    # NEW — Do NOT auto-unlock the next part. It stays "locked" until
    # partner reviews + admin approves (mirrors the ₹5,100 PA-fee review flow).
    pending_unlock = False
    if not all_paid:
        remaining_locked = [p for p in parts if p.get("status") == "locked"]
        if remaining_locked:
            pending_unlock = True  # admin must unlock via /unlock-next-installment

    update = {
        "proposal_payment_parts": parts,
        "proposal_amount_paid": amount_paid_total,
        "proposal_amount_pending": max(0, amount_pending),
        "pending_installment_unlock": pending_unlock,
        "updated_at": now,
    }
    if all_paid:
        update.update({
            "stage": "proposal_paid",
            "proposal_status": "paid",
            "proposal_paid_at": now,
            "proposal_payment_ref": f"MOCK-{secrets.token_hex(8)}",
        })

    # 👇 THIS LINE WAS MISSING — actually save the update to the database
    await pre_assessments_col.update_one({"id": pa_id}, {"$set": update})


    

# ── Sync sales_col so the Client "Payments" dashboard reflects this too ──
    if pa.get("sale_id"):
        sale = await db["sales"].find_one({"id": pa["sale_id"]}, {"_id": 0})
        if sale:
            new_received = round((sale.get("amount_received", 0) or 0) + amount_just_paid, 2)
            new_pending = round((sale.get("fee_amount", 0) or 0) - new_received, 2)
            if new_pending < 0:
                new_pending = 0
            new_pay_status = "paid" if new_pending <= 0 else "partial"
            rate = sale.get("commission_rate", 0) or 0
            new_commission = round(new_received * (rate / 100), 2)

            payment_entry = {
                "amount": amount_just_paid,
                "method": "mock_installment",
                "reference": next_part.get("payment_ref"),
                "date": now.isoformat(),
                "recorded_by": "system_mock",
                "part_label": next_part["label"],
            }

            # 👇 NEW — mirror the same installment-status array (with due dates)
            # that pre_assessments_col.proposal_payment_parts has, so the client
            # "My Proposals & Payments" widget can render the full schedule.
            await db["sales"].update_one({"id": pa["sale_id"]}, {
                "$set": {
                    "amount_received": new_received,
                    "pending_amount": new_pending,
                    "payment_status": new_pay_status,
                    "commission_amount": new_commission,
                    "payment_parts": parts,   # 👈 same array we just updated on `parts` above
                },
                "$push": {"payment_history": payment_entry},
            })

    if all_paid:
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
                "message": f"{pa.get('client_name')} paid ₹{amount_paid_total:,.0f} (full). Upload payment receipt + agreement + any basic docs, then submit to Admin for final approval.",
                "type": "main_fee_paid_to_partner", "read": False,
                "link": "/partner?tab=pre-assessment",
                "created_at": now,
            })
    else:
        # Partial payment — partner must review + forward to admin before next part unlocks
        if pa.get("partner_id"):
            await notifications_col.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": pa["partner_id"],
                "title": f"Installment received — ₹{amount_just_paid:,.0f}",
                "message": f"{pa.get('client_name')} paid {next_part['label']} (₹{amount_just_paid:,.0f}). Review and forward to admin to unlock the next installment.",
                "type": "installment_review_needed", "read": False,
                "link": "/partner?tab=pre-assessment",
                "created_at": now,
            })

    await _log(current_user["id"], pa_id, "installment_paid" if not all_paid else "main_fee_paid",
            {"amount": amount_just_paid, "part": next_part["label"], "all_paid": all_paid})

    return {
        "ok": True,
        "stage": "proposal_paid" if all_paid else "proposal_sent",
        "part_paid": next_part["label"],
        "amount_paid_now": amount_just_paid,
        "amount_paid_total": amount_paid_total,
        "amount_pending": max(0, amount_pending),
        "fully_paid": all_paid,
    }

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
    spouse_case_manager_id: Optional[str] = None 


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

    if pa.get("case_id"):
        await pre_assessments_col.update_one({"id": pa_id}, {"$set": {
            "stage": "case_created",
            "updated_at": _now(),
        }})
         # 👇 NEW — main case existed already, but spouse case might still be missing
        spouse_case_id = pa.get("spouse_case_id")
        spouse_case_code = None
        spouse_info = pa.get("spouse_info")
        if spouse_info and spouse_info.get("email") and not spouse_case_id:
            # run the SAME spouse-case-creation block here (extract it into a helper function
            # so it isn't duplicated — see note below)
            spouse_case_id, spouse_case_code = await _create_spouse_case(
                pa, data.spouse_case_manager_id if data else None
            )
            await pre_assessments_col.update_one({"id": pa_id}, {"$set": {
                "spouse_case_id": spouse_case_id, "updated_at": _now(),
            }})
        return {
            "ok": True, "case_id": pa["case_id"], "already_activated": True, "stage": "case_created",
            "spouse_case_id": spouse_case_id, "spouse_case_code": spouse_case_code,
        }
    
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

    # 👇 auto-create spouse/partner account if this PA has spouse_info
    spouse_id = None
    spouse_info = pa.get("spouse_info")
    if spouse_info and spouse_info.get("email"):
        spouse_email = spouse_info["email"].lower()
        spouse_user = await users_col.find_one({"email": spouse_email}, {"_id": 0})
        if not spouse_user:
            spouse_user_id = str(uuid.uuid4())
            temp_pw = secrets.token_urlsafe(10)
            spouse_user = {
                "id": spouse_user_id,
                "name": spouse_info.get("name", ""),
                "email": spouse_email,
                "phone": spouse_info.get("mobile", ""),
                "password_hash": get_password_hash(temp_pw),
                "role": "client",
                "status": "active",
                "source": "partner_skill_assessment_spouse",
                "partner_id": pa.get("partner_id"),
                "created_at": _now(),
                "updated_at": _now(),
            }
            await users_col.insert_one(spouse_user)
        spouse_id = spouse_user["id"]

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
        # "spouse_id": spouse_id,
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
        "occupation_code": pa.get("occupation_code") or pa.get("suggested_occupation_code") or "",
        "occupation_title": pa.get("occupation_title") or pa.get("suggested_occupation_title") or "",
        "assessing_authority_code": pa.get("assessing_authority_code") or pa.get("suggested_assessing_authority_code") or "",
        "country": pa.get("country") or "AU",
        "service_type": pa.get("service_type") or "PR",
        "client_occupation_review_status": "pending_client_review",
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
            # 👇 NEW — spouse gets a fully SEPARATE case + own account + own login
    spouse_case_id, spouse_case_code = await _create_spouse_case(
        pa, data.spouse_case_manager_id if data else None
    )
    spouse_id = None
    if spouse_case_id:
        spouse_case_doc = await cases_col.find_one({"id": spouse_case_id}, {"_id": 0, "client_id": 1})
        spouse_id = spouse_case_doc.get("client_id") if spouse_case_doc else None

    await pre_assessments_col.update_one({"id": pa_id}, {"$set": {
    "stage": "case_created",
    "case_id": case_id,
    "case_manager_id": cm_id,      # 👈 NEW — allocations_logic la vendor auto-assign karnyasathi lagto
    "spouse_case_id": spouse_case_id,
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
            "related_id": pa["id"],
            "link": "/client", "created_at": _now(),
        })

    # Notify spouse (if this PA has one)
    if spouse_id:
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": spouse_id,
            "title": f"Case activated: {case_code}",
            "message": "You've been added as a partner on this case. You now have full portal access.",
            "type": "case_created", "read": False,
            "related_id": pa["id"],
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
            "related_id": pa["id"],
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

    return {
        "ok": True, "case_id": case_id, "case_code": case_code,
        "case_manager_id": cm_id, "case_manager_name": cm_name,
        "spouse_case_id": spouse_case_id, "spouse_case_code": spouse_case_code,
        "stage": "case_created",
    }
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