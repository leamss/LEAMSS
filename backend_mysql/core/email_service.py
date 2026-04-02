"""
Email Service for LEAMSS Portal
Handles all email notifications
"""
import os
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Template
from typing import Optional, List
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("GMAIL_EMAIL", "")
SMTP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
SENDER_NAME = os.getenv("SENDER_NAME", "LEAMSS Portal")

# Email Templates
TEMPLATES = {
    "sale_approved": {
        "subject": "🎉 Sale Approved - {{ client_name }}",
        "body": """
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #22c55e;">Sale Approved!</h2>
            <p>Hi {{ partner_name }},</p>
            <p>Great news! Your sale has been approved.</p>
            <div style="background: #f3f4f6; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <p><strong>Client:</strong> {{ client_name }}</p>
                <p><strong>Product:</strong> {{ product_name }}</p>
                <p><strong>Fee Amount:</strong> ₹{{ fee_amount }}</p>
                <p><strong>Your Commission:</strong> ₹{{ commission_amount }}</p>
            </div>
            <p>A case has been created and assigned to a case manager.</p>
            <p>Thank you for your partnership!</p>
            <p>Best regards,<br>LEAMSS Team</p>
        </body>
        </html>
        """
    },
    "sale_rejected": {
        "subject": "❌ Sale Rejected - {{ client_name }}",
        "body": """
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #ef4444;">Sale Rejected</h2>
            <p>Hi {{ partner_name }},</p>
            <p>Unfortunately, your sale has been rejected.</p>
            <div style="background: #f3f4f6; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <p><strong>Client:</strong> {{ client_name }}</p>
                <p><strong>Product:</strong> {{ product_name }}</p>
                <p><strong>Reason:</strong> {{ rejection_reason }}</p>
            </div>
            <p>Please review the feedback and feel free to resubmit.</p>
            <p>Best regards,<br>LEAMSS Team</p>
        </body>
        </html>
        """
    },
    "document_approved": {
        "subject": "✅ Document Approved - {{ document_name }}",
        "body": """
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #22c55e;">Document Approved!</h2>
            <p>Hi {{ client_name }},</p>
            <p>Your document has been approved.</p>
            <div style="background: #f3f4f6; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <p><strong>Document:</strong> {{ document_name }}</p>
                <p><strong>Case:</strong> {{ case_id }}</p>
                <p><strong>Approved by:</strong> {{ reviewer_name }}</p>
            </div>
            <p>You can continue with the next steps in your application.</p>
            <p>Best regards,<br>LEAMSS Team</p>
        </body>
        </html>
        """
    },
    "document_rejected": {
        "subject": "⚠️ Document Requires Attention - {{ document_name }}",
        "body": """
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #f59e0b;">Document Needs Revision</h2>
            <p>Hi {{ client_name }},</p>
            <p>Your document requires some changes.</p>
            <div style="background: #f3f4f6; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <p><strong>Document:</strong> {{ document_name }}</p>
                <p><strong>Case:</strong> {{ case_id }}</p>
                <p><strong>Feedback:</strong> {{ rejection_reason }}</p>
            </div>
            <p>Please upload a revised version at your earliest convenience.</p>
            <p>Best regards,<br>LEAMSS Team</p>
        </body>
        </html>
        """
    },
    "ticket_reply": {
        "subject": "💬 New Reply on Ticket - {{ ticket_subject }}",
        "body": """
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #3b82f6;">New Reply on Your Ticket</h2>
            <p>Hi {{ user_name }},</p>
            <p>You have a new reply on your support ticket.</p>
            <div style="background: #f3f4f6; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <p><strong>Ticket:</strong> {{ ticket_subject }}</p>
                <p><strong>From:</strong> {{ replier_name }}</p>
                <p><strong>Message:</strong></p>
                <p style="background: white; padding: 10px; border-radius: 4px;">{{ message }}</p>
            </div>
            <p>Login to your portal to respond.</p>
            <p>Best regards,<br>LEAMSS Team</p>
        </body>
        </html>
        """
    },
    "case_step_completed": {
        "subject": "🎯 Step Completed - {{ step_name }}",
        "body": """
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #22c55e;">Workflow Step Completed!</h2>
            <p>Hi {{ client_name }},</p>
            <p>A step in your application has been completed.</p>
            <div style="background: #f3f4f6; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <p><strong>Case:</strong> {{ case_id }}</p>
                <p><strong>Completed Step:</strong> {{ step_name }}</p>
                <p><strong>Next Step:</strong> {{ next_step_name }}</p>
                <p><strong>Progress:</strong> {{ progress }}%</p>
            </div>
            <p>Keep up the great progress!</p>
            <p>Best regards,<br>LEAMSS Team</p>
        </body>
        </html>
        """
    },
    "document_expiry_alert": {
        "subject": "⏰ Document Expiring Soon - {{ document_name }}",
        "body": """
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #f59e0b;">Document Expiry Alert</h2>
            <p>Hi {{ client_name }},</p>
            <p>One of your documents is expiring soon.</p>
            <div style="background: #fef3c7; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #f59e0b;">
                <p><strong>Document:</strong> {{ document_name }}</p>
                <p><strong>Case:</strong> {{ case_id }}</p>
                <p><strong>Expiry Date:</strong> {{ expiry_date }}</p>
                <p><strong>Days Remaining:</strong> {{ days_remaining }}</p>
            </div>
            <p>Please upload a renewed document before expiry to avoid delays.</p>
            <p>Best regards,<br>LEAMSS Team</p>
        </body>
        </html>
        """
    },
    "welcome": {
        "subject": "🎉 Welcome to LEAMSS Portal!",
        "body": """
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #3b82f6;">Welcome to LEAMSS Portal!</h2>
            <p>Hi {{ user_name }},</p>
            <p>Your account has been created successfully.</p>
            <div style="background: #f3f4f6; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <p><strong>Email:</strong> {{ email }}</p>
                <p><strong>Role:</strong> {{ role }}</p>
            </div>
            <p>You can now login to your portal and start using our services.</p>
            <p>If you have any questions, feel free to raise a support ticket.</p>
            <p>Best regards,<br>LEAMSS Team</p>
        </body>
        </html>
        """
    }
}


