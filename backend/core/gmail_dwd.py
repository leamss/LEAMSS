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
    return (os.environ.get("GMAIL_DEFAULT_SENDER") or "").strip().lower()


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
    if _sa_info() is not None and bool(default_sender()):
        return True
    if (os.environ.get("GMAIL_EMAIL") or os.environ.get("SMTP_USER")) and (os.environ.get("GMAIL_APP_PASSWORD") or os.environ.get("SMTP_PASS") or os.environ.get("SMTP_PASSWORD")):
        return True
    if os.environ.get("RESEND_API_KEY") and os.environ.get("RESEND_API_KEY") != "re_your_api_key_here":
        return True
    return False


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

    # Build standard email message
    msg = EmailMessage()
    def _hdr(v):
        return " ".join(str(v or "").replace("\r", " ").replace("\n", " ").split())
    from_name = _hdr(sender_name or os.environ.get("SENDER_NAME") or "LEAMSS")
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

    # 2. Try SMTP with Gmail App Password or SMTP credentials
    smtp_user = os.environ.get("GMAIL_EMAIL") or os.environ.get("SMTP_USER") or sender_email
    smtp_pass = os.environ.get("GMAIL_APP_PASSWORD") or os.environ.get("SMTP_PASS") or os.environ.get("SMTP_PASSWORD")
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))

    if smtp_user and smtp_pass:
        import aiosmtplib
        recipients = [recipient]
        if bcc:
            recipients.append(bcc)
        try:
            async with aiosmtplib.SMTP(hostname=smtp_host, port=smtp_port, start_tls=True, timeout=30) as smtp:
                await smtp.login(smtp_user, smtp_pass.replace(" ", "").strip())
                await smtp.send_message(msg, sender=smtp_user, recipients=recipients)
            logger.info("Email sent via SMTP (%s) to %s", smtp_host, recipient)
            return
        except Exception as e:
            logger.warning("SMTP send failed: %s", e)
            raise RuntimeError(f"SMTP send failed: {e}") from e

    # 3. If neither is configured, raise clear setup message
    raise RuntimeError(
        "No email service credentials configured. Please provide your Gmail App Password "
        "(GMAIL_EMAIL & GMAIL_APP_PASSWORD) or Google Workspace Service Account JSON (GMAIL_SA_JSON_B64) in backend/.env."
    )

