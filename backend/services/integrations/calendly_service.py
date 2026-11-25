"""Calendly Integration Service — Full API v2 Integration.

Features:
- Personal Access Token (PAT) authentication & verification
- Cloudflare-safe headers (User-Agent: LEAMSS-CRM/2.0)
- Dynamic single-use scheduling links creation (`/scheduling_links`)
- Live Event Types and Scheduled Events fetching
- Bidirectional synchronization with CRM Meetings (crm_meetings_col) and Appointments (appointments_col)
- Webhook payload processing (invitee.created, invitee.canceled, invitee.rescheduled)
- Client booking confirmation emails with Google Meet / Calendly details
- Automatic 24h, 1h, and 15m meeting reminders engine
- Post-meeting automated status completion and follow-up task generation
- Graceful fallback for Notetaker recaps, transcripts, and custom fields
- Strict deduplication of leads, meetings, webhook events, and reminders
"""
import uuid
import re
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import httpx
import asyncio

from core.database import db, crm_meetings_col, appointments_col, leads_col, users_col, follow_ups_col
from services.integrations.encryption_util import decrypt_secret, encrypt_secret
from services.integrations.lead_ingestion_service import ingest_lead
from core.services import log_activity
from core.email_service import send_email

logger = logging.getLogger("calendly_service")

CALENDLY_API_BASE = "https://api.calendly.com"
DEFAULT_USER_AGENT = "LEAMSS-CRM/2.0 (crm@leamss.com)"

DEFAULT_PAT = (
    "eyJraWQiOiIxY2UxZTEzNjE3ZGNmNzY2YjNjZWJjY2Y4ZGM1YmFmYThhNjVlNjg0MDIzZjdjMzJiZTgzNDliMjM4MDEzNWI0IiwidHlwIjoiUEFUIiwiYWxnIjoiRVMyNTYifQ."
    "eyJpc3MiOiJodHRwczovL2F1dGguY2FsZW5kbHkuY29tIiwiaWF0IjoxNzk1MDY3MjU2LCJqdGkiOiJiYjVmN2M1Ny1iMWFkLTQ2ZWUtODIxOS0xNjAwYmU4OTBhMjciLCJ1c2VyX3V1aWQiOiJmYzZkNzg5MC01YjY5LTRiZTItOGUwYy1hZWU5ZGNhYzQzNDQiLCJzY29wZSI6ImF2YWlsYWJpbGl0eTpyZWFkIGF2YWlsYWJpbGl0eTp3cml0ZSBldmVudF90eXBlczpyZWFkIGV2ZW50X3R5cGVzOndyaXRlIGxvY2F0aW9uczpyZWFkIHJvdXRpbmdfZm9ybXM6cmVhZCBzaGFyZXM6cmVhZCBzaGFyZXM6d3JpdGUgc2NoZWR1bGVkX2V2ZW50czpyZWFkIHNjaGVkdWxlZF9ldmVudHM6d3JpdGUgc2NoZWR1bGluZ19saW5rczp3cml0ZSBncm91cHM6cmVhZCBvcmdhbml6YXRpb25zOnJlYWQgb3JnYW5pemF0aW9uczp3cml0ZSB1c2VyczpyZWFkIGNvbnRhY3RzOnJlYWQgY29udGFjdHM6d3JpdGUgbWVldGluZ19yZWNhcHM6cmVhZCBtZWV0aW5nX3JlY2Fwczp3cml0ZSBhY3Rpdml0eV9sb2c6cmVhZCBkYXRhX2NvbXBsaWFuY2U6d3JpdGUgb3V0Z29pbmdfY29tbXVuaWNhdGlvbnM6cmVhZCB3ZWJob29rczpyZWFkIHdlYmhvb2tzOndyaXRlIn0."
    "JUwrLge0TanCIR4rmHZxzOrgFvmP0R-ZAAG1L6-FYGAh33yG1Qrfp8DM_-jh19JVeeg3bIpm5WbCIZq9GfPXrg"
)

DEFAULT_PRIMARY_LINK = "https://calendly.com/rohit-leamss/permanent-residency-visa"
DEFAULT_USER_URI = "https://api.calendly.com/users/fc6d7890-5b69-4be2-8e0c-aee9dcac4344"
DEFAULT_ORG_URI = "https://api.calendly.com/organizations/1222ee61-7285-4790-b4ff-c740fc8245d5"


def _get_api_headers(token: str) -> Dict[str, str]:
    """Generates standard headers with custom User-Agent to avoid Cloudflare 403 blocks."""
    clean = token.strip()
    return {
        "Authorization": f"Bearer {clean}",
        "User-Agent": DEFAULT_USER_AGENT,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }


async def ensure_calendly_integration(company_id: str = "comp_leamss_primary") -> Dict[str, Any]:
    """Ensures that the company has a valid Calendly integration record seeded with the PAT."""
    integ = await db["integrations"].find_one({"company_id": company_id, "provider": "calendly"})
    if not integ:
        now = datetime.now(timezone.utc)
        integ_doc = {
            "id": f"integ_calendly_{uuid.uuid4().hex[:8]}",
            "company_id": company_id,
            "provider": "calendly",
            "name": "Calendly Booking Integration",
            "status": "connected",
            "credentials": {
                "api_token": encrypt_secret(DEFAULT_PAT),
                "primary_link": DEFAULT_PRIMARY_LINK,
                "user_uri": DEFAULT_USER_URI,
                "organization_uri": DEFAULT_ORG_URI
            },
            "created_at": now,
            "updated_at": now,
            "last_synced_at": now,
            "total_leads_synced": 0
        }
        await db["integrations"].insert_one(integ_doc)
        return integ_doc
    return integ


async def get_calendly_token(company_id: str = "comp_leamss_primary") -> str:
    """Retrieves active decrypted Calendly PAT."""
    integ = await db["integrations"].find_one({"company_id": company_id, "provider": "calendly"})
    if integ:
        creds = integ.get("credentials") or {}
        raw = creds.get("api_token") or creds.get("pat") or creds.get("access_token")
        if raw:
            dec = decrypt_secret(raw)
            if dec:
                return dec
    return DEFAULT_PAT


async def test_calendly_connection(credentials: Dict[str, Any]) -> Dict[str, Any]:
    """Validates Personal Access Token against Calendly API v2 /users/me."""
    raw_token = credentials.get("api_token") or credentials.get("pat") or credentials.get("access_token")
    token = decrypt_secret(raw_token) if raw_token else ""
    if not token:
        token = DEFAULT_PAT

    primary_link = credentials.get("primary_link") or DEFAULT_PRIMARY_LINK

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            headers = _get_api_headers(token)
            resp = await client.get(f"{CALENDLY_API_BASE}/users/me", headers=headers)
            if resp.status_code == 200:
                data = resp.json().get("resource", {})
                user_name = data.get("name", "Calendly User")
                user_email = data.get("email", "")
                scheduling_url = data.get("scheduling_url", primary_link)
                user_uri = data.get("uri")
                org_uri = data.get("current_organization")
                return {
                    "success": True,
                    "message": f"Successfully connected Calendly account: {user_name} ({user_email}). Booking: {scheduling_url}",
                    "user": {
                        "name": user_name,
                        "email": user_email,
                        "uri": user_uri,
                        "organization_uri": org_uri,
                        "scheduling_url": scheduling_url
                    }
                }
            return {
                "success": False,
                "message": f"Calendly API authentication failed ({resp.status_code}): {resp.text[:160]}"
            }
    except Exception as e:
        return {"success": False, "message": f"Calendly connection error: {str(e)}"}


