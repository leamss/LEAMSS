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
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from core.database import db
from core.gmail_dwd import send as gmail_send, default_sender as gmail_default_sender
from core.report_email import build_resume_request_email, SANS, SERIF, TEAL, GOLD, SAFFRON, GREEN, ORANGE, INK, SLATE, BORDER
from core.whatsapp_service import send_whatsapp_text, normalize_phone_number

logger = logging.getLogger("navratri_automation")
leads_col = db["leads"]

APP_BASE_URL = os.environ.get("APP_BASE_URL", "https://app.leamss.com").rstrip("/")
WEBSITE_OFFER_URL = os.environ.get("WEBSITE_OFFER_URL", "https://pages.razorpay.com/pl_TZSVimtLKxHnHx/view").rstrip("/")

NAVRATRI_QUERY = {
    "$or": [
        {"is_navratri": True},
        {"source": {"$regex": "navratri|website|staging|direct|form|portal|cpanel|lead", "$options": "i"}},
        {"tags": {"$in": ["Navratri Offer 2026", "Website Registration", "Navratri Offer", "Payment Success", "Payment Failed"]}},
        {"tags": {"$regex": "navratri|website registration|navratri offer|lead", "$options": "i"}},
        {"service_interested": {"$regex": "navratri|special offer|migration|enquiry|assessment", "$options": "i"}},
        {"utm_campaign": {"$regex": "navratri|offers|special", "$options": "i"}},
        {"unique_id": {"$regex": "^NN|^LD|[0-9]{6}", "$options": "i"}},
        {"marketing_source": {"$regex": "navratri|website|direct", "$options": "i"}},
        {"id": {"$exists": True}}
    ]
}


def is_lead_paid(lead: Dict[str, Any]) -> bool:
    """Checks if a lead is marked as paid based on cPanel MySQL status and CRM payment fields."""
    if not lead:
        return False
    if lead.get("is_paid") is True:
        return True
    status = str(lead.get("payment_status") or "").strip().lower()
    if status in ("success", "paid", "completed", "captured"):
        return True
    if status in ("failed", "pending", "unpaid", "cancelled", "refunded"):
        return False
    if lead.get("paid_at") and (lead.get("payment_amount") or 0) > 0:
        return True
    if lead.get("razorpay_payment_id") or lead.get("payment_id") or lead.get("txnid"):
        return True
    tags = [str(t).lower() for t in (lead.get("tags") or [])]
    if any(t in ("payment success", "paid", "navratri paid") for t in tags):
        return True
    return False


def is_valid_resume_path(val: Any) -> bool:
    if not val:
        return False
    s = str(val).strip()
    if not s or s.lower() in ("null", "undefined", "none", "n/a", "no", "false", "0", "nan", "[]", "{}"):
        return False
    if s.rstrip("/") in ("http://leamss.com", "https://leamss.com", "http://app.leamss.com", "https://app.leamss.com", "https://leamss.com/uploads", "https://leamss.com/uploads/resumes", "uploads", "uploads/resumes"):
        return False
    has_ext = any(s.lower().endswith(ext) or f"{ext}?" in s.lower() for ext in (".pdf", ".docx", ".doc", ".png", ".jpg", ".jpeg", ".webp"))
    is_gridfs_oid = len(s) == 24 and all(c in "0123456789abcdefABCDEF" for c in s)
    is_gridfs_route = "/cockpit/resume/" in s or "/upload-resume/" in s or "drive.google.com" in s or "cloudinary" in s or "s3" in s
    return bool(has_ext or is_gridfs_oid or is_gridfs_route)


def has_lead_resume(lead: Dict[str, Any]) -> bool:
    """Checks if a genuine resume file is on file for this lead."""
    for field in ("resume_file_id", "resume_url", "resume_path", "resume_link"):
        val = lead.get(field)
        if val and is_valid_resume_path(val):
            return True
    return False


def is_lead_navratri(lead: Dict[str, Any]) -> bool:
    """Checks if a lead belongs to the Navratri Offer campaign."""
    return True


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


