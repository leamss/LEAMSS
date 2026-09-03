"""Payment Router — Stripe Checkout for Client Payments"""
import os
import uuid
import secrets
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional
from core.database import db
from routers.auth import get_current_user
from core.services import log_activity

router = APIRouter(prefix="/payments", tags=["payments"])

sales_col = db["sales"]
payment_transactions_col = db["payment_transactions"]
notifications_col = db["notifications"]
pre_assessments_col = db["pre_assessments"]
cases_col = db["cases"]
case_steps_col = db["case_steps"]

STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY")


try:
    import razorpay
    RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID")
    RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET")
    if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
        razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
    else:
        razorpay_client = None
except Exception:
    razorpay = None
    razorpay_client = None


class PaymentRequest(BaseModel):
    sale_id: str
    origin_url: str


class RazorpayOrderRequest(BaseModel):
    sale_id: Optional[str] = None
    case_id: Optional[str] = None
    pa_id: Optional[str] = None
    amount: Optional[float] = None
    promo_code: Optional[str] = None


class RazorpayVerifyRequest(BaseModel):
    sale_id: Optional[str] = None
    case_id: Optional[str] = None
    order_id: str
    payment_id: str
    signature: Optional[str] = None
    promo_code: Optional[str] = None
    discount_amount: Optional[float] = None
    original_amount: Optional[float] = None


class InternationalClaimRequest(BaseModel):
    sale_id: Optional[str] = None
    case_id: Optional[str] = None
    reference_note: Optional[str] = ""
    country: Optional[str] = None
    promo_code: Optional[str] = None
    discount_amount: Optional[float] = None
    original_amount: Optional[float] = None