async def send_email(
    to_email: str,
    template_name: str,
    context: dict,
    cc: Optional[List[str]] = None
) -> bool:
    """Send email using template"""
    
    if not SMTP_USER or not SMTP_PASSWORD:
        print(f"Email not configured. Would send '{template_name}' to {to_email}")
        return False
    
    template = TEMPLATES.get(template_name)
    if not template:
        print(f"Template '{template_name}' not found")
        return False
    
    try:
        # Render template
        subject = Template(template["subject"]).render(**context)
        body = Template(template["body"]).render(**context)
        
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{SENDER_NAME} <{SMTP_USER}>"
        msg["To"] = to_email
        if cc:
            msg["Cc"] = ", ".join(cc)
        
        msg.attach(MIMEText(body, "html"))
        
        # Send email
        await aiosmtplib.send(
            msg,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USER,
            password=SMTP_PASSWORD,
            start_tls=True
        )
        
        print(f"Email sent: '{template_name}' to {to_email}")
        return True
        
    except Exception as e:
        print(f"Email failed: {e}")
        return False


# Convenience functions
async def notify_sale_approved(partner_email: str, partner_name: str, client_name: str, 
                                product_name: str, fee_amount: float, commission_amount: float):
    return await send_email(partner_email, "sale_approved", {
        "partner_name": partner_name,
        "client_name": client_name,
        "product_name": product_name,
        "fee_amount": f"{fee_amount:,.2f}",
        "commission_amount": f"{commission_amount:,.2f}"
    })


async def notify_sale_rejected(partner_email: str, partner_name: str, client_name: str,
                                product_name: str, rejection_reason: str):
    return await send_email(partner_email, "sale_rejected", {
        "partner_name": partner_name,
        "client_name": client_name,
        "product_name": product_name,
        "rejection_reason": rejection_reason
    })


async def notify_document_reviewed(client_email: str, client_name: str, document_name: str,
                                    case_id: str, reviewer_name: str, approved: bool, reason: str = ""):
    template = "document_approved" if approved else "document_rejected"
    return await send_email(client_email, template, {
        "client_name": client_name,
        "document_name": document_name,
        "case_id": case_id,
        "reviewer_name": reviewer_name,
        "rejection_reason": reason
    })


async def notify_ticket_reply(user_email: str, user_name: str, ticket_subject: str,
                               replier_name: str, message: str):
    return await send_email(user_email, "ticket_reply", {
        "user_name": user_name,
        "ticket_subject": ticket_subject,
        "replier_name": replier_name,
        "message": message
    })


async def notify_step_completed(client_email: str, client_name: str, case_id: str,
                                 step_name: str, next_step_name: str, progress: int):
    return await send_email(client_email, "case_step_completed", {
        "client_name": client_name,
        "case_id": case_id,
        "step_name": step_name,
        "next_step_name": next_step_name,
        "progress": progress
    })


async def notify_document_expiry(client_email: str, client_name: str, document_name: str,
                                  case_id: str, expiry_date: str, days_remaining: int):
    return await send_email(client_email, "document_expiry_alert", {
        "client_name": client_name,
        "document_name": document_name,
        "case_id": case_id,
        "expiry_date": expiry_date,
        "days_remaining": days_remaining
    })


async def notify_welcome(user_email: str, user_name: str, role: str):
    return await send_email(user_email, "welcome", {
        "user_name": user_name,
        "email": user_email,
        "role": role.replace("_", " ").title()
    })
