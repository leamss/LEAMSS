"""Bidirectional Mailbox IMAP Synchronization for LEAMSS CRM.

Synchronizes:
1. Inbound client email replies from INBOX
2. Outbound replies sent directly from email client (Gmail/Outlook) from Sent Mail

Features:
- Auto-resolves IMAP host/port from user's mailbox settings (Gmail, Outlook, Zoho, etc.)
- Multi-tier thread matching: In-Reply-To -> References -> Normalized Subject -> Client Email
- Strict deduplication: Checks Message-ID, in_reply_to, and timestamp fingerprinting
- Automatic association with Leads or Clients in CRM
- Activity logging and salesperson notifications
"""
import asyncio
import email
import email.message
from email.header import decode_header
import email.utils
import imaplib
import logging
import re
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("mail_sync")


def _decode_header(raw: Optional[str]) -> str:
    """Decode RFC 2047 encoded email header text safely."""
    if not raw:
        return ""
    try:
        parts = decode_header(raw)
        out = []
        for b, enc in parts:
            if isinstance(b, bytes):
                out.append(b.decode(enc or "utf-8", errors="replace"))
            else:
                out.append(str(b))
        return "".join(out).strip()
    except Exception:
        return str(raw).strip()


def _clean_email_addr(raw: Optional[str]) -> str:
    """Extract clean lowercase email address from 'Name <email@domain.com>' string."""
    if not raw:
        return ""
    match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", raw)
    if match:
        return match.group(0).lower().strip()
    return raw.replace("<", "").replace(">", "").lower().strip()


def _clean_sender_name(raw: Optional[str]) -> str:
    """Extract human-readable sender name from 'Name <email@domain.com>'."""
    if not raw:
        return ""
    decoded = _decode_header(raw)
    if "<" in decoded:
        name_part = decoded.split("<")[0].strip(' "')
        if name_part:
            return name_part
    return _clean_email_addr(raw)