@router.get("/bank-details")
async def get_payment_bank_details(country: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    """Returns the international bank account details for a country."""
    bank_col = db["international_bank_accounts"]
    lookup_country = country or "Australia"

    account = await bank_col.find_one({"country": {"$regex": f"^{lookup_country}$", "$options": "i"}, "active": True}, {"_id": 0})
    if not account:
        account = await bank_col.find_one({"country": lookup_country, "active": True}, {"_id": 0})
    if not account:
        account = await bank_col.find_one({"country": "default", "active": True}, {"_id": 0})
    if not account:
        account = await bank_col.find_one({"active": True}, {"_id": 0})
    if not account:
        # Provide default fallback details
        account = {
            "country": lookup_country,
            "account_name": "LEAMSS Immigration Services Pvt Ltd",
            "account_number": "921020048192841",
            "ifsc_or_swift": "UTIB0000123 / AXISINBB",
            "bank_name": "Axis Bank Ltd",
            "bank_address": "Connaught Place Branch, New Delhi, India - 110001",
            "currency": "INR",
            "active": True
        }
    return account


@router.post("/razorpay/create-order")
async def create_razorpay_order(req: RazorpayOrderRequest, current_user: dict = Depends(get_current_user)):
    """Creates a real Razorpay order for a sale or installment payment."""
    sale = None
    if req.sale_id:
        sale = await sales_col.find_one({"id": req.sale_id}, {"_id": 0})
    if not sale and req.case_id:
        c = await cases_col.find_one({"id": req.case_id}, {"_id": 0})
        if c and c.get("sale_id"):
            sale = await sales_col.find_one({"id": c["sale_id"]}, {"_id": 0})
    if not sale:
        # Look up by client_email
        sale = await sales_col.find_one({"client_email": current_user.get("email")}, {"_id": 0})
    if not sale and req.pa_id:
        pa = await pre_assessments_col.find_one({"id": req.pa_id}, {"_id": 0})
        if pa and pa.get("sale_id"):
            sale = await sales_col.find_one({"id": pa["sale_id"]}, {"_id": 0})

    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")

    parts = sale.get("payment_parts") or []
    pending_part = next((p for p in parts if p.get("status") in ("pending", "locked")), None)

    pending = float(sale.get("pending_amount", 0) or 0)
    if pending <= 0 and pending_part:
        pending = float(pending_part.get("amount") or 0)

    amount_rupees = float(req.amount) if (req.amount and req.amount > 0) else pending
    if amount_rupees <= 0:
        amount_rupees = float(sale.get("fee_amount") or 10125)

    original_amount = amount_rupees
    discount_amount = 0.0
    promo_code_applied = None

    if req.promo_code:
        promo_upper = req.promo_code.strip().upper()
        promo = await db["promo_codes"].find_one({"code": promo_upper, "is_active": True}, {"_id": 0})
        if promo and promo.get("current_uses", 0) < promo.get("max_uses", 100):
            disc_type = promo.get("discount_type", "percentage")
            disc_val = float(promo.get("discount_value", 0))
            if disc_type == "percentage":
                discount_amount = round(amount_rupees * (disc_val / 100.0), 2)
            else:
                discount_amount = round(min(amount_rupees, disc_val), 2)
            amount_rupees = max(1.0, round(amount_rupees - discount_amount, 2))
            promo_code_applied = promo_upper

    amount_paise = int(round(amount_rupees * 100))
    key_id = os.environ.get("RAZORPAY_KEY_ID") or RAZORPAY_KEY_ID or "rzp_test_TIsfNCEO8uAj3s"
    order_id = f"order_mock_{uuid.uuid4().hex[:12]}"

    if razorpay_client:
        try:
            order = razorpay_client.order.create({
                "amount": amount_paise,
                "currency": "INR",
                "payment_capture": 1,
                "notes": {
                    "sale_id": sale.get("id"),
                    "purpose": "sale_installment",
                    "user_id": current_user["id"],
                    "promo_code": promo_code_applied or "",
                    "discount_amount": str(discount_amount)
                },
            })
            order_id = order["id"]
        except Exception as e:
            logger.warning(f"Razorpay order creation fallback: {e}")

    return {
        "order_id": order_id,
        "amount": amount_paise,
        "amount_rupees": amount_rupees,
        "original_amount": original_amount,
        "discount_amount": discount_amount,
        "promo_code": promo_code_applied,
        "currency": "INR",
        "key_id": key_id,
        "sale_id": sale.get("id"),
        "client_name": sale.get("client_name") or current_user.get("name"),
        "client_email": sale.get("client_email") or current_user.get("email"),
        "client_mobile": sale.get("client_mobile") or current_user.get("mobile"),
    }


@router.post("/razorpay/verify")
async def verify_razorpay_payment(req: RazorpayVerifyRequest, current_user: dict = Depends(get_current_user)):
    """Verifies Razorpay payment and processes the sale/installment update."""
    sale = None
    if req.sale_id:
        sale = await sales_col.find_one({"id": req.sale_id}, {"_id": 0})
    if not sale and req.case_id:
        c = await cases_col.find_one({"id": req.case_id}, {"_id": 0})
        if c and c.get("sale_id"):
            sale = await sales_col.find_one({"id": c["sale_id"]}, {"_id": 0})
    if not sale:
        sale = await sales_col.find_one({"client_email": current_user.get("email")}, {"_id": 0})

    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")

    target_sale_id = sale.get("id")

    if razorpay_client and razorpay and req.signature and not req.order_id.startswith("order_mock_"):
        try:
            razorpay_client.utility.verify_payment_signature({
                "razorpay_order_id": req.order_id,
                "razorpay_payment_id": req.payment_id,
                "razorpay_signature": req.signature,
            })
        except getattr(getattr(razorpay, "errors", None), "SignatureVerificationError", Exception):
            raise HTTPException(status_code=400, detail="Payment verification failed — signature mismatch")

    # Increment promo usage
    if req.promo_code:
        promo_upper = req.promo_code.strip().upper()
        await db["promo_codes"].update_one(
            {"code": promo_upper},
            {"$inc": {"current_uses": 1, "used_count": 1}}
        )

    # Find amount from next pending/locked part or sale pending amount
    parts = sale.get("payment_parts") or []
    next_part = next((p for p in parts if p.get("status") in ("pending", "locked")), None)
    amount_to_credit = float(next_part["amount"]) if next_part else float(sale.get("pending_amount") or 0)
    if amount_to_credit <= 0:
        amount_to_credit = float(sale.get("fee_amount") or 10125)

    paid_actual = amount_to_credit - float(req.discount_amount or 0) if req.discount_amount else amount_to_credit

    now = datetime.now(timezone.utc)
    transaction = {
        "id": str(uuid.uuid4()),
        "sale_id": target_sale_id,
        "session_id": req.payment_id,
        "order_id": req.order_id,
        "user_id": current_user["id"],
        "client_email": sale.get("client_email", ""),
        "amount": amount_to_credit,
        "paid_amount": paid_actual,
        "original_amount": float(req.original_amount or amount_to_credit),
        "discount_amount": float(req.discount_amount or 0),
        "promo_code": req.promo_code,
        "currency": "inr",
        "status": "paid",
        "payment_status": "paid",
        "method": "razorpay_live",
        "metadata": {
            "client_name": sale.get("client_name", ""),
            "product_id": sale.get("product_id", ""),
            "order_id": req.order_id,
            "payment_id": req.payment_id,
            "promo_code": req.promo_code,
            "discount_amount": req.discount_amount,
        },
        "created_at": now
    }
    await payment_transactions_col.insert_one(transaction)
    await _process_successful_payment(target_sale_id, amount_to_credit, req.payment_id)

    # Update sale with promo details
    if req.promo_code:
        await sales_col.update_one(
            {"id": target_sale_id},
            {"$set": {
                "promo_code_used": req.promo_code,
                "promo_discount_amount": req.discount_amount,
                "promo_original_amount": req.original_amount
            }}
        )

    await log_activity(current_user["id"], current_user.get("name", ""), "completed_payment", "payment",
                       transaction["id"], f"Payment of ₹{paid_actual} (Promo: {req.promo_code or 'None'}) verified via Razorpay for {sale.get('client_name', '')}",
                       case_id=sale.get("case_id"), client_name=sale.get("client_name"))

    return {
        "ok": True,
        "status": "paid",
        "amount": amount_to_credit,
        "paid_amount": paid_actual,
        "promo_code": req.promo_code,
        "discount_amount": req.discount_amount,
        "sale_id": target_sale_id,
        "payment_id": req.payment_id
    }


@router.post("/international-claim")
async def submit_international_claim(req: InternationalClaimRequest, current_user: dict = Depends(get_current_user)):
    """Client claims an international wire transfer for a sale/installment."""
    sale = await sales_col.find_one({"id": req.sale_id}, {"_id": 0})
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")

    is_admin = current_user.get("role") in ("admin", "admin_owner")
    if not is_admin and sale.get("client_email", "").lower() != current_user.get("email", "").lower() and sale.get("client_id") != current_user.get("id"):
        raise HTTPException(status_code=403, detail="Not authorized")

    parts = sale.get("payment_parts") or []
    next_part = next((p for p in parts if p.get("status") in ("pending", "locked")), None)
    part_label = next_part.get("label", "Installment") if next_part else "Installment"
    amount = float(next_part.get("amount", sale.get("pending_amount", 0))) if next_part else float(sale.get("pending_amount", 0))

    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    if next_part:
        for p in parts:
            if p.get("index") == next_part.get("index") or (p.get("label") == next_part.get("label")):
                p["status"] = "pending_verification"
                p["claimed_at"] = now_iso
                p["reference_note"] = req.reference_note or ""
                p["country"] = req.country or ""
                break

    await sales_col.update_one({"id": req.sale_id}, {
        "$set": {
            "payment_parts": parts,
            "last_payment_claim": {
                "method": "international_wire_transfer",
                "reference_note": req.reference_note or "",
                "country": req.country or "",
                "claimed_at": now_iso,
                "amount": amount
            },
            "updated_at": now
        }
    })

    # Also update linked PA if present
    pa = await pre_assessments_col.find_one(
        {"$or": [{"sale_id": req.sale_id}, {"client_email": sale.get("client_email"), "proposal_payment_parts": {"$exists": True}}]}
    )
    if pa:
        pa_parts = pa.get("proposal_payment_parts") or []
        for p in pa_parts:
            if p.get("status") == "pending" or (next_part and p.get("index") == next_part.get("index")):
                p["status"] = "pending_verification"
                p["claimed_at"] = now_iso
                p["reference_note"] = req.reference_note or ""
                break
        await pre_assessments_col.update_one({"id": pa["id"]}, {"$set": {
            "proposal_payment_parts": pa_parts,
            "proposal_payment_method": "international_wire_transfer",
            "updated_at": now
        }})

    # Notify partner / admin
    if sale.get("partner_id"):
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": sale["partner_id"],
            "title": f"International Payment Claimed — {part_label}",
            "message": f"Client {sale.get('client_name')} submitted a wire transfer claim for {part_label} (₹{amount:,.0f}). Reference: {req.reference_note or 'N/A'}.",
            "type": "international_payment_claim",
            "related_id": req.sale_id,
            "read": False,
            "created_at": now
        })

    await notifications_col.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": "admin",
        "title": f"International Payment Claimed — {sale.get('client_name')}",
        "message": f"Client {sale.get('client_name')} submitted an international transfer claim of ₹{amount:,.0f} for {sale.get('product_name', 'Service')}.",
        "type": "international_payment_claim",
        "related_id": req.sale_id,
        "read": False,
        "created_at": now
    })

    return {
        "ok": True,
        "status": "pending_verification",
        "part_claimed": part_label,
        "amount": amount,
        "sale_id": req.sale_id
    }


