"""Phase 18.6 — Client Errors collection.

Captures React render crashes / unhandled JS errors from the frontend
``<AppErrorBoundary>`` and exposes a small admin-only read endpoint for a
future "Client Errors" dashboard.

Design choices:
  • Auth required — anonymous events would invite spam.
  • Rate limit — 30 events/min per user. Protects against error loops that
    fire ``componentDidCatch`` thousands of times.
  • Deduplication — same ``(message, route, user_id)`` within 24h → increment
    ``occurrence_count`` instead of inserting a new row. Keeps the collection
    actionable rather than a flood log.
  • Indexes — created lazily on first call (``ensure_indexes``).
"""
from __future__ import annotations
import uuid
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Any, Deque, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from core.auth import get_current_user
from core.database import db


router = APIRouter(prefix="/client-errors", tags=["Client Errors"])


# ─────────────────────────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────────────────────────
class ClientErrorIn(BaseModel):
    message: str = Field(..., max_length=500)
    stack: str = Field("", max_length=5000)
    component_stack: str = Field("", max_length=5000, alias="componentStack")
    route: str = Field("", max_length=500)
    scope: str = Field("unknown", max_length=50)  # sales / admin / public / unknown
    user_agent: str = Field("", max_length=300, alias="userAgent")
    client_timestamp: Optional[str] = Field(default=None, alias="timestamp", max_length=50)

    class Config:
        populate_by_name = True


class ClientErrorPatch(BaseModel):
    """Phase 18.7 — partial update from the admin dashboard."""
    resolved: Optional[bool] = None
    notes: Optional[str] = Field(default=None, max_length=2000)


# ─────────────────────────────────────────────────────────────────────────────
# In-memory rate limit (per process — sufficient for our single-replica setup)
# 30 events per user per 60s
# ─────────────────────────────────────────────────────────────────────────────
_RATE_WINDOW_S = 60
_RATE_MAX = 30
_rate_buckets: Dict[str, Deque[float]] = defaultdict(deque)


def _allow(user_id: str) -> bool:
    bucket = _rate_buckets[user_id]
    now = time.monotonic()
    # Evict old entries
    while bucket and (now - bucket[0]) > _RATE_WINDOW_S:
        bucket.popleft()
    if len(bucket) >= _RATE_MAX:
        return False
    bucket.append(now)
    return True


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/client-errors/_test/reset-rate-limit
#   Admin-only escape hatch used by the regression test suite to clear the
#   in-process per-user rate buckets between rate-limit-sensitive tests.
#   It's safe to ship — admin-gated and only resets an in-memory counter.
# ─────────────────────────────────────────────────────────────────────────────
def _reset_rate_limit() -> None:  # pragma: no cover — test helper
    _rate_buckets.clear()


