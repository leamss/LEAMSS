"""Phase 21 Slice 4 Sub-Slice B.2 — Internal Support Tickets (v2).

Department-routed help-desk with SLA tracking, audit log, and
auto-link to Dev Tracker when the ticket smells like a bug.

Uses /api/support-tickets/* namespace + `support_tickets` collection
to coexist with the pre-existing /api/tickets client-facing router.
"""
import re
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from core.database import db, users_col
from core.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/support-tickets", tags=["Support Tickets"])

tickets_col = db["support_tickets"]
counters_col = db["counters"]
dev_items_col = db["dev_tracker_items"]

ALLOWED_DEPARTMENTS = ("it", "hr", "finance", "marketing", "ops")
ALLOWED_PRIORITIES = ("P0", "P1", "P2", "P3")
ALLOWED_STATUSES = ("open", "in_progress", "waiting", "resolved", "closed")

# SLA in hours per priority
SLA_HOURS = {"P0": 4, "P1": 8, "P2": 24, "P3": 72}

TECH_DEPARTMENTS = {"it", "marketing"}
BUG_PATTERN = re.compile(r"\b(crash|error|broken|bug|fail|exception|stacktrace|500\s*error)\b", re.I)


class TicketCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    description: str = ""
    department: str
    category: Optional[str] = None
    priority: Optional[str] = None
    tags: List[str] = []


class TicketPatch(BaseModel):
    status: Optional[str] = None
    assignee_id: Optional[str] = None
    priority: Optional[str] = None
    department: Optional[str] = None
    category: Optional[str] = None


class CommentCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=2000)
    is_internal: bool = False


class RateRequest(BaseModel):
    stars: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


def _is_admin(user: dict) -> bool:
    r = (user.get("rbac_role") or user.get("role") or "").lower()
    return r in ("admin_owner", "admin")


def _is_dept_lead(user: dict, dept: str) -> bool:
    if _is_admin(user):
        return True
    r = (user.get("rbac_role") or user.get("role") or "").lower()
    d = (user.get("department") or "").lower()
    return d == dept and ("head" in r or "lead" in r or "manager" in r or r in ("hr", "it"))


def _can_edit_ticket(user: dict, ticket: dict) -> bool:
    if _is_admin(user):
        return True
    if _is_dept_lead(user, ticket.get("department", "")):
        return True
    return ticket.get("assignee_id") == user["id"]