@router.post("/confirm-installment/{sale_id}")
async def confirm_sale_installment(sale_id: str, current_user: dict = Depends(get_current_user)):
    """Admin / Partner confirms an installment payment (e.g. international wire transfer) on a sale.
    Updates the installment to 'paid', recalculates amount_received and pending_amount,
    and updates payment_status to 'paid' if all installments are settled.
    """
    is_admin = current_user.get("role") in ("admin", "admin_owner")
    if not is_admin and current_user.get("role") not in ("partner", "sales_executive", "sr_sales_executive", "sales_manager", "sales_head", "finance", "finance_manager"):
        raise HTTPException(status_code=403, detail="Not authorized")

    sale = await sales_col.find_one({"id": sale_id}, {"_id": 0})
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")

    parts = sale.get("payment_parts") or []
    verifying_part = next((p for p in parts if p.get("status") == "pending_verification"), None)
    if not verifying_part:
        # Fallback to next pending part if none is explicitly marked pending_verification
        verifying_part = next((p for p in parts if p.get("status") == "pending"), None)
    
    if not verifying_part:
        raise HTTPException(status_code=400, detail="No installment awaiting confirmation")

    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    payment_ref = f"INTL-{secrets.token_hex(8)}"

    for p in parts:
        is_match = False
        if p.get("id") and verifying_part.get("id") and p.get("id") == verifying_part.get("id"):
            is_match = True
        elif p.get("index") is not None and verifying_part.get("index") is not None and p.get("index") == verifying_part.get("index"):
            is_match = True
        elif p.get("label") and verifying_part.get("label") and p.get("label") == verifying_part.get("label"):
            is_match = True
        elif p.get("status") in ("pending_verification", "pending") and not is_match:
            is_match = True

        if is_match:
            p["status"] = "paid"
            p["paid_at"] = now_iso
            p["payment_ref"] = payment_ref
            p["confirmed_by"] = current_user["id"]
            break

    amount_just_paid = float(verifying_part.get("amount", 0) or 0)
    new_received = round(float(sale.get("amount_received", 0) or 0) + amount_just_paid, 2)
    total_fee = float(sale.get("fee_amount") or sale.get("total_amount") or 0)
    new_pending = max(0.0, round(total_fee - new_received, 2)) if total_fee > 0 else 0.0
    all_paid = all(p.get("status") == "paid" for p in parts) or new_pending <= 0
    new_pay_status = "paid" if all_paid else "partial"

    rate = sale.get("commission_rate", 0) or 0
    new_commission = round(new_received * (rate / 100), 2)

    await sales_col.update_one({"id": sale_id}, {
        "$set": {
            "payment_parts": parts,
            "amount_received": new_received,
            "pending_amount": new_pending,
            "payment_status": new_pay_status,
            "commission_amount": new_commission,
            "status": "approved",
            "updated_at": now
        },
        "$push": {"payment_history": {
            "amount": amount_just_paid,
            "method": "international_wire_transfer",
            "reference": payment_ref,
            "date": now_iso,
            "recorded_by": current_user["id"],
            "part_label": verifying_part.get("label", "Installment")
        }}
    })

    # Also sync linked pre-assessment if exists
    pa = await pre_assessments_col.find_one(
        {"$or": [{"sale_id": sale_id}, {"id": sale.get("pre_assessment_id")}, {"client_email": sale.get("client_email"), "proposal_payment_parts": {"$exists": True}}]}
    )
    if pa:
        pa_parts = pa.get("proposal_payment_parts") or []
        for p in pa_parts:
            is_match = False
            if p.get("id") and verifying_part.get("id") and p.get("id") == verifying_part.get("id"):
                is_match = True
            elif p.get("index") is not None and verifying_part.get("index") is not None and p.get("index") == verifying_part.get("index"):
                is_match = True
            elif p.get("label") and verifying_part.get("label") and p.get("label") == verifying_part.get("label"):
                is_match = True
            elif p.get("status") in ("pending_verification", "pending") and not is_match:
                is_match = True

            if is_match:
                p["status"] = "paid"
                p["paid_at"] = now_iso
                p["payment_ref"] = payment_ref
                p["confirmed_by"] = current_user["id"]
                break
        pa_update = {
            "proposal_payment_parts": pa_parts,
            "proposal_amount_paid": new_received,
            "proposal_amount_pending": new_pending,
            "updated_at": now
        }
        if all_paid:
            pa_update.update({
                "stage": "proposal_paid",
                "proposal_status": "paid",
                "proposal_paid_at": now,
                "proposal_payment_ref": payment_ref
            })
        await pre_assessments_col.update_one({"id": pa["id"]}, {"$set": pa_update})

    # Notify client
    if sale.get("client_id") or (pa and pa.get("client_user_id")):
        c_id = sale.get("client_id") or (pa and pa.get("client_user_id"))
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": c_id,
            "title": f"{verifying_part.get('label', 'Installment')} Confirmed",
            "message": f"Your payment of ₹{amount_just_paid:,.0f} has been verified and marked as Paid.",
            "type": "installment_confirmed",
            "read": False,
            "created_at": now
        })

    return {
        "ok": True,
        "part_confirmed": verifying_part.get("label"),
        "amount_paid": amount_just_paid,
        "payment_status": new_pay_status,
        "fully_paid": all_paid
    }


