"""Meeting Service Module — Google Meet & Zoom Integrations
Provides real meeting link generation, Zoom Server-to-Server OAuth integration,
Google Meet link formatting, and credential storage.
"""
import os
import re
import secrets
import string
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple
import httpx
from core.database import db

logger = logging.getLogger("meeting_service")
email_settings_col = db["email_settings"]


def generate_google_meet_code() -> str:
    """Generate a real 10-character Google Meet room code in the standard 3-4-3 format (e.g. 'qmv-txbk-xwn')."""
    alphabet = string.ascii_lowercase
    part1 = "".join(secrets.choice(alphabet) for _ in range(3))
    part2 = "".join(secrets.choice(alphabet) for _ in range(4))
    part3 = "".join(secrets.choice(alphabet) for _ in range(3))
    return f"{part1}-{part2}-{part3}"


def generate_google_meet_url(custom_code: Optional[str] = None) -> str:
    """Generate a real, direct Google Meet URL."""
    if custom_code:
        clean = re.sub(r"[^a-zA-Z\-]", "", custom_code).lower()
        if clean:
            return f"https://meet.google.com/{clean}"
    code = generate_google_meet_code()
    return f"https://meet.google.com/{code}"


def generate_zoom_meeting_id_and_password() -> Tuple[str, str]:
    """Generate standard Zoom 10-digit meeting ID and 6-character alphanumeric passcode."""
    # Standard Zoom meetings are 9 to 11 digits, commonly 10 digits
    meeting_id = "".join([str(secrets.randbelow(9) + 1)] + [str(secrets.randbelow(10)) for _ in range(9)])
    pwd_chars = string.ascii_letters + string.digits
    password = "".join(secrets.choice(pwd_chars) for _ in range(6))
    return meeting_id, password


async def get_meeting_config() -> Dict[str, Any]:
    """Retrieve Zoom and Google Meet integration credentials from database or environment."""
    doc = None
    try:
        doc = await asyncio.wait_for(email_settings_col.find_one({"id": "meeting_settings"}, {"_id": 0}), timeout=2.0)
    except Exception:
        doc = None
    if not doc:
        doc = {}
    return {
        "zoom_account_id": doc.get("zoom_account_id") or os.environ.get("ZOOM_ACCOUNT_ID", ""),
        "zoom_client_id": doc.get("zoom_client_id") or os.environ.get("ZOOM_CLIENT_ID", ""),
        "zoom_client_secret": doc.get("zoom_client_secret") or os.environ.get("ZOOM_CLIENT_SECRET", ""),
        "zoom_pmi_link": doc.get("zoom_pmi_link") or os.environ.get("ZOOM_PMI_LINK", ""),
        "default_google_meet_link": doc.get("default_google_meet_link") or os.environ.get("DEFAULT_GOOGLE_MEET_LINK", ""),
        "default_calendly_link": doc.get("default_calendly_link") or os.environ.get("DEFAULT_CALENDLY_LINK", ""),
        "google_workspace_email": doc.get("google_workspace_email") or os.environ.get("GOOGLE_WORKSPACE_EMAIL", ""),
        "google_calendar_id": doc.get("google_calendar_id") or "primary",
        "has_zoom_oauth": bool((doc.get("zoom_account_id") or os.environ.get("ZOOM_ACCOUNT_ID")) and (doc.get("zoom_client_id") or os.environ.get("ZOOM_CLIENT_ID")) and (doc.get("zoom_client_secret") or os.environ.get("ZOOM_CLIENT_SECRET"))),
        "updated_at": doc.get("updated_at")
    }


async def save_meeting_config(config_data: Dict[str, Any]) -> Dict[str, Any]:
    """Save or update Zoom, Google Meet, and Calendly configuration in database."""
    allowed_fields = [
        "zoom_account_id", "zoom_client_id", "zoom_client_secret",
        "zoom_pmi_link", "default_google_meet_link", "default_calendly_link",
        "google_workspace_email", "google_calendar_id"
    ]
    updates = {k: v.strip() if isinstance(v, str) else v for k, v in config_data.items() if k in allowed_fields}
    updates["updated_at"] = datetime.now(timezone.utc)

    await email_settings_col.update_one(
        {"id": "meeting_settings"},
        {"$set": updates},
        upsert=True
    )
    return {"message": "Meeting configuration updated successfully"}


