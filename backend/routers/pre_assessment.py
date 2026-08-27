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
import secrets
from core.auth import get_current_user, get_password_hash

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
partner_product_commissions_col = db["partner_product_commissions"]
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
    "installment_pending_approval", # Partner sent an installment-plan proposal — awaiting admin approval
    "proposal_paid",                # Client paid service fee
    "case_created",                 # Case auto-created, process started
    "refund_initiated",             # Refund in progress
    "refunded",                     # Refund completed
    # Phase 4B (Part 2) — Express Sale stages
    "express_pending_approval",     # Express PA awaiting admin approval (no fees needed)
    "express_rejected",             # Admin rejected express request (no payment was made, no refund needed)
    "standard_pending_approval",
    "standard_rejected",
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
    standard_sale_reason: Optional[str] = None
    standard_sale_justification: Optional[str] = None

class AdminReview(BaseModel):
    decision: str  # "approved" or "rejected"
    reason: Optional[str] = ""
    notes: Optional[str] = ""
    suggested_occupation_code: Optional[str] = None
    suggested_occupation_title: Optional[str] = None
    suggested_assessing_authority_code: Optional[str] = None

# ─── Phase: Packages & Payment Methods on Proposal ──────────────────────────
class InstallmentItem(BaseModel):
    amount: float
    due_date: str  # ISO date e.g. "2026-08-15"

class ProposalData(BaseModel):
    fee_amount: float
    payment_method: str = "online"
    notes: str = ""
    currency: str = "INR"
    promo_code: Optional[str] = None
    additional_discount: Optional[float] = 0.0
    upsell_bundle_ids: Optional[List[str]] = []
    ai_proposal_text: Optional[str] = None
    product_package_id: Optional[str] = None
    payment_method_type: str = "full_payment"
    installment_schedule: Optional[List[InstallmentItem]] = None

#  ADD THIS — was missing
class ProposalDraftData(BaseModel):
    fee_amount: float
    notes: str = ""
    currency: str = "INR"
    promo_code: Optional[str] = None
    additional_discount: Optional[float] = 0.0
    upsell_bundle_ids: Optional[List[str]] = []
    ai_proposal_text: Optional[str] = None
class ForwardPackagesData(BaseModel):
    package_ids: List[str]
    notes: str = ""
    ai_proposal_text: Optional[str] = None
class FinalizePaymentMethodData(BaseModel):
    payment_method_type: str  # full_payment | split_50_50 | installments
    installment_schedule: Optional[List[InstallmentItem]] = None
    include_gst: bool = False  # partner toggles this for domestic (India) clients
    coupon_code: Optional[str] = None  # 👈 NEW — admin-defined product coupon

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
        now = datetime.now(timezone.utc)
        express_meta = {
            "sale_type": "standard",
            "pa_fees_skipped": False,
            "standard_sale_reason": data.standard_sale_reason,
            "standard_sale_justification": data.standard_sale_justification,
            "standard_sale_requested_at": now,
            "standard_sale_approval_status": "pending",
            "standard_sale_approved_by": None,
            "standard_sale_approved_at": None,
            "standard_sale_approval_remarks": None,
        }

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
    title = (
    "🚀 New Express Sale — Approval Needed" if sale_type == "express" and starting_stage == "express_pending_approval"
    else "📋 New Standard Sale — Approval Needed" if sale_type == "standard"
    else "New Pre-Assessment Created"
)

    link = (
    "/admin/sales/express-approvals" if sale_type == "express" and starting_stage == "express_pending_approval"
    else "/admin/sales/standard-approvals" if sale_type == "standard"
    else "/admin/pre-assessments"
)
    msg = (
    f"{current_user.get('name', '')} created Express Sale for {data.client_name} — please review"
    if sale_type == "express" and starting_stage == "express_pending_approval"
    else f"{current_user.get('name', '')} created Standard Sale for {data.client_name} — please review"
    if sale_type == "standard"
    else f"{current_user.get('name', '')} created pre-assessment for {data.client_name}"
)
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

    if pa["stage"] not in ["payment_received", "documents_submitted", "partner_review", "rejected", "standard_rejected"]:
        raise HTTPException(status_code=400, detail=f"Cannot submit at stage: {pa['stage']}. Payment must be received first.")

    update_set = {
        "stage": "under_review",
        "partner_remarks": remarks,
        "admin_decision": None,
        "standard_sale_approval_status": "pending",
        "submitted_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }

    await pre_assessments_col.update_one({"id": pa_id}, {"$set": update_set})

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
        "uploaded_by_role": current_user.get("role", ""),   # 👈 NEW
        "created_at": datetime.now(timezone.utc)
    }
    await pre_assessment_docs_col.insert_one(doc)
    doc.pop("_id", None)

    #  NEW — Notify partner when ADMIN uploads a document
    if current_user.get("role") == "admin" and pa.get("partner_id"):
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": pa["partner_id"],
            "title": "Admin uploaded a document",
            "message": f"Admin uploaded '{file.filename}' for {pa.get('client_name')}'s pre-assessment.",
            "type": "admin_document_uploaded", "read": False,
            "link": "/partner?tab=pre-assessment",
            "created_at": datetime.now(timezone.utc)
        })

    return {"id": doc["id"], "message": "Document uploaded", "file_name": file.filename}

class SetOccupationPayload(BaseModel):
    occupation_code: str
    occupation_title: Optional[str] = None
    assessing_authority_code: Optional[str] = None

@router.patch("/{pa_id}/occupation")
@router.post("/{pa_id}/set-occupation")
async def set_pa_occupation(
    pa_id: str,
    payload: SetOccupationPayload,
    current_user: dict = Depends(get_current_user)
):
    """Partner or Admin selects/updates the Occupation Code and Assessing Authority for a Pre-Assessment"""
    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Pre-assessment not found")

    occ_code = payload.occupation_code.strip()
    occ_title = payload.occupation_title.strip() if payload.occupation_title else None
    auth_code = payload.assessing_authority_code.strip() if payload.assessing_authority_code else None

    # Lookup occupation details if needed
    if not occ_title or not auth_code:
        occ = await db_client.get_database()["occupation_master"].find_one(
            {"$or": [{"code": occ_code}, {"anzsco_code": occ_code}]},
            {"_id": 0}
        )
        if occ:
            if not occ_title:
                occ_title = occ.get("title") or occ.get("name")
            if not auth_code:
                auth = occ.get("assessing_authority")
                if isinstance(auth, dict):
                    auth_code = auth.get("short_name") or auth.get("code")
                elif isinstance(auth, str):
                    auth_code = auth

    update_fields = {
        "occupation_code": occ_code,
        "occupation_title": occ_title or occ_code,
        "updated_at": datetime.now(timezone.utc)
    }
    if auth_code:
        update_fields["assessing_authority_code"] = auth_code

    await pre_assessments_col.update_one({"id": pa_id}, {"$set": update_fields})
    return {
        "message": "Occupation code saved",
        "occupation_code": occ_code,
        "occupation_title": occ_title,
        "assessing_authority_code": auth_code
    }


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
        {"stage": {"$in": ["under_review", "documents_submitted", "awaiting_final_approval", "installment_pending_approval"]}}, {"_id": 0}
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

