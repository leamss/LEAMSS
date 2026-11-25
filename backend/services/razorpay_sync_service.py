"""Razorpay Payment Synchronization & Consultation Tracking Service.

Integrates Razorpay payments (via webhooks and direct API polling) with LEAMSS CRM leads:
- Tracks Consultation form leads (https://leamss.com/consultation) paying via Razorpay Payment Page (pl_TZSVimtLKxHnHx).
- Matches leads by normalized email, phone (last 10 digits), or lead ID without creating duplicates.
- Handles all payment states: Paid (captured), Failed, Unpaid, and Partially Paid.
- Records full payment history per lead (deduplicated by payment_id).
- Logs audit timeline events in CRM.
"""

import os
import re
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import httpx

from core.database import db
from core.services import log_activity

logger = logging.getLogger("razorpay_sync")

leads_col = db["leads"]

RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "rzp_test_TIsfNCEO8uAj3s")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "44U5DyQ8wDflrot7O8VFF1b1")
RAZORPAY_WEBHOOK_SECRET = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "")
CONSULTATION_PAGE_LINK_ID = "pl_TZSVimtLKxHnHx"


def normalize_phone(phone: Optional[str]) -> str:
    """Extracts the last 10 digits of a phone number for consistent cross-source matching."""
    if not phone:
        return ""
    digits = re.sub(r"\D", "", str(phone))
    return digits[-10:] if len(digits) >= 10 else digits


def normalize_email(email: Optional[str]) -> str:
    """Normalizes email to lower-case stripped string."""
    if not email:
        return ""
    return str(email).strip().lower()


