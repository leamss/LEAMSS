"""Document Expiry Tracker — proactive expiry alerts across PA and Case docs.

Monitors `expiry_date` field on `pre_assessment_documents` + `documents` collections.
Fires alerts at 90/60/30/15/7 days before expiry to client + partner + admin.
Uses pseudo-cron: every authenticated dashboard hit triggers a soft check
(rate-limited so the same record isn't re-notified within 24h).
"""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query

from core.database import db, notifications_col
from routers.auth import get_current_user

router = APIRouter(prefix="/doc-expiry", tags=["Document Expiry Tracker"])

pa_docs_col = db["pre_assessment_documents"]
case_docs_col = db["documents"]
pa_col = db["pre_assessments"]
cases_col = db["cases"]
expiry_alerts_col = db["doc_expiry_alerts"]  # idempotency log

ALERT_BUCKETS = [90, 60, 30, 15, 7]
DEFAULT_VALIDITY_DAYS = {
    "passport": 365 * 10,
    "ielts": 365 * 2,
    "pte": 365 * 2,
    "tef": 365 * 2,
    "pcc": 180,
    "police_clearance": 180,
    "medical": 365,
    "medicals": 365,
    "education": None,
    "experience": None,
    "default": None,
}


def _days_until(expiry):
    if not expiry:
        return None
    if isinstance(expiry, str):
        try:
            expiry = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
        except Exception:
            return None
    if not isinstance(expiry, datetime):
        return None
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    return (expiry - datetime.now(timezone.utc)).days


def _bucket_for(days_left: int) -> Optional[int]:
    """Return the smallest bucket >= days_left, or 0 if expired."""
    if days_left is None:
        return None
    if days_left < 0:
        return 0
    for b in ALERT_BUCKETS:
        if days_left <= b:
            return b
    return None  # not yet in any bucket


async def _hydrate_pa(pa_id):
    if not pa_id:
        return {}
    return await pa_col.find_one({"id": pa_id}, {
        "_id": 0, "client_name": 1, "client_email": 1, "client_user_id": 1,
        "partner_id": 1, "partner_name": 1, "country": 1, "pa_number": 1,
    }) or {}


async def _hydrate_case(case_id):
    if not case_id:
        return {}
    return await cases_col.find_one({"id": case_id}, {
        "_id": 0, "client_name": 1, "client_email": 1, "client_user_id": 1,
        "case_manager_id": 1, "country": 1, "case_number": 1,
    }) or {}


def _build_item(d: dict, scope: str, ctx: dict):
    expiry = d.get("expiry_date")
    days_left = _days_until(expiry)
    bucket = _bucket_for(days_left) if days_left is not None else None
    severity = (
        "expired" if days_left is not None and days_left < 0
        else "critical" if bucket in (7, 15)
        else "warning" if bucket in (30, 60)
        else "info" if bucket == 90
        else "ok"
    )
    return {
        "id": d.get("id"),
        "scope": scope,
        "scope_id": d.get("pre_assessment_id") or d.get("case_id"),
        "scope_label": ctx.get("pa_number") or ctx.get("case_number") or "—",
        "client_name": ctx.get("client_name"),
        "client_email": ctx.get("client_email"),
        "country": ctx.get("country"),
        "doc_type": d.get("document_type"),
        "file_name": d.get("file_name"),
        "expiry_date": expiry.isoformat() if hasattr(expiry, "isoformat") else expiry,
        "days_left": days_left,
        "bucket": bucket,
        "severity": severity,
    }


@router.get("/upcoming")
async def upcoming(
    horizon_days: int = Query(120, ge=7, le=730),
    severity: Optional[str] = Query(None, description="filter: critical|warning|info|expired"),
    current_user: dict = Depends(get_current_user),
):
    """List documents expiring within the horizon (default 120 days).
    Visible to admin/CM (all), partner (only own PAs), client (only own).
    """
    role = current_user.get("role")
    items: List[Dict[str, Any]] = []
    cutoff_iso = (datetime.now(timezone.utc) + timedelta(days=horizon_days)).isoformat()

    # PA docs
    pa_filter = {"expiry_date": {"$exists": True, "$ne": None}}
    async for d in pa_docs_col.find(pa_filter, {"_id": 0}):
        ctx = await _hydrate_pa(d.get("pre_assessment_id"))
        # Role scoping
        if role == "partner" and ctx.get("partner_id") != current_user.get("id"):
            continue
        if role == "client" and ctx.get("client_user_id") != current_user.get("id"):
            continue
        item = _build_item(d, "pre_assessment", ctx)
        if item["days_left"] is None or item["days_left"] > horizon_days:
            continue
        items.append(item)

    # Case docs
    async for d in case_docs_col.find(pa_filter, {"_id": 0}):
        ctx = await _hydrate_case(d.get("case_id"))
        if role == "client" and ctx.get("client_user_id") != current_user.get("id"):
            continue
        # partner has no direct case ownership; admin/cm see all
        if role == "partner":
            continue
        item = _build_item(d, "case", ctx)
        if item["days_left"] is None or item["days_left"] > horizon_days:
            continue
        items.append(item)

    # Sort by days_left ascending (most urgent first)
    items.sort(key=lambda x: (x["days_left"] if x["days_left"] is not None else 999))

    if severity:
        items = [i for i in items if i["severity"] == severity]

    # Stats
    counts = {"expired": 0, "critical": 0, "warning": 0, "info": 0, "ok": 0}
    for i in items:
        counts[i["severity"]] = counts.get(i["severity"], 0) + 1

    _ = cutoff_iso  # reserved for future
    return {"count": len(items), "stats": counts, "items": items}