@router.get("/admin/standard-queue")
async def admin_standard_queue(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    items = await pre_assessments_col.find(
        {
            "sale_type": "standard",
            "stage": {"$in": ["standard_pending_approval", "documents_submitted", "under_review"]}
        },
        {"_id": 0}
    ).sort("updated_at", -1).to_list(200)

    for item in items:
        docs = await pre_assessment_docs_col.find(
            {"pre_assessment_id": item["id"]}, {"_id": 0}
        ).to_list(50)
        item["documents"] = docs
        for field in ["created_at", "updated_at", "standard_sale_requested_at",
                    "standard_sale_approved_at", "submitted_at"]:
            if item.get(field) and hasattr(item[field], "isoformat"):
                item[field] = item[field].isoformat()
        for d in docs:
            if hasattr(d.get("created_at"), "isoformat"):
                d["created_at"] = d["created_at"].isoformat()

    return {"items": items}

@router.get("/admin/standard-history")
async def admin_standard_history(current_user: dict = Depends(get_current_user)):
    """Admin: Decided Standard Sale gate approvals"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    items = await pre_assessments_col.find(
        {"sale_type": "standard", "standard_sale_approval_status": {"$in": ["approved", "rejected"]}},
        {"_id": 0}
    ).sort("standard_sale_approved_at", -1).to_list(200)

    for item in items:
        docs = await pre_assessment_docs_col.find(
            {"pre_assessment_id": item["id"]}, {"_id": 0}
        ).to_list(50)
        item["documents"] = docs

        for field in ["created_at", "updated_at", "standard_sale_requested_at",
                    "standard_sale_approved_at"]:
            if field in item and item[field] and hasattr(item[field], "isoformat"):
                item[field] = item[field].isoformat()
        for d in docs:
            if hasattr(d.get("created_at"), "isoformat"):
                d["created_at"] = d["created_at"].isoformat()

    return {"items": items}
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
    role = (current_user.get("role") or current_user.get("rbac_role") or "").lower()
    if role not in ("admin", "admin_owner"):
        raise HTTPException(status_code=403, detail="Admin only")

    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Pre-assessment not found")

    if review.decision not in ["approved", "rejected"]:
        raise HTTPException(status_code=400, detail="Decision must be 'approved' or 'rejected'")

    if pa.get("stage") == "standard_pending_approval":
        if review.decision == "approved":
            await pre_assessments_col.update_one({"id": pa_id}, {"$set": {
                "stage": "new",
                "standard_sale_approval_status": "approved",
                "standard_sale_approved_by": current_user["id"],
                "standard_sale_approved_at": datetime.now(timezone.utc),
                "standard_sale_approval_remarks": review.notes or review.reason or "",
                "updated_at": datetime.now(timezone.utc),
            }})
            await notifications_col.insert_one({
                "id": str(uuid.uuid4()), "user_id": pa["partner_id"],
                "title": "Standard Sale Approved",
                "message": f"Your Standard Sale for {pa['client_name']} was approved. You can now send the pre-assessment payment link.",
                "type": "standard_sale_approved", "read": False,
                "created_at": datetime.now(timezone.utc)
            })
            await log_activity(current_user["id"], current_user.get("name", ""), "standard_sale_approved",
                            "pre_assessment", pa_id, f"Standard Sale approved for {pa['client_name']}")
            return {"message": "Standard Sale approved", "stage": "new"}
        else:
            reason = review.reason or review.notes or ""
            if len(reason.strip()) < 5:
                raise HTTPException(status_code=400, detail="Rejection reason must be at least 5 characters")
            await pre_assessments_col.update_one({"id": pa_id}, {"$set": {
                "stage": "standard_rejected",
                "standard_sale_approval_status": "rejected",
                "standard_sale_approved_by": current_user["id"],
                "standard_sale_approved_at": datetime.now(timezone.utc),
                "standard_sale_approval_remarks": reason.strip(),
                "updated_at": datetime.now(timezone.utc),
            }})
            await notifications_col.insert_one({
                "id": str(uuid.uuid4()), "user_id": pa["partner_id"],
                "title": "Standard Sale Rejected",
                "message": f"Your Standard Sale for {pa['client_name']} was rejected. Reason: {reason.strip()}",
                "type": "standard_sale_rejected", "read": False,
                "created_at": datetime.now(timezone.utc)
            })
            await log_activity(current_user["id"], current_user.get("name", ""), "standard_sale_rejected",
                            "pre_assessment", pa_id, f"Standard Sale rejected for {pa['client_name']}: {reason.strip()}")
            return {"message": "Standard Sale rejected", "stage": "standard_rejected"}

    new_stage = ("case_created" if pa.get("case_id") or pa.get("stage") == "case_created" else "approved") if review.decision == "approved" else "rejected"

    update_fields = {
        "stage": new_stage,
        "admin_decision": review.decision,
        "admin_reason": review.reason,
        "admin_notes": review.notes,
        "admin_reviewed_by": current_user["id"],
        "admin_reviewed_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }

    if review.suggested_occupation_code:
        update_fields["suggested_occupation_code"] = review.suggested_occupation_code.strip()
        update_fields["suggested_occupation_title"] = (review.suggested_occupation_title or "").strip()
        update_fields["suggested_assessing_authority_code"] = (review.suggested_assessing_authority_code or "").strip()
    elif review.decision == "approved":
        update_fields["suggested_occupation_code"] = None
        update_fields["suggested_occupation_title"] = None
        update_fields["suggested_assessing_authority_code"] = None

    # Mirror decision into standard_sale_* fields so it also shows in
    # "Standard Sale Approvals" history tab (unified tracking view)
    if pa.get("sale_type") == "standard":
        update_fields["standard_sale_approval_status"] = review.decision
        update_fields["standard_sale_approved_by"] = current_user["id"]
        update_fields["standard_sale_approved_at"] = datetime.now(timezone.utc)
        update_fields["standard_sale_approval_remarks"] = review.notes or review.reason or ""

    if review.decision == "approved":
        update_fields["client_occupation_review_status"] = "pending_client_review"
        update_fields["client_suggested_occupation_code"] = None
        update_fields["client_suggested_occupation_title"] = None
        update_fields["client_suggested_occupation_notes"] = None
        update_fields["suggested_occupation_code"] = None
        update_fields["suggested_occupation_title"] = None
        update_fields["suggested_assessing_authority_code"] = None

    await pre_assessments_col.update_one({"id": pa_id}, {"$set": update_fields})

    # Sync to linked case(s)
    if review.decision == "approved":
        approved_code = pa.get("occupation_code") or review.suggested_occupation_code or ""
        approved_title = pa.get("occupation_title") or review.suggested_occupation_title or ""
        approved_auth = pa.get("assessing_authority_code") or review.suggested_assessing_authority_code or ""
        case_up = {
            "occupation_code": approved_code,
            "occupation_title": approved_title,
            "assessing_authority_code": approved_auth,
            "client_occupation_review_status": "pending_client_review",
            "client_suggested_occupation_code": None,
            "client_suggested_occupation_title": None,
            "client_suggested_occupation_notes": None,
            "suggested_occupation_code": None,
            "updated_at": datetime.now(timezone.utc),
        }
        await cases_col.update_many(
            {"$or": [
                {"pre_assessment_id": pa_id},
                {"id": pa.get("case_id") or "____"},
                {"client_email": (pa.get("client_email") or "____").lower()},
                {"client_id": pa.get("client_user_id") or "____"},
            ]},
            {"$set": case_up}
        )

    await log_activity(current_user["id"], current_user.get("name", ""), f"pa_{review.decision}",
                    "pre_assessment", pa_id, f"Pre-assessment {review.decision} for {pa['client_name']} - {review.reason}")

    # Notify partner with suggestion if present
    suggested_text = f" Suggested code: {review.suggested_occupation_code} - {review.suggested_occupation_title}" if review.suggested_occupation_code else ""
    await notifications_col.insert_one({
        "id": str(uuid.uuid4()), "user_id": pa["partner_id"],
        "title": f"Pre-Assessment {review.decision.title()}",
        "message": f"{pa['client_name']} eligibility: {review.decision.upper()}. {review.reason}{suggested_text}",
        "type": "pre_assessment_decision", "read": False,
        "created_at": datetime.now(timezone.utc)
    })

    # Notify client if approved
    if review.decision == "approved" and (pa.get("client_user_id") or pa.get("client_id")):
        client_uid = pa.get("client_user_id") or pa.get("client_id")
        occ_desc = f"{pa.get('occupation_code')} - {pa.get('occupation_title')}"
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()), "user_id": client_uid,
            "title": "Occupation Profile Approved",
            "message": f"Admin has approved your occupation code: {occ_desc}. Please review and accept in your client portal.",
            "type": "occupation_approved", "read": False,
            "link": "/client",
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


class ClientSuggestionPayload(BaseModel):
    remarks: Optional[str] = ""


@router.post("/{pa_id}/submit-client-suggestion-to-admin")
async def submit_client_suggestion_to_admin(
    pa_id: str,
    payload: Optional[ClientSuggestionPayload] = None,
    current_user: dict = Depends(get_current_user)
):
    """Partner submits client's requested occupation code change to Admin for approval"""
    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Pre-assessment not found")

    now = datetime.now(timezone.utc)
    suggested_code = pa.get("client_suggested_occupation_code") or pa.get("occupation_code")
    suggested_title = pa.get("client_suggested_occupation_title") or pa.get("occupation_title") or f"ANZSCO {suggested_code}"
    notes = pa.get("client_suggested_occupation_notes") or (payload.remarks if payload else "")

    update_doc = {
        "stage": "under_review",
        "standard_sale_approval_status": "pending",
        "admin_decision": None,
        "occupation_code": suggested_code,
        "occupation_title": suggested_title,
        "suggested_occupation_code": None,
        "suggested_occupation_title": None,
        "suggested_assessing_authority_code": None,
        "client_occupation_review_status": "pending_admin_approval",
        "partner_remarks": f"Client requested occupation change: {suggested_code} - {suggested_title}. Note: {notes}",
        "submitted_at": now,
        "updated_at": now,
    }
    await pre_assessments_col.update_one({"id": pa_id}, {"$set": update_doc})

    if pa.get("case_id"):
        await cases_col.update_one({"id": pa["case_id"]}, {"$set": {
            "occupation_code": suggested_code,
            "occupation_title": suggested_title,
            "client_occupation_review_status": "pending_admin_approval",
            "updated_at": now,
        }})

    admins = await users_col.find({"role": "admin", "status": "active"}, {"_id": 0, "id": 1}).to_list(50)
    for admin in admins:
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()), "user_id": admin["id"],
            "title": "Client Requested Occupation Change",
            "message": f"{pa['client_name']} requested occupation change to {suggested_code} - {suggested_title}. Submitted by Partner {pa.get('partner_name')} for Admin Approval.",
            "type": "occupation_change_approval", "read": False,
            "link": "/admin/standard-approvals",
            "created_at": now,
        })

    return {"message": "Client suggestion submitted to Admin for approval"}