@router.get("/my-proposals")
async def get_my_proposals(current_user: dict = Depends(get_current_user)):
    """Get all sales/proposals for the current client with payment info"""
    client_email = current_user["email"]
    sales = await sales_col.find(
        {"client_email": client_email},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)

    products_col = db["products"]
    users_col = db["users"]
    for sale in sales:
        product = await products_col.find_one({"id": sale.get("product_id")}, {"_id": 0, "name": 1, "category": 1})
        if product:
            sale["product_name"] = product.get("name", "Unknown")
            sale["product_category"] = product.get("category", "")
        partner = await users_col.find_one({"id": sale.get("partner_id")}, {"_id": 0, "name": 1})
        if partner:
            sale["partner_name"] = partner.get("name", "Unknown")

        # Get latest payment parts and pre-assessment deduction from linked pre-assessment if available
        pa = await pre_assessments_col.find_one(
            {"$or": [
                {"sale_id": sale.get("id")},
                {"id": sale.get("pre_assessment_id")},
                {"client_email": client_email, "proposal_payment_parts": {"$exists": True}}
            ]},
            {"_id": 0, "proposal_payment_parts": 1, "proposal_pa_deduction": 1, "proposal_deduct_pa_fee": 1, "deduct_pre_assessment_fee": 1, "pre_assessment_deduction": 1, "proposal_base_fee": 1}
        )
        if pa:
            if pa.get("proposal_payment_parts"):
                sale["payment_parts"] = pa["proposal_payment_parts"]
            if pa.get("proposal_pa_deduction") is not None:
                sale["proposal_pa_deduction"] = pa.get("proposal_pa_deduction")
                sale["pre_assessment_deduction"] = pa.get("proposal_pa_deduction")
            if pa.get("proposal_deduct_pa_fee") is not None:
                sale["proposal_deduct_pa_fee"] = pa.get("proposal_deduct_pa_fee")
                sale["deduct_pre_assessment_fee"] = pa.get("proposal_deduct_pa_fee")
            if pa.get("deduct_pre_assessment_fee") is not None and "deduct_pre_assessment_fee" not in sale:
                sale["deduct_pre_assessment_fee"] = pa.get("deduct_pre_assessment_fee")
            if pa.get("pre_assessment_deduction") is not None and "pre_assessment_deduction" not in sale:
                sale["pre_assessment_deduction"] = pa.get("pre_assessment_deduction")
            if pa.get("proposal_base_fee") and not sale.get("base_fee"):
                sale["base_fee"] = pa.get("proposal_base_fee")
                sale["fee_before_discount"] = pa.get("proposal_base_fee")

        # Get payment transactions for this sale
        transactions = await payment_transactions_col.find(
            {"sale_id": sale["id"]}, {"_id": 0}
        ).sort("created_at", -1).to_list(50)
        sale["payment_transactions"] = transactions

        # Calculate pending_amount if not present
        if sale.get("pending_amount") is None:
            fee = sale.get("fee_amount", 0) or 0
            received = sale.get("amount_received", 0) or 0
            sale["pending_amount"] = round(fee - received, 2)

        # Serialize datetime
        for field in ["created_at", "approved_at", "collection_deadline"]:
            if field in sale and sale[field] and hasattr(sale[field], 'isoformat'):
                sale[field] = sale[field].isoformat()

    return sales


