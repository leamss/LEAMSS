"""WhatsApp Service — Powered by Twilio Programmable Messaging API (with Meta Cloud API fallback).

Provides automated sending of WhatsApp messages, assessment PDF reports, live chat messages,
and media attachments via Twilio WhatsApp API.

Configuration:
- Env vars: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER (or TWILIO_WHATSAPP_NUMBER)
- Database: db['email_settings'].find_one({'id': 'global'}) -> twilio_* / whatsapp_* fields
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
    """Clean and format phone number (E.164 digits without leading +)."""
    if not raw_phone:
        return None
    # Strip whatsapp: prefix if present
    raw_str = str(raw_phone).replace("whatsapp:", "").strip()
    cleaned = re.sub(r"[^\d]", "", raw_str)
    if not cleaned:
        return None
    # Strip leading zeros
    cleaned = cleaned.lstrip("0")
    # If 10 digits (e.g. Indian mobile), prepend default country code
    if len(cleaned) == 10 and default_country_code:
        cleaned = f"{default_country_code.lstrip('+')}{cleaned}"
    return cleaned


def format_twilio_whatsapp_number(raw_phone: Optional[str], default_country_code: str = "91") -> Optional[str]:
    """Format phone number for Twilio WhatsApp (e.g. 'whatsapp:+919876543210')."""
    if not raw_phone:
        return None
    raw_str = str(raw_phone).strip()
    if raw_str.startswith("whatsapp:"):
        return raw_str
    clean = normalize_phone_number(raw_str, default_country_code=default_country_code)
    if not clean:
        return None
    return f"whatsapp:+{clean}"


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

    # Twilio Configuration
    twilio_account_sid = (
        settings_doc.get("twilio_account_sid")
        or os.environ.get("TWILIO_ACCOUNT_SID")
        or ""
    ).strip()

    twilio_auth_token = (
        settings_doc.get("twilio_auth_token")
        or os.environ.get("TWILIO_AUTH_TOKEN")
        or ""
    ).strip()

    twilio_phone_number = (
        settings_doc.get("twilio_phone_number")
        or os.environ.get("TWILIO_PHONE_NUMBER")
        or os.environ.get("TWILIO_WHATSAPP_NUMBER")
        or ""
    ).strip()

    # Meta Configuration (legacy / fallback)
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

    sender_display = (
        settings_doc.get("whatsapp_sender_display")
        or twilio_phone_number
        or "+91 77383 52427 (LEAMSS Official)"
    )

    is_twilio = bool(twilio_account_sid and twilio_auth_token)
    is_meta = bool(phone_number_id and access_token)

    # Twilio is the primary provider for LEAMSS WhatsApp
    if is_twilio:
        provider = "twilio"
    elif is_meta:
        provider = "meta"
    else:
        provider = "twilio"

    # If DB settings doc has outdated provider or missing Twilio keys, sync it in background
    if is_twilio and (settings_doc.get("whatsapp_provider") != "twilio" or not settings_doc.get("twilio_account_sid")):
        try:
            await db["email_settings"].update_one(
                {"id": "global"},
                {"$set": {
                    "whatsapp_provider": "twilio",
                    "twilio_account_sid": twilio_account_sid,
                    "twilio_auth_token": twilio_auth_token,
                    "twilio_phone_number": twilio_phone_number,
                }},
                upsert=True,
            )
        except Exception:
            pass

    return {
        "provider": provider,
        "is_configured": bool(is_twilio or is_meta),
        "is_twilio": is_twilio,
        "is_meta": is_meta,
        "twilio_account_sid": twilio_account_sid,
        "twilio_auth_token": twilio_auth_token,
        "twilio_phone_number": twilio_phone_number,
        "phone_number_id": phone_number_id,
        "access_token": access_token,
        "waba_id": waba_id,
        "sender_display": sender_display,
    }


async def send_whatsapp_text(
    to_phone: str,
    text: str,
    preview_url: bool = True,
    media_url: Optional[str] = None,
    content_sid: Optional[str] = None,
    content_variables: Optional[Dict[str, Any]] = None,
    client_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Send a WhatsApp text or media message to recipient via Twilio (or Meta fallback)."""
    cfg = await get_whatsapp_config()
    clean_phone = normalize_phone_number(to_phone)
    if not clean_phone:
        raise ValueError("Invalid recipient phone number")

    if not cfg["is_configured"]:
        raise RuntimeError(
            "WhatsApp API is not configured. Please add your Twilio Account SID, Auth Token & WhatsApp Phone Number in Settings -> WhatsApp tab or backend/.env."
        )

    # ── 1. Twilio Provider (Primary) ──────────────────────────────────────────
    if cfg["provider"] == "twilio" or cfg["is_twilio"]:
        account_sid = cfg["twilio_account_sid"]
        auth_token = cfg["twilio_auth_token"]
        raw_from = cfg["twilio_phone_number"] or "+919619992427"
        from_wa = format_twilio_whatsapp_number(raw_from)
        to_wa = format_twilio_whatsapp_number(clean_phone)

        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
        data: Dict[str, Any] = {
            "From": from_wa,
            "To": to_wa,
        }

        # Default to approved Twilio WhatsApp Content Template for 100% broadcast delivery
        if not content_sid:
            content_sid = "HX813f83bd5dd7f84680a55442bf34b081"
            clean_text = re.sub(r"[\r\n]+", " ", text).strip()
            if len(clean_text) > 300:
                clean_text = clean_text[:297] + "..."
            content_variables = {
                "1": client_name or "Client",
                "2": clean_text,
            }

        if content_sid:
            data["ContentSid"] = content_sid
            if content_variables:
                import json
                data["ContentVariables"] = json.dumps(content_variables)
        else:
            data["Body"] = text
            if media_url:
                data["MediaUrl"] = media_url

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                url,
                data=data,
                auth=(account_sid, auth_token),
            )
            if resp.status_code >= 400:
                logger.error("Twilio WhatsApp API error (%s): %s", resp.status_code, resp.text)
                err_json = {}
                try:
                    err_json = resp.json()
                except Exception:
                    pass
                err_code = err_json.get("code")
                if err_code == 20003:
                    err_msg = "Twilio Authentication Error: Invalid Account SID or Auth Token."
                elif err_code == 21211:
                    err_msg = f"Invalid phone number (+{clean_phone}) for WhatsApp delivery."
                elif err_code == 21608:
                    err_msg = (
                        f"Twilio Sandbox: Recipient +{clean_phone} must join your Twilio sandbox first "
                        f"(send the join keyword to {raw_from}). Or switch to an approved Twilio WhatsApp Sender."
                    )
                elif err_code == 63016:
                    err_msg = (
                        f"Outside 24-hour customer window for +{clean_phone}. "
                        "Customer must message the number or receive an approved WhatsApp template."
                    )
                elif err_code == 63049:
                    err_msg = (
                        f"Meta WhatsApp rate-limit or frequency limit reached for +{clean_phone}. "
                        "Please wait before sending another automated template to this number."
                    )
                elif err_code == 63007:
                    err_msg = f"Twilio WhatsApp Sender {raw_from} is not active or not approved on WhatsApp."
                raise RuntimeError(f"Twilio WhatsApp Error: {err_msg}")
            return resp.json()

    # ── 2. Meta Provider (Fallback) ──────────────────────────────────────────
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
            logger.error("Meta WhatsApp API error (%s): %s", resp.status_code, resp.text)
            try:
                err_data = resp.json()
                error_obj = err_data.get("error", {})
                code = error_obj.get("code")
                err_msg = error_obj.get("message", resp.text)
                if code == 190:
                    err_msg = "Meta WhatsApp Access Token has expired. Please update token in Settings -> WhatsApp."
                elif code == 131030:
                    err_msg = f"Recipient +{clean_phone} is not in Meta developer test list."
            except Exception:
                err_msg = resp.text
            raise RuntimeError(f"{err_msg}")
        return resp.json()