@router.post("/_test/reset-rate-limit")
async def reset_rate_limit_admin_only(current_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    role = (current_user.get("rbac_role") or current_user.get("role") or "").lower()
    if role not in {"admin", "admin_owner"}:
        raise HTTPException(status_code=403, detail="Admin only")
    _reset_rate_limit()
    return {"status": "ok", "cleared": True}


# ─────────────────────────────────────────────────────────────────────────────
# Indexes — lazily ensured on first call
# ─────────────────────────────────────────────────────────────────────────────
_indexes_ensured = False


async def ensure_indexes() -> None:
    global _indexes_ensured
    if _indexes_ensured:
        return
    try:
        coll = db["client_errors"]
        await coll.create_index([("message", 1), ("route", 1), ("received_at", -1)])
        await coll.create_index([("resolved", 1), ("received_at", -1)])
        await coll.create_index("user_id")
        _indexes_ensured = True
    except Exception:  # noqa: BLE001
        # Index creation must not block ingestion
        pass


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/client-errors
# ─────────────────────────────────────────────────────────────────────────────
@router.post("")
async def post_client_error(payload: ClientErrorIn, current_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """Ingest a single client-side render/JS error."""
    user_id = str(current_user.get("id") or current_user.get("user_id") or "anonymous")
    if not _allow(user_id):
        raise HTTPException(status_code=429, detail="Too many client error reports — slow down.")

    await ensure_indexes()
    coll = db["client_errors"]
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)

    dedupe_key = {
        "message": payload.message,
        "route": payload.route,
        "user_id": user_id,
        "received_at": {"$gte": cutoff},
    }
    existing = await coll.find_one(dedupe_key, sort=[("received_at", -1)])
    if existing:
        new_count = (existing.get("occurrence_count") or 1) + 1
        await coll.update_one(
            {"id": existing["id"]},
            {"$set": {
                "occurrence_count": new_count,
                "last_seen_at": now.isoformat(),
            }},
        )
        return {
            "id": existing["id"],
            "deduped": True,
            "occurrence_count": new_count,
        }

    doc = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "user_role": current_user.get("rbac_role") or current_user.get("role"),
        "user_email": current_user.get("email"),
        "message": payload.message,
        "stack": payload.stack,
        "componentStack": payload.component_stack,
        "route": payload.route,
        "scope": payload.scope,
        "user_agent": payload.user_agent,
        "client_timestamp": payload.client_timestamp,
        "received_at": now,
        "last_seen_at": now.isoformat(),
        "occurrence_count": 1,
        "resolved": False,
        "resolved_by": None,
        "resolved_at": None,
    }
    await coll.insert_one(doc)
    return {"id": doc["id"], "deduped": False, "occurrence_count": 1}


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard read endpoints (Phase 18.7 — extends the Phase 18.6 scaffold)
# ─────────────────────────────────────────────────────────────────────────────
def _is_admin_user(user: dict) -> bool:
    role = (user.get("rbac_role") or user.get("role") or "").lower()
    return role in {"admin", "admin_owner"}


def _iso_dt(d: dict, *keys: str) -> dict:
    for k in keys:
        if isinstance(d.get(k), datetime):
            d[k] = d[k].isoformat()
    return d