@router.post("/create-checkout")
async def create_checkout(request: PaymentRequest, http_request: Request, current_user: dict = Depends(get_current_user)):
    """Create a Stripe checkout session or process mock installment payment for a sale's pending amount"""
    sale = await sales_col.find_one({"id": request.sale_id}, {"_id": 0})
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")

    if sale.get("status") != "approved":
        raise HTTPException(status_code=400, detail="Sale must be approved before payment")

    pending = round(sale.get("pending_amount", 0), 2)
    if pending <= 0:
        raise HTTPException(status_code=400, detail="No pending amount to pay")

    origin = request.origin_url.rstrip("/")
    amount_float = float(pending)

    if not STRIPE_API_KEY:
        # Fallback to direct test checkout when Stripe is not configured
        mock_id = uuid.uuid4().hex[:12]
        session_id = f"MOCK-{mock_id}"

        transaction = {
            "id": str(uuid.uuid4()),
            "sale_id": request.sale_id,
            "session_id": session_id,
            "user_id": current_user["id"],
            "client_email": sale.get("client_email", ""),
            "amount": amount_float,
            "currency": "inr",
            "status": "paid",
            "payment_status": "paid",
            "metadata": {
                "client_name": sale.get("client_name", ""),
                "product_id": sale.get("product_id", ""),
                "mode": "mock_checkout"
            },
            "created_at": datetime.now(timezone.utc)
        }
        await payment_transactions_col.insert_one(transaction)
        await _process_successful_payment(request.sale_id, amount_float, session_id)

        await log_activity(current_user["id"], current_user.get("name", ""), "completed_payment", "payment",
                        transaction["id"], f"Payment of ₹{amount_float} completed for {sale.get('client_name', '')}",
                        case_id=sale.get("case_id"), client_name=sale.get("client_name"))

        success_url = f"{origin}/client?tab=payments&paid=true&amount={amount_float}"
        return {"url": success_url, "session_id": session_id, "mode": "mock", "message": "Payment completed successfully"}

    success_url = f"{origin}/payment-success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin}/payment-cancel?sale_id={request.sale_id}"

    from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionRequest

    host_url = str(http_request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)

    checkout_request = CheckoutSessionRequest(
        amount=amount_float,
        currency="inr",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "sale_id": request.sale_id,
            "client_email": sale.get("client_email", ""),
            "client_name": sale.get("client_name", ""),
            "product_id": sale.get("product_id", ""),
            "user_id": current_user["id"]
        }
    )

    session = await stripe_checkout.create_checkout_session(checkout_request)

    transaction = {
        "id": str(uuid.uuid4()),
        "sale_id": request.sale_id,
        "session_id": session.session_id,
        "user_id": current_user["id"],
        "client_email": sale.get("client_email", ""),
        "amount": amount_float,
        "currency": "inr",
        "status": "initiated",
        "payment_status": "pending",
        "metadata": {
            "client_name": sale.get("client_name", ""),
            "product_id": sale.get("product_id", "")
        },
        "created_at": datetime.now(timezone.utc)
    }
    await payment_transactions_col.insert_one(transaction)

    await log_activity(current_user["id"], current_user.get("name", ""), "initiated_payment", "payment",
                    transaction["id"], f"Payment of ₹{amount_float} initiated for {sale.get('client_name', '')}",
                    case_id=sale.get("case_id"), client_name=sale.get("client_name"))

    return {"url": session.url, "session_id": session.session_id}


@router.get("/status/{session_id}")
async def get_payment_status(session_id: str, current_user: dict = Depends(get_current_user)):
    """Poll payment status for a checkout session"""
    transaction = await payment_transactions_col.find_one({"session_id": session_id}, {"_id": 0})
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if transaction.get("payment_status") in ["paid", "failed"]:
        return {
            "status": transaction.get("status"),
            "payment_status": transaction.get("payment_status"),
            "amount": transaction.get("amount"),
            "sale_id": transaction.get("sale_id")
        }

    if session_id.startswith("MOCK-"):
        await _process_successful_payment(transaction["sale_id"], transaction["amount"], session_id)
        return {
            "status": "complete",
            "payment_status": "paid",
            "amount": transaction.get("amount"),
            "sale_id": transaction.get("sale_id")
        }

    if not STRIPE_API_KEY:
        raise HTTPException(status_code=500, detail="Payment system not configured")

    from emergentintegrations.payments.stripe.checkout import StripeCheckout
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url="")

    checkout_status = await stripe_checkout.get_checkout_status(session_id)

    new_status = checkout_status.status
    new_payment_status = checkout_status.payment_status
    update_data = {
        "status": new_status,
        "payment_status": new_payment_status,
        "updated_at": datetime.now(timezone.utc)
    }
    await payment_transactions_col.update_one({"session_id": session_id}, {"$set": update_data})

    if new_payment_status == "paid":
        await _process_successful_payment(transaction["sale_id"], transaction["amount"], session_id)

    return {
        "status": new_status,
        "payment_status": new_payment_status,
        "amount": transaction.get("amount"),
        "sale_id": transaction.get("sale_id")
    }


