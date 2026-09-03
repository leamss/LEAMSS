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
    return _sa_info() is not None and bool(default_sender())


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
    if not is_configured():
        raise RuntimeError(
            "Gmail (domain-wide delegation) is not configured. Add GMAIL_SA_JSON_B64 in "
            "backend/.env and complete the Google Admin console authorization."
        )
    sender_email = (sender_email or default_sender()).strip().lower()
    dom = delegated_domain()
    if dom and not sender_email.endswith("@" + dom):
        raise RuntimeError(f"Sender {sender_email} is not on the delegated domain @{dom}.")

    from core.database import db
    key = _quota_key(sender_email)
    doc = await db["email_quota"].find_one({"_id": key}, {"count": 1})
    if (doc or {}).get("count", 0) >= DAILY_BUDGET:
        raise RuntimeError(f"Daily limit ({DAILY_BUDGET}) reached for {sender_email}. Continue tomorrow.")

    msg = EmailMessage()
    # Header values must not contain CR/LF — collapse any newlines/tabs to single spaces.
    def _hdr(v):
        return " ".join(str(v or "").replace("\r", " ").replace("\n", " ").split())
    from_name = _hdr(sender_name)
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

    try:
        await asyncio.to_thread(_send_sync, sender_email, msg.as_bytes())
    except Exception as e:  # noqa: BLE001
        try:
            from googleapiclient.errors import HttpError
        except Exception:
            HttpError = tuple()
        if HttpError and isinstance(e, HttpError):
            code = getattr(getattr(e, "resp", None), "status", "?")
            reason = getattr(e, "_get_reason", lambda: "")() or "send failed"
            logger.error("Gmail API HttpError %s: %s", code, reason)
            raise RuntimeError(
                f"Gmail API error {code}: {reason}. Verify the sender {sender_email} exists and "
                "that the service account is authorized for gmail.send in the Admin console."
            ) from e
        low = str(e).lower()
        if "unauthorized_client" in low or "access_denied" in low or "delegation" in low:
            raise RuntimeError(
                "Delegation denied. In Google Admin console → Security → API controls → "
                "Domain-wide delegation, authorize the service account Client ID with scope "
                "https://www.googleapis.com/auth/gmail.send."
            ) from e
        logger.exception("Gmail DWD send failed")
        raise RuntimeError(f"Email send failed ({type(e).__name__}). Please try again shortly.") from e

    await db["email_quota"].update_one(
        {"_id": key},
        {"$inc": {"count": 1}, "$set": {"updated_at": datetime.now(timezone.utc), "sender": sender_email}},
        upsert=True,
    )
