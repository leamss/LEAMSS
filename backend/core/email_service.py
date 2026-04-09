"""Email Service — Send transactional emails via Resend, with graceful fallback to in-app notifications"""
import os
import asyncio
import logging
import uuid
from datetime import datetime, timezone

logger = logging.getLogger("email_service")

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")
COMPANY_NAME = "LEAMSS Immigration"

# Check if resend is configured
_resend_available = False
try:
    import resend
    if RESEND_API_KEY and RESEND_API_KEY != "re_your_api_key_here":
        resend.api_key = RESEND_API_KEY
        _resend_available = True
        logger.info("Resend email service configured")
    else:
        logger.warning("No RESEND_API_KEY configured - emails will be logged only")
except ImportError:
    logger.warning("Resend library not installed - emails will be logged only")


def _build_html(title: str, body: str) -> str:
    """Build a branded HTML email template"""
    return f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #ffffff;">
        <div style="background: #2a777a; padding: 24px 32px; text-align: center;">
            <h1 style="color: white; margin: 0; font-size: 22px; font-weight: 700;">{COMPANY_NAME}</h1>
        </div>
        <div style="padding: 32px; background: #ffffff;">
            <h2 style="color: #1a1a1a; font-size: 18px; margin-bottom: 16px;">{title}</h2>
            {body}
        </div>
        <div style="background: #f5f7fa; padding: 20px 32px; text-align: center; border-top: 1px solid #e5e7eb;">
            <p style="color: #9ca3af; font-size: 12px; margin: 0;">This is an automated message from {COMPANY_NAME}.</p>
            <p style="color: #9ca3af; font-size: 12px; margin: 4px 0 0 0;">Please do not reply to this email.</p>
        </div>
    </div>"""


async def send_email(to_email: str, subject: str, title: str, body_html: str) -> dict:
    """Send an email. Falls back to logging if Resend is not configured."""
    from core.database import db
    email_logs_col = db["email_logs"]
    
    full_html = _build_html(title, body_html)
    
    log_entry = {
        "id": str(uuid.uuid4()),
        "to": to_email,
        "subject": subject,
        "status": "pending",
        "sent_at": datetime.now(timezone.utc),
        "provider": "resend" if _resend_available else "mock"
    }
    
    if _resend_available:
        try:
            params = {
                "from": SENDER_EMAIL,
                "to": [to_email],
                "subject": f"[{COMPANY_NAME}] {subject}",
                "html": full_html
            }
            result = await asyncio.to_thread(resend.Emails.send, params)
            log_entry["status"] = "sent"
            log_entry["provider_id"] = result.get("id", "")
            logger.info(f"Email sent to {to_email}: {subject}")
        except Exception as e:
            log_entry["status"] = "failed"
            log_entry["error"] = str(e)
            logger.error(f"Failed to send email to {to_email}: {e}")
    else:
        log_entry["status"] = "mock_sent"
        logger.info(f"[MOCK] Email to {to_email}: {subject}")
    
    await email_logs_col.insert_one(log_entry)
    return log_entry


# Pre-built email templates

async def send_case_update_email(client_email: str, client_name: str, case_id: str, update_message: str):
    """Send case status update to client"""
    body = f"""
    <p style="color: #374151; font-size: 14px; line-height: 1.6;">Dear {client_name},</p>
    <p style="color: #374151; font-size: 14px; line-height: 1.6;">{update_message}</p>
    <div style="background: #f0fdf4; border-left: 4px solid #2a777a; padding: 12px 16px; margin: 16px 0;">
        <p style="color: #2a777a; font-size: 13px; margin: 0;"><strong>Case ID:</strong> {case_id}</p>
    </div>
    <p style="color: #374151; font-size: 14px;">Please log in to your LEAMSS portal to view the details.</p>
    """
    return await send_email(client_email, f"Case Update - {case_id}", "Case Status Update", body)


async def send_document_reminder_email(client_email: str, client_name: str, doc_name: str, expiry_date: str, urgency: str):
    """Send document expiry reminder to client"""
    urgency_color = "#dc2626" if urgency in ["expired", "critical"] else "#f59e0b"
    urgency_text = "EXPIRED" if urgency == "expired" else "Expiring Soon" if urgency == "critical" else "Expiry Reminder"
    body = f"""
    <p style="color: #374151; font-size: 14px; line-height: 1.6;">Dear {client_name},</p>
    <p style="color: #374151; font-size: 14px; line-height: 1.6;">This is a reminder about your document:</p>
    <div style="background: #fef3c7; border-left: 4px solid {urgency_color}; padding: 12px 16px; margin: 16px 0;">
        <p style="color: #92400e; font-size: 13px; margin: 0;"><strong>Document:</strong> {doc_name}</p>
        <p style="color: #92400e; font-size: 13px; margin: 4px 0 0 0;"><strong>Expiry Date:</strong> {expiry_date}</p>
        <p style="color: {urgency_color}; font-size: 13px; margin: 4px 0 0 0; font-weight: bold;">{urgency_text}</p>
    </div>
    <p style="color: #374151; font-size: 14px;">Please take action at your earliest convenience.</p>
    """
    return await send_email(client_email, f"Document {urgency_text}: {doc_name}", "Document Expiry Reminder", body)


async def send_payment_confirmation_email(client_email: str, client_name: str, amount: float, case_id: str):
    """Send payment confirmation to client"""
    body = f"""
    <p style="color: #374151; font-size: 14px; line-height: 1.6;">Dear {client_name},</p>
    <p style="color: #374151; font-size: 14px; line-height: 1.6;">Your payment has been received successfully!</p>
    <div style="background: #f0fdf4; border-left: 4px solid #22c55e; padding: 12px 16px; margin: 16px 0;">
        <p style="color: #166534; font-size: 16px; margin: 0; font-weight: bold;">Amount Paid: INR {amount:,.2f}</p>
        <p style="color: #166534; font-size: 13px; margin: 4px 0 0 0;">Case: {case_id}</p>
    </div>
    <p style="color: #374151; font-size: 14px;">Thank you for your payment. You can view the receipt in your portal.</p>
    """
    return await send_email(client_email, f"Payment Confirmed - INR {amount:,.2f}", "Payment Confirmation", body)


async def send_welcome_email(client_email: str, client_name: str):
    """Send welcome email to new client"""
    body = f"""
    <p style="color: #374151; font-size: 14px; line-height: 1.6;">Dear {client_name},</p>
    <p style="color: #374151; font-size: 14px; line-height: 1.6;">Welcome to <strong>{COMPANY_NAME}</strong>! We are excited to help you with your immigration journey.</p>
    <p style="color: #374151; font-size: 14px; line-height: 1.6;">Your account has been created. You can now log in to your portal to:</p>
    <ul style="color: #374151; font-size: 14px; line-height: 1.8;">
        <li>Track your case progress</li>
        <li>Upload required documents</li>
        <li>Fill your information sheet</li>
        <li>Chat with your case manager</li>
    </ul>
    <p style="color: #374151; font-size: 14px;">If you have any questions, feel free to raise a ticket from your dashboard.</p>
    """
    return await send_email(client_email, "Welcome to LEAMSS Immigration", "Welcome!", body)



async def send_sale_approval_email(client_email: str, client_name: str, product_name: str, case_id: str):
    """Send email when a sale is approved and case is created"""
    body = f"""
    <p style="color: #374151; font-size: 14px; line-height: 1.6;">Dear {client_name},</p>
    <p style="color: #374151; font-size: 14px; line-height: 1.6;">Great news! Your application for <strong>{product_name}</strong> has been approved.</p>
    <div style="background: #f0fdf4; border-left: 4px solid #22c55e; padding: 12px 16px; margin: 16px 0;">
        <p style="color: #166534; font-size: 14px; margin: 0;"><strong>Case ID:</strong> {case_id}</p>
        <p style="color: #166534; font-size: 13px; margin: 4px 0 0 0;">Your case has been created and assigned to a case manager.</p>
    </div>
    <p style="color: #374151; font-size: 14px;">You can now log in to your portal to track your case progress.</p>
    """
    return await send_email(client_email, f"Application Approved - {product_name}", "Application Approved", body)


async def send_sale_rejection_email(client_email: str, client_name: str, product_name: str, rejection_reason: str = ""):
    """Send email when a sale is rejected"""
    reason_text = f'<p style="color: #991b1b; font-size: 13px; margin: 4px 0 0 0;"><strong>Reason:</strong> {rejection_reason}</p>' if rejection_reason else ""
    body = f"""
    <p style="color: #374151; font-size: 14px; line-height: 1.6;">Dear {client_name},</p>
    <p style="color: #374151; font-size: 14px; line-height: 1.6;">We regret to inform you that your application for <strong>{product_name}</strong> could not be processed at this time.</p>
    <div style="background: #fef2f2; border-left: 4px solid #dc2626; padding: 12px 16px; margin: 16px 0;">
        <p style="color: #991b1b; font-size: 14px; margin: 0;">Application Status: Rejected</p>
        {reason_text}
    </div>
    <p style="color: #374151; font-size: 14px;">Please contact us for more information or to discuss alternative options.</p>
    """
    return await send_email(client_email, f"Application Update - {product_name}", "Application Update", body)


async def send_case_step_update_email(client_email: str, client_name: str, case_id: str, step_name: str, status: str):
    """Send email when a case step is updated"""
    status_color = "#22c55e" if status == "completed" else "#f59e0b" if status == "in_progress" else "#6b7280"
    body = f"""
    <p style="color: #374151; font-size: 14px; line-height: 1.6;">Dear {client_name},</p>
    <p style="color: #374151; font-size: 14px; line-height: 1.6;">There's an update on your case:</p>
    <div style="background: #f5f7fa; border-left: 4px solid {status_color}; padding: 12px 16px; margin: 16px 0;">
        <p style="color: #1f2937; font-size: 14px; margin: 0;"><strong>Case:</strong> {case_id}</p>
        <p style="color: #1f2937; font-size: 13px; margin: 4px 0 0 0;"><strong>Step:</strong> {step_name}</p>
        <p style="color: {status_color}; font-size: 13px; margin: 4px 0 0 0; font-weight: bold; text-transform: capitalize;">{status.replace('_', ' ')}</p>
    </div>
    <p style="color: #374151; font-size: 14px;">Log in to your portal to see the details.</p>
    """
    return await send_email(client_email, f"Case Update - {step_name}", "Case Progress Update", body)


async def send_document_review_email(client_email: str, client_name: str, doc_name: str, status: str, notes: str = ""):
    """Send email when a document is reviewed"""
    is_approved = status == "approved"
    status_color = "#22c55e" if is_approved else "#dc2626"
    notes_text = f'<p style="color: #6b7280; font-size: 13px; margin: 8px 0 0 0;"><strong>Notes:</strong> {notes}</p>' if notes else ""
    body = f"""
    <p style="color: #374151; font-size: 14px; line-height: 1.6;">Dear {client_name},</p>
    <p style="color: #374151; font-size: 14px; line-height: 1.6;">Your document has been reviewed:</p>
    <div style="background: {'#f0fdf4' if is_approved else '#fef2f2'}; border-left: 4px solid {status_color}; padding: 12px 16px; margin: 16px 0;">
        <p style="color: #1f2937; font-size: 14px; margin: 0;"><strong>Document:</strong> {doc_name}</p>
        <p style="color: {status_color}; font-size: 14px; margin: 4px 0 0 0; font-weight: bold;">{'Approved' if is_approved else 'Rejected'}</p>
        {notes_text}
    </div>
    <p style="color: #374151; font-size: 14px;">{'You can proceed to the next step.' if is_approved else 'Please re-upload the document with the required corrections.'}</p>
    """
    return await send_email(client_email, f"Document {'Approved' if is_approved else 'Rejected'} - {doc_name}", "Document Review", body)


async def send_ticket_update_email(user_email: str, user_name: str, ticket_subject: str, message: str):
    """Send email when a ticket receives a reply"""
    body = f"""
    <p style="color: #374151; font-size: 14px; line-height: 1.6;">Dear {user_name},</p>
    <p style="color: #374151; font-size: 14px; line-height: 1.6;">Your support ticket has received a reply:</p>
    <div style="background: #eff6ff; border-left: 4px solid #3b82f6; padding: 12px 16px; margin: 16px 0;">
        <p style="color: #1e40af; font-size: 14px; margin: 0;"><strong>Ticket:</strong> {ticket_subject}</p>
        <p style="color: #374151; font-size: 13px; margin: 8px 0 0 0;">{message[:200]}{'...' if len(message) > 200 else ''}</p>
    </div>
    <p style="color: #374151; font-size: 14px;">Log in to your portal to view the full conversation.</p>
    """
    return await send_email(user_email, f"Ticket Update - {ticket_subject}", "Support Ticket Update", body)