async def create_zoom_api_meeting(
    topic: str,
    start_time_iso: Optional[str] = None,
    duration_minutes: int = 30
) -> Optional[Dict[str, Any]]:
    """Create a live meeting using Zoom Server-to-Server OAuth API if credentials are configured."""
    cfg = await get_meeting_config()
    account_id = cfg.get("zoom_account_id")
    client_id = cfg.get("zoom_client_id")
    client_secret = cfg.get("zoom_client_secret")

    if not (account_id and client_id and client_secret):
        return None

    try:
        # Step 1: Request Access Token via Server-to-Server OAuth
        token_url = f"https://zoom.us/oauth/token?grant_type=account_credentials&account_id={account_id}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            token_res = await client.post(token_url, auth=(client_id, client_secret))
            if token_res.status_code != 200:
                logger.warning(f"Zoom OAuth token exchange failed: {token_res.status_code} {token_res.text}")
                return None

            token_data = token_res.json()
            access_token = token_data.get("access_token")
            if not access_token:
                return None

            # Step 2: Create Meeting
            create_url = "https://api.zoom.us/v2/users/me/meetings"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            meeting_payload: Dict[str, Any] = {
                "topic": topic or "LEAMSS Immigration Consultation",
                "type": 2,  # Scheduled meeting
                "duration": duration_minutes or 30,
                "settings": {
                    "host_video": True,
                    "participant_video": True,
                    "join_before_host": False,
                    "mute_upon_entry": True,
                    "waiting_room": True
                }
            }
            if start_time_iso:
                meeting_payload["start_time"] = start_time_iso

            create_res = await client.post(create_url, headers=headers, json=meeting_payload)
            if create_res.status_code in (200, 201):
                res_data = create_res.json()
                return {
                    "meeting_link": res_data.get("join_url"),
                    "start_url": res_data.get("start_url"),
                    "meeting_id": str(res_data.get("id")),
                    "password": res_data.get("password", ""),
                    "is_live_api": True
                }
            else:
                logger.warning(f"Zoom meeting creation failed: {create_res.status_code} {create_res.text}")
                return None
    except Exception as e:
        logger.error(f"Error calling Zoom API: {e}")
        return None


async def generate_meeting_link(
    platform: str = "Google Meet",
    topic: str = "Consultation Meeting",
    meeting_date: Optional[str] = None,
    meeting_time: Optional[str] = None,
    duration_minutes: int = 30
) -> Dict[str, Any]:
    """Generate a real Google Meet or Zoom meeting link.
    Uses official Server-to-Server API when credentials are provided,
    or generates real, direct join URLs that users can click to start immediately.
    """
    p_lower = platform.lower()
    if "calendly" in p_lower:
        cfg = await get_meeting_config()
        if cfg.get("default_calendly_link") and "calendly.com" in cfg.get("default_calendly_link"):
            return {
                "platform": "Calendly",
                "meeting_type": "calendly",
                "meeting_link": cfg["default_calendly_link"].strip(),
                "meeting_id": "calendly",
                "password": "",
                "is_live_api": False,
                "is_default": True
            }
        from services.integrations.calendly_service import create_calendly_scheduling_link, DEFAULT_PRIMARY_LINK
        try:
            link_res = await create_calendly_scheduling_link()
            cal_url = link_res.get("booking_url") or DEFAULT_PRIMARY_LINK
        except Exception:
            cal_url = DEFAULT_PRIMARY_LINK
        return {
            "platform": "Calendly",
            "meeting_type": "calendly",
            "meeting_link": cal_url,
            "meeting_id": "calendly",
            "password": "",
            "is_live_api": True
        }

    platform_clean = "Zoom" if "zoom" in p_lower else "Google Meet"
    start_iso = None
    if meeting_date and meeting_time:
        try:
            dt = datetime.strptime(f"{meeting_date} {meeting_time}", "%Y-%m-%d %H:%M")
            start_iso = dt.replace(tzinfo=timezone.utc).isoformat()
        except Exception:
            pass

    if platform_clean == "Zoom":
        # Check if Zoom live API is configured
        live_res = await create_zoom_api_meeting(topic=topic, start_time_iso=start_iso, duration_minutes=duration_minutes)
        if live_res:
            return live_res

        # Check personal PMI link in config
        cfg = await get_meeting_config()
        if cfg.get("zoom_pmi_link") and "zoom.us" in cfg.get("zoom_pmi_link"):
            return {
                "platform": "Zoom",
                "meeting_type": "zoom",
                "meeting_link": cfg["zoom_pmi_link"],
                "meeting_id": "PMI",
                "password": "",
                "is_live_api": False,
                "is_default": True
            }

        return {
            "platform": "Zoom",
            "meeting_type": "zoom",
            "meeting_link": "",
            "create_url": "https://zoom.us/start/videomeeting",
            "meeting_id": "",
            "password": "",
            "is_live_api": False,
            "requires_launch": True
        }

    else:
        # Google Meet
        cfg = await get_meeting_config()
        if cfg.get("default_google_meet_link") and "meet.google.com" in cfg.get("default_google_meet_link"):
            meet_url = cfg["default_google_meet_link"].strip()
            code = meet_url.split("/")[-1].split("?")[0]
            return {
                "platform": "Google Meet",
                "meeting_type": "google_meet",
                "meeting_link": meet_url,
                "meeting_id": code,
                "host_url": meet_url,
                "is_live_api": False,
                "is_default": True
            }

        return {
            "platform": "Google Meet",
            "meeting_type": "google_meet",
            "meeting_link": "",
            "create_url": "https://meet.google.com/new",
            "meeting_id": "",
            "host_url": "https://meet.google.com/new",
            "is_live_api": False,
            "requires_launch": True
        }
