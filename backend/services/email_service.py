"""Option 1 / Z3 — Centralised Email Service with Resend graceful fallback.

When `RESEND_API_KEY` env var is present, sends real email via Resend.
Otherwise, logs an `EMAIL_PREVIEW_LOGGED` line for inspection and returns
a `preview_only` status. Every email send (real or preview) is audit-logged.

Usage:
    from services.email_service import send_email
    await send_email(to="x@y.com", subject="Hi", html_body="<p>Hi</p>")
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DEFAULT_FROM_ADDRESS = "hello@leamss.com"
RESEND_KEY_ENV = "RESEND_API_KEY"


async def send_email(
    to: str,
    subject: str,
    html_body: str,
    text_body: Optional[str] = None,
    from_name: str = "LEAMSS",
    from_address: Optional[str] = None,
) -> Dict[str, Any]:
    """Send an email. Graceful fallback to preview when no API key.

    Returns a status dict:
      {"status": "sent" | "preview_only" | "error", ...}
    """
    api_key = os.environ.get(RESEND_KEY_ENV)
    from_addr = from_address or DEFAULT_FROM_ADDRESS
    sender = f"{from_name} <{from_addr}>"

    # Always audit
    audit_record = {
        "to": to, "subject": subject, "from": sender,
        "html_length": len(html_body or ""),
        "has_key": bool(api_key),
        "at": datetime.now(timezone.utc).isoformat(),
    }

    if not api_key:
        # Preview-only mode (key not yet provided)
        logger.info(
            f"EMAIL_PREVIEW_LOGGED: to={to} from={sender} subject={subject!r} "
            f"len={len(html_body or '')}"
        )
        return {"status": "preview_only", "to": to,
                "subject": subject, "delivery": "logged",
                **audit_record}

    # Real send via Resend
    try:
        import resend
        resend.api_key = api_key
        payload = {
            "from": sender, "to": [to] if isinstance(to, str) else to,
            "subject": subject, "html": html_body,
        }
        if text_body:
            payload["text"] = text_body
        result = resend.Emails.send(payload)
        message_id = result.get("id") if isinstance(result, dict) else getattr(result, "id", None)
        return {"status": "sent", "message_id": message_id,
                "to": to, "delivery": "resend", **audit_record}
    except ImportError:
        logger.warning("RESEND_API_KEY set but `resend` package not installed; falling back to preview mode")
        return {"status": "preview_only", "to": to,
                "error": "resend_package_not_installed",
                **audit_record}
    except Exception as e:  # noqa: BLE001
        logger.error(f"[email_service] Resend send failed: {e!r}")
        return {"status": "error", "to": to, "error": str(e)[:200], **audit_record}