def _normalize_subject(subj: str) -> str:
    """Normalize subject line by stripping Re:, Fwd:, and brackets."""
    if not subj:
        return ""
    cleaned = re.sub(r"^(re|fwd|fw|aw|antw|wg)\s*:\s*", "", subj, flags=re.IGNORECASE)
    cleaned = re.sub(r"^(re|fwd|fw|aw|antw|wg)\s*\[\d+\]\s*:\s*", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def _extract_body(msg: email.message.Message) -> Tuple[str, str]:
    """Extract HTML and plain text bodies from an email message."""
    html_body = ""
    text_body = ""

    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            cdispo = str(part.get("Content-Disposition") or "")
            if "attachment" in cdispo:
                continue

            try:
                payload = part.get_payload(decode=True)
                if not payload:
                    continue
                charset = part.get_content_charset() or "utf-8"
                decoded_str = payload.decode(charset, errors="replace")
            except Exception:
                continue

            if ctype == "text/html" and not html_body:
                html_body = decoded_str
            elif ctype == "text/plain" and not text_body:
                text_body = decoded_str
    else:
        try:
            payload = msg.get_payload(decode=True)
            charset = msg.get_content_charset() or "utf-8"
            decoded_str = payload.decode(charset, errors="replace") if payload else ""
            if msg.get_content_type() == "text/html":
                html_body = decoded_str
            else:
                text_body = decoded_str
        except Exception:
            text_body = str(msg.get_payload() or "")

    # Format fallback HTML if only plain text is available
    if not html_body and text_body:
        paras = "".join(f"<p style='margin:0 0 10px; line-height:1.5;'>{p}</p>" for p in text_body.split("\n\n") if p.strip())
        html_body = f"<div style='font-family: Arial, sans-serif; font-size: 13px; color: #1e293b;'>{paras}</div>"

    return html_body, text_body


def _resolve_imap_server(smtp_host: str) -> Tuple[str, int]:
    """Derive IMAP server host and SSL port from SMTP host."""
    host_lower = (smtp_host or "").lower().strip()
    if "gmail" in host_lower or "google" in host_lower:
        return "imap.gmail.com", 993
    if "office365" in host_lower or "outlook" in host_lower:
        return "outlook.office365.com", 993
    if "zoho" in host_lower:
        return "imap.zoho.com", 993
    # Fallback heuristic
    if host_lower.startswith("smtp."):
        return host_lower.replace("smtp.", "imap."), 993
    return "imap.gmail.com", 993


def _find_sent_folder(mail: imaplib.IMAP4_SSL) -> Optional[str]:
    """Find the valid Sent folder in the IMAP mailbox."""
    candidates = [
        '"[Gmail]/Sent Mail"',
        '[Gmail]/Sent Mail',
        '"Sent"',
        'Sent',
        '"Sent Messages"',
        'Sent Messages',
        '"Sent Items"',
        'Sent Items',
    ]
    for cand in candidates:
        try:
            status, _ = mail.select(cand, readonly=True)
            if status == "OK":
                return cand
        except Exception:
            continue
    return None


async def sync_user_mailbox(
    user_id: str,
    target_contact_email: Optional[str] = None,
    limit: int = 40,
) -> Dict[str, Any]:
    """Synchronize both incoming replies and sent replies for a specific user's mailbox.

    Returns:
      {
        "success": bool,
        "synced_inbound": int,
        "synced_outbound": int,
        "total_synced": int,
        "message": str
      }
    """
    from core.database import db

    # 1. Fetch user doc & mailbox credentials
    user_doc = await db["users"].find_one({"id": user_id})
    if not user_doc:
        user_doc = await db["users"].find_one({"email": user_id})
    if not user_doc:
        return {"success": False, "error": "User not found", "synced_inbound": 0, "synced_outbound": 0}

    mb = user_doc.get("mailbox_settings") or {}
    smtp_user = (mb.get("smtp_user") or user_doc.get("email") or "").strip()
    smtp_pass = (mb.get("smtp_pass") or "").replace(" ", "").strip()
    smtp_host = mb.get("smtp_host", "smtp.gmail.com")

    if not smtp_user or not smtp_pass:
        return {
            "success": False,
            "status": "unconfigured",
            "message": "Mailbox password/credentials not configured yet for this user.",
            "synced_inbound": 0,
            "synced_outbound": 0,
            "total_synced": 0,
        }

    imap_host, imap_port = _resolve_imap_server(smtp_host)

    # 2. Build fast lookup of known leads and clients
    contact_query = {}
    if target_contact_email:
        clean_target = _clean_email_addr(target_contact_email)
        contact_query["email"] = {"$regex": f"^{re.escape(clean_target)}$", "$options": "i"}

    known_leads = {}
    async for l in db["leads"].find(contact_query, {"id": 1, "name": 1, "email": 1, "assigned_to": 1}):
        if l.get("email"):
            known_leads[l["email"].lower().strip()] = l

    known_clients = {}
    async for c in db["users"].find(contact_query, {"id": 1, "name": 1, "email": 1}):
        if c.get("email"):
            known_clients[c["email"].lower().strip()] = c

    # Merge contact emails set
    known_contact_emails = set(known_leads.keys()) | set(known_clients.keys())
    if target_contact_email:
        known_contact_emails.add(_clean_email_addr(target_contact_email))

    # Also build index of existing threads in crm_emails to connect replies
    known_threads_by_msg_id = {}
    known_threads_by_subject = {}
    known_thread_notify_by_id = {}
    async for e in db["crm_emails"].find({}, {
        "id": 1, "thread_id": 1, "message_id": 1, "lead_id": 1, "client_id": 1,
        "subject": 1, "from_email": 1, "to_email": 1, "notify_by_email": 1, "direction": 1,
    }).sort("created_at", 1):
        t_id = e.get("thread_id") or e.get("id")
        m_id = (e.get("message_id") or "").strip("<> ").strip()
        if m_id:
            known_threads_by_msg_id[m_id] = e
        
        # Norm subject + contact key
        contact_e = _clean_email_addr(e.get("to_email") if e.get("direction") == "outbound" else e.get("from_email"))
        norm_subj = _normalize_subject(e.get("subject", ""))
        if norm_subj and contact_e:
            known_threads_by_subject[(norm_subj, contact_e)] = e

        if t_id and e.get("notify_by_email") is not None:
            known_thread_notify_by_id[t_id] = bool(e.get("notify_by_email"))

    # 3. Connect to IMAP in worker thread
    def _run_imap_sync():
        synced_inbound_msgs = []
        synced_outbound_msgs = []
        try:
            mail = imaplib.IMAP4_SSL(imap_host, imap_port, timeout=25)
            mail.login(smtp_user, smtp_pass)
        except Exception as e:
            logger.warning("IMAP connection/login failed for %s on %s: %s", smtp_user, imap_host, e)
            return {"error": str(e), "inbound": [], "outbound": []}

        try:
            # ────────────────────────────────────────────────────────────
            # A. SYNC INBOX (Incoming client replies)
            # ────────────────────────────────────────────────────────────
            # Select INBOX as read-write to archive messages when notify_by_email is False
            status, _ = mail.select("INBOX", readonly=False)
            if status == "OK":
                search_criteria = "ALL"
                if target_contact_email:
                    search_criteria = f'(FROM "{_clean_email_addr(target_contact_email)}")'

                status, data = mail.search(None, search_criteria)
                if status == "OK" and data and data[0]:
                    msg_ids = data[0].split()
                    uids_to_archive = []
                    # Inspect recent messages up to limit
                    for num in msg_ids[-limit:]:
                        try:
                            _, fetch_data = mail.fetch(num, "(RFC822)")
                            if not fetch_data or not fetch_data[0] or not isinstance(fetch_data[0], tuple):
                                continue
                            raw_email = fetch_data[0][1]
                            parsed_msg = email.message_from_bytes(raw_email)

                            from_hdr = _decode_header(parsed_msg.get("From"))
                            from_addr = _clean_email_addr(from_hdr)
                            to_hdr = _decode_header(parsed_msg.get("To"))
                            to_addr = _clean_email_addr(to_hdr)
                            subj = _decode_header(parsed_msg.get("Subject"))
                            msg_id_hdr = (parsed_msg.get("Message-ID") or f"<gen_{num.decode()}@imap>").strip()
                            in_reply_to_hdr = (parsed_msg.get("In-Reply-To") or "").strip()
                            refs_hdr = (parsed_msg.get("References") or "").strip()
                            date_hdr = parsed_msg.get("Date")

                            # Parse date
                            parsed_dt = datetime.now(timezone.utc)
                            if date_hdr:
                                try:
                                    parsed_tuple = email.utils.parsedate_to_datetime(date_hdr)
                                    if parsed_tuple:
                                        parsed_dt = parsed_tuple.astimezone(timezone.utc)
                                except Exception:
                                    pass

                            # Check if sender is a known CRM contact or replies to our CRM message
                            is_known_contact = from_addr in known_contact_emails
                            in_reply_clean = in_reply_to_hdr.strip("<> ")
                            is_reply_to_us = any(
                                ref_id in known_threads_by_msg_id
                                for ref_id in ([in_reply_clean] + [r.strip("<> ") for r in refs_hdr.split()])
                                if ref_id
                            )

                            if is_known_contact or is_reply_to_us:
                                html_b, text_b = _extract_body(parsed_msg)

                                # Check notify_by_email preference for this conversation
                                # Default is False (only in CRM, keep Gmail inbox clean)
                                notify = False
                                parent_e = None
                                for ref_id in ([in_reply_clean] + [r.strip("<> ") for r in refs_hdr.split()]):
                                    if ref_id and ref_id in known_threads_by_msg_id:
                                        parent_e = known_threads_by_msg_id[ref_id]
                                        break
                                if parent_e:
                                    t_id = parent_e.get("thread_id") or parent_e.get("id")
                                    notify = bool(parent_e.get("notify_by_email", False)) or known_thread_notify_by_id.get(t_id, False)
                                else:
                                    norm_s = _normalize_subject(subj)
                                    if (norm_s, from_addr) in known_threads_by_subject:
                                        parent_e = known_threads_by_subject[(norm_s, from_addr)]
                                        t_id = parent_e.get("thread_id") or parent_e.get("id")
                                        notify = bool(parent_e.get("notify_by_email", False)) or known_thread_notify_by_id.get(t_id, False)

                                synced_inbound_msgs.append({
                                    "message_id": msg_id_hdr,
                                    "in_reply_to": in_reply_to_hdr,
                                    "references": refs_hdr,
                                    "from_email": from_addr,
                                    "from_name": _clean_sender_name(from_hdr),
                                    "to_email": to_addr or smtp_user,
                                    "subject": subj,
                                    "body_html": html_b,
                                    "raw_text": text_b,
                                    "sent_at": parsed_dt,
                                    "direction": "inbound",
                                    "notify_by_email": notify,
                                })

                                # If notify is False, archive this message from Gmail INBOX
                                if not notify:
                                    uids_to_archive.append(num)
                            elif "mailer-daemon" in from_addr.lower() or "postmaster" in from_addr.lower() or "delivery status notification" in subj.lower():
                                # Automatically sweep bounce/failure notifications from INBOX
                                uids_to_archive.append(num)
                        except Exception as parse_err:
                            logger.debug("Error parsing inbox message: %s", parse_err)
                            continue

                    # Archive queued messages from INBOX so they don't clutter Gmail inbox
                    if uids_to_archive:
                        for mid in uids_to_archive:
                            try:
                                # Native Gmail label removal: removes \Inbox label so it immediately vanishes from user's Gmail Inbox
                                mail.store(mid, "-X-GM-LABELS", "\\Inbox")
                            except Exception as lbl_err:
                                logger.debug("Error removing \\Inbox label on mid %s: %s", mid, lbl_err)
                            try:
                                mail.store(mid, "+FLAGS", "\\Deleted")
                            except Exception as st_err:
                                logger.debug("Error setting Deleted flag on mid %s: %s", mid, st_err)
                        try:
                            mail.expunge()
                            logger.info("Archived %d client replies from INBOX (notify_by_email=False)", len(uids_to_archive))
                        except Exception as exp_err:
                            logger.warning("Error expunging archived messages: %s", exp_err)

            # ────────────────────────────────────────────────────────────
            # B. SYNC SENT MAIL (Outbound replies sent directly from email client)
            # ────────────────────────────────────────────────────────────
            sent_folder = _find_sent_folder(mail)
            if sent_folder:
                status, _ = mail.select(sent_folder, readonly=False)
                if status == "OK":
                    search_criteria = "ALL"
                    if target_contact_email:
                        search_criteria = f'(TO "{_clean_email_addr(target_contact_email)}")'

                    status, s_data = mail.search(None, search_criteria)
                    if status == "OK" and s_data and s_data[0]:
                        s_ids = s_data[0].split()
                        uids_to_purge_sent = []
                        for num in s_ids[-limit:]:
                            try:
                                _, fetch_data = mail.fetch(num, "(RFC822)")
                                if not fetch_data or not fetch_data[0] or not isinstance(fetch_data[0], tuple):
                                    continue
                                raw_email = fetch_data[0][1]
                                parsed_msg = email.message_from_bytes(raw_email)

                                to_hdr = _decode_header(parsed_msg.get("To"))
                                to_addr = _clean_email_addr(to_hdr)
                                from_hdr = _decode_header(parsed_msg.get("From"))
                                from_addr = _clean_email_addr(from_hdr)
                                subj = _decode_header(parsed_msg.get("Subject"))
                                msg_id_hdr = (parsed_msg.get("Message-ID") or f"<sent_{num.decode()}@imap>").strip()
                                in_reply_to_hdr = (parsed_msg.get("In-Reply-To") or "").strip()
                                refs_hdr = (parsed_msg.get("References") or "").strip()
                                date_hdr = parsed_msg.get("Date")

                                parsed_dt = datetime.now(timezone.utc)
                                if date_hdr:
                                    try:
                                        parsed_tuple = email.utils.parsedate_to_datetime(date_hdr)
                                        if parsed_tuple:
                                            parsed_dt = parsed_tuple.astimezone(timezone.utc)
                                    except Exception:
                                        pass

                                is_known_contact = to_addr in known_contact_emails
                                in_reply_clean = in_reply_to_hdr.strip("<> ")
                                is_reply_to_us = any(
                                    ref_id in known_threads_by_msg_id
                                    for ref_id in ([in_reply_clean] + [r.strip("<> ") for r in refs_hdr.split()])
                                    if ref_id
                                )

                                # If this message is a CRM-sent email where notify_by_email is False,
                                # mark it to be purged from Gmail Sent folder so Sent stays clean!
                                clean_msg_id = msg_id_hdr.strip("<> ")
                                if clean_msg_id in known_threads_by_msg_id:
                                    c_doc = known_threads_by_msg_id[clean_msg_id]
                                    if not c_doc.get("notify_by_email", False):
                                        uids_to_purge_sent.append(num)

                                if is_known_contact or is_reply_to_us:
                                    html_b, text_b = _extract_body(parsed_msg)
                                    synced_outbound_msgs.append({
                                        "message_id": msg_id_hdr,
                                        "in_reply_to": in_reply_to_hdr,
                                        "references": refs_hdr,
                                        "from_email": from_addr or smtp_user,
                                        "from_name": _clean_sender_name(from_hdr) or user_doc.get("name"),
                                        "to_email": to_addr,
                                        "subject": subj,
                                        "body_html": html_b,
                                        "raw_text": text_b,
                                        "sent_at": parsed_dt,
                                        "direction": "outbound",
                                    })
                            except Exception as parse_err:
                                logger.debug("Error parsing sent message: %s", parse_err)
                                continue

                        if uids_to_purge_sent:
                            for mid in uids_to_purge_sent:
                                try:
                                    mail.store(mid, "-X-GM-LABELS", "\\Sent")
                                    mail.store(mid, "+FLAGS", "\\Deleted")
                                except Exception:
                                    pass
                            try:
                                mail.expunge()
                                logger.info("Purged %d non-notified CRM outbound emails from Sent Mail", len(uids_to_purge_sent))
                            except Exception:
                                pass

            mail.logout()
        except Exception as e:
            logger.warning("Error during IMAP sync process: %s", e)

        return {"error": None, "inbound": synced_inbound_msgs, "outbound": synced_outbound_msgs}

    # Execute IMAP reading in non-blocking thread
    raw_results = await asyncio.to_thread(_run_imap_sync)
    if raw_results.get("error"):
        err_msg = str(raw_results["error"])
        if "AUTHENTICATIONFAILED" in err_msg or "Invalid credentials" in err_msg:
            now_iso = datetime.now(timezone.utc).isoformat()
            await db["users"].update_many(
                {"$or": [{"id": user_doc.get("id")}, {"email": user_doc.get("email")}]},
                {"$set": {
                    "mailbox_settings.last_test_status": "failed",
                    "mailbox_settings.last_test_message": "Google IMAP authentication failed. Please update your 16-character App Password.",
                    "mailbox_settings.last_synced_at": now_iso,
                    "mailbox_settings.last_sync_status": "failed",
                }}
            )
        return {
            "success": False,
            "error": raw_results["error"],
            "message": f"Mailbox sync failed: {raw_results['error']}",
            "synced_inbound": 0,
            "synced_outbound": 0,
            "total_synced": 0,
        }

    inbound_items = raw_results.get("inbound") or []
    outbound_items = raw_results.get("outbound") or []

    synced_inbound_count = 0
    synced_outbound_count = 0

    from core.services import create_notification, log_activity

    # 4. Ingest and match each message into crm_emails with zero duplicates
    all_items = inbound_items + outbound_items
    for item in all_items:
        clean_msg_id = item["message_id"].strip("<> ").strip()

        # Strict duplicate check
        existing = await db["crm_emails"].find_one({
            "$or": [
                {"message_id": item["message_id"]},
                {"message_id": f"<{clean_msg_id}>"},
                {"message_id": clean_msg_id},
            ]
        })
        if existing:
            continue

        # Secondary duplicate check by (from_email, to_email, subject, sent_at within 45s)
        time_low = item["sent_at"] - timedelta(seconds=45)
        time_high = item["sent_at"] + timedelta(seconds=45)
        near_dup = await db["crm_emails"].find_one({
            "from_email": item["from_email"],
            "to_email": item["to_email"],
            "subject": item["subject"],
            "sent_at": {"$gte": time_low, "$lte": time_high},
        })
        if near_dup:
            continue

        # Determine thread_id, lead_id, and client_id
        target_thread_id = None
        target_lead_id = None
        target_client_id = None

        # Tier 1: Check In-Reply-To / References match against known threads
        clean_in_reply = item["in_reply_to"].strip("<> ")
        all_refs = [clean_in_reply] + [r.strip("<> ") for r in item.get("references", "").split() if r.strip()]
        for ref in all_refs:
            if ref and ref in known_threads_by_msg_id:
                parent = known_threads_by_msg_id[ref]
                target_thread_id = parent.get("thread_id") or parent.get("id")
                target_lead_id = parent.get("lead_id")
                target_client_id = parent.get("client_id")
                break

        # Tier 2: Check normalized subject + contact email match
        contact_key_email = item["from_email"] if item["direction"] == "inbound" else item["to_email"]
        if not target_thread_id:
            norm_s = _normalize_subject(item["subject"])
            if (norm_s, contact_key_email) in known_threads_by_subject:
                parent = known_threads_by_subject[(norm_s, contact_key_email)]
                target_thread_id = parent.get("thread_id") or parent.get("id")
                target_lead_id = target_lead_id or parent.get("lead_id")
                target_client_id = target_client_id or parent.get("client_id")

        # Tier 3: Resolve lead_id / client_id from known contacts lookup
        if not target_lead_id and not target_client_id:
            if contact_key_email in known_leads:
                target_lead_id = known_leads[contact_key_email]["id"]
            elif contact_key_email in known_clients:
                target_client_id = known_clients[contact_key_email]["id"]
            else:
                # Query db directly in case created recently
                lead_cand = await db["leads"].find_one({"email": {"$regex": f"^{re.escape(contact_key_email)}$", "$options": "i"}})
                if lead_cand:
                    target_lead_id = lead_cand["id"]
                else:
                    client_cand = await db["users"].find_one({"email": {"$regex": f"^{re.escape(contact_key_email)}$", "$options": "i"}})
                    if client_cand:
                        target_client_id = client_cand["id"]

        # If still no thread_id, create new thread_id for this conversation
        if not target_thread_id:
            target_thread_id = str(uuid.uuid4())

        # Determine notify_by_email flag
        item_notify = item.get("notify_by_email")
        if item_notify is None and target_thread_id:
            item_notify = known_thread_notify_by_id.get(target_thread_id, False)
        item_notify = bool(item_notify)

        new_email_id = str(uuid.uuid4())
        doc_to_insert = {
            "id": new_email_id,
            "lead_id": target_lead_id,
            "client_id": target_client_id,
            "thread_id": target_thread_id,
            "message_id": item["message_id"],
            "in_reply_to": item["in_reply_to"] or None,
            "direction": item["direction"],
            "to_email": item["to_email"],
            "contact_name": item["from_name"] if item["direction"] == "inbound" else item.get("to_name", item["to_email"]),
            "from_email": item["from_email"],
            "notify_by_email": item_notify,
            "sales_person_id": user_doc["id"],
            "sales_person_name": user_doc.get("name") or (item["from_name"] if item["direction"] == "outbound" else "Salesperson"),
            "subject": item["subject"],
            "body_html": item["body_html"],
            "raw_text": item["raw_text"],
            "status": "received" if item["direction"] == "inbound" else "delivered",
            "delivery_provider": "personal_mailbox_sync",
            "delivery_info": "Synced to CRM (Gmail notification enabled)" if item_notify else "Synced to CRM (Archived from Gmail Inbox)",
            "read": item["direction"] == "outbound",
            "sent_at": item["sent_at"],
            "created_at": item["sent_at"],
        }
        await db["crm_emails"].insert_one(doc_to_insert)

        # Update cache for chaining subsequent replies in this same batch
        known_threads_by_msg_id[clean_msg_id] = doc_to_insert
        norm_s = _normalize_subject(item["subject"])
        if norm_s:
            known_threads_by_subject[(norm_s, contact_key_email)] = doc_to_insert

        # Increment count
        if item["direction"] == "inbound":
            synced_inbound_count += 1
            # Log activity & send notification
            if target_lead_id or target_client_id:
                await log_activity(
                    user_id=user_doc["id"],
                    user_name=item["from_name"] or item["from_email"],
                    action="email_reply_received",
                    entity_type="lead" if target_lead_id else "client",
                    entity_id=target_lead_id or target_client_id,
                    details=f"Received client reply from {item['from_name']} ({item['from_email']}): {item['subject']}",
                )
                try:
                    from services.salesperson_activity_service import log_salesperson_activity
                    await log_salesperson_activity(
                        db=db,
                        salesperson_id=user_doc["id"],
                        salesperson_name=user_doc.get("name") or "Salesperson",
                        salesperson_email=user_doc.get("email"),
                        salesperson_role=user_doc.get("rbac_role") or user_doc.get("role"),
                        activity_type="email",
                        client_id=target_lead_id or target_client_id,
                        client_name=item["from_name"] if item["direction"] == "inbound" else item.get("to_name", item["to_email"]),
                        client_email=item["from_email"],
                        title=f"Email (Received): {item['subject']} - {item['from_name'] or item['from_email']}",
                        details=f"Received email reply from {item['from_name'] or item['from_email']}: {item['subject']}",
                        metadata={
                            "subject": item["subject"],
                            "direction": "received",
                            "status": "received",
                            "from_email": item["from_email"],
                            "to_email": item["to_email"],
                            "message_id": item["message_id"]
                        }
                    )
                except Exception as e_act:
                    logger.debug(f"Could not log inbound email to salesperson audit: {e_act}")
                await create_notification(
                    user_id=user_doc["id"],
                    title="Client Email Reply Received",
                    message=f"{item['from_name'] or item['from_email']} replied: '{item['subject']}'",
                    notification_type="email_reply",
                    related_id=target_lead_id or target_client_id,
                )
        else:
            synced_outbound_count += 1
            if target_lead_id or target_client_id:
                await log_activity(
                    user_id=user_doc["id"],
                    user_name=item["from_name"] or user_doc.get("name", "Sales Person"),
                    action="email_sent",
                    entity_type="lead" if target_lead_id else "client",
                    entity_id=target_lead_id or target_client_id,
                    details=f"Email reply sent to {item['to_email']}: {item['subject']}",
                )

    # Update last sync timestamp in user doc
    now_iso = datetime.now(timezone.utc).isoformat()
    await db["users"].update_one(
        {"id": user_doc["id"]},
        {"$set": {
            "mailbox_settings.last_synced_at": now_iso,
            "mailbox_settings.last_sync_status": "success",
            "mailbox_settings.last_sync_inbound": synced_inbound_count,
            "mailbox_settings.last_sync_outbound": synced_outbound_count,
        }}
    )

    total = synced_inbound_count + synced_outbound_count
    return {
        "success": True,
        "synced_inbound": synced_inbound_count,
        "synced_outbound": synced_outbound_count,
        "total_synced": total,
        "message": f"Successfully synchronized {total} new message(s) ({synced_inbound_count} incoming, {synced_outbound_count} outgoing)",
    }
