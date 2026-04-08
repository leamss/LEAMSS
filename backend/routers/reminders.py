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


@router.get("/pending-payments")
async def get_pending_payments(current_user: dict = Depends(get_current_user)):
    """Get all sales with pending payments — for admin dashboard"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    sales = await sales_col.find(
        {"status": "approved", "payment_status": {"$in": ["pending", "partial"]}},
        {"_id": 0}
    ).sort("created_at", 1).to_list(500)

    products_col = db["products"]
    result = []
    for sale in sales:
        product = await products_col.find_one({"id": sale.get("product_id")}, {"_id": 0, "name": 1})
        created_at = sale.get("created_at")
        if created_at:
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            days_since = (datetime.now(timezone.utc) - created_at).days
        else:
            days_since = 0

        # Check last reminder sent
        last_reminder = await reminder_log_col.find_one(
            {"sale_id": sale["id"]}, {"_id": 0}
        )
        last_reminded = last_reminder.get("sent_at") if last_reminder else None

        result.append({
            "sale_id": sale["id"],
            "client_name": sale.get("client_name", ""),
            "client_email": sale.get("client_email", ""),
            "product_name": product.get("name", "Unknown") if product else "Unknown",
            "fee_amount": sale.get("fee_amount", 0),
            "amount_received": sale.get("amount_received", 0),
            "pending_amount": sale.get("pending_amount", 0),
            "payment_status": sale.get("payment_status", "pending"),
            "days_since_creation": days_since,
            "last_reminder_sent": last_reminded.isoformat() if last_reminded and hasattr(last_reminded, 'isoformat') else str(last_reminded) if last_reminded else None,
            "urgency": "critical" if days_since > 14 else "high" if days_since > 7 else "medium" if days_since > 3 else "low"
        })

    return result


@router.post("/send/{sale_id}")
async def send_reminder(sale_id: str, current_user: dict = Depends(get_current_user)):
    """Manually send a payment reminder for a specific sale"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    sale = await sales_col.find_one({"id": sale_id}, {"_id": 0})
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")

    pending = sale.get("pending_amount", 0)
    if pending <= 0:
        raise HTTPException(status_code=400, detail="No pending amount")

    # Find client user
    client = await users_col.find_one({"email": sale.get("client_email")}, {"_id": 0})

    # Send notification to client
    if client:
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": client["id"],
            "title": "Payment Reminder",
            "message": f"You have a pending payment of ₹{pending:,.0f} for your service. Please complete the payment at your earliest convenience.",
            "type": "payment_reminder",
            "related_id": sale_id,
            "read": False,
            "created_at": datetime.now(timezone.utc)
        })

    # Send email reminder
    from core.email_service import send_email
    await send_email(
        sale.get("client_email", ""),
        "Payment Reminder — LEAMSS Immigration Services",
        f"Dear {sale.get('client_name', 'Client')},\n\nThis is a friendly reminder that you have a pending payment of ₹{pending:,.0f}.\n\nTotal Fee: ₹{sale.get('fee_amount', 0):,.0f}\nAmount Paid: ₹{sale.get('amount_received', 0):,.0f}\nPending: ₹{pending:,.0f}\n\nPlease log in to your LEAMSS portal to complete the payment.\n\nThank you,\nLEAMSS Immigration Services",
        "payment_reminder",
        sale_id
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
        await send_email(
            sale.get("client_email", ""),
            "Payment Reminder — LEAMSS",
            f"Dear {sale.get('client_name', 'Client')}, you have a pending payment of ₹{pending:,.0f}. Please log in to your portal to complete.",
            "payment_reminder", sale["id"]
        )

        await reminder_log_col.update_one(
            {"sale_id": sale["id"]},
            {"$set": {"sent_at": datetime.now(timezone.utc), "sent_by": current_user["id"], "pending_amount": pending},
             "$inc": {"reminder_count": 1}},
            upsert=True
        )
        sent_count += 1

    return {"message": f"Sent {sent_count} payment reminders", "count": sent_count}
