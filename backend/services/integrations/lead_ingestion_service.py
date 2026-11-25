"""Centralized Lead Ingestion Service for 3rd-Party Integrations.

Handles:
- Inbound lead payload normalization
- Company data privacy isolation
- Multi-field duplicate detection (phone, email, whatsapp)
- Flexible duplicate strategies (skip, update_existing, flag_for_review)
- Intelligent lead assignment (round-robin among company reps, specific rep, or unassigned)
- Score calculation, activity logging, and notifications
"""
import uuid
import re
import logging
from urllib.parse import unquote
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
from core.database import db, users_col, leads_col
from core.services import create_notification, log_activity

logger = logging.getLogger(__name__)

integrations_col = db["integrations"]
sync_logs_col = db["integration_sync_logs"]
companies_col = db["companies"]


def _clean_phone(phone: Optional[str]) -> str:
    if not phone:
        return ""
    digits = re.sub(r"[^\d+]", "", str(phone).strip())
    return digits


async def _next_lead_number() -> str:
    count = await leads_col.count_documents({})
    return f"LD{(count + 6620):06d}"


def _calculate_score(lead: Dict[str, Any]) -> Tuple[int, str]:
    score = 25
    src = str(lead.get("source", "")).lower()
    if any(k in src for k in ["referral", "google", "website"]):
        score += 20
    elif any(k in src for k in ["facebook", "instagram", "meta", "zoho"]):
        score += 18
    else:
        score += 10

    if lead.get("email") and lead.get("phone"):
        score += 15
    if lead.get("country_of_interest") or lead.get("country"):
        score += 10
    if lead.get("service_interested"):
        score += 10
    if lead.get("message"):
        score += 10

    score = min(100, score)
    category = "HOT" if score >= 70 else "WARM" if score >= 40 else "COLD"
    return score, category


