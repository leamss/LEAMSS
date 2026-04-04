"""Email Service — Mocked email notifications (logs to DB + console)"""
import uuid
from datetime import datetime, timezone
from core.database import db

email_logs_col = db["email_logs"]


async def send_email(to_email: str, subject: str, body: str, 
                     template: str = "general", related_id: str = None):
    """Send an email (mocked — logs to DB instead of sending)"""
    log = {
        "id": str(uuid.uuid4()),
        "to": to_email,
        "subject": subject,
        "body": body,
        "template": template,
        "related_id": related_id,
        "status": "sent",
        "sent_at": datetime.now(timezone.utc)
    }
    await email_logs_col.insert_one(log)
    print(f"[EMAIL MOCK] To: {to_email} | Subject: {subject}")
    return log


async def send_sale_approval_email(client_email: str, client_name: str, 
                                    product_name: str, sale_id: str):
    """Notify client their sale has been approved and a case is created"""
    subject = f"LEAMSS — Your {product_name} application has been approved!"
    body = (
        f"Dear {client_name},\n\n"
        f"Great news! Your application for {product_name} has been approved.\n"
        f"A case has been created and assigned to a case manager who will guide you "
        f"through the process.\n\n"
        f"Please log in to your LEAMSS Portal to view your case details and "
        f"upload the required documents.\n\n"
        f"Best regards,\nLEAMSS Immigration Services"
    )
    return await send_email(client_email, subject, body, "sale_approved", sale_id)


async def send_sale_rejection_email(client_email: str, client_name: str,
                                     product_name: str, reason: str, sale_id: str):
    """Notify client their sale has been rejected"""
    subject = f"LEAMSS — Update on your {product_name} application"
    body = (
        f"Dear {client_name},\n\n"
        f"We regret to inform you that your application for {product_name} "
        f"could not be approved at this time.\n\n"
        f"Reason: {reason}\n\n"
        f"Please contact your partner or raise a support ticket for more details.\n\n"
        f"Best regards,\nLEAMSS Immigration Services"
    )
    return await send_email(client_email, subject, body, "sale_rejected", sale_id)


async def send_document_review_email(client_email: str, client_name: str,
                                      doc_name: str, status: str, comment: str = ""):
    """Notify client about document review result"""
    status_text = "approved" if status == "approved" else "requires revision"
    subject = f"LEAMSS — Document {status_text}: {doc_name}"
    body = (
        f"Dear {client_name},\n\n"
        f"Your document '{doc_name}' has been reviewed and {status_text}.\n"
    )
    if comment:
        body += f"\nReviewer comments: {comment}\n"
    if status != "approved":
        body += "\nPlease log in to upload a revised version.\n"
    body += "\nBest regards,\nLEAMSS Immigration Services"
    return await send_email(client_email, subject, body, "document_review")


async def send_ticket_update_email(user_email: str, user_name: str,
                                    ticket_subject: str, message: str, ticket_id: str):
    """Notify user about a ticket update"""
    subject = f"LEAMSS — Ticket Update: {ticket_subject}"
    body = (
        f"Dear {user_name},\n\n"
        f"There is a new update on your support ticket: '{ticket_subject}'\n\n"
        f"Message: {message}\n\n"
        f"Please log in to view the full conversation.\n\n"
        f"Best regards,\nLEAMSS Immigration Services"
    )
    return await send_email(user_email, subject, body, "ticket_update", ticket_id)


async def send_case_step_update_email(client_email: str, client_name: str,
                                       case_id: str, step_name: str, status: str):
    """Notify client about case step progression"""
    subject = f"LEAMSS — Case Update: {step_name} {status}"
    body = (
        f"Dear {client_name},\n\n"
        f"Your case step '{step_name}' has been updated to: {status}.\n\n"
        f"Please log in to your LEAMSS Portal to view the latest status "
        f"and any pending actions.\n\n"
        f"Best regards,\nLEAMSS Immigration Services"
    )
    return await send_email(client_email, subject, body, "case_step_update", case_id)
