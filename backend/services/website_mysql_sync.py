"""Website MySQL & Live API Sync Service
Synchronizes leads from live website (https://leamss.com/api/crm-website-leads-export)
and cPanel MySQL database (hosldwuh_staging) tables:
- general_enquiries (name, phone, email, country, services, qualification, work_exp, msg, enquired_for, created_at)
- popup_enquiries (name, phone, email, qualification, services, work_experience, created_at)
into LEAMSS CRM MongoDB leads collection.
"""
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import pymysql
import pymysql.cursors

from core.database import db
from core.services import log_activity
from routers.crm_website_leads import classify_lead_category, normalize_country, resolve_page_details
from routers.leads import _next_lead_number, calculate_lead_score

leads_col = db["leads"]


def _parse_datetime(dt_val: Any) -> datetime:
    """Parses various datetime representations from MySQL into UTC datetime."""
    if isinstance(dt_val, datetime):
        return dt_val if dt_val.tzinfo else dt_val.replace(tzinfo=timezone.utc)
    if isinstance(dt_val, str) and dt_val.strip():
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(dt_val.strip()[:19], fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    return datetime.now(timezone.utc)


async def sync_mysql_general_row(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Converts a row from MySQL general_enquiries into a CRM lead doc and inserts if not duplicate."""
    row_id = str(row.get("id") or "")
    dedup_tag = f"mysql_general_{row_id}"

    name = str(row.get("name") or "Website Client").strip()
    phone = str(row.get("phone") or "").strip()
    email = str(row.get("email") or "").strip()
    country_raw = str(row.get("country") or "").strip()
    services = str(row.get("services") or "").strip()
    qualification = str(row.get("qualification") or "").strip()
    work_exp = str(row.get("work_exp") or "").strip()
    msg = str(row.get("msg") or "").strip()
    enquired_for = str(row.get("enquired_for") or "Migrate").strip()
    created_at = _parse_datetime(row.get("created_at"))

    page_url_raw = str(row.get("website_page_url") or row.get("page_url") or row.get("url") or "").strip()
    page_title_raw = str(row.get("website_page_title") or row.get("page_title") or "").strip()
    atlas_code = str(row.get("atlas_code") or row.get("code") or "").strip()
    atlas_title = str(row.get("atlas_title") or row.get("occupation") or "").strip()
    explicit_cat = str(row.get("lead_category") or row.get("category") or "").strip()
    raw_source = str(row.get("source") or ("public_atlas" if (atlas_code or atlas_title) else "Website")).strip()

    row_context = {
        **row,
        "services": services,
        "service_interested": services,
        "enquired_for": enquired_for,
        "country": country_raw,
        "msg": msg,
        "message": msg,
        "website_page_url": page_url_raw,
        "website_page_title": page_title_raw,
        "atlas_code": atlas_code,
        "atlas_title": atlas_title,
        "lead_category": explicit_cat,
        "source": raw_source
    }

    category = classify_lead_category(row_context)
    page_title, page_url, visa_pathway = resolve_page_details(row_context)
    country_norm = normalize_country(country_raw, page_url=page_url, atlas_code=atlas_code)

    # Check deduplication & update outdated fields if exists
    existing = await leads_col.find_one(
        {"$or": [{"id": row_id}, {"tags": dedup_tag}]} if row_id else {"tags": dedup_tag},
        {"_id": 1, "website_page_title": 1, "website_page_url": 1}
    )
    if existing:
        upd_fields = {
            "website_page_title": page_title,
            "website_page_url": page_url,
            "enquired_for": enquired_for,
            "visa_pathway": visa_pathway or services,
            "lead_category": category,
            "country": country_norm,
            "country_of_interest": country_norm,
            "interested_country": country_norm,
        }
        if atlas_code:
            upd_fields["atlas_code"] = atlas_code
        if atlas_title:
            upd_fields["atlas_title"] = atlas_title
        await leads_col.update_one({"_id": existing["_id"]}, {"$set": upd_fields})
        return None

    lead_number = await _next_lead_number()

    score, score_category = calculate_lead_score({
        "phone": phone,
        "email": email,
        "country": country_norm,
        "services": services,
        "qualification": qualification,
        "work_exp": work_exp
    })

    lead_doc = {
        "id": str(uuid.uuid4()),
        "lead_number": lead_number,
        "name": name,
        "email": email,
        "phone": phone,
        "alternate_phone": "",
        "whatsapp_number": phone,
        "country": country_norm,
        "country_of_interest": country_norm,
        "interested_country": country_norm,
        "service_interested": services or "General Migration Consultation",
        "service_type": services,
        "services": services,
        "visa_pathway": visa_pathway or services or "General Migration Consultation",
        "lead_category": category,
        "latest_qualification": qualification,
        "qualification": qualification,
        "total_work_experience": work_exp,
        "work_experience": work_exp,
        "work_exp": work_exp,
        "message": msg,
        "enquired_for": enquired_for,
        "website_page_title": page_title,
        "website_page_url": page_url,
        "source": raw_source,
        "atlas_code": atlas_code or None,
        "atlas_title": atlas_title or None,
        "stage": "new",
        "status": "new",
        "priority": "medium",
        "lead_score": score,
        "score_category": score_category,
        "assigned_to": None,
        "assigned_to_name": "Unassigned",
        "tags": ["website", "general_enquiry", dedup_tag] + (["atlas", "public_atlas"] if (category == "Atlas" or atlas_code or atlas_title) else []),
        "notes": [f"Imported from cPanel MySQL table 'general_enquiries' (ID: {row_id})"],
        "call_count": 0,
        "created_at": created_at,
        "updated_at": created_at,
        "converted": False,
        "company_id": "comp_leamss_primary",
    }

    await leads_col.insert_one(lead_doc)
    return lead_doc


async def sync_mysql_popup_row(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Converts a row from MySQL popup_enquiries into a CRM lead doc and inserts if not duplicate."""
    row_id = str(row.get("id") or "")
    dedup_tag = f"mysql_popup_{row_id}"

    # Check deduplication
    existing = await leads_col.find_one({"tags": dedup_tag}, {"_id": 1})
    if existing:
        return None

    name = str(row.get("name") or "Popup Client").strip()
    phone = str(row.get("phone") or "").strip()
    email = str(row.get("email") or "").strip()
    qualification = str(row.get("qualification") or "").strip()
    services = str(row.get("services") or "").strip()
    work_exp = str(row.get("work_experience") or "").strip()
    created_at = _parse_datetime(row.get("created_at"))

    category = classify_lead_category({
        "services": services,
        "service_interested": services
    })

    # Detect country from services (e.g. "PR Australia", "TR Canada")
    country_raw = "Australia" if "australia" in services.lower() else ("Canada" if "canada" in services.lower() else "Other")
    country_norm = normalize_country(country_raw)
    lead_number = await _next_lead_number()

    score, score_category = calculate_lead_score({
        "phone": phone,
        "email": email,
        "country": country_norm,
        "services": services,
        "qualification": qualification,
        "work_exp": work_exp
    })

    lead_doc = {
        "id": str(uuid.uuid4()),
        "lead_number": lead_number,
        "name": name,
        "email": email,
        "phone": phone,
        "alternate_phone": "",
        "whatsapp_number": phone,
        "country": country_norm,
        "country_of_interest": country_norm,
        "interested_country": country_norm,
        "service_interested": services or "Website Consultation Popup",
        "service_type": services,
        "services": services,
        "visa_pathway": services or "Website Consultation Popup",
        "lead_category": category,
        "latest_qualification": qualification,
        "qualification": qualification,
        "total_work_experience": work_exp,
        "work_experience": work_exp,
        "work_exp": work_exp,
        "message": f"Submitted enquiry via website popup for service: {services}",
        "enquired_for": "Website Popup",
        "website_page_title": "LEAMSS Official Website - Popup Enquiry",
        "website_page_url": "https://leamss.com",
        "source": "Website Popup",
        "stage": "new",
        "status": "new",
        "priority": "medium",
        "lead_score": score,
        "score_category": score_category,
        "assigned_to": None,
        "assigned_to_name": "Unassigned",
        "tags": ["website", "popup_enquiry", dedup_tag],
        "notes": [f"Imported from cPanel MySQL table 'popup_enquiries' (ID: {row_id})"],
        "call_count": 0,
        "created_at": created_at,
        "updated_at": created_at,
        "converted": False,
        "company_id": "comp_leamss_primary",
    }

    await leads_col.insert_one(lead_doc)
    return lead_doc


async def sync_from_mysql_connection(
    host: str,
    user: str,
    password: str,
    database: str = "hosldwuh_staging",
    port: int = 3306
) -> Dict[str, Any]:
    """Connects to cPanel MySQL and synchronizes all general_enquiries and popup_enquiries."""
    conn = pymysql.connect(
        host=host,
        user=user,
        password=password,
        database=database,
        port=port,
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=15
    )

    general_synced = 0
    popup_synced = 0

    try:
        with conn.cursor() as cursor:
            # 1. Fetch general_enquiries
            cursor.execute("SELECT * FROM general_enquiries ORDER BY id ASC")
            general_rows = cursor.fetchall()
            for r in general_rows:
                res = await sync_mysql_general_row(r)
                if res:
                    general_synced += 1

            # 2. Fetch popup_enquiries
            cursor.execute("SELECT * FROM popup_enquiries ORDER BY id ASC")
            popup_rows = cursor.fetchall()
            for r in popup_rows:
                res = await sync_mysql_popup_row(r)
                if res:
                    popup_synced += 1
    finally:
        conn.close()

    return {
        "success": True,
        "general_enquiries_synced": general_synced,
        "popup_enquiries_synced": popup_synced,
        "total_new_leads_synced": general_synced + popup_synced,
        "message": f"Successfully synced {general_synced} general enquiries and {popup_synced} popup enquiries into CRM."
    }


async def import_enquiry_rows_batch(rows: List[Dict[str, Any]], table_type: str = "general_enquiries") -> Dict[str, Any]:
    """Imports batch of enquiry rows (from phpMyAdmin JSON or CSV export)."""
    synced = 0
    for r in rows:
        if table_type == "popup_enquiries":
            res = await sync_mysql_popup_row(r)
        else:
            res = await sync_mysql_general_row(r)
        if res:
            synced += 1

    return {
        "success": True,
        "table_type": table_type,
        "rows_processed": len(rows),
        "new_leads_inserted": synced,
        "message": f"Processed {len(rows)} rows, inserted {synced} new leads into CRM."
    }


async def sync_live_website_export(url: str = "https://leamss.com/api/crm-website-leads-export") -> Dict[str, Any]:
    """Fetches general & popup enquiries from https://leamss.com/api/crm-website-leads-export and imports into MongoDB leads collection."""
    import httpx
    headers = {"User-Agent": "curl/8.7.1", "Accept": "*/*"}
    async with httpx.AsyncClient(timeout=30.0, verify=False, headers=headers) as client:
        resp = await client.get(url)
        if resp.status_code != 200:
            return {
                "success": False,
                "error": f"Website returned status {resp.status_code}",
                "general_inserted": 0,
                "popup_inserted": 0,
                "total_new_leads": 0,
                "message": f"Failed to fetch leads from {url}: status {resp.status_code}"
            }
        data = resp.json()

    gen_rows = data.get("general") if isinstance(data, dict) else (data if isinstance(data, list) else [])
    pop_rows = data.get("popups", []) if isinstance(data, dict) else []

    gen_res = await import_enquiry_rows_batch(gen_rows, "general_enquiries") if gen_rows else {"new_leads_inserted": 0}
    pop_res = await import_enquiry_rows_batch(pop_rows, "popup_enquiries") if pop_rows else {"new_leads_inserted": 0}

    total = gen_res["new_leads_inserted"] + pop_res["new_leads_inserted"]
    return {
        "success": True,
        "general_inserted": gen_res["new_leads_inserted"],
        "popup_inserted": pop_res["new_leads_inserted"],
        "total_new_leads": total,
        "message": f"Successfully synced {total} new leads from live website."
    }