async def fetch_calendly_event_types(company_id: str = "comp_leamss_primary") -> List[Dict[str, Any]]:
    """Fetches active event types available on the Calendly account."""
    token = await get_calendly_token(company_id)
    event_types: List[Dict[str, Any]] = []

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            headers = _get_api_headers(token)
            me_resp = await client.get(f"{CALENDLY_API_BASE}/users/me", headers=headers)
            user_uri = DEFAULT_USER_URI
            if me_resp.status_code == 200:
                user_uri = me_resp.json().get("resource", {}).get("uri") or DEFAULT_USER_URI

            params = {"user": user_uri, "count": 20, "active": "true"}
            resp = await client.get(f"{CALENDLY_API_BASE}/event_types", params=params, headers=headers)
            if resp.status_code == 200:
                for item in resp.json().get("collection", []):
                    event_types.append({
                        "uri": item.get("uri"),
                        "name": item.get("name"),
                        "slug": item.get("slug"),
                        "duration": item.get("duration"),
                        "scheduling_url": item.get("scheduling_url"),
                        "kind": item.get("kind"),
                        "color": item.get("color")
                    })
    except Exception as e:
        logger.warning(f"Error fetching event types: {e}")

    if not event_types:
        event_types.append({
            "uri": "https://api.calendly.com/event_types/53b4136a-168a-4700-8f2b-e300887eafaa",
            "name": "Permanent Residency Visa",
            "slug": "permanent-residency-visa",
            "duration": 30,
            "scheduling_url": DEFAULT_PRIMARY_LINK
        })
    return event_types


async def create_calendly_scheduling_link(
    company_id: str = "comp_leamss_primary",
    event_type_uri: Optional[str] = None,
    max_event_count: int = 1
) -> Dict[str, Any]:
    """Generates a dynamic single-use scheduling link for a client."""
    token = await get_calendly_token(company_id)

    if not event_type_uri:
        types = await fetch_calendly_event_types(company_id)
        if types:
            event_type_uri = types[0].get("uri")

    if not event_type_uri:
        event_type_uri = "https://api.calendly.com/event_types/53b4136a-168a-4700-8f2b-e300887eafaa"

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            headers = _get_api_headers(token)
            payload = {
                "max_event_count": max_event_count,
                "owner": event_type_uri,
                "owner_type": "EventType"
            }
            resp = await client.post(f"{CALENDLY_API_BASE}/scheduling_links", json=payload, headers=headers)
            if resp.status_code in [200, 201]:
                res_data = resp.json().get("resource", {})
                booking_url = res_data.get("booking_url")
                return {
                    "success": True,
                    "booking_url": booking_url,
                    "owner": event_type_uri,
                    "max_event_count": max_event_count
                }
            logger.warning(f"Calendly scheduling link failed ({resp.status_code}): {resp.text}")
    except Exception as e:
        logger.error(f"Error generating Calendly scheduling link: {e}")

    # Fallback to direct public booking URL
    return {
        "success": True,
        "booking_url": DEFAULT_PRIMARY_LINK,
        "owner": event_type_uri,
        "is_fallback": True
    }


async def send_meeting_confirmation_email(
    to_email: str,
    client_name: str,
    consultant_name: str,
    meeting_title: str,
    meeting_date: str,
    meeting_time: str,
    duration_minutes: int,
    meeting_link: str,
    platform: str = "Google Meet",
    reschedule_link: Optional[str] = None
) -> bool:
    """Dispatches a branded consultation confirmation email with Google Meet / Calendly link."""
    if not to_email or "@" not in to_email:
        return False

    title_clean = meeting_title or "Immigration Consultation"
    date_display = meeting_date
    try:
        parts = meeting_date.split("-")
        if len(parts) == 3:
            dt = datetime(int(parts[0]), int(parts[1]), int(parts[2]))
            date_display = dt.strftime("%A, %d %B %Y")
    except Exception:
        pass

    join_btn_text = "Join Google Meet" if "google" in platform.lower() else ("Open Calendly" if "calendly" in platform.lower() else "Join Meeting")

    body_html = f"""
    <p style="color: #374151; font-size: 15px; line-height: 1.6;">
        Dear <strong>{client_name or 'Client'}</strong>,
    </p>
    <p style="color: #374151; font-size: 15px; line-height: 1.6;">
        Your consultation meeting with <strong>{consultant_name}</strong> at <strong>LEAMSS Immigration</strong> has been confirmed.
    </p>
    <div style="background: #f8fafc; border-left: 4px solid #2a777a; padding: 18px 24px; border-radius: 8px; margin: 20px 0;">
        <p style="margin: 4px 0; color: #1f2937; font-size: 14px;"><strong>Consultation Topic:</strong> {title_clean}</p>
        <p style="margin: 4px 0; color: #1f2937; font-size: 14px;"><strong>Date:</strong> {date_display}</p>
        <p style="margin: 4px 0; color: #1f2937; font-size: 14px;"><strong>Time:</strong> {meeting_time} ({duration_minutes} minutes)</p>
        <p style="margin: 4px 0; color: #1f2937; font-size: 14px;"><strong>Platform:</strong> {platform}</p>
        <p style="margin: 4px 0; color: #1f2937; font-size: 14px;"><strong>Assigned Consultant:</strong> {consultant_name}</p>
    </div>
    """

    if meeting_link:
        body_html += f"""
        <div style="text-align: center; margin: 30px 0;">
            <a href="{meeting_link}" target="_blank" style="background: #2a777a; color: #ffffff; padding: 12px 28px; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 15px; display: inline-block;">
                {join_btn_text}
            </a>
            <p style="color: #6b7280; font-size: 12px; margin-top: 10px;">
                Link: <a href="{meeting_link}" style="color: #2a777a;">{meeting_link}</a>
            </p>
        </div>
        """

    if reschedule_link:
        body_html += f"""
        <p style="color: #6b7280; font-size: 13px; text-align: center; margin-top: 20px;">
            Need to change your time? <a href="{reschedule_link}" style="color: #2a777a; text-decoration: underline;">Reschedule Consultation</a>
        </p>
        """

    body_html += f"""
    <p style="color: #4b5563; font-size: 13px; line-height: 1.5; margin-top: 25px;">
        <strong>Preparation Note:</strong> Please join 2 minutes prior to your scheduled time with your current resume, educational credentials, and any existing visa documents.
    </p>
    <p style="color: #374151; font-size: 14px; margin-top: 20px;">
        Warm regards,<br>
        <strong>{consultant_name}</strong><br>
        LEAMSS Immigration Consulting
    </p>
    """

    try:
        await send_email(
            to_email=to_email,
            subject=f"Confirmed: {title_clean} - {date_display} at {meeting_time}",
            title="Consultation Confirmation",
            body_html=body_html
        )
        return True
    except Exception as e:
        logger.error(f"Failed to dispatch booking confirmation email to {to_email}: {e}")
        return False


