"""Payment Router — Stripe Checkout for Client Payments"""
import os
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional
from core.database import db
from routers.auth import get_current_user

router = APIRouter(prefix="/payments", tags=["payments"])

sales_col = db["sales"]
payment_transactions_col = db["payment_transactions"]
notifications_col = db["notifications"]

STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY")


class PaymentRequest(BaseModel):
    sale_id: str
    origin_url: str


@router.get("/my-proposals")
async def get_my_proposals(current_user: dict = Depends(get_current_user)):
    """Get all sales/proposals for the current client with payment info"""
    # Find sales where client_email matches
    client_email = current_user["email"]
    sales = await sales_col.find(
        {"client_email": client_email},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)

    # Enrich with product and payment info
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
    """Create a Stripe checkout session for a sale's pending amount"""
    if not STRIPE_API_KEY:
        raise HTTPException(status_code=500, detail="Payment system not configured")

    sale = await sales_col.find_one({"id": request.sale_id}, {"_id": 0})
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")

    if sale.get("status") != "approved":
        raise HTTPException(status_code=400, detail="Sale must be approved before payment")

    # Calculate pending amount from server-side data (NEVER trust frontend amount)
    pending = round(sale.get("pending_amount", 0), 2)
    if pending <= 0:
        raise HTTPException(status_code=400, detail="No pending amount to pay")

    # Build dynamic URLs from origin
    origin = request.origin_url.rstrip("/")
    success_url = f"{origin}/payment-success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin}/payment-cancel?sale_id={request.sale_id}"

    # Create Stripe checkout session
    from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionRequest

    host_url = str(http_request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)

    # Amount in float for Stripe (INR)
    amount_float = float(pending)

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

    # Create payment transaction record BEFORE redirect
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

    return {"url": session.url, "session_id": session.session_id}


@router.get("/status/{session_id}")
async def get_payment_status(session_id: str, current_user: dict = Depends(get_current_user)):
    """Poll payment status for a checkout session"""
    if not STRIPE_API_KEY:
        raise HTTPException(status_code=500, detail="Payment system not configured")

    transaction = await payment_transactions_col.find_one({"session_id": session_id}, {"_id": 0})
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # If already processed, return cached status
    if transaction.get("payment_status") in ["paid", "failed"]:
        return {
            "status": transaction.get("status"),
            "payment_status": transaction.get("payment_status"),
            "amount": transaction.get("amount"),
            "sale_id": transaction.get("sale_id")
        }

    from emergentintegrations.payments.stripe.checkout import StripeCheckout
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url="")

    checkout_status = await stripe_checkout.get_checkout_status(session_id)

    # Update transaction
    new_status = checkout_status.status
    new_payment_status = checkout_status.payment_status
    update_data = {
        "status": new_status,
        "payment_status": new_payment_status,
        "updated_at": datetime.now(timezone.utc)
    }
    await payment_transactions_col.update_one({"session_id": session_id}, {"$set": update_data})

    # If payment successful, update the sale
    if new_payment_status == "paid":
        await _process_successful_payment(transaction["sale_id"], transaction["amount"], session_id)

    return {
        "status": new_status,
        "payment_status": new_payment_status,
        "amount": transaction.get("amount"),
        "sale_id": transaction.get("sale_id")
    }


async def _process_successful_payment(sale_id: str, amount: float, session_id: str):
    """Update sale after successful payment — idempotent (won't double-count)"""
    # Check if this session was already processed
    existing = await payment_transactions_col.find_one(
        {"session_id": session_id, "processed": True}, {"_id": 0}
    )
    if existing:
        return  # Already processed

    sale = await sales_col.find_one({"id": sale_id}, {"_id": 0})
    if not sale:
        return

    new_received = round((sale.get("amount_received", 0) or 0) + amount, 2)
    new_pending = round(sale.get("fee_amount", 0) - new_received, 2)
    if new_pending < 0:
        new_pending = 0

    pay_status = "paid" if new_pending <= 0 else "partial"
    rate = sale.get("commission_rate", 0) or 0
    new_commission = round(new_received * (rate / 100), 2)

    # Add to payment history
    payment_entry = {
        "amount": amount,
        "method": "stripe_online",
        "reference": session_id,
        "date": datetime.now(timezone.utc).isoformat(),
        "recorded_by": "system_stripe"
    }

    await sales_col.update_one({"id": sale_id}, {
        "$set": {
            "amount_received": new_received,
            "pending_amount": new_pending,
            "payment_status": pay_status,
            "commission_amount": new_commission
        },
        "$push": {"payment_history": payment_entry}
    })

    # Mark as processed to prevent double-counting
    await payment_transactions_col.update_one({"session_id": session_id}, {"$set": {"processed": True}})

    # Notify admin
    await notifications_col.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": "admin",
        "title": "Online Payment Received",
        "message": f"₹{amount:,.0f} received for sale of {sale.get('client_name', 'Unknown')} via Stripe",
        "type": "payment_received",
        "related_id": sale_id,
        "read": False,
        "created_at": datetime.now(timezone.utc)
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
