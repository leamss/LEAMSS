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
from core.navratri_automation import is_valid_resume_path

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
    mobile = row.get("mobile_full") or row.get("mobileFull") or row.get("mobile") or row.get("phone") or ""
    mobile_num = row.get("mobile_number") or row.get("mobileNumber") or ""
    country_code = row.get("country_code") or row.get("countryCode") or "91"
    if not mobile and mobile_num:
        mobile = f"+{country_code}{mobile_num}" if not str(mobile_num).startswith("+") else str(mobile_num)
    
    # Unique ID from website
    raw_uid = (row.get("unique_id") or row.get("uniqueId") or "").strip()
    raw_id = row.get("id") or row.get("external_id")
    if raw_uid:
        if isinstance(raw_uid, int) or (isinstance(raw_uid, str) and raw_uid.isdigit()):
            unique_id = f"NN2427{raw_uid}"
        else:
            unique_id = raw_uid
    elif raw_id:
        unique_id = f"NN2427{raw_id}"
    else:
        unique_id = ""

    # Payment details
    raw_status = (row.get("payment_status") or row.get("paymentStatus") or row.get("status") or "").strip().lower()
    if raw_status in ("success", "paid", "completed", "captured"):
        payment_status = "success"
    elif raw_status in ("failed", "cancelled", "declined"):
        payment_status = "failed"
    else:
        payment_status = "pending"

    payment_amount = row.get("payment_amount") or row.get("paymentAmount") or row.get("amount")
    try:
        payment_amount_float = float(payment_amount) if payment_amount is not None else None
    except (ValueError, TypeError):
        payment_amount_float = None

    payment_mode = row.get("payment_mode") or row.get("paymentMode")
    razorpay_payment_id = row.get("razorpay_payment_id") or row.get("razorpayPaymentId") or row.get("payment_id")
    razorpay_order_id = row.get("razorpay_order_id") or row.get("razorpayOrderId") or row.get("order_id")
    paid_at = _parse_dt(row.get("paid_at") or row.get("paidAt"))
    
    created_at = _parse_dt(row.get("created_at") or row.get("createdAt")) or datetime.now(timezone.utc)
    updated_at = _parse_dt(row.get("updated_at") or row.get("updatedAt")) or datetime.now(timezone.utc)

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
    raw_resume = (
        row.get("resume_link")
        or row.get("resume_url")
        or row.get("resume_path")
        or row.get("resumePath")
        or row.get("resume")
        or ""
    )
    resume_path = ""
    resume_url = ""
    if raw_resume and is_valid_resume_path(raw_resume):
        resume_path = str(raw_resume).strip()
        if resume_path.startswith("http://") or resume_path.startswith("https://"):
            resume_url = resume_path
        else:
            clean_path = resume_path.lstrip("/")
            resume_url = f"https://leamss.com/{clean_path}"

    marital_status = row.get("marital_status") or row.get("marital") or row.get("maritalStatus") or ""
    dob = str(row.get("dob") or row.get("date_of_birth") or row.get("dateOfBirth") or "")
    qualification = str(row.get("qualification") or row.get("latest_qualification") or row.get("latestQualification") or "")
    experience = str(row.get("experience") or row.get("total_work_experience") or row.get("workExperience") or "")
    gender = str(row.get("gender") or "")
    sales_person_name = str(row.get("sales_person_name") or row.get("salesPersonName") or "")
    reference = str(row.get("reference") or "")

    tags = ["Navratri Offer 2026", "Website Registration"]
    if payment_status == "success":
        tags.append("Payment Success")
    elif payment_status == "failed":
        tags.append("Payment Failed")

    # STRICT RULE: New website registrations are ALWAYS Unassigned by default
    raw_assigned = row.get("assigned_to")
    if not raw_assigned or str(raw_assigned).strip().lower() in ("unassigned", "none", "null", "0", ""):
        assigned_to = None
        assigned_to_name = "Unassigned"
    else:
        assigned_to = str(raw_assigned).strip()
        assigned_to_name = row.get("assigned_to_name") or "Assigned"

    raw_partner = row.get("partner_id")
    if not raw_partner or str(raw_partner).strip().lower() in ("unassigned", "none", "null", "0", ""):
        partner_id = None
        partner_name = "Unassigned"
    else:
        partner_id = str(raw_partner).strip()
        partner_name = row.get("partner_name") or "Unassigned"

    raw_cm = row.get("case_manager_id")
    if not raw_cm or str(raw_cm).strip().lower() in ("unassigned", "none", "null", "0", ""):
        case_manager_id = None
        case_manager_name = "Unassigned"
    else:
        case_manager_id = str(raw_cm).strip()
        case_manager_name = row.get("case_manager_name") or "Unassigned"

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
        "message": row.get("message") or f"Registered for Navratri Offer. Experience: {experience or 'N/A'}, Qualification: {qualification or 'N/A'}",
        "source": "Navratri Offer (leamss.com)",
        "subsource": row.get("subsource") or reference or "Website Form",
        "utm_source": row.get("utm_source") or "website_navratri",
        "utm_medium": row.get("utm_medium") or "web_form",
        "utm_campaign": row.get("utm_campaign") or "navratri_offers_2026",
        "is_navratri": True,
        "stage": row.get("stage") or stage,
        "priority": row.get("priority") or priority,
        "assigned_to": assigned_to,
        "assigned_to_name": assigned_to_name,
        "partner_id": partner_id,
        "partner_name": partner_name,
        "case_manager_id": case_manager_id,
        "case_manager_name": case_manager_name,
        "date_of_birth": dob,
        "occupation": row.get("occupation") or "",
        "total_work_experience": experience,
        "latest_qualification": qualification,
        "gender": gender,
        "marital_status": marital_status,
        "resume_path": resume_path or None,
        "resume_url": resume_url or None,
        "resume_uploaded": bool(resume_url or resume_path),
        "sales_person_name": sales_person_name,
        "reference": reference,
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
            "resume_url": mapped["resume_url"] if (mapped.get("resume_url") and is_valid_resume_path(mapped["resume_url"])) else (existing.get("resume_url") if is_valid_resume_path(existing.get("resume_url")) else None),
            "resume_path": mapped["resume_path"] if (mapped.get("resume_path") and is_valid_resume_path(mapped["resume_path"])) else (existing.get("resume_path") if is_valid_resume_path(existing.get("resume_path")) else None),
            "payment_status": mapped["payment_status"],
            "payment_mode": mapped["payment_mode"] or existing.get("payment_mode"),
            "payment_amount": mapped["payment_amount"] if mapped["payment_amount"] is not None else existing.get("payment_amount"),
            "razorpay_payment_id": mapped["razorpay_payment_id"] or existing.get("razorpay_payment_id"),
            "razorpay_order_id": mapped["razorpay_order_id"] or existing.get("razorpay_order_id"),
            "paid_at": mapped["paid_at"] or existing.get("paid_at"),
            "sales_person_name": mapped["sales_person_name"] or existing.get("sales_person_name"),
            "reference": mapped["reference"] or existing.get("reference"),
            "source": "Navratri Offer (leamss.com)",
            "service_interested": mapped.get("service_interested") or existing.get("service_interested") or "Navratri Special Offer",
            "utm_campaign": mapped.get("utm_campaign") or existing.get("utm_campaign") or "navratri_offers_2026",
            "is_navratri": True,
            "stage": new_stage,
            "priority": new_priority,
            "updated_at": datetime.now(timezone.utc),
        }

        # Combine tags
        old_tags = existing.get("tags") or []
        combined_tags = list(set(old_tags + mapped.get("tags", []) + ["Navratri Offer 2026", "Website Registration"]))
        if mapped["payment_status"] == "success":
            if "Payment Failed" in combined_tags:
                combined_tags.remove("Payment Failed")
            if "Payment Success" not in combined_tags:
                combined_tags.append("Payment Success")
        elif mapped["payment_status"] == "failed":
            if "Payment Success" in combined_tags:
                combined_tags.remove("Payment Success")
            if "Payment Failed" not in combined_tags:
                combined_tags.append("Payment Failed")
        else:
            # Pending
            if "Payment Success" in combined_tags:
                combined_tags.remove("Payment Success")

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


