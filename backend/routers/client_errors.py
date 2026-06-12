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
# GET /api/client-errors — admin only, future dashboard scaffold
# ─────────────────────────────────────────────────────────────────────────────
@router.get("")
async def list_client_errors(
    resolved: Optional[bool] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """List recent client errors. Admin-only — used by the future ops dashboard."""
    role = (current_user.get("rbac_role") or current_user.get("role") or "").lower()
    if role not in {"admin", "admin_owner"}:
        raise HTTPException(status_code=403, detail="Admin only")
    q: Dict[str, Any] = {}
    if resolved is not None:
        q["resolved"] = resolved
    cur = db["client_errors"].find(q, {"_id": 0}).sort("received_at", -1).limit(limit)
    items: List[Dict[str, Any]] = []
    async for d in cur:
        # ISO-stringify datetime
        for k in ("received_at",):
            if isinstance(d.get(k), datetime):
                d[k] = d[k].isoformat()
        items.append(d)
    total = await db["client_errors"].count_documents(q)
    return {"items": items, "total": total}
