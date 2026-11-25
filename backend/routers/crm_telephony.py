"""
LEAMSS CRM Telephony Router - Callyzer Enterprise Integration
Company-wide call tracking & recording synchronization for all salespersons,
leads, and clients with zero duplicate employee creation.

Architecture:
- Single Company Callyzer API Token & Centralized Webhook for all employees.
- Automatic Salesperson Identification via Mobile Number / Callyzer Number.
- Dynamic Client/Lead Resolution across Leads, Pre-assessments, Cases & Clients.
- MongoDB Deduplication using Callyzer Call ID (Upsert).
- Comprehensive Call History & KPI Analytics for Leads & Salespersons.
"""

import os
import re
import uuid
import httpx
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Union
from fastapi import APIRouter, HTTPException, Depends, Query, Body, Header, Request
from core.database import db
from core.auth import get_current_user
from core.services import log_activity

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/crm/telephony", tags=["CRM Telephony & Callyzer"])


crm_calls_col = db["crm_calls"]
leads_col = db["leads"]
pre_assessments_col = db["pre_assessments"]
cases_col = db["cases"]
users_col = db["users"]
audit_logs_col = db["audit_logs"]
crm_settings_col = db["crm_settings"]


def _is_admin(user: dict) -> bool:
    role = str(user.get("role") or "").strip().lower()
    rbac = str(user.get("rbac_role") or "").strip().lower()
    return role in ["admin", "admin_owner", "super_admin"] or rbac in ["admin", "admin_owner", "super_admin"]


def _is_manager_or_admin(user: dict) -> bool:
    role = str(user.get("role") or "").strip().lower()
    rbac = str(user.get("rbac_role") or "").strip().lower()
    return role in ["admin", "admin_owner", "super_admin", "sales_manager", "sales_head"] or rbac in ["admin_owner", "sales_manager", "sales_head", "admin", "super_admin"]



# ────────────────────────────────────────────────────────────
# 1. PHONE NORMALIZATION & SMART MATCHING HELPERS
# ────────────────────────────────────────────────────────────

def normalize_phone_number(phone: Optional[str]) -> str:
    """
    Normalizes phone numbers to standard 10-digit format for matching.
    Strips spaces, hyphens, parentheses, +91, 91, leading 0, or double country codes.
    Example: '+91 98765-43210' -> '9876543210'
    """
    if not phone:
        return ""
    digits = re.sub(r"\D", "", str(phone))
    if len(digits) >= 10:
        return digits[-10:]
    return digits


def make_phone_regex(raw_phone: Optional[str]) -> Optional[re.Pattern]:
    """
    Generates a regex that matches the 10-digit sequence regardless of
    spaces, dashes, parentheses, +91 prefix, or leading 0 in the database field.
    """
    digits = normalize_phone_number(raw_phone)
    if not digits or len(digits) < 6:
        return None
    pattern_str = r"\D*".join(re.escape(d) for d in digits) + r"\D*$"
    return re.compile(pattern_str)


async def find_salesperson_by_phone(employee_number: str) -> Optional[dict]:
    """
    Finds existing salesperson in users collection by normalized phone number,
    mobile, or dedicated callyzer_number.
    DOES NOT create any new user record (prevents duplicates).
    """
    pattern = make_phone_regex(employee_number)
    if not pattern:
        return None

    user = await users_col.find_one(
        {
            "$or": [
                {"mobile": pattern},
                {"phone": pattern},
                {"callyzer_number": pattern}
            ]
        },
        {"_id": 0, "id": 1, "name": 1, "email": 1, "phone": 1, "mobile": 1, "role": 1, "rbac_role": 1, "employee_id": 1}
    )
    return user


