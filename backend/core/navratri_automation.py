"""Navratri Campaign Automation Engine — Single Source of Truth.

Handles:
1. Lead classification (Paid vs Unpaid; Resume Received vs Resume Pending)
2. Automated & On-Demand Email + WhatsApp dispatch for Resume Upload Links
3. Automated & On-Demand Email + WhatsApp dispatch for Payment Links
4. Transition state machine when payment is completed or resume is uploaded
5. De-duplication and communication logging
"""
from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from core.database import db
from core.gmail_dwd import send as gmail_send, default_sender as gmail_default_sender
from core.report_email import build_resume_request_email, SANS, SERIF, TEAL, GOLD, SAFFRON, GREEN, ORANGE, INK, SLATE, BORDER
from core.whatsapp_service import send_whatsapp_text, normalize_phone_number

logger = logging.getLogger("navratri_automation")
leads_col = db["leads"]

APP_BASE_URL = os.environ.get("APP_BASE_URL", "https://app.leamss.com").rstrip("/")
WEBSITE_OFFER_URL = os.environ.get("WEBSITE_OFFER_URL", "https://leamss.com/navratri-offers").rstrip("/")

NAVRATRI_QUERY = {
    "$or": [
        {"is_navratri": True},
        {"source": {"$regex": "navratri|website", "$options": "i"}},
        {"tags": {"$in": ["Navratri Offer 2026", "Website Registration", "Navratri Offer", "Payment Success", "Payment Failed"]}},
        {"tags": {"$regex": "navratri|website registration|navratri offer", "$options": "i"}},
        {"service_interested": {"$regex": "navratri|special offer", "$options": "i"}},
        {"utm_campaign": {"$regex": "navratri", "$options": "i"}},
        {"unique_id": {"$regex": "^NN", "$options": "i"}},
        {"marketing_source": {"$regex": "navratri|website", "$options": "i"}},
    ]
}


def is_lead_paid(lead: Dict[str, Any]) -> bool:
    """Checks if a lead is marked as paid based on cPanel MySQL status and CRM payment fields."""
    status = str(lead.get("payment_status") or "").strip().lower()
    # Non-paid statuses from cPanel MySQL take absolute precedence
    if status in ("failed", "pending", "unpaid", "cancelled", "refunded"):
        return False
    if status in ("success", "paid", "completed", "captured"):
        return True
    if str(lead.get("stage") or "").strip().lower() == "payment_done":
        return True
    if "Payment Success" in (lead.get("tags") or []):
        return True
    if lead.get("paid_at") and status not in ("failed", "pending"):
        return True
    return False


def has_lead_resume(lead: Dict[str, Any]) -> bool:
    """Checks if a resume is on file for this lead."""
    return bool(
        lead.get("resume_file_id")
        or lead.get("resume_url")
        or lead.get("resume_path")
        or lead.get("resume_link")
        or lead.get("resume_uploaded") is True
    )


def is_lead_navratri(lead: Dict[str, Any]) -> bool:
    """Checks if a lead belongs to the Navratri Offer campaign."""
    if lead.get("is_navratri") is True:
        return True
    src = str(lead.get("source") or "")
    svc = str(lead.get("service_interested") or "")
    uid = str(lead.get("unique_id") or "")
    cmp = str(lead.get("utm_campaign") or "")
    mkt = str(lead.get("marketing_source") or "")
    tags = [str(t) for t in (lead.get("tags") or [])]
    
    if re.search(r"navratri", src, re.I) or re.search(r"navratri", svc, re.I) or re.search(r"navratri", cmp, re.I) or re.search(r"navratri", mkt, re.I):
        return True
    if uid.upper().startswith("NN"):
        return True
    if any("navratri" in t.lower() or "website registration" in t.lower() for t in tags):
        return True
    return False


def get_navratri_category(lead: Dict[str, Any]) -> str:
    """Classify lead into exact segregation category:
    - 'paid_resume_received' (Ready for Bulk Pre-Assessment & Report Gen)
    - 'paid_resume_pending'  (Paid, but awaiting Resume Upload)
    - 'unpaid'               (Unpaid / Payment Pending)
    """
    paid = is_lead_paid(lead)
    resume = has_lead_resume(lead)
    if paid and resume:
        return "paid_resume_received"
    if paid and not resume:
        return "paid_resume_pending"
    return "unpaid"


def get_resume_upload_url(lead: Dict[str, Any]) -> str:
    """Generate public secure upload URL for the lead."""
    token = lead.get("unique_id") or lead.get("id") or lead.get("phone") or ""
    return f"{APP_BASE_URL}/upload-resume/{token}"


