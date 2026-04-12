"""Email Digest Router — Weekly/On-demand admin summary email"""
import uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional
from core.database import (
    db, sales_col, cases_col, users_col, tickets_col,
    refunds_col, pre_assessments_col, audit_logs_col, notifications_col
)
from core.auth import get_current_user

router = APIRouter(prefix="/email-digest", tags=["Email Digest"])

settings_col = db["settings"]


class DigestSettings(BaseModel):
    frequency: str = "weekly"  # daily, weekly, monthly
    recipients: list = []
    enabled: bool = True


@router.get("/preview")
async def preview_digest(current_user: dict = Depends(get_current_user)):
    """Preview the email digest content (same data that would be emailed)"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return await _build_digest_data()


@router.post("/send-now")
async def send_digest_now(current_user: dict = Depends(get_current_user)):
    """Send the digest email immediately to all admins"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    digest = await _build_digest_data()

    # Build HTML email body
    html_body = _build_digest_html(digest)

    # Get all admin emails
    admins = await users_col.find({"role": "admin", "status": "active"}, {"_id": 0, "email": 1, "name": 1}).to_list(20)

    from core.email_service import send_email
    sent_count = 0
    for admin in admins:
        try:
            await send_email(admin["email"], "Weekly Stats Digest", "LEAMSS Weekly Digest", html_body)
            sent_count += 1
        except Exception as e:
            print(f"Failed to send digest to {admin['email']}: {e}")

    # Log it
    await audit_logs_col.insert_one({
        "id": str(uuid.uuid4()), "user_id": current_user["id"],
        "action": "digest_sent", "entity_type": "system",
        "entity_id": "digest", "new_value": {"recipients": sent_count},
        "created_at": datetime.now(timezone.utc)
    })

    return {"message": f"Digest sent to {sent_count} admin(s)", "recipients": sent_count}


@router.get("/settings")
async def get_digest_settings(current_user: dict = Depends(get_current_user)):
    """Get digest settings"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    settings = await settings_col.find_one({"type": "email_digest"}, {"_id": 0})
    if not settings:
        return {"frequency": "weekly", "recipients": [], "enabled": True, "last_sent": None}
    return settings


@router.put("/settings")
async def update_digest_settings(data: DigestSettings, current_user: dict = Depends(get_current_user)):
    """Update digest settings"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    await settings_col.update_one(
        {"type": "email_digest"},
        {"$set": {
            "type": "email_digest",
            "frequency": data.frequency,
            "recipients": data.recipients,
            "enabled": data.enabled,
            "updated_by": current_user["id"],
            "updated_at": datetime.now(timezone.utc),
        }},
        upsert=True
    )
    return {"message": "Digest settings updated"}


async def _build_digest_data():
    """Build the digest data payload"""
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    # Revenue stats
    approved_sales = await sales_col.find({"status": "approved"}, {"_id": 0}).to_list(10000)
    total_revenue = sum(s.get("fee_amount", 0) or 0 for s in approved_sales)
    total_received = sum(s.get("amount_received", 0) or 0 for s in approved_sales)
    total_pending = total_revenue - total_received
    total_commission = sum(s.get("commission_amount", 0) or 0 for s in approved_sales)

    # This week's new sales
    all_sales = await sales_col.find({}, {"_id": 0}).to_list(10000)
    week_sales = [s for s in all_sales if _is_recent(s.get("created_at"), week_ago)]
    week_revenue = sum(s.get("fee_amount", 0) or 0 for s in week_sales if s.get("status") == "approved")

    # Pending approvals
    pending_sales = await sales_col.count_documents({"status": "pending"})
    pending_pa = await pre_assessments_col.count_documents({"stage": {"$in": ["under_review", "documents_submitted"]}})

    # Cases
    total_cases = await cases_col.count_documents({})
    active_cases = await cases_col.count_documents({"status": {"$in": ["active", "in_progress"]}})
    completed_cases = await cases_col.count_documents({"status": "completed"})
    completion_rate = round((completed_cases / total_cases * 100), 1) if total_cases > 0 else 0

    # Tickets
    open_tickets = await tickets_col.count_documents({"status": {"$in": ["open"]}})
    urgent_tickets = await tickets_col.count_documents({"status": "open", "priority": {"$in": ["urgent", "high"]}})

    # Refunds
    all_refunds = await refunds_col.find({}, {"_id": 0, "amount": 1}).to_list(5000)
    total_refunded = sum(r.get("amount", 0) for r in all_refunds)

    # Top partner this week
    partner_sales = {}
    for s in week_sales:
        pid = s.get("partner_id", "")
        if pid and s.get("status") == "approved":
            partner_sales[pid] = partner_sales.get(pid, 0) + (s.get("fee_amount", 0) or 0)
    top_partner_id = max(partner_sales, key=partner_sales.get) if partner_sales else None
    top_partner = None
    if top_partner_id:
        top_partner_doc = await users_col.find_one({"id": top_partner_id}, {"_id": 0, "name": 1})
        if top_partner_doc:
            top_partner = {"name": top_partner_doc["name"], "revenue": partner_sales[top_partner_id]}

    # PA stats
    pa_total = await pre_assessments_col.count_documents({})
    pa_approved = await pre_assessments_col.count_documents({"stage": {"$in": ["approved", "proposal_sent", "case_created"]}})

    return {
        "generated_at": now.isoformat(),
        "period": "Last 7 days",
        "revenue": {
            "total": round(total_revenue, 2),
            "received": round(total_received, 2),
            "pending": round(total_pending, 2),
            "commission": round(total_commission, 2),
            "refunded": round(total_refunded, 2),
            "net": round(total_received - total_refunded, 2),
            "week_new_sales": len(week_sales),
            "week_revenue": round(week_revenue, 2),
        },
        "approvals": {
            "pending_sales": pending_sales,
            "pending_pre_assessments": pending_pa,
            "total_pending": pending_sales + pending_pa,
        },
        "cases": {
            "total": total_cases,
            "active": active_cases,
            "completed": completed_cases,
            "completion_rate": completion_rate,
        },
        "tickets": {
            "open": open_tickets,
            "urgent": urgent_tickets,
        },
        "pre_assessments": {
            "total": pa_total,
            "approved": pa_approved,
        },
        "top_partner": top_partner,
    }