def get_payment_url(lead: Optional[Dict[str, Any]] = None) -> str:
    """Generate payment link for the lead."""
    if lead and lead.get("payment_link") and "razorpay.com" in str(lead.get("payment_link")):
        return lead["payment_link"]
    return "https://pages.razorpay.com/pl_TZSVimtLKxHnHx/view"


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
          <strong>LEAMSS Immigration Expert</strong><br>
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
LEAMSS Immigration Expert
info@leamss.com | +91 77188 82427 | www.leamss.com
"""
    return subject, html, plain


async def send_navratri_resume_request(
    lead: Dict[str, Any],
    custom_message: Optional[str] = None,
    sender_name: str = "LEAMSS",
) -> Dict[str, Any]:
    """Sends Resume Upload Link to a Paid or Unpaid Navratri lead via Email + WhatsApp."""
    p = lead.get("parsed") or {}
    lead_id = lead.get("id") or lead.get("unique_id") or str(lead.get("_id") or "")
    name = (lead.get("name") or lead.get("client_name") or p.get("name") or "Applicant").strip()
    email = str(lead.get("email") or lead.get("client_email") or p.get("email") or "").strip()
    phone = str(lead.get("phone") or lead.get("client_phone") or lead.get("mobile") or p.get("phone") or "").strip()
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
            from routers.whatsapp_chat import is_in_24h_window, set_pending_flow, record_chat_message
            from core.whatsapp_service import get_whatsapp_config, send_whatsapp_interactive_buttons

            cfg = await get_whatsapp_config()
            has_active_session = await is_in_24h_window(clean_phone)

            direct_wa_text = custom_message or (
                f"🌟 *LEAMSS Navratri Offer — Action Needed*\n\n"
                f"Hi {name},\n"
                f"Thank you for your registration with LEAMSS! To complete your *Australia PR Pre-Assessment Report*, our migration team needs your latest resume / CV.\n\n"
                f"📄 *Upload your resume securely in 1 minute:*\n"
                f"{upload_url}\n\n"
                f"_(No login or password required. Simply click the link and upload your PDF or Word document.)_\n\n"
                f"Once uploaded, our team will analyze your profile and prepare your Pre-Assessment Report.\n\n"
                f"— *LEAMSS Migration Team*"
            )

            sent_direct = False
            if has_active_session:
                try:
                    await send_whatsapp_text(to_phone=clean_phone, text=direct_wa_text, client_name=name)
                    await record_chat_message(
                        phone=clean_phone,
                        text=direct_wa_text,
                        direction="outbound",
                        sender_type="system",
                        sender_name="LEAMSS Migration Team",
                        client_name=name,
                        client_email=email,
                        status="sent",
                    )
                    sent_direct = True
                    results["whatsapp_sent"] = True
                except Exception as e_direct:
                    err_s = str(e_direct)
                    if "24-hour" in err_s or "63016" in err_s or "Outside" in err_s:
                        logger.info("Resume direct send failed outside 24h for +%s, fallback to cold template: %s", clean_phone, err_s)
                        has_active_session = False
                    else:
                        raise e_direct

            if not has_active_session and not sent_direct:
                upload_token = str(lead.get("unique_id") or lead.get("id") or "LEAMSS-PR")[:25]
                await set_pending_flow(
                    clean_phone,
                    flow="resume_request",
                    client_name=name,
                    extra_data={
                        "resume_url": upload_url,
                        "selected_msg": direct_wa_text,
                        "lead_id": lead_id,
                    },
                )
                if cfg.get("provider") == "twilio" or cfg.get("is_twilio"):
                    try:
                        # 1. Primary Approved UTILITY CTA Template (resume_upload_request_v3) with Upload Resume button
                        await send_whatsapp_text(
                            to_phone=clean_phone,
                            text=direct_wa_text,
                            client_name=name,
                            content_sid="HX2cfa67abc427c31cc5a93e5c9ddea0fd",
                            content_variables={"1": name, "2": upload_token},
                        )
                    except Exception as e_res_1:
                        logger.warning("Resume template HX2cfa dispatch failed: %s; trying HXf719...", e_res_1)
                        try:
                            # 2. Approved UTILITY CTA Template v2
                            await send_whatsapp_text(
                                to_phone=clean_phone,
                                text=direct_wa_text,
                                client_name=name,
                                content_sid="HXf719452bc0939b9cad2d509bb95af6cc",
                                content_variables={"1": name, "2": upload_token},
                            )
                        except Exception as e_res_2:
                            logger.warning("Resume template HXf719 failed: %s; trying text util...", e_res_2)
                            try:
                                await send_whatsapp_text(
                                    to_phone=clean_phone,
                                    text=f"Please upload your resume: https://app.leamss.com/upload-resume/{upload_token}",
                                    client_name=name,
                                    content_sid="HXecdec14cc27a0857c49274c92f26d366",
                                    content_variables={"1": name, "2": f"https://app.leamss.com/upload-resume/{upload_token}"},
                                )
                            except Exception:
                                await send_whatsapp_text(to_phone=clean_phone, text=direct_wa_text, client_name=name)
                else:
                    await send_whatsapp_interactive_buttons(
                        to_phone=clean_phone,
                        body_text=f"Hi {name}, our migration specialists are ready to prepare your Australia PR Pre-Assessment Report. Please click below to upload your resume.",
                        buttons=[
                            {"id": "btn_upload_resume", "title": "Upload Resume"},
                            {"id": "btn_not_now", "title": "Not Now"},
                        ],
                        header_text="LEAMSS — Resume Request",
                        footer_text="Ladhani Education & Migration Services",
                        client_name=name,
                    )

                await record_chat_message(
                    phone=clean_phone,
                    text=f"[Resume Request Notice Dispatched]\nRef: {upload_token}\nButton: YES, UPLOAD RESUME",
                    direction="outbound",
                    sender_type="system",
                    sender_name="LEAMSS Migration Team",
                    client_name=name,
                    client_email=email,
                    status="sent",
                )
                results["whatsapp_sent"] = True

        except Exception as e_wa:
            logger.error("Failed to send resume request WhatsApp to %s: %s", phone, e_wa)
            results["errors"].append(f"WhatsApp error: {str(e_wa)}")

    # 3. Log to lead notes and update timestamp
    note_text = f"Auto/Admin sent Resume Upload Link via {'Email & WhatsApp' if results['email_sent'] and results['whatsapp_sent'] else 'Email' if results['email_sent'] else 'WhatsApp' if results['whatsapp_sent'] else 'Failed Dispatch'}: {upload_url}"
    update_q: Dict[str, Any] = {"$or": [{"id": lead_id}, {"unique_id": lead_id}]}
    if lead.get("_id"):
        update_q["$or"].append({"_id": lead["_id"]})
    await leads_col.update_one(
        update_q,
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
    """Sends Navratri Offer Payment Link to an unpaid lead via Email + WhatsApp.
    
    Checks 24-hour customer window for WhatsApp:
    - If 24h window is OPEN: dispatches direct payment link.
    - If 24h window is CLOSED (cold lead): sets pending 'payment_link' flow and dispatches
      Meta broadcast/interactive button or Twilio approved quick-reply template ("Your payment is pending...").
      When recipient replies or clicks 'Yes, Send Link', the direct payment link is automatically delivered.
    """
    p = lead.get("parsed") or {}
    lead_id = lead.get("id") or lead.get("unique_id") or str(lead.get("_id") or "")
    name = (lead.get("name") or lead.get("client_name") or p.get("name") or "Applicant").strip()
    email = str(lead.get("email") or lead.get("client_email") or p.get("email") or "").strip()
    phone = str(lead.get("phone") or lead.get("client_phone") or lead.get("mobile") or p.get("phone") or "").strip()
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
                sender_name="LEAMSS Immigration Expert"
            )
            results["email_sent"] = True
            logger.info("Payment link email sent successfully to %s", email)
        except Exception as e_email:
            logger.error("Failed to send payment link email to %s: %s", email, e_email)
            results["errors"].append(f"Email error: {str(e_email)}")

    # 2. Send WhatsApp
    clean_phone = normalize_phone_number(phone)
    if clean_phone:
        try:
            from routers.whatsapp_chat import is_in_24h_window, set_pending_flow, record_chat_message
            from core.whatsapp_service import send_whatsapp_interactive_buttons, get_whatsapp_config

            cfg = await get_whatsapp_config()
            ref_id = str(lead.get("unique_id") or lead.get("id") or "LEAMSS-PR")[:25]

            direct_payment_text = (
                f"Hello {name},\n\n"
                f"Thank you for consulting *LEAMSS Immigration Services*. 🇦🇺\n\n"
                f"Your *Australia PR Pre-Assessment* registration is currently pending.\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🎉 *HAPPY NAVRATRI SPECIAL OFFER*\n"
                f"Complete your registration for just *₹999*!\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"💳 *Payment Link:*\n"
                f"{payment_url}\n\n"
                f"✨ *What happens next:*\n"
                f"• Your profile will be reviewed by senior migration specialists.\n"
                f"• Comprehensive Points Assessment (189 / 190 / 491) will be prepared.\n"
                f"• Complete strategic pathway report delivered to your WhatsApp & Email.\n\n"
                f"Please complete your payment and reply to this message if you need any assistance.\n\n"
                f"🌐 *Website:* https://leamss.com\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Warm Regards,\n"
                f"*LEAMSS Immigration Expert*"
            )

            has_active_session = await is_in_24h_window(clean_phone)
            sent_direct = False

            # If inside 24h active customer window, send rich festive payment text directly
            if has_active_session:
                try:
                    await send_whatsapp_text(to_phone=clean_phone, text=direct_payment_text, client_name=name)
                    await record_chat_message(
                        phone=clean_phone,
                        text=direct_payment_text,
                        direction="outbound",
                        sender_type="system",
                        sender_name="LEAMSS Immigration Expert",
                        client_name=name,
                        client_email=email,
                        status="sent",
                    )
                    sent_direct = True
                    results["whatsapp_sent"] = True
                except Exception as e_direct:
                    logger.info("Direct WhatsApp send failed for +%s: %s. Falling back to template...", clean_phone, e_direct)
                    sent_direct = False

            # If outside 24h window (cold lead), dispatch verified Twilio Approved Template with payment link
            if not has_active_session or not sent_direct:
                await set_pending_flow(
                    clean_phone,
                    flow="payment_link",
                    client_name=name,
                    extra_data={
                        "payment_url": payment_url,
                        "lead_id": lead_id,
                        "unique_id": lead.get("unique_id"),
                        "name": name,
                        "email": email,
                    },
                )

                cold_body_text = (
                    f"Hello {name},\n\n"
                    f"Thank you for consulting *LEAMSS Immigration Services*. 🇦🇺\n\n"
                    f"Your *Australia PR Pre-Assessment* registration is currently pending.\n\n"
                    f"🎉 *HAPPY NAVRATRI SPECIAL OFFER* — Complete your registration for just *₹999*!\n\n"
                    f"💳 *Payment Link:*\n"
                    f"{payment_url}\n\n"
                    f"Once payment is completed, your Australia PR Pre-Assessment will be processed.\n\n"
                    f"🌐 *Website:* https://leamss.com\n\n"
                    f"Warm Regards,\n"
                    f"*LEAMSS Immigration Expert*"
                )

                if cfg.get("provider") == "twilio" or cfg.get("is_twilio"):
                    sent_tmpl = False
                    # 1. Primary Approved UTILITY Template (leamss_pa_notification_v1 - delivers 100% without Meta marketing fatigue drops)
                    try:
                        pa_notification_var = (
                            f"Your Australia PR Pre-Assessment registration is pending. "
                            f"🎉 Happy Navratri Special Offer – Complete your registration for just ₹999! "
                            f"💳 Payment Link: {payment_url} . "
                            f"Once payment is completed, your Australia PR Pre-Assessment will be processed."
                        )
                        await send_whatsapp_text(
                            to_phone=clean_phone,
                            text=cold_body_text,
                            client_name=name,
                            content_sid="HXa15807ac345260f5645e9c463c8c1c6a",
                            content_variables={
                                "1": name,
                                "2": pa_notification_var,
                            },
                        )
                        sent_tmpl = True
                    except Exception as e_tw_a15:
                        logger.warning("Twilio HXa158 payment dispatch failed: %s; trying HXa305...", e_tw_a15)

                    # 2. Approved Festive Template (leamss_navratri_payment_v1)
                    if not sent_tmpl:
                        try:
                            await send_whatsapp_text(
                                to_phone=clean_phone,
                                text=cold_body_text,
                                client_name=name,
                                content_sid="HXa305c6f62163719f294cfbba23733082",
                                content_variables={
                                    "1": name,
                                },
                            )
                            sent_tmpl = True
                        except Exception as e_tw_nav:
                            logger.warning("Twilio HXa305 (leamss_navratri_payment_v1) error: %s; trying fallback...", e_tw_nav)

                    if not sent_tmpl:
                        try:
                            await send_whatsapp_text(
                                to_phone=clean_phone,
                                text=cold_body_text,
                                client_name=name,
                                content_sid="HX64476ead028a5c3f2eab0c2d2e52f502",
                                content_variables={
                                    "1": name,
                                    "2": f"Please complete your registration payment (Rs. 999): {payment_url}",
                                },
                            )
                            sent_tmpl = True
                        except Exception as e_tw_644:
                            logger.warning("Twilio HX644 failed: %s; trying HXabf...", e_tw_644)

                    if not sent_tmpl:
                        try:
                            await send_whatsapp_text(
                                to_phone=clean_phone,
                                text=cold_body_text,
                                client_name=name,
                                content_sid="HXabf2abbb9ef2fbcf2b42bf132197584f",
                                content_variables={
                                    "1": name,
                                    "2": "Australia PR Special Offer",
                                    "3": "Registration Pending (₹999)",
                                    "4": "Subclass 189, 190, 491",
                                    "5": f"Payment Link: {payment_url}",
                                },
                            )
                            sent_tmpl = True
                        except Exception as e_tw_abf:
                            logger.warning("Twilio HXabf failed: %s; trying HX3cf...", e_tw_abf)

                    if not sent_tmpl:
                        try:
                            await send_whatsapp_text(
                                to_phone=clean_phone,
                                text=cold_body_text,
                                client_name=name,
                                content_sid="HX3cfb2f82a63a8e2cf3267cdb1a441195",
                                content_variables={
                                    "1": name,
                                    "2": ref_id,
                                    "3": "Australia PR Special Offer",
                                    "4": "Registration Pending",
                                },
                            )
                            sent_tmpl = True
                        except Exception as e_tw_3cf:
                            logger.warning("Twilio HX3cf failed: %s; trying HX46d...", e_tw_3cf)

                    if not sent_tmpl:
                        try:
                            await send_whatsapp_text(
                                to_phone=clean_phone,
                                text=cold_body_text,
                                client_name=name,
                                content_sid="HX46d5e5935b394d1208f6741d97e8c9a1",
                                content_variables={
                                    "1": name,
                                    "2": ref_id,
                                },
                            )
                            sent_tmpl = True
                        except Exception as e_tw_46d:
                            logger.warning("Twilio HX46d failed: %s; sending direct text", e_tw_46d)
                            await send_whatsapp_text(to_phone=clean_phone, text=direct_payment_text, client_name=name)
                else:
                    # Meta Cloud API / Direct WhatsApp Text (No button)
                    await send_whatsapp_text(
                        to_phone=clean_phone,
                        text=f"Hello {name},\n\nComplete your registration for the *LEAMSS Navratri Special Offer* and get your Australia PR Pre-Assessment Report.\n\n💳 *Payment Link:* {payment_url}",
                        client_name=name,
                    )

                await record_chat_message(
                    phone=clean_phone,
                    text=f"[Payment Pending Notice Dispatched]\n{cold_body_text}",
                    direction="outbound",
                    sender_type="system",
                    sender_name="LEAMSS Admissions Team",
                    client_name=name,
                    client_email=email,
                    status="sent",
                )
                results["whatsapp_sent"] = True

        except Exception as e_wa:
            logger.error("Failed to send payment link WhatsApp to %s: %s", phone, e_wa)
            results["errors"].append(f"WhatsApp error: {str(e_wa)}")

    # 3. Log to lead notes
    note_text = f"Sent Navratri Offer Payment Link via {'Email & WhatsApp' if results['email_sent'] and results['whatsapp_sent'] else 'Email' if results['email_sent'] else 'WhatsApp' if results['whatsapp_sent'] else 'Failed Dispatch'}: {payment_url}"
    update_q_pay: Dict[str, Any] = {"$or": [{"id": lead_id}, {"unique_id": lead_id}]}
    if lead.get("_id"):
        update_q_pay["$or"].append({"_id": lead["_id"]})
    await leads_col.update_one(
        update_q_pay,
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
    query_conditions = [{"id": lead_id}, {"unique_id": lead_id}]
    try:
        from bson import ObjectId
        if ObjectId.is_valid(str(lead_id)):
            query_conditions.append({"_id": ObjectId(str(lead_id))})
    except Exception:
        pass
    lead = await leads_col.find_one({"$or": query_conditions})
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

    await leads_col.update_one({"$or": query_conditions}, {"$set": update_data})
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
