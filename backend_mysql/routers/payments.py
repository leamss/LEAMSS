"""
Payments Router for LEAMSS Portal (MySQL)
Stripe Payment Gateway Integration
"""
import os
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from dotenv import load_dotenv

from core.database import get_db
from core.models import (
    PaymentTransaction, PaymentStatus, Sale, Case, User, Product
)
from core.auth import get_current_user

from emergentintegrations.payments.stripe.checkout import (
    StripeCheckout, CheckoutSessionRequest, CheckoutSessionResponse, CheckoutStatusResponse
)

load_dotenv()

router = APIRouter(prefix="/payments", tags=["Payments"])

STRIPE_API_KEY = os.getenv("STRIPE_API_KEY")

# Define fixed payment packages (security: amounts are server-side only)
PAYMENT_PACKAGES = {
    "consultation_basic": {"amount": 5000.00, "currency": "inr", "name": "Basic Consultation"},
    "consultation_premium": {"amount": 15000.00, "currency": "inr", "name": "Premium Consultation"},
    "document_review": {"amount": 2500.00, "currency": "inr", "name": "Document Review"},
}


class CreateCheckoutRequest(BaseModel):
    sale_id: Optional[str] = None
    case_id: Optional[str] = None
    package_id: Optional[str] = None  # For predefined packages
    origin_url: str


class CheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str


