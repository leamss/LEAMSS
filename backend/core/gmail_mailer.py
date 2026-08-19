"""Gmail SMTP mailer — send emails (with PDF attachments) directly from the
consultant's own Google / Workspace account (e.g. rohit@leamss.com) using an
App Password. Kept separate from core.email_service (Resend, in-app transactional
mails) so existing flows stay untouched.

Config (backend/.env):
  GMAIL_EMAIL          e.g. rohit@leamss.com
  GMAIL_APP_PASSWORD   16-char Google App Password (2-Step Verification required)
  SENDER_NAME          display name, e.g. "Rohit · LEAMSS"
  GMAIL_DAILY_BUDGET   optional cap (default 1800, below Google's 2000/day ceiling)
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import datetime, timezone
from email.message import EmailMessage
from html import escape
from typing import Optional, Tuple

import aiosmtplib

logger = logging.getLogger("gmail_mailer")

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
DAILY_BUDGET = int(os.environ.get("GMAIL_DAILY_BUDGET", "1800"))
MIN_INTERVAL_SECONDS = float(os.environ.get("GMAIL_MIN_INTERVAL", "0.8"))

BRAND_TEAL = "#1F4D44"
BRAND_ORANGE = "#D4633F"
COMPANY = "Ladhani Education & Migration Services"
TAGLINE = "We Value Emotions"
CONTACT_LINE = "Toll-Free 1800-210-2427 · +91 77188-82427 · Thane, Mumbai"


def _cfg() -> Tuple[str, str, str]:
    email = (os.environ.get("GMAIL_EMAIL") or "").strip()
    pw = (os.environ.get("GMAIL_APP_PASSWORD") or "").replace(" ", "").strip()
    name = (os.environ.get("SENDER_NAME") or "LEAMSS").strip()
    return email, pw, name


def is_configured() -> bool:
    email, pw, _ = _cfg()
    return bool(email and pw)


def sender_address() -> Optional[str]:
    email, _, _ = _cfg()
    return email or None


def sender_display_name() -> str:
    _, _, name = _cfg()
    return name


def _quota_key() -> str:
    email, _, _ = _cfg()
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"{day}:{email}"


async def remaining_budget() -> int:
    if not is_configured():
        return 0
    from core.database import db
    doc = await db["email_quota"].find_one({"_id": _quota_key()}, {"count": 1})
    return max(0, DAILY_BUDGET - (doc or {}).get("count", 0))


class GmailMailer:
    """One serialized async SMTP path with pacing + a persisted daily quota."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._last_sent = 0.0

    async def send(
        self, *, recipient: str, subject: str, html: str, plain: str,
        pdf_bytes: Optional[bytes] = None, filename: str = "report.pdf",
        bcc: Optional[str] = None,
    ) -> None:
        email, pw, name = _cfg()
        if not (email and pw):
            raise RuntimeError(
                "Gmail is not configured. Add GMAIL_APP_PASSWORD in backend/.env "
                "and restart the backend."
            )
        from core.database import db
        key = _quota_key()
        doc = await db["email_quota"].find_one({"_id": key}, {"count": 1})
        if (doc or {}).get("count", 0) >= DAILY_BUDGET:
            raise RuntimeError(
                f"Daily Gmail limit ({DAILY_BUDGET}) reached for {email}. "
                "Please continue tomorrow."
            )

        msg = EmailMessage()
        msg["From"] = f"{name} <{email}>" if name else email
        msg["To"] = recipient
        msg["Subject"] = subject
        recipients = [recipient]
        if bcc:
            msg["Bcc"] = bcc
            recipients.append(bcc)
        msg.set_content(plain or "Please open this email in an HTML-capable client.")
        msg.add_alternative(html, subtype="html")
        if pdf_bytes:
            msg.add_attachment(pdf_bytes, maintype="application", subtype="pdf", filename=filename)

        async with self._lock:
            wait = MIN_INTERVAL_SECONDS - (time.monotonic() - self._last_sent)
            if wait > 0:
                await asyncio.sleep(wait)
            try:
                async with aiosmtplib.SMTP(
                    hostname=SMTP_HOST, port=SMTP_PORT, start_tls=True, timeout=30,
                ) as smtp:
                    await smtp.login(email, pw)
                    await smtp.send_message(msg, sender=email, recipients=recipients)
            except aiosmtplib.SMTPAuthenticationError as e:
                logger.error("Gmail authentication failed for %s", email)
                raise RuntimeError(
                    "Gmail authentication failed. Ensure GMAIL_APP_PASSWORD is a valid "
                    "16-char App Password (not the normal password) and 2-Step "
                    "Verification is ON for this account."
                ) from e
            except (aiosmtplib.SMTPException, OSError, asyncio.TimeoutError) as e:
                logger.exception("Gmail SMTP delivery failed")
                raise RuntimeError(
                    f"Email delivery failed ({type(e).__name__}). Please try again shortly."
                ) from e
            self._last_sent = time.monotonic()

        await db["email_quota"].update_one(
            {"_id": key},
            {"$inc": {"count": 1}, "$set": {"updated_at": datetime.now(timezone.utc), "sender": email}},
            upsert=True,
        )