async def find_matching_lead(
    email: Optional[str] = None,
    phone: Optional[str] = None,
    lead_id: Optional[str] = None,
    payment_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Finds an existing CRM lead using email, phone (last 10 digits), lead ID, or payment ID."""
    # 1. Match by explicit lead ID / unique_id
    if lead_id and lead_id.strip():
        lead_id_clean = lead_id.strip()
        lead = await leads_col.find_one({
            "$or": [
                {"id": lead_id_clean},
                {"unique_id": lead_id_clean},
                {"lead_number": lead_id_clean}
            ]
        })
        if lead:
            return lead

    # 2. Match by email (case-insensitive)
    norm_email = normalize_email(email)
    if norm_email and "@" in norm_email:
        lead = await leads_col.find_one({
            "email": {"$regex": f"^{re.escape(norm_email)}$", "$options": "i"}
        })
        if lead:
            return lead

    # 3. Match by phone (last 10 digits)
    phone_10 = normalize_phone(phone)
    if phone_10 and len(phone_10) == 10:
        phone_query = {
            "$or": [
                {"phone": {"$regex": f"{re.escape(phone_10)}$"}},
                {"whatsapp_number": {"$regex": f"{re.escape(phone_10)}$"}},
                {"mobile_number": {"$regex": f"{re.escape(phone_10)}$"}},
                {"mobile_full": {"$regex": f"{re.escape(phone_10)}$"}}
            ]
        }
        # If payment provided an email, ensure we don't accidentally match a lead with a different known email
        norm_email = normalize_email(email)
        if norm_email and "@" in norm_email:
            leads_matching_phone = await leads_col.find(phone_query).to_list(20)
            for l in leads_matching_phone:
                l_email = normalize_email(l.get("email"))
                if not l_email or l_email == norm_email:
                    return l
        else:
            lead = await leads_col.find_one(phone_query)
            if lead:
                return lead

    # 4. Match by payment ID in razorpay_payment_id or payment_history
    if payment_id and payment_id.strip():
        pid = payment_id.strip()
        lead = await leads_col.find_one({
            "$or": [
                {"razorpay_payment_id": pid},
                {"payment_history.payment_id": pid}
            ]
        })
        if lead:
            return lead

    return None


async def process_razorpay_payment_entity(
    payment: Dict[str, Any],
    event_type: str = "payment.captured",
    default_link_id: str = CONSULTATION_PAGE_LINK_ID,
    target_lead_id: Optional[str] = None
) -> Dict[str, Any]:
    """Processes a Razorpay payment entity and associates it with a CRM lead without duplicates.

    Handles:
    - Status: captured/paid, failed, pending/authorized.
    - Captures payment amount, method, VPA/bank, timestamp, and link ID.
    - Deduplicates payment_history array entries by payment_id.
    - Appends timeline event to the CRM lead.
    """
    payment_id = str(payment.get("id") or "").strip()
    if not payment_id:
        return {"success": False, "error": "No payment ID found in entity"}

    amount_paise = int(payment.get("amount") or 0)
    amount_rupees = round(amount_paise / 100.0, 2)
    currency = str(payment.get("currency") or "INR").upper()
    raw_status = str(payment.get("status") or "").strip().lower()

    # Determine consolidated payment status
    if event_type == "payment.failed" or raw_status == "failed":
        payment_status = "failed"
        is_paid = False
    elif raw_status == "captured" or event_type in ("payment.captured", "payment_link.paid", "order.paid"):
        payment_status = "paid"
        is_paid = True
    elif raw_status == "authorized":
        payment_status = "pending"
        is_paid = False
    else:
        payment_status = raw_status or "unpaid"
        is_paid = payment_status in ("paid", "captured", "success")

    notes = payment.get("notes") or {}
    email = payment.get("email") or notes.get("email") or ""
    contact = payment.get("contact") or notes.get("phone") or notes.get("mobile") or ""
    client_name = notes.get("name") or notes.get("fullName") or notes.get("client_name") or ""
    explicit_lead_id = notes.get("lead_id") or notes.get("unique_id") or notes.get("id") or ""

    method = str(payment.get("method") or "online").lower()
    vpa = str(payment.get("vpa") or "")
    bank = str(payment.get("bank") or "")
    wallet = str(payment.get("wallet") or "")
    card_info = payment.get("card") or {}
    card_network = card_info.get("network", "") if isinstance(card_info, dict) else ""
    card_last4 = card_info.get("last4", "") if isinstance(card_info, dict) else ""

    error_code = str(payment.get("error_code") or "")
    error_desc = str(payment.get("error_description") or payment.get("error_reason") or "")

    link_id = (
        payment.get("payment_link_id")
        or notes.get("payment_page_id")
        or notes.get("link_id")
        or default_link_id
    )

    created_timestamp = payment.get("created_at")
    if isinstance(created_timestamp, (int, float)) and created_timestamp > 0:
        dt = datetime.fromtimestamp(created_timestamp, tz=timezone.utc)
        payment_date_iso = dt.isoformat()
    else:
        payment_date_iso = datetime.now(timezone.utc).isoformat()

    # Build structured history entry
    history_entry = {
        "payment_id": payment_id,
        "amount": amount_rupees,
        "currency": currency,
        "status": payment_status,
        "method": method,
        "vpa": vpa,
        "bank": bank,
        "card_network": card_network,
        "card_last4": card_last4,
        "wallet": wallet,
        "link_id": link_id,
        "error_code": error_code if payment_status == "failed" else "",
        "error_description": error_desc if payment_status == "failed" else "",
        "created_at": payment_date_iso,
    }

    # Match existing lead
    if target_lead_id and target_lead_id.strip():
        matched_lead = await leads_col.find_one({
            "$or": [
                {"id": target_lead_id.strip()},
                {"unique_id": target_lead_id.strip()},
                {"lead_number": target_lead_id.strip()}
            ]
        })
    else:
        matched_lead = await find_matching_lead(
            email=email,
            phone=contact,
            lead_id=explicit_lead_id,
            payment_id=payment_id
        )

    now_utc = datetime.now(timezone.utc).isoformat()

    if matched_lead:
        lead_id = matched_lead["id"]
        # Filter existing payment history to prevent duplicates
        existing_history = [
            h for h in (matched_lead.get("payment_history") or [])
            if h.get("payment_id") != payment_id
        ]
        updated_history = [history_entry] + existing_history

        update_fields: Dict[str, Any] = {
            "payment_history": updated_history,
            "updated_at": now_utc,
            "razorpay_payment_link_id": link_id
        }

        if is_paid:
            update_fields["is_paid"] = True
            update_fields["payment_status"] = "paid"
            update_fields["amount_paid"] = amount_rupees
            update_fields["payment_amount"] = max(matched_lead.get("payment_amount") or 0, amount_rupees, 2427.0)
            update_fields["paid_at"] = payment_date_iso
            update_fields["payment_date"] = payment_date_iso
            update_fields["razorpay_payment_id"] = payment_id
            update_fields["payment_method"] = method
            update_fields["payment_mode"] = method.upper()
            if vpa:
                update_fields["payment_vpa"] = vpa

            if matched_lead.get("stage") in ("new", "contacted", "assigned", None):
                update_fields["stage"] = "payment_done"

            method_display = f"{method.upper()}" + (f" ({vpa})" if vpa else "")
            await log_activity(
                lead_id,
                f"Razorpay payment of ₹{amount_rupees:,.2f} captured successfully (Payment ID: {payment_id}, Link: {link_id}, Method: {method_display})",
                "payment_captured",
                "razorpay"
            )
        elif payment_status == "failed":
            # Only set lead payment_status to failed if lead is not already successfully paid
            if not matched_lead.get("is_paid"):
                update_fields["payment_status"] = "failed"
                update_fields["is_paid"] = False
                update_fields["last_payment_error"] = error_desc or "Payment failed"
                update_fields["last_payment_error_code"] = error_code
                update_fields["last_payment_attempt_at"] = payment_date_iso

            await log_activity(
                lead_id,
                f"Razorpay payment attempt of ₹{amount_rupees:,.2f} failed: {error_desc or 'Unknown error'} (Payment ID: {payment_id})",
                "payment_failed",
                "razorpay"
            )

        await leads_col.update_one({"id": lead_id}, {"$set": update_fields})
        logger.info(f"Updated lead {lead_id} with Razorpay payment {payment_id} (status: {payment_status})")
        return {
            "success": True,
            "action": "updated",
            "lead_id": lead_id,
            "payment_id": payment_id,
            "payment_status": update_fields.get("payment_status", matched_lead.get("payment_status")),
            "is_paid": update_fields.get("is_paid", matched_lead.get("is_paid")),
            "amount_paid": amount_rupees if is_paid else (matched_lead.get("amount_paid") or 0.0)
        }
    else:
        # Lead not found in CRM yet (e.g. client paid directly on link or payment arrived before form sync)
        from routers.leads import _next_lead_number, calculate_lead_score
        lead_number = await _next_lead_number()
        lead_id = str(uuid.uuid4())
        name_val = client_name or f"Consultation Client ({payment_id[-6:]})"
        score, score_category = calculate_lead_score({
            "phone": contact,
            "email": email,
            "country": "India",
            "services": "Consultation"
        })

        new_lead = {
            "id": lead_id,
            "lead_number": lead_number,
            "name": name_val,
            "email": email,
            "phone": contact,
            "alternate_phone": "",
            "whatsapp_number": contact,
            "country": "India",
            "country_of_interest": "Australia",
            "interested_country": "Australia",
            "service_interested": "Consultation",
            "service_type": "Consultation",
            "services": "Consultation",
            "visa_pathway": "Consultation Registration",
            "lead_category": "Consultation",
            "website_page_title": "Consultation Registration",
            "website_page_url": "https://leamss.com/consultation",
            "source": "Website Consultation",
            "original_source": "Razorpay Payment Link",
            "stage": "payment_done" if is_paid else "new",
            "status": "active",
            "priority": "high" if is_paid else "medium",
            "lead_score": score,
            "score_category": score_category,
            "assigned_to": None,
            "assigned_to_name": "Unassigned",
            "is_paid": is_paid,
            "payment_status": payment_status,
            "payment_amount": max(amount_rupees, 2427.0),
            "amount_paid": amount_rupees if is_paid else 0.0,
            "paid_at": payment_date_iso if is_paid else None,
            "payment_date": payment_date_iso if is_paid else None,
            "razorpay_payment_id": payment_id if is_paid else "",
            "razorpay_payment_link_id": link_id,
            "payment_method": method,
            "payment_mode": method.upper(),
            "payment_history": [history_entry],
            "last_payment_error": error_desc if payment_status == "failed" else "",
            "tags": ["website", "consultation", "razorpay", link_id],
            "notes": [f"Created automatically via Razorpay payment {payment_id} ({payment_status})"],
            "call_count": 0,
            "created_at": payment_date_iso,
            "updated_at": now_utc,
            "converted": False,
            "company_id": "comp_leamss_primary"
        }

        await leads_col.insert_one(new_lead)
        logger.info(f"Created new lead {lead_id} from Razorpay payment {payment_id} (status: {payment_status})")
        return {
            "success": True,
            "action": "created",
            "lead_id": lead_id,
            "payment_id": payment_id,
            "payment_status": payment_status,
            "is_paid": is_paid,
            "amount_paid": amount_rupees if is_paid else 0.0
        }


async def fetch_razorpay_payments_api(count: int = 50) -> List[Dict[str, Any]]:
    """Fetches recent payments directly from Razorpay REST API."""
    key_id = os.environ.get("RAZORPAY_KEY_ID") or RAZORPAY_KEY_ID
    key_secret = os.environ.get("RAZORPAY_KEY_SECRET") or RAZORPAY_KEY_SECRET
    if not key_id or not key_secret:
        logger.warning("Razorpay credentials not configured")
        return []

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                "https://api.razorpay.com/v1/payments",
                params={"count": min(count, 100)},
                auth=(key_id, key_secret)
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("items") or []
            else:
                logger.error(f"Razorpay API error {resp.status_code}: {resp.text}")
                return []
    except Exception as e:
        logger.error(f"Failed to query Razorpay API: {e}")
        return []


async def sync_all_recent_razorpay_payments(count: int = 50) -> Dict[str, Any]:
    """Fetches recent payments from Razorpay API and syncs them to CRM leads."""
    payments = await fetch_razorpay_payments_api(count=count)
    processed = 0
    updated = 0
    created = 0

    for payment in payments:
        res = await process_razorpay_payment_entity(payment)
        processed += 1
        if res.get("action") == "updated":
            updated += 1
        elif res.get("action") == "created":
            created += 1

    return {
        "success": True,
        "total_fetched": len(payments),
        "processed": processed,
        "updated": updated,
        "created": created
    }


async def reconcile_single_lead_payment(lead_id: str) -> Dict[str, Any]:
    """Checks live Razorpay API for payments associated with a specific lead's email or phone."""
    lead = await leads_col.find_one({"$or": [{"id": lead_id}, {"unique_id": lead_id}, {"lead_number": lead_id}]})
    if not lead:
        return {"success": False, "error": "Lead not found"}

    target_email = normalize_email(lead.get("email"))
    target_phone_10 = normalize_phone(lead.get("phone") or lead.get("whatsapp_number"))

    # Fetch recent payments from Razorpay API
    payments = await fetch_razorpay_payments_api(count=100)
    matched_payment = None

    for p in payments:
        p_email = normalize_email(p.get("email") or p.get("notes", {}).get("email"))
        p_phone_10 = normalize_phone(p.get("contact") or p.get("notes", {}).get("phone"))
        p_notes_id = p.get("notes", {}).get("lead_id") or p.get("notes", {}).get("unique_id")
        p_link_id = p.get("payment_link_id") or p.get("notes", {}).get("payment_page_id") or p.get("notes", {}).get("link_id")

        # 1. Match by explicit lead ID in notes
        id_match = bool(p_notes_id and p_notes_id in (lead.get("id"), lead.get("unique_id"), lead.get("lead_number")))
        # 2. Match by email
        email_match = bool(target_email and p_email and target_email == p_email)
        # 3. Match by phone only when email does not conflict
        email_conflict = bool(target_email and p_email and target_email != p_email)
        phone_match = bool(target_phone_10 and p_phone_10 and target_phone_10 == p_phone_10 and not email_conflict)

        # Do not match payments with conflicting email unless ID explicitly matches
        if email_conflict and not id_match:
            continue

        if id_match or email_match or phone_match:
            is_consultation = (p_link_id == CONSULTATION_PAGE_LINK_ID or p.get("amount") in (99900, 242700))
            if not matched_payment or is_consultation or p.get("status") == "captured":
                matched_payment = p
                if is_consultation and p.get("status") == "captured":
                    break

    if matched_payment:
        result = await process_razorpay_payment_entity(
            matched_payment,
            event_type=f"payment.{matched_payment.get('status', 'captured')}",
            target_lead_id=lead["id"]
        )
        from core.navratri_automation import is_lead_paid, has_lead_resume
        refreshed = await leads_col.find_one({"id": lead["id"]}, {"_id": 0})
        if refreshed:
            paid = is_lead_paid(refreshed)
            refreshed["is_paid"] = paid
            refreshed["has_resume"] = has_lead_resume(refreshed)
            if paid and not refreshed.get("payment_status"):
                refreshed["payment_status"] = "paid"
            elif not paid and not refreshed.get("payment_status"):
                refreshed["payment_status"] = "unpaid"
            if not refreshed.get("payment_amount"):
                refreshed["payment_amount"] = refreshed.get("amount") or 2427.0
            if "amount_paid" not in refreshed or refreshed.get("amount_paid") is None:
                refreshed["amount_paid"] = refreshed["payment_amount"] if paid else 0.0

        return {
            "success": True,
            "matched": True,
            "payment": matched_payment,
            "lead": refreshed,
            "message": f"Payment {matched_payment.get('id')} reconciled (Status: {matched_payment.get('status')})"
        }

    return {
        "success": True,
        "matched": False,
        "message": f"No matching payments found for {lead.get('name', 'client')} (Email: {lead.get('email') or 'None'}, Phone: {lead.get('phone') or 'None'})"
    }
