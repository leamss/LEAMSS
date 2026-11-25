"""Client Credentials Provisioning & Email Notification Service.

Whenever a Partner, Salesperson, or Admin creates a new client profile, this service
automatically provisions their client portal login account and sends their login
credentials (login ID and password / portal access link) to their registered email address.
"""
from __future__ import annotations

import logging
import os
import secrets
import string
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from core.auth import get_password_hash
from core.database import db, users_col
from core.email_service import send_email
from core.mail_dispatch import dispatch_email

logger = logging.getLogger(__name__)

MINI_PORTAL_COLL = "client_mini_portals"
FRONTEND_URL = os.environ.get("FRONTEND_URL") or os.environ.get("REACT_APP_FRONTEND_URL") or "http://localhost:3000"


def generate_temp_password(length: int = 6) -> str:
    """Generate a readable, secure initial password like Leamss@7xK92b"""
    chars = string.ascii_letters + string.digits
    suffix = "".join(secrets.choice(chars) for _ in range(length))
    return f"Leamss@{suffix}"


async def provision_and_email_client_credentials(
    client_name: str,
    client_email: str,
    client_phone: Optional[str] = None,
    pa_id: Optional[str] = None,
    service_type: Optional[str] = None,
    country: Optional[str] = None,
    triggered_by_user: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Ensure client user exists in `users_col` & `client_mini_portals`, and email login credentials.

    Idempotent: If user already exists, it will still email their portal access instructions.
    If a new user is created, a secure initial password is generated and sent.
    """
    if not client_email or not client_email.strip():
        logger.warning("provision_and_email_client_credentials called with empty email")
        return {"ok": False, "error": "Email is required"}

    email_clean = client_email.strip().lower()
    name_clean = client_name.strip() if client_name else "Valued Client"
    now = datetime.now(timezone.utc)

    # 1. Check if user already exists in users_col
    existing_user = await users_col.find_one(
        {"email": {"$regex": f"^{email_clean}$", "$options": "i"}}
    )

    is_new_user = False
    raw_password = None

    if not existing_user:
        is_new_user = True
        user_id = str(uuid.uuid4())
        raw_password = generate_temp_password()
        hashed_password = get_password_hash(raw_password)

        new_user = {
            "id": user_id,
            "name": name_clean,
            "email": email_clean,
            "phone": client_phone or "",
            "password": hashed_password,
            "password_hash": hashed_password,
            "role": "client",
            "rbac_role": "client",
            "user_type": "client",
            "status": "active",
            "source": "partner_sales_admin_creation",
            "created_at": now,
            "updated_at": now,
            "must_change_password_on_next_login": False,
        }
        await users_col.insert_one(new_user)
        user_record = new_user
        logger.info(f"Created new client account {email_clean} (id: {user_id})")
    else:
        user_record = existing_user
        user_id = existing_user.get("id") or str(existing_user.get("_id"))
        # If user exists but has no password or password_hash set, set one
        if not existing_user.get("password") and not existing_user.get("password_hash") and not existing_user.get("hashed_password"):
            raw_password = generate_temp_password()
            hashed_password = get_password_hash(raw_password)
            await users_col.update_one(
                {"id": user_id},
                {"$set": {"password": hashed_password, "password_hash": hashed_password, "updated_at": now}}
            )
            logger.info(f"Updated password for client {email_clean}")

    # 2. Synchronize with client_mini_portals so /client-portal/login also works
    try:
        mini_portal = await db[MINI_PORTAL_COLL].find_one({"client_email": email_clean})
        if not mini_portal:
            portal_id = str(uuid.uuid4())
            mini_doc = {
                "id": portal_id,
                "client_id": user_id,
                "client_name": name_clean,
                "client_email": email_clean,
                "pa_id": pa_id,
                "country": country,
                "service_type": service_type,
                "temp_password": raw_password or "Use your existing password",
                "password_hash": user_record.get("password_hash") or user_record.get("password"),
                "status": "active",
                "locked": False,
                "created_at": now,
                "updated_at": now,
            }
            await db[MINI_PORTAL_COLL].insert_one(mini_doc)
        elif raw_password:
            await db[MINI_PORTAL_COLL].update_one(
                {"client_email": email_clean},
                {"$set": {
                    "temp_password": raw_password,
                    "password_hash": user_record.get("password_hash") or user_record.get("password"),
                    "updated_at": now,
                }}
            )
    except Exception as e:
        logger.warning(f"Error syncing client_mini_portals for {email_clean}: {e}")

    # 3. Format email body
    login_url = f"{FRONTEND_URL}/login"
    client_portal_url = f"{FRONTEND_URL}/client-portal/login"

    password_row = (
        f"""
        <div style="margin-bottom: 12px;">
            <span style="font-size: 12px; color: #6b7280; text-transform: uppercase; font-weight: 600; display: block;">Temporary Password:</span>
            <span style="font-size: 16px; font-weight: 700; color: #111827; font-family: monospace; background: #f3f4f6; padding: 4px 10px; border-radius: 4px; display: inline-block;">{raw_password}</span>
        </div>
        """
        if raw_password
        else """
        <div style="margin-bottom: 12px;">
            <span style="font-size: 12px; color: #6b7280; text-transform: uppercase; font-weight: 600; display: block;">Password:</span>
            <span style="font-size: 14px; color: #111827;">Use your existing LEAMSS client account password, or use Forgot Password on the login page to reset.</span>
        </div>
        """
    )

    service_line = (
        f"<p style='color: #4b5563; font-size: 14px; margin: 4px 0 0 0;'>Application: <strong>{service_type}</strong> ({country})</p>"
        if service_type and country
        else (f"<p style='color: #4b5563; font-size: 14px; margin: 4px 0 0 0;'>Destination: <strong>{country}</strong></p>" if country else "")
    )

    body_html = f"""
    <p style="color: #374151; font-size: 15px; line-height: 1.6; margin-top: 0;">Dear {name_clean},</p>
    <p style="color: #374151; font-size: 14px; line-height: 1.6;">
        Welcome to <strong>LEAMSS</strong>! Your client portal account has been created. 
        You can now log in to track your migration workflow, follow your application steps, 
        review proposals, and upload required documents securely.
    </p>
    {service_line}

    <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-left: 4px solid #2a777a; border-radius: 8px; padding: 18px 24px; margin: 24px 0;">
        <h3 style="margin: 0 0 14px 0; font-size: 15px; color: #2a777a; font-weight: 700;">Your Client Portal Login Details</h3>
        
        <div style="margin-bottom: 12px;">
            <span style="font-size: 12px; color: #6b7280; text-transform: uppercase; font-weight: 600; display: block;">Login ID / Registered Email:</span>
            <span style="font-size: 15px; font-weight: 600; color: #111827;">{email_clean}</span>
        </div>

        {password_row}

        <div style="margin-top: 18px;">
            <a href="{login_url}" style="background-color: #2a777a; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 14px; display: inline-block;">
                Log In to Your Client Portal &rarr;
            </a>
        </div>
    </div>

    <div style="background: #fffbeb; border: 1px solid #fef3c7; border-radius: 6px; padding: 12px 16px; margin: 20px 0;">
        <p style="color: #92400e; font-size: 13px; line-height: 1.5; margin: 0;">
            <strong>Next Steps:</strong> Log in to check your application progress and follow each step of your process. For security, please update your password after logging in.
        </p>
    </div>

    <p style="color: #6b7280; font-size: 13px; line-height: 1.5;">
        You can access your portal anytime at <a href="{login_url}" style="color: #2a777a;">{login_url}</a> or <a href="{client_portal_url}" style="color: #2a777a;">{client_portal_url}</a>.
    </p>
    """

    subject = "Your LEAMSS Client Portal Login Details"
    sender_uid = triggered_by_user.get("id") if triggered_by_user else None
    sender_name = triggered_by_user.get("name") if triggered_by_user else "LEAMSS Immigration"
    sender_email = triggered_by_user.get("email") if triggered_by_user else "info@leamss.com"

    try:
        dispatch_res = await dispatch_email(
            to_email=email_clean,
            subject=subject,
            body_html=body_html,
            user_id=sender_uid,
            sender_name=sender_name,
            sender_email=sender_email,
        )
        is_ok = dispatch_res.get("status") in ("delivered", "sent")
        email_status = "sent" if is_ok else dispatch_res.get("status", "failed")
        email_provider = dispatch_res.get("provider", "smtp")
        email_error = dispatch_res.get("error")
        email_info = dispatch_res.get("info")
    except Exception as e:
        logger.error(f"Error dispatching client credentials email to {email_clean}: {e}")
        email_status = "failed"
        email_provider = "smtp"
        email_error = str(e)
        email_info = None

    # Record in db["email_logs"]
    log_doc = {
        "id": str(uuid.uuid4()),
        "to": email_clean,
        "subject": subject,
        "body": body_html,
        "body_html": body_html,
        "status": email_status,
        "provider": email_provider,
        "error": email_error,
        "info": email_info,
        "sent_at": datetime.now(timezone.utc),
        "pa_id": pa_id,
        "triggered_by": sender_uid,
    }
    await db["email_logs"].insert_one(log_doc)

    return {
        "ok": True,
        "user_id": user_id,
        "email": email_clean,
        "is_new_user": is_new_user,
        "raw_password": raw_password,
        "email_status": email_status,
        "email_provider": email_provider,
        "email_error": email_error,
    }


async def send_payment_link_and_login_details_email(
    pa_id: str,
    payment_url: str,
    amount_label: str,
    amount: Optional[float] = None,
    gst_included: bool = False,
    triggered_by_user: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Sends an email containing both the Pre-Assessment payment link AND the client portal login
    details directly to the client's registered email address (entered during creation).

    Crucial: Recipient is ALWAYS pa["client_email"], never the partner or admin.
    """
    pre_assessments_col = db["pre_assessments"]
    pa = await pre_assessments_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        logger.error(f"Cannot send payment email: Pre-assessment {pa_id} not found")
        return {"ok": False, "error": "Pre-assessment not found"}

    client_email = (pa.get("client_email") or "").strip().lower()
    if not client_email:
        logger.warning(f"Pre-assessment {pa_id} has no registered client email")
        return {"ok": False, "error": "Client email is missing on pre-assessment"}

    client_name = (pa.get("client_name") or "Valued Client").strip()
    country = pa.get("country") or "Destination Country"
    service_type = pa.get("service_type") or "Immigration Service"
    program_name = pa.get("product_name") or f"{service_type} ({country})"

    # Ensure client account is provisioned and get their credentials
    creds_res = await provision_and_email_client_credentials(
        client_name=client_name,
        client_email=client_email,
        client_phone=pa.get("client_mobile"),
        pa_id=pa_id,
        service_type=service_type,
        country=country,
        triggered_by_user=triggered_by_user,
    )

    # Get temporary password if available
    raw_password = creds_res.get("raw_password")
    if not raw_password:
        mini = await db[MINI_PORTAL_COLL].find_one({"client_email": client_email})
        if mini and mini.get("temp_password"):
            raw_password = mini.get("temp_password")

    login_url = f"{FRONTEND_URL}/login"

    password_row = (
        f"""
        <div style="margin-bottom: 12px;">
            <span style="font-size: 12px; color: #6b7280; text-transform: uppercase; font-weight: 600; display: block;">Temporary Password:</span>
            <span style="font-size: 16px; font-weight: 700; color: #111827; font-family: monospace; background: #f3f4f6; padding: 4px 10px; border-radius: 4px; display: inline-block;">{raw_password}</span>
        </div>
        """
        if raw_password and raw_password != "Use your existing password"
        else """
        <div style="margin-bottom: 12px;">
            <span style="font-size: 12px; color: #6b7280; text-transform: uppercase; font-weight: 600; display: block;">Password:</span>
            <span style="font-size: 14px; color: #111827;">Use your existing client portal password (or click Forgot Password on the login page if needed).</span>
        </div>
        """
    )

    fee_details = f"<strong>{amount_label}</strong>"
    if gst_included:
        fee_details += " (Includes 18% GST)"

    body_html = f"""
    <p style="color: #374151; font-size: 15px; line-height: 1.6; margin-top: 0;">Dear {client_name},</p>
    <p style="color: #374151; font-size: 14px; line-height: 1.6;">
        Your consultant has registered your application for <strong>{program_name}</strong> and generated your secure Pre-Assessment payment link.
    </p>

    <!-- SECTION 1: PRE-ASSESSMENT PAYMENT LINK -->
    <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-left: 4px solid #16a34a; border-radius: 8px; padding: 20px 24px; margin: 20px 0;">
        <h3 style="margin: 0 0 10px 0; font-size: 16px; color: #15803d; font-weight: 700;">Pre-Assessment Payment</h3>
        <p style="color: #374151; font-size: 14px; margin: 0 0 8px 0;">
            Program: <strong>{program_name}</strong>
        </p>
        <p style="color: #374151; font-size: 14px; margin: 0 0 16px 0;">
            Total Amount Due: {fee_details}
        </p>
        <div>
            <a href="{payment_url}" style="background-color: #f7620b; color: #ffffff; padding: 12px 28px; text-decoration: none; border-radius: 6px; font-weight: 700; font-size: 14px; display: inline-block;">
                Pay {amount_label} Securely Online &rarr;
            </a>
        </div>
        <p style="color: #6b7280; font-size: 12px; margin: 12px 0 0 0;">
            Or copy and paste this link in your browser: <br/>
            <a href="{payment_url}" style="color: #2a777a; word-break: break-all;">{payment_url}</a>
        </p>
    </div>

    <!-- SECTION 2: CLIENT PORTAL ACCESS & LOGIN DETAILS -->
    <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-left: 4px solid #2a777a; border-radius: 8px; padding: 20px 24px; margin: 20px 0;">
        <h3 style="margin: 0 0 12px 0; font-size: 16px; color: #2a777a; font-weight: 700;">Your Client Portal Login Details</h3>
        <p style="color: #4b5563; font-size: 13px; margin: 0 0 14px 0;">
            Log in to your portal anytime to check your workflow progress, review upcoming steps, and upload your documents:
        </p>
        
        <div style="margin-bottom: 12px;">
            <span style="font-size: 12px; color: #6b7280; text-transform: uppercase; font-weight: 600; display: block;">Login ID / Registered Email:</span>
            <span style="font-size: 15px; font-weight: 600; color: #111827;">{client_email}</span>
        </div>

        {password_row}

        <div style="margin-top: 16px;">
            <a href="{login_url}" style="background-color: #2a777a; color: #ffffff; padding: 10px 22px; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 13px; display: inline-block;">
                Log In to Client Portal &rarr;
            </a>
        </div>
    </div>

    <!-- SECTION 3: INSTRUCTIONS -->
    <div style="background: #fffbeb; border: 1px solid #fef3c7; border-radius: 6px; padding: 14px 18px; margin: 20px 0;">
        <h4 style="margin: 0 0 6px 0; font-size: 13px; color: #92400e; font-weight: 700;">Instructions for Your Journey:</h4>
        <ol style="margin: 0; padding-left: 18px; color: #78350f; font-size: 13px; line-height: 1.6;">
            <li>Click the orange <strong>Pay Securely Online</strong> button above to complete your initial Pre-Assessment fee.</li>
            <li>Once paid, log in to your Client Portal using your credentials to view your customized application workflow and begin uploading your required documents.</li>
        </ol>
    </div>

    <p style="color: #6b7280; font-size: 12px; line-height: 1.5;">
        Need help? Reply to this email or contact your assigned LEAMSS migration consultant.
    </p>
    """

    subject = f"Pre-Assessment Payment Link & Portal Login Details — {program_name}"
    sender_uid = triggered_by_user.get("id") if triggered_by_user else pa.get("created_by")
    sender_name = triggered_by_user.get("name") if triggered_by_user else (pa.get("partner_name") or "LEAMSS Immigration")
    sender_email = triggered_by_user.get("email") if triggered_by_user else "info@leamss.com"

    try:
        dispatch_res = await dispatch_email(
            to_email=client_email,
            subject=subject,
            body_html=body_html,
            user_id=sender_uid,
            sender_name=sender_name,
            sender_email=sender_email,
        )
        is_ok = dispatch_res.get("status") in ("delivered", "sent")
        email_status = "sent" if is_ok else dispatch_res.get("status", "failed")
        email_provider = dispatch_res.get("provider", "smtp")
        email_error = dispatch_res.get("error")
        email_info = dispatch_res.get("info")
    except Exception as e:
        logger.error(f"Error dispatching payment link & login details to {client_email}: {e}")
        email_status = "failed"
        email_provider = "smtp"
        email_error = str(e)
        email_info = None

    # Record in db["email_logs"]
    log_doc = {
        "id": str(uuid.uuid4()),
        "to": client_email,
        "subject": subject,
        "body": body_html,
        "body_html": body_html,
        "status": email_status,
        "provider": email_provider,
        "error": email_error,
        "info": email_info,
        "sent_at": datetime.now(timezone.utc),
        "pa_id": pa_id,
        "triggered_by": sender_uid,
    }
    await db["email_logs"].insert_one(log_doc)

    # Record in db["crm_emails"] for CRM email history
    crm_email_doc = {
        "id": str(uuid.uuid4()),
        "client_email": client_email,
        "to_email": client_email,
        "from_email": sender_email,
        "sender_name": sender_name,
        "sales_person_id": sender_uid,
        "sales_person_name": sender_name,
        "subject": subject,
        "body_html": body_html,
        "status": email_status,
        "delivery_provider": email_provider,
        "delivery_error": email_error,
        "delivery_info": email_info,
        "sent_at": datetime.now(timezone.utc),
        "direction": "outbound",
        "channel": "email",
        "pa_id": pa_id,
    }
    await db["crm_emails"].insert_one(crm_email_doc)

    # Record in pre_assessments audit_log
    audit_entry = {
        "action": "payment_link_and_credentials_emailed",
        "actor_id": triggered_by_user.get("id") if triggered_by_user else "system",
        "actor_name": triggered_by_user.get("name") if triggered_by_user else "System",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "channel": "email",
        "to": client_email,
        "amount_label": amount_label,
        "payment_url": payment_url,
        "status": email_status,
    }
    await pre_assessments_col.update_one(
        {"id": pa_id},
        {
            "$push": {"audit_log": audit_entry},
            "$set": {
                "payment_link_emailed_to": client_email,
                "payment_link_emailed_at": datetime.now(timezone.utc),
                "client_login_email": client_email,
                "client_temp_password": raw_password,
                "updated_at": datetime.now(timezone.utc),
            }
        }
    )

    logger.info(f"Payment link & login details emailed ({email_status}) to client {client_email} for PA {pa_id}")
    return {
        "ok": email_status == "sent",
        "client_email": client_email,
        "email_status": email_status,
        "email_provider": email_provider,
        "email_info": email_info or email_error,
        "email_error": email_error,
        "payment_url": payment_url,
        "login_email": client_email,
        "temp_password": raw_password,
        "login_url": login_url,
    }
