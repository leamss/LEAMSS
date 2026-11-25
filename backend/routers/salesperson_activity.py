"""Real-Time Salesperson Activity Audit Log Router for Admin.

Provides immutable real-time tracking of:
- Logins & logouts
- Page visits & CRM navigation
- Client profile views (with dwell time duration)
- Calls (with actual recorded talk duration in seconds)
- WhatsApp and Email interactions
- Follow-up creations & completions
- Notes added
- Lead stage & status changes
- Document uploads & updates
- Meetings & payment discussions

Restricted strictly to Administrator roles for reading/querying logs.
"""
from __future__ import annotations

import csv
import io
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel

from core.auth import get_current_user
from core.database import db, users_col
from services.salesperson_activity_service import (
    COLLECTION,
    format_duration,
    log_salesperson_activity,
)

logger = logging.getLogger("salesperson_activity")
router = APIRouter(prefix="/salesperson-activity", tags=["Salesperson Activity Audit"])

activity_logs_col = db[COLLECTION]
audit_logs_col = db["audit_logs"]
crm_audit_logs_col = db["crm_audit_logs"]


def _require_admin(user: dict):
    """Enforces that only Admin, Admin Owner, or Super Admin can access Activity Audit Logs."""
    role = str(user.get("role") or "").lower()
    rbac_role = str(user.get("rbac_role") or "").lower()
    allowed = ["admin", "admin_owner", "super_admin"]
    if role not in allowed and rbac_role not in allowed:
        raise HTTPException(status_code=403, detail="Admin access required for Salesperson Activity Audit Log.")


def _can_access_rep_activity(user: dict, target_rep_id: str) -> bool:
    """Returns True if user is Admin or if user is requesting their own activity report."""
    role = str(user.get("role") or "").lower()
    rbac_role = str(user.get("rbac_role") or "").lower()
    allowed_admin = ["admin", "admin_owner", "super_admin"]
    if role in allowed_admin or rbac_role in allowed_admin:
        return True

    current_uid = str(user.get("id") or user.get("_id") or "").strip()
    current_email = str(user.get("email") or "").strip().lower()
    t_id = str(target_rep_id or "").strip()
    t_email = str(target_rep_id or "").strip().lower()

    if current_uid and current_uid == t_id:
        return True
    if current_email and current_email == t_email:
        return True
    return False


class LogClientActivityRequest(BaseModel):
    activity_type: str
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    client_email: Optional[str] = None
    client_phone: Optional[str] = None
    title: Optional[str] = None
    details: Optional[str] = None
    duration_seconds: Optional[int] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    session_state: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# ────────────────────────────────────────────────────────────
# 1. ADMIN AUDIT LOG QUERIES & LIVE FEED
# ────────────────────────────────────────────────────────────

@router.get("/logs")
async def get_activity_logs(
    salesperson_id: Optional[str] = Query(None),
    client_id: Optional[str] = Query(None),
    client_search: Optional[str] = Query(None),
    activity_type: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),  # YYYY-MM-DD
    end_date: Optional[str] = Query(None),    # YYYY-MM-DD
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user)
):
    """Admin-only query for salesperson activity audit logs with full filtering."""
    _require_admin(current_user)

    query: Dict[str, Any] = {}

    if salesperson_id and salesperson_id.strip() not in ["", "all"]:
        query["salesperson_id"] = salesperson_id.strip()

    if client_id and client_id.strip() not in ["", "all"]:
        query["client_id"] = client_id.strip()

    if client_search and client_search.strip():
        rgx = {"$regex": client_search.strip(), "$options": "i"}
        query["$or"] = [
            {"client_name": rgx},
            {"client_email": rgx},
            {"client_phone": rgx},
            {"client_id": rgx}
        ]

    if activity_type and activity_type.strip() not in ["", "all"]:
        act_clean = activity_type.strip().lower()
        if act_clean == "follow_up":
            query["activity_type"] = {"$in": ["follow_up", "follow_up_created", "follow_up_completed", "follow_up_rescheduled"]}
        elif act_clean == "call":
            query["activity_type"] = {"$in": ["call", "phone_call", "telephony_call"]}
        elif act_clean == "client_view":
            query["activity_type"] = {"$in": ["client_view", "client_profile_view"]}
        else:
            query["activity_type"] = act_clean

    # Date range filtering
    if start_date or end_date:
        date_q: Dict[str, Any] = {}
        if start_date:
            date_q["$gte"] = start_date.strip()
        if end_date:
            date_q["$lte"] = end_date.strip()
        query["date"] = date_q

    # Free text search across title, details, salesperson_name, client_name
    if search and search.strip():
        search_rgx = {"$regex": search.strip(), "$options": "i"}
        or_clauses = [
            {"salesperson_name": search_rgx},
            {"client_name": search_rgx},
            {"title": search_rgx},
            {"details": search_rgx},
            {"activity_type": search_rgx}
        ]
        if "$or" in query:
            query["$and"] = query.get("$and", []) + [{"$or": query.pop("$or")}, {"$or": or_clauses}]
        else:
            query["$or"] = or_clauses

    total = await activity_logs_col.count_documents(query)
    skip = (page - 1) * limit

    cursor = activity_logs_col.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit)
    items = await cursor.to_list(limit)

    for item in items:
        if isinstance(item.get("created_at"), datetime):
            item["created_at"] = item["created_at"].isoformat()

    total_pages = (total + limit - 1) // limit if total > 0 else 1

    return {
        "success": True,
        "logs": items,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "has_more": page < total_pages
    }