def get_payment_url(lead: Dict[str, Any]) -> str:
    """Generate payment link for the lead."""
    token = lead.get("unique_id") or lead.get("id") or ""
    if lead.get("payment_link"):
        return lead["payment_link"]
    if token:
        return f"{WEBSITE_OFFER_URL}?ref={token}"
    return WEBSITE_OFFER_URL


def build_navratri_payment_email(lead: Dict[str, Any], payment_url: str) -> Tuple[str, str, str]:
    """Generates branded Navratri Offer payment reminder email."""
    name = (lead.get("name") or "Applicant").strip()
    uid = lead.get("unique_id") or ""
    
    subject = f"Complete your Navratri Special Offer Registration — Australia PR Assessment ({name})"
    
    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f6f8f7;font-family:{SANS};">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f6f8f7;padding:24px 0;"><tr><td align="center">
    <table role="presentation" width="620" cellpadding="0" cellspacing="0" style="width:620px;max-width:96%;background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 6px 24px rgba(18,67,59,0.12);">
      <tr><td style="height:5px;background:{SAFFRON};font-size:0;line-height:0;">&nbsp;</td></tr>
      <tr><td style="height:5px;background:#ffffff;font-size:0;line-height:0;">&nbsp;</td></tr>
      <tr><td style="height:5px;background:{GREEN};font-size:0;line-height:0;">&nbsp;</td></tr>
      <tr><td style="background:{TEAL};padding:26px 34px;">
        <div style="color:{GOLD};font-size:11px;font-weight:800;letter-spacing:1.5px;text-transform:uppercase;">✨ FESTIVE SPECIAL OFFER</div>
        <div style="color:#ffffff;font-family:{SERIF};font-size:22px;font-weight:800;margin-top:4px;">LEAMSS · Australia PR Pre-Assessment</div>
      </td></tr>
      <tr><td style="padding:32px 34px;">
        <p style="margin:0 0 14px;color:{INK};font-size:16px;font-weight:700;">Dear {name},</p>
        <p style="margin:0 0 14px;color:{SLATE};font-size:14px;line-height:1.75;">
          Thank you for registering for the <strong>LEAMSS Navratri Special Offer</strong> {f'({uid})' if uid else ''}. 
          To confirm your assessment slot and initiate your personalized Australia PR evaluation report, please complete your registration payment.
        </p>
        
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#FFFDF5;border:2px solid {GOLD};border-radius:12px;padding:20px;margin:22px 0;text-align:center;">
          <tr><td>
            <div style="color:{TEAL};font-size:15px;font-weight:800;letter-spacing:0.5px;">NAVRATRI SPECIAL ENROLMENT</div>
            <div style="color:{ORANGE};font-size:28px;font-weight:900;margin:8px 0 4px;">Exclusive Festive Fee</div>
            <div style="color:{SLATE};font-size:12px;">Includes Full ANZSCO Evaluation + Points Calculation + Strategic Pathway Report</div>
            <table role="presentation" cellpadding="0" cellspacing="0" style="margin:18px auto 6px;"><tr>
              <td style="background:{ORANGE};border-radius:28px;">
                <a href="{payment_url}" style="display:inline-block;padding:14px 38px;color:#fff;text-decoration:none;font-size:15px;font-weight:800;">
                  💳&nbsp; Complete Payment Now
                </a>
              </td>
            </tr></table>
          </td></tr>
        </table>

        <div style="color:{SLATE};font-size:13px;line-height:1.7;">
          <strong>What happens once paid:</strong>
          <ol style="margin:6px 0 0;padding-left:20px;">
            <li>Your status will immediately update to <strong>Paid</strong> in our system.</li>
            <li>Our migration experts will review your credentials and generate your comprehensive Pre-Assessment Report.</li>
            <li>You will receive your official report via Email and WhatsApp.</li>
          </ol>
        </div>

        <p style="margin:26px 0 0;color:{SLATE};font-size:13px;line-height:1.75;">
          Warm Regards,<br>
          <strong>LEAMSS Admissions &amp; Evaluation Team</strong><br>
          <span style="font-size:11px;color:#94a3b8;">Ladhani Education &amp; Migration Services Pvt. Ltd. · info@leamss.com · +91 77188 82427</span>
        </p>
      </td></tr>
    </table>
  </td></tr></table>
</body></html>"""

    plain = f"""Dear {name},

Thank you for registering for the LEAMSS Navratri Special Offer {f'({uid})' if uid else ''}.

To confirm your Australia PR Pre-Assessment and receive your strategic evaluation report, please complete your registration payment at:
{payment_url}

