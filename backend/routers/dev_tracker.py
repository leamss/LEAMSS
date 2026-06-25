"""Phase 21 Slice 4 Sub-Slice A.2 — Dev Tracker.

Lightweight internal kanban for bugs / features / chores reported by any
employee. IT/Admin can see + edit all; reporters can edit own items only.
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from core.database import db, users_col
from core.auth import get_current_user
from core.rbac.dependencies import require_any_permission

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dev-tracker", tags=["Dev Tracker"])

items_col = db["dev_tracker_items"]

# IT/Admin gate — for "edit any" routes
_IT_EDIT_ANY = require_any_permission("it.view.all", "system.view.all", _legacy_role="admin")

ALLOWED_STATUSES = ("backlog", "in_progress", "in_review", "done")
ALLOWED_TYPES = ("bug", "feature", "chore")
ALLOWED_PRIORITIES = ("P0", "P1", "P2", "P3")


def _is_it_or_admin(user: dict) -> bool:
    r = (user.get("rbac_role") or user.get("role") or "").lower()
    return r in ("admin_owner", "admin", "it") or "it" in r or "admin" in r


# ─────────────────────────── Models ────────────────────────────

class ItemCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    description: str = ""
    type: str = "bug"
    priority: str = "P2"
    status: str = "backlog"
    assignee_id: Optional[str] = None
    labels: List[str] = []
    linked_employee_id: Optional[str] = None


class ItemPatch(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    assignee_id: Optional[str] = None
    labels: Optional[List[str]] = None


class CommentCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=2000)


# ─────────────────────────── Helpers ────────────────────────────

def _validate_enums(payload: dict, *, partial: bool) -> None:
    if (s := payload.get("status")) and s not in ALLOWED_STATUSES:
        raise HTTPException(status_code=400, detail=f"status must be one of {ALLOWED_STATUSES}")
    if (t := payload.get("type")) and t not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"type must be one of {ALLOWED_TYPES}")
    if (p := payload.get("priority")) and p not in ALLOWED_PRIORITIES:
        raise HTTPException(status_code=400, detail=f"priority must be one of {ALLOWED_PRIORITIES}")


async def _enrich_user(uid: Optional[str]) -> dict:
    if not uid:
        return {}
    u = await users_col.find_one({"id": uid}, {"_id": 0, "id": 1, "name": 1, "email": 1, "department": 1})
    return u or {}


async def _can_edit(item: dict, user: dict) -> bool:
    if _is_it_or_admin(user):
        return True
    return item.get("reporter_id") == user["id"] or item.get("assignee_id") == user["id"]


# ─────────────────────────── Endpoints ────────────────────────────

@router.get("/items")
async def list_items(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    assignee_id: Optional[str] = Query(None),
    label: Optional[str] = Query(None),
    q: Optional[str] = Query(None, description="Title substring search"),
    user: dict = Depends(get_current_user),
):
    """List items. Non-IT users see items they reported, are assigned to, OR are public (non-confidential)."""
    flt: dict = {}
    if status:
        flt["status"] = status
    if priority:
        flt["priority"] = priority
    if type:
        flt["type"] = type
    if assignee_id:
        flt["assignee_id"] = assignee_id
    if label:
        flt["labels"] = label
    if q:
        flt["title"] = {"$regex": q, "$options": "i"}

    if not _is_it_or_admin(user):
        flt["$or"] = [
            {"reporter_id": user["id"]},
            {"assignee_id": user["id"]},
            {"linked_employee_id": user["id"]},
        ]

    out = []
    async for it in items_col.find(flt, {"_id": 0, "audit_log": 0}).sort("created_at", -1).limit(500):
        out.append(it)
    return out


@router.post("/items")
async def create_item(payload: ItemCreate, user: dict = Depends(get_current_user)):
    data = payload.dict()
    _validate_enums(data, partial=False)

    now = datetime.now(timezone.utc)
    item_id = str(uuid.uuid4())
    assignee = await _enrich_user(data.get("assignee_id"))
    item = {
        "id": item_id,
        "title": data["title"].strip(),
        "description": (data.get("description") or "").strip(),
        "type": data["type"],
        "priority": data["priority"],
        "status": data["status"],
        "assignee_id": data.get("assignee_id"),
        "assignee_name": assignee.get("name"),
        "reporter_id": user["id"],
        "reporter_name": user.get("name"),
        "labels": list(dict.fromkeys((data.get("labels") or [])[:10])),  # dedupe + cap
        "linked_employee_id": data.get("linked_employee_id"),
        "comments": [],
        "comment_count": 0,
        "audit_log": [{
            "action": "created",
            "actor_id": user["id"],
            "actor_name": user.get("name"),
            "timestamp": now.isoformat(),
        }],
        "created_at": now,
        "updated_at": now,
    }
    await items_col.insert_one(item)
    item.pop("_id", None)
    return item


@router.get("/items/{item_id}")
async def get_item(item_id: str, user: dict = Depends(get_current_user)):
    it = await items_col.find_one({"id": item_id}, {"_id": 0})
    if not it:
        raise HTTPException(status_code=404, detail="Item not found")
    if not _is_it_or_admin(user):
        if user["id"] not in (it.get("reporter_id"), it.get("assignee_id"), it.get("linked_employee_id")):
            raise HTTPException(status_code=403, detail="No access")
    return it


@router.patch("/items/{item_id}")
async def patch_item(item_id: str, payload: ItemPatch, user: dict = Depends(get_current_user)):
    it = await items_col.find_one({"id": item_id}, {"_id": 0})
    if not it:
        raise HTTPException(status_code=404, detail="Item not found")
    if not await _can_edit(it, user):
        raise HTTPException(status_code=403, detail="No edit access")

    delta = {k: v for k, v in payload.dict(exclude_unset=True).items() if v is not None}
    _validate_enums(delta, partial=True)
    if not delta:
        return it

    if "assignee_id" in delta:
        assignee = await _enrich_user(delta["assignee_id"])
        delta["assignee_name"] = assignee.get("name")
    if "labels" in delta:
        delta["labels"] = list(dict.fromkeys((delta["labels"] or [])[:10]))

    now = datetime.now(timezone.utc)
    audit_events = []
    for k, v in delta.items():
        if it.get(k) != v:
            audit_events.append({
                "action": f"updated_{k}",
                "actor_id": user["id"],
                "actor_name": user.get("name"),
                "timestamp": now.isoformat(),
                "from": it.get(k),
                "to": v,
            })

    update = {"$set": {**delta, "updated_at": now}}
    if audit_events:
        update["$push"] = {"audit_log": {"$each": audit_events}}
    await items_col.update_one({"id": item_id}, update)
    return await items_col.find_one({"id": item_id}, {"_id": 0})


@router.post("/items/{item_id}/comments")
async def add_comment(item_id: str, payload: CommentCreate, user: dict = Depends(get_current_user)):
    it = await items_col.find_one({"id": item_id}, {"_id": 0, "reporter_id": 1, "assignee_id": 1, "linked_employee_id": 1})
    if not it:
        raise HTTPException(status_code=404, detail="Item not found")
    if not _is_it_or_admin(user):
        if user["id"] not in (it.get("reporter_id"), it.get("assignee_id"), it.get("linked_employee_id")):
            raise HTTPException(status_code=403, detail="No comment access")

    now = datetime.now(timezone.utc)
    comment = {
        "comment_id": str(uuid.uuid4()),
        "body": payload.body.strip(),
        "author_id": user["id"],
        "author_name": user.get("name"),
        "created_at": now.isoformat(),
    }
    await items_col.update_one(
        {"id": item_id},
        {
            "$push": {
                "comments": comment,
                "audit_log": {
                    "action": "commented",
                    "actor_id": user["id"],
                    "actor_name": user.get("name"),
                    "timestamp": now.isoformat(),
                },
            },
            "$inc": {"comment_count": 1},
            "$set": {"updated_at": now},
        },
    )
    return comment


@router.get("/stats")
async def stats(user: dict = Depends(get_current_user)):
    """Quick rollup for the IT dashboard tile / kanban header."""
    flt: dict = {}
    if not _is_it_or_admin(user):
        flt["$or"] = [
            {"reporter_id": user["id"]},
            {"assignee_id": user["id"]},
            {"linked_employee_id": user["id"]},
        ]
    pipeline = [{"$match": flt}, {"$group": {"_id": "$status", "count": {"$sum": 1}}}]
    by_status = {s: 0 for s in ALLOWED_STATUSES}
    async for row in items_col.aggregate(pipeline):
        if row["_id"] in by_status:
            by_status[row["_id"]] = row["count"]
    total = sum(by_status.values())
    return {"total": total, "by_status": by_status}
