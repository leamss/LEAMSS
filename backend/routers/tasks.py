"""Phase 21.E — Employee Tasks Router (Kanban-style task management).

Endpoints under /api/tasks:
- GET /tasks                   list with filters (assignee, status, priority, dept)
- GET /tasks/{id}              detail
- POST /tasks                  create (requires assign permission)
- PATCH /tasks/{id}            update fields (status, assignee, priority, due, tags)
- POST /tasks/{id}/comments    add comment
- DELETE /tasks/{id}           soft-archive (set archived=True)

RBAC keys (added to catalog by Day 5 — for now fall back to legacy admin check):
- task.assign.any         super-admin / hr_head
- task.assign.team        any manager / dept-lead
- task.view.own           every employee
- task.view.team          managers
- task.view.all           admin / HR
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from core.database import db, users_col
from core.auth import get_current_user

router = APIRouter(prefix="/tasks", tags=["Tasks"])

tasks_col = db["employee_tasks"]
activity_log_col = db["activity_log"]

VALID_STATUS = {"todo", "in_progress", "review", "done", "blocked"}
VALID_PRIORITY = {"low", "medium", "high", "urgent"}


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    assignee_id: str
    status: str = "todo"
    priority: str = "medium"
    due_date: Optional[str] = None  # ISO date string
    tags: List[str] = Field(default_factory=list)


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assignee_id: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[str] = None
    tags: Optional[List[str]] = None


class TaskComment(BaseModel):
    text: str


def _is_manager_or_admin(user: dict) -> bool:
    role = (user.get("role") or "").lower()
    rbac = (user.get("rbac_role") or "").lower()
    if role == "admin" or "*" in (user.get("permissions") or []):
        return True
    # rbac_role suffixes that imply seniority
    return any(k in rbac for k in ["admin", "owner", "head", "manager", "lead"])


async def _can_view_task(user: dict, task: dict) -> bool:
    if _is_manager_or_admin(user):
        return True
    return task.get("assignee_id") == user["id"] or task.get("assigner_id") == user["id"]


async def _enrich(task: dict) -> dict:
    """Add denormalised assignee/assigner names + comment count."""
    out = dict(task)
    out.pop("_id", None)
    if task.get("assignee_id"):
        u = await users_col.find_one({"id": task["assignee_id"]}, {"_id": 0, "name": 1, "avatar_url": 1, "department": 1, "designation": 1})
        out["assignee"] = u or None
    if task.get("assigner_id"):
        u = await users_col.find_one({"id": task["assigner_id"]}, {"_id": 0, "name": 1, "avatar_url": 1})
        out["assigner"] = u or None
    out["comment_count"] = len(task.get("comments", []))
    # Normalise datetimes for JSON
    for k in ("created_at", "updated_at", "started_at", "completed_at"):
        if isinstance(task.get(k), datetime):
            out[k] = task[k].isoformat()
    # Comments datetimes
    if "comments" in out:
        out["comments"] = [
            {**c, "created_at": c["created_at"].isoformat() if isinstance(c.get("created_at"), datetime) else c.get("created_at")}
            for c in out["comments"]
        ]
    return out


# ────────────────────────────────────────────────────────────
# Routes
# ────────────────────────────────────────────────────────────
@router.get("")
async def list_tasks(
    assignee_id: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    department: Optional[str] = None,
    tag: Optional[str] = None,
    archived: bool = False,
    limit: int = 200,
    current_user: dict = Depends(get_current_user),
):
    q: dict = {"archived": archived}
    # Permission scoping: non-managers only see their own + tasks they assigned
    if not _is_manager_or_admin(current_user):
        q["$or"] = [{"assignee_id": current_user["id"]}, {"assigner_id": current_user["id"]}]

    if assignee_id == "me":
        q["assignee_id"] = current_user["id"]
        q.pop("$or", None)
    elif assignee_id:
        q["assignee_id"] = assignee_id
    if status and status in VALID_STATUS:
        q["status"] = status
    if priority and priority in VALID_PRIORITY:
        q["priority"] = priority
    if department:
        q["department"] = department
    if tag:
        q["tags"] = tag

    items = []
    cursor = tasks_col.find(q, {"_id": 0}).sort([("priority", -1), ("due_date", 1), ("created_at", -1)]).limit(limit)
    async for t in cursor:
        items.append(await _enrich(t))
    return items


@router.get("/stats")
async def task_stats(current_user: dict = Depends(get_current_user)):
    """Quick aggregate for dashboard tiles."""
    base_q: dict = {"archived": False}
    if not _is_manager_or_admin(current_user):
        base_q["$or"] = [{"assignee_id": current_user["id"]}, {"assigner_id": current_user["id"]}]

    by_status: dict = {s: 0 for s in VALID_STATUS}
    total = 0
    async for t in tasks_col.find(base_q, {"_id": 0, "status": 1}):
        s = t.get("status") or "todo"
        by_status[s] = by_status.get(s, 0) + 1
        total += 1

    overdue_q = {**base_q, "status": {"$nin": ["done"]}, "due_date": {"$lt": datetime.now(timezone.utc).date().isoformat()}}
    overdue = await tasks_col.count_documents(overdue_q)

    return {"total": total, "by_status": by_status, "overdue": overdue}


@router.get("/{task_id}")
async def get_task(task_id: str, current_user: dict = Depends(get_current_user)):
    t = await tasks_col.find_one({"id": task_id}, {"_id": 0})
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")
    if not await _can_view_task(current_user, t):
        raise HTTPException(status_code=403, detail="No access to this task")
    return await _enrich(t)


@router.post("")
async def create_task(payload: TaskCreate, current_user: dict = Depends(get_current_user)):
    if not _is_manager_or_admin(current_user) and payload.assignee_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Only managers can assign tasks to others")
    if payload.status not in VALID_STATUS:
        raise HTTPException(status_code=400, detail=f"Invalid status. Allowed: {sorted(VALID_STATUS)}")
    if payload.priority not in VALID_PRIORITY:
        raise HTTPException(status_code=400, detail=f"Invalid priority. Allowed: {sorted(VALID_PRIORITY)}")

    assignee = await users_col.find_one({"id": payload.assignee_id}, {"_id": 0, "id": 1, "department": 1})
    if not assignee:
        raise HTTPException(status_code=404, detail="Assignee not found")

    task = {
        "id": str(uuid.uuid4()),
        "title": payload.title.strip(),
        "description": (payload.description or "").strip(),
        "assignee_id": payload.assignee_id,
        "assigner_id": current_user["id"],
        "status": payload.status,
        "priority": payload.priority,
        "due_date": payload.due_date,
        "department": assignee.get("department"),
        "tags": payload.tags or [],
        "comments": [],
        "archived": False,
        "audit_history": [{
            "actor_id": current_user["id"],
            "actor_name": current_user.get("name"),
            "action": "created",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "started_at": None,
        "completed_at": None,
    }
    await tasks_col.insert_one(task)
    await activity_log_col.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "entity_type": "task",
        "entity_id": task["id"],
        "action": "task_created",
        "details": {"title": task["title"], "assignee_id": task["assignee_id"], "priority": task["priority"]},
        "created_at": datetime.now(timezone.utc),
    })
    return await _enrich(task)


@router.patch("/{task_id}")
async def update_task(task_id: str, payload: TaskUpdate, current_user: dict = Depends(get_current_user)):
    t = await tasks_col.find_one({"id": task_id}, {"_id": 0})
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")
    if not await _can_view_task(current_user, t):
        raise HTTPException(status_code=403, detail="No access to this task")

    updates_raw = payload.model_dump(exclude_unset=True)
    # Non-managers may only update status of their own tasks (cannot reassign/etc.)
    if not _is_manager_or_admin(current_user):
        allowed_keys = {"status", "tags"}
        bad = set(updates_raw.keys()) - allowed_keys
        if bad:
            raise HTTPException(status_code=403, detail=f"Cannot modify: {sorted(bad)} (managers only)")

    if "status" in updates_raw and updates_raw["status"] not in VALID_STATUS:
        raise HTTPException(status_code=400, detail="Invalid status")
    if "priority" in updates_raw and updates_raw["priority"] not in VALID_PRIORITY:
        raise HTTPException(status_code=400, detail="Invalid priority")

    # Status transitions: timestamps
    if updates_raw.get("status") == "in_progress" and not t.get("started_at"):
        updates_raw["started_at"] = datetime.now(timezone.utc)
    if updates_raw.get("status") == "done":
        updates_raw["completed_at"] = datetime.now(timezone.utc)
    if updates_raw.get("status") and updates_raw["status"] != "done" and t.get("completed_at"):
        updates_raw["completed_at"] = None  # reopened

    audit_entry = {
        "actor_id": current_user["id"],
        "actor_name": current_user.get("name"),
        "action": "updated",
        "changes": {k: v for k, v in updates_raw.items() if k not in ("updated_at", "started_at", "completed_at")},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    updates_raw["updated_at"] = datetime.now(timezone.utc)
    await tasks_col.update_one(
        {"id": task_id},
        {"$set": updates_raw, "$push": {"audit_history": audit_entry}},
    )

    await activity_log_col.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "entity_type": "task",
        "entity_id": task_id,
        "action": "task_updated",
        "details": audit_entry["changes"],
        "created_at": datetime.now(timezone.utc),
    })

    updated = await tasks_col.find_one({"id": task_id}, {"_id": 0})
    return await _enrich(updated)


@router.post("/{task_id}/comments")
async def add_comment(task_id: str, payload: TaskComment, current_user: dict = Depends(get_current_user)):
    t = await tasks_col.find_one({"id": task_id}, {"_id": 0})
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")
    if not await _can_view_task(current_user, t):
        raise HTTPException(status_code=403, detail="No access to this task")
    if not (payload.text or "").strip():
        raise HTTPException(status_code=400, detail="Comment text required")

    comment = {
        "id": str(uuid.uuid4()),
        "author_id": current_user["id"],
        "author_name": current_user.get("name"),
        "text": payload.text.strip(),
        "created_at": datetime.now(timezone.utc),
    }
    await tasks_col.update_one(
        {"id": task_id},
        {"$push": {"comments": comment}, "$set": {"updated_at": datetime.now(timezone.utc)}},
    )
    return {"message": "Comment added", "comment": {**comment, "created_at": comment["created_at"].isoformat()}}


@router.delete("/{task_id}")
async def archive_task(task_id: str, current_user: dict = Depends(get_current_user)):
    t = await tasks_col.find_one({"id": task_id}, {"_id": 0})
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")
    if not (_is_manager_or_admin(current_user) or t.get("assigner_id") == current_user["id"]):
        raise HTTPException(status_code=403, detail="Only managers / assigner can archive")

    await tasks_col.update_one(
        {"id": task_id},
        {"$set": {"archived": True, "updated_at": datetime.now(timezone.utc)}},
    )
    return {"message": "Archived"}