mailer = GmailMailer()


def build_report_email(
    client_name: str, *, occupation: Optional[str] = None, code: Optional[str] = None,
    points: Optional[dict] = None, sender_name: str = "LEAMSS",
) -> Tuple[str, str, str]:
    """Branded LEAMSS pre-assessment report email → (subject, html, plain)."""
    name = escape(client_name or "Applicant")
    subject = f"Your Australia PR Pre-Assessment Report — {client_name}".strip()

    occ_line = ""
    if code or occupation:
        occ_txt = " · ".join([x for x in [escape(str(code)) if code else "", escape(occupation) if occupation else ""] if x])
        occ_line = f'<tr><td style="padding:4px 0;color:{BRAND_TEAL};font-weight:600;">Occupation</td><td style="padding:4px 0;color:#334155;">{occ_txt}</td></tr>'

    pts_line = ""
    if points and isinstance(points, dict):
        parts = []
        for sc in ("189", "190", "491"):
            if points.get(sc) is not None:
                parts.append(f"{sc}: <b>{points[sc]}</b>")
        if parts:
            pts_line = (f'<tr><td style="padding:4px 0;color:{BRAND_TEAL};font-weight:600;">Indicative Points</td>'
                        f'<td style="padding:4px 0;color:#334155;">{" &nbsp;·&nbsp; ".join(parts)}</td></tr>')

    summary_table = ""
    if occ_line or pts_line:
        summary_table = (
            f'<table style="width:100%;border-collapse:collapse;background:#f8faf9;'
            f'border:1px solid #e2e8e5;border-radius:8px;margin:18px 0;padding:6px 14px;font-size:14px;">'
            f'{occ_line}{pts_line}</table>'
        )

    html = f"""<!DOCTYPE html>
<html><body style="margin:0;padding:0;background:#eef2f1;font-family:'Segoe UI',Arial,sans-serif;">
  <div style="max-width:600px;margin:0 auto;background:#ffffff;">
    <div style="background:{BRAND_TEAL};padding:26px 32px;">
      <h1 style="color:#ffffff;margin:0;font-size:20px;font-weight:700;letter-spacing:0.3px;">{escape(COMPANY)}</h1>
      <p style="color:{BRAND_ORANGE};margin:4px 0 0;font-size:13px;font-style:italic;font-weight:600;">{escape(TAGLINE)}</p>
    </div>
    <div style="padding:30px 32px;">
      <p style="color:#1f2937;font-size:15px;line-height:1.6;margin:0 0 12px;">Dear {name},</p>
      <p style="color:#374151;font-size:14px;line-height:1.7;margin:0 0 8px;">
        Thank you for connecting with us. Please find your <b>Australia PR Pre-Assessment Report</b>
        attached to this email (PDF). It covers your eligible skilled visa pathways (subclass 189 / 190 / 491),
        indicative points, occupation deep-dive, SkillSelect competition and the investment involved.
      </p>
      {summary_table}
      <p style="color:#374151;font-size:14px;line-height:1.7;margin:8px 0 0;">
        This is an indicative assessment. Our migration team will be glad to walk you through the report
        and plan your next steps. Simply reply to this email or call us on the numbers below.
      </p>
      <div style="text-align:center;margin:24px 0 8px;">
        <a href="tel:18002102427" style="background:{BRAND_ORANGE};color:#ffffff;text-decoration:none;
           font-size:14px;font-weight:600;padding:12px 26px;border-radius:24px;display:inline-block;">
          Book a Free Consultation
        </a>
      </div>
    </div>
    <div style="background:#f5f7f6;padding:18px 32px;border-top:1px solid #e5e9e7;">
      <p style="color:#64748b;font-size:12px;margin:0;">{escape(sender_name)} — {escape(COMPANY)}</p>
      <p style="color:#94a3b8;font-size:11px;margin:6px 0 0;">{escape(CONTACT_LINE)}</p>
      <p style="color:#94a3b8;font-size:10px;margin:8px 0 0;line-height:1.5;">
        This assessment is based on the information provided and current publicly available migration rules.
        It is indicative only and not legal or migration advice under any contract until formally engaged.
      </p>
    </div>
  </div>
</body></html>"""

    plain_parts = [f"Dear {client_name or 'Applicant'},", "",
                   "Thank you for connecting with us. Your Australia PR Pre-Assessment Report is attached (PDF).",
                   "It covers your eligible pathways (189/190/491), indicative points, occupation deep-dive and investment."]
    if code or occupation:
        plain_parts.append(f"Occupation: {code or ''} {occupation or ''}".strip())
    if points and isinstance(points, dict):
        pp = " · ".join([f"{sc}: {points[sc]}" for sc in ("189", "190", "491") if points.get(sc) is not None])
        if pp:
            plain_parts.append(f"Indicative points — {pp}")
    plain_parts += ["", "Reply to this email or call Toll-Free 1800-210-2427 to book a free consultation.",
                    "", f"{sender_name} — {COMPANY}", CONTACT_LINE]
    plain = "\n".join(plain_parts)
    return subject, html, plain