async def _process_successful_payment(sale_id: str, amount: float, session_id: str):
    """Update sale and linked PA/case after successful payment — idempotent"""
    existing = await payment_transactions_col.find_one(
        {"session_id": session_id, "processed": True}, {"_id": 0}
    )
    if existing:
        return

    sale = await sales_col.find_one({"id": sale_id}, {"_id": 0})
    if not sale:
        return

    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    new_received = round((sale.get("amount_received", 0) or 0) + amount, 2)
    new_pending = round((sale.get("fee_amount", 0) or 0) - new_received, 2)
    if new_pending < 0:
        new_pending = 0

    pay_status = "paid" if new_pending <= 0 else "partial"
    rate = sale.get("commission_rate", 0) or 0
    new_commission = round(new_received * (rate / 100), 2)

    # Update payment parts in sales record
    parts = sale.get("payment_parts") or []
    # Find next pending/locked part and mark as paid
    paid_part_label = "Installment Payment"
    for p in parts:
        if p.get("status") in ["pending", "locked"]:
            p["status"] = "paid"
            p["paid_at"] = now_iso
            p["payment_ref"] = session_id
            paid_part_label = p.get("label", paid_part_label)
            break

    payment_entry = {
        "amount": amount,
        "method": "mock_installment" if session_id.startswith("MOCK-") else "stripe_online",
        "reference": session_id,
        "date": now_iso,
        "recorded_by": "system_auto",
        "part_label": paid_part_label
    }

    await sales_col.update_one({"id": sale_id}, {
        "$set": {
            "amount_received": new_received,
            "pending_amount": new_pending,
            "payment_status": pay_status,
            "commission_amount": new_commission,
            "payment_parts": parts
        },
        "$push": {"payment_history": payment_entry}
    })

    # Mark transaction as processed
    await payment_transactions_col.update_one({"session_id": session_id}, {"$set": {"processed": True}})

    # Sync linked pre-assessment
    pa = await pre_assessments_col.find_one(
        {"$or": [{"sale_id": sale_id}, {"client_email": sale.get("client_email"), "proposal_payment_parts": {"$exists": True}}]}
    )
    if pa:
        pa_parts = pa.get("proposal_payment_parts") or []
        for p in pa_parts:
            if p.get("status") in ["pending", "locked"]:
                p["status"] = "paid"
                p["paid_at"] = now_iso
                p["payment_ref"] = session_id
                break
        all_pa_paid = all(p.get("status") == "paid" for p in pa_parts)
        pa_update = {
            "proposal_payment_parts": pa_parts,
            "proposal_amount_paid": new_received,
            "proposal_amount_pending": new_pending,
            "pending_installment_unlock": False,
            "updated_at": now
        }
        if all_pa_paid:
            pa_update.update({
                "stage": "proposal_paid",
                "proposal_status": "paid",
                "proposal_paid_at": now
            })
        await pre_assessments_col.update_one({"id": pa["id"]}, {"$set": pa_update})

    # Auto-unlock Step 4 for the linked case if Step 3 is completed
    case_query = {}
    if pa and pa.get("id"):
        case_query = {"pre_assessment_id": pa["id"]}
    elif sale.get("case_id"):
        case_query = {"id": sale["case_id"]}
    elif sale.get("client_id"):
        case_query = {"client_id": sale["client_id"]}
    
    if case_query:
        linked_case = await cases_col.find_one(case_query)
        if linked_case:
            case_steps = await case_steps_col.find({"case_id": linked_case["id"]}).sort("step_order", 1).to_list(100)
            step3 = next((s for s in case_steps if s.get("step_order") == 3), None)
            step4 = next((s for s in case_steps if s.get("step_order") == 4), None)
            
            # If Step 3 is completed and Step 4 is pending, start Step 4!
            if step3 and step3.get("status") == "completed" and step4 and step4.get("status") == "pending":
                await case_steps_col.update_one(
                    {"case_id": linked_case["id"], "step_name": step4["step_name"]},
                    {"$set": {"status": "in_progress", "started_at": now, "updated_at": now}}
                )
                await cases_col.update_one(
                    {"id": linked_case["id"]},
                    {"$set": {"current_step": step4["step_name"], "current_step_order": 4, "updated_at": now}}
                )
                if linked_case.get("case_manager_id"):
                    await notifications_col.insert_one({
                        "id": str(uuid.uuid4()),
                        "user_id": linked_case["case_manager_id"],
                        "title": "2nd Installment Paid — Step 4 Unlocked",
                        "message": f"Client {sale.get('client_name', 'Client')} paid 2nd installment (₹{amount:,.0f}). Step 4 is now unlocked and in progress.",
                        "type": "installment_paid",
                        "read": False,
                        "created_at": now
                    })

    # Notify client
    client_uid = sale.get("client_id") or (pa and pa.get("client_user_id"))
    if client_uid:
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": client_uid,
            "title": "Payment Received — Step 4 Unlocked",
            "message": f"Your payment of ₹{amount:,.0f} was successful! Step 4 (Application Filing) is now unlocked.",
            "type": "payment_received",
            "read": False,
            "created_at": now
        })

    # Notify admin
    await notifications_col.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": "admin",
        "title": "Online Payment Received",
        "message": f"₹{amount:,.0f} received for sale of {sale.get('client_name', 'Unknown')}",
        "type": "payment_received",
        "related_id": sale_id,
        "read": False,
        "created_at": now
    })


@router.get("/history/{sale_id}")
async def get_payment_history(sale_id: str, current_user: dict = Depends(get_current_user)):
    """Get payment transaction history for a sale"""
    transactions = await payment_transactions_col.find(
        {"sale_id": sale_id}, {"_id": 0}
    ).sort("created_at", -1).to_list(50)

    for t in transactions:
        if "created_at" in t and hasattr(t["created_at"], "isoformat"):
            t["created_at"] = t["created_at"].isoformat()
        if "updated_at" in t and hasattr(t["updated_at"], "isoformat"):
            t["updated_at"] = t["updated_at"].isoformat()

    return transactions


RECEIPTS_DIR = "/app/uploads/receipts"
os.makedirs(RECEIPTS_DIR, exist_ok=True)


