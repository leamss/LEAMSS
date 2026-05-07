"""Legal Archive — searchable index of consents, signatures, invoices for compliance audit.

Endpoints:
  GET  /api/legal-archive/search   — unified search across all 3 record types
  GET  /api/legal-archive/stats    — counts per type
  GET  /api/legal-archive/{ref_id} — fetch full record by reference_id
"""
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from core.database import db
from routers.auth import get_current_user
from core.integrity import compute_hash, verify_hash

router = APIRouter(prefix="/legal-archive", tags=["Legal Archive"])

consent_col = db["proposal_consent_emails"]
signatures_col = db["pa_signatures"]
invoices_col = db["pa_invoices"]
pa_col = db["pre_assessments"]


def _admin_only(current_user: dict):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only — Legal Archive is restricted to compliance officers")


def _iso(v):
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return v


@router.get("/stats")
async def legal_stats(current_user: dict = Depends(get_current_user)):
    _admin_only(current_user)
    consents = await consent_col.count_documents({})
    sigs = await signatures_col.count_documents({})
    invs = await invoices_col.count_documents({})
    return {
        "consents": consents,
        "signatures": sigs,
        "invoices": invs,
        "total": consents + sigs + invs,
    }


@router.get("/search")
async def legal_search(
    q: str = Query("", description="Free text — searches client name/email, ref_id, pa_number"),
    record_type: Optional[str] = Query("all", description="all | consent | signature | invoice"),
    start_date: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    limit: int = Query(100, ge=1, le=500),
    current_user: dict = Depends(get_current_user),
):
    """Unified search returning a single sorted timeline of records."""
    _admin_only(current_user)
    q_lower = (q or "").strip().lower()

    # Date filter
    date_q = {}
    if start_date:
        try:
            date_q["$gte"] = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
        except Exception:
            pass
    if end_date:
        try:
            date_q["$lt"] = datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc)
        except Exception:
            pass

    results = []

    async def _hydrate_pa(pa_id):
        if not pa_id:
            return {}
        pa = await pa_col.find_one({"id": pa_id}, {"_id": 0, "client_name": 1, "client_email": 1,
                                                    "partner_name": 1, "country": 1, "service_type": 1,
                                                    "pa_number": 1})
        return pa or {}

    def _matches(text: str):
        if not q_lower:
            return True
        return q_lower in (text or "").lower()

    # ===== CONSENTS =====
    if record_type in ("all", "consent"):
        cq = {"created_at": date_q} if date_q else {}
        cursor = consent_col.find(cq, {"_id": 0}).sort("created_at", -1).to_list(limit)
        consents = await cursor
        for c in consents:
            pa = await _hydrate_pa(c.get("pre_assessment_id"))
            haystack = " ".join([
                c.get("reference_id") or "", c.get("to_name") or "", c.get("to_email") or "",
                c.get("partner_name") or "", c.get("pa_number") or "",
                pa.get("client_name") or "", pa.get("client_email") or "",
            ])
            if not _matches(haystack):
                continue
            body = c.get("body_snapshot") or {}
            integrity = verify_hash("consent", c)
            results.append({
                "type": "consent",
                "id": c.get("id"),
                "reference_id": c.get("reference_id"),
                "pa_id": c.get("pre_assessment_id"),
                "pa_number": c.get("pa_number"),
                "client_name": c.get("to_name") or pa.get("client_name"),
                "client_email": c.get("to_email") or pa.get("client_email"),
                "partner_name": c.get("partner_name") or pa.get("partner_name"),
                "country": pa.get("country"),
                "service_type": pa.get("service_type"),
                "amount": body.get("final_amount"),
                "timestamp": _iso(c.get("created_at")),
                "channel": c.get("channel"),
                "mode": c.get("mode"),
                "integrity_status": integrity["status"],
                "integrity_hash": (c.get("integrity_hash") or "")[:12],
                "preview": {
                    "base_fee": body.get("base_fee"),
                    "promo_code": body.get("promo_code"),
                    "promo_discount": body.get("promo_discount"),
                    "custom_discount": body.get("custom_discount"),
                    "upsells": body.get("upsells") or [],
                    "upsell_total": body.get("upsell_total"),
                    "final_amount": body.get("final_amount"),
                },
            })

    # ===== SIGNATURES =====
    if record_type in ("all", "signature"):
        sq = {"signed_at": date_q} if date_q else {}
        sigs = await signatures_col.find(sq, {"_id": 0}).sort("signed_at", -1).to_list(limit)
        for s in sigs:
            pa = await _hydrate_pa(s.get("pre_assessment_id"))
            haystack = " ".join([
                s.get("typed_name") or "", s.get("user_email") or "",
                pa.get("client_name") or "", pa.get("client_email") or "",
                pa.get("pa_number") or "",
            ])
            if not _matches(haystack):
                continue
            integrity = verify_hash("signature", s)
            results.append({
                "type": "signature",
                "id": s.get("id"),
                "reference_id": f"SIG-{(pa.get('pa_number') or '')}-{s.get('id', '')[:6].upper()}",
                "pa_id": s.get("pre_assessment_id"),
                "pa_number": pa.get("pa_number"),
                "client_name": s.get("typed_name") or pa.get("client_name"),
                "client_email": s.get("user_email") or pa.get("client_email"),
                "partner_name": pa.get("partner_name"),
                "country": pa.get("country"),
                "service_type": pa.get("service_type"),
                "timestamp": _iso(s.get("signed_at")),
                "ip_address": s.get("ip_address"),
                "user_agent": (s.get("user_agent") or "")[:80],
                "file_size": s.get("file_size"),
                "integrity_status": integrity["status"],
                "integrity_hash": (s.get("integrity_hash") or "")[:12],
            })

    # ===== INVOICES =====
    if record_type in ("all", "invoice"):
        iq = {"sent_at": date_q} if date_q else {}
        invs = await invoices_col.find(iq, {"_id": 0}).sort("sent_at", -1).to_list(limit)
        for inv in invs:
            pa = await _hydrate_pa(inv.get("pre_assessment_id"))
            haystack = " ".join([
                inv.get("reference_id") or "", inv.get("client_name") or "",
                inv.get("client_email") or "", pa.get("client_name") or "",
                pa.get("pa_number") or "",
            ])
            if not _matches(haystack):
                continue
            integrity = verify_hash("invoice", inv)
            results.append({
                "type": "invoice",
                "id": inv.get("id"),
                "reference_id": inv.get("reference_id"),
                "pa_id": inv.get("pre_assessment_id"),
                "pa_number": inv.get("pa_number") or pa.get("pa_number"),
                "client_name": inv.get("client_name") or pa.get("client_name"),
                "client_email": inv.get("client_email") or pa.get("client_email"),
                "partner_name": pa.get("partner_name"),
                "country": pa.get("country"),
                "service_type": pa.get("service_type"),
                "amount": inv.get("amount_received_total"),
                "timestamp": _iso(inv.get("sent_at")),
                "channel": inv.get("channel"),
                "mode": inv.get("mode"),
                "integrity_status": integrity["status"],
                "integrity_hash": (inv.get("integrity_hash") or "")[:12],
            })

    # Sort all-typed combined by timestamp desc
    results.sort(key=lambda r: (r.get("timestamp") or ""), reverse=True)
    results = results[:limit]

    return {
        "count": len(results),
        "filters": {"q": q, "record_type": record_type, "start_date": start_date, "end_date": end_date},
        "items": results,
    }