async def _next_ticket_number() -> str:
    res = await counters_col.find_one_and_update(
        {"_id": "support_tickets"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
    )
    seq = (res or {}).get("seq", 1)
    return f"TKT-{seq:04d}"


async def _maybe_auto_link_dev_item(ticket: dict, user: dict) -> Optional[str]:
    if ticket.get("department") not in TECH_DEPARTMENTS:
        return None
    has_bug_tag = any(t.lower() == "bug" for t in (ticket.get("tags") or []))
    description = ticket.get("description") or ""
    title = ticket.get("title") or ""
    smells_buggy = has_bug_tag or BUG_PATTERN.search(f"{title} {description}") is not None
    if not smells_buggy:
        return None
    now = datetime.now(timezone.utc)
    dev_item_id = str(uuid.uuid4())
    dev = {
        "id": dev_item_id,
        "title": f"[from {ticket['ticket_number']}] {ticket['title']}",
        "description": ticket.get("description") or "",
        "type": "bug",
        "priority": ticket.get("priority") or "P2",
        "status": "backlog",
        "assignee_id": None,
        "assignee_name": None,
        "reporter_id": user["id"],
        "reporter_name": user.get("name"),
        "labels": list(dict.fromkeys(["from-ticket", ticket["department"]] + (ticket.get("tags") or [])))[:10],
        "linked_employee_id": ticket.get("raised_by_id"),
        "linked_ticket_id": ticket["id"],
        "linked_ticket_number": ticket["ticket_number"],
        "comments": [],
        "comment_count": 0,
        "audit_log": [{
            "action": "auto_created_from_ticket",
            "actor_id": user["id"],
            "actor_name": user.get("name"),
            "timestamp": now.isoformat(),
            "ticket_id": ticket["id"],
            "ticket_number": ticket["ticket_number"],
        }],
        "created_at": now,
        "updated_at": now,
    }
    await dev_items_col.insert_one(dev)
    return dev_item_id


@router.post("")
async def create_ticket(payload: TicketCreate, user: dict = Depends(get_current_user)):
    if payload.department not in ALLOWED_DEPARTMENTS:
        raise HTTPException(status_code=400, detail=f"department must be one of {ALLOWED_DEPARTMENTS}")
    priority = payload.priority
    if priority and priority not in ALLOWED_PRIORITIES:
        raise HTTPException(status_code=400, detail=f"priority must be one of {ALLOWED_PRIORITIES}")
    if not priority or not (_is_admin(user) or _is_dept_lead(user, payload.department)):
        priority = "P3"

    now = datetime.now(timezone.utc)
    sla_at = now + timedelta(hours=SLA_HOURS[priority])
    ticket_id = str(uuid.uuid4())
    ticket_number = await _next_ticket_number()
    ticket = {
        "id": ticket_id,
        "ticket_number": ticket_number,
        "title": payload.title.strip(),
        "description": (payload.description or "").strip(),
        "department": payload.department,
        "category": (payload.category or "").strip() or None,
        "raised_by_id": user["id"],
        "raised_by_name": user.get("name"),
        "priority": priority,
        "status": "open",
        "assignee_id": None,
        "assignee_name": None,
        "tags": list(dict.fromkeys((payload.tags or [])))[:10],
        "attachments": [],
        "comments": [],
        "audit_log": [{
            "action": "created",
            "actor_id": user["id"],
            "actor_name": user.get("name"),
            "timestamp": now.isoformat(),
        }],
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "resolved_at": None,
        "sla_target_at": sla_at.isoformat(),
        "satisfaction_rating": None,
        "linked_dev_item_id": None,
    }
    await tickets_col.insert_one(ticket)

    dev_id = await _maybe_auto_link_dev_item(ticket, user)
    if dev_id:
        await tickets_col.update_one(
            {"id": ticket_id},
            {
                "$set": {"linked_dev_item_id": dev_id},
                "$push": {"audit_log": {
                    "action": "auto_linked_dev_item",
                    "actor_id": user["id"],
                    "actor_name": user.get("name"),
                    "timestamp": now.isoformat(),
                    "dev_item_id": dev_id,
                }},
            },
        )
        ticket["linked_dev_item_id"] = dev_id
    ticket.pop("_id", None)
    return ticket


@router.get("")
async def list_tickets(
    department: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    assignee_id: Optional[str] = Query(None),
    mine_only: bool = Query(False),
    user: dict = Depends(get_current_user),
):
    flt: dict = {}
    if department:
        flt["department"] = department
    if status:
        flt["status"] = status
    if priority:
        flt["priority"] = priority
    if assignee_id:
        flt["assignee_id"] = assignee_id

    if mine_only:
        flt["raised_by_id"] = user["id"]
    elif not _is_admin(user):
        user_dept = (user.get("department") or "").lower()
        if user_dept and _is_dept_lead(user, user_dept):
            flt["$or"] = [{"department": user_dept}, {"raised_by_id": user["id"]}, {"assignee_id": user["id"]}]
        else:
            flt["$or"] = [{"raised_by_id": user["id"]}, {"assignee_id": user["id"]}]

    out = []
    async for t in tickets_col.find(flt, {"_id": 0, "comments": 0, "audit_log": 0}).sort("created_at", -1).limit(500):
        out.append(t)
    return out


@router.get("/stats")
async def stats(user: dict = Depends(get_current_user)):
    flt: dict = {}
    if not _is_admin(user):
        user_dept = (user.get("department") or "").lower()
        if user_dept and _is_dept_lead(user, user_dept):
            flt["$or"] = [{"department": user_dept}, {"raised_by_id": user["id"]}, {"assignee_id": user["id"]}]
        else:
            flt["$or"] = [{"raised_by_id": user["id"]}, {"assignee_id": user["id"]}]

    now_iso = datetime.now(timezone.utc).isoformat()
    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

    by_status = {s: 0 for s in ALLOWED_STATUSES}
    pipeline = [{"$match": flt}, {"$group": {"_id": "$status", "count": {"$sum": 1}}}]
    async for row in tickets_col.aggregate(pipeline):
        if row["_id"] in by_status:
            by_status[row["_id"]] = row["count"]

    past_sla = await tickets_col.count_documents({
        **flt,
        "status": {"$in": ["open", "in_progress", "waiting"]},
        "sla_target_at": {"$lt": now_iso},
    })
    resolved_this_week = await tickets_col.count_documents({
        **flt,
        "status": "resolved",
        "resolved_at": {"$gte": week_ago},
    })
    return {
        "total": sum(by_status.values()),
        "by_status": by_status,
        "past_sla": past_sla,
        "resolved_this_week": resolved_this_week,
    }


@router.get("/{ticket_id}")
async def get_ticket(ticket_id: str, user: dict = Depends(get_current_user)):
    t = await tickets_col.find_one({"id": ticket_id}, {"_id": 0})
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if not (_is_admin(user) or t.get("raised_by_id") == user["id"] or t.get("assignee_id") == user["id"]
            or _is_dept_lead(user, t.get("department", ""))):
        raise HTTPException(status_code=403, detail="No access")
    is_resolver = _is_admin(user) or t.get("assignee_id") == user["id"] or _is_dept_lead(user, t.get("department", ""))
    if not is_resolver:
        t["comments"] = [c for c in (t.get("comments") or []) if not c.get("is_internal")]
    return t


@router.patch("/{ticket_id}")
async def patch_ticket(ticket_id: str, payload: TicketPatch, user: dict = Depends(get_current_user)):
    t = await tickets_col.find_one({"id": ticket_id}, {"_id": 0})
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if not _can_edit_ticket(user, t):
        raise HTTPException(status_code=403, detail="No edit access")

    delta = {k: v for k, v in payload.dict(exclude_unset=True).items() if v is not None}
    if "status" in delta and delta["status"] not in ALLOWED_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    if "priority" in delta and delta["priority"] not in ALLOWED_PRIORITIES:
        raise HTTPException(status_code=400, detail="Invalid priority")
    if "department" in delta and delta["department"] not in ALLOWED_DEPARTMENTS:
        raise HTTPException(status_code=400, detail="Invalid department")
    if not delta:
        return t

    if "assignee_id" in delta and delta["assignee_id"]:
        u = await users_col.find_one({"id": delta["assignee_id"]}, {"_id": 0, "name": 1})
        delta["assignee_name"] = (u or {}).get("name")
    if "priority" in delta:
        created = datetime.fromisoformat(t["created_at"].replace("Z", "+00:00"))
        delta["sla_target_at"] = (created + timedelta(hours=SLA_HOURS[delta["priority"]])).isoformat()

    now = datetime.now(timezone.utc)
    audit_events = []
    for k, v in delta.items():
        if t.get(k) != v:
            audit_events.append({
                "action": f"updated_{k}",
                "actor_id": user["id"],
                "actor_name": user.get("name"),
                "timestamp": now.isoformat(),
                "from": t.get(k),
                "to": v,
            })

    update = {"$set": {**delta, "updated_at": now.isoformat()}}
    if audit_events:
        update["$push"] = {"audit_log": {"$each": audit_events}}
    await tickets_col.update_one({"id": ticket_id}, update)
    return await tickets_col.find_one({"id": ticket_id}, {"_id": 0})


@router.post("/{ticket_id}/comments")
async def add_comment(ticket_id: str, payload: CommentCreate, user: dict = Depends(get_current_user)):
    t = await tickets_col.find_one({"id": ticket_id}, {"_id": 0})
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")
    is_resolver = _is_admin(user) or t.get("assignee_id") == user["id"] or _is_dept_lead(user, t.get("department", ""))
    if not (is_resolver or t.get("raised_by_id") == user["id"]):
        raise HTTPException(status_code=403, detail="No comment access")
    if payload.is_internal and not is_resolver:
        raise HTTPException(status_code=403, detail="Internal notes are resolver-only")

    now = datetime.now(timezone.utc).isoformat()
    comment = {
        "comment_id": str(uuid.uuid4()),
        "body": payload.body.strip(),
        "is_internal": payload.is_internal,
        "author_id": user["id"],
        "author_name": user.get("name"),
        "created_at": now,
    }
    await tickets_col.update_one(
        {"id": ticket_id},
        {
            "$push": {
                "comments": comment,
                "audit_log": {
                    "action": "commented_internal" if payload.is_internal else "commented",
                    "actor_id": user["id"],
                    "actor_name": user.get("name"),
                    "timestamp": now,
                },
            },
            "$set": {"updated_at": now},
        },
    )
    return comment


@router.post("/{ticket_id}/resolve")
async def resolve_ticket(ticket_id: str, user: dict = Depends(get_current_user)):
    t = await tickets_col.find_one({"id": ticket_id}, {"_id": 0})
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if not _can_edit_ticket(user, t):
        raise HTTPException(status_code=403, detail="No edit access")
    if t.get("status") == "resolved":
        return t
    now = datetime.now(timezone.utc).isoformat()
    await tickets_col.update_one(
        {"id": ticket_id},
        {
            "$set": {"status": "resolved", "resolved_at": now, "updated_at": now},
            "$push": {"audit_log": {
                "action": "resolved", "actor_id": user["id"], "actor_name": user.get("name"), "timestamp": now,
            }},
        },
    )
    return await tickets_col.find_one({"id": ticket_id}, {"_id": 0})


@router.post("/{ticket_id}/reopen")
async def reopen_ticket(ticket_id: str, user: dict = Depends(get_current_user)):
    t = await tickets_col.find_one({"id": ticket_id}, {"_id": 0})
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if t.get("raised_by_id") != user["id"] and not _is_admin(user):
        raise HTTPException(status_code=403, detail="Only the raiser can reopen")
    if t.get("status") not in ("resolved", "closed"):
        raise HTTPException(status_code=400, detail="Can only reopen resolved/closed tickets")
    now = datetime.now(timezone.utc).isoformat()
    await tickets_col.update_one(
        {"id": ticket_id},
        {
            "$set": {"status": "open", "resolved_at": None, "updated_at": now},
            "$push": {"audit_log": {
                "action": "reopened", "actor_id": user["id"], "actor_name": user.get("name"), "timestamp": now,
            }},
        },
    )
    return await tickets_col.find_one({"id": ticket_id}, {"_id": 0})


@router.post("/{ticket_id}/rate")
async def rate_ticket(ticket_id: str, payload: RateRequest, user: dict = Depends(get_current_user)):
    t = await tickets_col.find_one({"id": ticket_id}, {"_id": 0})
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if t.get("raised_by_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Only the raiser can rate")
    if t.get("status") not in ("resolved", "closed"):
        raise HTTPException(status_code=400, detail="Can only rate after resolution")
    now = datetime.now(timezone.utc).isoformat()
    rating = {"stars": payload.stars, "comment": payload.comment, "rated_at": now}
    await tickets_col.update_one(
        {"id": ticket_id},
        {
            "$set": {"satisfaction_rating": rating, "updated_at": now},
            "$push": {"audit_log": {
                "action": "rated", "actor_id": user["id"], "actor_name": user.get("name"),
                "timestamp": now, "stars": payload.stars,
            }},
        },
    )
    return rating