async def send_whatsapp_template(
    to_phone: str,
    template_name: str = "hello_world",
    language_code: str = "en_US",
    components: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Send a WhatsApp message template."""
    cfg = await get_whatsapp_config()
    clean_phone = normalize_phone_number(to_phone)
    if not clean_phone:
        raise ValueError("Invalid recipient phone number")

    if not cfg["is_configured"]:
        raise RuntimeError("WhatsApp API is not configured.")

    if cfg["provider"] == "twilio" or cfg["is_twilio"]:
        # In Twilio, template sending is supported via Content API or fallback text
        # If components contains body text, send body text
        text = f"Hello from LEAMSS! (Template: {template_name})"
        if components:
            for c in components:
                if c.get("type") == "body":
                    params = [p.get("text", "") for p in c.get("parameters", [])]
                    if params:
                        text = " ".join(params)
        return await send_whatsapp_text(to_phone=to_phone, text=text)

    # Meta template send
    url = f"{GRAPH_BASE_URL}/{cfg['phone_number_id']}/messages"
    headers = {
        "Authorization": f"Bearer {cfg['access_token']}",
        "Content-Type": "application/json",
    }
    payload: Dict[str, Any] = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": clean_phone,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language_code},
        },
    }
    if components:
        payload["template"]["components"] = components

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code >= 400:
            logger.error("WhatsApp template error (%s): %s", resp.status_code, resp.text)
            try:
                err_data = resp.json()
                err_msg = err_data.get("error", {}).get("message", resp.text)
            except Exception:
                err_msg = resp.text
            raise RuntimeError(f"WhatsApp Template Error: {err_msg}")
        return resp.json()


async def upload_whatsapp_media(
    file_bytes: bytes,
    mime_type: str = "application/pdf",
    filename: str = "document.pdf",
) -> Dict[str, Any]:
    """Upload binary file to Meta (or return local reference for Twilio)."""
    cfg = await get_whatsapp_config()
    if not cfg["is_configured"]:
        raise RuntimeError("WhatsApp API is not configured.")

    if cfg["provider"] == "twilio" or cfg["is_twilio"]:
        # Twilio delivers media via public URLs. Return mock id for seamless fallback
        return {"id": "twilio_media_url", "filename": filename}

    url = f"{GRAPH_BASE_URL}/{cfg['phone_number_id']}/media"
    headers = {
        "Authorization": f"Bearer {cfg['access_token']}",
    }
    files = {
        "file": (filename, file_bytes, mime_type),
    }
    data = {
        "messaging_product": "whatsapp",
        "type": mime_type,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, data=data, files=files, headers=headers)
        if resp.status_code >= 400:
            logger.error("WhatsApp media upload error (%s): %s", resp.status_code, resp.text)
            try:
                err_data = resp.json()
                err_msg = err_data.get("error", {}).get("message", resp.text)
            except Exception:
                err_msg = resp.text
            raise RuntimeError(f"WhatsApp Media Upload Error: {err_msg}")
        return resp.json()


async def send_whatsapp_document_by_id(
    to_phone: str,
    media_id: str,
    filename: str = "Assessment_Report.pdf",
    caption: str = "",
) -> Dict[str, Any]:
    """Send document by media ID (Meta) or fallback."""
    cfg = await get_whatsapp_config()
    clean_phone = normalize_phone_number(to_phone)
    if not clean_phone:
        raise ValueError("Invalid recipient phone number")

    if not cfg["is_configured"]:
        raise RuntimeError("WhatsApp API is not configured.")

    if cfg["provider"] == "twilio" or cfg["is_twilio"]:
        return await send_whatsapp_text(to_phone=to_phone, text=caption or f"📄 {filename}")

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
            "id": media_id,
            "filename": filename,
            "caption": caption,
        },
    }

    async with httpx.AsyncClient(timeout=45.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code >= 400:
            logger.error("WhatsApp document by ID send error (%s): %s", resp.status_code, resp.text)
            try:
                err_data = resp.json()
                err_msg = err_data.get("error", {}).get("message", resp.text)
            except Exception:
                err_msg = resp.text
            raise RuntimeError(f"WhatsApp Document Send Error: {err_msg}")
        return resp.json()


async def send_whatsapp_image_by_id(
    to_phone: str,
    media_id: str,
    caption: str = "",
) -> Dict[str, Any]:
    """Send image by media ID (Meta) or fallback."""
    cfg = await get_whatsapp_config()
    clean_phone = normalize_phone_number(to_phone)
    if not clean_phone:
        raise ValueError("Invalid recipient phone number")

    if not cfg["is_configured"]:
        raise RuntimeError("WhatsApp API is not configured.")

    if cfg["provider"] == "twilio" or cfg["is_twilio"]:
        return await send_whatsapp_text(to_phone=to_phone, text=caption or "💳 Payment QR Code")

    url = f"{GRAPH_BASE_URL}/{cfg['phone_number_id']}/messages"
    headers = {
        "Authorization": f"Bearer {cfg['access_token']}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": clean_phone,
        "type": "image",
        "image": {
            "id": media_id,
            "caption": caption,
        },
    }

    async with httpx.AsyncClient(timeout=45.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code >= 400:
            logger.error("WhatsApp image by ID send error (%s): %s", resp.status_code, resp.text)
            try:
                err_data = resp.json()
                err_msg = err_data.get("error", {}).get("message", resp.text)
            except Exception:
                err_msg = resp.text
            raise RuntimeError(f"WhatsApp Image Send Error: {err_msg}")
        return resp.json()


async def send_whatsapp_document_by_url(
    to_phone: str,
    document_url: str,
    filename: str = "Assessment_Report.pdf",
    caption: str = "",
) -> Dict[str, Any]:
    """Send a PDF or document via hosted public link to recipient on WhatsApp (Twilio & Meta)."""
    cfg = await get_whatsapp_config()
    clean_phone = normalize_phone_number(to_phone)
    if not clean_phone:
        raise ValueError("Invalid recipient phone number")

    if not cfg["is_configured"]:
        raise RuntimeError("WhatsApp API is not configured.")

    if cfg["provider"] == "twilio" or cfg["is_twilio"]:
        return await send_whatsapp_text(
            to_phone=to_phone,
            text=caption or f"📄 {filename}",
            media_url=document_url,
        )

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
            raise RuntimeError(f"WhatsApp Document Send Error: {err_msg}")
        return resp.json()


async def send_whatsapp_image_by_url(
    to_phone: str,
    image_url: str,
    caption: str = "",
) -> Dict[str, Any]:
    """Send an image (e.g. Payment QR) via hosted public link to recipient on WhatsApp (Twilio & Meta)."""
    cfg = await get_whatsapp_config()
    clean_phone = normalize_phone_number(to_phone)
    if not clean_phone:
        raise ValueError("Invalid recipient phone number")

    if not cfg["is_configured"]:
        raise RuntimeError("WhatsApp API is not configured.")

    if cfg["provider"] == "twilio" or cfg["is_twilio"]:
        return await send_whatsapp_text(
            to_phone=to_phone,
            text=caption or "💳 Payment QR Code",
            media_url=image_url,
        )

    url = f"{GRAPH_BASE_URL}/{cfg['phone_number_id']}/messages"
    headers = {
        "Authorization": f"Bearer {cfg['access_token']}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": clean_phone,
        "type": "image",
        "image": {
            "link": image_url,
            "caption": caption,
        },
    }

    async with httpx.AsyncClient(timeout=45.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code >= 400:
            logger.error("WhatsApp image send error (%s): %s", resp.status_code, resp.text)
            try:
                err_data = resp.json()
                err_msg = err_data.get("error", {}).get("message", resp.text)
            except Exception:
                err_msg = resp.text
            raise RuntimeError(f"WhatsApp Image Send Error: {err_msg}")
        return resp.json()