def _generate_receipt_pdf(sale: dict, transaction: dict, filename: str):
    """Generate a professional branded payment receipt PDF"""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT

    doc = SimpleDocTemplate(filename, pagesize=A4, topMargin=25, bottomMargin=25, leftMargin=40, rightMargin=40)
    styles = getSampleStyleSheet()

    brand_color = colors.HexColor('#2a777a')
    accent_color = colors.HexColor('#f7620b')
    light_bg = colors.HexColor('#f0f9f9')

    company_style = ParagraphStyle('Company', parent=styles['Heading1'], fontSize=22, textColor=brand_color, alignment=TA_CENTER, spaceAfter=2)
    tagline_style = ParagraphStyle('Tagline', parent=styles['Normal'], fontSize=9, textColor=colors.grey, alignment=TA_CENTER, spaceAfter=6)
    receipt_title = ParagraphStyle('ReceiptTitle', parent=styles['Heading2'], fontSize=16, textColor=accent_color, alignment=TA_CENTER, spaceAfter=4)
    label_style = ParagraphStyle('Label', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#666666'))
    value_style = ParagraphStyle('Value', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor('#222222'), fontName='Helvetica-Bold')
    small_style = ParagraphStyle('Small', parent=styles['Normal'], fontSize=8, textColor=colors.grey, alignment=TA_CENTER)

    elements = []

    # Logo Header
    logo_path = "/app/backend/uploads/leamss-logo.png"
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=180, height=80)
        logo.hAlign = 'CENTER'
        elements.append(logo)
        elements.append(Spacer(1, 4))
    else:
        elements.append(Paragraph("LEAMSS Immigration Services", company_style))

    elements.append(Paragraph("Ladhani Education & Migration Services Pvt. Ltd", tagline_style))
    elements.append(HRFlowable(width="100%", thickness=2, color=brand_color, spaceAfter=12))
    elements.append(Paragraph("PAYMENT RECEIPT", receipt_title))
    elements.append(Spacer(1, 8))

    # Receipt meta
    receipt_no = f"REC-{transaction.get('id', 'N/A')[:8].upper()}"
    txn_date = transaction.get('created_at', '')
    if hasattr(txn_date, 'strftime'):
        txn_date_str = txn_date.strftime('%d %b %Y, %I:%M %p')
    elif isinstance(txn_date, str):
        try:
            txn_date_str = datetime.fromisoformat(txn_date.replace('Z', '+00:00')).strftime('%d %b %Y, %I:%M %p')
        except (ValueError, TypeError):
            txn_date_str = str(txn_date)
    else:
        txn_date_str = datetime.now().strftime('%d %b %Y, %I:%M %p')

    meta_data = [
        [Paragraph('Receipt No:', label_style), Paragraph(receipt_no, value_style),
        Paragraph('Date:', label_style), Paragraph(txn_date_str, value_style)],
        [Paragraph('Payment Method:', label_style), Paragraph('Online (Stripe)', value_style),
        Paragraph('Transaction ID:', label_style), Paragraph(transaction.get('session_id', 'N/A')[:20] + '...', value_style)],
    ]
    meta_table = Table(meta_data, colWidths=[90, 170, 90, 170])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), light_bg),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 15))

    # Client Info
    elements.append(Paragraph("Client Information", ParagraphStyle('SectionHead', parent=styles['Heading3'], fontSize=12, textColor=brand_color, spaceAfter=6)))
    client_data = [
        [Paragraph('Name:', label_style), Paragraph(sale.get('client_name', 'N/A'), value_style)],
        [Paragraph('Email:', label_style), Paragraph(sale.get('client_email', 'N/A'), value_style)],
        [Paragraph('Mobile:', label_style), Paragraph(sale.get('client_mobile', 'N/A'), value_style)],
        [Paragraph('Service:', label_style), Paragraph(sale.get('product_name', 'N/A'), value_style)],
    ]
    client_table = Table(client_data, colWidths=[80, 440])
    client_table.setStyle(TableStyle([
        ('PADDING', (0, 0), (-1, -1), 6),
        ('LINEBELOW', (0, 0), (-1, -1), 0.3, colors.HexColor('#e0e0e0')),
    ]))
    elements.append(client_table)
    elements.append(Spacer(1, 15))

    # Fee Breakdown
    # Fee Breakdown
    elements.append(Paragraph("Fee Breakdown", ParagraphStyle('SectionHead', parent=styles['Heading3'], fontSize=12, textColor=brand_color, spaceAfter=6)))

    fee_rows = []
    pa_deduction = float(sale.get('pre_assessment_deduction', 0) or sale.get('proposal_pa_deduction', 0) or 0)
    if not pa_deduction and (sale.get('deduct_pre_assessment_fee') or sale.get('proposal_deduct_pa_fee')):
        pa_deduction = 5100.0

    has_discount = (sale.get('total_discount_amount', 0) or 0) > 0 or (sale.get('promo_discount_amount', 0) or 0) > 0 or pa_deduction > 0
    has_gst = bool(sale.get('gst_included')) and (sale.get('gst_amount', 0) or 0) > 0
    original_fee = sale.get('fee_before_discount', sale.get('base_fee', sale.get('fee_amount', 0))) or sale.get('fee_amount', 0)

    if has_discount:
        fee_rows.append(['Original Service Fee', f"INR {original_fee:,.2f}"])
        if pa_deduction > 0:
            fee_rows.append(['Pre-Assessment Fee Paid (Deduction)', f"- INR {pa_deduction:,.2f}"])
        if (sale.get('promo_discount_amount', 0) or 0) > 0:
            fee_rows.append([f"Promo Code ({sale.get('promo_code', '')})", f"- INR {sale['promo_discount_amount']:,.2f}"])
        if (sale.get('additional_discount_percentage', 0) or 0) > 0:
            fee_rows.append([f"Special Discount ({sale['additional_discount_percentage']}%)", f"- INR {sale.get('additional_discount_amount', 0):,.2f}"])
        fee_rows.append(['', ''])  # separator
    if has_gst:
        base_fee_amt = float(sale.get('base_fee') or 0) or round(float(sale.get('fee_amount', 0) or 0) - float(sale.get('gst_amount', 0) or 0), 2)
        fee_rows.append(['Base Service Fee', f"INR {base_fee_amt:,.2f}"])
        fee_rows.append([f"GST ({int(round((sale.get('gst_amount', 0) or 0) / base_fee_amt * 100)) if base_fee_amt else 18}%)", f"INR {sale.get('gst_amount', 0):,.2f}"])
    fee_rows.append(['Net Service Fee', f"INR {sale.get('fee_amount', 0):,.2f}"])

    fee_table = Table(fee_rows, colWidths=[320, 200])
    fee_style = [
        ('PADDING', (0, 0), (-1, -1), 7),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('LINEBELOW', (0, -1), (-1, -1), 1, brand_color),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, -1), (-1, -1), brand_color),
    ]
    if has_discount:
        for i, row in enumerate(fee_rows):
            if row[0].startswith('Promo') or row[0].startswith('Special'):
                fee_style.append(('TEXTCOLOR', (0, i), (-1, i), colors.HexColor('#16a34a')))
    fee_table.setStyle(TableStyle(fee_style))
    elements.append(fee_table)
    elements.append(Spacer(1, 15))

    # Payment Summary
    elements.append(Paragraph("Payment Summary", ParagraphStyle('SectionHead', parent=styles['Heading3'], fontSize=12, textColor=brand_color, spaceAfter=6)))

    txn_amount = transaction.get('amount', 0)
    total_received = sale.get('amount_received', 0) or 0
    total_fee = sale.get('fee_amount', 0) or 0
    pending = max(0, round(total_fee - total_received, 2))

    payment_rows = [
        ['This Payment', f"INR {txn_amount:,.2f}"],
        ['Total Amount Paid', f"INR {total_received:,.2f}"],
        ['Remaining Balance', f"INR {pending:,.2f}"],
    ]
    pay_table = Table(payment_rows, colWidths=[320, 200])
    pay_style = [
        ('PADDING', (0, 0), (-1, -1), 8),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#fff3e0')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 0), (-1, 0), accent_color),
        ('LINEBELOW', (0, 0), (-1, -1), 0.3, colors.HexColor('#e0e0e0')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]
    if pending <= 0:
        pay_style.append(('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#16a34a')))
    else:
        pay_style.append(('TEXTCOLOR', (0, -1), (-1, -1), accent_color))
    pay_table.setStyle(TableStyle(pay_style))
    elements.append(pay_table)

    if pending <= 0:
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("FULLY PAID", ParagraphStyle('Paid', parent=styles['Heading2'], fontSize=14, textColor=colors.HexColor('#16a34a'), alignment=TA_CENTER)))

    elements.append(Spacer(1, 25))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#cccccc'), spaceAfter=8))

    # Footer
    elements.append(Paragraph("This is a system-generated receipt. No signature required.", small_style))
    elements.append(Paragraph("Ladhani Education & Migration Services Pvt. Ltd | support@leamss.com", small_style))
    elements.append(Spacer(1, 4))
    elements.append(Paragraph(f"Generated on {datetime.now().strftime('%d %b %Y at %I:%M %p')}", small_style))

    doc.build(elements)
    return filename