# ===================== PARTNER PROPOSAL ENDPOINTS =====================
@router.post("/{pa_id}/send-proposal-draft")
async def send_proposal_draft(pa_id: str, data: ProposalDraftData, current_user: dict = Depends(get_current_user)):
    """Partner sends base proposal terms WITHOUT picking a package.
    Client then picks the package from their portal; partner finalizes payment method after."""
    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Pre-assessment not found")
    if pa["stage"] != "approved":
        raise HTTPException(status_code=400, detail=f"Must be at 'approved' stage. Current: {pa['stage']}")
    role = current_user.get("role")
    if role in ("partner", "sales_executive", "sr_sales_executive") and pa["partner_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your pre-assessment")

    product = await products_col.find_one({"id": pa.get("product_id", "")}, {"_id": 0, "packages": 1, "name": 1})
    packages = [p for p in (product.get("packages") or []) if p.get("is_active", True)] if product else []
    if not packages:
        raise HTTPException(status_code=400, detail="This product has no active packages configured. Ask admin to set up packages first.")

    await pre_assessments_col.update_one({"id": pa_id}, {"$set": {
        "stage": "awaiting_package_selection",
        "proposal_draft_fee": float(data.fee_amount),
        "proposal_draft_notes": data.notes,
        "proposal_draft_currency": data.currency,
        "proposal_draft_promo_code": data.promo_code,
        "proposal_draft_additional_discount": data.additional_discount,
        "proposal_draft_upsell_bundle_ids": data.upsell_bundle_ids,
        "proposal_draft_ai_text": data.ai_proposal_text,
        "available_packages_snapshot": packages,  # frozen at send time
        "selected_package_id": None,
        "updated_at": datetime.now(timezone.utc),
    }})

    await log_activity(current_user["id"], current_user.get("name", ""), "send_proposal_draft",
                    "pre_assessment", pa_id, f"Proposal draft sent to {pa['client_name']} — awaiting client package selection")

    return {"message": "Sent to client for package selection", "stage": "awaiting_package_selection", "packages": packages}

@router.post("/{pa_id}/forward-packages")
async def forward_packages(pa_id: str, data: ForwardPackagesData, current_user: dict = Depends(get_current_user)):
    """Partner selects specific packages (from the product's configured packages) and
    forwards ONLY those to the client. Client picks one from their portal;
    partner finalizes the payment method after (see /finalize-payment-method)."""
    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Pre-assessment not found")
    if pa["stage"] != "approved":
        raise HTTPException(status_code=400, detail=f"Must be at 'approved' stage. Current: {pa['stage']}")
    role = current_user.get("role")
    if role in ("partner", "sales_executive", "sr_sales_executive") and pa["partner_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your pre-assessment")

    if not data.package_ids:
        raise HTTPException(status_code=400, detail="Select at least one package")

    product = await products_col.find_one({"id": pa.get("product_id", "")}, {"_id": 0, "packages": 1, "name": 1})
    if not product:
        raise HTTPException(status_code=400, detail="This pre-assessment isn't linked to a product. Ask admin to link a product first.")

    all_packages = product.get("packages") or []
    selected = [p for p in all_packages if p.get("id") in data.package_ids and p.get("is_active", True)]
    if not selected:
        raise HTTPException(status_code=400, detail="None of the selected packages are valid/active")

    await pre_assessments_col.update_one({"id": pa_id}, {"$set": {
        "stage": "awaiting_package_selection",
        "proposal_draft_notes": data.notes,
        "proposal_draft_ai_text": data.ai_proposal_text,
        "available_packages_snapshot": selected,
        "selected_package_id": None,
        "updated_at": datetime.now(timezone.utc),
    }})

    await log_activity(current_user["id"], current_user.get("name", ""), "forward_packages",
                    "pre_assessment", pa_id, f"{len(selected)} package(s) forwarded to {pa['client_name']} for selection")

    if pa.get("client_user_id"):
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()), "user_id": pa["client_user_id"],
            "title": "Choose your package",
            "message": f"Your partner sent you {len(selected)} package option(s) to choose from.",
            "type": "package_selection_pending", "read": False,
            "created_at": datetime.now(timezone.utc)
        })

    return {"message": "Packages sent to client for selection", "stage": "awaiting_package_selection", "packages": selected}

