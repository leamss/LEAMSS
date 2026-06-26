"""Pre-Assessment Workflow Router
Flow: Partner creates → Sends ₹5,100 payment to client → Client pays → 
Partner submits docs to Admin → Admin approves/rejects → 
If approved: Partner sends sales proposal with payment link → Client pays → Case starts
If rejected: ₹5,100 refunded
"""
import os
import uuid
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Request, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, List
from core.database import db
from routers.auth import get_current_user
from core.services import log_activity

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pre-assessment", tags=["Pre-Assessment"])

# Phase 4A — Centralized scope constants & ownership helper
PA_CREATOR_ROLES = ("partner", "admin", "sales_executive", "sr_sales_executive", "sales_manager", "sales_head")
OWN_SCOPED_ROLES = ("partner", "sales_executive", "sr_sales_executive")  # see their own PAs only


def _assert_pa_owner(pa: dict, current_user: dict):
    """Raise 403 if current_user is not allowed to access the given PA.

    Allowed roles:
    - admin / case_manager → full access
    - partner / sales_executive / sr_sales_executive → only if partner_id matches user.id
    - client → only if client_email or client_user_id matches
    - anyone else → 403
    """
    role = (current_user.get("role") or "").lower()
    if role in ("admin", "case_manager"):
        return
    user_id = current_user.get("id")
    if role in OWN_SCOPED_ROLES:
        if pa.get("partner_id") != user_id:
            raise HTTPException(status_code=403, detail="Not your pre-assessment")
        return
    if role == "client":
        same_email = (pa.get("client_email") or "").lower() == (current_user.get("email") or "").lower()
        same_user = pa.get("client_user_id") == user_id
        if not (same_email or same_user):
            raise HTTPException(status_code=403, detail="Not your pre-assessment")
        return
    raise HTTPException(status_code=403, detail="You don't have permission to access this pre-assessment")


pre_assessments_col = db["pre_assessments"]
pre_assessment_docs_col = db["pre_assessment_documents"]
payment_transactions_col = db["payment_transactions"]
notifications_col = db["notifications"]
users_col = db["users"]
products_col = db["products"]
sales_col = db["sales"]

PRE_ASSESSMENT_FEE = 5100  # Phase 20.3 — DEPRECATED hardcoded fallback only; use resolver below
PRE_ASSESSMENT_SAFETY_NET_INR = 5100


async def _resolve_pa_fee(pa: dict) -> dict:
    """Phase 20.3 — Resolve PA fee using 3-tier policy resolver.

    Returns dict: {amount, currency, source, policy_id?, product_id?}
    """
    from services.pre_assessment_fee_resolver import resolve_pre_assessment_fee
    return await resolve_pre_assessment_fee(
        db,
        product_id=pa.get("product_id"),
        country_code=(pa.get("country") or "").upper()[:2] if pa.get("country") else None,
        visa_category=(pa.get("service_type") or pa.get("visa_type") or "").upper() or None,
    )
STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY")

STAGES = [
    "new",                          # Partner just created lead
    "payment_pending",              # Payment link sent to client
    "payment_received",             # Client paid ₹5,100
    "documents_submitted",          # Partner submitted docs to admin
    "under_review",                 # Admin is reviewing
    "approved",                     # Admin approved → Partner can send proposal (also reused by Express after admin approve)
    "rejected",                     # Admin rejected → Refund initiated
    "proposal_sent",                # Partner sent sales proposal to client
    "proposal_paid",                # Client paid service fee
    "case_created",                 # Case auto-created, process started
    "refund_initiated",             # Refund in progress
    "refunded",                     # Refund completed
    # Phase 4B (Part 2) — Express Sale stages
    "express_pending_approval",     # Express PA awaiting admin approval (no fees needed)
    "express_rejected",             # Admin rejected express request (no payment was made, no refund needed)
]


class CreatePreAssessment(BaseModel):
    client_name: str
    client_email: str
    client_mobile: str = ""
    country: str
    service_type: str
    product_id: str = ""
    notes: str = ""
    client_age: int = 0
    education: str = ""
    work_experience: str = ""
    # Phase 4A — Lead Source Tracking (optional)
    lead_source: Optional[str] = None  # maple_crm | walkin | referral | cold_call | linkedin | whatsapp | email | event | direct | other
    lead_source_detail: Optional[str] = None  # location (walkin) / referrer name / other text
    # Phase 4B (Part 2) — Express Sale support
    sale_type: Optional[str] = "standard"  # "standard" | "express"
    express_sale_reason: Optional[str] = None  # required if sale_type=="express"
    express_sale_justification: Optional[str] = None  # min 30 chars if express
    # Phase 4D — Express Sale modes
    # express_mode = "token" → client pays a nominal token to lock the deal, then proposal
    # express_mode = "direct" → no token, partner sends full proposal payment link directly
    express_mode: Optional[str] = "direct"  # "token" | "direct"
    express_token_amount: Optional[float] = None  # required if express_mode=="token"


class AdminReview(BaseModel):
    decision: str  # "approved" or "rejected"
    reason: str = ""
    notes: str = ""


class ProposalData(BaseModel):
    fee_amount: float  # base fee (before discounts/upsells)
    payment_method: str = "online"
    notes: str = ""
    currency: str = "INR"
    # New v2 fields (backward compatible)
    promo_code: Optional[str] = None
    additional_discount: Optional[float] = 0.0  # flat ₹ off
    upsell_bundle_ids: Optional[List[str]] = []
    ai_proposal_text: Optional[str] = None


# ===================== PARTNER ENDPOINTS =====================