@router.post("/checkout/session", response_model=CheckoutResponse)
async def create_checkout_session(
    request: Request,
    checkout_request: CreateCheckoutRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a Stripe checkout session for payment"""
    
    if not STRIPE_API_KEY:
        raise HTTPException(status_code=500, detail="Payment gateway not configured")
    
    # Determine amount based on sale, case, or package
    amount = 0.0
    currency = "inr"
    payment_type = "fee_payment"
    sale_id = None
    case_id = None
    metadata = {
        "user_id": current_user["id"],
        "user_email": current_user["email"],
        "source": "leamss_portal"
    }
    
    if checkout_request.sale_id:
        # Payment for a specific sale
        result = await db.execute(
            select(Sale).where(Sale.id == checkout_request.sale_id)
        )
        sale = result.scalar_one_or_none()
        if not sale:
            raise HTTPException(status_code=404, detail="Sale not found")
        
        amount = float(sale.fee_amount)
        sale_id = sale.id
        metadata["sale_id"] = sale.id
        metadata["client_name"] = sale.client_name
        payment_type = "sale_payment"
        
    elif checkout_request.case_id:
        # Payment for a case
        result = await db.execute(
            select(Case).where(Case.id == checkout_request.case_id)
        )
        case = result.scalar_one_or_none()
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        
        # Get associated sale for amount
        if case.sale_id:
            sale_result = await db.execute(
                select(Sale).where(Sale.id == case.sale_id)
            )
            sale = sale_result.scalar_one_or_none()
            if sale:
                amount = float(sale.fee_amount)
                sale_id = sale.id
        
        case_id = case.id
        metadata["case_id"] = case.id
        metadata["case_number"] = case.case_id
        payment_type = "case_payment"
        
    elif checkout_request.package_id:
        # Predefined package payment
        package = PAYMENT_PACKAGES.get(checkout_request.package_id)
        if not package:
            raise HTTPException(status_code=400, detail="Invalid package")
        
        amount = package["amount"]
        currency = package["currency"]
        metadata["package_id"] = checkout_request.package_id
        metadata["package_name"] = package["name"]
        payment_type = "package_payment"
    else:
        raise HTTPException(status_code=400, detail="Must specify sale_id, case_id, or package_id")
    
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid payment amount")
    
    # Build success/cancel URLs
    origin_url = checkout_request.origin_url.rstrip('/')
    success_url = f"{origin_url}/payment/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin_url}/payment/cancel"
    
    # Initialize Stripe checkout
    host_url = str(request.base_url).rstrip('/')
    webhook_url = f"{host_url}/api/webhook/stripe"
    
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
    
    try:
        # Create checkout session
        checkout_req = CheckoutSessionRequest(
            amount=amount,
            currency=currency,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata=metadata
        )
        
        session: CheckoutSessionResponse = await stripe_checkout.create_checkout_session(checkout_req)
        
        # Create payment transaction record BEFORE redirect
        payment_transaction = PaymentTransaction(
            session_id=session.session_id,
            user_id=current_user["id"],
            sale_id=sale_id,
            case_id=case_id,
            amount=amount,
            currency=currency,
            payment_type=payment_type,
            status=PaymentStatus.initiated,
            payment_status="initiated",
            metadata=metadata
        )
        db.add(payment_transaction)
        await db.commit()
        
        return CheckoutResponse(
            checkout_url=session.url,
            session_id=session.session_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Payment error: {str(e)}")


@router.get("/checkout/status/{session_id}")
async def get_checkout_status(
    request: Request,
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get the status of a checkout session"""
    
    if not STRIPE_API_KEY:
        raise HTTPException(status_code=500, detail="Payment gateway not configured")
    
    # Get existing transaction
    result = await db.execute(
        select(PaymentTransaction).where(PaymentTransaction.session_id == session_id)
    )
    transaction = result.scalar_one_or_none()
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # If already processed, return cached status
    if transaction.status in [PaymentStatus.paid, PaymentStatus.refunded]:
        return {
            "session_id": session_id,
            "status": transaction.status.value,
            "payment_status": transaction.payment_status,
            "amount": transaction.amount,
            "currency": transaction.currency,
            "paid_at": transaction.paid_at.isoformat() if transaction.paid_at else None
        }
    
    # Check status with Stripe
    host_url = str(request.base_url).rstrip('/')
    webhook_url = f"{host_url}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
    
    try:
        status: CheckoutStatusResponse = await stripe_checkout.get_checkout_status(session_id)
        
        # Update transaction based on status
        new_status = PaymentStatus.pending
        if status.payment_status == "paid":
            new_status = PaymentStatus.paid
        elif status.status == "expired":
            new_status = PaymentStatus.expired
        elif status.payment_status == "unpaid" and status.status == "complete":
            new_status = PaymentStatus.failed
        
        # Only update if status changed
        if transaction.status != new_status:
            transaction.status = new_status
            transaction.payment_status = status.payment_status
            
            if new_status == PaymentStatus.paid:
                transaction.paid_at = datetime.utcnow()
                
                # Update related sale status if applicable
                if transaction.sale_id:
                    await db.execute(
                        update(Sale)
                        .where(Sale.id == transaction.sale_id)
                        .values(payment_status="paid")
                    )
            
            await db.commit()
        
        return {
            "session_id": session_id,
            "status": new_status.value,
            "payment_status": status.payment_status,
            "amount": status.amount_total / 100 if status.amount_total else transaction.amount,
            "currency": status.currency or transaction.currency,
            "paid_at": transaction.paid_at.isoformat() if transaction.paid_at else None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking status: {str(e)}")


@router.get("/history")
async def get_payment_history(
    page: int = 1,
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get payment history for the current user"""
    
    query = select(PaymentTransaction).order_by(PaymentTransaction.created_at.desc())
    
    # Role-based filtering
    if current_user["role"] == "client":
        query = query.where(PaymentTransaction.user_id == current_user["id"])
    elif current_user["role"] == "partner":
        # Partners see payments for their sales
        sales_result = await db.execute(
            select(Sale.id).where(Sale.partner_id == current_user["id"])
        )
        sale_ids = [s[0] for s in sales_result.all()]
        query = query.where(PaymentTransaction.sale_id.in_(sale_ids))
    # Admin sees all
    
    # Pagination
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    transactions = result.scalars().all()
    
    return [
        {
            "id": t.id,
            "session_id": t.session_id,
            "amount": t.amount,
            "currency": t.currency,
            "payment_type": t.payment_type,
            "status": t.status.value if t.status else "unknown",
            "payment_status": t.payment_status,
            "paid_at": t.paid_at.isoformat() if t.paid_at else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "metadata": t.metadata
        }
        for t in transactions
    ]


@router.get("/stats")
async def get_payment_stats(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get payment statistics (Admin only)"""
    
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    from sqlalchemy import func
    
    # Total collected
    total_result = await db.execute(
        select(func.sum(PaymentTransaction.amount))
        .where(PaymentTransaction.status == PaymentStatus.paid)
    )
    total_collected = total_result.scalar() or 0
    
    # Total pending
    pending_result = await db.execute(
        select(func.sum(PaymentTransaction.amount))
        .where(PaymentTransaction.status.in_([PaymentStatus.initiated, PaymentStatus.pending]))
    )
    total_pending = pending_result.scalar() or 0
    
    # Count by status
    status_result = await db.execute(
        select(PaymentTransaction.status, func.count(PaymentTransaction.id))
        .group_by(PaymentTransaction.status)
    )
    status_counts = {row[0].value if row[0] else "unknown": row[1] for row in status_result.all()}
    
    # Recent transactions
    recent_result = await db.execute(
        select(PaymentTransaction)
        .order_by(PaymentTransaction.created_at.desc())
        .limit(5)
    )
    recent = recent_result.scalars().all()
    
    return {
        "total_collected": total_collected,
        "total_pending": total_pending,
        "status_breakdown": status_counts,
        "recent_transactions": [
            {
                "id": t.id,
                "amount": t.amount,
                "currency": t.currency,
                "status": t.status.value if t.status else "unknown",
                "created_at": t.created_at.isoformat() if t.created_at else None
            }
            for t in recent
        ]
    }


# Webhook endpoint for Stripe
@router.post("/webhook/stripe")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Handle Stripe webhooks"""
    
    if not STRIPE_API_KEY:
        raise HTTPException(status_code=500, detail="Payment gateway not configured")
    
    # Get request body and signature
    body = await request.body()
    signature = request.headers.get("Stripe-Signature")
    
    host_url = str(request.base_url).rstrip('/')
    webhook_url = f"{host_url}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
    
    try:
        webhook_response = await stripe_checkout.handle_webhook(body, signature)
        
        # Update transaction based on webhook event
        if webhook_response.session_id:
            result = await db.execute(
                select(PaymentTransaction)
                .where(PaymentTransaction.session_id == webhook_response.session_id)
            )
            transaction = result.scalar_one_or_none()
            
            if transaction:
                if webhook_response.payment_status == "paid":
                    transaction.status = PaymentStatus.paid
                    transaction.paid_at = datetime.utcnow()
                elif webhook_response.event_type == "checkout.session.expired":
                    transaction.status = PaymentStatus.expired
                
                transaction.payment_status = webhook_response.payment_status
                await db.commit()
        
        return {"status": "success"}
        
    except Exception as e:
        print(f"Webhook error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