@router.get("/integrity/verify-all")
async def integrity_verify_all(current_user: dict = Depends(get_current_user)):
    """Recompute SHA-256 hash for every record. Returns counts + tampered records."""
    _admin_only(current_user)
    summary = {"verified": 0, "tampered": 0, "unverified": 0}
    tampered = []
    for col, rtype in [(consent_col, "consent"), (signatures_col, "signature"), (invoices_col, "invoice")]:
        async for d in col.find({}, {"_id": 0}):
            r = verify_hash(rtype, d)
            summary[r["status"]] = summary.get(r["status"], 0) + 1
            if r["status"] == "tampered":
                tampered.append({
                    "type": rtype, "id": d.get("id"), "reference_id": d.get("reference_id"),
                    "expected": r["expected"][:16] + "…", "actual": (r["actual"] or "")[:16] + "…",
                })
    summary["total"] = summary["verified"] + summary["tampered"] + summary["unverified"]
    summary["tampered_records"] = tampered
    summary["scanned_at"] = datetime.now(timezone.utc).isoformat()
    return summary


@router.post("/integrity/backfill")
async def integrity_backfill(current_user: dict = Depends(get_current_user)):
    """Compute and persist integrity_hash on legacy records that lack one.
    Only writes when hash is missing — never overwrites an existing hash.
    """
    _admin_only(current_user)
    written = {"consent": 0, "signature": 0, "invoice": 0}
    for col, rtype in [(consent_col, "consent"), (signatures_col, "signature"), (invoices_col, "invoice")]:
        async for d in col.find({"integrity_hash": {"$exists": False}}, {"_id": 0}):
            h = compute_hash(rtype, d)
            await col.update_one({"id": d.get("id")}, {"$set": {"integrity_hash": h}})
            written[rtype] += 1
    written["total"] = written["consent"] + written["signature"] + written["invoice"]
    return written


@router.get("/{ref_id}")
async def get_by_reference_id(ref_id: str, current_user: dict = Depends(get_current_user)):
    """Fetch full record by reference_id (CON-... / INV-... / SIG-...)."""
    _admin_only(current_user)
    rec = await consent_col.find_one({"reference_id": ref_id}, {"_id": 0})
    if rec:
        if hasattr(rec.get("created_at"), "isoformat"):
            rec["created_at"] = rec["created_at"].isoformat()
        return {"type": "consent", "record": rec}
    rec = await invoices_col.find_one({"reference_id": ref_id}, {"_id": 0})
    if rec:
        if hasattr(rec.get("sent_at"), "isoformat"):
            rec["sent_at"] = rec["sent_at"].isoformat()
        return {"type": "invoice", "record": rec}
    raise HTTPException(status_code=404, detail="Reference ID not found")