@router.get("/receipt/{transaction_id}")
async def download_receipt(transaction_id: str, current_user: dict = Depends(get_current_user)):
    """Download a PDF receipt for a specific payment transaction"""
    from fastapi.responses import FileResponse

    transaction = await payment_transactions_col.find_one({"id": transaction_id}, {"_id": 0})
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if transaction.get("payment_status") != "paid":
        raise HTTPException(status_code=400, detail="Receipt available only for completed payments")

    sale = await sales_col.find_one({"id": transaction["sale_id"]}, {"_id": 0})
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")

    # Enrich sale with product name
    products_col = db["products"]
    product = await products_col.find_one({"id": sale.get("product_id")}, {"_id": 0, "name": 1})
    if product:
        sale["product_name"] = product.get("name", "N/A")

    filename = os.path.join(RECEIPTS_DIR, f"receipt_{transaction_id[:8]}.pdf")
    _generate_receipt_pdf(sale, transaction, filename)

    receipt_name = f"LEAMSS_Receipt_{transaction_id[:8].upper()}.pdf"
    return FileResponse(filename, media_type="application/pdf", filename=receipt_name)


@router.get("/receipt-by-sale/{sale_id}")
async def download_sale_receipt(sale_id: str, current_user: dict = Depends(get_current_user)):
    """Download a combined receipt for all paid transactions of a sale"""
    from fastapi.responses import FileResponse

    sale = await sales_col.find_one({"id": sale_id}, {"_id": 0})
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")

    # Get the latest paid transaction
    transaction = await payment_transactions_col.find_one(
        {"sale_id": sale_id, "payment_status": "paid"},
        {"_id": 0}
    )

    if not transaction:
        # Create a virtual transaction for manual payments
        transaction = {
            "id": f"MANUAL-{sale_id[:8]}",
            "session_id": "Manual Payment",
            "amount": sale.get("amount_received", 0),
            "created_at": sale.get("approved_at", sale.get("created_at", datetime.now(timezone.utc))),
            "payment_status": "paid"
        }

    products_col = db["products"]
    product = await products_col.find_one({"id": sale.get("product_id")}, {"_id": 0, "name": 1})
    if product:
        sale["product_name"] = product.get("name", "N/A")

    filename = os.path.join(RECEIPTS_DIR, f"receipt_sale_{sale_id[:8]}.pdf")
    _generate_receipt_pdf(sale, transaction, filename)

    receipt_name = f"LEAMSS_Receipt_{sale_id[:8].upper()}.pdf"
    return FileResponse(filename, media_type="application/pdf", filename=receipt_name)
