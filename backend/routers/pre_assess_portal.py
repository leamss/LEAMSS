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
from fastapi import APIRouter, Depends, HTTPException

from core.auth import get_current_user, get_password_hash, create_access_token
from core.database import db, users_col, notifications_col
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
    """Attach a share-token to an existing pre-assessment so client can pay without login."""
    pa = await pre_assessments_col.find_one({"id": data.pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Pre-assessment not found")
    if current_user.get("role") not in ("partner", "admin") or (
        current_user.get("role") == "partner" and pa.get("partner_id") != current_user["id"]):
        raise HTTPException(status_code=403, detail="Not allowed")

    token = pa.get("share_token") or secrets.token_urlsafe(22)
    expires_at = _now() + timedelta(days=30)
    await pre_assessments_col.update_one({"id": data.pa_id}, {"$set": {
        "share_token": token,
        "share_expires_at": expires_at,
        "share_active": True,
        "updated_at": _now(),
    }})

    base = _frontend_url()
    public_url = f"{base}/pre-assess/{token}" if base else f"/pre-assess/{token}"

    msg = (f"Hi {pa.get('client_name', '')}, your pre-assessment for "
           f"{pa.get('service_type', 'immigration')} is ready. "
           f"Pay ₹5,100 to begin: {public_url}")
    await _mock_send("email", pa.get("client_email", ""), "Start your immigration pre-assessment", msg)
    if pa.get("client_mobile"):
        await _mock_send("whatsapp", pa["client_mobile"], "Pre-assessment", msg)

    return {
        "token": token,
        "public_url": public_url,
        "expires_at": expires_at.isoformat(),
    }


# ======================== PARTNER: PREVIEW AS CLIENT ========================
@router.post("/partner/preview-magic/{pa_id}")
async def partner_preview_magic(pa_id: str, current_user: dict = Depends(get_current_user)):
    """Partner-only: generate a short-lived magic link to preview the client portal/MiniPortal.
    Useful for demos / support. Works only on PAs where client has paid.
    """
    if current_user.get("role") not in ("partner", "admin"):
        raise HTTPException(status_code=403, detail="Partners or admins only")

    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Pre-assessment not found")
    if current_user.get("role") == "partner" and pa.get("partner_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your assessment")

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
async def public_view(token: str):
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
        await pre_assessments_col.update_one(
            {"share_token": data.token},
            {"$set": {
                "stage": "payment_received",
                "fee_payment_status": "paid",
                "fee_paid_at": _now(),
                "fee_payment_ref": f"MOCK-{secrets.token_hex(8)}",
                "client_user_id": user["id"],
                "updated_at": _now(),
            }},
        )
        # Notify partner
        if pa.get("partner_id"):
            await notifications_col.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": pa["partner_id"],
                "title": "Pre-assessment payment received",
                "message": f"{user['name']} has paid ₹5,100. Client will upload docs next.",
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
async def magic_login(data: MagicLoginRequest):
    doc = await magic_col.find_one({"token": data.token}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Invalid login link")
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
    await magic_col.update_one({"token": data.token}, {"$set": {"used": True, "used_at": _now()}})
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

    await pre_assessments_col.update_one({"id": pa_id}, {"$set": {
        "stage": "documents_submitted",
        "client_submitted_at": _now(),
        "updated_at": _now(),
    }})

    # Notify partner
    if pa.get("partner_id"):
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": pa["partner_id"],
            "title": "Client ready for review",
            "message": f"{pa.get('client_name')} has uploaded {docs_count} document(s) and is ready for your review.",
            "type": "pre_assess_ready",
            "read": False,
            "link": "/partner?tab=pre-assessment",
            "created_at": _now(),
        })

    await _log(current_user["id"], pa_id, "client_submitted_for_review", {"documents_count": docs_count})

    return {"ok": True, "stage": "documents_submitted", "documents_count": docs_count}


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
    if stage in ("payment_received", "documents_submitted", "under_review", "rejected", "refund_initiated", "refunded"):
        access_level = "mini"  # can upload docs only (view-only after submission)
    elif stage in ("approved", "proposal_sent"):
        access_level = "expanded"  # can explore tools, proposal, pay service fee
    elif stage in ("proposal_paid", "case_created"):
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


@router.post("/client/mock-pay-proposal/{pa_id}")
async def client_mock_pay_proposal(pa_id: str, current_user: dict = Depends(get_current_user)):
    """MOCK main-fee payment. On success, marks proposal_paid (awaits admin 2nd approval for case creation)."""
    if current_user.get("role") != "client":
        raise HTTPException(status_code=403, detail="Client only")
    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa or (pa.get("client_email", "").lower() != current_user.get("email", "").lower()
                  and pa.get("client_user_id") != current_user["id"]):
        raise HTTPException(status_code=404, detail="Not found")
    if pa.get("stage") != "proposal_sent":
        raise HTTPException(status_code=400, detail=f"Cannot pay at stage: {pa.get('stage')}")

    await pre_assessments_col.update_one({"id": pa_id}, {"$set": {
        "stage": "proposal_paid",
        "proposal_status": "paid",
        "proposal_paid_at": _now(),
        "proposal_payment_ref": f"MOCK-{secrets.token_hex(8)}",
        "updated_at": _now(),
    }})

    # Notify admins for 2nd approval (case creation)
    admins = await users_col.find({"role": "admin", "status": "active"}, {"_id": 0, "id": 1}).to_list(50)
    for admin in admins:
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": admin["id"],
            "title": "Main fee received — needs case creation",
            "message": f"{pa.get('client_name')} paid ₹{pa.get('proposal_fee', 0):,} main fee. Approve to create case.",
            "type": "main_fee_paid", "read": False,
            "link": "/admin?tab=pre-assessments",
            "created_at": _now(),
        })
    # Notify partner
    if pa.get("partner_id"):
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": pa["partner_id"],
            "title": "Client paid main fee",
            "message": f"{pa.get('client_name')} paid ₹{pa.get('proposal_fee', 0):,}. Awaiting admin approval to create case.",
            "type": "main_fee_paid", "read": False,
            "created_at": _now(),
        })

    await _log(current_user["id"], pa_id, "main_fee_paid", {"amount": pa.get("proposal_fee", 0)})
    return {"ok": True, "stage": "proposal_paid"}


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
    if pa.get("stage") != "proposal_paid":
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