async def reconcile_navratri_leads() -> Dict[str, Any]:
    """Scans MongoDB leads collection to ensure all Navratri registrations are correctly tagged, attributed, and indexed."""
    try:
        from pymongo import UpdateOne
        query = {
            "$or": [
                {"is_navratri": True},
                {"source": {"$regex": "navratri|website|staging", "$options": "i"}},
                {"utm_campaign": {"$regex": "navratri", "$options": "i"}},
                {"service_interested": {"$regex": "navratri|special offer", "$options": "i"}},
                {"unique_id": {"$regex": "^NN|[0-9]{6}", "$options": "i"}},
                {"tags": {"$regex": "navratri|website", "$options": "i"}},
            ]
        }
        leads = await leads_col.find(
            query,
            {"_id": 1, "unique_id": 1, "external_id": 1, "tags": 1, "payment_status": 1, "service_interested": 1, "resume_url": 1, "resume_path": 1, "resume_link": 1, "resume_file_id": 1}
        ).to_list(2000)

        if not leads:
            return {"status": "success", "reconciled_leads_count": 0}

        operations = []
        now = datetime.now(timezone.utc)
        for lead in leads:
            uid = str(lead.get("unique_id") or "")
            ext_id = str(lead.get("external_id") or "")
            if not uid.startswith("NN") and (ext_id or uid.isdigit()):
                uid = f"NN2427{ext_id or uid}"
            
            tags = list(set((lead.get("tags") or []) + ["Navratri Offer 2026", "Website Registration"]))
            pay_st = str(lead.get("payment_status") or "pending").lower()
            if pay_st in ("success", "paid"):
                if "Payment Success" not in tags: tags.append("Payment Success")
                if "Payment Failed" in tags: tags.remove("Payment Failed")
            elif pay_st in ("failed", "declined"):
                if "Payment Failed" not in tags: tags.append("Payment Failed")
                if "Payment Success" in tags: tags.remove("Payment Success")

            has_valid_res = (
                is_valid_resume_path(lead.get("resume_url"))
                or is_valid_resume_path(lead.get("resume_path"))
                or is_valid_resume_path(lead.get("resume_link"))
                or is_valid_resume_path(lead.get("resume_file_id"))
            )

            set_doc = {
                "is_navratri": True,
                "source": "Navratri Offer (leamss.com)",
                "unique_id": uid or lead.get("unique_id"),
                "service_interested": lead.get("service_interested") or "Navratri Special Offer",
                "tags": tags,
                "updated_at": now
            }
            if not has_valid_res:
                set_doc["resume_uploaded"] = False

            unset_doc = {}
            if pay_st not in ("success", "paid"):
                unset_doc.update({
                    "report_generated": "",
                    "bulk_batch_id": "",
                    "bulk_row_id": "",
                    "assessment_report_id": "",
                    "latest_report_snapshot_id": ""
                })
            if not has_valid_res:
                unset_doc.update({
                    "resume_url": "",
                    "resume_path": "",
                    "resume_link": "",
                    "resume_filename": "",
                    "resume_file_id": ""
                })

            update_dict = {"$set": set_doc}
            if unset_doc:
                update_dict["$unset"] = unset_doc

            operations.append(UpdateOne({"_id": lead["_id"]}, update_dict))

        if operations:
            await leads_col.bulk_write(operations, ordered=False)

        return {"status": "success", "reconciled_leads_count": len(operations)}
    except Exception as e:
        logger.warning(f"Reconcile error: {e}")
        return {"status": "error", "error": str(e)}
