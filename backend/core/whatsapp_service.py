"""Meta WhatsApp Cloud API Service.

Provides automated sending of WhatsApp messages, pre-assessment / assessment PDF reports,
and template messages via Meta Graph API v19.0+.

Configuration:
- Env vars: WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_WABA_ID
- Database: db['email_settings'].find_one({'id': 'global'}) -> whatsapp_* fields
"""
from __future__ import annotations

import os
import re
import logging
import httpx
from typing import Optional, Dict, Any, List

logger = logging.getLogger("whatsapp_service")

GRAPH_API_VERSION = "v21.0"
GRAPH_BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


def normalize_phone_number(raw_phone: Optional[str], default_country_code: str = "91") -> Optional[str]:
    """Clean and format phone number for WhatsApp Cloud API (E.164 without leading +)."""
    if not raw_phone:
        return None
    cleaned = re.sub(r"[^\d]", "", str(raw_phone).strip())
    if not cleaned:
        return None
    # Strip leading zeros
    cleaned = cleaned.lstrip("0")
    # If 10 digits (standard Indian mobile), prepend default country code
    if len(cleaned) == 10 and default_country_code:
        cleaned = f"{default_country_code.lstrip('+')}{cleaned}"
    return cleaned


async def get_whatsapp_config() -> Dict[str, Any]:
    """Retrieve WhatsApp configuration from database settings or environment variables."""
    from core.database import db
    try:
        from dotenv import load_dotenv
        load_dotenv()
        load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
    except Exception:
        pass

    try:
        settings_doc = await db["email_settings"].find_one({"id": "global"}) or {}
    except Exception:
        settings_doc = {}

    phone_number_id = (
        settings_doc.get("whatsapp_phone_number_id")
        or os.environ.get("WHATSAPP_PHONE_NUMBER_ID")
        or ""
    ).strip()

    access_token = (
        settings_doc.get("whatsapp_access_token")
        or os.environ.get("WHATSAPP_ACCESS_TOKEN")
        or ""
    ).strip()

    waba_id = (
        settings_doc.get("whatsapp_waba_id")
        or os.environ.get("WHATSAPP_WABA_ID")
        or ""
    ).strip()

    sender_display = settings_doc.get("whatsapp_sender_display") or "+91 77383 52427 (LEAMSS Official)"

    return {
        "is_configured": bool(phone_number_id and access_token),
        "phone_number_id": phone_number_id,
        "access_token": access_token,
        "waba_id": waba_id,
        "sender_display": sender_display,
    }


async def send_whatsapp_text(
    to_phone: str,
    text: str,
    preview_url: bool = True,
) -> Dict[str, Any]:
    """Send a plain text or link message to recipient via WhatsApp Cloud API."""
    cfg = await get_whatsapp_config()
    clean_phone = normalize_phone_number(to_phone)
    if not clean_phone:
        raise ValueError("Invalid recipient phone number")

    if not cfg["is_configured"]:
        logger.warning("WhatsApp API not configured. Simulated dispatch to %s", clean_phone)
        return {
            "status": "simulated",
            "sent_to": clean_phone,
            "message": "WhatsApp API credentials not configured yet. Message simulated successfully.",
            "text": text,
        }

    url = f"{GRAPH_BASE_URL}/{cfg['phone_number_id']}/messages"
    headers = {
        "Authorization": f"Bearer {cfg['access_token']}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": clean_phone,
        "type": "text",
        "text": {
            "preview_url": preview_url,
            "body": text,
        },
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code >= 400:
            logger.error("WhatsApp API error (%s): %s", resp.status_code, resp.text)
            try:
                err_data = resp.json()
                error_obj = err_data.get("error", {})
                code = error_obj.get("code")
                err_msg = error_obj.get("message", resp.text)
                if code == 131030 or "not in allowed list" in err_msg.lower():
                    err_msg = f"Recipient +{clean_phone} is not in Meta developer test list. Click 'Open WhatsApp Web' to send directly, or add this number to the test recipient list in Meta Developers."
                elif code == 131047 or "24 hours" in err_msg.lower():
                    err_msg = f"Cannot send direct template outside 24h window. Please click 'Open WhatsApp Web' to send directly to +{clean_phone}."
                elif code == 200:
                    err_msg = "Meta Cloud API Permissions error. Please use 'Open WhatsApp Web' for direct sending."
            except Exception:
                err_msg = resp.text
            raise RuntimeError(f"{err_msg}")
        return resp.json()


async def send_whatsapp_document_by_url(
    to_phone: str,
    document_url: str,
    filename: str = "Assessment_Report.pdf",
    caption: str = "",
) -> Dict[str, Any]:
    """Send a PDF or document via hosted public link to recipient on WhatsApp."""
    cfg = await get_whatsapp_config()
    clean_phone = normalize_phone_number(to_phone)
    if not clean_phone:
        raise ValueError("Invalid recipient phone number")

    if not cfg["is_configured"]:
        logger.warning("WhatsApp API not configured. Simulated document dispatch to %s", clean_phone)
        return {
            "status": "simulated",
            "sent_to": clean_phone,
            "document_url": document_url,
            "filename": filename,
            "caption": caption,
        }

    url = f"{GRAPH_BASE_URL}/{cfg['phone_number_id']}/messages"
    headers = {
        "Authorization": f"Bearer {cfg['access_token']}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": clean_phone,
        "type": "document",
        "document": {
            "link": document_url,
            "filename": filename,
            "caption": caption,
        },
    }

    async with httpx.AsyncClient(timeout=45.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code >= 400:
            logger.error("WhatsApp document send error (%s): %s", resp.status_code, resp.text)
            try:
                err_data = resp.json()
                err_msg = err_data.get("error", {}).get("message", resp.text)
            except Exception:
                err_msg = resp.text
            raise RuntimeError(f"WhatsApp Cloud API Error: {err_msg}")
        return resp.json()