@router.post("/create")
async def create_pre_assessment(data: CreatePreAssessment, current_user: dict = Depends(get_current_user)):
    """Create a new pre-assessment. Supports partners AND internal sales executives.

    Phase 4A: Sales executives are treated as 'internal partners' — their user_id
    becomes the partner_id for backward compatibility. The new created_by_role and
    created_by_user_id fields capture the distinction.

    Phase 4B Part 2: Supports sale_type="express" — skips PA fees collection,
    requires admin approval before proposal generation. Standard path is unchanged.
    """
    if current_user["role"] not in PA_CREATOR_ROLES:
        raise HTTPException(status_code=403, detail="You don't have permission to create pre-assessments")

    sale_type = (data.sale_type or "standard").lower()
    if sale_type not in ("standard", "express"):
        raise HTTPException(status_code=400, detail="sale_type must be 'standard' or 'express'")

    # ─── Express-specific validation ───────────────────────
    express_meta = {}
    if sale_type == "express":
        from core.express_logic import (
            get_express_settings,
            validate_express_request,
            check_limit,
            should_auto_approve,
        )
        settings = await get_express_settings()
        if not settings.get("express_sale_enabled", True):
            raise HTTPException(status_code=403, detail="Express Sales are currently disabled by Admin")

        # Reason + justification validation
        err = validate_express_request(
            data.express_sale_reason or "",
            data.express_sale_justification or "",
            min_chars=int(settings.get("express_min_justification_chars", 30)),
        )
        if err:
            raise HTTPException(status_code=400, detail=err)

        # Monthly limit check
        allowed, used, limit, msg = await check_limit(current_user)
        if not allowed:
            raise HTTPException(status_code=429, detail=msg)

        # Phase 4D — Validate mode
        mode = (data.express_mode or "direct").lower()
        if mode not in ("token", "direct"):
            raise HTTPException(status_code=400, detail="express_mode must be 'token' or 'direct'")
        token_amount = None
        if mode == "token":
            ta = data.express_token_amount
            if ta is None or float(ta) <= 0:
                raise HTTPException(status_code=400, detail="express_token_amount is required (> 0) when express_mode='token'")
            token_amount = float(ta)

        # Phase 4D — Auto-approve for senior roles
        # Phase 4D-fix — TOKEN mode also auto-approves so partner can immediately share token-payment
        # link with client. Admin approval moves to AFTER token is paid (post-payment admin review).
        # DIRECT mode keeps requiring admin approval first (since no token guard).
        auto = should_auto_approve(current_user, settings)
        auto_for_token = mode == "token"
        auto_final = auto or auto_for_token
        now = datetime.now(timezone.utc)
        approval_remarks = (
            "Auto-approved (senior role)" if auto else
            ("Auto-approved (Token mode — admin review after token payment)" if auto_for_token else None)
        )
        express_meta = {
            "sale_type": "express",
            "express_mode": mode,
            "express_token_amount": token_amount,
            "express_token_paid": False,  # Will flip to True when client pays the token
            "express_sale_reason": data.express_sale_reason,
            "express_sale_justification": data.express_sale_justification,
            "express_sale_requested_at": now,
            "express_sale_approval_status": "approved" if auto_final else "pending",
            "express_sale_approved_by": current_user["id"] if auto_final else None,
            "express_sale_approved_at": now if auto_final else None,
            "express_sale_approval_remarks": approval_remarks,
            "pa_fees_skipped": True,
            "pa_fees_amount": PRE_ASSESSMENT_FEE,
        }
    else:
        express_meta = {"sale_type": "standard", "pa_fees_skipped": False}

    pa_id = str(uuid.uuid4())
    pa_number = f"PA-{datetime.now().strftime('%Y%m%d')}-{pa_id[:6].upper()}"

    # Phase 20.3 — resolve fee using 3-tier policy resolver BEFORE creating the PA
    from services.pre_assessment_fee_resolver import resolve_pre_assessment_fee
    fee_resolution = await resolve_pre_assessment_fee(
        db,
        product_id=data.product_id,
        country_code=(data.country or "").upper()[:2] if data.country else None,
        visa_category=(data.service_type or "").upper() or None,
    )
    resolved_fee = int(fee_resolution["amount"])

    # Inject resolved fee back into express_meta for backward compat
    if sale_type == "express":
        express_meta["pa_fees_amount"] = resolved_fee

    product_name = ""
    if data.product_id:
        product = await products_col.find_one({"id": data.product_id}, {"_id": 0, "name": 1})
        if product:
            product_name = product.get("name", "")

    # Determine starting stage:
    #  - Standard → "new"
    #  - Express auto-approved → "approved" (ready for proposal)
    #  - Express needs approval → "express_pending_approval"
    if sale_type == "express":
        if express_meta["express_sale_approval_status"] == "approved":
            starting_stage = "approved"
        else:
            starting_stage = "express_pending_approval"
    else:
        starting_stage = "new"

    pre_assessment = {
        "id": pa_id,
        "pa_number": pa_number,
        "partner_id": current_user["id"],
        "partner_name": current_user.get("name", ""),
        # Phase 4A — Internal sales tracking
        "created_by_user_id": current_user["id"],
        "created_by_role": current_user["role"],
        "created_by_user_type": current_user.get("user_type", "external"),
        "lead_source": data.lead_source,
        "lead_source_detail": data.lead_source_detail,
        "client_name": data.client_name,
        "client_email": data.client_email,
        "client_mobile": data.client_mobile,
        "country": data.country,
        "service_type": data.service_type,
        "product_id": data.product_id,
        "product_name": product_name,
        "notes": data.notes,
        "client_age": data.client_age,
        "education": data.education,
        "work_experience": data.work_experience,
        "stage": starting_stage,
        "pre_assessment_fee": resolved_fee,
        "pre_assessment_fee_source": fee_resolution.get("source"),
        "pre_assessment_fee_policy_id": fee_resolution.get("policy_id"),
        "pre_assessment_fee_currency": fee_resolution.get("currency", "INR"),
        "fee_payment_status": "skipped" if sale_type == "express" else "unpaid",
        "fee_session_id": None,
        "admin_decision": None,
        "admin_reason": "",
        "admin_notes": "",
        "admin_reviewed_by": None,
        "admin_reviewed_at": None,
        "proposal_fee": 0,
        "proposal_status": None,
        "proposal_session_id": None,
        "sale_id": None,
        "case_id": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        **express_meta,
    }
    await pre_assessments_col.insert_one(pre_assessment)
    pre_assessment.pop("_id", None)

    action_label = "create_express_pre_assessment" if sale_type == "express" else "create_pre_assessment"
    detail_label = (
        f"Express PA created for {data.client_name} - {data.country} {data.service_type} (reason: {data.express_sale_reason})"
        if sale_type == "express"
        else f"Pre-assessment created for {data.client_name} - {data.country} {data.service_type}"
    )
    await log_activity(current_user["id"], current_user.get("name", ""), action_label,
                       "pre_assessment", pa_id, detail_label)

    # Notify admins
    title = "🚀 New Express Sale — Approval Needed" if sale_type == "express" and starting_stage == "express_pending_approval" else "New Pre-Assessment Created"
    link = "/admin/sales/express-approvals" if sale_type == "express" and starting_stage == "express_pending_approval" else "/admin/pre-assessments"
    msg = (f"{current_user.get('name', '')} created Express Sale for {data.client_name} — please review"
           if sale_type == "express" and starting_stage == "express_pending_approval"
           else f"{current_user.get('name', '')} created pre-assessment for {data.client_name}")
    admins = await users_col.find({"role": "admin", "status": "active"}, {"_id": 0, "id": 1}).to_list(50)
    for admin in admins:
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()), "user_id": admin["id"],
            "title": title,
            "message": msg,
            "type": "express_pending" if sale_type == "express" else "pre_assessment",
            "read": False,
            "link": link,
            "created_at": datetime.now(timezone.utc)
        })

    return {
        "id": pa_id,
        "pa_number": pa_number,
        "sale_type": sale_type,
        "stage": starting_stage,
        "express_sale_approval_status": pre_assessment.get("express_sale_approval_status"),
        "message": (
            "Express Sale submitted — awaiting admin approval"
            if starting_stage == "express_pending_approval"
            else (
                "Express Sale auto-approved — proceed to proposal generation"
                if sale_type == "express"
                else "Pre-assessment created successfully"
            )
        ),
    }