@router.post("/{pa_id}/finalize-payment-method")
async def finalize_payment_method(pa_id: str, data: FinalizePaymentMethodData, current_user: dict = Depends(get_current_user)):
    """Partner sets the payment method (full / 50-50 / installments) AFTER the client
    has already picked a package. Creates the sale record + payment_parts schedule,
    same shape as /send-proposal, but using the client-selected package's price."""
    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Pre-assessment not found")
    if pa["stage"] != "package_selected":
        raise HTTPException(status_code=400, detail=f"Must be at 'package_selected' stage. Current: {pa['stage']}")
    role = current_user.get("role")
    if role in ("partner", "sales_executive", "sr_sales_executive") and pa["partner_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your pre-assessment")

    selected_package = pa.get("selected_package_snapshot")
    if not selected_package:
        raise HTTPException(status_code=400, detail="No package selected by client")

    base_fee = float(selected_package.get("price") or 0)
    if base_fee <= 0:
        raise HTTPException(status_code=400, detail="Selected package has no valid price")

    # 👇 NEW — Validate + apply coupon (server-side truth, never trust frontend amount)
    coupon_applied = None
    discount_amount = 0.0
    if data.coupon_code:
        product_doc = await products_col.find_one({"id": pa.get("product_id", "")}, {"_id": 0, "discount_coupons": 1})
        all_coupons = (product_doc or {}).get("discount_coupons") or []
        code_upper = data.coupon_code.strip().upper()
        coupon_applied = next(
            (c for c in all_coupons if (c.get("code") or "").upper() == code_upper and c.get("is_active", True)),
            None
        )
        if not coupon_applied:
            raise HTTPException(status_code=400, detail=f"Invalid or inactive coupon code: {code_upper}")
        if coupon_applied["discount_type"] == "percentage":
            discount_amount = round(base_fee * float(coupon_applied["discount_value"]) / 100, 2)
        else:
            discount_amount = round(float(coupon_applied["discount_value"]), 2)
        discount_amount = min(discount_amount, base_fee)

    discounted_fee = round(base_fee - discount_amount, 2)

    include_gst = bool(data.include_gst)
    gst_amount = round(discounted_fee * 0.18, 2) if include_gst else 0.0
    final_amount = round(discounted_fee + gst_amount, 2)

    payment_method_type = data.payment_method_type

    if payment_method_type not in ("full_payment", "split_50_50", "installments"):
        raise HTTPException(status_code=400, detail="Invalid payment_method_type")

    pm_config = (selected_package.get("payment_methods") or {}).get(payment_method_type)
    if not pm_config or not pm_config.get("enabled"):
        raise HTTPException(status_code=400, detail=f"Payment method '{payment_method_type}' is not enabled for this package")

    is_installments = payment_method_type == "installments"
    installment_total = None
    if is_installments:
        if not data.installment_schedule or len(data.installment_schedule) < 2:
            raise HTTPException(status_code=400, detail="Installment schedule must have at least 2 entries")
        max_allowed = (pm_config or {}).get("max_installments", 5)
        if len(data.installment_schedule) > max_allowed:
            raise HTTPException(status_code=400, detail=f"Max {max_allowed} installments allowed for this package")
        installment_total = round(sum(i.amount for i in data.installment_schedule), 2)
        if abs(installment_total - final_amount) > 1:
            raise HTTPException(status_code=400, detail=f"Installment total (₹{installment_total:,.0f}) must equal package price (₹{final_amount:,.0f})")

    # Build payment_parts
    payment_parts = []
    if payment_method_type == "split_50_50":
        first_pct = float(pm_config.get("first_pct") or 50)
        trigger = pm_config.get("trigger_condition") or ""
        part1 = round(final_amount * first_pct / 100, 2)
        part2 = round(final_amount - part1, 2)
        payment_parts = [
            {"index": 0, "label": f"1st Installment ({first_pct:.0f}%)", "amount": part1,
            "status": "pending", "due_date": None, "trigger_condition": None},
            {"index": 1, "label": f"2nd Installment ({100-first_pct:.0f}%)", "amount": part2,
            "status": "locked", "due_date": None, "trigger_condition": trigger or "Admin unlock required"},
        ]
    elif is_installments:
        payment_parts = [
            {"index": idx, "label": f"Installment {idx+1}", "amount": round(inst.amount, 2),
            "status": "pending" if idx == 0 else "locked",
            "due_date": inst.due_date, "trigger_condition": None}
            for idx, inst in enumerate(data.installment_schedule)
        ]
    else:  # full_payment
        payment_parts = [
            {"index": 0, "label": "Full Payment", "amount": final_amount,
            "status": "pending", "due_date": None, "trigger_condition": None},
        ]

    # Resolve commission rate (same logic as send_proposal)
    product = await products_col.find_one({"id": pa.get("product_id", "")}, {"_id": 0}) or {}
    custom = await partner_product_commissions_col.find_one(
        {"partner_id": current_user["id"], "product_id": pa.get("product_id", "")}, {"_id": 0}
    )
    if custom:
        commission_rate = custom["commission_rate"]
    elif product.get("commission_rate") is not None and product.get("commission_rate", 0) > 0:
        commission_rate = product["commission_rate"]
    else:
        sales_comm_alloc = next(
            (a for a in (product.get("cost_allocations") or []) if a.get("vendor_category") == "sales_commission"),
            None
        )
        if sales_comm_alloc and sales_comm_alloc.get("payment_type") == "percentage" and float(sales_comm_alloc.get("rate") or 0) > 0:
            commission_rate = float(sales_comm_alloc["rate"])
        else:
            commission_rate = current_user.get("commission_rate", 0)
    commission_amount = 0  # amount_received starts at 0

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
        "coupon_code": coupon_applied["code"] if coupon_applied else None,
        "coupon_discount_type": coupon_applied["discount_type"] if coupon_applied else None,
        "coupon_discount_value": coupon_applied["discount_value"] if coupon_applied else None,
        "coupon_discount_amount": discount_amount,
        "discounted_fee": discounted_fee,
        "gst_included": include_gst,
        "gst_amount": gst_amount,
        "upsell_items": [],
        "upsell_total": 0,
        "promo_code": None,
        "promo_discount_amount": 0,
        "additional_discount_amount": 0,
        "total_discount_amount": 0,
        "amount_received": 0,
        "pending_amount": final_amount,
        "payment_method": "online",
        "currency": "INR",
        "status": "pending_installment_approval" if is_installments else "approved",
        "commission_rate": commission_rate,
        "commission_amount": commission_amount,
        "pre_assessment_id": pa_id,
        "notes": pa.get("proposal_draft_notes", ""),
        "ai_proposal_text": pa.get("proposal_draft_ai_text", ""),
        "product_package_id": selected_package.get("id"),
        "product_package_name": selected_package.get("name"),
        "payment_method_type": payment_method_type,
        "installment_schedule": [i.dict() for i in data.installment_schedule] if data.installment_schedule else None,
        "payment_parts": payment_parts,
        "amount_paid_so_far": 0,
        "created_at": datetime.now(timezone.utc),
        "approved_at": datetime.now(timezone.utc),
    }
    await sales_col.insert_one(sale)

    new_stage = "installment_pending_approval" if is_installments else "proposal_sent"

    await pre_assessments_col.update_one({"id": pa_id}, {"$set": {
        "stage": new_stage,
        "proposal_fee": final_amount,
        "proposal_base_fee": base_fee,
        "proposal_coupon_code": coupon_applied["code"] if coupon_applied else None,
        "proposal_coupon_discount_amount": discount_amount,
        "proposal_discounted_fee": discounted_fee,
        "proposal_gst_included": include_gst,
        "proposal_gst_amount": gst_amount,
        "proposal_upsells": [],
        "proposal_upsell_total": 0,
        "proposal_promo_code": None,
        "proposal_promo_discount": 0,
        "proposal_additional_discount": 0,
        "proposal_total_discount": 0,
        "proposal_notes": pa.get("proposal_draft_notes", ""),
        "proposal_ai_text": pa.get("proposal_draft_ai_text", ""),
        "proposal_status": "pending_installment_approval" if is_installments else "sent",
        "sale_id": sale_id,
        "product_package_id": selected_package.get("id"),
        "product_package_name": selected_package.get("name"),
        "proposal_payment_method_type": payment_method_type,
        "proposal_installment_schedule": [i.dict() for i in data.installment_schedule] if data.installment_schedule else None,
        "proposal_payment_parts": payment_parts,
        "proposal_amount_paid": 0,
        "proposal_amount_pending": final_amount,
        "updated_at": datetime.now(timezone.utc),
    }})

    await log_activity(current_user["id"], current_user.get("name", ""), "finalize_payment_method",
                    "pre_assessment", pa_id, f"Payment method '{payment_method_type}' set for {pa['client_name']} — ₹{final_amount}")

    if pa.get("client_user_id"):
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()), "user_id": pa["client_user_id"],
            "title": "Payment ready" if not is_installments else "Installment plan submitted",
            "message": (
                f"Your payment plan is ready — ₹{final_amount:,.0f} ({payment_method_type})"
                if not is_installments else
                f"Installment plan for ₹{final_amount:,.0f} submitted for admin approval"
            ),
            "type": "payment_ready", "read": False,
            "created_at": datetime.now(timezone.utc)
        })

    if is_installments:
        admins = await users_col.find({"role": "admin", "status": "active"}, {"_id": 0, "id": 1}).to_list(50)
        for admin in admins:
            await notifications_col.insert_one({
                "id": str(uuid.uuid4()), "user_id": admin["id"],
                "title": "Installment Approval Needed",
                "message": f"{current_user.get('name', '')} sent an installment plan (₹{final_amount:,.0f}) for {pa['client_name']} — needs your approval",
                "type": "installment_pending", "read": False,
                "link": "/admin/pre-assessments",
                "created_at": datetime.now(timezone.utc)
            })

    return {
        "message": (
            f"Installment plan for {pa['client_name']} sent for admin approval"
            if is_installments else
            f"Payment method set — {pa['client_name']} can now pay"
        ),
        "stage": new_stage,
        "sale_id": sale_id,
    }

