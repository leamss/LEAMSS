"""Refunds Router"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from core.database import refunds_col, sales_col, users_col, audit_logs_col
from core.auth import get_current_user
import uuid
from datetime import datetime, timezone

router = APIRouter(prefix="/refunds", tags=["Refunds"])


class RefundCreate(BaseModel):
    sale_id: str
    amount: float
    reason: str
    refund_method: str = "original_payment"
    notes: str = ""


@router.get("")
async def get_refunds(current_user: dict = Depends(get_current_user)):
    """Get all refunds"""
    if current_user["role"] not in ["admin", "case_manager"]:
        raise HTTPException(status_code=403, detail="Admin or Case Manager only")
    
    refunds = await refunds_col.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    for r in refunds:
        sale = await sales_col.find_one({"id": r.get("sale_id")}, {"_id": 0})
        r["client_name"] = sale.get("client_name", "N/A") if sale else "N/A"
        r["client_email"] = sale.get("client_email", "N/A") if sale else "N/A"
        r["original_fee"] = sale.get("fee_amount", 0) if sale else 0
        if isinstance(r.get("created_at"), datetime):
            r["created_at"] = r["created_at"].isoformat()
        if isinstance(r.get("processed_at"), datetime):
            r["processed_at"] = r["processed_at"].isoformat()
    return refunds


@router.post("")
async def create_refund(data: RefundCreate, current_user: dict = Depends(get_current_user)):
    """Create a refund and auto-adjust commission"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    if not data.reason or len(data.reason.strip()) < 5:
        raise HTTPException(status_code=400, detail="Refund reason is required (minimum 5 characters)")
    
    sale = await sales_col.find_one({"id": data.sale_id}, {"_id": 0})
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    
    if sale.get("status") not in ["approved", "pending"]:
        raise HTTPException(status_code=400, detail="Can only refund approved or pending sales")
    
    if data.amount <= 0:
        raise HTTPException(status_code=400, detail="Refund amount must be positive")
    
    # Calculate total already refunded
    existing_refunds = await refunds_col.find({"sale_id": data.sale_id, "status": {"$ne": "cancelled"}}, {"_id": 0}).to_list(100)
    total_refunded = sum(r.get("amount", 0) for r in existing_refunds)
    
    received = sale.get("amount_received", 0) or 0
    if total_refunded + data.amount > received:
        raise HTTPException(status_code=400, detail=f"Refund amount exceeds received amount. Received: ${received}, Already refunded: ${total_refunded}")
    
    # Create refund record
    refund = {
        "id": str(uuid.uuid4()),
        "sale_id": data.sale_id,
        "amount": data.amount,
        "reason": data.reason.strip(),
        "refund_method": data.refund_method,
        "notes": data.notes,
        "status": "processed",
        "processed_by": current_user["id"],
        "processed_at": datetime.now(timezone.utc),
        "created_at": datetime.now(timezone.utc)
    }
    await refunds_col.insert_one(refund)
    
    # Adjust sale: reduce amount_received and recalculate commission
    new_received = round(received - data.amount, 2)
    fee = sale.get("fee_amount", 0) or 0
    new_pending = round(fee - new_received, 2)
    rate = sale.get("commission_rate", 0) or 0
    new_commission = round(new_received * (rate / 100), 2) if rate else 0
    
    # Determine new payment status
    if new_received <= 0:
        pay_status = "refunded"
    elif new_received < fee:
        pay_status = "partial"
    else:
        pay_status = "paid"
    
    new_total_refunded = total_refunded + data.amount
    
    await sales_col.update_one({"id": data.sale_id}, {"$set": {
        "amount_received": new_received,
        "pending_amount": new_pending,
        "commission_amount": new_commission,
        "payment_status": pay_status,
        "total_refunded": new_total_refunded
    }})
    
    # Log the refund
    await audit_logs_col.insert_one({
        "id": str(uuid.uuid4()), "user_id": current_user["id"],
        "action": "refund_processed", "entity_type": "sale",
        "entity_id": data.sale_id, "new_value": {
            "refund_amount": data.amount, "reason": data.reason,
            "new_received": new_received, "new_commission": new_commission,
            "client_name": sale.get("client_name")
        }, "created_at": datetime.now(timezone.utc)
    })
    
    return {
        "message": "Refund processed successfully",
        "refund_id": refund["id"],
        "refund_amount": data.amount,
        "new_amount_received": new_received,
        "new_commission": new_commission,
        "new_payment_status": pay_status
    }


@router.get("/by-sale/{sale_id}")
async def get_sale_refunds(sale_id: str, current_user: dict = Depends(get_current_user)):
    """Get refund history for a sale"""
    refunds = await refunds_col.find({"sale_id": sale_id}, {"_id": 0}).sort("created_at", -1).to_list(100)
    for r in refunds:
        processor = await users_col.find_one({"id": r.get("processed_by")}, {"_id": 0, "password": 0})
        r["processed_by_name"] = processor["name"] if processor else "System"
        if isinstance(r.get("created_at"), datetime):
            r["created_at"] = r["created_at"].isoformat()
        if isinstance(r.get("processed_at"), datetime):
            r["processed_at"] = r["processed_at"].isoformat()
    return refunds