async def find_lead_or_client_by_phone(client_number: str) -> Optional[dict]:
    """
    Finds lead, pre-assessment, case, or registered client by phone number.
    Returns matched entity metadata.
    """
    pattern = make_phone_regex(client_number)
    if not pattern:
        return None

    # 1. Check Leads collection
    lead = await leads_col.find_one(
        {
            "$or": [
                {"phone": pattern},
                {"mobile": pattern},
                {"whatsapp": pattern}
            ]
        },
        {"_id": 0, "id": 1, "name": 1, "phone": 1, "assigned_to": 1, "assigned_to_name": 1, "stage": 1, "status": 1}
    )
    if lead:
        return {
            "entity_type": "lead",
            "id": lead.get("id"),
            "lead_id": lead.get("id"),
            "name": lead.get("name", "Lead"),
            "phone": lead.get("phone") or client_number,
            "assigned_to": lead.get("assigned_to"),
            "assigned_to_name": lead.get("assigned_to_name")
        }

    # 2. Check Pre-Assessments collection
    pa = await pre_assessments_col.find_one(
        {
            "$or": [
                {"client_mobile": pattern},
                {"spouse_info.mobile": pattern}
            ]
        },
        {"_id": 0, "id": 1, "client_name": 1, "client_mobile": 1, "partner_id": 1, "partner_name": 1}
    )
    if pa:
        return {
            "entity_type": "pre_assessment",
            "id": pa.get("id"),
            "pa_id": pa.get("id"),
            "name": pa.get("client_name", "Client"),
            "phone": pa.get("client_mobile") or client_number,
            "assigned_to": pa.get("partner_id"),
            "assigned_to_name": pa.get("partner_name")
        }

    # 3. Check Cases collection
    case = await cases_col.find_one(
        {
            "$or": [
                {"client_phone": pattern},
                {"client_mobile": pattern}
            ]
        },
        {"_id": 0, "id": 1, "case_id": 1, "client_name": 1, "client_phone": 1, "case_manager_id": 1, "case_manager_name": 1}
    )
    if case:
        return {
            "entity_type": "case",
            "id": case.get("id"),
            "case_id": case.get("case_id"),
            "name": case.get("client_name", "Client"),
            "phone": case.get("client_phone") or client_number,
            "assigned_to": case.get("case_manager_id"),
            "assigned_to_name": case.get("case_manager_name")
        }

    # 4. Check Registered Client Users
    client = await users_col.find_one(
        {
            "role": "client",
            "$or": [
                {"mobile": pattern},
                {"phone": pattern}
            ]
        },
        {"_id": 0, "id": 1, "name": 1, "phone": 1, "mobile": 1}
    )
    if client:
        return {
            "entity_type": "client",
            "id": client.get("id"),
            "client_id": client.get("id"),
            "name": client.get("name", "Client"),
            "phone": client.get("mobile") or client.get("phone") or client_number
        }

    return None


# ────────────────────────────────────────────────────────────
# 2. CALLYZER REAL-TIME WEBHOOK INGESTION (COMPANY-WIDE)
# ────────────────────────────────────────────────────────────

@router.post("/callyzer/webhook")
async def callyzer_webhook(
    request: Request = None,
    payload: Union[List[Dict[str, Any]], Dict[str, Any]] = Body(...)
):
    """
    Receives real-time call logs & audio recording URLs from Callyzer.
    Handles single employee log objects, list of employee batches, or array of call logs.
    Automatically matches salesperson and client/lead, preventing duplicate calls.
    """
    raw_batches = payload if isinstance(payload, list) else [payload]
    processed_count = 0
    created_calls = []

    for batch in raw_batches:
        # Batch might be an employee wrapper (logs or call_logs) or a direct log entry
        emp_logs = batch.get("logs") or batch.get("call_logs")
        if emp_logs is not None and isinstance(emp_logs, list):
            employee_name = batch.get("emp_name") or batch.get("employeeName") or batch.get("employee_name") or ""
            employee_number = str(batch.get("emp_number") or batch.get("employeeNumber") or batch.get("employee_number") or "")
            logs = emp_logs
        else:
            # Direct single log object
            employee_name = batch.get("emp_name") or batch.get("employeeName") or batch.get("employee_name") or ""
            employee_number = str(batch.get("emp_number") or batch.get("employeeNumber") or batch.get("employee_number") or "")
            logs = [batch]

        # 1. Resolve Salesperson automatically (no duplicate user creation)
        salesperson = await find_salesperson_by_phone(employee_number)
        sales_person_id = salesperson.get("id") if salesperson else None
        sales_person_name = salesperson.get("name") if salesperson else (employee_name or f"Staff ({employee_number})")

        for log_entry in logs:
            callyzer_id = str(
                log_entry.get("id")
                or log_entry.get("call_id")
                or log_entry.get("callId")
                or log_entry.get("callyzer_call_id")
                or uuid.uuid4()
            )
            client_number = str(
                log_entry.get("client_number")
                or log_entry.get("number")
                or log_entry.get("clientNumber")
                or log_entry.get("phone")
                or ""
            ).strip()
            client_name = (
                log_entry.get("client_name")
                or log_entry.get("name")
                or log_entry.get("clientName")
                or "Client"
            )
            duration = int(
                log_entry.get("call_duration")
                or log_entry.get("duration")
                or log_entry.get("callDuration")
                or 0
            )
            raw_call_type = str(
                log_entry.get("call_type")
                or log_entry.get("callType")
                or log_entry.get("type")
                or "Outgoing"
            ).strip()
            call_time_str = (
                log_entry.get("call_time")
                or log_entry.get("callTime")
                or log_entry.get("createdDate")
                or log_entry.get("created_date")
            )
            recording_url = (
                log_entry.get("recording_url")
                or log_entry.get("recordingURL")
                or log_entry.get("recordingUrl")
                or log_entry.get("call_recording")
                or log_entry.get("call_recording_url")
                or log_entry.get("audio_url")
                or log_entry.get("audio_file")
                or log_entry.get("recording")
                or log_entry.get("media_url")
                or ""
            )
            note = log_entry.get("note") or log_entry.get("notes") or ""

            # Normalize direction
            lower_type = raw_call_type.lower()
            if "incoming" in lower_type or "missed" in lower_type or "rejected" in lower_type:
                direction = "incoming"
            else:
                direction = "outgoing"

            # Normalize status
            if "missed" in lower_type or "never" in lower_type:
                status = "missed"
            elif "rejected" in lower_type:
                status = "rejected"
            elif duration > 0:
                status = "connected"
            else:
                status = "not_connected"

            # Parse timestamp
            call_time = datetime.now(timezone.utc)
            if call_time_str:
                for fmt in [
                    "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%d, %H:%M:%S",
                    "%Y-%m-%dT%H:%M:%S",
                    "%Y-%m-%dT%H:%M:%SZ",
                    "%d-%m-%Y %H:%M:%S"
                ]:
                    try:
                        call_time = datetime.strptime(str(call_time_str).strip(), fmt).replace(tzinfo=timezone.utc)
                        break
                    except Exception:
                        pass

            # 2. Resolve Client / Lead dynamically
            matched_entity = await find_lead_or_client_by_phone(client_number)
            lead_id = None
            client_id = None
            case_id = None
            pa_id = None
            resolved_client_name = client_name

            if matched_entity:
                lead_id = matched_entity.get("lead_id")
                client_id = matched_entity.get("client_id")
                case_id = matched_entity.get("case_id")
                pa_id = matched_entity.get("pa_id")
                resolved_client_name = matched_entity.get("name") or client_name

            # 3. Check for existing log with same callyzer_call_id to guarantee deduplication
            existing_call = await crm_calls_col.find_one({
                "$or": [
                    {"callyzer_call_id": callyzer_id},
                    {"callyzer_log_id": callyzer_id}
                ]
            })

            call_doc = {
                "id": existing_call["id"] if existing_call else str(uuid.uuid4()),
                "callyzer_call_id": callyzer_id,
                "callyzer_log_id": callyzer_id,
                "provider": "callyzer",
                "lead_id": lead_id,
                "client_id": client_id,
                "case_id": case_id,
                "pa_id": pa_id,
                "lead_name": resolved_client_name,
                "client_name": resolved_client_name,
                "lead_phone": client_number,
                "client_phone": client_number,
                "sales_person_id": sales_person_id,
                "sales_person_name": sales_person_name,
                "sales_person_phone": employee_number,
                "direction": direction,
                "call_type": raw_call_type,
                "raw_call_type": raw_call_type,
                "duration_seconds": duration,
                "status": status,
                "outcome": "connected" if status == "connected" else status,
                "notes": note or f"{direction.title()} Call logged via Callyzer SIM tracker",
                "recording_url": recording_url,
                "call_time": call_time.isoformat(),
                "created_at": call_time,
                "updated_at": datetime.now(timezone.utc)
            }

            if existing_call:
                # Update existing record (e.g. recording URL or duration updated)
                await crm_calls_col.update_one(
                    {"id": existing_call["id"]},
                    {"$set": call_doc}
                )
            else:
                await crm_calls_col.insert_one(call_doc)

            # Automatically process structured AI summary & genuine transcription status
            try:
                from core.call_intelligence_service import process_call_intelligence
                await process_call_intelligence(call_doc["id"])
            except Exception as e:
                logger.warning(f"Callyzer auto call intelligence processing skipped: {e}")

            # 4. Update lead metrics & contact timestamps
            if lead_id:
                update_fields = {"last_contacted_at": datetime.now(timezone.utc)}
                if status == "connected":
                    update_fields["last_connected_at"] = datetime.now(timezone.utc)
                await leads_col.update_one(
                    {"id": lead_id},
                    {"$set": update_fields, "$inc": {"call_count": 1}}
                )

                mins = duration // 60
                secs = duration % 60
                dur_str = f"{mins:02d}:{secs:02d}"
                rec_badge = " [Recording Attached]" if recording_url else ""
                await log_activity(
                    user_id=sales_person_id or "system",
                    user_name=sales_person_name,
                    action="callyzer_call_synced",
                    entity_type="lead",
                    entity_id=lead_id,
                    details=f"{direction.title()} Call via SIM ({status}) - Duration: {dur_str}. Caller: {employee_number} -> {client_number}{rec_badge}"
                )

            processed_count += 1
            created_calls.append(call_doc["id"])

    return {
        "success": True,
        "processed_count": processed_count,
        "call_ids": created_calls
    }


# ────────────────────────────────────────────────────────────
# 3. CALL HISTORY & PROFILE QUERY ENDPOINTS
# ────────────────────────────────────────────────────────────

@router.get("/calls/lead/{lead_id}")
async def get_lead_call_history(
    lead_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Retrieve all call history and recording links for a specific lead."""
    # Find lead to get phone number for fuzzy phone match
    lead = await leads_col.find_one({"id": lead_id}, {"_id": 0, "phone": 1, "mobile": 1, "whatsapp": 1})
    lead_phones = []
    if lead:
        for k in ["phone", "mobile", "whatsapp"]:
            val = lead.get(k)
            if val:
                norm = normalize_phone_number(val)
                if norm:
                    lead_phones.append(norm)

    query = {
        "$or": [
            {"lead_id": lead_id}
        ]
    }
    for p in lead_phones:
        pat = make_phone_regex(p)
        if pat:
            query["$or"].append({"lead_phone": pat})
            query["$or"].append({"client_phone": pat})

    calls = await crm_calls_col.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
    return {
        "success": True,
        "lead_id": lead_id,
        "total_calls": len(calls),
        "calls": calls
    }


@router.get("/calls/client/{phone}")
async def get_client_call_history(
    phone: str,
    current_user: dict = Depends(get_current_user)
):
    """Retrieve call history for any client phone number across all records."""
    pat = make_phone_regex(phone)
    if not pat:
        return {"success": True, "phone": phone, "total_calls": 0, "calls": []}

    calls = await crm_calls_col.find(
        {
            "$or": [
                {"lead_phone": pat},
                {"client_phone": pat}
            ]
        },
        {"_id": 0}
    ).sort("created_at", -1).to_list(200)

    return {
        "success": True,
        "phone": phone,
        "total_calls": len(calls),
        "calls": calls
    }


@router.get("/calls/salesperson/{user_id}")
async def get_salesperson_call_history(
    user_id: str,
    limit: int = Query(100, ge=1, le=500),
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieve call history, recordings, and aggregated performance KPIs
    for a specific salesperson/employee profile.
    """
    # RBAC Enforcement: Salespersons can only view their own calls unless Admin/Manager
    if not _is_manager_or_admin(current_user) and user_id != current_user.get("id"):
        raise HTTPException(status_code=403, detail="Access denied: salespersons can only view their own calls")

    user = await users_col.find_one({"id": user_id}, {"_id": 0, "id": 1, "name": 1, "phone": 1, "mobile": 1, "callyzer_number": 1})
    if not user:
        raise HTTPException(status_code=404, detail="Salesperson user not found")

    user_phones = []
    for k in ["mobile", "phone", "callyzer_number"]:
        val = user.get(k)
        if val:
            norm = normalize_phone_number(val)
            if norm:
                user_phones.append(norm)

    query = {
        "$or": [
            {"sales_person_id": user_id}
        ]
    }
    for p in user_phones:
        pat = make_phone_regex(p)
        if pat:
            query["$or"].append({"sales_person_phone": pat})

    calls = await crm_calls_col.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)

    # Compute KPIs
    total_calls = len(calls)
    total_duration = sum(c.get("duration_seconds", 0) for c in calls)
    connected_calls = sum(1 for c in calls if c.get("status") == "connected")
    missed_calls = sum(1 for c in calls if c.get("status") == "missed")
    incoming_calls = sum(1 for c in calls if c.get("direction") == "incoming")
    outgoing_calls = sum(1 for c in calls if c.get("direction") == "outgoing")
    recorded_calls = sum(1 for c in calls if bool(c.get("recording_url")))
    avg_duration = round(total_duration / connected_calls) if connected_calls > 0 else 0

    return {
        "success": True,
        "salesperson": {
            "id": user.get("id"),
            "name": user.get("name"),
            "mobile": user.get("mobile") or user.get("phone"),
            "callyzer_number": user.get("callyzer_number")
        },
        "kpis": {
            "total_calls": total_calls,
            "connected_calls": connected_calls,
            "missed_calls": missed_calls,
            "incoming_calls": incoming_calls,
            "outgoing_calls": outgoing_calls,
            "recorded_calls": recorded_calls,
            "total_duration_seconds": total_duration,
            "avg_duration_seconds": avg_duration
        },
        "calls": calls
    }