class SpouseInfoData(BaseModel):
    name: str
    mobile: str = ""
    email: str = ""
    age: Optional[int] = None
    education: str = ""
    work_experience: str = ""
    notes: str = ""

@router.post("/{pa_id}/spouse-info")
async def save_spouse_info(pa_id: str, data: SpouseInfoData, current_user: dict = Depends(get_current_user)):
    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Pre-assessment not found")
    role = current_user.get("role")
    if role in ("partner", "sales_executive", "sr_sales_executive") and pa.get("partner_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your pre-assessment")
    if pa.get("stage") != "package_selected":
        raise HTTPException(status_code=400, detail=f"Cannot add spouse info at stage: {pa.get('stage')}")

    await pre_assessments_col.update_one({"id": pa_id}, {"$set": {
        "spouse_info": data.dict(),
        "updated_at": datetime.now(timezone.utc),
    }})
    await log_activity(current_user["id"], current_user.get("name", ""), "spouse_info_saved",
                        "pre_assessment", pa_id, f"Spouse/partner info recorded for {pa['client_name']}")

    # 👇 NEW — notify admins right away so they know a 2nd person (sponsor/spouse)
    # will also need a case + case manager once the case is created.
    admins = await users_col.find({"role": "admin", "status": "active"}, {"_id": 0, "id": 1}).to_list(50)
    for admin in admins:
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()), "user_id": admin["id"],
            "title": "Partner/Spouse details added",
            "message": f"{pa['client_name']}'s partner/spouse '{data.name}' added — this case will need a 2nd case manager assignment too.",
            "type": "spouse_info_added", "read": False,
            "link": "/admin?tab=pre-assessments",
            "created_at": datetime.now(timezone.utc),
        })

    return {"ok": True, "spouse_info": data.dict()}