@router.get("/summary")
async def client_errors_summary(current_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """Counters for the dashboard top strip: open / resolved / last_24h / critical."""
    if not _is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    now = datetime.now(timezone.utc)
    cutoff_24h = now - timedelta(hours=24)
    coll = db["client_errors"]
    open_count = await coll.count_documents({"resolved": False})
    resolved_count = await coll.count_documents({"resolved": True})
    last_24h = await coll.count_documents({"received_at": {"$gte": cutoff_24h}})
    critical = await coll.count_documents({"occurrence_count": {"$gt": 10}, "resolved": False})
    return {
        "open": open_count,
        "resolved": resolved_count,
        "last_24h": last_24h,
        "critical": critical,
    }


@router.get("")
async def list_client_errors(
    resolved: Optional[bool] = Query(default=None),
    scope: Optional[str] = Query(default=None, max_length=50),
    since: Optional[str] = Query(default=None),
    until: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None, max_length=200),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    limit: Optional[int] = Query(default=None, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """List client errors with filters + pagination. Admin-only.

    Backwards-compatible: the original ``limit`` parameter still works and, when
    supplied, takes precedence over ``page_size`` (legacy clients pass only limit).
    """
    if not _is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Admin only")

    q: Dict[str, Any] = {}
    if resolved is not None:
        q["resolved"] = resolved
    if scope:
        q["scope"] = scope
    received_at_clause: Dict[str, Any] = {}
    for label, raw in (("$gte", since), ("$lte", until)):
        if raw:
            try:
                received_at_clause[label] = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            except Exception:  # noqa: BLE001
                raise HTTPException(status_code=400, detail=f"Bad date format: {raw}")
    if received_at_clause:
        q["received_at"] = received_at_clause
    if search:
        q["message"] = {"$regex": search, "$options": "i"}

    coll = db["client_errors"]
    total_count = await coll.count_documents(q)

    effective_limit = limit if limit is not None else page_size
    skip = 0 if limit is not None else (page - 1) * page_size

    cur = coll.find(q, {"_id": 0}).sort("received_at", -1).skip(skip).limit(effective_limit)
    items: List[Dict[str, Any]] = []
    async for d in cur:
        _iso_dt(d, "received_at", "resolved_at", "last_digest_sent_at")
        items.append(d)

    return {
        "items": items,
        "total": total_count,         # keep legacy key
        "total_count": total_count,   # spec key
        "page": page,
        "page_size": effective_limit,
    }


@router.get("/groups")
async def client_errors_groups(
    limit: int = Query(default=10, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Top occurrence groups aggregated by (message, route)."""
    if not _is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    pipeline = [
        {"$group": {
            "_id": {"message": "$message", "route": "$route"},
            "total_occurrences": {"$sum": "$occurrence_count"},
            "row_count": {"$sum": 1},
            "scopes": {"$addToSet": "$scope"},
            "latest": {"$max": "$received_at"},
        }},
        {"$sort": {"total_occurrences": -1}},
        {"$limit": limit},
    ]
    items: List[Dict[str, Any]] = []
    async for r in db["client_errors"].aggregate(pipeline):
        items.append({
            "message": (r["_id"] or {}).get("message"),
            "route": (r["_id"] or {}).get("route"),
            "total_occurrences": r.get("total_occurrences", 0),
            "row_count": r.get("row_count", 0),
            "scopes": [s for s in (r.get("scopes") or []) if s],
            "latest": _iso(r.get("latest")),
        })
    return {"items": items, "total": len(items)}


@router.get("/{cid}/users")
async def client_error_users(cid: str, current_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """Distinct users who hit this exact error (matched by message + route)."""
    if not _is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    err = await db["client_errors"].find_one({"id": cid})
    if not err:
        raise HTTPException(status_code=404, detail="Error not found")
    pipeline = [
        {"$match": {"message": err.get("message"), "route": err.get("route")}},
        {"$group": {
            "_id": "$user_id",
            "user_email": {"$last": "$user_email"},
            "user_role": {"$last": "$user_role"},
            "last_seen_at": {"$max": "$received_at"},
            "occurrences": {"$sum": "$occurrence_count"},
        }},
        {"$sort": {"last_seen_at": -1}},
    ]
    users: List[Dict[str, Any]] = []
    async for r in db["client_errors"].aggregate(pipeline):
        users.append({
            "user_id": r["_id"],
            "user_email": r.get("user_email"),
            "user_role": r.get("user_role"),
            "last_seen_at": _iso(r.get("last_seen_at")),
            "occurrences": r.get("occurrences", 0),
        })
    return {"items": users, "total": len(users)}


@router.patch("/{cid}")
async def patch_client_error(
    cid: str,
    payload: "ClientErrorPatch",
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Mark an error resolved/unresolved + optional notes."""
    if not _is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Admin only")

    now = datetime.now(timezone.utc)
    set_payload: Dict[str, Any] = {}
    if payload.resolved is not None:
        set_payload["resolved"] = payload.resolved
        if payload.resolved:
            set_payload["resolved_at"] = now
            set_payload["resolved_by"] = str(current_user.get("id") or current_user.get("user_id") or "admin")
            set_payload["resolved_by_name"] = current_user.get("name") or current_user.get("email") or "admin"
        else:
            set_payload["resolved_at"] = None
            set_payload["resolved_by"] = None
            set_payload["resolved_by_name"] = None
    if payload.notes is not None:
        set_payload["resolution_notes"] = payload.notes[:2000]

    if not set_payload:
        raise HTTPException(status_code=400, detail="No fields to update")

    r = await db["client_errors"].find_one_and_update(
        {"id": cid},
        {"$set": set_payload},
        return_document=True,
    )
    if not r:
        raise HTTPException(status_code=404, detail="Error not found")

    # audit trail (best-effort)
    try:
        await db["audit_logs"].insert_one({
            "id": str(uuid.uuid4()),
            "kind": "client_error.patch",
            "entity_id": cid,
            "actor_id": str(current_user.get("id") or ""),
            "actor_email": current_user.get("email"),
            "payload": set_payload,
            "at": now,
        })
    except Exception:  # noqa: BLE001
        pass

    r.pop("_id", None)
    _iso_dt(r, "received_at", "resolved_at", "last_digest_sent_at")
    return r


def _iso(v: Any) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.isoformat()
    return str(v)



# ─────────────────────────────────────────────────────────────────────────────
# Phase 18.7.1 — Admin-only synthetic test pipeline
#   POST /_test/throw — writes a synthetic client_errors row (flagged
#     ``is_synthetic: true``), then runs the digest evaluator immediately so
#     matching channels receive the message in real time. Returns the new
#     error id + dispatch result so the UI can show pipeline health.
#   DELETE /_test/cleanup — purges all synthetic rows (admin escape hatch).
# ─────────────────────────────────────────────────────────────────────────────
class TestThrowIn(BaseModel):
    message: Optional[str] = Field(default=None, max_length=500)
    route: Optional[str] = Field(default=None, max_length=500)
    scope: Optional[str] = Field(default=None, max_length=50)


@router.post("/_test/throw")
async def test_throw(payload: TestThrowIn, current_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    if not _is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    await ensure_indexes()
    now = datetime.now(timezone.utc)
    msg = (payload.message or "Synthetic ops test error").strip()[:500] or "Synthetic ops test error"
    route = (payload.route or "/admin/client-errors")[:500]
    scope = (payload.scope or "admin")[:50]

    # Reuse the dedup-aware insert so test errors behave like real ones — if a
    # synthetic with the same (message, route, user_id) exists in the last 24h,
    # we bump occurrence_count instead of creating a flood of duplicates.
    user_id = str(current_user.get("id") or current_user.get("user_id") or "anonymous")
    cutoff = now - timedelta(hours=24)
    existing = await db["client_errors"].find_one({
        "message": msg, "route": route, "user_id": user_id,
        "received_at": {"$gte": cutoff},
        "is_synthetic": True,
    }, sort=[("received_at", -1)])

    if existing:
        new_count = (existing.get("occurrence_count") or 1) + 1
        await db["client_errors"].update_one(
            {"id": existing["id"]},
            {"$set": {"occurrence_count": new_count, "last_seen_at": now.isoformat()}},
        )
        error_id = existing["id"]
    else:
        error_id = str(uuid.uuid4())
        await db["client_errors"].insert_one({
            "id": error_id,
            "user_id": user_id,
            "user_role": current_user.get("rbac_role") or current_user.get("role"),
            "user_email": current_user.get("email"),
            "message": msg,
            "stack": "Synthetic stack — generated by /_test/throw\n  at ops.testThrow (client_errors.py:throw)",
            "componentStack": "in DevPipelineTester\n  in ChannelsTab",
            "route": route,
            "scope": scope,
            "user_agent": "synthetic/ops-pipeline-test",
            "client_timestamp": now.isoformat(),
            "received_at": now,
            "last_seen_at": now.isoformat(),
            "occurrence_count": 1,
            "resolved": False,
            "resolved_by": None,
            "resolved_at": None,
            "is_synthetic": True,
        })

    # Audit log
    try:
        await db["audit_logs"].insert_one({
            "id": str(uuid.uuid4()),
            "kind": "client_error.test_error_thrown",
            "entity_id": error_id,
            "actor_id": user_id,
            "actor_email": current_user.get("email"),
            "payload": {"message": msg, "route": route, "scope": scope},
            "at": now,
        })
    except Exception:  # noqa: BLE001
        pass

    # Immediately run digest evaluator so matching channels send right away
    dispatch_result: Dict[str, Any] = {"matched_channels": 0, "sent": 0, "failed": 0, "details": []}
    try:
        from routers.notification_channels import run_digest_once
        summary = await run_digest_once()
        dispatch_result = {
            "matched_channels": summary.get("channels_processed", 0),
            "sent": summary.get("alerts_sent", 0),
            "failed": summary.get("failures", 0),
            "details": summary.get("details", []),
        }
    except Exception as e:  # noqa: BLE001
        dispatch_result["failed"] = -1
        dispatch_result["error"] = str(e)[:300]

    return {
        "ok": True,
        "error_id": error_id,
        "dispatch_result": dispatch_result,
        "synthetic": True,
    }


@router.delete("/_test/cleanup")
async def test_cleanup(current_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """Purge synthetic rows. Real (non-synthetic) errors are untouched."""
    if not _is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    r = await db["client_errors"].delete_many({"is_synthetic": True})
    try:
        await db["audit_logs"].insert_one({
            "id": str(uuid.uuid4()),
            "kind": "client_error.test_cleanup",
            "entity_id": None,
            "actor_id": str(current_user.get("id") or ""),
            "actor_email": current_user.get("email"),
            "payload": {"deleted_count": r.deleted_count},
            "at": datetime.now(timezone.utc),
        })
    except Exception:  # noqa: BLE001
        pass
    return {"deleted_count": r.deleted_count}
