"""
Document Expiry Service for LEAMSS Portal
Handles checking for expiring documents and sending notifications
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional

from core.database import db
from services.notification_service import create_notification

logger = logging.getLogger(__name__)

# Reminder thresholds in days
REMINDER_THRESHOLDS = [30, 14, 7, 3, 1]


async def check_expiring_documents() -> Dict[str, int]:
    """
    Check all documents for upcoming expirations and send notifications.
    Returns statistics about notifications sent.
    """
    stats = {
        "documents_checked": 0,
        "expiring_soon": 0,
        "notifications_sent": 0,
        "emails_sent": 0
    }
    
    now = datetime.now(timezone.utc)
    
    try:
        # Get all cases with their documents
        cases = await db.cases.find({}, {"_id": 0}).to_list(10000)
        
        for case in cases:
            case_id = case.get("id")
            client_id = case.get("client_id")
            client_name = case.get("client_name", "Client")
            case_manager_id = case.get("case_manager_id")
            
            if not client_id or not case_manager_id:
                continue
            
            # Get client and case manager info for email
            client = await db.users.find_one({"id": client_id}, {"_id": 0, "email": 1, "name": 1})
            case_manager = await db.users.find_one({"id": case_manager_id}, {"_id": 0, "email": 1, "name": 1})
            
            if not client:
                continue
                
            client_email = client.get("email")
            cm_email = case_manager.get("email") if case_manager else None
            cm_name = case_manager.get("name", "Case Manager") if case_manager else None
            
            # Get documents for this case
            documents = await db.documents.find(
                {"case_id": case_id},
                {"_id": 0}
            ).to_list(1000)
            
            for doc in documents:
                stats["documents_checked"] += 1
                
                expiry_date_str = doc.get("expiry_date")
                if not expiry_date_str:
                    continue
                
                try:
                    # Parse expiry date
                    expiry_date = datetime.fromisoformat(expiry_date_str.replace("Z", "+00:00"))
                    if expiry_date.tzinfo is None:
                        expiry_date = expiry_date.replace(tzinfo=timezone.utc)
                    
                    days_until_expiry = (expiry_date - now).days
                    
                    # Check if this falls within any reminder threshold
                    for threshold in REMINDER_THRESHOLDS:
                        if days_until_expiry == threshold:
                            stats["expiring_soon"] += 1
                            
                            doc_name = doc.get("filename") or doc.get("document_type", "Document")
                            doc_id = doc.get("id")
                            
                            # Check if we already sent a reminder for this threshold
                            existing_reminder = await db.expiry_reminders.find_one({
                                "document_id": doc_id,
                                "days_before": threshold
                            })
                            
                            if existing_reminder:
                                continue  # Already sent this reminder
                            
                            # Send notification to client
                            await send_expiry_notification(
                                user_id=client_id,
                                client_name=client_name,
                                client_email=client_email,
                                document_name=doc_name,
                                expiry_date=expiry_date_str,
                                days_remaining=days_until_expiry,
                                case_id=case.get("case_id", case_id)
                            )
                            stats["notifications_sent"] += 1
                            
                            # Also notify case manager
                            if case_manager_id and cm_email:
                                await send_expiry_notification_to_cm(
                                    user_id=case_manager_id,
                                    cm_name=cm_name,
                                    cm_email=cm_email,
                                    client_name=client_name,
                                    document_name=doc_name,
                                    expiry_date=expiry_date_str,
                                    days_remaining=days_until_expiry,
                                    case_id=case.get("case_id", case_id)
                                )
                                stats["notifications_sent"] += 1
                            
                            # Record that we sent this reminder
                            await db.expiry_reminders.insert_one({
                                "document_id": doc_id,
                                "case_id": case_id,
                                "days_before": threshold,
                                "sent_at": now.isoformat()
                            })
                            
                            break  # Only send one reminder per document per check
                            
                except Exception as e:
                    logger.error(f"Error processing document {doc.get('id')}: {e}")
                    continue
        
        logger.info(f"Expiry check complete: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"Error checking expiring documents: {e}")
        return stats


async def send_expiry_notification(
    user_id: str,
    client_name: str,
    client_email: str,
    document_name: str,
    expiry_date: str,
    days_remaining: int,
    case_id: str
):
    """Send expiry notification to client via in-app + email"""
    
    urgency = "urgent" if days_remaining <= 3 else "warning"
    
    # Create in-app notification
    await create_notification(
        user_id=user_id,
        title=f"⚠️ Document Expiring Soon - {document_name}",
        message=f"Your document '{document_name}' will expire in {days_remaining} day(s). Please upload a renewed document.",
        notification_type="doc_expiry",
        related_id=case_id
    )
    
    # Send email notification
    try:
        from email_service import email_service
        if email_service.is_configured():
            await send_expiry_email_to_client(
                email_service,
                client_email,
                client_name,
                document_name,
                expiry_date,
                days_remaining,
                case_id
            )
    except Exception as e:
        logger.error(f"Failed to send expiry email to client: {e}")


async def send_expiry_notification_to_cm(
    user_id: str,
    cm_name: str,
    cm_email: str,
    client_name: str,
    document_name: str,
    expiry_date: str,
    days_remaining: int,
    case_id: str
):
    """Send expiry notification to case manager via in-app + email"""
    
    # Create in-app notification
    await create_notification(
        user_id=user_id,
        title=f"Client Document Expiring - {client_name}",
        message=f"Document '{document_name}' for {client_name} will expire in {days_remaining} day(s).",
        notification_type="doc_expiry_cm",
        related_id=case_id
    )
    
    # Send email notification
    try:
        from email_service import email_service
        if email_service.is_configured():
            await send_expiry_email_to_cm(
                email_service,
                cm_email,
                cm_name,
                client_name,
                document_name,
                expiry_date,
                days_remaining,
                case_id
            )
    except Exception as e:
        logger.error(f"Failed to send expiry email to CM: {e}")


async def send_expiry_email_to_client(
    email_service,
    to_email: str,
    client_name: str,
    document_name: str,
    expiry_date: str,
    days_remaining: int,
    case_id: str
):
    """Send document expiry email to client"""
    
    urgency_color = "#d81f26" if days_remaining <= 3 else "#f7620b"
    urgency_text = "URGENT" if days_remaining <= 3 else "Action Required"
    
    subject = f"⚠️ {urgency_text}: Document Expiring in {days_remaining} Day(s) - {document_name}"
    
    content = f"""
    <h2>Document Expiring Soon</h2>
    <p>Hello {client_name},</p>
    
    <div class="warning-box" style="border-color: {urgency_color};">
        <p><strong>{urgency_text}:</strong> One of your documents is about to expire.</p>
    </div>
    
    <table style="width: 100%; border-collapse: collapse; margin: 20px 0; background: #fef3c7; border-radius: 8px;">
        <tr>
            <td style="padding: 15px; border-bottom: 1px solid #fcd34d;"><strong>Document:</strong></td>
            <td style="padding: 15px; border-bottom: 1px solid #fcd34d; font-weight: bold;">{document_name}</td>
        </tr>
        <tr>
            <td style="padding: 15px; border-bottom: 1px solid #fcd34d;"><strong>Expiry Date:</strong></td>
            <td style="padding: 15px; border-bottom: 1px solid #fcd34d; color: {urgency_color}; font-weight: bold;">{expiry_date[:10]}</td>
        </tr>
        <tr>
            <td style="padding: 15px; border-bottom: 1px solid #fcd34d;"><strong>Days Remaining:</strong></td>
            <td style="padding: 15px; border-bottom: 1px solid #fcd34d;">
                <span style="background: {urgency_color}; color: white; padding: 4px 12px; border-radius: 20px; font-weight: bold;">
                    {days_remaining} day(s)
                </span>
            </td>
        </tr>
        <tr>
            <td style="padding: 15px;"><strong>Case ID:</strong></td>
            <td style="padding: 15px;">{case_id}</td>
        </tr>
    </table>
    
    <p><strong>What you need to do:</strong></p>
    <ol>
        <li>Obtain a renewed/updated version of the document</li>
        <li>Login to your LEAMSS Portal</li>
        <li>Upload the new document before the expiry date</li>
    </ol>
    
    <p style="text-align: center;">
        <a href="#" class="button" style="background-color: {urgency_color};">Upload Renewed Document</a>
    </p>
    
    <p><strong>Why is this important?</strong></p>
    <p>Expired documents can delay your immigration application. Please ensure all your documents remain valid throughout the process.</p>
    
    <p>If you have any questions, please contact your Case Manager through the portal.</p>
    """
    
    await email_service.send_email(to_email, subject, email_service.get_base_template(content))


async def send_expiry_email_to_cm(
    email_service,
    to_email: str,
    cm_name: str,
    client_name: str,
    document_name: str,
    expiry_date: str,
    days_remaining: int,
    case_id: str
):
    """Send document expiry alert email to case manager"""
    
    urgency_color = "#d81f26" if days_remaining <= 3 else "#f7620b"
    urgency_text = "URGENT" if days_remaining <= 3 else "Attention Required"
    
    subject = f"📋 Client Document Expiring - {client_name} ({days_remaining} days)"
    
    content = f"""
    <h2>Client Document Expiring</h2>
    <p>Hello {cm_name},</p>
    
    <div class="warning-box" style="border-color: {urgency_color};">
        <p><strong>{urgency_text}:</strong> A document for one of your clients is about to expire.</p>
    </div>
    
    <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
        <tr>
            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb; background: #f9fafb;"><strong>Client:</strong></td>
            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb;">{client_name}</td>
        </tr>
        <tr>
            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb; background: #f9fafb;"><strong>Document:</strong></td>
            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb;">{document_name}</td>
        </tr>
        <tr>
            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb; background: #f9fafb;"><strong>Expiry Date:</strong></td>
            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb; color: {urgency_color}; font-weight: bold;">{expiry_date[:10]}</td>
        </tr>
        <tr>
            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb; background: #f9fafb;"><strong>Days Remaining:</strong></td>
            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb;">
                <span style="background: {urgency_color}; color: white; padding: 4px 12px; border-radius: 20px; font-weight: bold;">
                    {days_remaining} day(s)
                </span>
            </td>
        </tr>
        <tr>
            <td style="padding: 12px; background: #f9fafb;"><strong>Case ID:</strong></td>
            <td style="padding: 12px;">{case_id}</td>
        </tr>
    </table>
    
    <p><strong>Recommended Actions:</strong></p>
    <ul>
        <li>The client has been automatically notified via email and in-app notification</li>
        <li>Consider sending a personal follow-up if the document is critical</li>
        <li>Use the portal ticket system if you need to request additional documents</li>
    </ul>
    
    <p style="text-align: center;">
        <a href="#" class="button">View Client Case</a>
    </p>
    """
    
    await email_service.send_email(to_email, subject, email_service.get_base_template(content))


async def get_expiring_documents_summary() -> List[Dict]:
    """Get a summary of all documents expiring within the next 30 days"""
    now = datetime.now(timezone.utc)
    threshold_date = (now + timedelta(days=30)).isoformat()
    
    expiring_docs = []
    
    cases = await db.cases.find({}, {"_id": 0}).to_list(10000)
    
    for case in cases:
        documents = await db.documents.find(
            {"case_id": case.get("id")},
            {"_id": 0}
        ).to_list(1000)
        
        for doc in documents:
            expiry_date_str = doc.get("expiry_date")
            if not expiry_date_str:
                continue
            
            try:
                expiry_date = datetime.fromisoformat(expiry_date_str.replace("Z", "+00:00"))
                if expiry_date.tzinfo is None:
                    expiry_date = expiry_date.replace(tzinfo=timezone.utc)
                
                if now < expiry_date <= datetime.fromisoformat(threshold_date):
                    days_remaining = (expiry_date - now).days
                    expiring_docs.append({
                        "document_id": doc.get("id"),
                        "document_name": doc.get("filename") or doc.get("document_type"),
                        "case_id": case.get("case_id"),
                        "client_name": case.get("client_name"),
                        "client_id": case.get("client_id"),
                        "case_manager_id": case.get("case_manager_id"),
                        "expiry_date": expiry_date_str,
                        "days_remaining": days_remaining
                    })
            except:
                continue
    
    # Sort by days remaining (most urgent first)
    expiring_docs.sort(key=lambda x: x["days_remaining"])
    
    return expiring_docs