@router.post("/{pa_id}/remind-payment")
async def remind_client_payment(pa_id: str, current_user: dict = Depends(get_current_user)):
    """Sweep A.3 — Re-send / remind client about pending payment after PA approval.

    Works at stages: approved, proposal_sent, payment_pending. Idempotent — safe to call multiple times.
    Records `payment_link_resent` audit_log entry with admin id + timestamp.
    """
    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Pre-assessment not found")

    role = current_user.get("role")
    if role not in ("admin", "partner") or (role == "partner" and pa.get("partner_id") != current_user["id"]):
        raise HTTPException(status_code=403, detail="Only the assigned partner or admin can remind client")

    if pa.get("fee_payment_status") == "paid":
        raise HTTPException(status_code=400, detail="Payment already received — no reminder needed")

    allowed_stages = {"approved", "proposal_sent", "payment_pending"}
    if pa.get("stage") not in allowed_stages:
        raise HTTPException(status_code=400, detail=f"Cannot remind at stage '{pa.get('stage')}'. PA must be approved first.")

    # Capture payment URL — prefer proposal sale's payment link if exists; else PA mock link
    payment_url = pa.get("proposal_payment_url") or pa.get("payment_url") or ""
    if not payment_url and pa.get("sale_id"):
        sale = await db["sales"].find_one({"id": pa["sale_id"]}, {"_id": 0, "payment_url": 1})
        if sale:
            payment_url = sale.get("payment_url", "")

    # Append audit_log entry
    audit_entry = {
        "action": "payment_link_resent",
        "actor_id": current_user["id"],
        "actor_name": current_user.get("name", ""),
        "actor_role": role,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "channel": "email",
        "to": pa.get("client_email", ""),
        "stage_at_resend": pa.get("stage"),
    }
    await pre_assessments_col.update_one(
        {"id": pa_id},
        {"$push": {"audit_log": audit_entry}, "$set": {"updated_at": datetime.now(timezone.utc)}},
    )

    await log_activity(
        current_user["id"], current_user.get("name", ""), "payment_link_resent",
        "pre_assessment", pa_id, f"Payment reminder sent to {pa.get('client_name', '')} ({pa.get('client_email', '')})",
    )

    return {
        "ok": True,
        "message": f"Payment link sent to {pa.get('client_email', 'client')}",
        "client_email": pa.get("client_email", ""),
        "payment_url": payment_url,
        "stage": pa.get("stage"),
    }


@router.post("/{pa_id}/send-payment-link")
async def send_payment_link(pa_id: str, http_request: Request, current_user: dict = Depends(get_current_user)):
    """Partner sends pre-assessment payment link to client (Phase 20.3 — uses stored resolved fee)"""
    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Pre-assessment not found")

    if pa["partner_id"] != current_user["id"] and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    if pa["stage"] not in ["new", "payment_pending"]:
        raise HTTPException(status_code=400, detail=f"Cannot send payment link at stage: {pa['stage']}")

    # Phase 20.3 — use stored resolved fee (with safety fallback for legacy PAs)
    pa_fee = int(pa.get("pre_assessment_fee") or PRE_ASSESSMENT_FEE)

    if not STRIPE_API_KEY:
        # Mock mode — simulate payment link
        mock_link = f"{str(http_request.base_url)}api/pre-assessment/{pa_id}/mock-payment"
        await pre_assessments_col.update_one({"id": pa_id}, {"$set": {
            "stage": "payment_pending", "updated_at": datetime.now(timezone.utc)
        }})
        await log_activity(current_user["id"], current_user.get("name", ""), "send_payment_link",
                           "pre_assessment", pa_id, f"Payment link sent to {pa['client_name']} (₹{pa_fee})")
        return {"message": f"Payment link sent to {pa['client_email']}", "payment_url": mock_link, "mode": "mock"}

    from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionRequest

    origin = str(http_request.headers.get("origin", http_request.base_url)).rstrip("/")
    success_url = f"{origin}/payment-success?session_id={{CHECKOUT_SESSION_ID}}&type=pre_assessment&pa_id={pa_id}"
    cancel_url = f"{origin}/payment-cancel?type=pre_assessment&pa_id={pa_id}"

    host_url = str(http_request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)

    checkout_request = CheckoutSessionRequest(
        amount=float(pa_fee),
        currency="inr",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "type": "pre_assessment",
            "pa_id": pa_id,
            "client_email": pa["client_email"],
            "client_name": pa["client_name"],
            "partner_id": current_user["id"]
        }
    )
    session = await stripe_checkout.create_checkout_session(checkout_request)

    # Save transaction
    tx_id = str(uuid.uuid4())
    await payment_transactions_col.insert_one({
        "id": tx_id, "type": "pre_assessment_fee",
        "pre_assessment_id": pa_id, "session_id": session.session_id,
        "user_id": current_user["id"], "client_email": pa["client_email"],
        "amount": float(pa_fee), "currency": "inr",
        "status": "initiated", "payment_status": "pending",
        "created_at": datetime.now(timezone.utc)
    })

    await pre_assessments_col.update_one({"id": pa_id}, {"$set": {
        "stage": "payment_pending", "fee_session_id": session.session_id,
        "updated_at": datetime.now(timezone.utc)
    }})

    await log_activity(current_user["id"], current_user.get("name", ""), "send_payment_link",
                       "pre_assessment", pa_id, f"₹{pa_fee} payment link sent to {pa['client_name']} (source: {pa.get('pre_assessment_fee_source', 'legacy')})")

    return {"message": f"Payment link sent to {pa['client_email']}", "payment_url": session.url, "session_id": session.session_id}