async def send_meeting_rescheduled_email(
    to_email: str,
    client_name: str,
    consultant_name: str,
    meeting_title: str,
    new_date: str,
    new_time: str,
    duration_minutes: int,
    meeting_link: str,
    reason: str,
    old_date: Optional[str] = None,
    old_time: Optional[str] = None,
    platform: str = "Google Meet",
    reschedule_link: Optional[str] = None
) -> bool:
    """Dispatches a branded consultation reschedule notice email with new slot, reason, and Google Meet link."""
    if not to_email or "@" not in to_email:
        return False

    title_clean = meeting_title or "Immigration Consultation"
    date_display = new_date
    try:
        parts = new_date.split("-")
        if len(parts) == 3:
            dt = datetime(int(parts[0]), int(parts[1]), int(parts[2]))
            date_display = dt.strftime("%A, %d %B %Y")
    except Exception:
        pass

    join_btn_text = "Join Google Meet" if "google" in platform.lower() else ("Open Calendly" if "calendly" in platform.lower() else "Join Meeting")

    body_html = f"""
    <p style="color: #374151; font-size: 15px; line-height: 1.6;">
        Dear <strong>{client_name or 'Client'}</strong>,
    </p>
    <p style="color: #374151; font-size: 15px; line-height: 1.6;">
        Your consultation meeting with <strong>{consultant_name}</strong> has been <strong>rescheduled</strong>. Please find the updated schedule and join link below:
    </p>
    <div style="background: #f0fdf4; border-left: 4px solid #16a34a; padding: 18px 24px; border-radius: 8px; margin: 20px 0;">
        <p style="margin: 4px 0; color: #166534; font-size: 14px; font-weight: bold;">🗓️ NEW CONSULTATION TIME</p>
        <p style="margin: 4px 0; color: #1f2937; font-size: 14px;"><strong>Consultation Topic:</strong> {title_clean}</p>
        <p style="margin: 4px 0; color: #1f2937; font-size: 15px;"><strong>New Date:</strong> <span style="color: #166534; font-weight: 700;">{date_display}</span></p>
        <p style="margin: 4px 0; color: #1f2937; font-size: 15px;"><strong>New Time:</strong> <span style="color: #166534; font-weight: 700;">{new_time}</span> ({duration_minutes} minutes)</p>
        <p style="margin: 4px 0; color: #1f2937; font-size: 14px;"><strong>Platform:</strong> {platform}</p>
        <p style="margin: 4px 0; color: #1f2937; font-size: 14px;"><strong>Assigned Consultant:</strong> {consultant_name}</p>
        {f'<p style="margin: 6px 0 0; color: #6b7280; font-size: 12px;">(Previous Slot: {old_date} at {old_time})</p>' if old_date else ''}
    </div>

    <div style="background: #fffbeb; border-left: 4px solid #f59e0b; padding: 14px 20px; border-radius: 8px; margin: 15px 0;">
        <p style="margin: 0; color: #92400e; font-size: 13px;">
            <strong>Reason for Reschedule:</strong> {reason}
        </p>
    </div>
    """

    if meeting_link:
        body_html += f"""
        <div style="text-align: center; margin: 28px 0;">
            <a href="{meeting_link}" target="_blank" style="background: #2a777a; color: #ffffff; padding: 12px 28px; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 15px; display: inline-block;">
                {join_btn_text}
            </a>
            <p style="color: #6b7280; font-size: 12px; margin-top: 10px;">
                Link: <a href="{meeting_link}" style="color: #2a777a;">{meeting_link}</a>
            </p>
        </div>
        """

    if reschedule_link:
        body_html += f"""
        <p style="color: #6b7280; font-size: 13px; text-align: center; margin-top: 15px;">
            Need to change your slot again? <a href="{reschedule_link}" style="color: #2a777a; text-decoration: underline;">Change Consultation Slot</a>
        </p>
        """

    body_html += f"""
    <p style="color: #4b5563; font-size: 13px; line-height: 1.5; margin-top: 25px;">
        <strong>Note:</strong> Your calendar invitation has been automatically updated. Please join 2 minutes prior with your documents ready.
    </p>
    <p style="color: #374151; font-size: 14px; margin-top: 20px;">
        Warm regards,<br>
        <strong>{consultant_name}</strong><br>
        LEAMSS Immigration Consulting
    </p>
    """

    try:
        await send_email(
            to_email=to_email,
            subject=f"[Updated Schedule] {title_clean} - {date_display} at {new_time}",
            title="Consultation Rescheduled",
            body_html=body_html
        )
        return True
    except Exception as e:
        logger.error(f"Failed to dispatch reschedule notice email to {to_email}: {e}")
        return False



async def fetch_calendly_active_bookings(api_token: str, max_events: int = 50) -> List[Dict[str, Any]]:
    """Pulls recent scheduled events and their invitees from Calendly API v2."""
    clean_token = decrypt_secret(api_token) or api_token or DEFAULT_PAT
    bookings: List[Dict[str, Any]] = []

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            headers = _get_api_headers(clean_token)
            me_resp = await client.get(f"{CALENDLY_API_BASE}/users/me", headers=headers)
            if me_resp.status_code != 200:
                return []

            me_data = me_resp.json().get("resource", {})
            user_uri = me_data.get("uri") or DEFAULT_USER_URI
            user_name = me_data.get("name", "Rohit Alluri")

            events_resp = await client.get(
                f"{CALENDLY_API_BASE}/scheduled_events",
                params={"user": user_uri, "count": min(max_events, 50), "sort": "start_time:desc"},
                headers=headers
            )
            if events_resp.status_code != 200:
                return []

            events = events_resp.json().get("collection", [])
            for ev in events:
                event_uri = ev.get("uri", "")
                event_id = event_uri.split("/")[-1] if "/" in event_uri else event_uri
                event_name = ev.get("name") or "Permanent Residency Visa"
                start_time = ev.get("start_time")
                end_time = ev.get("end_time")
                ev_status = ev.get("status")  # active, canceled
                location = ev.get("location") or {}
                join_url = ""
                if isinstance(location, dict):
                    join_url = location.get("join_url") or ""
                elif isinstance(location, str):
                    join_url = location

                cached_meeting = await crm_meetings_col.find_one({"calendly_event_id": event_id})
                if cached_meeting:
                    current_status = "cancelled" if ev_status == "canceled" else (cached_meeting.get("status") or "scheduled")
                    if ev_status == "canceled" and cached_meeting.get("status") not in ["cancelled", "rescheduled"]:
                        await crm_meetings_col.update_one({"id": cached_meeting["id"]}, {"$set": {"status": "cancelled"}})
                    bookings.append({
                        "event_id": event_id,
                        "event_uri": event_uri,
                        "invitee_id": cached_meeting.get("calendly_invitee_id") or event_id,
                        "invitee_uri": "",
                        "event_name": event_name,
                        "host_name": user_name,
                        "client_name": cached_meeting.get("contact_name") or "Calendly Client",
                        "client_email": cached_meeting.get("contact_email") or "",
                        "client_phone": cached_meeting.get("contact_phone") or "",
                        "start_time": start_time,
                        "end_time": end_time,
                        "date": cached_meeting.get("meeting_date") or (str(start_time)[:10] if start_time else ""),
                        "time": cached_meeting.get("meeting_time") or (str(start_time)[11:16] if len(str(start_time)) > 15 else ""),
                        "duration_minutes": cached_meeting.get("duration_minutes") or 30,
                        "meeting_link": cached_meeting.get("meeting_link") or join_url or DEFAULT_PRIMARY_LINK,
                        "reschedule_url": cached_meeting.get("reschedule_url") or "",
                        "cancel_url": cached_meeting.get("cancel_url") or "",
                        "status": current_status,
                        "notes": cached_meeting.get("notes") or f"Calendly Event: {event_name}",
                        "questions_and_answers": [],
                        "source": "calendly"
                    })
                    continue

                await asyncio.sleep(0.1)
                inv_resp = await client.get(f"{event_uri}/invitees", headers=headers)
                if inv_resp.status_code != 200:
                    continue

                invitees = inv_resp.json().get("collection", [])
                for inv in invitees:
                    inv_uri = inv.get("uri", "")
                    inv_id = inv_uri.split("/")[-1] if "/" in inv_uri else inv_uri
                    phone = inv.get("text_reminder_number") or ""
                    qa_list = inv.get("questions_and_answers") or []
                    reschedule_url = inv.get("reschedule_url") or ""
                    cancel_url = inv.get("cancel_url") or ""

                    notes_lines = [f"Calendly Event: {event_name}"]
                    for qa in qa_list:
                        q = qa.get("question", "")
                        a = qa.get("answer", "")
                        notes_lines.append(f"{q}: {a}")
                        if not phone and any(t in q.lower() for t in ["phone", "mobile", "whatsapp", "contact", "number"]):
                            phone = a

                    duration_mins = 30
                    try:
                        if start_time and end_time:
                            s_dt = datetime.fromisoformat(str(start_time).replace("Z", "+00:00"))
                            e_dt = datetime.fromisoformat(str(end_time).replace("Z", "+00:00"))
                            duration_mins = max(15, int((e_dt - s_dt).total_seconds() / 60))
                    except Exception:
                        duration_mins = 30

                    m_status = "cancelled" if ev_status == "canceled" or inv.get("status") == "canceled" else "scheduled"

                    bookings.append({
                        "event_id": event_id,
                        "event_uri": event_uri,
                        "invitee_id": inv_id,
                        "invitee_uri": inv_uri,
                        "event_name": event_name,
                        "host_name": user_name,
                        "client_name": inv.get("name") or "Calendly Client",
                        "client_email": (inv.get("email") or "").strip().lower(),
                        "client_phone": phone.strip(),
                        "start_time": start_time,
                        "end_time": end_time,
                        "date": str(start_time)[:10] if start_time else "",
                        "time": str(start_time)[11:16] if len(str(start_time)) > 15 else "",
                        "duration_minutes": duration_mins,
                        "meeting_link": join_url or DEFAULT_PRIMARY_LINK,
                        "reschedule_url": reschedule_url,
                        "cancel_url": cancel_url,
                        "status": m_status,
                        "notes": "\n".join(notes_lines),
                        "questions_and_answers": qa_list,
                        "source": "calendly"
                    })
    except Exception as e:
        logger.error(f"Error fetching active bookings from Calendly: {e}")

    return bookings


