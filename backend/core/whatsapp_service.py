"""WhatsApp Service — Powered by Twilio Programmable Messaging & Meta WhatsApp Cloud API.

Provides automated sending and receiving of WhatsApp messages, assessment PDF reports,
live chat messages, media attachments (images, PDFs, documents, audio), interactive templates,
webhook signature verification, and live diagnostics.

Configuration:
- Twilio: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER
- Meta: WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_WABA_ID, WHATSAPP_APP_SECRET, WHATSAPP_VERIFY_TOKEN
- Database: db['email_settings'].find_one({'id': 'global'})
"""
from __future__ import annotations

import os
import re
import hmac
import hashlib
import logging
import io
import httpx
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone

logger = logging.getLogger("whatsapp_service")

GRAPH_API_VERSION = "v21.0"
GRAPH_BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"
DEFAULT_VERIFY_TOKEN = "leamss_wa_verify_token_2026"


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
    elif len(cleaned) == 9 and cleaned.startswith("4"):
        cleaned = f"61{cleaned}"
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

    app_secret = (
        settings_doc.get("whatsapp_app_secret")
        or os.environ.get("WHATSAPP_APP_SECRET")
        or ""
    ).strip()

    verify_token = (
        settings_doc.get("whatsapp_verify_token")
        or os.environ.get("WHATSAPP_VERIFY_TOKEN")
        or DEFAULT_VERIFY_TOKEN
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
        "app_secret": app_secret,
        "verify_token": verify_token,
        "sender_display": sender_display,
    }


def verify_meta_signature(raw_body: bytes, signature_header: Optional[str], app_secret: str) -> bool:
    """Validate X-Hub-Signature-256 header sent by Meta Webhooks using HMAC-SHA256."""
    if not app_secret:
        # If no secret configured yet, log warning and allow payload during setup
        logger.warning("No WHATSAPP_APP_SECRET configured. Skipping HMAC signature validation.")
        return True
    if not signature_header:
        logger.warning("Missing X-Hub-Signature-256 header from incoming webhook request.")
        return False

    expected_sig = signature_header.replace("sha256=", "").strip()
    mac = hmac.new(app_secret.encode("utf-8"), raw_body, hashlib.sha256)
    computed_sig = mac.hexdigest()
    return hmac.compare_digest(computed_sig, expected_sig)