@router.post("/{pa_id}/mock-payment")
async def mock_payment_received(pa_id: str):
    """Mock endpoint to simulate payment (for testing without Stripe)"""
    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Pre-assessment not found")
    pa_fee = int(pa.get("pre_assessment_fee") or PRE_ASSESSMENT_FEE)

    await pre_assessments_col.update_one({"id": pa_id}, {"$set": {
        "stage": "payment_received", "fee_payment_status": "paid",
        "paid_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }})

    # Phase 20.5 — auto-provision Mini Portal + Info Sheet (idempotent)
    try:
        from routers.mini_portal import provision_mini_portal
        from core.database import db as _db
        pa_fresh = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
        result = await provision_mini_portal(_db, pa_fresh, triggered_by="pa_mock_payment")
        logger.info(f"[Phase20.5] mock_payment provisioned mini-portal: {result.get('status')}")
    except Exception as e:
        logger.error(f"[Phase20.5] mock_payment mini-portal provisioning failed: {e}")

    # Notify partner
    await notifications_col.insert_one({
        "id": str(uuid.uuid4()), "user_id": pa["partner_id"],
        "title": "Payment Received!", "type": "payment",
        "message": f"₹{pa_fee} received from {pa['client_name']}. Submit documents for admin review.",
        "read": False, "created_at": datetime.now(timezone.utc)
    })

    return {"message": "Payment received (mock). Submit documents to proceed."}


@router.post("/{pa_id}/confirm-payment")
async def confirm_payment(pa_id: str, current_user: dict = Depends(get_current_user)):
    """Confirm payment was received (for Stripe webhook or manual confirmation)"""
    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Pre-assessment not found")
    pa_fee = int(pa.get("pre_assessment_fee") or PRE_ASSESSMENT_FEE)

    await pre_assessments_col.update_one({"id": pa_id}, {"$set": {
        "stage": "payment_received", "fee_payment_status": "paid",
        "paid_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }})

    # Phase 20.5 — auto-provision Mini Portal + Info Sheet (idempotent)
    try:
        from routers.mini_portal import provision_mini_portal
        from core.database import db as _db
        pa_fresh = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
        result = await provision_mini_portal(_db, pa_fresh, triggered_by=str(current_user.get("id")))
        logger.info(f"[Phase20.5] confirm_payment provisioned mini-portal: {result.get('status')}")
    except Exception as e:
        logger.error(f"[Phase20.5] confirm_payment mini-portal provisioning failed: {e}")

    await log_activity(current_user["id"], current_user.get("name", ""), "confirm_pa_payment",
                       "pre_assessment", pa_id, f"₹{pa_fee} payment confirmed for {pa['client_name']}")

    return {"message": "Payment confirmed"}


@router.post("/{pa_id}/submit-documents")
async def submit_to_admin(pa_id: str, remarks: str = Form(""), current_user: dict = Depends(get_current_user)):
    """Partner submits pre-assessment with documents for admin review"""
    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Pre-assessment not found")

    # Phase 4A-aligned: admin OR ownership via partner_id/created_by_user_id
    is_admin = (current_user.get("role") in ("admin", "admin_owner") or current_user.get("rbac_role") in ("admin", "admin_owner"))
    is_owner = (pa.get("partner_id") == current_user["id"] or pa.get("created_by_user_id") == current_user["id"])
    if not is_admin and not is_owner:
        raise HTTPException(status_code=403, detail="Not authorized")

    if pa["stage"] not in ["payment_received", "documents_submitted"]:
        raise HTTPException(status_code=400, detail=f"Cannot submit at stage: {pa['stage']}. Payment must be received first.")

    await pre_assessments_col.update_one({"id": pa_id}, {"$set": {
        "stage": "under_review", "partner_remarks": remarks,
        "submitted_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }})

    await log_activity(current_user["id"], current_user.get("name", ""), "submit_pa_for_review",
                       "pre_assessment", pa_id, f"Documents submitted for review - {pa['client_name']}")

    # Notify admins
    admins = await users_col.find({"role": "admin", "status": "active"}, {"_id": 0, "id": 1}).to_list(50)
    for admin in admins:
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()), "user_id": admin["id"],
            "title": "Pre-Assessment Ready for Review",
            "message": f"{pa['client_name']} ({pa['country']} - {pa['service_type']}) documents submitted by {pa['partner_name']}",
            "type": "pre_assessment_review", "read": False,
            "link": "/admin/pre-assessments",
            "created_at": datetime.now(timezone.utc)
        })

    return {"message": "Documents submitted for admin review"}


@router.post("/{pa_id}/upload-document")
async def upload_pa_document(
    pa_id: str,
    document_type: str = Form(...),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload a document for pre-assessment"""
    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Pre-assessment not found")

    # Save file
    os.makedirs(f"/app/uploads/pre_assessments/{pa_id}", exist_ok=True)
    file_path = f"/app/uploads/pre_assessments/{pa_id}/{file.filename}"
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    doc = {
        "id": str(uuid.uuid4()),
        "pre_assessment_id": pa_id,
        "document_type": document_type,
        "file_name": file.filename,
        "file_path": file_path,
        "file_size": len(content),
        "uploaded_by": current_user["id"],
        "uploaded_by_name": current_user.get("name", ""),
        "created_at": datetime.now(timezone.utc)
    }
    await pre_assessment_docs_col.insert_one(doc)
    doc.pop("_id", None)

    return {"id": doc["id"], "message": "Document uploaded", "file_name": file.filename}


@router.get("/{pa_id}/documents")
async def get_pa_documents(pa_id: str, current_user: dict = Depends(get_current_user)):
    """Get all documents for a pre-assessment"""
    docs = await pre_assessment_docs_col.find(
        {"pre_assessment_id": pa_id}, {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    for d in docs:
        if hasattr(d.get("created_at"), "isoformat"):
            d["created_at"] = d["created_at"].isoformat()
    return docs


@router.get("/{pa_id}/document/{doc_id}/download")
async def download_pa_document(pa_id: str, doc_id: str, inline: bool = False, current_user: dict = Depends(get_current_user)):
    """Serve a specific PA document file. Use ?inline=true to view in browser, else download."""
    from fastapi.responses import FileResponse
    import mimetypes
    doc = await pre_assessment_docs_col.find_one({"id": doc_id, "pre_assessment_id": pa_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    path = doc.get("file_path")
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File missing on server")
    fname = doc.get("file_name", "document")
    mime, _ = mimetypes.guess_type(fname)
    if not mime:
        mime = "application/pdf" if fname.lower().endswith(".pdf") else "application/octet-stream"
    disp = "inline" if inline else "attachment"
    return FileResponse(path, filename=fname, media_type=mime, content_disposition_type=disp)


@router.delete("/{pa_id}/document/{doc_id}")
async def delete_pa_document(pa_id: str, doc_id: str, current_user: dict = Depends(get_current_user)):
    """Delete an uploaded document. Allowed for: the owner client, the partner of this PA, or admin."""
    doc = await pre_assessment_docs_col.find_one({"id": doc_id, "pre_assessment_id": pa_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Pre-assessment not found")
    role = current_user.get("role")
    if role in ("partner", "sales_executive", "sr_sales_executive") and pa.get("partner_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your pre-assessment")
    if role == "client":
        email_match = pa.get("client_email", "").lower() == current_user.get("email", "").lower()
        id_match = pa.get("client_user_id") == current_user["id"]
        if not (email_match or id_match):
            raise HTTPException(status_code=403, detail="Not your document")

    # Delete file from disk (best-effort)
    path = doc.get("file_path")
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass
    await pre_assessment_docs_col.delete_one({"id": doc_id, "pre_assessment_id": pa_id})
    return {"ok": True}


# ===================== ADMIN ENDPOINTS =====================

@router.get("/admin/queue")
async def admin_queue(current_user: dict = Depends(get_current_user)):
    """Admin gets all pre-assessments pending review"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    items = await pre_assessments_col.find(
        {"stage": {"$in": ["under_review", "documents_submitted", "awaiting_final_approval"]}}, {"_id": 0}
    ).sort("submitted_at", -1).to_list(200)

    for item in items:
        docs = await pre_assessment_docs_col.find(
            {"pre_assessment_id": item["id"]}, {"_id": 0}
        ).to_list(50)
        item["documents"] = docs
        for field in ["created_at", "updated_at", "submitted_at", "admin_reviewed_at"]:
            if field in item and item[field] and hasattr(item[field], "isoformat"):
                item[field] = item[field].isoformat()
        for d in docs:
            if hasattr(d.get("created_at"), "isoformat"):
                d["created_at"] = d["created_at"].isoformat()

    return items


class PADetailsUpdate(BaseModel):
    """Editable PA fields. Only non-financial / non-stage fields allowed here.
    Stage transitions go through their dedicated endpoints (review, send-proposal, etc.)
    """
    client_name: Optional[str] = None
    client_email: Optional[str] = None
    client_mobile: Optional[str] = None
    client_age: Optional[int] = None
    education: Optional[str] = None
    work_experience: Optional[str] = None
    country: Optional[str] = None
    service_type: Optional[str] = None
    notes: Optional[str] = None


@router.put("/{pa_id}/details")
async def update_pa_details(pa_id: str, body: PADetailsUpdate, current_user: dict = Depends(get_current_user)):
    """Edit basic PA contact / profile details after creation.
    Allowed: admin (any), partner (only own PA), case_manager (any).
    Locked once stage = case_created (case is active).
    """
    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Pre-assessment not found")

    role = current_user.get("role")
    if role in ("partner", "sales_executive", "sr_sales_executive") and pa.get("partner_id") != current_user.get("id"):
        raise HTTPException(status_code=403, detail="Not your pre-assessment")
    if role not in ("admin", "case_manager", "partner"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    if pa.get("stage") == "case_created":
        raise HTTPException(status_code=400, detail="Case is active — edit details from the Case page")

    upd = {k: v for k, v in body.dict().items() if v is not None and v != ""}
    if not upd:
        raise HTTPException(status_code=400, detail="No fields provided to update")

    # Track what changed for audit
    changes = []
    for k, v in upd.items():
        old_v = pa.get(k)
        if str(old_v or "") != str(v):
            changes.append({"field": k, "old": old_v, "new": v})
    if not changes:
        return {"ok": True, "no_change": True}

    upd["updated_at"] = datetime.now(timezone.utc)
    await pre_assessments_col.update_one({"id": pa_id}, {"$set": upd})

    # Sync the linked client user (so login email / name stay in step) — skip for safety on email
    if pa.get("client_user_id"):
        user_upd = {}
        if "client_name" in upd:
            user_upd["name"] = upd["client_name"]
        if "client_mobile" in upd:
            user_upd["mobile"] = upd["client_mobile"]
        if user_upd:
            await users_col.update_one({"id": pa["client_user_id"]}, {"$set": user_upd})

    await log_activity(
        user_id=current_user.get("id"),
        user_name=current_user.get("name") or current_user.get("email") or "unknown",
        action="pa_details_edited",
        entity_type="pre_assessment",
        entity_id=pa_id,
        details={"changes": changes, "role": role},
    )
    return {"ok": True, "updated_fields": list(upd.keys()), "changes": changes}


# ─── Phase 9.9 — Edit History tab (audit trail per PA) ──────────────────────
@router.get("/{pa_id}/edit-history")
async def get_pa_edit_history(pa_id: str, current_user: dict = Depends(get_current_user)):
    """Returns full audit timeline for a PA — all field edits, stage changes,
    document uploads, approvals, signatures, etc. Latest first.
    """
    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Pre-assessment not found")
    _assert_pa_owner(pa, current_user)

    cur = db["audit_logs"].find(
        {"entity_type": "pre_assessment", "entity_id": pa_id},
        {"_id": 0},
    ).sort("created_at", -1).limit(500)
    entries = []
    async for log in cur:
        if isinstance(log.get("created_at"), datetime):
            log["created_at"] = log["created_at"].isoformat()
        entries.append(log)

    # Also surface signature events from pa_signatures collection
    sig_cur = db["pa_signatures"].find(
        {"pre_assessment_id": pa_id},
        {"_id": 0, "signed_at": 1, "user_email": 1, "typed_name": 1, "ip_address": 1,
         "agreement_id": 1, "id": 1, "biometric_packet": 1},
    ).sort("signed_at", -1)
    async for sig in sig_cur:
        signed = sig.get("signed_at")
        if isinstance(signed, datetime):
            signed = signed.isoformat()
        entries.append({
            "action": "agreement_signed",
            "entity_type": "pre_assessment",
            "entity_id": pa_id,
            "user_id": None,
            "user_name": sig.get("typed_name") or sig.get("user_email"),
            "created_at": signed,
            "details": {
                "agreement_id": sig.get("agreement_id"),
                "signature_id": sig.get("id"),
                "ip_address": sig.get("ip_address"),
                "biometric_captured": bool(sig.get("biometric_packet")),
            },
        })

    # Sort by created_at desc
    def _ts(e):
        return e.get("created_at") or ""
    entries.sort(key=_ts, reverse=True)

    return {
        "pa_id": pa_id,
        "pa_number": pa.get("pa_number"),
        "client_name": pa.get("client_name"),
        "current_stage": pa.get("stage"),
        "total_entries": len(entries),
        "entries": entries,
    }


@router.put("/{pa_id}/review")
async def admin_review(pa_id: str, review: AdminReview, current_user: dict = Depends(get_current_user)):
    """Admin approves or rejects pre-assessment"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Pre-assessment not found")

    if review.decision not in ["approved", "rejected"]:
        raise HTTPException(status_code=400, detail="Decision must be 'approved' or 'rejected'")

    new_stage = "approved" if review.decision == "approved" else "rejected"

    await pre_assessments_col.update_one({"id": pa_id}, {"$set": {
        "stage": new_stage,
        "admin_decision": review.decision,
        "admin_reason": review.reason,
        "admin_notes": review.notes,
        "admin_reviewed_by": current_user["id"],
        "admin_reviewed_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }})

    await log_activity(current_user["id"], current_user.get("name", ""), f"pa_{review.decision}",
                       "pre_assessment", pa_id, f"Pre-assessment {review.decision} for {pa['client_name']} - {review.reason}")

    # Notify partner
    await notifications_col.insert_one({
        "id": str(uuid.uuid4()), "user_id": pa["partner_id"],
        "title": f"Pre-Assessment {review.decision.title()}",
        "message": f"{pa['client_name']} eligibility: {review.decision.upper()}. {review.reason}",
        "type": "pre_assessment_decision", "read": False,
        "created_at": datetime.now(timezone.utc)
    })

    if review.decision == "rejected":
        # Initiate refund
        await pre_assessments_col.update_one({"id": pa_id}, {"$set": {"stage": "refund_initiated"}})
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()), "user_id": pa["partner_id"],
            "title": "Refund Initiated",
            "message": f"₹{PRE_ASSESSMENT_FEE} refund initiated for {pa['client_name']}",
            "type": "refund", "read": False,
            "created_at": datetime.now(timezone.utc)
        })

    return {"message": f"Pre-assessment {review.decision}", "stage": new_stage}


# ===================== PARTNER PROPOSAL ENDPOINTS =====================

@router.post("/{pa_id}/send-proposal")
async def send_proposal(pa_id: str, proposal: ProposalData, http_request: Request, current_user: dict = Depends(get_current_user)):
    """After approval, partner sends sales proposal with payment link to client.
    Supports promo_code, additional_discount (flat ₹), and upsell_bundle_ids.
    """
    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Pre-assessment not found")

    if pa["stage"] != "approved":
        raise HTTPException(status_code=400, detail=f"Pre-assessment is at stage '{pa['stage']}'. It must be at 'approved' stage (after 1st Admin approval) to send a proposal.")

    role = current_user.get("role")
    if role not in ("partner", "admin"):
        raise HTTPException(status_code=403, detail=f"Your role '{role}' cannot send proposals. Please log in as Partner or Admin.")
    if role in ("partner", "sales_executive", "sr_sales_executive") and pa["partner_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="This pre-assessment belongs to another partner. You can only send proposals for your own leads.")

    base_fee = float(proposal.fee_amount or 0)
    if base_fee <= 0:
        raise HTTPException(status_code=400, detail="Base fee must be greater than 0")

    # Resolve upsells
    upsell_items: List[dict] = []
    upsell_total = 0.0
    if proposal.upsell_bundle_ids:
        bundles_col = db["upsell_bundles"]
        items = await bundles_col.find(
            {"id": {"$in": proposal.upsell_bundle_ids}, "is_active": True}, {"_id": 0}
        ).to_list(100)
        for b in items:
            upsell_items.append({"id": b["id"], "name": b["name"], "amount": float(b.get("amount", 0))})
            upsell_total += float(b.get("amount", 0))

    # Resolve promo code
    promo_discount = 0.0
    promo_code_applied = None
    if proposal.promo_code:
        promo_codes_col = db["promo_codes"]
        code_upper = proposal.promo_code.strip().upper()
        promo = await promo_codes_col.find_one({"code": code_upper, "is_active": True}, {"_id": 0})
        if promo:
            if promo.get("current_uses", 0) >= promo.get("max_uses", 100):
                raise HTTPException(status_code=400, detail=f"Promo code {code_upper} has reached max uses")
            pre_upsell_total = base_fee  # promo applies on base fee only
            if promo["discount_type"] == "percentage":
                promo_discount = round(pre_upsell_total * (float(promo["discount_value"]) / 100), 2)
            else:
                promo_discount = float(promo["discount_value"])
            promo_code_applied = code_upper
            # Increment usage
            await promo_codes_col.update_one({"code": code_upper}, {"$inc": {"current_uses": 1}})
        else:
            raise HTTPException(status_code=400, detail=f"Invalid or inactive promo code: {code_upper}")

    additional_discount = max(0.0, float(proposal.additional_discount or 0))
    total_discount = round(promo_discount + additional_discount, 2)
    final_amount = round(max(0.0, base_fee - total_discount + upsell_total), 2)

    # Create a sale record
    sale_id = str(uuid.uuid4())
    sale = {
        "id": sale_id,
        "partner_id": current_user["id"],
        "partner_name": current_user.get("name", ""),
        "client_name": pa["client_name"],
        "client_email": pa["client_email"],
        "client_mobile": pa.get("client_mobile", ""),
        "product_id": pa.get("product_id", ""),
        "product_name": pa.get("product_name", ""),
        "country": pa["country"],
        "service_type": pa["service_type"],
        "fee_amount": final_amount,
        "fee_before_discount": base_fee,
        "base_fee": base_fee,
        "upsell_items": upsell_items,
        "upsell_total": round(upsell_total, 2),
        "promo_code": promo_code_applied,
        "promo_discount_amount": round(promo_discount, 2),
        "additional_discount_amount": round(additional_discount, 2),
        "total_discount_amount": total_discount,
        "amount_received": 0,
        "pending_amount": final_amount,
        "payment_method": proposal.payment_method,
        "currency": proposal.currency,
        "status": "approved",
        "pre_assessment_id": pa_id,
        "notes": proposal.notes,
        "ai_proposal_text": proposal.ai_proposal_text or "",
        "created_at": datetime.now(timezone.utc),
        "approved_at": datetime.now(timezone.utc),
    }
    await sales_col.insert_one(sale)
    sale.pop("_id", None)

    # Generate payment link if Stripe available (uses final_amount)
    payment_url = None
    if STRIPE_API_KEY and final_amount > 0:
        try:
            from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionRequest
            origin = str(http_request.headers.get("origin", http_request.base_url)).rstrip("/")
            success_url = f"{origin}/payment-success?session_id={{CHECKOUT_SESSION_ID}}&type=proposal&pa_id={pa_id}"
            cancel_url = f"{origin}/payment-cancel?type=proposal&pa_id={pa_id}"
            host_url = str(http_request.base_url)
            stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=f"{host_url}api/webhook/stripe")
            session = await stripe_checkout.create_checkout_session(CheckoutSessionRequest(
                amount=float(final_amount), currency="inr",
                success_url=success_url, cancel_url=cancel_url,
                metadata={"type": "proposal", "pa_id": pa_id, "sale_id": sale_id,
                           "client_email": pa["client_email"], "client_name": pa["client_name"]}
            ))
            payment_url = session.url
            await pre_assessments_col.update_one({"id": pa_id}, {"$set": {"proposal_session_id": session.session_id}})
        except Exception as e:
            print(f"Stripe error: {e}")

    await pre_assessments_col.update_one({"id": pa_id}, {"$set": {
        "stage": "proposal_sent",
        "proposal_fee": final_amount,
        "proposal_base_fee": base_fee,
        "proposal_upsells": upsell_items,
        "proposal_upsell_total": round(upsell_total, 2),
        "proposal_promo_code": promo_code_applied,
        "proposal_promo_discount": round(promo_discount, 2),
        "proposal_additional_discount": round(additional_discount, 2),
        "proposal_total_discount": total_discount,
        "proposal_notes": proposal.notes,
        "proposal_ai_text": proposal.ai_proposal_text or "",
        "proposal_status": "sent", "sale_id": sale_id,
        "updated_at": datetime.now(timezone.utc)
    }})

    await log_activity(current_user["id"], current_user.get("name", ""), "send_proposal",
                       "pre_assessment", pa_id, f"Proposal sent to {pa['client_name']} - ₹{final_amount}")

    # Notify admins
    admins = await users_col.find({"role": "admin", "status": "active"}, {"_id": 0, "id": 1}).to_list(50)
    for admin in admins:
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()), "user_id": admin["id"],
            "title": "Proposal Sent",
            "message": f"{current_user.get('name', '')} sent ₹{final_amount:,.0f} proposal to {pa['client_name']}",
            "type": "proposal", "read": False,
            "created_at": datetime.now(timezone.utc)
        })

    return {
        "message": f"Proposal sent to {pa['client_name']}",
        "sale_id": sale_id,
        "payment_url": payment_url,
        "breakdown": {
            "base_fee": base_fee,
            "promo_code": promo_code_applied,
            "promo_discount": round(promo_discount, 2),
            "additional_discount": round(additional_discount, 2),
            "upsell_total": round(upsell_total, 2),
            "total_discount": total_discount,
            "final_amount": final_amount,
        }
    }


# ===================== SHARED ENDPOINTS =====================

@router.get("/my-assessments")
async def get_my_assessments(
    stage: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """Partner gets all their pre-assessments. Admin sees all. Optional ?stage= filter."""
    query = {"partner_id": current_user["id"]}
    if current_user["role"] == "admin":
        query = {}  # Admin sees all
    if stage:
        query["stage"] = stage

    items = await pre_assessments_col.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    for item in items:
        docs_count = await pre_assessment_docs_col.count_documents({"pre_assessment_id": item["id"]})
        item["documents_count"] = docs_count
        for field in ["created_at", "updated_at", "submitted_at", "admin_reviewed_at"]:
            if field in item and item[field] and hasattr(item[field], "isoformat"):
                item[field] = item[field].isoformat()
    return items


@router.get("/{pa_id}")
async def get_pre_assessment(pa_id: str, current_user: dict = Depends(get_current_user)):
    """Get single pre-assessment details (with ownership enforcement)."""
    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Pre-assessment not found")

    # Phase 4A — fix critical scope leak: was previously unrestricted
    _assert_pa_owner(pa, current_user)

    docs = await pre_assessment_docs_col.find(
        {"pre_assessment_id": pa_id}, {"_id": 0}
    ).to_list(100)
    pa["documents"] = docs

    for field in ["created_at", "updated_at", "submitted_at", "admin_reviewed_at"]:
        if field in pa and pa[field] and hasattr(pa[field], "isoformat"):
            pa[field] = pa[field].isoformat()
    for d in docs:
        if hasattr(d.get("created_at"), "isoformat"):
            d["created_at"] = d["created_at"].isoformat()
    return pa


@router.get("/stats/overview")
async def get_stats(current_user: dict = Depends(get_current_user)):
    """Get pre-assessment statistics (runs all counts in parallel for speed)."""
    import asyncio
    query = {}
    if current_user["role"] in OWN_SCOPED_ROLES:
        query = {"partner_id": current_user["id"]}

    stages = [
        ("total", {}),
        ("new", {"stage": "new"}),
        ("payment_pending", {"stage": "payment_pending"}),
        ("payment_received", {"stage": "payment_received"}),
        ("under_review", {"stage": {"$in": ["under_review", "documents_submitted"]}}),
        ("approved", {"stage": "approved"}),
        ("rejected", {"stage": {"$in": ["rejected", "refund_initiated", "refunded"]}}),
        ("proposal_sent", {"stage": "proposal_sent"}),
        ("case_created", {"stage": "case_created"}),
    ]
    results = await asyncio.gather(*[
        pre_assessments_col.count_documents({**query, **q}) for _, q in stages
    ])
    out = {k: v for (k, _), v in zip(stages, results)}
    total = out["total"]
    out["conversion_rate"] = round((out["case_created"] / total * 100) if total > 0 else 0, 1)
    return out


@router.get("/{pa_id}/bundle")
async def get_pa_bundle(pa_id: str, current_user: dict = Depends(get_current_user)):
    """Single round-trip endpoint returning pa + docs + activity + payment_history +
    smart_checklist + risk. Used by expanded PA cards to avoid N+1 requests."""
    import asyncio
    from routers.intelligence import _CHECKLIST_TEMPLATES, _pick_template, _days_since, STAGE_SLA_DAYS

    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Pre-assessment not found")
    role = current_user.get("role")
    if role in ("partner", "sales_executive", "sr_sales_executive") and pa.get("partner_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your pre-assessment")
    if role == "client":
        if (pa.get("client_email") or "").lower() != (current_user.get("email") or "").lower() and pa.get("client_user_id") != current_user["id"]:
            raise HTTPException(status_code=403, detail="Not your pre-assessment")

    # Run all independent queries in parallel
    docs_task = pre_assessment_docs_col.find({"pre_assessment_id": pa_id}, {"_id": 0}).to_list(100)
    activity_task = db["activity_log"].find({"entity_id": pa_id}, {"_id": 0}).sort("created_at", -1).to_list(30)
    invoices_task = db["pa_invoices"].find({"pre_assessment_id": pa_id}, {"_id": 0}).to_list(50)

    docs, activity, invoices = await asyncio.gather(docs_task, activity_task, invoices_task)

    # ISO-serialize dates
    def _iso(obj, fields=("created_at", "updated_at", "submitted_at", "admin_reviewed_at", "sent_at")):
        for f in fields:
            if f in obj and hasattr(obj.get(f), "isoformat"):
                obj[f] = obj[f].isoformat()
        return obj

    _iso(pa)
    for d in docs: _iso(d)
    for a in activity: _iso(a)
    for i in invoices: _iso(i)

    # ============= Payment history events =============
    events = []
    if pa.get("fee_payment_status") == "paid":
        events.append({"ts": pa.get("updated_at"), "kind": "pre_assessment_fee",
                       "label": "Pre-Assessment Fee Paid", "amount": float(pa.get("pre_assessment_fee") or 5100),
                       "direction": "in", "meta": {"reference": pa.get("pa_number")}})
    if pa.get("proposal_status") == "sent":
        events.append({"ts": pa.get("updated_at"), "kind": "proposal_sent",
                       "label": "Proposal Sent to Client", "amount": float(pa.get("proposal_fee") or 0),
                       "direction": "pending", "meta": {"promo_code": pa.get("proposal_promo_code")}})
    if pa.get("stage") in ("proposal_paid", "awaiting_final_approval", "case_created"):
        events.append({"ts": pa.get("updated_at"), "kind": "main_fee_paid",
                       "label": "Main Service Fee Paid", "amount": float(pa.get("proposal_fee") or 0),
                       "direction": "in", "meta": {}})
    for i in invoices:
        events.append({"ts": i.get("sent_at"), "kind": "invoice",
                       "label": f"Invoice {i.get('reference_id')} sent",
                       "amount": float(i.get("amount_received_total") or 0),
                       "direction": "info", "meta": {"reference": i.get("reference_id")}})
    events.sort(key=lambda e: (e.get("ts") or ""), reverse=True)
    totals = {
        "received": sum(e["amount"] for e in events if e["direction"] == "in"),
        "pending": sum(e["amount"] for e in events if e["direction"] == "pending"),
    }

    # ============= Smart checklist =============
    tpl_key = _pick_template(pa)
    items = [dict(it) for it in _CHECKLIST_TEMPLATES[tpl_key]]
    uploaded_types = [(d.get("document_type") or "").lower() for d in docs]
    for it in items:
        cat = it["category"].lower()
        nm = it["name"].split()[0].lower()
        it["uploaded"] = any(cat in u or nm in u for u in uploaded_types)
    done = sum(1 for it in items if it["uploaded"])
    req_done = sum(1 for it in items if it["required"] and it["uploaded"])
    checklist = {
        "template": tpl_key,
        "items": items,
        "stats": {
            "total": len(items), "done": done,
            "required_total": sum(1 for it in items if it["required"]),
            "required_done": req_done,
            "completion_pct": round((done / len(items) * 100) if items else 0, 1),
        },
    }

    # ============= Risk score =============
    score = 50.0
    factors = []
    age = int(pa.get("client_age") or 0)
    if 25 <= age <= 35:
        score += 15; factors.append({"+": "Prime age band (25-35)", "delta": 15})
    elif 35 < age <= 45:
        score += 5; factors.append({"+": "Moderate age band (36-45)", "delta": 5})
    elif age > 45:
        score -= 10; factors.append({"-": "Age above 45 reduces eligibility", "delta": -10})
    edu = (pa.get("education") or "").lower()
    if "masters" in edu or "phd" in edu:
        score += 15; factors.append({"+": "Advanced degree (Masters/PhD)", "delta": 15})
    elif "bachelor" in edu or "degree" in edu:
        score += 8; factors.append({"+": "Bachelor's degree", "delta": 8})
    exp = (pa.get("work_experience") or "").lower()
    if any(t in exp for t in ["5+", "6 ", "7 ", "8 ", "9 ", "10 ", "senior", "lead"]):
        score += 12; factors.append({"+": "5+ years of work experience", "delta": 12})
    if pa.get("fee_payment_status") == "paid":
        score += 8; factors.append({"+": "Pre-assessment fee paid", "delta": 8})
    if len(docs) >= 5:
        score += 8; factors.append({"+": f"{len(docs)} documents uploaded", "delta": 8})
    elif len(docs) == 0 and pa.get("stage") not in ("new", "payment_pending"):
        score -= 15; factors.append({"-": "No documents uploaded yet", "delta": -15})
    idle = _days_since(pa.get("updated_at"))
    sla = STAGE_SLA_DAYS.get(pa.get("stage"), 5)
    if idle > sla * 2:
        score -= 15; factors.append({"-": f"Stuck {idle} days at '{pa.get('stage')}'", "delta": -15})
    elif idle > sla:
        score -= 7; factors.append({"-": f"Idle {idle} days", "delta": -7})
    if pa.get("admin_decision") == "rejected":
        score -= 25; factors.append({"-": "Previously rejected", "delta": -25})
    score = max(0, min(100, round(score, 1)))
    if score >= 75:
        risk = {"score": score, "label": "High Conversion Likelihood", "color": "green", "factors": factors}
    elif score >= 50:
        risk = {"score": score, "label": "Moderate", "color": "amber", "factors": factors}
    else:
        risk = {"score": score, "label": "At Risk", "color": "red", "factors": factors}

    return {
        "pa": pa,
        "documents": docs,
        "activity": activity,
        "payment_history": {"events": events, "totals": totals},
        "checklist": checklist,
        "risk": risk,
    }