@router.get("/live-feed")
async def get_live_feed(
    since: Optional[str] = Query(None),
    limit: int = Query(25, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """Admin-only real-time live feed. Returns new events since timestamp or top recent."""
    _require_admin(current_user)

    query: Dict[str, Any] = {}
    if since:
        try:
            dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
            query["created_at"] = {"$gt": dt}
        except Exception:
            pass

    cursor = activity_logs_col.find(query, {"_id": 0}).sort("created_at", -1).limit(limit)
    items = await cursor.to_list(limit)

    for item in items:
        if isinstance(item.get("created_at"), datetime):
            item["created_at"] = item["created_at"].isoformat()

    return {
        "success": True,
        "events": items,
        "count": len(items),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/stats")
async def get_activity_stats(
    days: int = Query(7, ge=1, le=90),
    salesperson_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """Admin-only overview KPIs and breakdown metrics."""
    _require_admin(current_user)

    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")
    yesterday_str = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    start_date = (now - timedelta(days=days)).strftime("%Y-%m-%d")

    base_query: Dict[str, Any] = {"date": {"$gte": start_date}}
    if salesperson_id and salesperson_id.strip() not in ["", "all"]:
        base_query["salesperson_id"] = salesperson_id.strip()

    # Total in window
    total_in_period = await activity_logs_col.count_documents(base_query)

    # Today & Yesterday
    today_q = dict(base_query, date=today_str)
    yesterday_q = dict(base_query, date=yesterday_str)
    today_count = await activity_logs_col.count_documents(today_q)
    yesterday_count = await activity_logs_col.count_documents(yesterday_q)

    # Aggregations by activity type
    pipeline_types = [
        {"$match": base_query},
        {"$group": {"_id": "$activity_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    by_type_cur = activity_logs_col.aggregate(pipeline_types)
    by_type: Dict[str, int] = {}
    async for item in by_type_cur:
        by_type[item["_id"]] = item["count"]

    # Talk time & Call Stats
    call_query = dict(base_query, activity_type={"$in": ["call", "phone_call", "telephony_call"]})
    pipeline_calls = [
        {"$match": call_query},
        {"$group": {
            "_id": None,
            "total_calls": {"$sum": 1},
            "total_talk_time": {"$sum": "$duration_seconds"}
        }}
    ]
    call_stats_cur = activity_logs_col.aggregate(pipeline_calls)
    total_calls = 0
    total_talk_time_seconds = 0
    async for cs in call_stats_cur:
        total_calls = cs.get("total_calls") or 0
        total_talk_time_seconds = cs.get("total_talk_time") or 0

    # Active Salespersons in period
    active_reps = await activity_logs_col.distinct("salesperson_id", base_query)

    # Top Salespersons by activity count
    pipeline_reps = [
        {"$match": base_query},
        {"$group": {
            "_id": "$salesperson_id",
            "name": {"$first": "$salesperson_name"},
            "count": {"$sum": 1},
            "calls": {"$sum": {"$cond": [{"$in": ["$activity_type", ["call", "phone_call"]]}, 1, 0]}},
            "talk_time": {"$sum": {"$cond": [{"$in": ["$activity_type", ["call", "phone_call"]]}, "$duration_seconds", 0]}}
        }},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    reps_cur = activity_logs_col.aggregate(pipeline_reps)
    top_reps = []
    async for r in reps_cur:
        top_reps.append({
            "id": r["_id"],
            "name": r.get("name") or "Salesperson",
            "activities_count": r["count"],
            "calls_count": r.get("calls") or 0,
            "talk_time_display": format_duration(r.get("talk_time")) or "0s"
        })

    return {
        "success": True,
        "period_days": days,
        "total_activities": total_in_period,
        "today_activities": today_count,
        "yesterday_activities": yesterday_count,
        "total_calls": total_calls,
        "total_talk_time_seconds": total_talk_time_seconds,
        "total_talk_time_display": format_duration(total_talk_time_seconds) or "0s",
        "total_whatsapp": by_type.get("whatsapp", 0),
        "total_emails": by_type.get("email", 0),
        "total_follow_ups": by_type.get("follow_up", 0) + by_type.get("follow_up_completed", 0) + by_type.get("follow_up_created", 0),
        "total_notes": by_type.get("note", 0) + by_type.get("note_added", 0),
        "total_stage_changes": by_type.get("status_change", 0) + by_type.get("stage_change", 0),
        "total_profile_views": by_type.get("client_view", 0) + by_type.get("client_profile_view", 0),
        "active_salespersons_count": len(active_reps),
        "by_type": by_type,
        "top_salespersons": top_reps
    }


@router.get("/filters")
async def get_filter_options(current_user: dict = Depends(get_current_user)):
    """Admin-only helper returning distinct salespersons and activity types for filters."""
    _require_admin(current_user)

    # Salespersons from DB
    sales_roles = ["partner", "sales_executive", "sales_rep", "sales_person", "sales", "internal_salesperson", "sales_manager", "sales_head"]
    reps = await users_col.find(
        {"$or": [{"role": {"$in": sales_roles}}, {"rbac_role": {"$in": sales_roles}}]},
        {"_id": 0, "id": 1, "name": 1, "email": 1, "role": 1, "rbac_role": 1}
    ).sort("name", 1).to_list(200)

    # Activity types definition
    activity_types = [
        {"key": "call", "label": "Calls (with Duration)", "icon": "Phone"},
        {"key": "client_view", "label": "Client Profile Views", "icon": "Eye"},
        {"key": "page_visit", "label": "CRM Page Visits", "icon": "Compass"},
        {"key": "whatsapp", "label": "WhatsApp Messages", "icon": "MessageCircle"},
        {"key": "email", "label": "Emails Sent", "icon": "Mail"},
        {"key": "follow_up", "label": "Follow-ups (Created/Done)", "icon": "Clock"},
        {"key": "note", "label": "Notes Added", "icon": "FileText"},
        {"key": "status_change", "label": "Lead Stage Changes", "icon": "TrendingUp"},
        {"key": "document", "label": "Document Updates", "icon": "FileCheck"},
        {"key": "login", "label": "User Logins", "icon": "LogIn"},
        {"key": "logout", "label": "User Logouts", "icon": "LogOut"},
    ]

    return {
        "success": True,
        "salespersons": reps,
        "activity_types": activity_types
    }


@router.get("/export")
async def export_activity_csv(
    salesperson_id: Optional[str] = Query(None),
    client_id: Optional[str] = Query(None),
    activity_type: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(5000, le=10000),
    current_user: dict = Depends(get_current_user)
):
    """Admin-only (or Salesperson exporting own) CSV export of filtered activity logs."""
    if salesperson_id and salesperson_id.strip() not in ["", "all"]:
        if not _can_access_rep_activity(current_user, salesperson_id.strip()):
            raise HTTPException(status_code=403, detail="Access denied. You can only export your own activity logs.")
    else:
        _require_admin(current_user)

    query: Dict[str, Any] = {}
    if salesperson_id and salesperson_id.strip() not in ["", "all"]:
        query["salesperson_id"] = salesperson_id.strip()
    if client_id and client_id.strip() not in ["", "all"]:
        query["client_id"] = client_id.strip()
    if activity_type and activity_type.strip() not in ["", "all"]:
        query["activity_type"] = activity_type.strip().lower()
    if start_date or end_date:
        date_q: Dict[str, Any] = {}
        if start_date:
            date_q["$gte"] = start_date.strip()
        if end_date:
            date_q["$lte"] = end_date.strip()
        query["date"] = date_q
    if search and search.strip():
        search_rgx = {"$regex": search.strip(), "$options": "i"}
        query["$or"] = [
            {"salesperson_name": search_rgx},
            {"client_name": search_rgx},
            {"title": search_rgx},
            {"details": search_rgx}
        ]

    items = await activity_logs_col.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Activity ID", "Salesperson Name", "Salesperson Email", "Salesperson Role",
        "Client Name", "Client Phone", "Activity Type", "Title", "Duration",
        "Duration Seconds", "Date", "Exact Timestamp (UTC)", "Details"
    ])

    for item in items:
        dt = item.get("created_at")
        dt_str = dt.isoformat() if isinstance(dt, datetime) else str(dt or "")
        writer.writerow([
            item.get("id"),
            item.get("salesperson_name"),
            item.get("salesperson_email"),
            item.get("salesperson_role"),
            item.get("client_name") or "—",
            item.get("client_phone") or "—",
            item.get("activity_type"),
            item.get("title"),
            item.get("duration_display") or "—",
            item.get("duration_seconds") if item.get("duration_seconds") is not None else "",
            item.get("date"),
            dt_str,
            item.get("details")
        ])

    csv_data = output.getvalue()
    filename = f"salesperson_activity_audit_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ────────────────────────────────────────────────────────────
# 2. CLIENT-SIDE TELEMETRY / BEACON ENDPOINTS
# ────────────────────────────────────────────────────────────

@router.post("/log")
async def log_client_activity(
    req: LogClientActivityRequest,
    current_user: dict = Depends(get_current_user)
):
    """Endpoint for salesperson frontend to log page visits, client profile views, etc."""
    res = await log_salesperson_activity(
        db=db,
        salesperson_id=current_user.get("id") or str(current_user.get("_id")),
        salesperson_name=current_user.get("name") or "Salesperson",
        salesperson_email=current_user.get("email"),
        salesperson_role=current_user.get("rbac_role") or current_user.get("role"),
        activity_type=req.activity_type,
        client_id=req.client_id,
        client_name=req.client_name,
        client_email=req.client_email,
        client_phone=req.client_phone,
        title=req.title,
        details=req.details,
        duration_seconds=req.duration_seconds,
        start_time=req.start_time,
        end_time=req.end_time,
        session_state=req.session_state,
        metadata=req.metadata,
    )
    return {"success": True, "activity": res}


@router.post("/logout")
async def log_user_logout(
    current_user: dict = Depends(get_current_user)
):
    """Logs explicit logout for a salesperson."""
    res = await log_salesperson_activity(
        db=db,
        salesperson_id=current_user.get("id") or str(current_user.get("_id")),
        salesperson_name=current_user.get("name") or "Salesperson",
        salesperson_email=current_user.get("email"),
        salesperson_role=current_user.get("rbac_role") or current_user.get("role"),
        activity_type="logout",
        title=f"Logged Out - {current_user.get('name') or 'Salesperson'}",
        details=f"User signed out of CRM session.",
    )
    return {"success": True, "activity": res}


# ────────────────────────────────────────────────────────────
# 3. CRM EMBEDDED DASHBOARD: SALESPERSONS LIST & CLIENT-WISE ACTIVITY
# ────────────────────────────────────────────────────────────

crm_calls_col = db["crm_calls"]
crm_whatsapp_col = db["crm_whatsapp_messages"]
crm_emails_col = db["crm_emails"]
follow_ups_col = db["follow_ups"]
leads_col = db["leads"]
cases_col = db["cases"]


def _normalize_dt(dt: Any) -> datetime:
    """Ensures any datetime/timestamp is returned as an offset-aware UTC datetime."""
    if not dt:
        return datetime.now(timezone.utc)
    if isinstance(dt, str):
        try:
            d = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except Exception:
            try:
                d = datetime.strptime(dt[:19], "%Y-%m-%d %H:%M:%S")
            except Exception:
                d = datetime.now(timezone.utc)
    elif isinstance(dt, datetime):
        d = dt
    else:
        d = datetime.now(timezone.utc)

    if d.tzinfo is None:
        return d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc)


try:
    from zoneinfo import ZoneInfo
    LOCAL_TZ = ZoneInfo("Asia/Kolkata")
except Exception:
    LOCAL_TZ = timezone(timedelta(hours=5, minutes=30))


def _to_local_tz(dt: Any) -> datetime:
    dt_utc = _normalize_dt(dt)
    return dt_utc.astimezone(LOCAL_TZ)


def _format_pretty_ts(dt: Any) -> str:
    if not dt:
        return "—"
    try:
        dt_local = _to_local_tz(dt)
        return dt_local.strftime("%b %d, %Y • %I:%M:%S %p")
    except Exception:
        return str(dt)


def _format_time_only(dt: Any) -> str:
    if not dt:
        return "—"
    try:
        dt_local = _to_local_tz(dt)
        return dt_local.strftime("%I:%M:%S %p")
    except Exception:
        return str(dt)


def _format_date_only(dt: Any) -> str:
    if not dt:
        return "—"
    try:
        dt_local = _to_local_tz(dt)
        return dt_local.strftime("%b %d, %Y")
    except Exception:
        return str(dt)


def _format_relative_time(dt: datetime) -> str:
    now = datetime.now(timezone.utc)
    diff = now - dt
    total_seconds = int(diff.total_seconds())
    if total_seconds < 0:
        return "Just now"
    if total_seconds < 60:
        return "Just now"
    if total_seconds < 3600:
        mins = total_seconds // 60
        return f"{mins}m ago"
    if total_seconds < 86400:
        hrs = total_seconds // 3600
        return f"{hrs}h ago"
    days = total_seconds // 86400
    if days == 1:
        return "Yesterday"
    if days < 7:
        return f"{days}d ago"
    return _format_date_only(dt)


def _get_active_status(last_dt: Optional[datetime]) -> Dict[str, Any]:
    if not last_dt:
        return {
            "status": "offline",
            "badge": "No recent activity",
            "is_active_now": False,
            "is_active_today": False,
            "relative": "—",
            "display": "—"
        }
    now_utc = datetime.now(timezone.utc)
    diff_sec = int((now_utc - last_dt).total_seconds())
    
    # Check date in local timezone
    now_local = datetime.now(LOCAL_TZ)
    last_local = _to_local_tz(last_dt)
    is_today = last_local.date() == now_local.date()
    is_now = 0 <= diff_sec < 900  # active within 15 minutes

    relative = _format_relative_time(last_dt)
    exact_fmt = _format_pretty_ts(last_dt)

    if is_now:
        badge = "Active Now"
        status = "online"
    elif is_today:
        badge = f"Active Today ({last_local.strftime('%I:%M %p')})"
        status = "today"
    else:
        badge = f"Active {relative}"
        status = "recent"

    return {
        "status": status,
        "badge": badge,
        "is_active_now": is_now,
        "is_active_today": is_today,
        "relative": relative,
        "display": exact_fmt
    }


@router.get("/salespersons-list")
async def get_salespersons_audit_list(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """Admin-only endpoint returning all salespersons with their aggregated activity metrics."""
    _require_admin(current_user)

    sales_roles = [
        "admin", "admin_owner", "super_admin",
        "sales_head", "sales_manager", "sr_sales_executive", "senior_sales_executive",
        "sales_executive", "sales_person", "sales_agent", "sales_rep", "sales",
        "partner", "external_partner"
    ]

    users = await users_col.find({
        "$and": [
            {"role": {"$ne": "client"}},
            {"user_type": {"$ne": "client"}},
            {
                "$or": [
                    {"role": {"$in": sales_roles}},
                    {"rbac_role": {"$in": sales_roles}},
                    {"department": "sales"},
                    {"role": "partner"},
                    {"user_type": "external"}
                ]
            }
        ]
    }, {"_id": 0, "password": 0}).to_list(300)

    # Also include any salesperson IDs present in activity logs
    logged_reps = await activity_logs_col.distinct("salesperson_id")
    existing_uids = {u["id"] for u in users if "id" in u}
    missing_ids = [rid for rid in logged_reps if rid and rid not in existing_uids]
    if missing_ids:
        missing_users = await users_col.find({"id": {"$in": missing_ids}}, {"_id": 0, "password": 0}).to_list(100)
        users.extend([u for u in missing_users if u.get("role") != "client" and u.get("user_type") != "client"])

    # Clean date query params
    clean_start = str(start_date).strip() if (start_date and isinstance(start_date, str) and str(start_date).strip() not in ["", "all", "None"]) else None
    clean_end = str(end_date).strip() if (end_date and isinstance(end_date, str) and str(end_date).strip() not in ["", "all", "None"]) else None

    base_log_date_q: Dict[str, Any] = {}
    if clean_start or clean_end:
        dq: Dict[str, Any] = {}
        if clean_start:
            dq["$gte"] = clean_start
        if clean_end:
            dq["$lte"] = clean_end
        base_log_date_q["date"] = dq

    salespersons_data = []

    for u in users:
        uid = u.get("id")
        if not uid:
            continue

        rep_name = u.get("name") or u.get("email") or "Unknown Salesperson"
        rep_email = u.get("email") or ""
        role_key = u.get("rbac_role") or u.get("role") or "sales_executive"
        is_ext = (
            u.get("user_type") == "external"
            or "partner" in str(role_key).lower()
            or u.get("is_external") is True
        )
        rep_type = "external" if is_ext else "internal"

        # Build all identifier aliases for this rep
        rep_identifiers = [uid]
        if rep_email and rep_email.strip() and rep_email.strip() not in rep_identifiers:
            rep_identifiers.append(rep_email.strip())
        if rep_name and rep_name.strip() and rep_name.strip() not in rep_identifiers:
            rep_identifiers.append(rep_name.strip())

        # Match query for this rep in activity logs
        rep_log_q = {
            "$and": [
                {"$or": [
                    {"salesperson_id": {"$in": rep_identifiers}},
                    {"salesperson_email": {"$in": rep_identifiers}},
                    {"salesperson_name": {"$in": rep_identifiers}}
                ]}
            ]
        }
        if base_log_date_q:
            rep_log_q["$and"].append(base_log_date_q)

        # 1. Aggregated activity counts from permanent activity logs
        act_pipeline = [
            {"$match": rep_log_q},
            {"$group": {
                "_id": "$activity_type",
                "count": {"$sum": 1},
                "talk_time": {"$sum": "$duration_seconds"}
            }}
        ]
        act_cur = activity_logs_col.aggregate(act_pipeline)
        type_counts: Dict[str, int] = {}
        total_talk_seconds = 0
        async for row in act_cur:
            type_counts[row["_id"]] = row["count"]
            if row.get("talk_time"):
                total_talk_seconds += row["talk_time"]

        # Fetch assigned leads for this rep to cover inbound client messages
        rep_assigned_leads = await leads_col.find({
            "$or": [
                {"assigned_to": {"$in": rep_identifiers}},
                {"sales_person_id": {"$in": rep_identifiers}},
                {"assigned_sales_rep_id": {"$in": rep_identifiers}},
                {"created_by": {"$in": rep_identifiers}},
                {"assigned_to_email": {"$in": rep_identifiers}},
                {"assigned_to_name": {"$in": rep_identifiers}}
            ]
        }, {"id": 1, "email": 1, "phone": 1}).to_list(1000)
        rep_lead_ids = [l["id"] for l in rep_assigned_leads if l.get("id")]
        rep_lead_emails = [l["email"].strip().lower() for l in rep_assigned_leads if l.get("email")]
        rep_lead_phones = [l["phone"].strip() for l in rep_assigned_leads if l.get("phone")]

        # 2. Check crm_calls, crm_whatsapp, crm_emails, follow_ups
        crm_call_q = {"$or": [{"sales_person_id": {"$in": rep_identifiers}}, {"created_by": {"$in": rep_identifiers}}]}
        
        wa_or = [
            {"sales_person_id": {"$in": rep_identifiers}},
            {"created_by": {"$in": rep_identifiers}}
        ]
        if rep_lead_ids:
            wa_or.append({"lead_id": {"$in": rep_lead_ids}})
        if rep_lead_phones:
            wa_or.append({"phone": {"$in": rep_lead_phones}})
        crm_wa_q = {
            "$or": wa_or,
            "status": {"$in": ["sent", "delivered", "read", "received"]}
        }

        email_or = [
            {"sales_person_id": {"$in": rep_identifiers}},
            {"created_by": {"$in": rep_identifiers}},
            {"from": {"$in": rep_identifiers}},
            {"from_email": {"$in": rep_identifiers}},
            {"to": {"$in": rep_identifiers}},
            {"to_email": {"$in": rep_identifiers}},
            {"sender": {"$in": rep_identifiers}},
            {"recipient": {"$in": rep_identifiers}}
        ]
        if rep_lead_ids:
            email_or.append({"lead_id": {"$in": rep_lead_ids}})
        if rep_lead_emails:
            email_or.append({"from_email": {"$in": rep_lead_emails}})
            email_or.append({"to_email": {"$in": rep_lead_emails}})
        crm_email_q = {"$or": email_or}
        crm_fu_q = {"$or": [{"assigned_to": {"$in": rep_identifiers}}, {"created_by": {"$in": rep_identifiers}}]}

        if clean_start or clean_end:
            dt_q = {}
            if clean_start:
                dt_q["$gte"] = clean_start
            if clean_end:
                dt_q["$lte"] = clean_end
            crm_call_q["date"] = dt_q
            crm_wa_q["date"] = dt_q
            crm_email_q["date"] = dt_q
            crm_fu_q["date"] = dt_q

        calls_logged_count = type_counts.get("call", 0) + type_counts.get("phone_call", 0)
        crm_calls_count = await crm_calls_col.count_documents(crm_call_q)
        effective_calls = max(calls_logged_count, crm_calls_count)

        # Sum call duration from crm_calls if talk_time from logs is 0
        if total_talk_seconds == 0:
            call_dur_cursor = crm_calls_col.aggregate([
                {"$match": crm_call_q},
                {"$group": {"_id": None, "total_sec": {"$sum": "$duration_seconds"}}}
            ])
            async for cs in call_dur_cursor:
                total_talk_seconds = cs.get("total_sec") or 0

        wa_logged_count = type_counts.get("whatsapp", 0)
        crm_wa_count = await crm_whatsapp_col.count_documents(crm_wa_q)
        effective_wa = max(wa_logged_count, crm_wa_count)

        emails_logged_count = type_counts.get("email", 0)
        crm_emails_count = await crm_emails_col.count_documents(crm_email_q)
        effective_emails = max(emails_logged_count, crm_emails_count)

        fu_logged_count = (
            type_counts.get("follow_up", 0) +
            type_counts.get("follow_up_created", 0) +
            type_counts.get("follow_up_completed", 0)
        )
        crm_fu_count = await follow_ups_col.count_documents(crm_fu_q)
        effective_fu = max(fu_logged_count, crm_fu_count)

        status_changes_count = type_counts.get("status_change", 0) + type_counts.get("stage_change", 0)
        notes_count = type_counts.get("note", 0) + type_counts.get("note_added", 0)
        profile_views_count = type_counts.get("client_profile_view", 0) + type_counts.get("client_view", 0)

        # Unique clients interacted with
        clients_interacted = await activity_logs_col.distinct("client_id", rep_log_q)
        clients_interacted = [cid for cid in clients_interacted if cid]
        call_clients = await crm_calls_col.distinct("lead_id", crm_call_q)
        email_clients = await crm_emails_col.distinct("lead_id", crm_email_q)
        assigned_leads_count = await leads_col.count_documents({
            "$or": [{"assigned_to": {"$in": rep_identifiers}}, {"sales_person_id": {"$in": rep_identifiers}}]
        })
        all_unique_client_ids = set([cid for cid in clients_interacted + call_clients + email_clients if cid])
        effective_clients_count = max(len(all_unique_client_ids), assigned_leads_count)

        now_utc = datetime.now(timezone.utc)
        latest_timestamps = []

        last_log = await activity_logs_col.find_one(
            {"$and": [{"salesperson_id": {"$in": rep_identifiers}}, {"created_at": {"$lte": now_utc}}]},
            sort=[("created_at", -1)]
        )
        if last_log and last_log.get("created_at"):
            latest_timestamps.append(_normalize_dt(last_log["created_at"]))

        last_call = await crm_calls_col.find_one(crm_call_q, sort=[("created_at", -1)])
        if last_call and (last_call.get("created_at") or last_call.get("timestamp")):
            latest_timestamps.append(_normalize_dt(last_call.get("created_at") or last_call.get("timestamp")))

        last_email = await crm_emails_col.find_one(crm_email_q, sort=[("created_at", -1)])
        if last_email and (last_email.get("created_at") or last_email.get("sent_at")):
            latest_timestamps.append(_normalize_dt(last_email.get("created_at") or last_email.get("sent_at")))

        last_wa = await crm_whatsapp_col.find_one(crm_wa_q, sort=[("created_at", -1)])
        if last_wa and last_wa.get("created_at"):
            latest_timestamps.append(_normalize_dt(last_wa["created_at"]))

        # Follow-up: ONLY use created_at / updated_at, NEVER scheduled_at (which is a future due date)
        last_fu = await follow_ups_col.find_one(crm_fu_q, sort=[("created_at", -1)])
        if last_fu and (last_fu.get("created_at") or last_fu.get("updated_at")):
            latest_timestamps.append(_normalize_dt(last_fu.get("created_at") or last_fu.get("updated_at")))

        # Filter strictly to past timestamps (dt <= now_utc): Last Active cannot be in the future
        past_timestamps = [t for t in latest_timestamps if t and t <= now_utc]
        most_recent_dt = max(past_timestamps) if past_timestamps else None
        active_status = _get_active_status(most_recent_dt)
        last_active_raw = most_recent_dt.isoformat() if most_recent_dt else None

        effective_total_activities = max(
            sum(type_counts.values()),
            effective_calls + effective_wa + effective_emails + effective_fu + status_changes_count + notes_count
        )

        salespersons_data.append({
            "id": uid,
            "name": rep_name,
            "email": rep_email,
            "role": role_key,
            "role_label": role_key.replace("_", " ").title(),
            "salesperson_type": rep_type,
            "is_external": is_ext,
            "total_activities": effective_total_activities,
            "calls_count": effective_calls,
            "talk_time_seconds": total_talk_seconds,
            "talk_time_display": format_duration(total_talk_seconds) if total_talk_seconds > 0 else "0s",
            "whatsapp_count": effective_wa,
            "emails_count": effective_emails,
            "followups_count": effective_fu,
            "status_changes_count": status_changes_count,
            "notes_count": notes_count,
            "profile_views_count": profile_views_count,
            "clients_count": effective_clients_count,
            "last_active_at": most_recent_dt.isoformat() if most_recent_dt else None,
            "last_active_raw": most_recent_dt.isoformat() if most_recent_dt else None,
            "last_active_display": active_status["display"],
            "last_active_relative": active_status["relative"],
            "active_badge": active_status["badge"],
            "active_status": active_status["status"],
            "is_active_now": active_status["is_active_now"],
            "is_active_today": active_status["is_active_today"]
        })

    # Filter by search if provided
    if search and isinstance(search, str) and search.strip():
        q_lower = search.strip().lower()
        salespersons_data = [
            s for s in salespersons_data
            if q_lower in s["name"].lower() or q_lower in s["email"].lower() or q_lower in s["role_label"].lower()
        ]

    # Sort by total activities then calls
    salespersons_data.sort(key=lambda x: (x["total_activities"], x["calls_count"]), reverse=True)

    team_totals = {
        "total_salespersons": len(salespersons_data),
        "total_activities": sum(s["total_activities"] for s in salespersons_data),
        "total_calls": sum(s["calls_count"] for s in salespersons_data),
        "total_talk_time_seconds": sum(s["talk_time_seconds"] for s in salespersons_data),
        "total_talk_time_display": format_duration(sum(s["talk_time_seconds"] for s in salespersons_data)) or "0s",
        "total_whatsapp": sum(s["whatsapp_count"] for s in salespersons_data),
        "total_emails": sum(s["emails_count"] for s in salespersons_data),
        "total_followups": sum(s["followups_count"] for s in salespersons_data),
        "total_status_changes": sum(s["status_changes_count"] for s in salespersons_data),
        "total_clients": sum(s["clients_count"] for s in salespersons_data)
    }

    return {
        "success": True,
        "salespersons": salespersons_data,
        "team_totals": team_totals,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/my-activity")
async def get_my_activity_report(
    client_id: Optional[str] = Query(None),
    activity_type: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """Allows a salesperson to view their own activity history, call stats, and client interactions."""
    my_id = current_user.get("id") or str(current_user.get("_id"))
    return await get_salesperson_client_history(
        salesperson_id=my_id,
        client_id=client_id,
        activity_type=activity_type,
        start_date=start_date,
        end_date=end_date,
        search=search,
        current_user=current_user
    )


@router.get("/salesperson/{salesperson_id}/client-history")
async def get_salesperson_client_history(
    salesperson_id: str,
    client_id: Optional[str] = Query(None),
    activity_type: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """Returns complete client-wise and date-wise activity history for a specific salesperson.
    
    Admin can access any salesperson; Salesperson can access only their own activity report.
    """
    if not _can_access_rep_activity(current_user, salesperson_id):
        raise HTTPException(status_code=403, detail="Access denied. You can only view your own activity report.")

    rep_user = await users_col.find_one({"$or": [{"id": salesperson_id}, {"email": salesperson_id}]}, {"_id": 0, "password": 0})

    salesperson_name = rep_user.get("name") if rep_user else "Salesperson"
    salesperson_email = rep_user.get("email") if rep_user else ""
    salesperson_role = rep_user.get("rbac_role") or rep_user.get("role") if rep_user else "sales_executive"

    # Collect all identifiers for this salesperson
    rep_identifiers = [salesperson_id]
    if rep_user and rep_user.get("id") and rep_user["id"] not in rep_identifiers:
        rep_identifiers.append(rep_user["id"])
    if salesperson_email and salesperson_email not in rep_identifiers:
        rep_identifiers.append(salesperson_email)
    if salesperson_name and salesperson_name not in rep_identifiers:
        rep_identifiers.append(salesperson_name)

    # Clean query parameters
    clean_client_id = str(client_id).strip() if (client_id and isinstance(client_id, str) and str(client_id).strip() not in ["", "all", "None"]) else None
    clean_act_type = str(activity_type).strip().lower() if (activity_type and isinstance(activity_type, str) and str(activity_type).strip() not in ["", "all", "None"]) else None
    clean_start = str(start_date).strip() if (start_date and isinstance(start_date, str) and str(start_date).strip() not in ["", "all", "None"]) else None
    clean_end = str(end_date).strip() if (end_date and isinstance(end_date, str) and str(end_date).strip() not in ["", "all", "None"]) else None
    clean_search = str(search).strip() if (search and isinstance(search, str) and str(search).strip()) else None

    # Base query for permanent activity logs
    log_q: Dict[str, Any] = {
        "$or": [
            {"salesperson_id": {"$in": rep_identifiers}},
            {"salesperson_email": {"$in": rep_identifiers}},
            {"salesperson_name": {"$in": rep_identifiers}}
        ]
    }

    if clean_client_id:
        log_q["$and"] = [{"$or": [{"client_id": clean_client_id}, {"client_name": clean_client_id}]}]

    if clean_act_type:
        if clean_act_type == "follow_up":
            log_q["activity_type"] = {"$in": ["follow_up", "follow_up_created", "follow_up_completed", "follow_up_rescheduled"]}
        elif clean_act_type == "call":
            log_q["activity_type"] = {"$in": ["call", "phone_call", "telephony_call"]}
        elif clean_act_type == "client_view":
            log_q["activity_type"] = {"$in": ["client_view", "client_profile_view"]}
        elif clean_act_type == "status_change":
            log_q["activity_type"] = {"$in": ["status_change", "stage_change"]}
        elif clean_act_type == "note":
            log_q["activity_type"] = {"$in": ["note", "note_added"]}
        else:
            log_q["activity_type"] = clean_act_type

    if clean_start or clean_end:
        dq: Dict[str, Any] = {}
        if clean_start:
            dq["$gte"] = clean_start
        if clean_end:
            dq["$lte"] = clean_end
        log_q["date"] = dq

    # Search filter
    if clean_search:
        s_rgx = {"$regex": clean_search, "$options": "i"}
        log_q["$or"] = [
            {"client_name": s_rgx},
            {"title": s_rgx},
            {"details": s_rgx},
            {"client_email": s_rgx},
            {"client_phone": s_rgx}
        ]

    # 1. Fetch from permanent activity logs
    raw_logs = await activity_logs_col.find(log_q, {"_id": 0}).sort("created_at", -1).to_list(1500)

    # 2. Fetch assigned leads for this salesperson to build complete client map
    assigned_leads = await leads_col.find({
        "$or": [
            {"assigned_to": {"$in": rep_identifiers}},
            {"sales_person_id": {"$in": rep_identifiers}},
            {"assigned_sales_rep_id": {"$in": rep_identifiers}},
            {"created_by": {"$in": rep_identifiers}},
            {"assigned_to_email": {"$in": rep_identifiers}},
            {"assigned_to_name": {"$in": rep_identifiers}}
        ]
    }, {"_id": 0}).to_list(1000)

    lead_lookup: Dict[str, Dict[str, Any]] = {}
    for l in assigned_leads:
        lid = l.get("id")
        if lid:
            lead_lookup[lid] = l

    assigned_lead_ids = [lid for lid in lead_lookup.keys() if lid]
    assigned_lead_emails = [
        l.get("email").strip().lower()
        for l in lead_lookup.values()
        if l.get("email") and str(l.get("email")).strip()
    ]
    assigned_lead_phones = [
        l.get("phone").strip()
        for l in lead_lookup.values()
        if l.get("phone") and str(l.get("phone")).strip()
    ]

    # Also lookup clients from activity logs who might not be in assigned_leads
    log_client_ids = [log["client_id"] for log in raw_logs if log.get("client_id") and log["client_id"] not in lead_lookup]
    if log_client_ids:
        extra_leads = await leads_col.find({"id": {"$in": log_client_ids}}, {"_id": 0}).to_list(len(log_client_ids))
        for el in extra_leads:
            lead_lookup[el["id"]] = el
            if el.get("email"):
                assigned_lead_emails.append(el["email"].strip().lower())
            if el.get("phone"):
                assigned_lead_phones.append(el["phone"].strip())

    # Also incorporate existing CRM calls, WhatsApp, emails, follow-ups
    existing_log_ids = {item.get("id") for item in raw_logs if item.get("id")}

    # Fetch CRM calls
    crm_call_q: Dict[str, Any] = {"$or": [{"sales_person_id": {"$in": rep_identifiers}}, {"created_by": {"$in": rep_identifiers}}]}
    if clean_client_id:
        crm_call_q["lead_id"] = clean_client_id
    raw_calls = await crm_calls_col.find(crm_call_q, {"_id": 0}).sort("created_at", -1).to_list(500)

    for c in raw_calls:
        cid = c.get("id")
        if cid and cid not in existing_log_ids:
            lid = c.get("lead_id")
            lead_info = lead_lookup.get(lid, {}) if lid else {}
            c_name = c.get("client_name") or lead_info.get("name") or "Client"
            dur_sec = c.get("duration_seconds", 0)
            t = c.get("created_at") or c.get("timestamp") or datetime.now(timezone.utc)
            t_dt = _normalize_dt(t)
            direction_raw = str(c.get("direction") or "outgoing").lower()
            call_dir = "incoming" if direction_raw in ["incoming", "inbound"] else "outgoing"
            raw_logs.append({
                "id": cid,
                "salesperson_id": salesperson_id,
                "salesperson_name": salesperson_name,
                "client_id": lid,
                "client_name": c_name,
                "client_phone": c.get("phone") or lead_info.get("phone"),
                "activity_type": "call",
                "direction": call_dir,
                "title": f"Call ({call_dir.capitalize()}) - {c_name}",
                "details": c.get("notes") or f"Call completed. Outcome: {c.get('outcome', 'completed')}",
                "duration_seconds": dur_sec,
                "duration_display": format_duration(dur_sec),
                "date": t_dt.strftime("%Y-%m-%d"),
                "created_at": t_dt,
                "metadata": {
                    "outcome": c.get("outcome"),
                    "direction": call_dir,
                    "recording_url": c.get("recording_url")
                }
            })

    # Fetch CRM WhatsApp (track all statuses: sent, delivered, read, received, failed, and pending)
    crm_wa_or = [
        {"sales_person_id": {"$in": rep_identifiers}},
        {"created_by": {"$in": rep_identifiers}}
    ]
    if assigned_lead_ids:
        crm_wa_or.append({"lead_id": {"$in": assigned_lead_ids}})
    if assigned_lead_phones:
        crm_wa_or.append({"phone": {"$in": assigned_lead_phones}})

    crm_wa_q: Dict[str, Any] = {"$or": crm_wa_or}
    if clean_client_id:
        crm_wa_q = {"$and": [crm_wa_q, {"$or": [{"lead_id": clean_client_id}, {"client_id": clean_client_id}]}]}
    raw_wa = await crm_whatsapp_col.find(crm_wa_q, {"_id": 0}).sort("created_at", -1).to_list(500)
    for w in raw_wa:
        wid = w.get("id")
        if wid and wid not in existing_log_ids:
            lid = w.get("lead_id")
            lead_info = lead_lookup.get(lid, {}) if lid else {}
            c_name = w.get("contact_name") or w.get("client_name") or lead_info.get("name") or "Client"
            t = w.get("created_at") or datetime.now(timezone.utc)
            t_dt = _normalize_dt(t)
            w_status = (w.get("status") or "sent").lower()
            status_tag = "Failed" if w_status == "failed" else ("Pending" if w_status in ["pending", "pending_confirmation"] else ("Received" if w_status == "received" else "Sent"))
            fail_suffix = f" [Failed: {w.get('error_message')}]" if w_status == "failed" and w.get("error_message") else ""
            direction_raw = str(w.get("direction") or "outbound").lower()
            wa_dir = "received" if (direction_raw in ["incoming", "inbound", "received"] or w_status == "received") else "sent"
            raw_logs.append({
                "id": wid,
                "salesperson_id": salesperson_id,
                "salesperson_name": w.get("sales_person_name") or salesperson_name,
                "client_id": lid,
                "client_name": c_name,
                "client_phone": w.get("phone") or lead_info.get("phone"),
                "activity_type": "whatsapp",
                "direction": wa_dir,
                "message_status": w_status,
                "title": f"WhatsApp Message ({wa_dir.capitalize()}) - {c_name} ({status_tag})",
                "details": f"{w.get('text') or w.get('message') or 'WhatsApp communication'}{fail_suffix}",
                "duration_seconds": None,
                "duration_display": None,
                "date": _format_date_only(t_dt),
                "time": _format_time_only(t_dt),
                "created_at": t_dt,
                "metadata": {
                    "direction": wa_dir,
                    "status": w_status,
                    "message_status": w_status,
                    "channel": w.get("channel", "whatsapp_web"),
                    "salesperson_name": w.get("sales_person_name") or salesperson_name,
                    "client_name": c_name,
                    "template": w.get("template_name"),
                    "error_message": w.get("error_message")
                }
            })

    # Fetch CRM Emails (both outbound sent and inbound received / client replies)
    crm_email_or = [
        {"sales_person_id": {"$in": rep_identifiers}},
        {"created_by": {"$in": rep_identifiers}},
        {"from": {"$in": rep_identifiers}},
        {"from_email": {"$in": rep_identifiers}},
        {"to": {"$in": rep_identifiers}},
        {"to_email": {"$in": rep_identifiers}},
        {"sender": {"$in": rep_identifiers}},
        {"recipient": {"$in": rep_identifiers}},
    ]
    if assigned_lead_ids:
        crm_email_or.append({"lead_id": {"$in": assigned_lead_ids}})
    if assigned_lead_emails:
        crm_email_or.append({"from_email": {"$in": assigned_lead_emails}})
        crm_email_or.append({"to_email": {"$in": assigned_lead_emails}})

    crm_email_q: Dict[str, Any] = {"$or": crm_email_or}
    if clean_client_id:
        crm_email_q = {"$and": [crm_email_q, {"$or": [{"lead_id": clean_client_id}, {"client_id": clean_client_id}]}]}

    raw_emails = await crm_emails_col.find(crm_email_q, {"_id": 0}).sort("created_at", -1).to_list(500)

    # Populate any missing leads from email items into lead_lookup
    missing_email_lids = [e.get("lead_id") for e in raw_emails if e.get("lead_id") and e.get("lead_id") not in lead_lookup]
    if missing_email_lids:
        extra_email_leads = await leads_col.find({"id": {"$in": missing_email_lids}}, {"_id": 0}).to_list(len(missing_email_lids))
        for eml in extra_email_leads:
            lead_lookup[eml["id"]] = eml

    rep_emails_lower = [str(r).lower().strip() for r in rep_identifiers if "@" in str(r)]
    for e in raw_emails:
        eid = e.get("id")
        if eid and eid not in existing_log_ids:
            lid = e.get("lead_id")
            lead_info = lead_lookup.get(lid, {}) if lid else {}
            t = e.get("created_at") or e.get("sent_at") or datetime.now(timezone.utc)
            t_dt = _normalize_dt(t)
            
            # Accurate direction detection
            direction_raw = str(e.get("direction") or "").lower()
            status_raw = str(e.get("status") or "").lower()
            from_e = str(e.get("from_email") or e.get("from") or "").strip().lower()
            to_e = str(e.get("to_email") or e.get("to") or "").strip().lower()

            is_received = (
                direction_raw in ["incoming", "inbound", "received"]
                or status_raw == "received"
                or (to_e in rep_emails_lower and from_e not in rep_emails_lower)
                or (from_e in [ae.lower() for ae in assigned_lead_emails] and to_e in rep_emails_lower)
            )
            email_dir = "received" if is_received else "sent"

            if is_received:
                c_name = e.get("contact_name") or lead_info.get("name") or e.get("client_name") or from_e or "Client"
                c_email = from_e or lead_info.get("email") or "—"
                subj = e.get("subject") or "Client Email Reply"
                title = f"Email (Received): {subj} - {c_name}"
                body_content = e.get("raw_text") or e.get("body") or e.get("snippet") or e.get("body_html") or "Received email reply from client"
            else:
                c_name = e.get("client_name") or lead_info.get("name") or e.get("contact_name") or to_e or "Client"
                c_email = to_e or lead_info.get("email") or "—"
                subj = e.get("subject") or "Consulting Follow-up"
                title = f"Email (Sent): {subj} - {c_name}"
                body_content = e.get("body") or e.get("snippet") or e.get("raw_text") or "Email communication"

            clean_body = re.sub(r'<[^>]+>', ' ', str(body_content)).strip()
            clean_body = ' '.join(clean_body.split())
            if len(clean_body) > 280:
                clean_body = clean_body[:277] + "..."

            raw_logs.append({
                "id": eid,
                "salesperson_id": salesperson_id,
                "salesperson_name": salesperson_name,
                "client_id": lid,
                "client_name": c_name,
                "client_email": c_email,
                "activity_type": "email",
                "direction": email_dir,
                "title": title,
                "details": clean_body or "Email communication",
                "duration_seconds": None,
                "duration_display": None,
                "date": t_dt.strftime("%Y-%m-%d"),
                "created_at": t_dt,
                "metadata": {
                    "subject": subj,
                    "direction": email_dir,
                    "status": e.get("status", "received" if is_received else "sent"),
                    "from_email": from_e,
                    "to_email": to_e
                }
            })

    # Fetch CRM Follow-ups
    crm_fu_q: Dict[str, Any] = {"$or": [{"assigned_to": {"$in": rep_identifiers}}, {"created_by": {"$in": rep_identifiers}}]}
    if clean_client_id:
        crm_fu_q["lead_id"] = clean_client_id
    now_utc = datetime.now(timezone.utc)
    raw_fu = await follow_ups_col.find(crm_fu_q, {"_id": 0}).sort("created_at", -1).to_list(500)
    for f in raw_fu:
        fid = f.get("id")
        if fid and fid not in existing_log_ids:
            lid = f.get("lead_id")
            lead_info = lead_lookup.get(lid, {}) if lid else {}
            c_name = f.get("client_name") or lead_info.get("name") or "Client"
            
            # Follow-up activity occurs when created/logged, NOT the future scheduled date
            t = f.get("created_at") or f.get("updated_at") or now_utc
            t_dt = _normalize_dt(t)
            if t_dt > now_utc:
                t_dt = now_utc

            sched_val = f.get("scheduled_at")
            sched_fmt = _format_pretty_ts(sched_val) if sched_val else None

            raw_logs.append({
                "id": fid,
                "salesperson_id": salesperson_id,
                "salesperson_name": salesperson_name,
                "client_id": lid,
                "client_name": c_name,
                "activity_type": "follow_up",
                "title": f"Follow-up: {f.get('type', 'General')} for {c_name}",
                "details": f.get("notes") or (f"Scheduled for {sched_fmt}. Status: {f.get('status', 'pending')}" if sched_fmt else f"Status: {f.get('status', 'pending')}"),
                "duration_seconds": None,
                "duration_display": None,
                "date": _format_date_only(t_dt),
                "time": _format_time_only(t_dt),
                "created_at": t_dt,
                "metadata": {"status": f.get("status"), "scheduled_at": str(sched_val) if sched_val else None, "scheduled_at_formatted": sched_fmt}
            })

    # Fetch Stage/Status changes from audit_logs (historical fallback if not yet in salesperson_activity_logs)
    audit_stage_q: Dict[str, Any] = {
        "user_id": {"$in": rep_identifiers},
        "$or": [
            {"action": {"$regex": "^moved_to_"}},
            {"action": {"$regex": "stage", "$options": "i"}},
            {"action": {"$regex": "status", "$options": "i"}}
        ]
    }
    if clean_client_id:
        audit_stage_q["$and"] = [
            audit_stage_q,
            {"$or": [{"entity_id": clean_client_id}, {"lead_id": clean_client_id}, {"case_id": clean_client_id}]}
        ]
    raw_audit_stages = await audit_logs_col.find(audit_stage_q, {"_id": 0}).sort("created_at", -1).to_list(500)
    for a in raw_audit_stages:
        aid = a.get("id") or str(uuid.uuid4())
        if aid not in existing_log_ids:
            lid = a.get("entity_id") or a.get("lead_id")
            lead_info = lead_lookup.get(lid, {}) if lid else {}
            c_name = a.get("client_name") or lead_info.get("name") or "Lead"
            t = a.get("created_at") or a.get("timestamp") or now_utc
            t_dt = _normalize_dt(t)
            old_s = str(a.get("old_value") or "").replace("_", " ").title()
            new_s = str(a.get("new_value") or a.get("action", "").replace("moved_to_", "")).replace("_", " ").title()
            raw_logs.append({
                "id": aid,
                "salesperson_id": salesperson_id,
                "salesperson_name": a.get("user_name") or salesperson_name,
                "client_id": lid,
                "client_name": c_name,
                "client_phone": lead_info.get("phone"),
                "client_email": lead_info.get("email"),
                "activity_type": "stage_change",
                "title": f"Stage Changed: {old_s} → {new_s} - {c_name}" if old_s else f"Stage Changed to {new_s} - {c_name}",
                "details": a.get("details") or f"Lead stage updated to {new_s}",
                "duration_seconds": None,
                "duration_display": None,
                "date": _format_date_only(t_dt),
                "time": _format_time_only(t_dt),
                "created_at": t_dt,
                "metadata": {
                    "previous_stage": a.get("old_value"),
                    "new_stage": a.get("new_value") or a.get("action", "").replace("moved_to_", ""),
                    "old_stage": a.get("old_value"),
                    "lead_id": lid
                }
            })
            existing_log_ids.add(aid)

    # 100% Guaranteed Offset-Aware UTC Datetime normalization
    for item in raw_logs:
        item["created_at_dt"] = _normalize_dt(item.get("created_at"))

    # Safely sort chronologically descending without any comparison errors
    raw_logs.sort(key=lambda x: x["created_at_dt"], reverse=True)

    # Calculate Local IST Today & Yesterday date bounds
    now_local = datetime.now(LOCAL_TZ)
    today_str = now_local.strftime("%Y-%m-%d")
    yesterday_str = (now_local - timedelta(days=1)).strftime("%Y-%m-%d")
    today_display = now_local.strftime("%b %d, %Y")
    yesterday_display = (now_local - timedelta(days=1)).strftime("%b %d, %Y")

    # Metrics containers
    today_stats = {
        "date": today_str,
        "date_display": today_display,
        "total_activities": 0,
        "calls_total": 0,
        "calls_incoming": 0,
        "calls_outgoing": 0,
        "talk_time_seconds": 0,
        "talk_time_display": "0s",
        "emails_total": 0,
        "emails_sent": 0,
        "emails_received": 0,
        "whatsapp_total": 0,
        "whatsapp_sent": 0,
        "whatsapp_received": 0,
        "followups_total": 0,
        "status_changes_total": 0,
        "notes_total": 0,
        "clients_interacted": set()
    }

    yesterday_stats = {
        "date": yesterday_str,
        "date_display": yesterday_display,
        "total_activities": 0,
        "calls_total": 0,
        "calls_incoming": 0,
        "calls_outgoing": 0,
        "talk_time_seconds": 0,
        "talk_time_display": "0s",
        "emails_total": 0,
        "emails_sent": 0,
        "emails_received": 0,
        "whatsapp_total": 0,
        "whatsapp_sent": 0,
        "whatsapp_received": 0,
        "followups_total": 0,
        "status_changes_total": 0,
        "notes_total": 0,
        "clients_interacted": set()
    }

    # Grouped structures
    clients_map: Dict[str, Dict[str, Any]] = {}
    date_wise_map: Dict[str, Dict[str, Any]] = {}
    timeline: List[Dict[str, Any]] = []

    for item in raw_logs:
        dt = item["created_at_dt"]
        iso_str = dt.isoformat()
        pretty_ts = _format_pretty_ts(dt)
        rel_time = _format_relative_time(dt)
        date_str = _format_date_only(dt)
        time_str = _format_time_only(dt)
        event_date_ist = _to_local_tz(dt).strftime("%Y-%m-%d")

        # Filter by clean_start / clean_end if specified
        if clean_start and event_date_ist < clean_start:
            continue
        if clean_end and event_date_ist > clean_end:
            continue

        lid = item.get("client_id") or (item.get("metadata") or {}).get("client_id") or (item.get("metadata") or {}).get("active_client_id")
        lead_info = lead_lookup.get(lid, {}) if lid else {}

        # Resolve clean client name
        c_name_cand = (
            item.get("client_name")
            or (item.get("metadata") or {}).get("client_name")
            or (item.get("metadata") or {}).get("active_client_name")
            or lead_info.get("name")
        )
        if not c_name_cand:
            t_str = str(item.get("title") or "")
            if "Client:" in t_str:
                try:
                    c_name_cand = t_str.split("Client:")[-1].split("(")[0].strip()
                except Exception:
                    pass
            elif "Working on" in t_str:
                try:
                    c_name_cand = t_str.split("Working on")[-1].split("(")[0].strip()
                except Exception:
                    pass

        client_name = c_name_cand or "Direct Activity / CRM"
        client_key = lid or client_name or "Unassigned / General"

        msg_status = item.get("message_status") or item.get("metadata", {}).get("status") or ("sent" if item.get("activity_type") == "whatsapp" else None)
        sp_name = item.get("salesperson_name") or salesperson_name

        # Resolve direction
        act_type = item.get("activity_type")
        direction = item.get("direction")
        if not direction:
            if act_type in ["call", "phone_call", "telephony_call"]:
                raw_d = str(item.get("metadata", {}).get("direction") or item.get("metadata", {}).get("call_type") or "outgoing").lower()
                direction = "incoming" if raw_d in ["incoming", "inbound"] else "outgoing"
            elif act_type == "whatsapp":
                raw_d = str(item.get("metadata", {}).get("direction") or item.get("message_status") or "sent").lower()
                direction = "received" if (raw_d in ["incoming", "inbound", "received"] or "received" in str(item.get("title", "")).lower()) else "sent"
            elif act_type == "email":
                raw_d = str(item.get("metadata", {}).get("direction") or item.get("direction") or ("received" if "received" in str(item.get("title", "")).lower() else "sent")).lower()
                direction = "received" if raw_d in ["incoming", "inbound", "received"] else "sent"

        dur_sec = item.get("duration_seconds")
        dur_display = item.get("duration_display") or ("—" if dur_sec is None else format_duration(dur_sec))

        st_event = item.get("start_time") or (item.get("metadata") or {}).get("start_time") or time_str
        et_event = item.get("end_time") or (item.get("metadata") or {}).get("end_time")
        sess_state = item.get("session_state") or (item.get("metadata") or {}).get("session_state")

        cleaned_event = {
            "id": item.get("id"),
            "activity_type": act_type,
            "direction": direction,
            "title": item.get("title"),
            "details": item.get("details"),
            "duration_seconds": dur_sec,
            "duration_display": dur_display,
            "start_time": st_event,
            "end_time": et_event,
            "session_state": sess_state,
            "date": date_str,
            "date_ist": event_date_ist,
            "time": time_str,
            "timestamp": iso_str,
            "exact_timestamp_formatted": pretty_ts,
            "relative_time": rel_time,
            "salesperson_id": item.get("salesperson_id") or salesperson_id,
            "salesperson_name": sp_name,
            "message_status": msg_status,
            "client_id": lid,
            "client_name": client_name,
            "client_phone": item.get("client_phone") or lead_info.get("phone") or "—",
            "client_email": item.get("client_email") or lead_info.get("email") or "—",
            "metadata": item.get("metadata") or {}
        }
        timeline.append(cleaned_event)

        # ─── 1. CLIENT-WISE AGGREGATION ───
        if client_key not in clients_map:
            clients_map[client_key] = {
                "client_id": lid,
                "client_name": client_name,
                "client_phone": item.get("client_phone") or lead_info.get("phone") or "—",
                "client_email": item.get("client_email") or lead_info.get("email") or "—",
                "stage": lead_info.get("stage") or lead_info.get("status") or "In Progress",
                "country": lead_info.get("country_of_interest") or "Canada",
                "service": lead_info.get("service_interested") or "Consulting",
                "total_activities": 0,
                "calls_count": 0,
                "calls_incoming": 0,
                "calls_outgoing": 0,
                "talk_time_seconds": 0,
                "whatsapp_count": 0,
                "whatsapp_sent": 0,
                "whatsapp_received": 0,
                "whatsapp_failed_count": 0,
                "whatsapp_pending_count": 0,
                "emails_count": 0,
                "emails_sent": 0,
                "emails_received": 0,
                "followups_count": 0,
                "status_changes_count": 0,
                "notes_count": 0,
                "client_views_count": 0,
                "active_time_seconds": 0,
                "active_time_display": "0s",
                "is_actively_viewing": False,
                "last_activity_at": iso_str,
                "last_activity_display": pretty_ts,
                "last_activity_relative": rel_time,
                "activities": []
            }

        c_entry = clients_map[client_key]
        c_entry["total_activities"] += 1
        c_entry["activities"].append(cleaned_event)

        if act_type in ["client_view", "client_profile_view"] or (client_name != "Direct Activity / CRM" and (act_type == "page_visit" or dur_sec or sess_state)):
            c_entry["client_views_count"] = c_entry.get("client_views_count", 0) + 1
            if dur_sec:
                c_entry["active_time_seconds"] = c_entry.get("active_time_seconds", 0) + dur_sec
                c_entry["active_time_display"] = format_duration(c_entry["active_time_seconds"])
            if sess_state == "active":
                c_entry["is_actively_viewing"] = True
        elif act_type in ["call", "phone_call", "telephony_call"]:
            c_entry["calls_count"] += 1
            if direction == "incoming":
                c_entry["calls_incoming"] += 1
            else:
                c_entry["calls_outgoing"] += 1
            if dur_sec:
                c_entry["talk_time_seconds"] += dur_sec
        elif act_type == "whatsapp":
            c_entry["whatsapp_count"] += 1
            if direction == "received":
                c_entry["whatsapp_received"] += 1
            else:
                c_entry["whatsapp_sent"] += 1
            w_st = (msg_status or "").lower()
            if w_st == "failed":
                c_entry["whatsapp_failed_count"] = c_entry.get("whatsapp_failed_count", 0) + 1
            elif w_st in ["pending", "pending_confirmation"]:
                c_entry["whatsapp_pending_count"] = c_entry.get("whatsapp_pending_count", 0) + 1
        elif act_type == "email":
            c_entry["emails_count"] += 1
            if direction == "received":
                c_entry["emails_received"] += 1
            else:
                c_entry["emails_sent"] += 1
        elif act_type in ["follow_up", "follow_up_created", "follow_up_completed", "follow_up_rescheduled"]:
            c_entry["followups_count"] += 1
        elif act_type in ["status_change", "stage_change"]:
            c_entry["status_changes_count"] += 1
        elif act_type in ["note", "note_added"]:
            c_entry["notes_count"] += 1

        # ─── 2. TODAY & YESTERDAY BREAKDOWNS ───
        target_bucket = None
        if event_date_ist == today_str:
            target_bucket = today_stats
        elif event_date_ist == yesterday_str:
            target_bucket = yesterday_stats

        if target_bucket is not None:
            target_bucket["total_activities"] += 1
            target_bucket["clients_interacted"].add(client_key)
            if act_type in ["call", "phone_call", "telephony_call"]:
                target_bucket["calls_total"] += 1
                if direction == "incoming":
                    target_bucket["calls_incoming"] += 1
                else:
                    target_bucket["calls_outgoing"] += 1
                if dur_sec:
                    target_bucket["talk_time_seconds"] += dur_sec
            elif act_type == "whatsapp":
                target_bucket["whatsapp_total"] += 1
                if direction == "received":
                    target_bucket["whatsapp_received"] += 1
                else:
                    target_bucket["whatsapp_sent"] += 1
            elif act_type == "email":
                target_bucket["emails_total"] += 1
                if direction == "received":
                    target_bucket["emails_received"] += 1
                else:
                    target_bucket["emails_sent"] += 1
            elif act_type in ["follow_up", "follow_up_created", "follow_up_completed", "follow_up_rescheduled"]:
                target_bucket["followups_total"] += 1
            elif act_type in ["status_change", "stage_change"]:
                target_bucket["status_changes_total"] += 1
            elif act_type in ["note", "note_added"]:
                target_bucket["notes_total"] += 1

        # ─── 3. DATE-WISE HISTORY AGGREGATION ───
        if event_date_ist not in date_wise_map:
            date_dt = _to_local_tz(dt)
            date_wise_map[event_date_ist] = {
                "date": event_date_ist,
                "date_display": date_dt.strftime("%b %d, %Y"),
                "day_name": date_dt.strftime("%A"),
                "is_today": event_date_ist == today_str,
                "is_yesterday": event_date_ist == yesterday_str,
                "total_activities": 0,
                "calls_total": 0,
                "calls_incoming": 0,
                "calls_outgoing": 0,
                "talk_time_seconds": 0,
                "talk_time_display": "0s",
                "emails_total": 0,
                "emails_sent": 0,
                "emails_received": 0,
                "whatsapp_total": 0,
                "whatsapp_sent": 0,
                "whatsapp_received": 0,
                "followups_total": 0,
                "status_changes_total": 0,
                "notes_total": 0,
                "clients_count": 0,
                "clients_interacted": set(),
                "activities": []
            }

        d_entry = date_wise_map[event_date_ist]
        d_entry["total_activities"] += 1
        d_entry["clients_interacted"].add(client_key)
        d_entry["activities"].append(cleaned_event)

        if act_type in ["call", "phone_call", "telephony_call"]:
            d_entry["calls_total"] += 1
            if direction == "incoming":
                d_entry["calls_incoming"] += 1
            else:
                d_entry["calls_outgoing"] += 1
            if dur_sec:
                d_entry["talk_time_seconds"] += dur_sec
        elif act_type == "whatsapp":
            d_entry["whatsapp_total"] += 1
            if direction == "received":
                d_entry["whatsapp_received"] += 1
            else:
                d_entry["whatsapp_sent"] += 1
        elif act_type == "email":
            d_entry["emails_total"] += 1
            if direction == "received":
                d_entry["emails_received"] += 1
            else:
                d_entry["emails_sent"] += 1
        elif act_type in ["follow_up", "follow_up_created", "follow_up_completed", "follow_up_rescheduled"]:
            d_entry["followups_total"] += 1
        elif act_type in ["status_change", "stage_change"]:
            d_entry["status_changes_total"] += 1
        elif act_type in ["note", "note_added"]:
            d_entry["notes_total"] += 1

    # Format talk time on all clients
    clients_list = list(clients_map.values())
    for c in clients_list:
        c["talk_time_display"] = format_duration(c["talk_time_seconds"]) or "0s"

    # Sort clients: REAL clients first by total activities / calls, Direct Activity / CRM always LAST
    def client_sort_key(c_item):
        is_direct = 1 if c_item.get("client_name") == "Direct Activity / CRM" else 0
        return (is_direct, -c_item.get("total_activities", 0), -c_item.get("calls_count", 0))

    clients_list.sort(key=client_sort_key)

    # Format Date-Wise History list sorted newest to oldest date
    date_wise_history = []
    for d_key in sorted(date_wise_map.keys(), reverse=True):
        d_val = date_wise_map[d_key]
        d_val["clients_count"] = len(d_val["clients_interacted"])
        d_val.pop("clients_interacted", None)
        d_val["talk_time_display"] = format_duration(d_val["talk_time_seconds"]) or "0s"
        date_wise_history.append(d_val)

    # Format today and yesterday summaries
    today_stats["clients_count"] = len(today_stats["clients_interacted"])
    today_stats.pop("clients_interacted", None)
    today_stats["talk_time_display"] = format_duration(today_stats["talk_time_seconds"]) or "0s"

    yesterday_stats["clients_count"] = len(yesterday_stats["clients_interacted"])
    yesterday_stats.pop("clients_interacted", None)
    yesterday_stats["talk_time_display"] = format_duration(yesterday_stats["talk_time_seconds"]) or "0s"

    # Rep summary totals
    total_talk = sum(c["talk_time_seconds"] for c in clients_list)
    # Strictly find the most recent PAST activity for salesperson's last active (never in future)
    past_timeline = [item for item in timeline if _normalize_dt(item.get("timestamp")) <= now_utc]
    most_recent_rep_dt = past_timeline[0]["timestamp"] if past_timeline else (timeline[0]["timestamp"] if timeline else None)
    
    most_recent_dt_obj = _normalize_dt(most_recent_rep_dt) if most_recent_rep_dt else None
    if most_recent_dt_obj and most_recent_dt_obj > now_utc:
        most_recent_dt_obj = now_utc
        most_recent_rep_dt = now_utc.isoformat()

    rep_active_status = _get_active_status(most_recent_dt_obj)

    rep_summary = {
        "salesperson_id": salesperson_id,
        "salesperson_name": salesperson_name,
        "salesperson_email": salesperson_email,
        "salesperson_role": salesperson_role,
        "total_activities": len(timeline),
        "total_clients_interacted": len(clients_list),
        "total_calls": sum(c["calls_count"] for c in clients_list),
        "calls_incoming": sum(c.get("calls_incoming", 0) for c in clients_list),
        "calls_outgoing": sum(c.get("calls_outgoing", 0) for c in clients_list),
        "total_talk_time_seconds": total_talk,
        "total_talk_time_display": format_duration(total_talk) or "0s",
        "total_whatsapp": sum(c["whatsapp_count"] for c in clients_list),
        "whatsapp_sent": sum(c.get("whatsapp_sent", 0) for c in clients_list),
        "whatsapp_received": sum(c.get("whatsapp_received", 0) for c in clients_list),
        "total_emails": sum(c["emails_count"] for c in clients_list),
        "emails_sent": sum(c.get("emails_sent", 0) for c in clients_list),
        "emails_received": sum(c.get("emails_received", 0) for c in clients_list),
        "total_followups": sum(c["followups_count"] for c in clients_list),
        "total_status_changes": sum(c["status_changes_count"] for c in clients_list),
        "total_notes": sum(c["notes_count"] for c in clients_list),
        "today": today_stats,
        "yesterday": yesterday_stats,
        "last_active_at": most_recent_rep_dt,
        "last_active_display": rep_active_status["display"],
        "last_active_relative": rep_active_status["relative"],
        "active_badge": rep_active_status["badge"],
        "is_active_now": rep_active_status["is_active_now"],
        "is_active_today": rep_active_status["is_active_today"]
    }

    return {
        "success": True,
        "salesperson": {
            "id": salesperson_id,
            "name": salesperson_name,
            "email": salesperson_email,
            "role": salesperson_role,
            "role_label": salesperson_role.replace("_", " ").title(),
            "active_badge": rep_active_status["badge"],
            "is_active_now": rep_active_status["is_active_now"],
            "is_active_today": rep_active_status["is_active_today"],
            "last_active_relative": rep_active_status["relative"],
            "last_active_display": rep_active_status["display"],
            "last_active_raw": most_recent_rep_dt
        },
        "summary": rep_summary,
        "today": today_stats,
        "yesterday": yesterday_stats,
        "date_wise_history": date_wise_history,
        "clients": clients_list,
        "timeline": timeline,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


