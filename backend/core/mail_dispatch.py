"""Central Email Dispatcher for LEAMSS CRM.

Supports:
1. Real SMTP delivery via aiosmtplib (using Gmail App Password or custom SMTP server)
2. Resend API delivery (if RESEND_API_KEY is provided)
3. Graceful fallback when credentials are not yet configured, reporting pending_configuration
   with actionable setup guidance.
"""
from __future__ import annotations

import asyncio
import email.utils
import logging
import os
import uuid
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Any, Dict, List, Optional

logger = logging.getLogger("mail_dispatch")


async def get_email_credentials(
    user_id: Optional[str] = None,
    sender_email: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve active email credentials.
    Priority:
    1. If user_id or sender_email is provided, check user's personal mailbox settings in db['users'].
    2. Fall back to global email_settings or environment variables.
    """
    from core.database import db

    user_doc = None
    query_parts = []
    if user_id:
        uid_str = str(user_id).strip()
        query_parts.append({"id": uid_str})
        query_parts.append({"email": uid_str.lower()})
        try:
            from bson import ObjectId
            if ObjectId.is_valid(uid_str):
                query_parts.append({"_id": ObjectId(uid_str)})
        except Exception:
            pass

    if sender_email:
        clean_sender = str(sender_email).strip().lower()
        query_parts.append({"email": clean_sender})
        query_parts.append({"mailbox_settings.smtp_user": clean_sender})
        query_parts.append({"mailbox_settings.sender_email": clean_sender})

    if query_parts:
        user_doc = await db["users"].find_one({"$or": query_parts})

    # Check if user has personal mailbox settings
    mailbox_settings = (user_doc.get("mailbox_settings") or {}) if user_doc else {}
    user_smtp_user = (mailbox_settings.get("smtp_user") or (user_doc.get("email") if user_doc else "") or sender_email or "").strip()
    user_smtp_pass = (mailbox_settings.get("smtp_pass") or "").replace(" ", "").strip()
    user_smtp_host = (mailbox_settings.get("smtp_host") or "smtp.gmail.com").strip()
    user_smtp_port = int(mailbox_settings.get("smtp_port") or 587)
    user_sender_name = (mailbox_settings.get("sender_name") or (user_doc.get("name") if user_doc else "")).strip()
    user_sender_email = (mailbox_settings.get("sender_email") or user_smtp_user or (user_doc.get("email") if user_doc else "") or sender_email or "").strip()
    system_reply_email = (
        (mailbox_settings.get("system_reply_email") if mailbox_settings else None)
        or os.environ.get("CRM_SYSTEM_EMAIL")
        or "info@leamss.com"
    ).strip()

    if user_smtp_user and user_smtp_pass:
        return {
            "smtp_host": user_smtp_host,
            "smtp_port": user_smtp_port,
            "smtp_user": user_smtp_user,
            "smtp_pass": user_smtp_pass,
            "sender_name": user_sender_name or "LEAMSS Immigration Advisor",
            "sender_email": user_sender_email,
            "system_reply_email": system_reply_email,
            "resend_api_key": "",
            "has_smtp": True,
            "has_resend": False,
            "is_personal": True,
            "provider": "personal_smtp",
        }

    # Otherwise check database global settings
    settings_doc = await db["email_settings"].find_one({"id": "global"}) or {}

    smtp_host = settings_doc.get("smtp_host") or os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(settings_doc.get("smtp_port") or os.environ.get("SMTP_PORT", 587))
    smtp_user = (
        settings_doc.get("smtp_user")
        or os.environ.get("GMAIL_EMAIL")
        or os.environ.get("SMTP_USER")
        or ""
    ).strip()
    smtp_pass = (
        settings_doc.get("smtp_pass")
        or os.environ.get("GMAIL_APP_PASSWORD")
        or os.environ.get("SMTP_PASS")
        or os.environ.get("SMTP_PASSWORD")
        or ""
    ).replace(" ", "").strip()

    # If user_doc exists or sender_email passed, personal sender name & email take precedence even if using relay
    sender_name = (
        (user_doc.get("name") if user_doc else None)
        or settings_doc.get("sender_name")
        or os.environ.get("SENDER_NAME")
        or "LEAMSS Immigration"
    ).strip()
    effective_sender_addr = (
        sender_email
        or (user_doc.get("email") if user_doc else None)
        or settings_doc.get("sender_email")
        or smtp_user
        or os.environ.get("SENDER_EMAIL")
        or "advisor@leamss.com"
    ).strip()

    resend_key = (
        settings_doc.get("resend_api_key")
        or os.environ.get("RESEND_API_KEY")
        or ""
    ).strip()

    global_system_reply = (
        settings_doc.get("crm_reply_email")
        or os.environ.get("CRM_SYSTEM_EMAIL")
        or "info@leamss.com"
    ).strip()

    return {
        "smtp_host": smtp_host,
        "smtp_port": smtp_port,
        "smtp_user": smtp_user,
        "smtp_pass": smtp_pass,
        "sender_name": sender_name,
        "sender_email": effective_sender_addr,
        "system_reply_email": global_system_reply,
        "resend_api_key": resend_key,
        "has_smtp": bool(smtp_user and smtp_pass),
        "has_resend": bool(resend_key and resend_key != "re_your_api_key_here"),
        "is_personal": False,
        "provider": "company_smtp" if (smtp_user and smtp_pass) else "resend" if resend_key else "unconfigured",
    }


async def test_smtp_connection(
    *,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_pass: str,
) -> Dict[str, Any]:
    """Test SMTP connection and authentication for a specific user's credentials."""
    import aiosmtplib

    clean_pass = smtp_pass.replace(" ", "").strip()
    use_ssl = int(smtp_port) == 465
    try:
        smtp = aiosmtplib.SMTP(
            hostname=smtp_host.strip(),
            port=int(smtp_port),
            use_tls=use_ssl,
            start_tls=not use_ssl,
            timeout=15,
        )
        await smtp.connect()
        await smtp.login(smtp_user.strip(), clean_pass)
        await smtp.quit()
        return {
            "success": True,
            "message": f"Successfully connected and authenticated with {smtp_host} as {smtp_user}",
        }
    except aiosmtplib.SMTPAuthenticationError as auth_err:
        return {
            "success": False,
            "error": f"Google SMTP authentication rejected for {smtp_user} (BadCredentials). Ensure you are logged into Google as {smtp_user} (not a personal @gmail.com) at myaccount.google.com/apppasswords, and verify 2-Step Verification is turned ON.",
            "details": str(auth_err),
        }
    except aiosmtplib.SMTPServerDisconnected as disc_err:
        return {
            "success": False,
            "error": f"Google SMTP authentication rejected for {smtp_user} (BadCredentials: connection closed). Ensure you are logged into Google as {smtp_user} (not a personal @gmail.com) at myaccount.google.com/apppasswords, and verify 2-Step Verification is turned ON.",
            "details": str(disc_err),
        }
    except Exception as e:
        msg_str = str(e)
        if "connection lost" in msg_str.lower() or "disconnected" in msg_str.lower() or "535" in msg_str or "badcredentials" in msg_str.lower():
            return {
                "success": False,
                "error": f"Google SMTP authentication rejected for {smtp_user} (BadCredentials). Ensure you are logged into Google as {smtp_user} (not a personal @gmail.com) at myaccount.google.com/apppasswords, and verify 2-Step Verification is turned ON.",
                "details": msg_str,
            }
        return {
            "success": False,
            "error": f"Failed to connect to {smtp_host}:{smtp_port} — {e}",
            "details": str(e),
        }


async def purge_sent_email_from_gmail(
    *,
    smtp_host: str,
    smtp_user: str,
    smtp_pass: str,
    message_id: str,
    delay_seconds: float = 1.0,
) -> None:
    """Purge an outbound CRM email from Gmail's Sent Mail, INBOX, and Trash folders.

    Ensures CRM-sent emails remain strictly inside CRM email history and do not appear
    in the Sales Person's Google/Gmail account unless 'CC / Notify me' was explicitly enabled.
    """
    if "gmail.com" not in smtp_host.lower():
        return

    def _run_purge():
        import imaplib
        import time

        if delay_seconds > 0:
            time.sleep(delay_seconds)

        imap_host = "imap.gmail.com"
        try:
            mail = imaplib.IMAP4_SSL(imap_host, 993, timeout=15)
            mail.login(smtp_user, smtp_pass)
        except Exception as conn_err:
            logger.debug("Could not connect to IMAP for purge: %s", conn_err)
            return

        try:
            clean_mid = message_id.strip("<> ")
            search_queries = [
                f'(HEADER Message-ID "{clean_mid}")',
                f'(HEADER Message-ID "<{clean_mid}>")',
            ]

            # 1. Purge from Sent Mail
            sent_folders = ['"[Gmail]/Sent Mail"', '"[Gmail]/Sent"', "Sent"]
            for sf in sent_folders:
                try:
                    st, _ = mail.select(sf, readonly=False)
                    if st == "OK":
                        found_ids = []
                        for q in search_queries:
                            res, data = mail.search(None, q)
                            if data and data[0]:
                                found_ids.extend(data[0].split())
                        if found_ids:
                            for mid in set(found_ids):
                                mail.store(mid, "-X-GM-LABELS", "\\Sent")
                                mail.store(mid, "+FLAGS", "\\Deleted")
                            mail.expunge()
                            logger.info("Purged CRM email %s from %s", message_id, sf)
                            break
                except Exception as s_err:
                    logger.debug("Error purging from %s: %s", sf, s_err)

            # 2. Purge from INBOX (in case auto-filtered or threaded)
            try:
                st, _ = mail.select("INBOX", readonly=False)
                if st == "OK":
                    found_ids = []
                    for q in search_queries:
                        res, data = mail.search(None, q)
                        if data and data[0]:
                            found_ids.extend(data[0].split())
                    if found_ids:
                        for mid in set(found_ids):
                            mail.store(mid, "-X-GM-LABELS", "\\Inbox")
                            mail.store(mid, "+FLAGS", "\\Deleted")
                        mail.expunge()
                        logger.info("Purged CRM email %s from INBOX", message_id)
            except Exception as inb_err:
                logger.debug("Error checking INBOX during purge: %s", inb_err)

            # 3. Purge from Trash so no remnants remain in Gmail
            try:
                st, _ = mail.select('"[Gmail]/Trash"', readonly=False)
                if st == "OK":
                    found_ids = []
                    for q in search_queries:
                        res, data = mail.search(None, q)
                        if data and data[0]:
                            found_ids.extend(data[0].split())
                    if found_ids:
                        for mid in set(found_ids):
                            mail.store(mid, "+FLAGS", "\\Deleted")
                        mail.expunge()
            except Exception as tr_err:
                logger.debug("Error cleaning Trash during purge: %s", tr_err)

            mail.logout()
        except Exception as e:
            logger.debug("Error during Gmail purge: %s", e)

    try:
        await asyncio.to_thread(_run_purge)
    except Exception as e:
        logger.debug("Error launching Gmail purge thread: %s", e)


async def dispatch_email(
    *,
    to_email: str,
    subject: str,
    body_html: str,
    user_id: Optional[str] = None,
    sender_name: Optional[str] = None,
    sender_email: Optional[str] = None,
    cc: Optional[str] = None,
    bcc: Optional[str] = None,
    notify_by_email: bool = False,
    reply_to: Optional[str] = None,
    message_id: Optional[str] = None,
    in_reply_to: Optional[str] = None,
    attachments: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Dispatch an email through configured personal SMTP, company SMTP, or Resend service.

    Returns a dict with:
      - status: 'delivered' | 'failed' | 'pending_configuration'
      - provider: 'personal_smtp' | 'smtp' | 'resend' | 'unconfigured'
      - message_id: str
      - reply_to: str
      - notify_by_email: bool
      - info: str
      - error: Optional[str]
    """
    creds = await get_email_credentials(user_id=user_id, sender_email=sender_email)
    msg_id = message_id or f"<crm_{uuid.uuid4().hex}@{creds['smtp_host']}>"
    effective_sender_name = sender_name or creds["sender_name"]
    effective_sender_email = sender_email or creds["sender_email"]
    # Configure Reply-To header:
    # Clients must ALWAYS see and reply directly to the Sales Person's email (e.g. tech@leamss.com).
    # Never override with info@leamss.com or system address unless explicitly provided in reply_to.
    if reply_to:
        effective_reply_to = reply_to
    else:
        effective_reply_to = f"{effective_sender_name} <{effective_sender_email}>"

    # Addresses associated with the salesperson/sender
    sender_addrs_to_filter = {
        effective_sender_email.lower().strip(),
        (creds.get("smtp_user") or "").lower().strip(),
    } - {""}

    # Parse and sanitize CC list
    parsed_cc_list = []
    if cc and cc.strip():
        for c_addr in cc.split(","):
            c_clean = c_addr.strip()
            if not c_clean:
                continue
            # If notify_by_email is False, ensure sender's own email is never CC'd
            if not notify_by_email and c_clean.lower() in sender_addrs_to_filter:
                continue
            if c_clean not in parsed_cc_list:
                parsed_cc_list.append(c_clean)

    # Parse and sanitize BCC list
    parsed_bcc_list = []
    if bcc and bcc.strip():
        for b_addr in bcc.split(","):
            b_clean = b_addr.strip()
            if b_clean and b_clean.lower() not in [x.lower() for x in parsed_bcc_list]:
                parsed_bcc_list.append(b_clean)

    # If notify_by_email is True, include sender's personal email in CC / recipients
    # so Google SMTP delivers the notification copy into the Sales Person's Gmail Inbox!
    if notify_by_email and effective_sender_email:
        sender_clean = effective_sender_email.strip()
        if sender_clean.lower() not in [c.lower() for c in parsed_cc_list]:
            parsed_cc_list.append(sender_clean)

    final_cc_header = ", ".join(parsed_cc_list) if parsed_cc_list else None

    # 1. Try SMTP if configured (personal or company)
    if creds["has_smtp"]:
        try:
            import aiosmtplib

            msg = EmailMessage()
            msg["From"] = f"{effective_sender_name} <{effective_sender_email}>"
            msg["Reply-To"] = effective_reply_to
            msg["Sender"] = effective_sender_email
            msg["To"] = to_email
            if final_cc_header:
                msg["Cc"] = final_cc_header
            msg["Subject"] = subject
            msg["Message-ID"] = msg_id
            msg["Date"] = email.utils.formatdate(localtime=True)
            if in_reply_to:
                msg["In-Reply-To"] = in_reply_to
                msg["References"] = in_reply_to

            # Plain text fallback
            plain_text = body_html.replace("<br>", "\n").replace("<br/>", "\n").replace("</p>", "\n\n")
            # Simple tag strip
            import re
            plain_text = re.sub(r"<[^>]+>", "", plain_text).strip()

            # Ensure accurate Gateway info in the email footer referencing the salesperson
            processed_html = body_html
            processed_html = re.sub(
                r"Gateway info:\s*Delivered (?:via company gateway|directly from personal mailbox)\s*\([^)]*\)",
                f"Gateway info: Delivered directly from personal mailbox ({effective_sender_email})",
                processed_html,
                flags=re.IGNORECASE
            )

            # Convert base64 images (such as uploaded custom signature logos) into standard CID inline attachments
            # so that Gmail, Outlook and web clients render them reliably instead of blocking data URIs.
            inline_images = []
            def _replace_base64_img(match):
                sub_type = match.group(1).lower()
                b64_str = match.group(2).replace("\n", "").replace("\r", "").strip()
                cid_id = f"img_inline_{uuid.uuid4().hex[:10]}"
                try:
                    import base64
                    raw_bytes = base64.b64decode(b64_str)
                    clean_subtype = "png" if sub_type in ("png", "x-png") else "jpeg" if sub_type in ("jpg", "jpeg") else sub_type
                    inline_images.append({
                        "bytes": raw_bytes,
                        "subtype": clean_subtype,
                        "cid": cid_id
                    })
                    return f'src="cid:{cid_id}"'
                except Exception as b64_err:
                    logger.warning("Could not decode base64 inline image: %s", b64_err)
                    return match.group(0)

            processed_html = re.sub(
                r'src=["\']data:image/([a-zA-Z0-9+\.\-]+);base64,([A-Za-z0-9+/=\s]+)["\']',
                _replace_base64_img,
                processed_html
            )

            msg.set_content(plain_text or "Please open this email in an HTML-compatible email client.")
            msg.add_alternative(processed_html, subtype="html")

            # Attach inline related images to the HTML part for standard RFC multipart/related rendering
            if inline_images:
                try:
                    # In python EmailMessage with set_content + add_alternative:
                    # payload is [plain_part, html_part]
                    html_part = msg.get_payload()[1]
                    for img in inline_images:
                        html_part.add_related(
                            img["bytes"],
                            maintype="image",
                            subtype=img["subtype"],
                            cid=f"<{img['cid']}>",
                            disposition="inline"
                        )
                except Exception as img_err:
                    logger.warning("Failed attaching inline related images: %s", img_err)

            # Attachments if any
            for att in (attachments or []):
                data = att.get("bytes") or att.get("content")
                file_path = att.get("file_path") or att.get("path")
                if not data and file_path and os.path.exists(file_path):
                    try:
                        with open(file_path, "rb") as f:
                            data = f.read()
                    except Exception as err:
                        logger.warning("Failed reading attachment %s: %s", file_path, err)

                if isinstance(data, str):
                    if "base64," in data:
                        data = data.split("base64,", 1)[1]
                    try:
                        import base64
                        data = base64.b64decode(data)
                    except Exception as err:
                        logger.warning("Failed to decode base64 attachment: %s", err)
                        data = data.encode("utf-8")

                if data:
                    filename = att.get("filename") or att.get("name") or "attachment"
                    content_type = att.get("content_type") or att.get("type") or "application/octet-stream"
                    maintype = att.get("maintype")
                    subtype = att.get("subtype")
                    if not maintype or not subtype:
                        if "/" in content_type:
                            maintype, subtype = content_type.split("/", 1)
                        else:
                            maintype, subtype = "application", "octet-stream"
                    try:
                        msg.add_attachment(
                            data,
                            maintype=maintype,
                            subtype=subtype,
                            filename=filename,
                        )
                    except Exception as att_err:
                        logger.warning("Failed to add attachment %s: %s", filename, att_err)

            recipients = [to_email]
            for c_addr in parsed_cc_list:
                if c_addr not in recipients:
                    recipients.append(c_addr)
            for b_addr in parsed_bcc_list:
                if b_addr not in recipients:
                    recipients.append(b_addr)

            # Strict isolation guarantee: When notify_by_email is False,
            # sender's email must NEVER appear in envelope recipients.
            # This ensures Gmail SMTP places the email strictly in [Gmail]/Sent Mail
            # and NEVER in the sender's INBOX.
            if not notify_by_email:
                recipients = [r for r in recipients if r.lower().strip() not in sender_addrs_to_filter]

            use_ssl = int(creds["smtp_port"]) == 465
            async with aiosmtplib.SMTP(
                hostname=creds["smtp_host"],
                port=creds["smtp_port"],
                use_tls=use_ssl,
                start_tls=not use_ssl,
                timeout=25,
            ) as smtp:
                await smtp.login(creds["smtp_user"], creds["smtp_pass"])
                await smtp.send_message(msg, sender=creds["smtp_user"], recipients=recipients)

            # Purge sent email from Gmail if notify_by_email is False
            if not notify_by_email and "gmail.com" in creds["smtp_host"].lower():
                asyncio.create_task(
                    purge_sent_email_from_gmail(
                        smtp_host=creds["smtp_host"],
                        smtp_user=creds["smtp_user"],
                        smtp_pass=creds["smtp_pass"],
                        message_id=msg_id,
                        delay_seconds=1.0,
                    )
                )

            provider_label = "personal_smtp" if creds.get("is_personal") else "smtp"
            info_msg = (
                f"Delivered directly from personal mailbox ({creds['sender_email']})"
                if creds.get("is_personal")
                else f"Delivered via company gateway ({creds['smtp_host']})"
            )
            logger.info("Successfully delivered email via %s to %s", provider_label, to_email)
            return {
                "status": "delivered",
                "provider": provider_label,
                "fallback": False,
                "message_id": msg_id,
                "reply_to": effective_reply_to,
                "notify_by_email": notify_by_email,
                "info": info_msg,
                "is_personal": bool(creds.get("is_personal")),
                "smtp_user": creds.get("smtp_user"),
                "from_email": effective_sender_email,
                "sender_email": effective_sender_email,
                "sent_at": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.warning("SMTP send failed to %s: %s", to_email, e)
            e_str = str(e)
            is_auth_rejection = (
                isinstance(e, aiosmtplib.SMTPAuthenticationError)
                or isinstance(e, aiosmtplib.SMTPServerDisconnected)
                or "connection lost" in e_str.lower()
                or "badcredentials" in e_str.lower()
                or "535" in e_str
            )

            # Resilient fallback: If personal SMTP fails (e.g. BadCredentials), fall back to company gateway
            # so the client email is DELIVERED and sales work is never blocked!
            if creds.get("is_personal"):
                try:
                    from core.database import db
                    settings_doc = await db["email_settings"].find_one({"id": "global"}) or {}
                    comp_user = (settings_doc.get("smtp_user") or os.environ.get("GMAIL_EMAIL") or os.environ.get("SMTP_USER") or "").strip()
                    comp_pass = (settings_doc.get("smtp_pass") or os.environ.get("GMAIL_APP_PASSWORD") or os.environ.get("SMTP_PASS") or "").replace(" ", "").strip()
                    comp_host = settings_doc.get("smtp_host") or os.environ.get("SMTP_HOST", "smtp.gmail.com")
                    comp_port = int(settings_doc.get("smtp_port") or os.environ.get("SMTP_PORT", 587))

                    if comp_user and comp_pass:
                        logger.info("Falling back to company gateway (%s) for sender %s to %s", comp_user, effective_sender_email, to_email)
                        comp_ssl = comp_port == 465
                        async with aiosmtplib.SMTP(
                            hostname=comp_host,
                            port=comp_port,
                            use_tls=comp_ssl,
                            start_tls=not comp_ssl,
                            timeout=25,
                        ) as comp_smtp:
                            await comp_smtp.login(comp_user, comp_pass)
                            # Keep From and Reply-To strictly as the salesperson
                            # Update Sender to the authenticated relay user to prevent SMTP relay rejection
                            if "Sender" in msg:
                                msg.replace_header("Sender", comp_user)
                            else:
                                msg["Sender"] = comp_user
                            msg["X-Personal-Sender"] = effective_sender_email
                            await comp_smtp.send_message(msg, sender=comp_user, recipients=recipients)

                        logger.info("Fallback delivery via company gateway SUCCEEDED for %s", effective_sender_email)
                        delivery_note = f"Delivered via company gateway ({effective_sender_email})"
                        if is_auth_rejection:
                            delivery_note += " · Personal Google App Password rejected by Google (BadCredentials); verify App Password in Mailbox Settings."

                        return {
                            "status": "delivered",
                            "provider": "company_smtp",
                            "fallback": True,
                            "message_id": msg_id,
                            "reply_to": effective_reply_to,
                            "notify_by_email": notify_by_email,
                            "info": delivery_note,
                            "is_personal": True,
                            "smtp_user": effective_sender_email,
                            "from_email": effective_sender_email,
                            "sender_email": effective_sender_email,
                            "sent_at": datetime.now(timezone.utc).isoformat(),
                        }
                except Exception as fb_err:
                    logger.warning("Fallback via company gateway failed: %s", fb_err)

            if is_auth_rejection:
                err_msg = (
                    f"Google SMTP authentication rejected for {creds.get('smtp_user')}. "
                    f"Please generate a 16-character Google App Password at myaccount.google.com/apppasswords while logged in as {creds.get('smtp_user')}."
                )
            else:
                err_msg = f"SMTP delivery failed: {e_str}"
            return {
                "status": "failed",
                "provider": "personal_smtp" if creds.get("is_personal") else "smtp",
                "message_id": msg_id,
                "reply_to": effective_reply_to,
                "notify_by_email": notify_by_email,
                "from_email": effective_sender_email,
                "sender_email": effective_sender_email,
                "error": err_msg,
                "info": err_msg,
            }

    # 2. Try Resend if configured
    if creds["has_resend"]:
        try:
            import resend

            resend.api_key = creds["resend_api_key"]
            params = {
                "from": f"{effective_sender_name} <{effective_sender_email}>",
                "to": [to_email],
                "subject": subject,
                "html": body_html,
                "reply_to": effective_reply_to,
            }
            if parsed_cc_list:
                params["cc"] = parsed_cc_list
            if parsed_bcc_list:
                params["bcc"] = parsed_bcc_list
            if attachments:
                resend_atts = []
                for att in attachments:
                    att_data = att.get("content")
                    file_path = att.get("file_path") or att.get("path")
                    if not att_data and file_path and os.path.exists(file_path):
                        try:
                            import base64
                            with open(file_path, "rb") as f:
                                att_data = base64.b64encode(f.read()).decode("utf-8")
                        except Exception as e:
                            logger.warning("Error reading attachment for Resend: %s", e)
                    if att_data:
                        if isinstance(att_data, bytes):
                            import base64
                            att_data = base64.b64encode(att_data).decode("utf-8")
                        elif isinstance(att_data, str) and "base64," in att_data:
                            att_data = att_data.split("base64,", 1)[1]
                        resend_atts.append({
                            "filename": att.get("filename") or att.get("name") or "attachment",
                            "content": att_data
                        })
                if resend_atts:
                    params["attachments"] = resend_atts
            res = await asyncio.to_thread(resend.Emails.send, params)
            res_id = (res or {}).get("id", msg_id)
            logger.info("Successfully delivered email via Resend to %s", to_email)
            return {
                "status": "delivered",
                "provider": "resend",
                "message_id": res_id,
                "reply_to": effective_reply_to,
                "notify_by_email": notify_by_email,
                "info": f"Delivered via Resend as {effective_sender_email}",
                "sent_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.warning("Resend send failed to %s: %s", to_email, e)
            return {
                "status": "failed",
                "provider": "resend",
                "message_id": msg_id,
                "reply_to": effective_reply_to,
                "notify_by_email": notify_by_email,
                "error": str(e),
                "info": f"Resend delivery failed: {e}",
            }

    # 3. Neither configured: Log & record in CRM
    info_guidance = (
        f"Email recorded in CRM. For live external dispatch from {effective_sender_email}, "
        f"configure your Mailbox App Password in Mailbox Settings."
    )
    logger.info("Email recorded in CRM (Pending Mailbox / SMTP setup) to %s: %s", to_email, subject)
    return {
        "status": "pending_configuration",
        "provider": "unconfigured",
        "message_id": msg_id,
        "reply_to": effective_reply_to,
        "notify_by_email": notify_by_email,
        "info": info_guidance,
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }
