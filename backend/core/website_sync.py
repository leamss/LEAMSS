"""Website Lead Synchronization Engine.

Maps registrations from https://leamss.com/navratri-offers (MySQL database `hosldwuh_staging`,
table `navratri_registrations`) and live Webhooks into the CRM MongoDB `leads` collection.
Preserves full data integrity and allows bi-directional sync without affecting any existing features.
"""
from __future__ import annotations

import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from core.database import db

logger = logging.getLogger("website_sync")
leads_col = db["leads"]

MYSQL_HOST = os.environ.get("WEBSITE_MYSQL_HOST", os.environ.get("MYSQL_HOST", "127.0.0.1"))
MYSQL_PORT = int(os.environ.get("WEBSITE_MYSQL_PORT", os.environ.get("MYSQL_PORT", "3306")))
MYSQL_USER = os.environ.get("WEBSITE_MYSQL_USER", os.environ.get("MYSQL_USER", "hosldwuh_staging"))
MYSQL_PASSWORD = os.environ.get("WEBSITE_MYSQL_PASSWORD", os.environ.get("MYSQL_PASSWORD", ""))
MYSQL_DB = os.environ.get("WEBSITE_MYSQL_DB", os.environ.get("MYSQL_DB", "hosldwuh_staging"))


def _parse_dt(val: Any) -> Optional[datetime]:
    if not val:
        return None
    if isinstance(val, datetime):
        if val.tzinfo is None:
            return val.replace(tzinfo=timezone.utc)
        return val
    if isinstance(val, str):
        try:
            # support formats like '2026-09-10 11:21:29' or ISO strings
            clean = val.replace("Z", "+00:00")
            if " " in clean and "T" not in clean:
                return datetime.strptime(clean, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            return datetime.fromisoformat(clean)
        except Exception:
            return None
    return None


def map_navratri_row_to_lead(row: Dict[str, Any]) -> Dict[str, Any]:
    """Transforms a raw MySQL row or Webhook JSON payload into a CRM Lead record."""
    full_name = (row.get("full_name") or row.get("fullName") or row.get("name") or "").strip()
    email = (row.get("email") or "").strip().lower()
    
    # Clean mobile number
    mobile = row.get("mobile_full") or row.get("mobile") or row.get("phone") or ""
    mobile_num = row.get("mobile_number") or ""
    country_code = row.get("country_code") or "91"
    if not mobile and mobile_num:
        mobile = f"+{country_code}{mobile_num}" if not str(mobile_num).startswith("+") else str(mobile_num)
    
    # Unique ID from website
    unique_id = (row.get("unique_id") or row.get("id") or "").strip()
    if isinstance(unique_id, int):
        unique_id = f"NN2427{unique_id}"

    # Payment details
    payment_status = (row.get("payment_status") or "pending").strip().lower()
    payment_amount = row.get("payment_amount")
    try:
        payment_amount_float = float(payment_amount) if payment_amount is not None else None
    except (ValueError, TypeError):
        payment_amount_float = None

    payment_mode = row.get("payment_mode")
    razorpay_payment_id = row.get("razorpay_payment_id")
    razorpay_order_id = row.get("razorpay_order_id")
    paid_at = _parse_dt(row.get("paid_at"))
    
    created_at = _parse_dt(row.get("created_at")) or datetime.now(timezone.utc)
    updated_at = _parse_dt(row.get("updated_at")) or datetime.now(timezone.utc)

    # CRM Stage based on payment
    if payment_status == "success":
        stage = "payment_done"
        priority = "high"
    elif payment_status == "failed":
        stage = "not_connected"
        priority = "medium"
    else:
        stage = "new"
        priority = "medium"

    # Resume URL formation
    resume_path = row.get("resume_link") or row.get("resume_url") or row.get("resume_path") or row.get("resumePath") or ""
    resume_url = ""
    if resume_path:
        if resume_path.startswith("http://") or resume_path.startswith("https://"):
            resume_url = resume_path
        else:
            clean_path = resume_path.lstrip("/")
            resume_url = f"https://leamss.com/{clean_path}"

    marital_status = row.get("marital_status") or row.get("marital") or ""

    tags = ["Navratri Offer 2026", "Website Registration"]
    if payment_status == "success":
        tags.append("Payment Success")
    elif payment_status == "failed":
        tags.append("Payment Failed")

    lead_doc = {
        "unique_id": unique_id,
        "external_id": str(row.get("id") or unique_id),
        "name": full_name or row.get("name") or "Website Lead",
        "email": email,
        "phone": str(mobile),
        "alternate_phone": row.get("alternate_phone", ""),
        "address": row.get("address", ""),
        "city": row.get("city", ""),
        "service_interested": row.get("service_interested") or "Navratri Special Offer",
        "country_of_interest": row.get("country_of_interest") or "AU",
        "message": row.get("message") or f"Registered for Navratri Offer. Experience: {row.get('experience', 'N/A')}, Qualification: {row.get('qualification', 'N/A')}",
        "source": row.get("source") or "Navratri Offer (leamss.com)",
        "subsource": row.get("subsource") or row.get("reference") or "Website Form",
        "utm_source": row.get("utm_source") or "website_navratri",
        "utm_medium": row.get("utm_medium") or "web_form",
        "utm_campaign": row.get("utm_campaign") or "navratri_offers_2026",
        "stage": row.get("stage") or stage,
        "priority": row.get("priority") or priority,
        "assigned_to": row.get("assigned_to"),
        "assigned_to_name": row.get("assigned_to_name") or "Unassigned",
        "date_of_birth": str(row.get("dob") or row.get("date_of_birth") or ""),
        "occupation": row.get("occupation") or "",
        "total_work_experience": str(row.get("experience") or row.get("total_work_experience") or ""),
        "latest_qualification": str(row.get("qualification") or row.get("latest_qualification") or ""),
        "gender": str(row.get("gender") or ""),
        "marital_status": str(marital_status),
        "resume_path": resume_path,
        "resume_url": resume_url,
        "sales_person_name": row.get("sales_person_name") or "",
        "reference": row.get("reference") or "",
        "payment_status": payment_status,
        "payment_mode": payment_mode,
        "payment_amount": payment_amount_float,
        "razorpay_payment_id": razorpay_payment_id,
        "razorpay_order_id": razorpay_order_id,
        "paid_at": paid_at.isoformat() if paid_at else None,
        "tags": tags,
        "created_at": created_at,
        "updated_at": updated_at,
        "last_contacted_at": None,
        "converted": False,
        "converted_sale_id": None
    }
    return lead_doc



async def upsert_website_lead(data: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    """Upsert a single website registration into the CRM MongoDB `leads` collection.
    
    Returns (lead_doc, is_new_boolean).
    """
    mapped = map_navratri_row_to_lead(data)
    email = mapped.get("email")
    unique_id = mapped.get("unique_id")
    phone = mapped.get("phone")

    # Match priority: 1) unique_id / external_id, 2) email, 3) phone
    existing = None
    if unique_id:
        existing = await leads_col.find_one({"$or": [{"unique_id": unique_id}, {"external_id": mapped.get("external_id")}]})
    
    if not existing and email:
        existing = await leads_col.find_one({"email": email})
        
    if not existing and phone and len(str(phone).strip()) >= 7:
        existing = await leads_col.find_one({"phone": str(phone).strip()})

    if existing:
        # Determine updated stage: if re-submitting or paying, bring to active leads
        current_stage = existing.get("stage")
        if mapped["payment_status"] == "success":
            new_stage = "payment_done"
            new_priority = "high"
        elif current_stage in ("converted", "not_interested", "closed") or not current_stage:
            new_stage = "new"
            new_priority = "medium"
        else:
            new_stage = current_stage
            new_priority = existing.get("priority") or "medium"

        # Update existing lead with latest payment / details without wiping sales notes/assignment
        update_fields = {
            "name": mapped["name"] or existing.get("name"),
            "email": mapped["email"] or existing.get("email"),
            "phone": mapped["phone"] or existing.get("phone"),
            "unique_id": mapped["unique_id"] or existing.get("unique_id"),
            "date_of_birth": mapped["date_of_birth"] or existing.get("date_of_birth"),
            "latest_qualification": mapped["latest_qualification"] or existing.get("latest_qualification"),
            "total_work_experience": mapped["total_work_experience"] or existing.get("total_work_experience"),
            "gender": mapped["gender"] or existing.get("gender"),
            "marital_status": mapped["marital_status"] or existing.get("marital_status"),
            "resume_url": mapped["resume_url"] or existing.get("resume_url"),
            "payment_status": mapped["payment_status"] or existing.get("payment_status"),
            "payment_mode": mapped["payment_mode"] or existing.get("payment_mode"),
            "payment_amount": mapped["payment_amount"] if mapped["payment_amount"] is not None else existing.get("payment_amount"),
            "razorpay_payment_id": mapped["razorpay_payment_id"] or existing.get("razorpay_payment_id"),
            "razorpay_order_id": mapped["razorpay_order_id"] or existing.get("razorpay_order_id"),
            "paid_at": mapped["paid_at"] or existing.get("paid_at"),
            "sales_person_name": mapped["sales_person_name"] or existing.get("sales_person_name"),
            "reference": mapped["reference"] or existing.get("reference"),
            "stage": new_stage,
            "priority": new_priority,
            "updated_at": datetime.now(timezone.utc),
        }

        # Combine tags
        combined_tags = list(set(existing.get("tags", []) + mapped.get("tags", [])))
        update_fields["tags"] = combined_tags

        await leads_col.update_one({"_id": existing["_id"]}, {"$set": update_fields})
        merged = {**existing, **update_fields}
        return merged, False
    else:
        # Generate new lead ID and sequential lead number
        count = await leads_col.count_documents({})
        lead_number = f"LD{(count + 6620):06d}"
        
        new_lead = {
            "id": str(uuid.uuid4()),
            "lead_number": lead_number,
            **mapped,
            "notes": [],
            "assigned_to": mapped.get("assigned_to"),
            "assigned_to_name": mapped.get("assigned_to_name") or "Unassigned",
        }
        await leads_col.insert_one(new_lead)
        return new_lead, True


async def sync_from_mysql_database(
    host: Optional[str] = None,
    port: Optional[int] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    database: Optional[str] = None,
) -> Dict[str, Any]:
    """Connects to MySQL database `hosldwuh_staging` and imports/updates all `navratri_registrations`."""
    h = host or MYSQL_HOST
    p = port or MYSQL_PORT
    u = user or MYSQL_USER
    pwd = password or MYSQL_PASSWORD
    db_name = database or MYSQL_DB

    rows = []
    # Try importing pymysql or aiomysql or mysql.connector
    try:
        import aiomysql
        conn = await aiomysql.connect(
            host=h,
            port=p,
            user=u,
            password=pwd,
            db=db_name,
            cursorclass=aiomysql.DictCursor,
            connect_timeout=10,
        )
        async with conn.cursor() as cur:
            await cur.execute("SELECT * FROM navratri_registrations ORDER BY id ASC")
            rows = await cur.fetchall()
        conn.close()
    except Exception as e_async:
        logger.warning(f"aiomysql connect failed ({e_async}), trying pymysql...")
        try:
            import pymysql
            conn = pymysql.connect(
                host=h,
                port=p,
                user=u,
                password=pwd,
                database=db_name,
                cursorclass=pymysql.cursors.DictCursor,
                connect_timeout=10,
            )
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM navratri_registrations ORDER BY id ASC")
                rows = cur.fetchall()
            conn.close()
        except Exception as e_sync:
            try:
                import mysql.connector
                conn = mysql.connector.connect(
                    host=h,
                    port=p,
                    user=u,
                    password=pwd,
                    database=db_name,
                    connection_timeout=10,
                )
                cur = conn.cursor(dictionary=True)
                cur.execute("SELECT * FROM navratri_registrations ORDER BY id ASC")
                rows = cur.fetchall()
                cur.close()
                conn.close()
            except Exception as e_mysql:
                raise RuntimeError(
                    f"Could not connect to MySQL database at {h}:{p} ({db_name}). Error: {e_mysql or e_sync or e_async}"
                )

    total_synced = 0
    new_count = 0
    updated_count = 0

    for row in rows:
        _, is_new = await upsert_website_lead(dict(row))
        total_synced += 1
        if is_new:
            new_count += 1
        else:
            updated_count += 1

    return {
        "status": "success",
        "total_rows_found": len(rows),
        "total_synced": total_synced,
        "new_leads_created": new_count,
        "existing_leads_updated": updated_count,
        "synced_at": datetime.now(timezone.utc).isoformat(),
    }