async def test_whatsapp_connection() -> Dict[str, Any]:
    """Test live connectivity with Meta Graph API and retrieve account status."""
    cfg = await get_whatsapp_config()
    if not cfg["is_configured"]:
        return {
            "connected": False,
            "error": "WhatsApp Phone Number ID and Permanent Access Token are required.",
            "is_configured": False
        }

    url = f"{GRAPH_BASE_URL}/{cfg['phone_number_id']}"
    headers = {
        "Authorization": f"Bearer {cfg['access_token']}",
    }
    params = {
        "fields": "verified_name,display_phone_number,quality_rating,code_verification_status,messaging_limit_tier"
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=headers, params=params)
            if resp.status_code >= 400:
                err_text = resp.text
                try:
                    err_json = resp.json()
                    err_text = err_json.get("error", {}).get("message", resp.text)
                except Exception:
                    pass
                return {
                    "connected": False,
                    "status_code": resp.status_code,
                    "error": err_text,
                    "is_configured": True
                }

            data = resp.json()
            return {
                "connected": True,
                "is_configured": True,
                "verified_name": data.get("verified_name"),
                "display_phone_number": data.get("display_phone_number"),
                "quality_rating": data.get("quality_rating"),
                "verification_status": data.get("code_verification_status"),
                "messaging_limit_tier": data.get("messaging_limit_tier"),
            }
    except Exception as e:
        logger.error(f"Error testing Meta WhatsApp connection: {e}")
        return {
            "connected": False,
            "error": str(e),
            "is_configured": True
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
        logger.warning("WhatsApp API not configured. Simulated dispatch to %s", clean_phone)
        return {
            "status": "simulated",
            "sent_to": clean_phone,
            "message": "WhatsApp API credentials not configured yet. Message saved in CRM.",
            "text": text,
            "meta_message_id": None,
        }

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

        if content_sid:
            data["ContentSid"] = content_sid
            if content_variables:
                import json
                sanitized_vars = {}
                for k, v in content_variables.items():
                    if v is not None:
                        s_val = str(v).replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
                        s_val = re.sub(r"\s+", " ", s_val).strip()
                        sanitized_vars[str(k)] = s_val
                data["ContentVariables"] = json.dumps(sanitized_vars)
            if media_url:
                data["MediaUrl"] = media_url
        else:
            # Twilio WhatsApp strict limit is 1600 characters (Error 21617)
            body_text = str(text or "").strip()
            if len(body_text) > 1550:
                logger.warning("Message body exceeds 1550 chars (%d chars); trimming to prevent Twilio Error 21617", len(body_text))
                # Find last clean newline or sentence before 1540 chars
                cut_idx = body_text[:1540].rfind("\n\n")
                if cut_idx == -1 or cut_idx < 1000:
                    cut_idx = body_text[:1540].rfind("\n")
                if cut_idx == -1 or cut_idx < 1000:
                    cut_idx = 1540
                body_text = body_text[:cut_idx].strip() + "\n\n...(see report for full details)"
            data["Body"] = body_text
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
                err_msg = err_json.get("message") or err_json.get("detail") or resp.text
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

                # If a ContentSid template failed on Twilio, attempt sending plain text body on Twilio before giving up
                if content_sid and text and err_code not in (20003, 21211, 21608):
                    logger.info("Twilio ContentSid failed (%s); retrying with plain text body on Twilio...", err_code)
                    try:
                        body_text = str(text or "").strip()
                        if len(body_text) > 1550:
                            body_text = body_text[:1540].strip() + "\n\n...(see report)"
                        plain_data = {
                            "From": from_wa,
                            "To": to_wa,
                            "Body": body_text,
                        }
                        if media_url:
                            plain_data["MediaUrl"] = media_url
                        plain_resp = await client.post(url, data=plain_data, auth=(account_sid, auth_token))
                        if plain_resp.status_code < 400:
                            return plain_resp.json()
                    except Exception as plain_exc:
                        logger.warning("Twilio plain-text retry after ContentSid failure failed: %s", plain_exc)

                # Fallback to Meta Cloud API if configured
                if cfg.get("is_meta") and cfg.get("phone_number_id") and cfg.get("access_token"):
                    logger.info("Twilio error (%s); attempting Meta Cloud API fallback for +%s...", err_code, clean_phone)
                    try:
                        meta_url = f"{GRAPH_BASE_URL}/{cfg['phone_number_id']}/messages"
                        meta_headers = {
                            "Authorization": f"Bearer {cfg['access_token']}",
                            "Content-Type": "application/json",
                        }
                        meta_payload = {
                            "messaging_product": "whatsapp",
                            "recipient_type": "individual",
                            "to": clean_phone,
                            "type": "text",
                            "text": {
                                "preview_url": preview_url,
                                "body": text,
                            },
                        }
                        async with httpx.AsyncClient(timeout=30.0) as meta_client:
                            meta_resp = await meta_client.post(meta_url, json=meta_payload, headers=meta_headers)
                            if meta_resp.status_code < 400:
                                return meta_resp.json()
                            logger.error("Meta fallback also returned error (%s): %s", meta_resp.status_code, meta_resp.text)
                    except Exception as meta_exc:
                        logger.error("Meta fallback failed: %s", meta_exc)

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
            err_msg = resp.text
            try:
                err_data = resp.json()
                error_obj = err_data.get("error", {})
                code = error_obj.get("code")
                err_msg = error_obj.get("message", resp.text)
                if code == 190 or "authentication error" in err_msg.lower() or "expired" in err_msg.lower():
                    err_msg = "Meta WhatsApp Access Token has expired. Please update token in Settings -> WhatsApp."
                elif code == 131030 or "not in allowed list" in err_msg.lower():
                    err_msg = f"Recipient +{clean_phone} is not in Meta developer test list. Add to test numbers in Meta Developers."
                elif code == 131047 or "24 hours" in err_msg.lower():
                    err_msg = f"Cannot send free-form message: Outside Meta 24-hour customer care window. Please select an approved template to message +{clean_phone}."
            except Exception:
                pass
            raise RuntimeError(f"{err_msg}")

        res_data = resp.json()
        meta_id = None
        if "messages" in res_data and len(res_data["messages"]) > 0:
            meta_id = res_data["messages"][0].get("id")

        return {
            "status": "sent",
            "sent_to": clean_phone,
            "meta_message_id": meta_id,
            "raw": res_data
        }


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
        logger.warning("WhatsApp API not configured. Simulated document dispatch to %s", clean_phone)
        return {"status": "simulated", "sent_to": clean_phone}

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


async def send_whatsapp_media(
    to_phone: str,
    media_type: str,  # image, document, audio, video
    media_url: str,
    caption: str = "",
    filename: str = ""
) -> Dict[str, Any]:
    """Send an image, document/PDF, audio, or video to recipient via Meta Cloud API."""
    cfg = await get_whatsapp_config()
    clean_phone = normalize_phone_number(to_phone)
    if not clean_phone:
        raise ValueError("Invalid recipient phone number")

    if not cfg["is_configured"]:
        return {
            "status": "simulated",
            "sent_to": clean_phone,
            "media_url": media_url,
            "media_type": media_type,
            "meta_message_id": None
        }

    url = f"{GRAPH_BASE_URL}/{cfg['phone_number_id']}/messages"
    headers = {
        "Authorization": f"Bearer {cfg['access_token']}",
        "Content-Type": "application/json",
    }

    media_obj: Dict[str, Any] = {"link": media_url}
    if caption and media_type in ["image", "video", "document"]:
        media_obj["caption"] = caption
    if filename and media_type == "document":
        media_obj["filename"] = filename

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": clean_phone,
        "type": media_type,
        media_type: media_obj
    }

    async with httpx.AsyncClient(timeout=45.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code >= 400:
            logger.error("WhatsApp media send error (%s): %s", resp.status_code, resp.text)
            err_msg = resp.text
            try:
                err_data = resp.json()
                err_msg = err_data.get("error", {}).get("message", resp.text)
            except Exception:
                err_msg = resp.text
            raise RuntimeError(f"WhatsApp Media Send Error: {err_msg}")
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


async def send_whatsapp_interactive_buttons(
    to_phone: str,
    body_text: str,
    buttons: List[Dict[str, str]],
    header_text: Optional[str] = None,
    footer_text: Optional[str] = None,
    content_sid: Optional[str] = None,
    content_variables: Optional[Dict[str, Any]] = None,
    client_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Send an interactive button message via WhatsApp (Meta Cloud API or Twilio Content API).
    
    buttons format: [{"id": "btn_send_payment_link", "title": "Yes, Send Link"}]
    """
    cfg = await get_whatsapp_config()
    clean_phone = normalize_phone_number(to_phone)
    if not clean_phone:
        raise ValueError("Invalid recipient phone number")

    if not cfg["is_configured"]:
        raise RuntimeError("WhatsApp API is not configured.")

    if cfg["provider"] == "twilio" or cfg["is_twilio"]:
        if content_sid:
            return await send_whatsapp_text(
                to_phone=to_phone,
                text=body_text,
                content_sid=content_sid,
                content_variables=content_variables,
                client_name=client_name,
            )
        btn_labels = " / ".join([f"*{b.get('title', '')}*" for b in buttons if b.get("title")])
        text_with_buttons = f"{body_text}\n\n👉 Reply: {btn_labels}"
        return await send_whatsapp_text(to_phone=to_phone, text=text_with_buttons, client_name=client_name)

    # Meta Cloud API Interactive Button Message
    url = f"{GRAPH_BASE_URL}/{cfg['phone_number_id']}/messages"
    headers = {
        "Authorization": f"Bearer {cfg['access_token']}",
        "Content-Type": "application/json",
    }
    
    meta_buttons = []
    for i, b in enumerate(buttons[:3]):
        b_id = str(b.get("id") or f"btn_{i}")[:256]
        b_title = str(b.get("title") or "Select")[:20]
        meta_buttons.append({
            "type": "reply",
            "reply": {
                "id": b_id,
                "title": b_title,
            }
        })

    interactive_obj: Dict[str, Any] = {
        "type": "button",
        "body": {"text": body_text[:1024]},
        "action": {"buttons": meta_buttons},
    }
    if header_text:
        interactive_obj["header"] = {"type": "text", "text": header_text[:60]}
    if footer_text:
        interactive_obj["footer"] = {"text": footer_text[:60]}

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": clean_phone,
        "type": "interactive",
        "interactive": interactive_obj,
    }

    async with httpx.AsyncClient(timeout=45.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code >= 400:
            logger.error("WhatsApp interactive button send error (%s): %s", resp.status_code, resp.text)
            try:
                err_data = resp.json()
                err_msg = err_data.get("error", {}).get("message", resp.text)
            except Exception:
                err_msg = resp.text
            raise RuntimeError(f"WhatsApp Interactive Button Error: {err_msg}")
        return resp.json()


async def download_and_store_meta_media(media_id: str, access_token: str) -> Optional[Dict[str, Any]]:
    """Retrieve media from Meta Graph API and store persistently into MongoDB GridFS."""
    from core.database import db
    from motor.motor_asyncio import AsyncIOMotorGridFSBucket
    from bson import ObjectId

    try:
        media_info_url = f"{GRAPH_BASE_URL}/{media_id}"
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            meta_res = await client.get(media_info_url, headers=headers)
            if meta_res.status_code >= 400:
                logger.error("Failed to query Meta media metadata (%s): %s", meta_res.status_code, meta_res.text)
                return None

            meta_data = meta_res.json()
            download_url = meta_data.get("url")
            mime_type = meta_data.get("mime_type", "application/octet-stream")
            file_size = meta_data.get("file_size", 0)

            if not download_url:
                return None

            # Stream download the binary bytes
            bin_res = await client.get(download_url, headers=headers)
            if bin_res.status_code >= 400:
                logger.error("Failed to download binary media from Meta CDN (%s)", bin_res.status_code)
                return None

            raw_bytes = bin_res.content

            # Save in GridFS
            gridfs = AsyncIOMotorGridFSBucket(db, bucket_name="whatsapp_media")
            filename = f"wa_{media_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Map extension from mime
            ext = ".bin"
            if "jpeg" in mime_type or "jpg" in mime_type:
                ext = ".jpg"
            elif "png" in mime_type:
                ext = ".png"
            elif "pdf" in mime_type:
                ext = ".pdf"
            elif "ogg" in mime_type or "opus" in mime_type:
                ext = ".ogg"
            elif "mp4" in mime_type:
                ext = ".mp4"
            
            clean_filename = f"{filename}{ext}"

            file_id = await gridfs.upload_from_stream(
                clean_filename,
                raw_bytes,
                metadata={"media_id": media_id, "mime_type": mime_type, "size": len(raw_bytes)}
            )

            return {
                "file_id": str(file_id),
                "filename": clean_filename,
                "mime_type": mime_type,
                "size": len(raw_bytes),
                "local_url": f"/api/crm/whatsapp/media/{str(file_id)}"
            }
    except Exception as e:
        logger.error(f"Error downloading/storing Meta media: {e}", exc_info=True)
        return None