What happens after payment:
1. Your registration is instantly confirmed as Paid.
2. Our migration specialists evaluate your profile and generate your Pre-Assessment Report.
3. Your detailed report will be delivered to your Email and WhatsApp.

Warm Regards,
LEAMSS Admissions Team
info@leamss.com | +91 77188 82427 | www.leamss.com
"""
    return subject, html, plain


async def send_navratri_resume_request(
    lead: Dict[str, Any],
    custom_message: Optional[str] = None,
    sender_name: str = "LEAMSS",
) -> Dict[str, Any]:
    """Sends Resume Upload Link to a Paid or Unpaid Navratri lead via Email + WhatsApp."""
    lead_id = lead.get("id")
    name = (lead.get("name") or "Applicant").strip()
    email = str(lead.get("email") or "").strip()
    phone = str(lead.get("phone") or "").strip()
    upload_url = get_resume_upload_url(lead)
    now = datetime.now(timezone.utc)
    
    results = {
        "lead_id": lead_id,
        "name": name,
        "email_sent": False,
        "whatsapp_sent": False,
        "upload_url": upload_url,
        "errors": []
    }

    # 1. Send Email if email exists
    if email and "@" in email:
        try:
            settings_doc = await db["email_settings"].find_one({"id": "global"}) or {}
            subject, html, plain = build_resume_request_email(
                settings_doc,
                client_name=name,
                upload_url=upload_url,
                sender_name=sender_name
            )
            sender_email = gmail_default_sender() or os.environ.get("GMAIL_EMAIL") or "info@leamss.com"
            await gmail_send(
                sender_email=sender_email,
                recipient=email,
                subject=subject,
                html=html,
                plain=plain,
                sender_name="LEAMSS Migration Team"
            )
            results["email_sent"] = True
        except Exception as e_email:
            logger.error("Failed to send resume request email to %s: %s", email, e_email)
            results["errors"].append(f"Email error: {str(e_email)}")

    # 2. Send WhatsApp if phone exists
    clean_phone = normalize_phone_number(phone)
    if clean_phone:
        try:
            wa_text = (
                f"🌟 *LEAMSS Navratri Offer — Action Needed*\n\n"
                f"Hi {name},\n"
                f"Thank you for your registration with LEAMSS! To complete your *Australia PR Pre-Assessment Report*, our migration team needs your latest resume / CV.\n\n"
                f"📄 *Upload your resume securely in 1 minute:*\n"
                f"{upload_url}\n\n"
                f"_(No login or password required. Simply click the link and upload your PDF or Word document.)_\n\n"
                f"Once uploaded, our team will analyze your profile and prepare your Pre-Assessment Report.\n\n"
                f"— *LEAMSS Migration Team*"
            )
            await send_whatsapp_text(to_phone=clean_phone, text=wa_text)
            results["whatsapp_sent"] = True
        except Exception as e_wa:
            logger.error("Failed to send resume request WhatsApp to %s: %s", phone, e_wa)
            results["errors"].append(f"WhatsApp error: {str(e_wa)}")

    # 3. Log to lead notes and update timestamp
    note_text = f"Auto/Admin sent Resume Upload Link via {'Email & WhatsApp' if results['email_sent'] and results['whatsapp_sent'] else 'Email' if results['email_sent'] else 'WhatsApp' if results['whatsapp_sent'] else 'Failed Dispatch'}: {upload_url}"
    await leads_col.update_one(
        {"id": lead_id},
        {
            "$set": {
                "last_resume_request_sent_at": now,
                "resume_upload_url": upload_url,
                "updated_at": now,
            },
            "$push": {
                "notes": {
                    "text": note_text,
                    "created_at": now.isoformat(),
                    "author": "System Automation",
                }
            }
        }
    )

    return results


async def send_navratri_payment_link(
    lead: Dict[str, Any],
    payment_url_override: Optional[str] = None,
) -> Dict[str, Any]:
    """Sends Navratri Offer Payment Link to an unpaid lead via Email + WhatsApp."""
    lead_id = lead.get("id")
    name = (lead.get("name") or "Applicant").strip()
    email = str(lead.get("email") or "").strip()
    phone = str(lead.get("phone") or "").strip()
    payment_url = payment_url_override or get_payment_url(lead)
    now = datetime.now(timezone.utc)

    results = {
        "lead_id": lead_id,
        "name": name,
        "email_sent": False,
        "whatsapp_sent": False,
        "payment_url": payment_url,
        "errors": []
    }

    # 1. Send Email
    if email and "@" in email:
        try:
            subject, html, plain = build_navratri_payment_email(lead, payment_url)
            sender_email = gmail_default_sender() or os.environ.get("GMAIL_EMAIL") or "info@leamss.com"
            await gmail_send(
                sender_email=sender_email,
                recipient=email,
                subject=subject,
                html=html,
                plain=plain,
                sender_name="LEAMSS Admissions Team"
            )
            results["email_sent"] = True
        except Exception as e_email:
            logger.error("Failed to send payment link email to %s: %s", email, e_email)
            results["errors"].append(f"Email error: {str(e_email)}")

    # 2. Send WhatsApp
    clean_phone = normalize_phone_number(phone)
    if clean_phone:
        try:
            wa_text = (
                f"✨ *LEAMSS Navratri Special Offer — Payment Link*\n\n"
                f"Dear {name},\n"
                f"Complete your registration for the *LEAMSS Navratri Special Offer* and get your personalized Australia PR Pre-Assessment Report.\n\n"
                f"💳 *Complete Payment Securely:*\n"
                f"{payment_url}\n\n"
                f"Once payment is completed, your profile will be immediately queued for evaluation by our expert migration team.\n\n"
                f"— *LEAMSS Global Education & Migration*"
            )
            await send_whatsapp_text(to_phone=clean_phone, text=wa_text)
            results["whatsapp_sent"] = True
        except Exception as e_wa:
            logger.error("Failed to send payment link WhatsApp to %s: %s", phone, e_wa)
            results["errors"].append(f"WhatsApp error: {str(e_wa)}")

    # 3. Log to lead notes
    note_text = f"Sent Navratri Offer Payment Link via {'Email & WhatsApp' if results['email_sent'] and results['whatsapp_sent'] else 'Email' if results['email_sent'] else 'WhatsApp' if results['whatsapp_sent'] else 'Failed Dispatch'}: {payment_url}"
    await leads_col.update_one(
        {"id": lead_id},
        {
            "$set": {
                "last_payment_link_sent_at": now,
                "payment_link": payment_url,
                "updated_at": now,
            },
            "$push": {
                "notes": {
                    "text": note_text,
                    "created_at": now.isoformat(),
                    "author": "System Automation",
                }
            }
        }
    )

    return results


async def mark_lead_paid_and_transition(
    lead_id: str,
    payment_mode: Optional[str] = "upi",
    payment_amount: Optional[float] = 1.0,
    razorpay_payment_id: Optional[str] = None,
    razorpay_order_id: Optional[str] = None,
    trigger_auto_resume_request: bool = True,
) -> Dict[str, Any]:
    """Updates lead payment status to 'success' and applies state transition logic.
    
    - If resume is on file -> moves to 'paid_resume_received' (Ready for Bulk Pre-Assessment).
    - If resume is NOT on file -> moves to 'paid_resume_pending' and auto-dispatches resume upload link via Email + WhatsApp.
    """
    lead = await leads_col.find_one({"id": lead_id})
    if not lead:
        raise ValueError("Lead not found")

    now = datetime.now(timezone.utc)
    update_data = {
        "payment_status": "success",
        "stage": "payment_done",
        "paid_at": now.isoformat(),
        "payment_mode": payment_mode or lead.get("payment_mode") or "online",
        "payment_amount": payment_amount if payment_amount is not None else (lead.get("payment_amount") or 1.0),
        "report_generated": False,
        "report_status": "pending",
        "latest_report_snapshot_id": None,
        "assessment_report_id": None,
        "updated_at": now,
    }
    if razorpay_payment_id:
        update_data["razorpay_payment_id"] = razorpay_payment_id
    if razorpay_order_id:
        update_data["razorpay_order_id"] = razorpay_order_id

    tags = list(set((lead.get("tags") or []) + ["Payment Success"]))
    update_data["tags"] = tags

    await leads_col.update_one({"id": lead_id}, {"$set": update_data})
    updated_lead = {**lead, **update_data}

    has_resume = has_lead_resume(updated_lead)
    resume_req_res = None

    if not has_resume and trigger_auto_resume_request:
        resume_req_res = await send_navratri_resume_request(updated_lead)

    category = "paid_resume_received" if has_resume else "paid_resume_pending"

    return {
        "status": "success",
        "lead_id": lead_id,
        "payment_status": "success",
        "has_resume": has_resume,
        "category": category,
        "next_step": "bulk_pre_assessment" if has_resume else "awaiting_resume_upload",
        "resume_request_sent": bool(resume_req_res and (resume_req_res.get("email_sent") or resume_req_res.get("whatsapp_sent"))),
    }
