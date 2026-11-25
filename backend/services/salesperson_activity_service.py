"""Salesperson Activity Audit Logging Service.

Permanently stores salesperson activities in MongoDB collection `salesperson_activity_logs`.
Tracks:
- Login / Logout
- Page visits
- Client profile views (with dwell duration)
- Calls (with actual duration in seconds)
- WhatsApp & Email interactions
- Follow-ups (created, completed, rescheduled)
- Notes added
- Status & Stage changes
- Document updates & agreements
- Client conversions & payments
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger("salesperson_activity")
COLLECTION = "salesperson_activity_logs"


try:
    from zoneinfo import ZoneInfo
    LOCAL_TZ = ZoneInfo("Asia/Kolkata")
except Exception:
    LOCAL_TZ = timezone(timedelta(hours=5, minutes=30))


def format_duration(seconds: Optional[int]) -> Optional[str]:
    """Formats duration in seconds to a human-readable string (e.g., '3m 12s', '45s').

    Returns None if seconds is None or negative.
    """
    if seconds is None or seconds < 0:
        return None
    seconds = int(seconds)
    if seconds == 0:
        return "0s"
    minutes = seconds // 60
    rem_seconds = seconds % 60
    hours = minutes // 60
    rem_minutes = minutes % 60

    if hours > 0:
        return f"{hours}h {rem_minutes}m {rem_seconds}s"
    elif minutes > 0:
        return f"{minutes}m {rem_seconds}s"
    else:
        return f"{seconds}s"


async def log_salesperson_activity(
    db,
    salesperson_id: str,
    salesperson_name: str,
    activity_type: str,
    salesperson_email: Optional[str] = None,
    salesperson_role: Optional[str] = None,
    client_id: Optional[str] = None,
    client_name: Optional[str] = None,
    client_email: Optional[str] = None,
    client_phone: Optional[str] = None,
    title: Optional[str] = None,
    details: Optional[str] = None,
    duration_seconds: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
    timestamp: Optional[datetime] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    session_state: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Inserts an immutable salesperson activity log entry into MongoDB.

    Duration is strictly recorded from actual events (e.g. real call durations,
    dwell time). Never generates artificial or fake duration numbers.
    """
    if not salesperson_id or not activity_type:
        return None

    try:
        now = timestamp or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        now_local = now.astimezone(LOCAL_TZ)
        date_str = now_local.strftime("%Y-%m-%d")
        time_str = now_local.strftime("%I:%M:%S %p")

        meta = dict(metadata or {})
        st = start_time or meta.get("start_time") or time_str
        et = end_time or meta.get("end_time")
        s_state = session_state or meta.get("session_state") or ("active" if not et and activity_type in ["client_view", "client_profile_view"] else "completed")

        # Auto-generate meaningful title if not provided
        if not title:
            act_label = activity_type.replace("_", " ").title()
            if client_name:
                title = f"{act_label} - {client_name}"
            else:
                title = f"{act_label} by {salesperson_name or 'Salesperson'}"

        # Clean duration
        clean_duration: Optional[int] = None
        if duration_seconds is not None:
            try:
                clean_duration = max(0, int(duration_seconds))
            except (ValueError, TypeError):
                clean_duration = None

        doc = {
            "id": f"sp_act_{uuid.uuid4().hex[:12]}",
            "salesperson_id": str(salesperson_id),
            "salesperson_name": str(salesperson_name or "Unknown Salesperson"),
            "salesperson_email": str(salesperson_email or ""),
            "salesperson_role": str(salesperson_role or "sales_person"),
            "client_id": str(client_id) if client_id else None,
            "client_name": str(client_name) if client_name else None,
            "client_email": str(client_email) if client_email else None,
            "client_phone": str(client_phone) if client_phone else None,
            "activity_type": str(activity_type).lower().strip(),
            "title": str(title),
            "details": str(details or ""),
            "duration_seconds": clean_duration,
            "duration_display": format_duration(clean_duration),
            "start_time": st,
            "end_time": et,
            "session_state": s_state,
            "metadata": meta,
            "date": date_str,
            "time": time_str,
            "created_at": now,
        }

        await db[COLLECTION].insert_one(doc)

        # Return serializable copy
        res = dict(doc)
        if "_id" in res:
            del res["_id"]
        res["created_at"] = now.isoformat()
        return res
    except Exception as e:
        logger.error(f"Failed to log salesperson activity: {e}", exc_info=True)
        return None
