"""Pre-Assessment Workflow Router
Flow: Partner creates → Sends ₹5,100 payment to client → Client pays → 
Partner submits docs to Admin → Admin approves/rejects → 
If approved: Partner sends sales proposal with payment link → Client pays → Case starts
If rejected: ₹5,100 refunded
"""
import os
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Request, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, List
from core.database import db
from routers.auth import get_current_user
from core.services import log_activity

router = APIRouter(prefix="/pre-assessment", tags=["Pre-Assessment"])

pre_assessments_col = db["pre_assessments"]
pre_assessment_docs_col = db["pre_assessment_documents"]
payment_transactions_col = db["payment_transactions"]
notifications_col = db["notifications"]
users_col = db["users"]
products_col = db["products"]
sales_col = db["sales"]

PRE_ASSESSMENT_FEE = 5100  # INR
STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY")

STAGES = [
    "new",                    # Partner just created lead
    "payment_pending",        # Payment link sent to client
    "payment_received",       # Client paid ₹5,100
    "documents_submitted",    # Partner submitted docs to admin
    "under_review",           # Admin is reviewing
    "approved",               # Admin approved → Partner can send proposal
    "rejected",               # Admin rejected → Refund initiated
    "proposal_sent",          # Partner sent sales proposal to client
    "proposal_paid",          # Client paid service fee
    "case_created",           # Case auto-created, process started
    "refund_initiated",       # Refund in progress
    "refunded",               # Refund completed
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
    """Partner creates a new pre-assessment for a potential client"""
    if current_user["role"] not in ["partner", "admin"]:
        raise HTTPException(status_code=403, detail="Only partners can create pre-assessments")

    pa_id = str(uuid.uuid4())
    pa_number = f"PA-{datetime.now().strftime('%Y%m%d')}-{pa_id[:6].upper()}"

    product_name = ""
    if data.product_id:
        product = await products_col.find_one({"id": data.product_id}, {"_id": 0, "name": 1})
        if product:
            product_name = product.get("name", "")

    pre_assessment = {
        "id": pa_id,
        "pa_number": pa_number,
        "partner_id": current_user["id"],
        "partner_name": current_user.get("name", ""),
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
        "stage": "new",
        "pre_assessment_fee": PRE_ASSESSMENT_FEE,
        "fee_payment_status": "unpaid",
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
    }
    await pre_assessments_col.insert_one(pre_assessment)
    pre_assessment.pop("_id", None)

    await log_activity(current_user["id"], current_user.get("name", ""), "create_pre_assessment",
                       "pre_assessment", pa_id, f"Pre-assessment created for {data.client_name} - {data.country} {data.service_type}")

    # Notify admins
    admins = await users_col.find({"role": "admin", "status": "active"}, {"_id": 0, "id": 1}).to_list(50)
    for admin in admins:
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()), "user_id": admin["id"],
            "title": "New Pre-Assessment Created",
            "message": f"{current_user.get('name', '')} created pre-assessment for {data.client_name}",
            "type": "pre_assessment", "read": False,
            "link": f"/admin/pre-assessments",
            "created_at": datetime.now(timezone.utc)
        })

    return {"id": pa_id, "pa_number": pa_number, "message": "Pre-assessment created successfully"}


