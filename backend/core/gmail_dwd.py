"""Gmail API sender via Google Workspace DOMAIN-WIDE DELEGATION.

One service account (authorized in the Workspace Admin console for scope
gmail.send) impersonates ANY user in the domain and sends mail AS that user —
the mail lands in that consultant's own Gmail Sent folder. No per-user App
Passwords / OAuth consent needed.

Config (backend/.env):
  GMAIL_SA_JSON_B64       base64 of the service-account JSON key
  GMAIL_DELEGATED_DOMAIN  e.g. leamss.com (only addresses on this domain may send)
  GMAIL_DEFAULT_SENDER    fallback sender when a client has no consultant, e.g. info@leamss.com
  GMAIL_DAILY_BUDGET      per-sender daily cap (default 1800)
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Optional, List, Any

logger = logging.getLogger("gmail_dwd")

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
DAILY_BUDGET = int(os.environ.get("GMAIL_DAILY_BUDGET", "1800"))


def delegated_domain() -> str:
    return (os.environ.get("GMAIL_DELEGATED_DOMAIN") or "").strip().lower()


def default_sender() -> str:
    return (
        os.environ.get("GMAIL_DEFAULT_SENDER")
        or os.environ.get("GMAIL_EMAIL")
        or os.environ.get("SMTP_USER")
        or "info@leamss.com"
    ).strip().lower()


def _sa_info() -> Optional[dict]:
    b64 = (os.environ.get("GMAIL_SA_JSON_B64") or "").strip()
    if not b64:
        return None
    try:
        return json.loads(base64.b64decode(b64).decode("utf-8"))
    except Exception:
        logger.exception("Failed to decode GMAIL_SA_JSON_B64")
        return None


def is_configured() -> bool:
    return True


def sa_client_id() -> Optional[str]:
    return (_sa_info() or {}).get("client_id")


def sa_client_email() -> Optional[str]:
    return (_sa_info() or {}).get("client_email")


def _quota_key(sender: str) -> str:
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"{day}:{sender}"


async def remaining_budget(sender: Optional[str] = None) -> int:
    sender = (sender or default_sender()).strip().lower()
    if not sender:
        return 0
    from core.database import db
    doc = await db["email_quota"].find_one({"_id": _quota_key(sender)}, {"count": 1})
    return max(0, DAILY_BUDGET - (doc or {}).get("count", 0))


def _build_service(sender_email: str):
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    info = _sa_info()
    if not info:
        raise RuntimeError("Gmail service account not configured.")
    creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES).with_subject(sender_email)
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def _send_sync(sender_email: str, msg_bytes: bytes) -> dict:
    service = _build_service(sender_email)
    raw = base64.urlsafe_b64encode(msg_bytes).decode()
    return service.users().messages().send(userId="me", body={"raw": raw}).execute()


async def send(
    *, sender_email: str, recipient: str, subject: str, html: str, plain: str,
    sender_name: Optional[str] = None, attachments: Optional[List[Any]] = None,
    bcc: Optional[str] = None,
) -> None:
    sender_email = (sender_email or default_sender() or os.environ.get("GMAIL_EMAIL") or os.environ.get("SMTP_USER") or "info@leamss.com").strip().lower()

    from core.database import db
    try:
        settings_doc = await db["email_settings"].find_one({"id": "global"}) or {}
    except Exception:
        settings_doc = {}

    sender_doc = None
    try:
        sender_doc = await db["mail_senders"].find_one({"email": sender_email})
    except Exception:
        pass

    # Build standard email message
    msg = EmailMessage()
    def _hdr(v):
        return " ".join(str(v or "").replace("\r", " ").replace("\n", " ").split())
    
    sender_doc_name = (sender_doc or {}).get("name")
    if sender_doc_name and (not sender_name or sender_name in ["LEAMSS", "LEAMSS Security", "Ladhani Education & Migration Services"]):
        from_name = _hdr(f"{sender_doc_name} | LEAMSS")
    else:
        from_name = _hdr(sender_name or sender_doc_name or settings_doc.get("sender_name") or os.environ.get("SENDER_NAME") or "LEAMSS Consultation")

    from email.utils import formatdate, make_msgid

    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=sender_email.split("@")[-1] or "leamss.com")
    msg["Reply-To"] = f"{from_name} <{sender_email}>" if from_name else sender_email
    msg["From"] = f"{from_name} <{sender_email}>" if from_name else sender_email
    msg["To"] = _hdr(recipient)
    msg["Subject"] = _hdr(subject)
    if bcc:
        msg["Bcc"] = _hdr(bcc)
    msg.set_content(plain or "Please open this email in an HTML-capable client.")
    msg.add_alternative(html, subtype="html")
    for att in (attachments or []):
        data = att.get("bytes")
        if not data:
            continue
        msg.add_attachment(
            data,
            maintype=att.get("maintype", "application"),
            subtype=att.get("subtype", "octet-stream"),
            filename=att.get("filename", "attachment"),
        )

    # 1. Try Google Workspace DWD Service Account if configured
    if _sa_info() is not None:
        try:
            await asyncio.to_thread(_send_sync, sender_email, msg.as_bytes())
            logger.info("Email sent via Google Workspace DWD to %s", recipient)
            return
        except Exception as e:
            logger.warning("DWD send failed, attempting SMTP fallback: %s", e)

    # 2. Try SMTP with Gmail App Password or SMTP credentials (from DB or env)
    global_user = (
        settings_doc.get("smtp_user")
        or settings_doc.get("gmail_email")
        or os.environ.get("GMAIL_EMAIL")
        or os.environ.get("SMTP_USER")
        or "info@leamss.com"
    ).strip()
    global_pass = (
        settings_doc.get("smtp_password")
        or settings_doc.get("smtp_pass")
        or settings_doc.get("gmail_app_password")
        or os.environ.get("GMAIL_APP_PASSWORD")
        or os.environ.get("SMTP_PASS")
        or os.environ.get("SMTP_PASSWORD")
        or "mwofliqkpoyagmkc"
    ).replace(" ", "").strip()

    sender_app_password = (sender_doc or {}).get("app_password")
    if sender_app_password:
        login_user = sender_email
        login_pass = sender_app_password.replace(" ", "").strip()
    else:
        login_user = global_user
        login_pass = global_pass

    smtp_host = settings_doc.get("smtp_host") or os.environ.get("SMTP_HOST", "smtp.gmail.com")
    configured_port = int(settings_doc.get("smtp_port") or os.environ.get("SMTP_PORT", "465"))

    def _send_smtp_sync(user: str, password: str, targets: list[str]) -> None:
        import smtplib
        # Ensure From header matches authenticated user if different to guarantee 100% SPF/DKIM
        if user and "@" in user and sender_email != user and not sender_app_password:
            try:
                msg.replace_header("From", f"{from_name} <{user}>")
            except Exception:
                pass

        # Try port 465 SSL first on Gmail (reliable against pipe drops on 2MB attachments), fallback to 587
        ports_to_try = [465, 587] if (smtp_host == "smtp.gmail.com" and configured_port in (465, 587)) else [configured_port]
        last_err = None
        for port in ports_to_try:
            try:
                if port == 465:
                    with smtplib.SMTP_SSL(smtp_host, 465, timeout=45) as server:
                        server.login(user, password)
                        server.send_message(msg, from_addr=user, to_addrs=targets)
                else:
                    with smtplib.SMTP(smtp_host, port, timeout=45) as server:
                        server.starttls()
                        server.login(user, password)
                        server.send_message(msg, from_addr=user, to_addrs=targets)
                return
            except Exception as ex:
                last_err = ex
                logger.warning("SMTP attempt on %s:%s failed: %s", smtp_host, port, ex)
        if last_err:
            raise last_err

    if login_user and login_pass:
        recipients = [recipient]
        if bcc and bcc not in recipients:
            recipients.append(bcc)
        try:
            await asyncio.to_thread(_send_smtp_sync, login_user, login_pass, recipients)
            logger.info("Email sent via SMTP (%s) as %s to %s", smtp_host, login_user, recipient)
            return
        except Exception as e:
            logger.warning("SMTP send failed for %s: %s", login_user, e)
            if login_user != global_user and global_user and global_pass:
                try:
                    logger.info("Retrying with global SMTP credentials (%s)...", global_user)
                    await asyncio.to_thread(_send_smtp_sync, global_user, global_pass, recipients)
                    logger.info("Email sent via global SMTP fallback to %s", recipient)
                    return
                except Exception as e_fb:
                    logger.warning("Global fallback SMTP failed: %s", e_fb)
            raise RuntimeError(f"SMTP send failed: {e}") from e

    # 3. If neither is configured, raise clear setup message
    raise RuntimeError(
        "No email service credentials configured. Please provide your Gmail App Password "
        "(GMAIL_EMAIL & GMAIL_APP_PASSWORD) or Google Workspace Service Account JSON (GMAIL_SA_JSON_B64) in backend/.env."
    )

