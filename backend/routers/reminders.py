"""Payment Reminders Router — Auto-detect and send payment reminders"""
import uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from core.database import db
from routers.auth import get_current_user

router = APIRouter(prefix="/reminders", tags=["reminders"])

sales_col = db["sales"]
notifications_col = db["notifications"]
users_col = db["users"]
reminder_log_col = db["reminder_logs"]
products_col = db["products"]


@router.get("/pending-payments")
async def get_pending_payments(current_user: dict = Depends(get_current_user)):
    """Get all sales with pending payments — for admin dashboard"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    sales = await sales_col.find(
        {"status": "approved", "payment_status": {"$in": ["pending", "partial", None]}},
        {"_id": 0}
    ).sort("created_at", 1).to_list(500)

    # Also include sales where pending_amount > 0 even if payment_status is not set
    extra_sales = await sales_col.find(
        {"status": "approved", "pending_amount": {"$gt": 0}, "payment_status": {"$nin": ["paid", "refunded"]}},
        {"_id": 0}
    ).to_list(500)

    seen_ids = set()
    all_sales = []
    for s in sales + extra_sales:
        if s["id"] not in seen_ids:
            seen_ids.add(s["id"])
            all_sales.append(s)

    result = []
    total_pending = 0
    for sale in all_sales:
        product = await products_col.find_one({"id": sale.get("product_id")}, {"_id": 0, "name": 1})
        partner = await users_col.find_one({"id": sale.get("partner_id")}, {"_id": 0, "name": 1})
        created_at = sale.get("created_at")
        days_since = 0
        if created_at:
            if isinstance(created_at, datetime):
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)
                days_since = (datetime.now(timezone.utc) - created_at).days

        pending = round((sale.get("fee_amount", 0) or 0) - (sale.get("amount_received", 0) or 0), 2)
        if pending <= 0:
            continue

        # Check reminder history
        reminders = await reminder_log_col.find(
            {"sale_id": sale["id"]}, {"_id": 0}
        ).sort("sent_at", -1).to_list(10)

        last_reminder = reminders[0] if reminders else None
        reminder_count = last_reminder.get("reminder_count", 0) if last_reminder else 0
        last_reminded = None
        if last_reminder and last_reminder.get("sent_at"):
            lr = last_reminder["sent_at"]
            last_reminded = lr.isoformat() if isinstance(lr, datetime) else str(lr)

        # Days since last reminder
        days_since_last_reminder = None
        if last_reminder and isinstance(last_reminder.get("sent_at"), datetime):
            lr = last_reminder["sent_at"]
            if lr.tzinfo is None:
                lr = lr.replace(tzinfo=timezone.utc)
            days_since_last_reminder = (datetime.now(timezone.utc) - lr).days

        total_pending += pending

        result.append({
            "sale_id": sale["id"],
            "client_name": sale.get("client_name", ""),
            "client_email": sale.get("client_email", ""),
            "client_mobile": sale.get("client_mobile", ""),
            "product_name": product.get("name", "Unknown") if product else "Unknown",
            "partner_name": partner.get("name", "") if partner else "",
            "fee_amount": sale.get("fee_amount", 0),
            "amount_received": sale.get("amount_received", 0),
            "pending_amount": pending,
            "payment_status": sale.get("payment_status", "pending"),
            "payment_method": sale.get("payment_method", ""),
            "days_since_creation": days_since,
            "reminder_count": reminder_count,
            "last_reminder_sent": last_reminded,
            "days_since_last_reminder": days_since_last_reminder,
            "urgency": "critical" if days_since > 14 else "high" if days_since > 7 else "medium" if days_since > 3 else "low",
            "created_at": sale.get("created_at").isoformat() if isinstance(sale.get("created_at"), datetime) else str(sale.get("created_at", "")),
        })

    # Sort by urgency (critical first)
    urgency_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    result.sort(key=lambda x: urgency_order.get(x["urgency"], 9))

    return {
        "items": result,
        "stats": {
            "total_clients": len(result),
            "total_pending": round(total_pending, 2),
            "critical": sum(1 for r in result if r["urgency"] == "critical"),
            "high": sum(1 for r in result if r["urgency"] == "high"),
            "medium": sum(1 for r in result if r["urgency"] == "medium"),
            "low": sum(1 for r in result if r["urgency"] == "low"),
            "never_reminded": sum(1 for r in result if r["reminder_count"] == 0),
        }
    }


from pydantic import BaseModel
from typing import Optional


class CustomReminderRequest(BaseModel):
    message: Optional[str] = None
    include_payment_link: bool = False


@router.post("/send/{sale_id}")
async def send_reminder(sale_id: str, body: CustomReminderRequest = CustomReminderRequest(), current_user: dict = Depends(get_current_user)):
    """Manually send a payment reminder for a specific sale with optional custom message"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    sale = await sales_col.find_one({"id": sale_id}, {"_id": 0})
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")

    pending = round((sale.get("fee_amount", 0) or 0) - (sale.get("amount_received", 0) or 0), 2)
    if pending <= 0:
        raise HTTPException(status_code=400, detail="No pending amount")

    client = await users_col.find_one({"email": sale.get("client_email")}, {"_id": 0})

    # Compose message
    custom_msg = body.message.strip() if body.message else None
    notification_msg = custom_msg or f"You have a pending payment of ₹{pending:,.0f} for your service. Please complete the payment at your earliest convenience."

    # Send notification to client
    if client:
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": client["id"],
            "title": "Payment Reminder",
            "message": notification_msg,
            "type": "payment_reminder",
            "related_id": sale_id,
            "read": False,
            "created_at": datetime.now(timezone.utc)
        })

    # Send email reminder
    email_body = custom_msg or f"Dear {sale.get('client_name', 'Client')},<br><br>This is a friendly reminder that you have a pending payment of ₹{pending:,.0f}.<br><br>Total Fee: ₹{sale.get('fee_amount', 0):,.0f}<br>Amount Paid: ₹{sale.get('amount_received', 0):,.0f}<br>Pending: ₹{pending:,.0f}<br><br>Please log in to your LEAMSS portal to complete the payment.<br><br>Thank you,<br>LEAMSS Immigration Services"
    from core.email_service import send_email
    await send_email(
        sale.get("client_email", ""),
        "Payment Reminder — LEAMSS Immigration Services",
        "Payment Reminder",
        email_body
    )

    # Log the reminder
    await reminder_log_col.update_one(
        {"sale_id": sale_id},
        {"$set": {
            "sale_id": sale_id,
            "client_email": sale.get("client_email", ""),
            "sent_at": datetime.now(timezone.utc),
            "sent_by": current_user["id"],
            "pending_amount": pending
        }, "$inc": {"reminder_count": 1}},
        upsert=True
    )

    return {"message": f"Reminder sent to {sale.get('client_name', '')} for ₹{pending:,.0f}"}