@router.post("/{pa_id}/send-payment-link")
async def send_payment_link(pa_id: str, http_request: Request, current_user: dict = Depends(get_current_user)):
    """Partner sends ₹5,100 pre-assessment payment link to client"""
    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Pre-assessment not found")

    if pa["partner_id"] != current_user["id"] and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    if pa["stage"] not in ["new", "payment_pending"]:
        raise HTTPException(status_code=400, detail=f"Cannot send payment link at stage: {pa['stage']}")

    if not STRIPE_API_KEY:
        # Mock mode — simulate payment link
        mock_link = f"{str(http_request.base_url)}api/pre-assessment/{pa_id}/mock-payment"
        await pre_assessments_col.update_one({"id": pa_id}, {"$set": {
            "stage": "payment_pending", "updated_at": datetime.now(timezone.utc)
        }})
        await log_activity(current_user["id"], current_user.get("name", ""), "send_payment_link",
                           "pre_assessment", pa_id, f"Payment link sent to {pa['client_name']} (₹{PRE_ASSESSMENT_FEE})")
        return {"message": f"Payment link sent to {pa['client_email']}", "payment_url": mock_link, "mode": "mock"}

    from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionRequest

    origin = str(http_request.headers.get("origin", http_request.base_url)).rstrip("/")
    success_url = f"{origin}/payment-success?session_id={{CHECKOUT_SESSION_ID}}&type=pre_assessment&pa_id={pa_id}"
    cancel_url = f"{origin}/payment-cancel?type=pre_assessment&pa_id={pa_id}"

    host_url = str(http_request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)

    checkout_request = CheckoutSessionRequest(
        amount=float(PRE_ASSESSMENT_FEE),
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
        "amount": float(PRE_ASSESSMENT_FEE), "currency": "inr",
        "status": "initiated", "payment_status": "pending",
        "created_at": datetime.now(timezone.utc)
    })

    await pre_assessments_col.update_one({"id": pa_id}, {"$set": {
        "stage": "payment_pending", "fee_session_id": session.session_id,
        "updated_at": datetime.now(timezone.utc)
    }})

    await log_activity(current_user["id"], current_user.get("name", ""), "send_payment_link",
                       "pre_assessment", pa_id, f"₹{PRE_ASSESSMENT_FEE} payment link sent to {pa['client_name']}")

    return {"message": f"Payment link sent to {pa['client_email']}", "payment_url": session.url, "session_id": session.session_id}


@router.post("/{pa_id}/mock-payment")
async def mock_payment_received(pa_id: str):
    """Mock endpoint to simulate payment (for testing without Stripe)"""
    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Pre-assessment not found")

    await pre_assessments_col.update_one({"id": pa_id}, {"$set": {
        "stage": "payment_received", "fee_payment_status": "paid",
        "updated_at": datetime.now(timezone.utc)
    }})

    # Notify partner
    await notifications_col.insert_one({
        "id": str(uuid.uuid4()), "user_id": pa["partner_id"],
        "title": "Payment Received!", "type": "payment",
        "message": f"₹{PRE_ASSESSMENT_FEE} received from {pa['client_name']}. Submit documents for admin review.",
        "read": False, "created_at": datetime.now(timezone.utc)
    })

    return {"message": "Payment received (mock). Submit documents to proceed."}


@router.post("/{pa_id}/confirm-payment")
async def confirm_payment(pa_id: str, current_user: dict = Depends(get_current_user)):
    """Confirm payment was received (for Stripe webhook or manual confirmation)"""
    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Pre-assessment not found")

    await pre_assessments_col.update_one({"id": pa_id}, {"$set": {
        "stage": "payment_received", "fee_payment_status": "paid",
        "updated_at": datetime.now(timezone.utc)
    }})

    await log_activity(current_user["id"], current_user.get("name", ""), "confirm_pa_payment",
                       "pre_assessment", pa_id, f"₹{PRE_ASSESSMENT_FEE} payment confirmed for {pa['client_name']}")

    return {"message": "Payment confirmed"}


@router.post("/{pa_id}/submit-documents")
async def submit_to_admin(pa_id: str, remarks: str = Form(""), current_user: dict = Depends(get_current_user)):
    """Partner submits pre-assessment with documents for admin review"""
    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Pre-assessment not found")

    if pa["partner_id"] != current_user["id"] and current_user["role"] != "admin":
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
    if role == "partner" and pa.get("partner_id") != current_user["id"]:
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
    if role == "partner" and pa["partner_id"] != current_user["id"]:
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
async def get_my_assessments(current_user: dict = Depends(get_current_user)):
    """Partner gets all their pre-assessments"""
    query = {"partner_id": current_user["id"]}
    if current_user["role"] == "admin":
        query = {}  # Admin sees all

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
    """Get single pre-assessment details"""
    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Pre-assessment not found")

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
    if current_user["role"] == "partner":
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
    if role == "partner" and pa.get("partner_id") != current_user["id"]:
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