@router.post("/{pa_id}/send-proposal")
async def send_proposal(pa_id: str, proposal: ProposalData, http_request: Request, current_user: dict = Depends(get_current_user)):
    """After approval, partner sends sales proposal with payment link to client.
    Supports promo_code, additional_discount (flat ₹), upsell_bundle_ids, and now
    Package + Payment Method selection (full_payment / split_50_50 / installments).
    Installments require a subsequent admin approval (see /review-installments).
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

    # ─── Resolve selected package (overrides manual fee_amount) ────────────
    selected_package = None
    if proposal.product_package_id:
        product_full = await products_col.find_one({"id": pa.get("product_id", "")}, {"_id": 0, "packages": 1})
        if not product_full:
            raise HTTPException(status_code=400, detail="Product not found for this pre-assessment")
        selected_package = next(
            (p for p in (product_full.get("packages") or []) if p.get("id") == proposal.product_package_id),
            None
        )
        if not selected_package:
            raise HTTPException(status_code=400, detail="Selected package not found on this product")
        if not selected_package.get("is_active", True):
            raise HTTPException(status_code=400, detail=f"Package '{selected_package.get('name')}' is not active")

        pm_config = (selected_package.get("payment_methods") or {}).get(proposal.payment_method_type)
        if not pm_config or not pm_config.get("enabled"):
            raise HTTPException(
                status_code=400,
                detail=f"Payment method '{proposal.payment_method_type}' is not enabled for package '{selected_package.get('name')}'"
            )

    base_fee = float(selected_package["price"]) if selected_package else float(proposal.fee_amount or 0)
    if base_fee <= 0:
        raise HTTPException(status_code=400, detail="Base fee must be greater than 0")

    is_installments = proposal.payment_method_type == "installments"

    # ─── Validate installment schedule if that payment method chosen ───────
    installment_total = None
    if is_installments:
        if not proposal.installment_schedule or len(proposal.installment_schedule) < 2:
            raise HTTPException(status_code=400, detail="Installment schedule must have at least 2 entries")
        max_allowed = ((selected_package or {}).get("payment_methods", {}).get("installments", {}) or {}).get("max_installments", 5)
        if len(proposal.installment_schedule) > max_allowed:
            raise HTTPException(status_code=400, detail=f"Max {max_allowed} installments allowed for this package")
        installment_total = round(sum(i.amount for i in proposal.installment_schedule), 2)

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

    if is_installments and installment_total is not None:
        if abs(installment_total - final_amount) > 1:  # ₹1 rounding tolerance
            raise HTTPException(
                status_code=400,
                detail=f"Installment total (₹{installment_total:,.0f}) must equal final amount (₹{final_amount:,.0f})"
            )

# ─── Build payment_parts — the actual schedule the client will pay against ──
    payment_parts = []
    if proposal.payment_method_type == "split_50_50":
        pm = (selected_package.get("payment_methods", {}).get("split_50_50") or {}) if selected_package else {}
        first_pct = float(pm.get("first_pct") or 50)
        trigger = pm.get("trigger_condition") or ""
        part1 = round(final_amount * first_pct / 100, 2)
        part2 = round(final_amount - part1, 2)
        payment_parts = [
            {"index": 0, "label": f"1st Installment ({first_pct:.0f}%)", "amount": part1,
             "status": "pending", "due_date": None, "trigger_condition": None},
            {"index": 1, "label": f"2nd Installment ({100-first_pct:.0f}%)", "amount": part2,
             "status": "locked", "due_date": None, "trigger_condition": trigger or "Admin unlock required"},
        ]
    elif is_installments and proposal.installment_schedule:
        payment_parts = [
            {"index": idx, "label": f"Installment {idx+1}", "amount": round(inst.amount, 2),
             "status": "pending" if idx == 0 else "locked",
             "due_date": inst.due_date, "trigger_condition": None}
            for idx, inst in enumerate(proposal.installment_schedule)
        ]
    else:  # full_payment
        payment_parts = [
            {"index": 0, "label": "Full Payment", "amount": final_amount,
             "status": "pending", "due_date": None, "trigger_condition": None},
        ]

    # --- Resolve commission rate (same logic as the direct-sale flow in sales.py) ---
    product = await products_col.find_one({"id": pa.get("product_id", "")}, {"_id": 0}) or {}
    custom = await partner_product_commissions_col.find_one(
        {"partner_id": current_user["id"], "product_id": pa.get("product_id", "")}, {"_id": 0}
    )
    if custom:
        commission_rate = custom["commission_rate"]
    elif product.get("commission_rate") is not None and product.get("commission_rate", 0) > 0:
        commission_rate = product["commission_rate"]
    else:
        sales_comm_alloc = next(
            (a for a in (product.get("cost_allocations") or []) if a.get("vendor_category") == "sales_commission"),
            None
        )
        if sales_comm_alloc and sales_comm_alloc.get("payment_type") == "percentage" and float(sales_comm_alloc.get("rate") or 0) > 0:
            commission_rate = float(sales_comm_alloc["rate"])
        else:
            commission_rate = current_user.get("commission_rate", 0)
    commission_amount = round(0 * (commission_rate / 100), 2) if commission_rate else 0  # amount_received starts at 0

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
        "status": "pending_installment_approval" if is_installments else "approved",
        "commission_rate": commission_rate,
        "commission_amount": commission_amount,
        "pre_assessment_id": pa_id,
        "notes": proposal.notes,
        "ai_proposal_text": proposal.ai_proposal_text or "",
        # 👇 Package + Payment method tracking
        "product_package_id": proposal.product_package_id,
        "product_package_name": selected_package.get("name") if selected_package else None,
        "payment_method_type": proposal.payment_method_type,
        "installment_schedule": [i.dict() for i in proposal.installment_schedule] if proposal.installment_schedule else None,
        "payment_parts": payment_parts,
        "amount_paid_so_far": 0,
        "created_at": datetime.now(timezone.utc),
        "approved_at": datetime.now(timezone.utc),
    }
    await sales_col.insert_one(sale)
    sale.pop("_id", None)

    # Generate payment link if Stripe available (uses final_amount) — SKIPPED for installments,
    # since the first-installment link is only generated after admin approves the plan.
    payment_url = None
    if STRIPE_API_KEY and final_amount > 0 and not is_installments:
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

    new_stage = "installment_pending_approval" if is_installments else "proposal_sent"

    await pre_assessments_col.update_one({"id": pa_id}, {"$set": {
        "stage": new_stage,
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
        "proposal_status": "pending_installment_approval" if is_installments else "sent",
        "sale_id": sale_id,
        #  Package + Payment method tracking
        "product_package_id": proposal.product_package_id,
        "product_package_name": selected_package.get("name") if selected_package else None,
        "proposal_payment_method_type": proposal.payment_method_type,
        "proposal_installment_schedule": [i.dict() for i in proposal.installment_schedule] if proposal.installment_schedule else None,
        #  NEW — the actual part-by-part payment schedule used by client_mock_pay_proposal()
        "proposal_payment_parts": payment_parts,
        "proposal_amount_paid": 0,
        "proposal_amount_pending": final_amount,
        "updated_at": datetime.now(timezone.utc)
    }})

    await log_activity(current_user["id"], current_user.get("name", ""), "send_proposal",
                    "pre_assessment", pa_id, f"Proposal sent to {pa['client_name']} - ₹{final_amount} ({proposal.payment_method_type})")

    # Notify admins
    admins = await users_col.find({"role": "admin", "status": "active"}, {"_id": 0, "id": 1}).to_list(50)
    for admin in admins:
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()), "user_id": admin["id"],
            "title": "Installment Approval Needed" if is_installments else "Proposal Sent",
            "message": (
                f"{current_user.get('name', '')} sent an installment proposal (₹{final_amount:,.0f}) for {pa['client_name']} — needs your approval"
                if is_installments else
                f"{current_user.get('name', '')} sent ₹{final_amount:,.0f} proposal to {pa['client_name']}"
            ),
            "type": "installment_pending" if is_installments else "proposal", "read": False,
            "link": "/admin/pre-assessments",
            "created_at": datetime.now(timezone.utc)
        })

    return {
        "message": (
            f"Installment proposal for {pa['client_name']} sent for admin approval"
            if is_installments else
            f"Proposal sent to {pa['client_name']}"
        ),
        "stage": new_stage,
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

# ─── Admin — Approve / Reject Installment Plan ──────────────────────────────
class InstallmentReview(BaseModel):
    decision: str  # "approved" or "rejected"
    reason: str = ""


@router.put("/{pa_id}/review-installments")
async def review_installment_proposal(pa_id: str, review: InstallmentReview, http_request: Request,
                                    current_user: dict = Depends(get_current_user)):
    """Admin approves/rejects the partner-proposed installment payment plan.

    On approval: generates a Stripe payment link for the FIRST installment only
    and moves the PA to 'proposal_sent' so the partner can share it with the client.
    On rejection: bounces the PA back to 'approved' so the partner can resend a
    revised proposal (e.g. different payment method).
    """
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Pre-assessment not found")
    if pa.get("stage") != "installment_pending_approval":
        raise HTTPException(status_code=400, detail=f"PA is at stage '{pa.get('stage')}', not awaiting installment approval")

    if review.decision not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="Decision must be 'approved' or 'rejected'")

    if review.decision == "rejected":
        await pre_assessments_col.update_one({"id": pa_id}, {"$set": {
            "stage": "approved",  # bounce back so partner can re-send proposal
            "updated_at": datetime.now(timezone.utc),
        }})
        if pa.get("sale_id"):
            await sales_col.update_one({"id": pa["sale_id"]}, {"$set": {"status": "rejected"}})
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()), "user_id": pa["partner_id"],
            "title": "Installment Plan Rejected",
            "message": f"Installment plan for {pa['client_name']} was rejected: {review.reason}. Please resend the proposal.",
            "type": "installment_rejected", "read": False,
            "created_at": datetime.now(timezone.utc)
        })
        await log_activity(current_user["id"], current_user.get("name", ""), "installment_rejected",
                        "pre_assessment", pa_id, f"Installment plan rejected for {pa['client_name']}: {review.reason}")
        return {"message": "Installment plan rejected", "stage": "approved"}

    # Approved — generate payment link for FIRST installment only
    schedule = pa.get("proposal_installment_schedule") or []
    first_amount = float(schedule[0]["amount"]) if schedule else float(pa.get("proposal_fee") or 0)

    payment_url = None
    if STRIPE_API_KEY and first_amount > 0:
        try:
            from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionRequest
            origin = str(http_request.headers.get("origin", http_request.base_url)).rstrip("/")
            success_url = f"{origin}/payment-success?session_id={{CHECKOUT_SESSION_ID}}&type=installment&pa_id={pa_id}&idx=0"
            cancel_url = f"{origin}/payment-cancel?type=installment&pa_id={pa_id}"
            host_url = str(http_request.base_url)
            stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=f"{host_url}api/webhook/stripe")
            session = await stripe_checkout.create_checkout_session(CheckoutSessionRequest(
                amount=float(first_amount), currency="inr",
                success_url=success_url, cancel_url=cancel_url,
                metadata={"type": "installment", "pa_id": pa_id, "installment_index": "0"}
            ))
            payment_url = session.url
        except Exception as e:
            print(f"Stripe error (installment): {e}")

    await pre_assessments_col.update_one({"id": pa_id}, {"$set": {
        "stage": "proposal_sent",
        "proposal_status": "sent",
        "installment_approved_by": current_user["id"],
        "installment_approved_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }})
    if pa.get("sale_id"):
        await sales_col.update_one({"id": pa["sale_id"]}, {"$set": {"status": "approved"}})

    await notifications_col.insert_one({
        "id": str(uuid.uuid4()), "user_id": pa["partner_id"],
        "title": "Installment Plan Approved",
        "message": f"Installment plan for {pa['client_name']} approved. First installment link is ready to share.",
        "type": "installment_approved", "read": False,
        "created_at": datetime.now(timezone.utc)
    })
    await log_activity(current_user["id"], current_user.get("name", ""), "installment_approved",
                    "pre_assessment", pa_id, f"Installment plan approved for {pa['client_name']}")

    return {"message": "Installment plan approved", "stage": "proposal_sent", "payment_url": payment_url}


# ─── Partner: forward an installment payment for admin unlock ──────────────
@router.post("/{pa_id}/forward-installment-review")
async def forward_installment_review(pa_id: str, current_user: dict = Depends(get_current_user)):
    """Partner reviews a just-paid installment and forwards it to admin so the
    NEXT installment can be unlocked for the client."""
    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Pre-assessment not found")

    role = current_user.get("role")
    if role in ("partner", "sales_executive", "sr_sales_executive") and pa.get("partner_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not your pre-assessment")
    if role not in ("admin", "partner", "sales_executive", "sr_sales_executive"):
        raise HTTPException(status_code=403, detail="Not authorized")

    if not pa.get("pending_installment_unlock"):
        raise HTTPException(status_code=400, detail="No installment is currently awaiting admin unlock")

    await pre_assessments_col.update_one({"id": pa_id}, {"$set": {
        "installment_forwarded_by": current_user["id"],
        "installment_forwarded_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }})

    admins = await users_col.find({"role": "admin", "status": "active"}, {"_id": 0, "id": 1}).to_list(50)
    for admin in admins:
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()), "user_id": admin["id"],
            "title": "Installment payment — unlock next?",
            "message": f"{pa['client_name']}'s installment payment was reviewed by {current_user.get('name','')}. Approve to unlock next installment.",
            "type": "installment_unlock_pending", "read": False,
            "link": "/admin/pre-assessments",
            "created_at": datetime.now(timezone.utc)
        })

    await log_activity(current_user["id"], current_user.get("name", ""), "forward_installment_review",
                    "pre_assessment", pa_id, f"Installment reviewed and forwarded to admin for {pa['client_name']}")
    return {"ok": True, "message": "Forwarded to admin"}

# ─── Admin: unlock the next installment for the client ──────────────────────
@router.post("/{pa_id}/unlock-next-installment")
async def unlock_next_installment(pa_id: str, current_user: dict = Depends(get_current_user)):
    """Admin approves and unlocks the next locked payment part so the client can pay it."""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Pre-assessment not found")

    parts = pa.get("proposal_payment_parts") or []
    next_locked = next((p for p in parts if p.get("status") == "locked"), None)
    if not next_locked:
        raise HTTPException(status_code=400, detail="No locked installment to unlock")

    for p in parts:
        if p["index"] == next_locked["index"]:
            p["status"] = "pending"

    await pre_assessments_col.update_one({"id": pa_id}, {"$set": {
        "proposal_payment_parts": parts,
        "pending_installment_unlock": False,
        "installment_unlocked_by": current_user["id"],
        "installment_unlocked_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }})

    if pa.get("client_user_id"):
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()), "user_id": pa["client_user_id"],
            "title": "Next installment unlocked",
            "message": f"{next_locked['label']} (₹{next_locked['amount']:,.0f}) is now ready — you can pay it in your portal.",
            "type": "installment_unlocked", "read": False,
            "created_at": datetime.now(timezone.utc)
        })
    if pa.get("partner_id"):
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()), "user_id": pa["partner_id"],
            "title": "Installment unlocked by admin",
            "message": f"{next_locked['label']} unlocked for {pa['client_name']}.",
            "type": "installment_unlocked", "read": False,
            "created_at": datetime.now(timezone.utc)
        })

    await log_activity(current_user["id"], current_user.get("name", ""), "unlock_next_installment",
                    "pre_assessment", pa_id, f"Unlocked {next_locked['label']} for {pa['client_name']}")
    return {"ok": True, "unlocked_part": next_locked["label"]}

# ═══════════════════════════════════════════════════════════════════════
# PATCH FOR: pre_assessment.py
# GOAL: When admin approves the 1st installment (forwarded by partner),
#       activate the Case + assign a Case Manager RIGHT THEN — instead of
#       waiting for the client to pay 100% of the fee.
#
# WHERE TO ADD:
#   Add this AFTER the existing `unlock_next_installment` endpoint in
#   pre_assessment.py (you can keep the old endpoint too, for pure
#   "unlock without activating" cases if you ever need it — but the
#   Forward-to-Admin banner in the frontend should now call THIS one).
# ═══════════════════════════════════════════════════════════════════════

from pydantic import BaseModel
from typing import Optional

class ApproveInstallmentActivateRequest(BaseModel):
    case_manager_id: Optional[str] = None  # optional — admin can assign later too
    spouse_case_manager_id: Optional[str] = None 

@router.post("/{pa_id}/approve-installment-and-activate-case")
async def approve_installment_and_activate_case(
    pa_id: str,
    data: Optional[ApproveInstallmentActivateRequest] = None,
    current_user: dict = Depends(get_current_user),
):
    """Admin approves a partner-forwarded installment payment.
    Does TWO/THREE things in one shot:
    1. Unlocks the next payment part (so client can pay installment #2 later)
    2. Activates the main applicant's Case + (optionally) assigns a Case Manager
    3. If this PA has spouse_info, creates a SEPARATE case + own login for the
        spouse/partner too — with its own optional Case Manager assignment.

    Safe to call more than once — if the main case already exists it is skipped,
    and if the spouse case already exists it is skipped too (idempotent).
    """
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Pre-assessment not found")

    if not pa.get("pending_installment_unlock"):
        raise HTTPException(status_code=400, detail="No installment is currently awaiting admin approval")

    now = datetime.now(timezone.utc)

    # ── Step 1: Unlock the next locked payment part ────────────────────────
    parts = pa.get("proposal_payment_parts") or []
    next_locked = next((p for p in parts if p.get("status") == "locked"), None)
    if next_locked:
        for p in parts:
            if p["index"] == next_locked["index"]:
                p["status"] = "pending"

    update_fields = {
        "proposal_payment_parts": parts,
        "pending_installment_unlock": False,
        "installment_unlocked_by": current_user["id"],
        "installment_unlocked_at": now,
        "updated_at": now,
    }

    # ── Step 2: Activate the main applicant's Case (only if not already created) ──
    case_id = pa.get("case_id")
    case_code = None
    cm_id = (data.case_manager_id if data else None)
    cm_name = "Pending assignment"

    if not case_id:
        cases_col = db["cases"]
        case_steps_col = db["case_steps"]
        workflow_steps_col = db["workflow_steps"]

        count = await cases_col.count_documents({})
        case_code = f"LEAMSS-{now.year}-{(count + 1):04d}"

        client_user = await users_col.find_one(
            {"$or": [{"id": pa.get("client_user_id")}, {"email": (pa.get("client_email") or "").lower()}]},
            {"_id": 0}
        )
        client_id = client_user["id"] if client_user else pa.get("client_user_id")

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
            "occupation_code": pa.get("occupation_code") or pa.get("suggested_occupation_code") or "",
            "occupation_title": pa.get("occupation_title") or pa.get("suggested_occupation_title") or "",
            "assessing_authority_code": pa.get("assessing_authority_code") or pa.get("suggested_assessing_authority_code") or "",
            "country": pa.get("country") or "AU",
            "service_type": pa.get("service_type") or "PR",
            "client_occupation_review_status": "pending_client_review",
            "created_at": now,
            "updated_at": now,
        }
        await cases_col.insert_one(case)

        if pa.get("product_id"):
            steps = await workflow_steps_col.find(
                {"product_id": pa["product_id"]}, {"_id": 0}
            ).sort("step_order", 1).to_list(100)
            for step in steps:
                cs = {
                    "id": str(uuid.uuid4()),
                    "case_id": case_id,
                    "step_name": step.get("step_name"),
                    "step_order": step.get("step_order"),
                    "status": "pending",
                    "description": step.get("description", ""),
                    "required_documents": step.get("required_documents", []),
                    "created_at": now,
                }
                await case_steps_col.insert_one(cs)

        update_fields.update({
            "case_id": case_id,
            "case_activated_early": True,
            "case_activated_at": now,
            "final_approved_by": current_user["id"],
            "final_approved_at": now,
        })

        if client_id:
            await notifications_col.insert_one({
                "id": str(uuid.uuid4()), "user_id": client_id,
                "title": f"Case activated: {case_code}",
                "message": "Your case is now live! Remaining installment(s) can still be paid from your portal.",
                "type": "case_created", "read": False,
                "related_id": pa_id, "link": "/client",
                "created_at": now,
            })
        if pa.get("partner_id"):
            await notifications_col.insert_one({
                "id": str(uuid.uuid4()), "user_id": pa["partner_id"],
                "title": f"Case created: {case_code}",
                "message": f"Case for {pa.get('client_name')} is now active (1st installment approved).",
                "type": "case_created", "read": False,
                "related_id": pa_id,
                "created_at": now,
            })
        if cm_id:
            await notifications_col.insert_one({
                "id": str(uuid.uuid4()), "user_id": cm_id,
                "title": f"New case assigned: {case_code}",
                "message": f"{pa.get('client_name')} - {pa.get('country')} {pa.get('service_type')} (2nd installment pending)",
                "type": "case_assigned", "read": False,
                "link": f"/cm?case={case_id}",
                "created_at": now,
            })

    # ── Step 3: Spouse/partner gets a SEPARATE case + own login (idempotent) ──
    spouse_case_id = pa.get("spouse_case_id")
    spouse_case_code = None
    spouse_info = pa.get("spouse_info")

    if spouse_info and spouse_info.get("email") and not spouse_case_id:
        from routers.pre_assess_portal import _create_spouse_case
        # _create_spouse_case needs pa["case_id"] to set linked_case_id — make sure
        # it has the just-created (or pre-existing) case_id available.
        pa_for_spouse = {**pa, "case_id": case_id}
        spouse_case_id, spouse_case_code = await _create_spouse_case(
            pa_for_spouse,
            data.spouse_case_manager_id if data else None,
        )
        if spouse_case_id:
            update_fields["spouse_case_id"] = spouse_case_id

    await pre_assessments_col.update_one({"id": pa_id}, {"$set": update_fields})

    await log_activity(
        current_user["id"], current_user.get("name", ""), "approve_installment_activate_case",
        "pre_assessment", pa_id,
        f"Installment approved + case {'created' if case_code else 'already existed'} for {pa['client_name']}"
        + (f" | spouse case {spouse_case_code}" if spouse_case_code else "")
    )

    return {
        "ok": True,
        "unlocked_part": next_locked["label"] if next_locked else None,
        "case_id": case_id,
        "case_code": case_code,
        "case_manager_id": cm_id,
        "case_manager_name": cm_name,
        "spouse_case_id": spouse_case_id,
        "spouse_case_code": spouse_case_code,
    }
# ===================== SHARED ENDPOINTS =====================

@router.get("/my-assessments")
async def get_my_assessments(
    stage: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """Partner gets all their pre-assessments. Admin sees all. Optional ?stage= filter."""
    is_admin = current_user.get("role") in ("admin", "admin_owner") or current_user.get("rbac_role") in ("admin", "admin_owner")
    query = {} if is_admin else {"$or": [{"partner_id": current_user["id"]}, {"created_by_user_id": current_user["id"]}]}
    
    if stage:
        if stage == "case_created":
            stage_cond = {
                "$or": [
                    {"stage": "case_created"},
                    {"case_id": {"$exists": True, "$ne": None}},
                    {"case_manager_id": {"$exists": True, "$ne": None}},
                ]
            }
            if query:
                query = {"$and": [query, stage_cond]}
            else:
                query = stage_cond
        else:
            if query:
                query["stage"] = stage
            else:
                query = {"stage": stage}

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

@router.get("/admin/standard-approvals")
async def standard_approvals(current_user: dict = Depends(get_current_user)):
    """Standard Sale Approval Queue"""

    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    query = {
        "stage": {
            "$in": [
                "documents_submitted",
                "under_review"
            ]
        },
        "$or": [
            {"sale_type": "standard"},
            {"sale_type": {"$exists": False}},
            {"sale_type": None}
        ]
    }

    items = await pre_assessments_col.find(
        query,
        {"_id": 0}
    ).sort("submitted_at", -1).to_list(200)

    for item in items:

        docs = await pre_assessment_docs_col.find(
            {"pre_assessment_id": item["id"]},
            {"_id": 0}
        ).to_list(50)

        item["documents"] = docs

        for field in [
            "created_at",
            "updated_at",
            "submitted_at",
            "admin_reviewed_at",
        ]:
            if item.get(field) and hasattr(item[field], "isoformat"):
                item[field] = item[field].isoformat()

        for d in docs:
            if d.get("created_at") and hasattr(d["created_at"], "isoformat"):
                d["created_at"] = d["created_at"].isoformat()

    return {
        "items": items,
        "count": len(items)
    }

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
        step1_amount = float(pa.get("fee_amount_paid") or pa.get("pre_assessment_fee") or 5100)
        step1_label = "Pre-Assessment Fee Paid"
        step1_meta = {"reference": pa.get("pa_number")}
        if pa.get("fee_gst_included"):
            step1_label = "Pre-Assessment Fee Paid (incl. 18% GST)"
            step1_meta["base_amount"] = float(pa.get("fee_base_amount") or 5100)
            step1_meta["gst_amount"] = float(pa.get("fee_gst_amount") or 0)
        events.append({"ts": pa.get("updated_at"), "kind": "pre_assessment_fee",
                        "label": step1_label, "amount": step1_amount,
                        "direction": "in", "meta": step1_meta})
    if pa.get("proposal_status") in ("sent", "pending_installment_approval"):
        events.append({"ts": pa.get("updated_at"), "kind": "proposal_sent",
                        "label": "Proposal Sent to Client", "amount": float(pa.get("proposal_fee") or 0),
                        "direction": "pending", "meta": {"promo_code": pa.get("proposal_promo_code")}})

    #  NEW — Installment / part payments (client paid 1 or more parts but not full amount yet)
    parts = pa.get("proposal_payment_parts") or []
    for p in parts:
        if p.get("status") == "paid" and p.get("paid_at"):
            events.append({
                "ts": p.get("paid_at"),
                "kind": "installment_paid",
                "label": f"{p.get('label', 'Installment')} Paid",
                "amount": float(p.get("amount") or 0),
                "direction": "in",
                "meta": {"reference": p.get("payment_ref"), "part_index": p.get("index")},
            })

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

    # FIX — totals should reflect actual amount_paid/pending on the proposal
    # (not just static proposal_fee), so partial installments show correctly.
    if pa.get("proposal_status") in ("sent", "pending_installment_approval") and parts:
        proposal_received = float(pa.get("proposal_amount_paid") or 0)
        proposal_pending = float(pa.get("proposal_amount_pending") or pa.get("proposal_fee") or 0)
    else:
        proposal_received = sum(e["amount"] for e in events if e["direction"] == "in" and e["kind"] in ("main_fee_paid", "installment_paid"))
        proposal_pending = sum(e["amount"] for e in events if e["direction"] == "pending")

    totals = {
        "received": (sum(e["amount"] for e in events if e["direction"] == "in" and e["kind"] not in ("main_fee_paid", "installment_paid"))
                    + proposal_received),
        "pending": proposal_pending,
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