async def check_duplicate_lead(
    company_id: str,
    phone: str,
    email: str,
    whatsapp_number: str,
    name: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Check if duplicate lead exists within the company scope."""
    checks = []
    clean_p = _clean_phone(phone)
    clean_w = _clean_phone(whatsapp_number)
    clean_e = (email or "").strip().lower()

    # 1. Exact Email Match (Highest Priority)
    if clean_e and "@" in clean_e:
        match_email = await leads_col.find_one(
            {"email": {"$regex": f"^{re.escape(clean_e)}$", "$options": "i"}},
            {"_id": 0}
        )
        if match_email:
            return match_email

    # 2. Phone / WhatsApp Match with Name Corroboration
    phone_checks = []
    if clean_p and len(clean_p) >= 7:
        phone_checks.extend([
            {"phone": clean_p},
            {"phone": {"$regex": re.escape(clean_p[-10:]), "$options": "i"}},
            {"alternate_phone": clean_p}
        ])
    if clean_w and len(clean_w) >= 7:
        phone_checks.append({"whatsapp_number": clean_w})

    if not phone_checks:
        return None

    matches = await leads_col.find({"$or": phone_checks}, {"_id": 0}).sort("created_at", -1).to_list(50)
    if not matches:
        return None

    if name and name.strip():
        new_name_parts = set(name.strip().lower().split())
        for m in matches:
            ex_name = (m.get("name") or "").strip().lower()
            ex_parts = set(ex_name.split())
            if new_name_parts and ex_parts and (new_name_parts & ex_parts):
                return m
        return None

    return matches[0]


async def ingest_lead(
    company_id: str,
    integration_id: Optional[str],
    provider: str,
    raw_lead: Dict[str, Any]
) -> Dict[str, Any]:
    """Ingest, de-duplicate, assign, and store a lead from any integration."""
    now = datetime.now(timezone.utc)

    # Fetch integration settings if integration_id provided
    integration = None
    assignment_rules = {}
    dup_rules = {}
    if integration_id:
        integration = await integrations_col.find_one({"id": integration_id})
        if integration:
            assignment_rules = integration.get("lead_assignment_rules", {})
            dup_rules = integration.get("duplicate_prevention", {})

    # Extract & normalize fields with flexible key matching
    flat_lookup = {re.sub(r'[^a-z0-9]', '', str(k).lower()): v for k, v in raw_lead.items() if v is not None}
    def _get_val(*keys):
        for k in keys:
            norm_k = re.sub(r'[^a-z0-9]', '', str(k).lower())
            if norm_k in flat_lookup and flat_lookup[norm_k] is not None:
                val = flat_lookup[norm_k]
                if isinstance(val, (list, tuple)):
                    val = val[0] if len(val) > 0 else ""
                s = str(val).strip()
                if s:
                    return s
        return ""

    first_n = _get_val("firstname", "first")
    last_n = _get_val("lastname", "last", "surname")
    full_combo = f"{first_n} {last_n}".strip() if (first_n or last_n) else ""

    name = (
        _get_val("name", "fullname", "clientname", "applicantname", "candidatename", "leadname", "studentname", "client")
        or full_combo
        or "Enquiry Lead"
    )
    email = _get_val("email", "emailaddress", "mail", "e-mail").lower()
    raw_phone_val = _get_val("phone", "phonenumber", "mobile", "mobilenumber", "fullmobile", "contact", "contactnumber", "tel", "cell")
    raw_wa_val = _get_val("whatsappnumber", "whatsapp", "wa_number")
    phone = _clean_phone(raw_phone_val or raw_wa_val)
    whatsapp_number = _clean_phone(raw_wa_val or raw_phone_val)

    city = _get_val("city", "location", "currentlocation", "state", "place")
    country = _get_val("country", "targetcountry", "countryofinterest", "preferredcountry", "destination")
    service = _get_val("serviceinterested", "service", "servicetype", "visa", "program", "visatype", "pathway", "subclass") or "Immigration & Visa Consultation"
    message = _get_val("message", "query", "notes", "remark", "remarks", "comments", "description", "disharemark")
    campaign = _get_val("campaign", "formname", "sheetname", "adname") or f"{provider.capitalize()} Campaign"
    from services.lead_source_tracker import detect_lead_source, SOURCE_CALENDLY
    canonical_source, original_source, source_details = detect_lead_source(
        {**raw_lead, "provider": provider},
        default_source=provider.capitalize()
    )
    source = canonical_source

    # Spam & fake lead protection
    from services.spam_filter import is_spam_or_fake_lead
    if is_spam_or_fake_lead({"name": name, "email": email, "phone": phone, "message": message, "source": source, **raw_lead}):
        return {
            "status": "rejected",
            "action": "spam_blocked",
            "message": "Lead submission rejected by spam protection filter."
        }

    # 1. Duplicate check
    duplicate_strategy = dup_rules.get("strategy", "update" if provider == "calendly" else "skip")
    if duplicate_strategy == "always_create" and provider != "calendly":
        existing_lead = None
    else:
        unique_id_incoming = str(raw_lead.get("unique_id") or "").strip()
        if unique_id_incoming:
            existing_by_uid = await leads_col.find_one({
                "$or": [{"unique_id": unique_id_incoming}, {"tags": f"ref_{unique_id_incoming}"}]
            })
            if existing_by_uid:
                existing_lead = existing_by_uid
            elif email and "@" in email:
                # If unique_id is new, only treat as duplicate if same email AND matching first name / phone exists
                same_email_lead = await leads_col.find_one({"email": {"$regex": f"^{re.escape(email)}$", "$options": "i"}})
                if same_email_lead:
                    existing_lead_name = (same_email_lead.get("name") or same_email_lead.get("full_name") or "").lower().strip()
                    incoming_name = name.lower().strip()
                    first_in = incoming_name.split()[0] if incoming_name else ""
                    first_ex = existing_lead_name.split()[0] if existing_lead_name else ""
                    same_phone = bool(phone and same_email_lead.get("phone") and (phone == same_email_lead.get("phone") or phone[-10:] == str(same_email_lead.get("phone"))[-10:]))
                    name_similar = (
                        not first_in or not first_ex or
                        first_in == first_ex or
                        first_in.startswith(first_ex[:3]) or first_ex.startswith(first_in[:3])
                    )
                    if not same_phone and not name_similar:
                        existing_lead = None
                    else:
                        existing_lead = same_email_lead
                else:
                    existing_lead = None
            else:
                existing_lead = None
        else:
            existing_lead = await check_duplicate_lead(company_id, phone, email, whatsapp_number, name)
            # If matched by phone but email is completely different and non-empty, do not skip as duplicate
            if existing_lead and email and existing_lead.get("email"):
                if email.strip().lower() != str(existing_lead.get("email")).strip().lower():
                    existing_lead = None

    if existing_lead:
        # Existing duplicate found
        assigned_to = existing_lead.get("assigned_to")
        assigned_to_name = existing_lead.get("assigned_to_name") or "Unassigned"

        # Check if incoming submission carries payment updates (from Google Sheets, forms, or webhook)
        incoming_pay_status = str(raw_lead.get("payment_status") or "").strip().lower()
        incoming_is_paid = bool(raw_lead.get("is_paid") or incoming_pay_status in ("paid", "success", "captured", "completed", "successful"))
        incoming_amt = raw_lead.get("amount_paid") or raw_lead.get("payment_amount")
        clean_amt = None
        if incoming_amt is not None and str(incoming_amt).strip():
            try:
                amt_str = re.sub(r"[^\d.]", "", str(incoming_amt))
                if amt_str:
                    clean_amt = float(amt_str)
            except Exception:
                clean_amt = None

        has_payment_update = False
        if incoming_is_paid and not existing_lead.get("is_paid"):
            has_payment_update = True
        elif incoming_is_paid and clean_amt and clean_amt > (existing_lead.get("amount_paid") or 0):
            has_payment_update = True
        elif incoming_pay_status in ("failed", "partially_paid") and existing_lead.get("payment_status") != incoming_pay_status and not existing_lead.get("is_paid"):
            has_payment_update = True

        if has_payment_update:
            pay_set_fields: Dict[str, Any] = {}
            push_ops: Dict[str, Any] = {}
            if incoming_is_paid:
                pay_set_fields["payment_status"] = "paid"
                pay_set_fields["is_paid"] = True
                paid_amt_val = clean_amt if clean_amt is not None else (existing_lead.get("amount_paid") or 2427.0)
                pay_set_fields["amount_paid"] = paid_amt_val
                pay_set_fields["payment_amount"] = paid_amt_val
                pay_set_fields["fee_amount"] = paid_amt_val
                pay_set_fields["payment_method"] = raw_lead.get("payment_method") or existing_lead.get("payment_method") or "online"
                pay_set_fields["paid_at"] = raw_lead.get("payment_timestamp") or now.isoformat()
                pay_set_fields["payment_date"] = raw_lead.get("payment_timestamp") or now.isoformat()
                if existing_lead.get("stage") in ("new", "open", "contacted", "assigned", "lead", None):
                    pay_set_fields["stage"] = "payment_done"

                pay_id = raw_lead.get("razorpay_payment_id") or raw_lead.get("payment_id") or f"sheet_{raw_lead.get('unique_id') or uuid.uuid4().hex[:8]}"
                existing_hist = existing_lead.get("payment_history") or []
                if not any(h.get("payment_id") == pay_id for h in existing_hist):
                    hist_entry = {
                        "payment_id": pay_id,
                        "amount": paid_amt_val,
                        "method": pay_set_fields["payment_method"],
                        "status": "paid",
                        "link_id": "pl_TZSVimtLKxHnHx",
                        "created_at": raw_lead.get("payment_timestamp") or now.isoformat(),
                        "source": f"{provider.capitalize()} ({campaign})"
                    }
                    push_ops["payment_history"] = hist_entry

                note_msg = f"Payment of ₹{paid_amt_val:,.2f} confirmed via {provider.capitalize()} ({campaign}). Status: paid, Method: {pay_set_fields['payment_method']}."
                push_ops["notes"] = {
                    "id": str(uuid.uuid4()),
                    "text": note_msg,
                    "author": f"System ({provider.capitalize()} Integration)",
                    "created_at": now.isoformat()
                }

            elif incoming_pay_status == "failed" and not existing_lead.get("is_paid"):
                pay_set_fields["payment_status"] = "failed"
                pay_set_fields["is_paid"] = False
                pay_set_fields["last_payment_error"] = raw_lead.get("message") or "Payment attempt failed"
                fail_hist_entry = {
                    "payment_id": raw_lead.get("razorpay_payment_id") or raw_lead.get("payment_id") or f"sheet_fail_{uuid.uuid4().hex[:8]}",
                    "amount": clean_amt or 999.0,
                    "method": raw_lead.get("payment_method") or "online",
                    "status": "failed",
                    "link_id": "pl_TZSVimtLKxHnHx",
                    "created_at": raw_lead.get("payment_timestamp") or now.isoformat(),
                    "error_description": pay_set_fields["last_payment_error"]
                }
                push_ops["payment_history"] = fail_hist_entry

            raw_res = raw_lead.get("resume_url") or raw_lead.get("resume_path") or raw_lead.get("resume") or raw_lead.get("resume_link")
            if raw_res and not existing_lead.get("resume_file_id"):
                pay_set_fields["resume_url"] = str(raw_res).strip()
                pay_set_fields["resume_path"] = str(raw_res).strip()
                from urllib.parse import unquote
                fname = raw_lead.get("resume_filename") or unquote(str(raw_res).split("/")[-1].split("?")[0]) or "resume.pdf"
                pay_set_fields["resume_filename"] = fname
                pay_set_fields["resume_uploaded"] = True
                try:
                    from core.resume_service import fetch_resume_from_external_or_path, save_resume_to_gridfs
                    res_fetched = await fetch_resume_from_external_or_path(str(raw_res))
                    if res_fetched:
                        raw_b, fn, ct = res_fetched
                        fid, dl_url = await save_resume_to_gridfs(filename=fn, file_bytes=raw_b, content_type=ct, metadata={"source": f"{provider}_ingestion_cached"})
                        pay_set_fields["resume_file_id"] = fid
                        pay_set_fields["resume_filename"] = fn
                        pay_set_fields["resume_url"] = dl_url
                except Exception:
                    pass

            update_mongo: Dict[str, Any] = {}
            if pay_set_fields:
                update_mongo["$set"] = pay_set_fields
            if push_ops:
                update_mongo["$push"] = push_ops

            if update_mongo:
                await leads_col.update_one({"id": existing_lead["id"]}, update_mongo)
                await log_activity(
                    user_id="system",
                    user_name=f"{provider.capitalize()} Integration",
                    action="payment_updated",
                    entity_type="lead",
                    entity_id=existing_lead["id"],
                    details=f"Payment updated for {existing_lead.get('name')}: {pay_set_fields.get('payment_status')} ₹{pay_set_fields.get('amount_paid')}"
                )
                return {
                    "status": "updated",
                    "action": "payment_updated",
                    "lead_id": existing_lead["id"],
                    "lead_number": existing_lead.get("lead_number"),
                    "assigned_to": assigned_to,
                    "assigned_to_name": assigned_to_name,
                    "message": f"Updated lead {existing_lead.get('name')} with payment status: {pay_set_fields.get('payment_status')} (₹{pay_set_fields.get('amount_paid')})."
                }

        if provider == "calendly":
            # For Calendly bookings, always update the lead so it surfaces in All Leads
            rep_is_active = False
            if assigned_to:
                rep_user = await users_col.find_one({"id": assigned_to, "status": "active"})
                if rep_user:
                    rep_is_active = True
                    assigned_to_name = rep_user.get("name") or assigned_to_name

            # If not assigned or assigned user is inactive, assign to an active sales rep
            if not rep_is_active:
                target_reps = await users_col.find(
                    {
                        "status": "active",
                        "$or": [
                            {"role": {"$in": ["partner", "sr_sales_executive", "sales_executive", "sales_manager", "sales_rep", "sales_person", "sales", "internal_salesperson"]}},
                            {"rbac_role": {"$in": ["partner", "sr_sales_executive", "sales_executive", "sales_manager", "sales_rep", "sales_person", "sales", "internal_salesperson"]}}
                        ]
                    },
                    {"_id": 0, "id": 1, "name": 1}
                ).to_list(100)
                if target_reps:
                    last_idx = (integration or {}).get("round_robin_cursor", 0)
                    chosen_rep = target_reps[last_idx % len(target_reps)]
                    assigned_to = chosen_rep["id"]
                    assigned_to_name = chosen_rep["name"]
                    if integration_id:
                        await integrations_col.update_one(
                            {"id": integration_id},
                            {"$set": {"round_robin_cursor": last_idx + 1}}
                        )

            existing_source = (existing_lead.get("source") or "").strip()
            final_source = existing_source if existing_source and existing_source.lower() not in ["", "unknown", "none"] else SOURCE_CALENDLY

            booking_info = {
                "event_name": raw_lead.get("service_interested") or campaign,
                "notes": message
            }

            is_new_booking_for_lead = not existing_lead.get("has_booking")

            update_fields: Dict[str, Any] = {
                "has_booking": True,
                "source": final_source,
                "assigned_to": assigned_to,
                "assigned_to_name": assigned_to_name,
                "calendly_booking": booking_info,
                "booking_details": {
                    **booking_info,
                    "status": "scheduled"
                }
            }
            if is_new_booking_for_lead:
                update_fields["updated_at"] = now
                update_fields["last_contacted_at"] = now

            if phone and not existing_lead.get("phone"):
                update_fields["phone"] = phone
            if whatsapp_number and not existing_lead.get("whatsapp_number"):
                update_fields["whatsapp_number"] = whatsapp_number
            if city and not existing_lead.get("city"):
                update_fields["city"] = city
            if country and not existing_lead.get("country"):
                update_fields["country"] = country
                update_fields["country_of_interest"] = country

            update_op: Dict[str, Any] = {
                "$set": update_fields,
                "$addToSet": {"tags": "calendly"}
            }
            if is_new_booking_for_lead:
                note_entry = {
                    "id": str(uuid.uuid4()),
                    "text": f"Booked consultation via Calendly ({campaign}) on {now.strftime('%Y-%m-%d %H:%M:%S UTC')}.",
                    "author": "System (Calendly Integration)",
                    "created_at": now.isoformat()
                }
                update_op["$push"] = {"notes": note_entry}

            await leads_col.update_one(
                {"id": existing_lead["id"]},
                update_op
            )

            # Also update all duplicate/prior lead docs matching this email to show active booking
            clean_email = (existing_lead.get("email") or email or "").strip().lower()
            if clean_email and "@" in clean_email:
                await leads_col.update_many(
                    {"email": {"$regex": f"^{re.escape(clean_email)}$", "$options": "i"}},
                    {
                        "$set": {
                            "has_booking": True,
                            "calendly_booking": update_fields["calendly_booking"],
                            "booking_details": update_fields["booking_details"]
                        },
                        "$addToSet": {"tags": "calendly"}
                    }
                )

            return {
                "status": "updated",
                "action": "calendly_booking_updated",
                "lead_id": existing_lead["id"],
                "lead_number": existing_lead.get("lead_number"),
                "assigned_to": assigned_to,
                "assigned_to_name": assigned_to_name,
                "message": f"Updated existing lead {existing_lead.get('name')} with Calendly booking."
            }

        elif duplicate_strategy == "skip":
            recent_notes = [
                n.get("text", "") if isinstance(n, dict) else str(n)
                for n in (existing_lead.get("notes") or [])[-5:]
            ]
            dup_text_prefix = f"Duplicate inquiry received from {provider}"
            already_noted = any(dup_text_prefix in t for t in recent_notes)

            # If not noted recently, log a note without altering updated_at to prevent scrambling lead sort order
            if not already_noted:
                note_entry = {
                    "id": str(uuid.uuid4()),
                    "text": f"Duplicate inquiry received from {provider} ({campaign}) at {now.strftime('%Y-%m-%d %H:%M:%S UTC')}.",
                    "author": f"System ({provider} Integration)",
                    "created_at": now.isoformat()
                }
                await leads_col.update_one(
                    {"id": existing_lead["id"]},
                    {"$push": {"notes": note_entry}}
                )
            return {
                "status": "skipped",
                "action": "duplicate_skipped",
                "lead_id": existing_lead["id"],
                "lead_number": existing_lead.get("lead_number"),
                "assigned_to": assigned_to,
                "assigned_to_name": assigned_to_name,
                "message": f"Duplicate detected matching existing lead {existing_lead.get('name')}; enquiry appended to notes."
            }

        elif duplicate_strategy == "update_existing":
            # Check if there is genuine new information
            has_new_info = False
            update_fields: Dict[str, Any] = {}
            if city and city != existing_lead.get("city"):
                update_fields["city"] = city
                has_new_info = True
            if service and service not in (existing_lead.get("service_interested") or ""):
                update_fields["service_interested"] = service
                update_fields["service_type"] = service
                update_fields["services"] = service
                has_new_info = True
            if country and country != existing_lead.get("country"):
                update_fields["country"] = country
                update_fields["country_of_interest"] = country
                has_new_info = True

            # Check if this exact inquiry was already recorded in recent notes
            existing_notes_texts = [n.get("text", "") for n in (existing_lead.get("notes") or [])[-10:]]
            inquiry_note_sig = f"via {provider} ({campaign})"
            already_recorded = any(inquiry_note_sig in t for t in existing_notes_texts)

            if not has_new_info and already_recorded:
                # Lead is already up-to-date; do not alter updated_at to prevent scrambling CRM order
                return {
                    "status": "skipped",
                    "action": "duplicate_unchanged",
                    "lead_id": existing_lead["id"],
                    "lead_number": existing_lead.get("lead_number"),
                    "assigned_to": assigned_to,
                    "assigned_to_name": assigned_to_name,
                    "message": f"Lead {existing_lead.get('name')} data is already up-to-date; skipped."
                }

            update_fields["updated_at"] = now
            note_entry = {
                "id": str(uuid.uuid4()),
                "text": f"Lead re-engaged via {provider} ({campaign}). Service: {service or 'N/A'}. Notes: {message or 'No message'}",
                "author": f"System ({provider} Integration)",
                "created_at": now.isoformat()
            }
            await leads_col.update_one(
                {"id": existing_lead["id"]},
                {
                    "$set": update_fields,
                    "$push": {"notes": note_entry}
                }
            )
            return {
                "status": "updated",
                "action": "duplicate_updated",
                "lead_id": existing_lead["id"],
                "lead_number": existing_lead.get("lead_number"),
                "assigned_to": assigned_to,
                "assigned_to_name": assigned_to_name,
                "message": f"Updated existing lead {existing_lead.get('name')} with fresh inquiry data."
            }

    # 2. Determine lead assignment
    mode = assignment_rules.get("mode", "round_robin")
    if provider == "calendly" and mode == "unassigned":
        mode = "round_robin"
    assigned_to = None
    assigned_to_name = "Unassigned"

    if mode == "specific_rep" and assignment_rules.get("specific_rep_id"):
        rep_id = assignment_rules["specific_rep_id"]
        rep = await users_col.find_one({"id": rep_id}, {"_id": 0, "name": 1, "id": 1})
        if rep:
            assigned_to = rep["id"]
            assigned_to_name = rep.get("name", "Sales Representative")

    elif mode == "round_robin":
        rep_ids = assignment_rules.get("rep_ids") or []
        target_reps = []
        if rep_ids:
            target_reps = await users_col.find(
                {"id": {"$in": rep_ids}, "status": "active"},
                {"_id": 0, "id": 1, "name": 1}
            ).to_list(100)
        if not target_reps:
            # Fallback to active sales reps in company
            comp_filter: Dict[str, Any] = {
                "status": "active",
                "$or": [
                    {"role": {"$in": ["partner", "sr_sales_executive", "sales_executive", "sales_manager", "sales_rep", "sales_person", "sales", "internal_salesperson"]}},
                    {"rbac_role": {"$in": ["partner", "sr_sales_executive", "sales_executive", "sales_manager", "sales_rep", "sales_person", "sales", "internal_salesperson"]}}
                ]
            }
            target_reps = await users_col.find(comp_filter, {"_id": 0, "id": 1, "name": 1}).to_list(100)

        if target_reps:
            # Get current round-robin cursor
            last_idx = (integration or {}).get("round_robin_cursor", 0)
            chosen_rep = target_reps[last_idx % len(target_reps)]
            assigned_to = chosen_rep["id"]
            assigned_to_name = chosen_rep["name"]
            # Increment cursor
            if integration_id:
                await integrations_col.update_one(
                    {"id": integration_id},
                    {"$set": {"round_robin_cursor": last_idx + 1}}
                )

    # 3. Score & Category
    lead_doc = {
        "source": source,
        "email": email,
        "phone": phone,
        "country": country,
        "country_of_interest": country,
        "service_interested": service,
        "message": message
    }
    score, category = _calculate_score(lead_doc)
    lead_number = await _next_lead_number()

    # 4. Construct Lead Object
    tags = list(assignment_rules.get("default_tags") or [])
    tags.append(provider.lower())
    if existing_lead and duplicate_strategy == "flag_for_review":
        tags.append("duplicate_review_needed")

    new_lead = {
        "id": str(uuid.uuid4()),
        "company_id": company_id,
        "lead_number": lead_number,
        "name": name,
        "email": email,
        "phone": phone,
        "alternate_phone": str(raw_lead.get("alternate_phone") or "").strip(),
        "whatsapp_number": whatsapp_number,
        "address": str(raw_lead.get("address") or "").strip(),
        "city": city,
        "country": country,
        "country_of_interest": country,
        "service_interested": service or assignment_rules.get("default_service", "Immigration & Visa Consultation"),
        "service_type": service,
        "services": service,
        "budget": str(raw_lead.get("budget") or "₹75,000").strip(),
        "qualification": str(raw_lead.get("qualification") or "").strip(),
        "latest_qualification": str(raw_lead.get("qualification") or "").strip(),
        "work_experience": str(raw_lead.get("work_experience") or "").strip(),
        "total_work_experience": str(raw_lead.get("work_experience") or "").strip(),
        "unique_id": str(raw_lead.get("unique_id") or "").strip(),
        "message": message,
        "source": canonical_source,
        "original_source": original_source,
        "source_details": source_details,
        "campaign": campaign,
        "utm_source": source_details.get("utm_source") or raw_lead.get("utm_source", ""),
        "utm_medium": source_details.get("utm_medium") or raw_lead.get("utm_medium", ""),
        "utm_campaign": source_details.get("utm_campaign") or raw_lead.get("utm_campaign", ""),
        "stage": "new",
        "status": "new",
        "priority": raw_lead.get("priority", "medium"),
        "lead_score": score,
        "score_category": category,
        "assigned_to": assigned_to,
        "assigned_to_name": assigned_to_name,
        "created_by": f"integration:{provider}",
        "created_by_name": f"{provider.capitalize()} Integration",
        "integration_id": integration_id,
        "tags": list(set(tags)),
        "notes": [
            {
                "id": str(uuid.uuid4()),
                "text": f"Lead automatically ingested from {provider.capitalize()} ({campaign}).",
                "author": "System",
                "created_at": now.isoformat()
            }
        ] if not message else [
            {
                "id": str(uuid.uuid4()),
                "text": f"Lead automatically ingested from {provider.capitalize()} ({campaign}). Initial query: {message}",
                "author": "System",
                "created_at": now.isoformat()
            }
        ],
        "call_count": 0,
        "created_at": now,
        "updated_at": now,
        "converted": False
    }

    # Populate payment details if present in raw_lead
    incoming_pay_status = str(raw_lead.get("payment_status") or "").strip().lower()
    incoming_is_paid = bool(raw_lead.get("is_paid") or incoming_pay_status in ("paid", "success", "captured", "completed", "successful"))
    incoming_amt = raw_lead.get("amount_paid") or raw_lead.get("payment_amount")
    clean_amt = None
    if incoming_amt is not None and str(incoming_amt).strip():
        try:
            amt_str = re.sub(r"[^\d.]", "", str(incoming_amt))
            if amt_str:
                clean_amt = float(amt_str)
        except Exception:
            clean_amt = None

    if incoming_is_paid:
        paid_amt_val = clean_amt if clean_amt is not None else 2427.0
        new_lead["payment_status"] = "paid"
        new_lead["is_paid"] = True
        new_lead["amount_paid"] = paid_amt_val
        new_lead["payment_amount"] = paid_amt_val
        new_lead["fee_amount"] = paid_amt_val
        new_lead["payment_method"] = raw_lead.get("payment_method") or "online"
        new_lead["stage"] = "payment_done"
        new_lead["paid_at"] = raw_lead.get("payment_timestamp") or now.isoformat()
        new_lead["payment_date"] = raw_lead.get("payment_timestamp") or now.isoformat()
        pay_id = raw_lead.get("razorpay_payment_id") or raw_lead.get("payment_id") or f"sheet_{raw_lead.get('unique_id') or uuid.uuid4().hex[:8]}"
        new_lead["payment_history"] = [
            {
                "payment_id": pay_id,
                "amount": paid_amt_val,
                "method": new_lead["payment_method"],
                "status": "paid",
                "link_id": "pl_TZSVimtLKxHnHx",
                "created_at": new_lead["paid_at"],
                "source": f"{provider.capitalize()} ({campaign})"
            }
        ]
    elif incoming_pay_status == "failed":
        new_lead["payment_status"] = "failed"
        new_lead["is_paid"] = False
        new_lead["amount_paid"] = 0.0
        new_lead["payment_amount"] = clean_amt or 2427.0
        new_lead["fee_amount"] = clean_amt or 2427.0
        new_lead["payment_method"] = raw_lead.get("payment_method") or ""
        new_lead["last_payment_error"] = raw_lead.get("message") or "Payment attempt failed"
        new_lead["payment_history"] = [
            {
                "payment_id": raw_lead.get("razorpay_payment_id") or raw_lead.get("payment_id") or f"sheet_fail_{uuid.uuid4().hex[:8]}",
                "amount": clean_amt or 2427.0,
                "method": raw_lead.get("payment_method") or "online",
                "status": "failed",
                "link_id": "pl_TZSVimtLKxHnHx",
                "created_at": raw_lead.get("payment_timestamp") or now.isoformat(),
                "error_description": new_lead["last_payment_error"]
            }
        ]
    elif incoming_pay_status == "partially_paid":
        new_lead["payment_status"] = "partially_paid"
        new_lead["is_paid"] = False
        new_lead["amount_paid"] = clean_amt or 0.0
        new_lead["payment_amount"] = clean_amt or 2427.0
        new_lead["fee_amount"] = 2427.0
        new_lead["payment_method"] = raw_lead.get("payment_method") or ""
        new_lead["payment_history"] = []
    else:
        new_lead["payment_status"] = "unpaid"
        new_lead["is_paid"] = False
        new_lead["amount_paid"] = 0.0
        new_lead["payment_amount"] = clean_amt or 2427.0
        new_lead["fee_amount"] = 2427.0
        new_lead["payment_method"] = raw_lead.get("payment_method") or ""
        new_lead["payment_history"] = []

    raw_res = raw_lead.get("resume_url") or raw_lead.get("resume_path") or raw_lead.get("resume") or raw_lead.get("resume_link")
    if raw_res:
        clean_res = str(raw_res).strip()
        new_lead["resume_url"] = clean_res
        new_lead["resume_path"] = clean_res
        fname = raw_lead.get("resume_filename") or unquote(clean_res.split("/")[-1].split("?")[0]) or "resume.pdf"
        new_lead["resume_filename"] = fname
        new_lead["resume_uploaded"] = True
        try:
            from core.resume_service import fetch_resume_from_external_or_path, save_resume_to_gridfs
            res_fetched = await fetch_resume_from_external_or_path(clean_res)
            if res_fetched:
                raw_b, fn, ct = res_fetched
                fid, dl_url = await save_resume_to_gridfs(filename=fn, file_bytes=raw_b, content_type=ct, metadata={"source": f"{provider}_ingestion_cached"})
                new_lead["resume_file_id"] = fid
                new_lead["resume_filename"] = fn
                new_lead["resume_url"] = dl_url
        except Exception as e:
            logger.warning(f"Could not immediately cache resume during ingestion: {e}")

    if provider == "calendly":
        new_lead["has_booking"] = True
        new_lead["calendly_booking"] = {
            "event_name": service or campaign,
            "notes": message
        }
        if "calendly" not in new_lead["tags"]:
            new_lead["tags"].append("calendly")

    await leads_col.insert_one(new_lead)

    # Sync to connected Google Sheets in real-time (if provider is not google_sheets to prevent loop)
    if provider != "google_sheets":
        try:
            from services.integrations.google_services import sync_lead_to_connected_sheets
            await sync_lead_to_connected_sheets(new_lead)
        except Exception:
            pass

    # 5. Activity log & Rep Notification
    await log_activity(
        user_id="system",
        user_name=f"{provider.capitalize()} Integration",
        action="lead_created",
        entity_type="lead",
        entity_id=new_lead["id"],
        details=f"New lead {name} ({lead_number}) imported via {provider} ({campaign}). Assigned: {assigned_to_name}."
    )

    if assigned_to:
        await create_notification(
            user_id=assigned_to,
            title=f"New {provider.capitalize()} Lead Assigned",
            message=f"You have been assigned {name} ({phone or email}) from {provider}.",
            notification_type="lead_assigned",
            related_id=new_lead["id"]
        )

    # 6. Update integration metric
    if integration_id:
        await integrations_col.update_one(
            {"id": integration_id},
            {
                "$inc": {"total_leads_synced": 1},
                "$set": {
                    "last_sync_at": now,
                    "last_sync_status": "success",
                    "last_sync_message": f"Successfully ingested lead {name} ({lead_number})"
                }
            }
        )

    return {
        "status": "created",
        "action": "lead_created",
        "lead_id": new_lead["id"],
        "lead_number": lead_number,
        "assigned_to_name": assigned_to_name,
        "message": f"Successfully captured lead {name} ({lead_number})."
    }