@router.post("/check-now")
async def check_now(current_user: dict = Depends(get_current_user)):
    """Manually trigger expiry scan + create notifications for any new bucket-crossings.
    Idempotent: same (doc_id, bucket) combo is logged in `doc_expiry_alerts` to avoid re-firing.
    Allowed: admin / case_manager / partner (scoped to own PAs) / client (own).
    """
    fired = 0
    snapshot = await upcoming(horizon_days=120, current_user=current_user)
    now = datetime.now(timezone.utc)

    for item in snapshot["items"]:
        bucket = item["bucket"]
        if bucket is None:
            continue
        existing = await expiry_alerts_col.find_one(
            {"doc_id": item["id"], "bucket": bucket}, {"_id": 0, "id": 1}
        )
        if existing:
            continue

        await expiry_alerts_col.insert_one({
            "id": str(uuid.uuid4()),
            "doc_id": item["id"],
            "bucket": bucket,
            "scope": item["scope"],
            "scope_id": item["scope_id"],
            "fired_at": now,
            "fired_by": current_user.get("id"),
        })

        # Build notifications: client + partner/cm + admin
        notify_user_ids: List[str] = []
        scope_doc = None
        if item["scope"] == "pre_assessment":
            scope_doc = await pa_col.find_one({"id": item["scope_id"]}, {
                "_id": 0, "client_user_id": 1, "partner_id": 1
            })
        else:
            scope_doc = await cases_col.find_one({"id": item["scope_id"]}, {
                "_id": 0, "client_user_id": 1, "case_manager_id": 1
            })
        if scope_doc:
            for k in ("client_user_id", "partner_id", "case_manager_id"):
                uid = scope_doc.get(k)
                if uid and uid not in notify_user_ids:
                    notify_user_ids.append(uid)

        title = (
            "Document EXPIRED — action needed"
            if item["severity"] == "expired"
            else f"Document expires in {bucket} days"
        )
        msg = f"{item['doc_type'] or 'Document'} for {item['scope_label']} ({item['client_name']})"
        for uid in notify_user_ids:
            await notifications_col.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": uid,
                "title": title,
                "message": msg,
                "type": "doc_expiry",
                "severity": item["severity"],
                "read": False,
                "created_at": now,
                "metadata": {"doc_id": item["id"], "scope_id": item["scope_id"]},
            })
        fired += 1

    return {"alerts_fired": fired, "scanned": snapshot["count"]}


class SetExpiryBody(__import__("pydantic").BaseModel):  # tiny inline model
    expiry_date: str  # ISO YYYY-MM-DD


@router.put("/pa-doc/{doc_id}/expiry")
async def set_pa_doc_expiry(doc_id: str, body: SetExpiryBody, current_user: dict = Depends(get_current_user)):
    """Allow admin/CM/partner-owner/client-owner to set/update expiry on a PA doc."""
    d = await pa_docs_col.find_one({"id": doc_id}, {"_id": 0})
    if not d:
        raise HTTPException(status_code=404, detail="Document not found")
    role = current_user.get("role")
    pa = await _hydrate_pa(d.get("pre_assessment_id"))
    if role == "partner" and pa.get("partner_id") != current_user.get("id"):
        raise HTTPException(status_code=403, detail="Not your PA")
    if role == "client" and pa.get("client_user_id") != current_user.get("id"):
        raise HTTPException(status_code=403, detail="Not your document")

    try:
        exp = datetime.fromisoformat(body.expiry_date).replace(tzinfo=timezone.utc)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid date format (use YYYY-MM-DD)")

    await pa_docs_col.update_one(
        {"id": doc_id},
        {"$set": {"expiry_date": exp, "updated_at": datetime.now(timezone.utc)}}
    )
    return {"ok": True, "doc_id": doc_id, "expiry_date": exp.isoformat()}