def _is_recent(created_at, since):
    """Check if a date is recent"""
    if isinstance(created_at, datetime):
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        return created_at >= since
    if isinstance(created_at, str):
        try:
            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            return dt >= since
        except (ValueError, TypeError):
            return False
    return False


def _build_digest_html(digest):
    """Build HTML email body from digest data"""
    r = digest["revenue"]
    a = digest["approvals"]
    c = digest["cases"]
    t = digest["tickets"]
    tp = digest.get("top_partner")

    top_partner_html = ""
    if tp:
        top_partner_html = f"""
        <div style="background: #fef3c7; border-left: 4px solid #f59e0b; padding: 12px 16px; margin: 16px 0;">
            <p style="color: #92400e; font-size: 13px; margin: 0; font-weight: bold;">Top Partner This Week</p>
            <p style="color: #92400e; font-size: 16px; margin: 4px 0 0 0;">{tp['name']} — ₹{tp['revenue']:,.0f}</p>
        </div>"""

    return f"""
    <p style="color: #374151; font-size: 14px; line-height: 1.6;">Here's your weekly summary:</p>

    <div style="background: #f0fdf4; border-radius: 8px; padding: 16px; margin: 16px 0;">
        <h3 style="color: #166534; margin: 0 0 12px 0; font-size: 15px;">Revenue Overview</h3>
        <table style="width: 100%; font-size: 13px; color: #374151;">
            <tr><td>Total Revenue</td><td style="text-align: right; font-weight: bold;">₹{r['total']:,.0f}</td></tr>
            <tr><td>Collected</td><td style="text-align: right; font-weight: bold; color: #16a34a;">₹{r['received']:,.0f}</td></tr>
            <tr><td>Pending</td><td style="text-align: right; font-weight: bold; color: #f59e0b;">₹{r['pending']:,.0f}</td></tr>
            <tr><td>Commission</td><td style="text-align: right;">₹{r['commission']:,.0f}</td></tr>
            <tr><td>Net Revenue</td><td style="text-align: right; font-weight: bold; color: #2a777a;">₹{r['net']:,.0f}</td></tr>
        </table>
        <p style="font-size: 12px; color: #6b7280; margin: 8px 0 0 0;">This week: {r['week_new_sales']} new sales, ₹{r['week_revenue']:,.0f} revenue</p>
    </div>

    <div style="display: flex; gap: 12px; margin: 16px 0;">
        <div style="flex: 1; background: #fef2f2; border-radius: 8px; padding: 12px; text-align: center;">
            <p style="font-size: 24px; font-weight: bold; color: #dc2626; margin: 0;">{a['total_pending']}</p>
            <p style="font-size: 11px; color: #991b1b; margin: 4px 0 0 0;">Pending Approvals</p>
        </div>
        <div style="flex: 1; background: #eff6ff; border-radius: 8px; padding: 12px; text-align: center;">
            <p style="font-size: 24px; font-weight: bold; color: #2563eb; margin: 0;">{c['active']}</p>
            <p style="font-size: 11px; color: #1e40af; margin: 4px 0 0 0;">Active Cases</p>
        </div>
        <div style="flex: 1; background: #faf5ff; border-radius: 8px; padding: 12px; text-align: center;">
            <p style="font-size: 24px; font-weight: bold; color: #7c3aed; margin: 0;">{t['open']}</p>
            <p style="font-size: 11px; color: #5b21b6; margin: 4px 0 0 0;">Open Tickets</p>
        </div>
    </div>

    <table style="width: 100%; font-size: 13px; color: #374151; margin: 16px 0; border-collapse: collapse;">
        <tr style="border-bottom: 1px solid #e5e7eb;"><td style="padding: 8px 0;">Cases Completion Rate</td><td style="text-align: right; font-weight: bold;">{c['completion_rate']}%</td></tr>
        <tr style="border-bottom: 1px solid #e5e7eb;"><td style="padding: 8px 0;">Urgent Tickets</td><td style="text-align: right; font-weight: bold; color: #dc2626;">{t['urgent']}</td></tr>
        <tr><td style="padding: 8px 0;">Pending Sales / PA</td><td style="text-align: right; font-weight: bold;">{a['pending_sales']} / {a['pending_pre_assessments']}</td></tr>
    </table>

    {top_partner_html}

    <p style="color: #9ca3af; font-size: 12px; margin: 16px 0 0 0;">Generated: {digest['generated_at'][:19]}</p>
    """
