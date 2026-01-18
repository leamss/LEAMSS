"""
Email Service Module for LEAMSS Portal
Uses Gmail SMTP for sending transactional emails
"""
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Gmail SMTP Configuration
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

class EmailService:
    def __init__(self):
        self.smtp_email = os.environ.get("GMAIL_EMAIL")
        self.smtp_password = os.environ.get("GMAIL_APP_PASSWORD")
        self.sender_name = os.environ.get("SENDER_NAME", "LEAMSS Portal")
    
    def is_configured(self) -> bool:
        return bool(self.smtp_email and self.smtp_password)
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        plain_content: Optional[str] = None
    ) -> bool:
        """Send an email using Gmail SMTP"""
        if not self.is_configured():
            logger.warning("Email service not configured - skipping email send")
            return False
        
        try:
            message = MIMEMultipart("alternative")
            message["From"] = f"{self.sender_name} <{self.smtp_email}>"
            message["To"] = to_email
            message["Subject"] = subject
            
            if plain_content:
                message.attach(MIMEText(plain_content, "plain"))
            message.attach(MIMEText(html_content, "html"))
            
            await aiosmtplib.send(
                message,
                hostname=SMTP_HOST,
                port=SMTP_PORT,
                start_tls=True,
                username=self.smtp_email,
                password=self.smtp_password
            )
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False
    
    # ==================== Email Templates ====================
    
    def get_base_template(self, content: str) -> str:
        """Base HTML template with LEAMSS branding"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f5f7fa; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; }}
                .header {{ background: linear-gradient(135deg, #2a777a 0%, #236466 100%); padding: 30px; text-align: center; }}
                .header h1 {{ color: white; margin: 0; font-size: 24px; }}
                .content {{ padding: 30px; }}
                .button {{ display: inline-block; padding: 12px 24px; background-color: #f7620b; color: white; text-decoration: none; border-radius: 6px; font-weight: 600; margin: 20px 0; }}
                .button:hover {{ background-color: #e55a09; }}
                .footer {{ background: #1e293b; color: #94a3b8; padding: 20px; text-align: center; font-size: 12px; }}
                .info-box {{ background: #f0fdfa; border-left: 4px solid #2a777a; padding: 15px; margin: 20px 0; }}
                .warning-box {{ background: #fff7ed; border-left: 4px solid #f7620b; padding: 15px; margin: 20px 0; }}
                .success-box {{ background: #f0fdf4; border-left: 4px solid #22c55e; padding: 15px; margin: 20px 0; }}
                .status-badge {{ display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; }}
                .status-approved {{ background: #dcfce7; color: #166534; }}
                .status-rejected {{ background: #fee2e2; color: #991b1b; }}
                .status-pending {{ background: #fef3c7; color: #92400e; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>LEAMSS Immigration Services</h1>
                </div>
                <div class="content">
                    {content}
                </div>
                <div class="footer">
                    <p>© 2025 LEAMSS Immigration Services. All rights reserved.</p>
                    <p>This is an automated notification. Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    # ==================== Client Notifications ====================
    
    async def send_welcome_email(self, to_email: str, client_name: str, temp_password: str, case_id: str):
        """Send welcome email to new client with login credentials"""
        subject = "Welcome to LEAMSS Portal - Your Account is Ready!"
        
        content = f"""
        <h2>Welcome, {client_name}!</h2>
        <p>Your immigration case has been approved and your LEAMSS Portal account is now active.</p>
        
        <div class="info-box">
            <strong>Your Case ID:</strong> {case_id}<br>
            <strong>Login Email:</strong> {to_email}<br>
            <strong>Temporary Password:</strong> {temp_password}
        </div>
        
        <p>Please login to your portal to:</p>
        <ul>
            <li>Track your case progress</li>
            <li>Upload required documents</li>
            <li>Communicate with your Case Manager</li>
        </ul>
        
        <p style="text-align: center;">
            <a href="#" class="button">Login to Portal</a>
        </p>
        
        <p><strong>Important:</strong> Please change your password after your first login for security.</p>
        """
        
        return await self.send_email(to_email, subject, self.get_base_template(content))
    
    async def send_document_approved_email(self, to_email: str, client_name: str, document_name: str, step_name: str, case_id: str):
        """Notify client that their document has been approved"""
        subject = f"Document Approved - {document_name}"
        
        content = f"""
        <h2>Document Approved</h2>
        <p>Hello {client_name},</p>
        
        <div class="success-box">
            <p><strong>Great news!</strong> Your document has been reviewed and approved.</p>
        </div>
        
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;"><strong>Document:</strong></td>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">{document_name}</td>
            </tr>
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;"><strong>Step:</strong></td>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">{step_name}</td>
            </tr>
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;"><strong>Case ID:</strong></td>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">{case_id}</td>
            </tr>
            <tr>
                <td style="padding: 10px;"><strong>Status:</strong></td>
                <td style="padding: 10px;"><span class="status-badge status-approved">Approved</span></td>
            </tr>
        </table>
        
        <p>Your Case Manager will continue processing your application. You'll be notified when there are further updates.</p>
        """
        
        return await self.send_email(to_email, subject, self.get_base_template(content))
    
    async def send_document_rejected_email(self, to_email: str, client_name: str, document_name: str, reason: str, case_id: str):
        """Notify client that their document has been rejected"""
        subject = "Action Required - Document Needs Resubmission"
        
        content = f"""
        <h2>Document Requires Resubmission</h2>
        <p>Hello {client_name},</p>
        
        <div class="warning-box">
            <p><strong>Attention Required:</strong> Your document needs to be resubmitted.</p>
        </div>
        
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;"><strong>Document:</strong></td>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">{document_name}</td>
            </tr>
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;"><strong>Case ID:</strong></td>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">{case_id}</td>
            </tr>
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;"><strong>Status:</strong></td>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;"><span class="status-badge status-rejected">Rejected</span></td>
            </tr>
            <tr>
                <td style="padding: 10px;"><strong>Reason:</strong></td>
                <td style="padding: 10px;">{reason or 'Please contact your Case Manager for details.'}</td>
            </tr>
        </table>
        
        <p style="text-align: center;">
            <a href="#" class="button">Upload New Document</a>
        </p>
        
        <p>If you have questions, please contact your Case Manager through the portal.</p>
        """
        
        return await self.send_email(to_email, subject, self.get_base_template(content))
    
    async def send_step_completed_email(self, to_email: str, client_name: str, step_name: str, next_step: str, case_id: str):
        """Notify client that a workflow step has been completed"""
        subject = "Case Progress Update - Step Completed!"
        
        content = f"""
        <h2>Congratulations! Step Completed</h2>
        <p>Hello {client_name},</p>
        
        <div class="success-box">
            <p><strong>Great progress!</strong> The following step has been completed for your case:</p>
            <p style="font-size: 18px; margin: 10px 0;"><strong>{step_name}</strong></p>
        </div>
        
        <p><strong>Case ID:</strong> {case_id}</p>
        
        {f'<div class="info-box"><strong>Next Step:</strong> {next_step}<br>Please login to your portal to see what documents or actions are required.</div>' if next_step else '<div class="success-box"><strong>All steps completed!</strong> Your case is being finalized.</div>'}
        
        <p style="text-align: center;">
            <a href="#" class="button">View Case Progress</a>
        </p>
        """
        
        return await self.send_email(to_email, subject, self.get_base_template(content))
    
    async def send_additional_doc_request_email(self, to_email: str, client_name: str, document_name: str, description: str, due_date: str, case_id: str):
        """Notify client that an additional document is required"""
        subject = f"Additional Document Required - {document_name}"
        
        content = f"""
        <h2>Additional Document Required</h2>
        <p>Hello {client_name},</p>
        
        <div class="warning-box">
            <p>Your Case Manager has requested an additional document for your case.</p>
        </div>
        
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;"><strong>Document Required:</strong></td>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">{document_name}</td>
            </tr>
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;"><strong>Description:</strong></td>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">{description}</td>
            </tr>
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;"><strong>Case ID:</strong></td>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">{case_id}</td>
            </tr>
            {f'<tr><td style="padding: 10px;"><strong>Due Date:</strong></td><td style="padding: 10px;"><span style="color: #d81f26; font-weight: bold;">{due_date}</span></td></tr>' if due_date else ''}
        </table>
        
        <p style="text-align: center;">
            <a href="#" class="button">Upload Document Now</a>
        </p>
        """
        
        return await self.send_email(to_email, subject, self.get_base_template(content))
    
    # ==================== Partner Notifications ====================
    
    async def send_sale_approved_email(self, to_email: str, partner_name: str, client_name: str, product_name: str, commission: float):
        """Notify partner that their sale has been approved"""
        subject = f"Sale Approved - {client_name}"
        
        content = f"""
        <h2>Sale Approved!</h2>
        <p>Hello {partner_name},</p>
        
        <div class="success-box">
            <p><strong>Congratulations!</strong> Your sale has been approved by the admin.</p>
        </div>
        
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;"><strong>Client:</strong></td>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">{client_name}</td>
            </tr>
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;"><strong>Product:</strong></td>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">{product_name}</td>
            </tr>
            <tr>
                <td style="padding: 10px;"><strong>Your Commission:</strong></td>
                <td style="padding: 10px; color: #2a777a; font-weight: bold; font-size: 18px;">${commission:.2f}</td>
            </tr>
        </table>
        
        <p>The client has been notified and their case file is now active. A Case Manager has been assigned to handle the application process.</p>
        """
        
        return await self.send_email(to_email, subject, self.get_base_template(content))
    
    async def send_sale_rejected_email(self, to_email: str, partner_name: str, client_name: str, product_name: str):
        """Notify partner that their sale has been rejected"""
        subject = f"Sale Not Approved - {client_name}"
        
        content = f"""
        <h2>Sale Not Approved</h2>
        <p>Hello {partner_name},</p>
        
        <div class="warning-box">
            <p>Unfortunately, the following sale was not approved.</p>
        </div>
        
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;"><strong>Client:</strong></td>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">{client_name}</td>
            </tr>
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;"><strong>Product:</strong></td>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">{product_name}</td>
            </tr>
            <tr>
                <td style="padding: 10px;"><strong>Status:</strong></td>
                <td style="padding: 10px;"><span class="status-badge status-rejected">Rejected</span></td>
            </tr>
        </table>
        
        <p>Please contact the admin for more information about why this sale was not approved.</p>
        """
        
        return await self.send_email(to_email, subject, self.get_base_template(content))

# Global email service instance
email_service = EmailService()