@router.post("/send-bulk")
async def send_bulk_reminders(current_user: dict = Depends(get_current_user)):
    """Send reminders to all clients with overdue payments (>3 days)"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    three_days_ago = datetime.now(timezone.utc) - timedelta(days=3)
    sales = await sales_col.find({
        "status": "approved",
        "payment_status": {"$in": ["pending", "partial"]},
        "created_at": {"$lt": three_days_ago}
    }, {"_id": 0}).to_list(500)

    sent_count = 0
    for sale in sales:
        # Skip if reminder sent in last 3 days
        last = await reminder_log_col.find_one({"sale_id": sale["id"]}, {"_id": 0})
        if last and last.get("sent_at"):
            last_sent = last["sent_at"]
            if hasattr(last_sent, 'timestamp'):
                # Ensure timezone awareness
                if last_sent.tzinfo is None:
                    last_sent = last_sent.replace(tzinfo=timezone.utc)
                if (datetime.now(timezone.utc) - last_sent).days < 3:
                    continue

        pending = sale.get("pending_amount", 0)
        if pending <= 0:
            continue

        client = await users_col.find_one({"email": sale.get("client_email")}, {"_id": 0})
        if client:
            await notifications_col.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": client["id"],
                "title": "Payment Reminder",
                "message": f"Pending payment of ₹{pending:,.0f}. Please complete your payment.",
                "type": "payment_reminder",
                "related_id": sale["id"],
                "read": False,
                "created_at": datetime.now(timezone.utc)
            })

        from core.email_service import send_email
        email_body = f"Dear {sale.get('client_name', 'Client')},<br><br>This is a reminder that you have a pending payment of ₹{pending:,.0f}.<br><br>Please log in to your LEAMSS portal to complete the payment.<br><br>Thank you,<br>LEAMSS Immigration Services"
        await send_email(
            sale.get("client_email", ""),
            "Payment Reminder — LEAMSS",
            "Payment Reminder",
            email_body
        )

        await reminder_log_col.update_one(
            {"sale_id": sale["id"]},
            {"$set": {"sent_at": datetime.now(timezone.utc), "sent_by": current_user["id"], "pending_amount": pending},
             "$inc": {"reminder_count": 1}},
            upsert=True
        )
        sent_count += 1

    return {"message": f"Sent {sent_count} payment reminders", "count": sent_count}


@router.get("/history")
async def get_reminder_history(current_user: dict = Depends(get_current_user)):
    """Get all reminder logs"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    logs = await reminder_log_col.find({}, {"_id": 0}).sort("sent_at", -1).to_list(200)
    for log in logs:
        if isinstance(log.get("sent_at"), datetime):
            log["sent_at"] = log["sent_at"].isoformat()
        # Enrich with sale info
        sale = await sales_col.find_one({"id": log.get("sale_id")}, {"_id": 0, "client_name": 1, "client_email": 1, "product_name": 1})
        if sale:
            log["client_name"] = sale.get("client_name", "")
            log["client_email"] = sale.get("client_email", "")

    return logs