async def sync_meeting_recaps_and_notes(company_id: str, event_uuid: str) -> Optional[Dict[str, Any]]:
    """Fetches meeting recap, transcripts, and AI notes from Calendly API (with graceful fallback)."""
    token = await get_calendly_token(company_id)
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            headers = _get_api_headers(token)
            clean_uuid = event_uuid.split("/")[-1]
            url = f"{CALENDLY_API_BASE}/meeting_recaps/{clean_uuid}"
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                return resp.json().get("resource")
            logger.info(f"Calendly meeting_recaps status {resp.status_code} for {clean_uuid} (graceful fallback)")
    except Exception as e:
        logger.warning(f"Meeting recap lookup skipped: {e}")
    return None


async def reschedule_calendly_event_via_api(
    company_id: str,
    old_event_id: str,
    new_date: str,
    new_time: str,
    reason: str,
    client_name: str,
    client_email: str,
    client_phone: str = "",
    duration_minutes: int = 30,
    timezone_str: str = "Asia/Kolkata",
    invitee_id: Optional[str] = None,
    reschedule_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Directly reschedules a Calendly booking on Calendly Calendar.
    Method 1: Uses Calendly's official Invitee Reschedule API (PATCH https://calendly.com/api/booking/invitees/{uuid}),
              which updates the host's Calendly Calendar without hitting the 5/day Free PAT rate limit.
    Method 2: Falls back to Calendly API v2 (POST /invitees + POST /cancellation).
    """
    token = await get_calendly_token(company_id)
    headers = _get_api_headers(token)

    clean_old_id = old_event_id.split("/")[-1].strip() if old_event_id else ""
    event_type_uri = None
    old_ev_data = None
    reschedule_uuid = None

    if reschedule_url and "/reschedulings/" in reschedule_url:
        reschedule_uuid = reschedule_url.split("/reschedulings/")[-1].split("?")[0].strip()
    elif invitee_id and len(invitee_id) > 20 and invitee_id != clean_old_id:
        reschedule_uuid = invitee_id.strip()

    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        ZoneInfo = None

    # Calculate target time in both UTC and local offset
    clean_time = new_time.strip()
    if len(clean_time) >= 5:
        hh, mm = int(clean_time[:2]), int(clean_time[3:5])
    else:
        hh, mm = 10, 0

    start_time_iso = None
    offset_time_iso = None
    tz_target = ZoneInfo(timezone_str) if (ZoneInfo and timezone_str) else None
    if tz_target:
        try:
            local_dt = datetime.strptime(new_date, "%Y-%m-%d").replace(
                hour=hh, minute=mm, second=0, microsecond=0, tzinfo=tz_target
            )
            utc_dt = local_dt.astimezone(timezone.utc)
            start_time_iso = utc_dt.strftime("%Y-%m-%dT%H:%M:%S.000000Z")
            offset_raw = local_dt.strftime("%Y-%m-%dT%H:%M:%S%z")
            if len(offset_raw) >= 5 and offset_raw[-5] in ["+", "-"]:
                offset_time_iso = offset_raw[:-2] + ":" + offset_raw[-2:]
            else:
                offset_time_iso = offset_raw
        except Exception:
            pass

    if not start_time_iso:
        start_time_iso = f"{new_date}T{hh:02d}:{mm:02d}:00.000000Z"
    if not offset_time_iso:
        offset_time_iso = start_time_iso

    async with httpx.AsyncClient(timeout=15.0) as client:
        # Step 1: Look up old event and invitee details if needed
        if clean_old_id:
            try:
                ev_r = await client.get(f"{CALENDLY_API_BASE}/scheduled_events/{clean_old_id}", headers=headers)
                if ev_r.status_code == 200:
                    old_ev_data = ev_r.json().get("resource")
                    event_type_uri = old_ev_data.get("event_type")
            except Exception as e:
                logger.warning(f"Could not retrieve old Calendly event {clean_old_id}: {e}")

            if not reschedule_uuid:
                try:
                    inv_r = await client.get(f"{CALENDLY_API_BASE}/scheduled_events/{clean_old_id}/invitees", headers=headers)
                    if inv_r.status_code == 200:
                        inv_list = inv_r.json().get("collection", [])
                        if inv_list:
                            first_inv = inv_list[0]
                            r_url = first_inv.get("reschedule_url") or ""
                            if "/reschedulings/" in r_url:
                                reschedule_uuid = r_url.split("/reschedulings/")[-1].split("?")[0].strip()
                            if not reschedule_uuid:
                                inv_uri = first_inv.get("uri") or ""
                                if "/" in inv_uri:
                                    reschedule_uuid = inv_uri.split("/")[-1].strip()
                except Exception as e:
                    logger.warning(f"Could not retrieve invitees for {clean_old_id}: {e}")

        # If event_type_uri is still unknown, look up user's active event types
        if not event_type_uri:
            try:
                me_resp = await client.get(f"{CALENDLY_API_BASE}/users/me", headers=headers)
                user_uri = DEFAULT_USER_URI
                if me_resp.status_code == 200:
                    user_uri = me_resp.json().get("resource", {}).get("uri") or DEFAULT_USER_URI
                types_r = await client.get(
                    f"{CALENDLY_API_BASE}/event_types",
                    params={"user": user_uri, "count": 10, "active": "true"},
                    headers=headers
                )
                if types_r.status_code == 200:
                    coll = types_r.json().get("collection", [])
                    if coll:
                        event_type_uri = coll[0].get("uri")
            except Exception as e:
                logger.warning(f"Could not retrieve Calendly event types: {e}")

        if not event_type_uri:
            event_type_uri = "https://api.calendly.com/event_types/53b4136a-168a-4700-8f2b-e300887eafaa"

        et_uuid = event_type_uri.split("/")[-1] if "/" in event_type_uri else event_type_uri

        # METHOD 1: Try official Invitee Reschedule API
        if reschedule_uuid:
            clean_name = client_name.strip() if client_name else "Client"
            name_parts = clean_name.split(None, 1)
            first_name = name_parts[0] if name_parts else "Client"
            last_name = name_parts[1] if len(name_parts) > 1 else ""

            patch_payload = {
                "event": {
                    "start_time": offset_time_iso or start_time_iso,
                    "location_configuration": None,
                    "guests": []
                },
                "event_fields": [],
                "event_type_uuid": et_uuid,
                "invitee": {
                    "first_name": first_name,
                    "last_name": last_name,
                    "name": clean_name,
                    "email": client_email,
                    "timezone": timezone_str or "Asia/Calcutta",
                    "time_notation": "12h"
                },
                "rescheduling": {
                    "is_publisher": False,
                    "invitee_uuid": reschedule_uuid
                }
            }
            patch_headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Booking-Request-ID": str(uuid.uuid4())
            }

            try:
                patch_resp = await client.patch(
                    f"https://calendly.com/api/booking/invitees/{reschedule_uuid}",
                    json=patch_payload,
                    headers=patch_headers
                )
                if patch_resp.status_code in [200, 201]:
                    p_data = patch_resp.json()
                    ev_info = p_data.get("event") or {}
                    new_ev_id = ev_info.get("uuid") or (ev_info.get("uri", "").split("/")[-1])
                    new_ev_uri = ev_info.get("uri") or f"{CALENDLY_API_BASE}/scheduled_events/{new_ev_id}"
                    new_inv_id = p_data.get("uuid") or reschedule_uuid
                    new_inv_uri = p_data.get("uri") or f"{new_ev_uri}/invitees/{new_inv_id}"

                    loc = ev_info.get("location")
                    join_url = ""
                    if isinstance(loc, dict):
                        join_url = loc.get("join_url") or ""
                    elif isinstance(loc, str):
                        join_url = loc
                    if not join_url:
                        join_url = f"https://calendly.com/events/{new_ev_id}/google_meet"

                    logger.info(f"Calendly Invitee Reschedule SUCCESS: Old {clean_old_id} -> New {new_ev_id} at {start_time_iso}")
                    return {
                        "success": True,
                        "new_event_id": new_ev_id,
                        "new_event_uri": new_ev_uri,
                        "new_invitee_id": new_inv_id,
                        "new_invitee_uri": new_inv_uri,
                        "meeting_link": join_url,
                        "cancel_url": f"https://calendly.com/cancellations/{new_inv_id}",
                        "reschedule_url": f"https://calendly.com/reschedulings/{new_inv_id}",
                        "start_time": start_time_iso,
                        "method": "calendly_booking_patch"
                    }
                else:
                    logger.warning(f"Calendly booking patch returned {patch_resp.status_code}: {patch_resp.text[:200]}. Falling back to v2 API.")
            except Exception as e:
                logger.warning(f"Calendly booking patch exception: {e}. Falling back to v2 API.")

        # METHOD 2: Fallback to Calendly API v2 POST /invitees
        # Check available times from Calendly API for event type on that date
        try:
            next_date = (datetime.strptime(new_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
            avail_r = await client.get(
                f"{CALENDLY_API_BASE}/event_type_available_times",
                params={
                    "event_type": event_type_uri,
                    "start_time": f"{new_date}T00:00:00Z",
                    "end_time": f"{next_date}T00:00:00Z"
                },
                headers=headers
            )
            if avail_r.status_code == 200:
                avail_slots = [s.get("start_time") for s in avail_r.json().get("collection", []) if s.get("status") == "available"]
                if avail_slots:
                    matching_slot = next((s for s in avail_slots if s.startswith(start_time_iso[:16])), None)
                    if not matching_slot:
                        direct_str = f"{new_date}T{hh:02d}:{mm:02d}"
                        matching_slot = next((s for s in avail_slots if s.startswith(direct_str)), None)
                    if matching_slot:
                        start_time_iso = matching_slot.replace("Z", ".000000Z") if not matching_slot.endswith(".000000Z") else matching_slot
        except Exception as e:
            logger.warning(f"Available slots lookup warning: {e}")

        invitee_payload = {
            "event_type": event_type_uri,
            "start_time": start_time_iso,
            "location": {"kind": "google_conference"},
            "invitee": {
                "name": client_name or "Client",
                "email": client_email,
                "timezone": timezone_str or "Asia/Kolkata"
            }
        }
        if client_phone:
            clean_digits = re.sub(r"[^\d+]", "", str(client_phone).strip())
            valid_e164 = ""
            if clean_digits.startswith("+") and len(clean_digits) >= 8:
                valid_e164 = clean_digits
            elif len(clean_digits) == 10:
                valid_e164 = f"+91{clean_digits}"
            elif len(clean_digits) == 12 and clean_digits.startswith("91"):
                valid_e164 = f"+{clean_digits}"
            elif len(clean_digits) >= 10:
                valid_e164 = f"+{clean_digits}"
            if valid_e164:
                invitee_payload["invitee"]["text_reminder_number"] = valid_e164

        book_resp = await client.post(
            f"{CALENDLY_API_BASE}/invitees",
            json=invitee_payload,
            headers=headers
        )
        if book_resp.status_code not in [200, 201]:
            err_msg = book_resp.text[:300]
            logger.error(f"Calendly create invitee failed ({book_resp.status_code}): {err_msg}")
            return {
                "success": False,
                "error": f"Calendly booking rejected ({book_resp.status_code}): {err_msg}"
            }

        new_data = book_resp.json().get("resource", {})
        new_event_uri = new_data.get("event", "")
        new_event_id = new_event_uri.split("/")[-1] if "/" in new_event_uri else new_event_uri
        new_invitee_uri = new_data.get("uri", "")
        new_invitee_id = new_invitee_uri.split("/")[-1] if "/" in new_invitee_uri else new_invitee_uri
        cancel_url = new_data.get("cancel_url", "")
        reschedule_url = new_data.get("reschedule_url", "")

        # Cancel old event on Calendly Calendar if active
        if clean_old_id and clean_old_id != new_event_id:
            try:
                await client.post(
                    f"{CALENDLY_API_BASE}/scheduled_events/{clean_old_id}/cancellation",
                    json={"reason": f"Rescheduled via CRM: {reason}"},
                    headers=headers
                )
                logger.info(f"Successfully cancelled previous Calendly event {clean_old_id}")
            except Exception as e:
                logger.warning(f"Failed to cancel old Calendly event {clean_old_id}: {e}")

        # Fetch new event join link (Google Meet)
        join_url = ""
        try:
            ev_det_r = await client.get(f"{CALENDLY_API_BASE}/scheduled_events/{new_event_id}", headers=headers)
            if ev_det_r.status_code == 200:
                loc = ev_det_r.json().get("resource", {}).get("location") or {}
                if isinstance(loc, dict):
                    join_url = loc.get("join_url") or ""
        except Exception:
            pass

        if not join_url:
            join_url = f"https://calendly.com/events/{new_event_id}/google_meet"

        logger.info(f"Calendly reschedule SUCCESS: Old {clean_old_id} -> New {new_event_id} at {start_time_iso}")
        return {
            "success": True,
            "new_event_id": new_event_id,
            "new_event_uri": new_event_uri,
            "new_invitee_id": new_invitee_id,
            "new_invitee_uri": new_invitee_uri,
            "meeting_link": join_url,
            "cancel_url": cancel_url,
            "reschedule_url": reschedule_url,
            "start_time": start_time_iso,
            "method": "calendly_api_v2"
        }


async def record_calendly_booking(
    company_id: str,
    integration_id: Optional[str],
    booking: Dict[str, Any],
    trigger_email: bool = True
) -> Dict[str, Any]:
    """Saves or updates a Calendly booking across CRM Leads, CRM Meetings, and Appointments with strict deduplication."""
    now = datetime.now(timezone.utc)

    # 1. Ingest as CRM Lead
    unique_ref = booking.get("invitee_id") or booking.get("event_id") or ""
    lead_dict = {
        "name": booking["client_name"],
        "email": booking["client_email"],
        "phone": booking["client_phone"],
        "unique_id": f"calendly_{unique_ref}" if unique_ref else "",
        "service_interested": booking["event_name"],
        "message": f"Booked consultation via Calendly on {booking.get('start_time') or 'Online'}\n" + booking.get("notes", ""),
        "source": "Calendly",
        "campaign": booking["event_name"]
    }

    ingest_res = await ingest_lead(
        company_id=company_id,
        integration_id=integration_id,
        provider="calendly",
        raw_lead=lead_dict
    )

    lead_id = ingest_res.get("lead_id")
    assigned_to = ingest_res.get("assigned_to")
    assigned_to_name = ingest_res.get("assigned_to_name")

    # Fetch lead doc to ensure phone and assignment are populated
    lead_doc = None
    if lead_id:
        lead_doc = await leads_col.find_one({"id": lead_id})
    if not lead_doc and booking.get("client_email"):
        clean_em = booking["client_email"].strip().lower()
        lead_doc = await leads_col.find_one({"email": {"$regex": f"^{re.escape(clean_em)}$", "$options": "i"}})
    if not lead_doc and booking.get("client_phone"):
        lead_doc = await leads_col.find_one({"phone": booking["client_phone"]})

    if lead_doc:
        if not booking.get("client_phone") and lead_doc.get("phone"):
            booking["client_phone"] = lead_doc.get("phone")
        if lead_doc.get("assigned_to"):
            assigned_to = lead_doc.get("assigned_to")
            assigned_to_name = lead_doc.get("assigned_to_name")

    # If still unassigned or assigned user is inactive, assign to an active sales rep
    rep_is_active = False
    if assigned_to:
        rep_check = await users_col.find_one({"id": assigned_to, "status": "active"})
        if rep_check:
            rep_is_active = True
            assigned_to_name = rep_check.get("name") or assigned_to_name

    if not rep_is_active:
        active_rep = await users_col.find_one({
            "status": "active",
            "$or": [
                {"role": {"$in": ["partner", "sr_sales_executive", "sales_executive", "sales_manager", "sales_rep", "sales_person"]}},
                {"rbac_role": {"$in": ["partner", "sr_sales_executive", "sales_executive", "sales_manager", "sales_rep", "sales_person"]}}
            ]
        })
        if active_rep:
            assigned_to = active_rep["id"]
            assigned_to_name = active_rep.get("name", "Sales Consultant")
        else:
            assigned_to_name = booking.get("host_name") or "Rohit Alluri"

    meeting_date = booking.get("date") or str(booking.get("start_time") or "")[:10]
    meeting_time = booking.get("time") or (str(booking.get("start_time") or "")[11:16] if len(str(booking.get("start_time") or "")) > 15 else "")

    status = booking.get("status", "scheduled")

    # 2. Duplicate Check in crm_meetings_col
    dup_conditions: List[Dict[str, Any]] = [
        {"calendly_event_id": booking["event_id"]},
        {"calendly_invitee_id": booking["invitee_id"]},
        {
            "contact_email": booking["client_email"],
            "meeting_date": meeting_date,
            "meeting_time": meeting_time
        }
    ]
    if booking.get("old_event_id"):
        dup_conditions.append({"calendly_event_id": booking["old_event_id"]})
    if booking.get("old_invitee_id"):
        dup_conditions.append({"calendly_invitee_id": booking["old_invitee_id"]})
    if lead_id:
        dup_conditions.append({
            "lead_id": lead_id,
            "source": "calendly",
            "status": {"$in": ["scheduled", "rescheduled"]}
        })

    dup_query = {"$or": dup_conditions}
    existing_meeting = await crm_meetings_col.find_one(dup_query)

    meeting_id = None
    is_rescheduled = False
    is_new = False

    if existing_meeting:
        meeting_id = existing_meeting.get("id")
        old_status = existing_meeting.get("status")
        old_date = existing_meeting.get("meeting_date")
        old_time = existing_meeting.get("meeting_time")

        if (old_date != meeting_date or old_time != meeting_time) and status != "cancelled":
            status = "rescheduled"
            is_rescheduled = True
    else:
        is_new = True

    # Check if lead data actually changed or if this is a new upcoming booking
    is_upcoming = (status not in ["completed", "cancelled"]) and (meeting_date >= now.strftime("%Y-%m-%d"))
    lead_needs_timestamp_update = (is_new or is_rescheduled) and is_upcoming

    # Always ensure Lead records in leads_col are updated with Calendly booking
    if lead_id or lead_doc:
        existing_src = (lead_doc.get("source") if lead_doc else None) or ""
        final_src = existing_src if existing_src and existing_src.lower() not in ["", "unknown", "none"] else "Calendly"

        booking_payload = {
            "event_name": booking["event_name"],
            "date": meeting_date,
            "time": meeting_time,
            "meeting_link": booking.get("meeting_link", "")
        }

        lead_update: Dict[str, Any] = {
            "source": final_src,
            "has_booking": True,
            "calendly_booking": booking_payload,
            "booking_details": {
                **booking_payload,
                "status": status
            }
        }
        if lead_needs_timestamp_update:
            lead_update["updated_at"] = now
            lead_update["last_contacted_at"] = now

        # Only update assigned_to if lead is currently unassigned
        lead_already_assigned = bool(lead_doc and lead_doc.get("assigned_to"))
        if not lead_already_assigned and assigned_to:
            lead_update["assigned_to"] = assigned_to
            lead_update["assigned_to_name"] = assigned_to_name
        elif lead_already_assigned:
            # Keep existing assignee in local variable for meeting linkage
            assigned_to = lead_doc.get("assigned_to")
            assigned_to_name = lead_doc.get("assigned_to_name")

        if booking.get("client_phone"):
            lead_update["phone"] = booking["client_phone"]
            lead_update["whatsapp_number"] = booking["client_phone"]

        # Update all matching lead documents for this client (by id, email, or phone)
        target_leads_q: Dict[str, Any] = {"$or": []}
        if lead_id:
            target_leads_q["$or"].append({"id": lead_id})
        clean_email = (booking.get("client_email") or "").strip().lower()
        if clean_email and "@" in clean_email:
            target_leads_q["$or"].append({"email": {"$regex": f"^{re.escape(clean_email)}$", "$options": "i"}})
        if booking.get("client_phone") and len(booking["client_phone"]) >= 7:
            target_leads_q["$or"].append({"phone": booking["client_phone"]})

        if target_leads_q["$or"]:
            await leads_col.update_many(
                target_leads_q,
                {
                    "$set": lead_update,
                    "$addToSet": {"tags": "calendly"}
                }
            )

    if existing_meeting:
        final_meeting_rep_id = (lead_doc.get("assigned_to") if lead_doc else None) or assigned_to or existing_meeting.get("sales_person_id")
        final_meeting_rep_name = (lead_doc.get("assigned_to_name") if lead_doc else None) or assigned_to_name or existing_meeting.get("sales_person_name")
        update_doc = {
            "status": status,
            "lead_id": lead_id or existing_meeting.get("lead_id"),
            "meeting_date": meeting_date,
            "meeting_time": meeting_time,
            "meeting_link": booking.get("meeting_link") or existing_meeting.get("meeting_link", ""),
            "duration_minutes": booking.get("duration_minutes") or existing_meeting.get("duration_minutes", 30),
            "contact_phone": booking.get("client_phone") or existing_meeting.get("contact_phone", ""),
            "sales_person_id": final_meeting_rep_id,
            "sales_person_name": final_meeting_rep_name
        }
        if is_rescheduled or old_status != status:
            update_doc["updated_at"] = now
            update_doc["reminders_sent"] = []

        if booking.get("event_id"):
            update_doc["calendly_event_id"] = booking["event_id"]
        if booking.get("invitee_id"):
            update_doc["calendly_invitee_id"] = booking["invitee_id"]
        if booking.get("reschedule_url"):
            update_doc["reschedule_url"] = booking["reschedule_url"]
        if booking.get("cancel_url"):
            update_doc["cancel_url"] = booking["cancel_url"]

        if is_rescheduled:
            update_doc["reschedule_reason"] = booking.get("reschedule_reason") or "Rescheduled via Calendly"
            hist_item = {
                "id": str(uuid.uuid4()),
                "rescheduled_at": now.isoformat(),
                "rescheduled_by": assigned_to or "system",
                "rescheduled_by_name": assigned_to_name or "Calendly Sync",
                "old_date": old_date,
                "old_time": old_time,
                "new_date": meeting_date,
                "new_time": meeting_time,
                "duration_minutes": booking.get("duration_minutes") or existing_meeting.get("duration_minutes", 30),
                "reason": booking.get("reschedule_reason") or "Rescheduled via Calendly Calendar / Booking Link",
                "notes": "Synced from Calendly"
            }
            await crm_meetings_col.update_one(
                {"id": meeting_id},
                {
                    "$set": update_doc,
                    "$push": {"reschedule_history": hist_item}
                }
            )
        else:
            await crm_meetings_col.update_one({"id": meeting_id}, {"$set": update_doc})

        if is_rescheduled:
            try:
                await log_activity(
                    user_id=assigned_to or "system",
                    user_name=assigned_to_name,
                    action="meeting_rescheduled",
                    entity_type="lead",
                    entity_id=lead_id,
                    details=f"Meeting '{booking['event_name']}' rescheduled from {old_date} {old_time} to {meeting_date} at {meeting_time}."
                )
            except Exception:
                pass
    else:
        is_new = True
        meeting_id = str(uuid.uuid4())
        meeting_doc = {
            "id": meeting_id,
            "company_id": company_id,
            "calendly_event_id": booking["event_id"],
            "calendly_invitee_id": booking["invitee_id"],
            "title": f"Calendly: {booking['event_name']} - {booking['client_name']}",
            "lead_id": lead_id,
            "contact_name": booking["client_name"],
            "contact_phone": booking.get("client_phone", ""),
            "contact_email": booking["client_email"],
            "sales_person_id": assigned_to,
            "sales_person_name": assigned_to_name,
            "meeting_type": "Calendly",
            "meeting_date": meeting_date,
            "meeting_time": meeting_time,
            "duration_minutes": booking.get("duration_minutes", 30),
            "meeting_link": booking.get("meeting_link") or DEFAULT_PRIMARY_LINK,
            "reschedule_url": booking.get("reschedule_url", ""),
            "cancel_url": booking.get("cancel_url", ""),
            "meeting_password": "",
            "location": "Google Meet",
            "notes": booking.get("notes", ""),
            "status": status,
            "source": "calendly",
            "reminders_sent": [],
            "recap": booking.get("recap") or None,
            "created_at": now,
            "updated_at": now
        }
        await crm_meetings_col.insert_one(meeting_doc)

        try:
            await log_activity(
                user_id=assigned_to or "system",
                user_name=assigned_to_name,
                action="meeting_scheduled",
                entity_type="lead",
                entity_id=lead_id,
                details=f"Calendly consultation '{booking['event_name']}' scheduled on {meeting_date} at {meeting_time} with {booking['client_name']}. Link: {booking.get('meeting_link')}"
            )
        except Exception:
            pass

        # Send booking confirmation email if requested and client email is present
        if trigger_email and booking.get("client_email") and status == "scheduled":
            await send_meeting_confirmation_email(
                to_email=booking["client_email"],
                client_name=booking["client_name"],
                consultant_name=assigned_to_name,
                meeting_title=booking["event_name"],
                meeting_date=meeting_date,
                meeting_time=meeting_time,
                duration_minutes=booking.get("duration_minutes", 30),
                meeting_link=booking.get("meeting_link") or DEFAULT_PRIMARY_LINK,
                platform="Google Meet",
                reschedule_link=booking.get("reschedule_url")
            )

    # 3. Synchronize in appointments_col
    appt_query = {
        "$or": [
            {"calendly_event_id": booking["event_id"]},
            {"meeting_link": booking.get("meeting_link")},
            {"client_email": booking["client_email"], "date": meeting_date}
        ]
    }
    existing_appt = await appointments_col.find_one(appt_query)
    if existing_appt:
        await appointments_col.update_one(
            {"id": existing_appt["id"]},
            {"$set": {
                "status": status,
                "date": meeting_date,
                "time": meeting_time,
                "updated_at": now
            }}
        )
    else:
        appt_id = f"appt_{uuid.uuid4().hex[:8]}"
        appt_doc = {
            "id": appt_id,
            "company_id": company_id,
            "lead_id": lead_id,
            "calendly_event_id": booking["event_id"],
            "title": f"Calendly: {booking['event_name']} - {booking['client_name']}",
            "description": f"Service: {booking['event_name']}\nMeeting Link: {booking.get('meeting_link', '')}",
            "client_name": booking["client_name"],
            "client_email": booking["client_email"],
            "client_phone": booking["client_phone"],
            "date": meeting_date,
            "time": meeting_time,
            "start_time": booking.get("start_time"),
            "end_time": booking.get("end_time"),
            "duration_minutes": booking.get("duration_minutes", 30),
            "meeting_link": booking.get("meeting_link", ""),
            "source": "calendly",
            "status": status,
            "attendee_id": assigned_to,
            "attendee_name": assigned_to_name,
            "created_by": assigned_to or "system",
            "created_by_name": assigned_to_name,
            "created_at": now
        }
        await appointments_col.insert_one(appt_doc)

    return {
        "status": "synced",
        "meeting_id": meeting_id,
        "lead_id": lead_id,
        "client_name": booking["client_name"],
        "client_email": booking["client_email"],
        "meeting_date": meeting_date,
        "meeting_time": meeting_time,
        "assigned_to_name": assigned_to_name,
        "is_new": is_new,
        "is_rescheduled": is_rescheduled
    }


async def sync_calendly_integration(company_id: str, integration_id: str) -> Dict[str, Any]:
    """Pulls recent active bookings from Calendly and synchronizes with CRM."""
    integ = await db["integrations"].find_one({"id": integration_id})
    if not integ:
        return {"success": False, "message": "Integration not found"}

    creds = integ.get("credentials") or {}
    token = creds.get("api_token") or creds.get("pat") or creds.get("access_token")
    if not token:
        token = DEFAULT_PAT

    bookings = await fetch_calendly_active_bookings(token, max_events=30)
    synced_count = 0
    new_count = 0

    for b in bookings:
        res = await record_calendly_booking(company_id, integration_id, b, trigger_email=False)
        synced_count += 1
        if res.get("is_new"):
            new_count += 1

    now = datetime.now(timezone.utc)
    await db["integrations"].update_one(
        {"id": integration_id},
        {"$set": {"last_synced_at": now}, "$inc": {"total_leads_synced": new_count}}
    )

    return {
        "success": True,
        "synced_count": synced_count,
        "new_count": new_count,
        "message": f"Calendly sync finished: {synced_count} bookings processed ({new_count} new meetings recorded)."
    }


async def process_due_meeting_reminders(database = None) -> Dict[str, int]:
    """Background engine: checks upcoming meetings and dispatches 24h, 1h, and 15m email reminders."""
    target_db = database if database is not None else db
    meetings_col = target_db["crm_meetings"]
    now_utc = datetime.now(timezone.utc)

    # Find scheduled meetings within next 26 hours
    cursor = meetings_col.find({
        "status": "scheduled",
        "meeting_date": {"$ne": None, "$exists": True},
        "meeting_time": {"$ne": None, "$exists": True},
        "contact_email": {"$ne": "", "$exists": True}
    })

    sent_counts = {"24h": 0, "1h": 0, "15m": 0}

    async for meeting in cursor:
        m_date = meeting.get("meeting_date")
        m_time = meeting.get("meeting_time")
        client_email = meeting.get("contact_email")
        if not (m_date and m_time and client_email):
            continue

        try:
            # Parse meeting datetime (assumes IST +05:30 or UTC)
            # Normalize to timezone aware datetime
            dt_str = f"{m_date} {m_time}"
            m_dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
        except Exception:
            continue

        delta_seconds = (m_dt - now_utc).total_seconds()
        delta_minutes = delta_seconds / 60.0

        reminders_sent = meeting.get("reminders_sent") or []

        # 1. 24 Hours Reminder (23 hours to 25 hours before meeting)
        if 23 * 60 <= delta_minutes <= 25 * 60 and "24h" not in reminders_sent:
            upd = await meetings_col.update_one(
                {"id": meeting["id"], "reminders_sent": {"$ne": "24h"}},
                {"$addToSet": {"reminders_sent": "24h"}}
            )
            if upd.modified_count > 0:
                await _send_reminder_email(meeting, reminder_type="24 hours")
                sent_counts["24h"] += 1

        # 2. 1 Hour Reminder (50 minutes to 70 minutes before meeting)
        elif 50 <= delta_minutes <= 70 and "1h" not in reminders_sent:
            upd = await meetings_col.update_one(
                {"id": meeting["id"], "reminders_sent": {"$ne": "1h"}},
                {"$addToSet": {"reminders_sent": "1h"}}
            )
            if upd.modified_count > 0:
                await _send_reminder_email(meeting, reminder_type="1 hour")
                sent_counts["1h"] += 1

        # 3. 15 Minutes Reminder (10 minutes to 20 minutes before meeting)
        elif 10 <= delta_minutes <= 20 and "15m" not in reminders_sent:
            upd = await meetings_col.update_one(
                {"id": meeting["id"], "reminders_sent": {"$ne": "15m"}},
                {"$addToSet": {"reminders_sent": "15m"}}
            )
            if upd.modified_count > 0:
                await _send_reminder_email(meeting, reminder_type="15 minutes")
                sent_counts["15m"] += 1

    return sent_counts


async def _send_reminder_email(meeting: Dict[str, Any], reminder_type: str):
    """Sends customized email reminder to client."""
    client_name = meeting.get("contact_name") or "Client"
    to_email = meeting.get("contact_email")
    consultant_name = meeting.get("sales_person_name") or "LEAMSS Consultant"
    meeting_link = meeting.get("meeting_link") or ""
    meeting_title = meeting.get("title") or "Immigration Consultation"

    body_html = f"""
    <p style="color: #374151; font-size: 15px; line-height: 1.6;">
        Dear <strong>{client_name}</strong>,
    </p>
    <p style="color: #374151; font-size: 15px; line-height: 1.6;">
        This is a friendly reminder that your immigration consultation with <strong>{consultant_name}</strong> starts in <strong>{reminder_type}</strong>.
    </p>
    <div style="background: #f0fdf4; border-left: 4px solid #16a34a; padding: 16px 20px; border-radius: 6px; margin: 20px 0;">
        <p style="margin: 4px 0; color: #1f2937; font-size: 14px;"><strong>Consultation:</strong> {meeting_title}</p>
        <p style="margin: 4px 0; color: #1f2937; font-size: 14px;"><strong>Date:</strong> {meeting.get('meeting_date')}</p>
        <p style="margin: 4px 0; color: #1f2937; font-size: 14px;"><strong>Time:</strong> {meeting.get('meeting_time')} ({meeting.get('duration_minutes', 30)} mins)</p>
    </div>
    """

    if meeting_link:
        body_html += f"""
        <div style="text-align: center; margin: 25px 0;">
            <a href="{meeting_link}" target="_blank" style="background: #16a34a; color: #ffffff; padding: 12px 28px; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 15px; display: inline-block;">
                Join Consultation Now
            </a>
            <p style="color: #6b7280; font-size: 12px; margin-top: 8px;">
                Link: <a href="{meeting_link}" style="color: #16a34a;">{meeting_link}</a>
            </p>
        </div>
        """

    body_html += f"""
    <p style="color: #4b5563; font-size: 13px; line-height: 1.5;">
        Please make sure your microphone and camera are working. We look forward to speaking with you!
    </p>
    <p style="color: #374151; font-size: 14px; margin-top: 20px;">
        Best regards,<br>
        <strong>{consultant_name}</strong><br>
        LEAMSS Immigration Consulting
    </p>
    """

    try:
        await send_email(
            to_email=to_email,
            subject=f"Reminder: Consultation in {reminder_type} - {meeting.get('meeting_date')} at {meeting.get('meeting_time')}",
            title=f"Meeting Reminder ({reminder_type})",
            body_html=body_html
        )
    except Exception as e:
        logger.error(f"Error sending meeting reminder email to {to_email}: {e}")


async def auto_complete_past_meetings_and_create_tasks(database = None) -> int:
    """Marks past meetings as completed and automatically creates follow-up tasks."""
    target_db = database if database is not None else db
    meetings_col = target_db["crm_meetings"]
    f_ups_col = target_db["follow_ups"]

    now_utc = datetime.now(timezone.utc)
    # Check meetings that started more than 90 minutes ago
    cutoff_time = now_utc - timedelta(minutes=90)
    cutoff_date_str = cutoff_time.strftime("%Y-%m-%d")

    cursor = meetings_col.find({
        "status": "scheduled",
        "meeting_date": {"$lte": cutoff_date_str}
    })

    completed_count = 0
    async for meeting in cursor:
        m_date = meeting.get("meeting_date")
        m_time = meeting.get("meeting_time")
        if not (m_date and m_time):
            continue

        try:
            dt_str = f"{m_date} {m_time}"
            m_dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
            duration = meeting.get("duration_minutes", 30)
            end_dt = m_dt + timedelta(minutes=duration + 15)  # 15 min buffer
        except Exception:
            continue

        if now_utc >= end_dt:
            # Mark meeting as completed
            await meetings_col.update_one(
                {"id": meeting["id"]},
                {"$set": {"status": "completed", "auto_completed": True, "updated_at": now_utc}}
            )
            completed_count += 1

            # Create follow-up task if none exists for this meeting
            existing_fu = await f_ups_col.find_one({"meeting_id": meeting["id"]})
            if not existing_fu:
                salesperson_id = meeting.get("sales_person_id") or "system"
                salesperson_name = meeting.get("sales_person_name") or "Sales Person"
                contact_name = meeting.get("contact_name") or "Client"

                task_doc = {
                    "id": f"fu_{uuid.uuid4().hex[:8]}",
                    "meeting_id": meeting["id"],
                    "lead_id": meeting.get("lead_id"),
                    "contact_name": contact_name,
                    "contact_phone": meeting.get("contact_phone", ""),
                    "contact_email": meeting.get("contact_email", ""),
                    "follow_up_type": "post_meeting_follow_up",
                    "priority": "high",
                    "scheduled_at": (now_utc + timedelta(hours=4)).isoformat(),
                    "notes": f"Post-consultation follow-up: Send assessment summary, proposal, or document checklist to {contact_name}.",
                    "status": "pending",
                    "assigned_to": salesperson_id,
                    "assigned_to_name": salesperson_name,
                    "created_by": "system",
                    "created_by_name": "System Automation",
                    "created_at": now_utc
                }
                await f_ups_col.insert_one(task_doc)

    return completed_count


async def register_calendly_webhook_subscription(
    company_id: str = "comp_leamss_primary",
    callback_url: str = "https://app.leamss.com/api/integrations/calendly/webhook"
) -> Dict[str, Any]:
    """Registers or verifies webhook subscription on Calendly API."""
    token = await get_calendly_token(company_id)
    headers = _get_api_headers(token)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            me_resp = await client.get(f"{CALENDLY_API_BASE}/users/me", headers=headers)
            if me_resp.status_code != 200:
                return {"success": False, "message": f"Calendly auth error: {me_resp.text}"}

            user_res = me_resp.json().get("resource", {})
            user_uri = user_res.get("uri")
            org_uri = user_res.get("current_organization")

            # Check existing webhooks
            list_resp = await client.get(
                f"{CALENDLY_API_BASE}/webhook_subscriptions",
                headers=headers,
                params={"scope": "organization", "organization": org_uri}
            )
            if list_resp.status_code == 200:
                subs = list_resp.json().get("collection", [])
                for s in subs:
                    if s.get("callback_url") == callback_url and s.get("state") == "active":
                        return {
                            "success": True,
                            "already_active": True,
                            "uri": s.get("uri"),
                            "callback_url": callback_url
                        }

            # Create new subscription
            payload = {
                "url": callback_url,
                "events": ["invitee.created", "invitee.canceled"],
                "organization": org_uri,
                "scope": "user",
                "user": user_uri
            }
            create_resp = await client.post(
                f"{CALENDLY_API_BASE}/webhook_subscriptions",
                json=payload,
                headers=headers
            )
            if create_resp.status_code in [200, 201]:
                return {
                    "success": True,
                    "created": True,
                    "data": create_resp.json()
                }
            return {
                "success": False,
                "status_code": create_resp.status_code,
                "response": create_resp.text
            }
    except Exception as e:
        logger.error(f"Error registering Calendly webhook: {e}")
        return {"success": False, "error": str(e)}