@router.get("/calls")
async def list_calls(
    sales_person_id: Optional[str] = Query(None),
    lead_id: Optional[str] = Query(None),
    phone: Optional[str] = Query(None),
    direction: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    skip: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user)
):
    """Filterable, paginated list of all call logs."""
    query: Dict[str, Any] = {}

    if sales_person_id:
        query["sales_person_id"] = sales_person_id
    if lead_id:
        lead_doc = await leads_col.find_one({"id": lead_id}, {"_id": 0, "phone": 1, "mobile": 1, "whatsapp": 1})
        or_clauses = [{"lead_id": lead_id}, {"client_id": lead_id}]
        if lead_doc:
            for fld in ["phone", "mobile", "whatsapp"]:
                val = lead_doc.get(fld)
                if val:
                    pat = make_phone_regex(str(val))
                    if pat:
                        or_clauses.append({"lead_phone": pat})
                        or_clauses.append({"client_phone": pat})
        query["$or"] = or_clauses
    if direction:
        query["direction"] = direction
    if status:
        query["status"] = status

    if phone:
        pat = make_phone_regex(phone)
        if pat:
            query["$or"] = [{"lead_phone": pat}, {"client_phone": pat}, {"sales_person_phone": pat}]

    if from_date or to_date:
        date_q = {}
        if from_date:
            try:
                date_q["$gte"] = datetime.strptime(from_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except Exception:
                pass
        if to_date:
            try:
                date_q["$lte"] = datetime.strptime(to_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
            except Exception:
                pass
        if date_q:
            query["created_at"] = date_q

    # RBAC Enforcement: Non-admin sales reps only see their assigned leads or own calls
    if not _is_admin(current_user):
        uid = str(current_user.get("id") or "").strip()
        uemail = str(current_user.get("email") or "").strip().lower()
        uname = str(current_user.get("name") or "").strip()
        lead_assign_criteria = []
        if uid:
            lead_assign_criteria.extend([
                {"assigned_to": uid},
                {"assigned_sales_rep_id": uid},
                {"sales_person_id": uid},
                {"block_assigned_to": uid},
                {"created_by": uid}
            ])
        if uemail:
            lead_assign_criteria.extend([
                {"assigned_to": uemail},
                {"assigned_to_email": uemail}
            ])
        if uname:
            lead_assign_criteria.append({"assigned_to_name": uname})
            lead_assign_criteria.append({"assigned_to_name": {"$regex": f"^{re.escape(uname)}$", "$options": "i"}})

        assigned_leads = await leads_col.find(
            {"$or": lead_assign_criteria},
            {"id": 1}
        ).to_list(1000)
        assigned_lead_ids = [l["id"] for l in assigned_leads if l.get("id")]

        call_scope = [{"sales_person_id": uid}]
        if assigned_lead_ids:
            call_scope.append({"lead_id": {"$in": assigned_lead_ids}})

        if "$and" in query:
            query["$and"].append({"$or": call_scope})
        elif query:
            query = {"$and": [query, {"$or": call_scope}]}
        else:
            query = {"$or": call_scope}

    total = await crm_calls_col.count_documents(query)
    calls = await crm_calls_col.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)

    return {
        "success": True,
        "total": total,
        "limit": limit,
        "skip": skip,
        "calls": calls
    }


# ────────────────────────────────────────────────────────────
# 4. COMPANY CALLYZER SETTINGS & MANUAL SYNC
# ────────────────────────────────────────────────────────────

@router.get("/callyzer/settings")
async def get_callyzer_settings(current_user: dict = Depends(get_current_user)):
    """Retrieve Callyzer integration status and all automatically mapped salespersons."""
    settings = await crm_settings_col.find_one({"key": "callyzer_config"}, {"_id": 0}) or {}
    api_key = settings.get("api_key") or os.getenv("CALLYZER_API_KEY", "")
    masked_key = f"{api_key[:6]}...{api_key[-4:]}" if len(api_key) > 10 else ("Configured" if api_key else "Not Set")

    # Get list of sales reps with phone numbers
    sales_reps = await users_col.find(
        {"role": {"$in": ["sales_executive", "sr_sales_executive", "partner", "sales_manager", "admin", "case_manager"]}},
        {"_id": 0, "id": 1, "name": 1, "email": 1, "phone": 1, "mobile": 1, "callyzer_number": 1, "role": 1, "employee_id": 1}
    ).to_list(200)

    # Attach synced call count per sales rep
    for rep in sales_reps:
        rep_phones = [p for p in [rep.get("mobile"), rep.get("phone"), rep.get("callyzer_number")] if p]
        count = await crm_calls_col.count_documents({"sales_person_id": rep["id"]})
        rep["synced_call_count"] = count

    total_calls = await crm_calls_col.count_documents({"provider": "callyzer"})
    latest_call = await crm_calls_col.find_one({"provider": "callyzer"}, {"_id": 0, "call_time": 1, "created_at": 1}, sort=[("created_at", -1)])

    return {
        "status": "connected" if api_key else "pending_key",
        "api_key_masked": masked_key,
        "webhook_url": "/api/crm/telephony/callyzer/webhook",
        "total_callyzer_calls_synced": total_calls,
        "last_sync_time": latest_call.get("created_at") if latest_call else None,
        "sales_reps_count": len(sales_reps),
        "sales_reps": sales_reps
    }


@router.post("/callyzer/settings")
async def update_callyzer_settings(
    data: dict = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """Save Callyzer API Key & settings (Admin only)."""
    if current_user.get("role") not in ["admin", "admin_owner", "sales_manager"]:
        raise HTTPException(status_code=403, detail="Only Admins can update Telephony Settings")

    api_key = data.get("api_key", "").strip()
    webhook_secret = data.get("webhook_secret", "").strip()

    await crm_settings_col.update_one(
        {"key": "callyzer_config"},
        {
            "$set": {
                "key": "callyzer_config",
                "api_key": api_key,
                "webhook_secret": webhook_secret,
                "updated_at": datetime.now(timezone.utc),
                "updated_by": current_user.get("name", "Admin")
            }
        },
        upsert=True
    )

    return {"success": True, "message": "Callyzer settings updated successfully"}


@router.post("/callyzer/sync")
async def sync_callyzer_calls(
    from_date: Optional[str] = Query(None, description="Format: YYYY-MM-DD"),
    to_date: Optional[str] = Query(None, description="Format: YYYY-MM-DD"),
    current_user: dict = Depends(get_current_user)
):
    """
    Manually pull historical call logs from Callyzer REST API using company API key.
    """
    settings = await crm_settings_col.find_one({"key": "callyzer_config"}) or {}
    api_key = settings.get("api_key") or os.getenv("CALLYZER_API_KEY")

    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="Callyzer API Key is not configured. Please save your API Key in CRM Settings or .env file."
        )

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    start_date = from_date or today_str
    end_date = to_date or today_str

    base_url = (os.getenv("CALLYZER_BASE_URL") or "https://sandbox.api.callyzer.co/api/v2.1").rstrip("/")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    params = {
        "from_date": start_date,
        "to_date": end_date
    }

    try:
        async with httpx.AsyncClient(timeout=35.0) as client:
            # Try /call-log/history first
            url = f"{base_url}/call-log/history"
            resp = await client.get(url, headers=headers, params=params)
            
            # Fallback to /call-logs if needed
            if resp.status_code == 404:
                url = f"{base_url}/call-logs"
                resp = await client.get(url, headers=headers, params=params)

            if resp.status_code != 200:
                return {
                    "success": False,
                    "status_code": resp.status_code,
                    "error": resp.text,
                    "message": "Failed to fetch logs from Callyzer API. Check API key and date range."
                }
            data = resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Callyzer API connection error: {str(e)}")

    # Ingest the returned logs
    sync_result = await callyzer_webhook(None, data)
    return {
        "success": True,
        "message": f"Successfully synced call logs from Callyzer for {start_date} to {end_date}",
        "details": sync_result
    }
