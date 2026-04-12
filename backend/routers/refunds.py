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
    category: str = ""  # service_issue, client_request, overcharge, other


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
    """Initiate a refund — goes to 'pending_review' status first"""
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

    existing_refunds = await refunds_col.find({"sale_id": data.sale_id, "status": {"$nin": ["cancelled", "rejected"]}}, {"_id": 0}).to_list(100)
    total_refunded = sum(r.get("amount", 0) for r in existing_refunds)

    received = sale.get("amount_received", 0) or 0
    if total_refunded + data.amount > received:
        raise HTTPException(status_code=400, detail=f"Refund exceeds received. Received: ₹{received}, Already refunded: ₹{total_refunded}")

    partner = await users_col.find_one({"id": sale.get("partner_id")}, {"_id": 0, "name": 1})

    refund = {
        "id": str(uuid.uuid4()),
        "sale_id": data.sale_id,
        "amount": data.amount,
        "reason": data.reason.strip(),
        "category": data.category or "other",
        "refund_method": data.refund_method,
        "notes": data.notes,
        "status": "pending_review",
        "client_name": sale.get("client_name", ""),
        "client_email": sale.get("client_email", ""),
        "partner_name": partner["name"] if partner else sale.get("partner_name", ""),
        "partner_id": sale.get("partner_id", ""),
        "product_name": sale.get("product_name", ""),
        "original_fee": sale.get("fee_amount", 0),
        "amount_received": received,
        "initiated_by": current_user["id"],
        "initiated_by_name": current_user.get("name", ""),
        "created_at": datetime.now(timezone.utc),
    }
    await refunds_col.insert_one(refund)
    refund.pop("_id", None)

    await audit_logs_col.insert_one({
        "id": str(uuid.uuid4()), "user_id": current_user["id"],
        "action": "refund_initiated", "entity_type": "refund",
        "entity_id": refund["id"], "new_value": {
            "amount": data.amount, "reason": data.reason,
            "client_name": sale.get("client_name")
        }, "created_at": datetime.now(timezone.utc)
    })

    return {
        "message": "Refund initiated — pending review",
        "refund_id": refund["id"],
        "status": "pending_review",
    }


class RefundReview(BaseModel):
    refund_id: str
    action: str  # "approve", "reject"
    review_notes: str = ""


@router.post("/review")
async def review_refund(data: RefundReview, current_user: dict = Depends(get_current_user)):
    """Review and approve/reject a pending refund"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    refund = await refunds_col.find_one({"id": data.refund_id}, {"_id": 0})
    if not refund:
        raise HTTPException(status_code=404, detail="Refund not found")

    if refund.get("status") != "pending_review":
        raise HTTPException(status_code=400, detail="Refund is not in pending review state")

    if data.action == "reject":
        if not data.review_notes or len(data.review_notes.strip()) < 5:
            raise HTTPException(status_code=400, detail="Rejection reason required (min 5 chars)")
        await refunds_col.update_one({"id": data.refund_id}, {"$set": {
            "status": "rejected",
            "review_notes": data.review_notes.strip(),
            "reviewed_by": current_user["id"],
            "reviewed_by_name": current_user.get("name", ""),
            "reviewed_at": datetime.now(timezone.utc),
        }})
        return {"message": "Refund rejected"}

    # Approve and process
    sale = await sales_col.find_one({"id": refund["sale_id"]}, {"_id": 0})
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")

    received = sale.get("amount_received", 0) or 0
    new_received = round(received - refund["amount"], 2)
    fee = sale.get("fee_amount", 0) or 0
    new_pending = round(fee - new_received, 2)
    rate = sale.get("commission_rate", 0) or 0
    new_commission = round(new_received * (rate / 100), 2) if rate else 0

    if new_received <= 0:
        pay_status = "refunded"
    elif new_received < fee:
        pay_status = "partial"
    else:
        pay_status = "paid"

    existing_refunds = await refunds_col.find({"sale_id": refund["sale_id"], "status": "processed"}, {"_id": 0}).to_list(100)
    new_total_refunded = sum(r.get("amount", 0) for r in existing_refunds) + refund["amount"]

    await sales_col.update_one({"id": refund["sale_id"]}, {"$set": {
        "amount_received": new_received,
        "pending_amount": new_pending,
        "commission_amount": new_commission,
        "payment_status": pay_status,
        "total_refunded": new_total_refunded
    }})

    await refunds_col.update_one({"id": data.refund_id}, {"$set": {
        "status": "processed",
        "review_notes": data.review_notes,
        "reviewed_by": current_user["id"],
        "reviewed_by_name": current_user.get("name", ""),
        "reviewed_at": datetime.now(timezone.utc),
        "processed_by": current_user["id"],
        "processed_at": datetime.now(timezone.utc),
    }})

    await audit_logs_col.insert_one({
        "id": str(uuid.uuid4()), "user_id": current_user["id"],
        "action": "refund_processed", "entity_type": "sale",
        "entity_id": refund["sale_id"], "new_value": {
            "refund_amount": refund["amount"], "reason": refund["reason"],
            "new_received": new_received, "new_commission": new_commission,
            "client_name": refund.get("client_name")
        }, "created_at": datetime.now(timezone.utc)
    })

    return {
        "message": "Refund approved and processed",
        "refund_id": data.refund_id,
        "refund_amount": refund["amount"],
        "new_payment_status": pay_status
    }


@router.get("/detail/{refund_id}")
async def get_refund_detail(refund_id: str, current_user: dict = Depends(get_current_user)):
    """Get full detail of a single refund"""
    if current_user["role"] not in ["admin", "case_manager"]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    refund = await refunds_col.find_one({"id": refund_id}, {"_id": 0})
    if not refund:
        raise HTTPException(status_code=404, detail="Refund not found")

    sale = await sales_col.find_one({"id": refund.get("sale_id")}, {"_id": 0})
    initiator = await users_col.find_one({"id": refund.get("initiated_by")}, {"_id": 0, "name": 1, "email": 1})
    reviewer = await users_col.find_one({"id": refund.get("reviewed_by")}, {"_id": 0, "name": 1, "email": 1})
    partner = await users_col.find_one({"id": refund.get("partner_id") or (sale.get("partner_id") if sale else "")}, {"_id": 0, "name": 1, "email": 1})

    for field in ["created_at", "reviewed_at", "processed_at"]:
        if isinstance(refund.get(field), datetime):
            refund[field] = refund[field].isoformat()

    return {
        **refund,
        "sale": {
            "id": sale["id"] if sale else "",
            "client_name": sale.get("client_name", "") if sale else "",
            "client_email": sale.get("client_email", "") if sale else "",
            "product_name": sale.get("product_name", "") if sale else "",
            "fee_amount": sale.get("fee_amount", 0) if sale else 0,
            "amount_received": sale.get("amount_received", 0) if sale else 0,
            "payment_method": sale.get("payment_method", "") if sale else "",
            "payment_status": sale.get("payment_status", "") if sale else "",
        } if sale else None,
        "initiator": {"name": initiator["name"], "email": initiator["email"]} if initiator else None,
        "reviewer": {"name": reviewer["name"], "email": reviewer["email"]} if reviewer else None,
        "partner": {"name": partner["name"], "email": partner["email"]} if partner else None,
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
