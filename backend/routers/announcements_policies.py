"""Phase 21.F — Announcements + Internal Policies Router.

Two related domains in one file for cohesion:
1. Announcements (company news feed with audience targeting + read receipts)
2. Internal Policies (employee handbook, versioned, with acknowledgments)
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from core.database import db, users_col
from core.auth import get_current_user

router = APIRouter(prefix="", tags=["Announcements & Policies"])

announcements_col = db["announcements"]
internal_policies_col = db["internal_policies"]
activity_log_col = db["activity_log"]


def _is_manager_or_admin(user: dict) -> bool:
    role = (user.get("role") or "").lower()
    rbac = (user.get("rbac_role") or "").lower()
    if role == "admin" or "*" in (user.get("permissions") or []):
        return True
    return any(k in rbac for k in ["admin", "owner", "head", "manager", "lead"])


def _can_publish(user: dict) -> bool:
    return _is_manager_or_admin(user)


# ════════════════════════════════════════════════════════════════
# ANNOUNCEMENTS
# ════════════════════════════════════════════════════════════════
VALID_PRIORITY = {"info", "important", "urgent"}
VALID_AUDIENCE = {"all", "department", "role", "specific_users"}


class AnnouncementCreate(BaseModel):
    title: str
    content: str
    priority: str = "info"
    target_audience: str = "all"
    department_ids: List[str] = Field(default_factory=list)
    role_keys: List[str] = Field(default_factory=list)
    user_ids: List[str] = Field(default_factory=list)
    expires_at: Optional[str] = None
    pinned: bool = False


class AnnouncementUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    priority: Optional[str] = None
    pinned: Optional[bool] = None
    expires_at: Optional[str] = None


def _audience_matches(announcement: dict, user: dict) -> bool:
    aud = announcement.get("target_audience", "all")
    if aud == "all":
        return True
    if aud == "department":
        return user.get("department") in (announcement.get("department_ids") or [])
    if aud == "role":
        return user.get("rbac_role") in (announcement.get("role_keys") or []) or user.get("role") in (announcement.get("role_keys") or [])
    if aud == "specific_users":
        return user["id"] in (announcement.get("user_ids") or [])
    return False


def _enrich_announcement(a: dict, current_user_id: Optional[str] = None) -> dict:
    out = dict(a)
    out.pop("_id", None)
    receipts = out.get("read_receipts") or []
    out["read_count"] = len(receipts)
    if current_user_id:
        out["i_read_it"] = any(r.get("user_id") == current_user_id for r in receipts)
    for k in ("posted_at", "expires_at", "created_at"):
        if isinstance(out.get(k), datetime):
            out[k] = out[k].isoformat()
    out["read_receipts"] = [
        {**r, "read_at": r["read_at"].isoformat() if isinstance(r.get("read_at"), datetime) else r.get("read_at")}
        for r in receipts
    ]
    return out


@router.get("/announcements")
async def list_announcements(
    for_me: bool = Query(False, alias="for"),
    pinned_only: bool = False,
    current_user: dict = Depends(get_current_user),
):
    """List announcements; pass ?for=me to filter to user's audience."""
    q: dict = {}
    if pinned_only:
        q["pinned"] = True

    cursor = announcements_col.find(q, {"_id": 0}).sort([("pinned", -1), ("posted_at", -1)])
    items = []
    async for a in cursor:
        if for_me and not _audience_matches(a, current_user):
            continue
        # Honour expiry
        if a.get("expires_at"):
            exp = a["expires_at"]
            if isinstance(exp, str):
                try:
                    exp_dt = datetime.fromisoformat(exp.replace("Z", "+00:00"))
                except ValueError:
                    exp_dt = None
            else:
                exp_dt = exp
            if exp_dt and exp_dt < datetime.now(timezone.utc):
                if for_me:
                    continue
        items.append(_enrich_announcement(a, current_user["id"]))
    return items


@router.post("/announcements")
async def create_announcement(payload: AnnouncementCreate, current_user: dict = Depends(get_current_user)):
    if not _can_publish(current_user):
        raise HTTPException(status_code=403, detail="Only managers / HR / admin can publish announcements")
    if payload.priority not in VALID_PRIORITY:
        raise HTTPException(status_code=400, detail=f"Invalid priority. Allowed: {sorted(VALID_PRIORITY)}")
    if payload.target_audience not in VALID_AUDIENCE:
        raise HTTPException(status_code=400, detail=f"Invalid audience. Allowed: {sorted(VALID_AUDIENCE)}")

    a = {
        "id": str(uuid.uuid4()),
        "title": payload.title.strip(),
        "content": payload.content.strip(),
        "priority": payload.priority,
        "target_audience": payload.target_audience,
        "department_ids": payload.department_ids,
        "role_keys": payload.role_keys,
        "user_ids": payload.user_ids,
        "expires_at": payload.expires_at,
        "pinned": bool(payload.pinned),
        "read_receipts": [],
        "posted_by": current_user["id"],
        "posted_by_name": current_user.get("name"),
        "posted_at": datetime.now(timezone.utc),
        "created_at": datetime.now(timezone.utc),
    }
    await announcements_col.insert_one(a)
    await activity_log_col.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "entity_type": "announcement",
        "entity_id": a["id"],
        "action": "announcement_created",
        "details": {"title": a["title"], "audience": a["target_audience"], "priority": a["priority"]},
        "created_at": datetime.now(timezone.utc),
    })
    return _enrich_announcement(a, current_user["id"])


@router.patch("/announcements/{announcement_id}/mark-read")
async def mark_announcement_read(announcement_id: str, current_user: dict = Depends(get_current_user)):
    a = await announcements_col.find_one({"id": announcement_id}, {"_id": 0})
    if not a:
        raise HTTPException(status_code=404, detail="Announcement not found")
    receipts = a.get("read_receipts") or []
    if any(r.get("user_id") == current_user["id"] for r in receipts):
        return {"message": "Already marked", "read_count": len(receipts)}
    new_receipt = {"user_id": current_user["id"], "user_name": current_user.get("name"), "read_at": datetime.now(timezone.utc)}
    await announcements_col.update_one(
        {"id": announcement_id},
        {"$push": {"read_receipts": new_receipt}},
    )
    return {"message": "Marked as read", "read_count": len(receipts) + 1}


@router.patch("/announcements/{announcement_id}")
async def update_announcement(announcement_id: str, payload: AnnouncementUpdate, current_user: dict = Depends(get_current_user)):
    if not _can_publish(current_user):
        raise HTTPException(status_code=403, detail="Only admin/HR can edit")
    updates = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    if not updates:
        return {"message": "No changes"}
    if "priority" in updates and updates["priority"] not in VALID_PRIORITY:
        raise HTTPException(status_code=400, detail="Invalid priority")
    updates["updated_at"] = datetime.now(timezone.utc)
    res = await announcements_col.update_one({"id": announcement_id}, {"$set": updates})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")
    return {"message": "Updated", "fields": list(updates.keys())}


@router.delete("/announcements/{announcement_id}")
async def delete_announcement(announcement_id: str, current_user: dict = Depends(get_current_user)):
    if not _can_publish(current_user):
        raise HTTPException(status_code=403, detail="Only admin/HR can delete")
    res = await announcements_col.delete_one({"id": announcement_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"message": "Deleted"}


# ════════════════════════════════════════════════════════════════
# INTERNAL POLICIES
# ════════════════════════════════════════════════════════════════
VALID_CATEGORY = {"HR", "IT", "Finance", "Code of Conduct", "Security", "Other"}
VALID_POLICY_STATUS = {"draft", "active", "archived"}


class PolicyCreate(BaseModel):
    title: str
    category: str = "HR"
    content: str
    requires_acknowledgment: bool = True
    effective_date: Optional[str] = None
    version: int = 1


class PolicyUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    content: Optional[str] = None
    requires_acknowledgment: Optional[bool] = None
    status: Optional[str] = None
    effective_date: Optional[str] = None


def _enrich_policy(p: dict, current_user_id: Optional[str] = None) -> dict:
    out = dict(p)
    out.pop("_id", None)
    acks = out.get("acknowledgments") or []
    out["acknowledgment_count"] = len(acks)
    if current_user_id:
        out["i_acknowledged"] = any(a.get("user_id") == current_user_id for a in acks)
    for k in ("effective_date", "created_at", "updated_at"):
        if isinstance(out.get(k), datetime):
            out[k] = out[k].isoformat()
    out["acknowledgments"] = [
        {**a, "acknowledged_at": a["acknowledged_at"].isoformat() if isinstance(a.get("acknowledged_at"), datetime) else a.get("acknowledged_at")}
        for a in acks
    ]
    return out


@router.get("/internal-policies")
async def list_policies(
    category: Optional[str] = None,
    active_only: bool = True,
    current_user: dict = Depends(get_current_user),
):
    q: dict = {}
    if active_only:
        q["status"] = "active"
    if category:
        q["category"] = category
    items = []
    async for p in internal_policies_col.find(q, {"_id": 0}).sort([("category", 1), ("title", 1), ("version", -1)]):
        items.append(_enrich_policy(p, current_user["id"]))
    return items


@router.get("/internal-policies/{policy_id}")
async def get_policy(policy_id: str, current_user: dict = Depends(get_current_user)):
    p = await internal_policies_col.find_one({"id": policy_id}, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Policy not found")
    return _enrich_policy(p, current_user["id"])


@router.post("/internal-policies")
async def create_policy(payload: PolicyCreate, current_user: dict = Depends(get_current_user)):
    if not _can_publish(current_user):
        raise HTTPException(status_code=403, detail="Only admin/HR can publish policies")
    if payload.category not in VALID_CATEGORY:
        raise HTTPException(status_code=400, detail=f"Invalid category. Allowed: {sorted(VALID_CATEGORY)}")
    p = {
        "id": str(uuid.uuid4()),
        "title": payload.title.strip(),
        "category": payload.category,
        "content": payload.content.strip(),
        "version": payload.version,
        "requires_acknowledgment": payload.requires_acknowledgment,
        "effective_date": payload.effective_date,
        "status": "active",
        "superseded_by": None,
        "acknowledgments": [],
        "created_by": current_user["id"],
        "created_by_name": current_user.get("name"),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    await internal_policies_col.insert_one(p)
    await activity_log_col.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "entity_type": "internal_policy",
        "entity_id": p["id"],
        "action": "policy_created",
        "details": {"title": p["title"], "category": p["category"], "version": p["version"]},
        "created_at": datetime.now(timezone.utc),
    })
    return _enrich_policy(p, current_user["id"])


@router.patch("/internal-policies/{policy_id}")
async def update_policy(policy_id: str, payload: PolicyUpdate, current_user: dict = Depends(get_current_user)):
    if not _can_publish(current_user):
        raise HTTPException(status_code=403, detail="Only admin/HR can edit")
    updates = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    if "status" in updates and updates["status"] not in VALID_POLICY_STATUS:
        raise HTTPException(status_code=400, detail="Invalid status")
    if "category" in updates and updates["category"] not in VALID_CATEGORY:
        raise HTTPException(status_code=400, detail="Invalid category")
    if not updates:
        return {"message": "No changes"}
    updates["updated_at"] = datetime.now(timezone.utc)
    res = await internal_policies_col.update_one({"id": policy_id}, {"$set": updates})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Policy not found")
    return {"message": "Updated", "fields": list(updates.keys())}


@router.post("/internal-policies/{policy_id}/acknowledge")
async def acknowledge_policy(policy_id: str, current_user: dict = Depends(get_current_user)):
    p = await internal_policies_col.find_one({"id": policy_id}, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Policy not found")
    if p.get("status") != "active":
        raise HTTPException(status_code=400, detail="Policy is not active")
    acks = p.get("acknowledgments") or []
    if any(a.get("user_id") == current_user["id"] for a in acks):
        return {"message": "Already acknowledged", "acknowledgment_count": len(acks)}
    ack = {
        "user_id": current_user["id"],
        "user_name": current_user.get("name"),
        "user_employee_id": current_user.get("employee_id"),
        "acknowledged_at": datetime.now(timezone.utc),
        # Lightweight signature hash for non-repudiation (no PKI here)
        "signature_hash": f"v{p.get('version', 1)}-{current_user['id'][:8]}-{int(datetime.now(timezone.utc).timestamp())}",
    }
    await internal_policies_col.update_one({"id": policy_id}, {"$push": {"acknowledgments": ack}})
    return {"message": "Acknowledged", "acknowledgment_count": len(acks) + 1, "signature_hash": ack["signature_hash"]}


@router.get("/internal-policies/{policy_id}/acknowledgments")
async def list_policy_acknowledgments(policy_id: str, current_user: dict = Depends(get_current_user)):
    if not _is_manager_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Managers only")
    p = await internal_policies_col.find_one({"id": policy_id}, {"_id": 0, "acknowledgments": 1})
    if not p:
        raise HTTPException(status_code=404, detail="Policy not found")
    # Count of all active internal users (potential acknowledgers)
    total_users = await users_col.count_documents({"user_type": "internal", "employment_status": "active"})
    return {
        "total_users": total_users,
        "acknowledged_count": len(p.get("acknowledgments") or []),
        "acknowledgments": [
            {**a, "acknowledged_at": a["acknowledged_at"].isoformat() if isinstance(a.get("acknowledged_at"), datetime) else a.get("acknowledged_at")}
            for a in (p.get("acknowledgments") or [])
        ],
    }


@router.post("/internal-policies/{policy_id}/new-version")
async def new_policy_version(policy_id: str, payload: PolicyCreate, current_user: dict = Depends(get_current_user)):
    """Supersede a policy with a new version. Old policy gets status=archived + superseded_by=new_id."""
    if not _can_publish(current_user):
        raise HTTPException(status_code=403, detail="Only admin/HR can supersede policies")
    old = await internal_policies_col.find_one({"id": policy_id}, {"_id": 0})
    if not old:
        raise HTTPException(status_code=404, detail="Original policy not found")

    new_version = (old.get("version") or 1) + 1
    new_id = str(uuid.uuid4())
    new_doc = {
        "id": new_id,
        "title": payload.title.strip(),
        "category": payload.category if payload.category in VALID_CATEGORY else old.get("category", "HR"),
        "content": payload.content.strip(),
        "version": new_version,
        "requires_acknowledgment": payload.requires_acknowledgment,
        "effective_date": payload.effective_date,
        "status": "active",
        "superseded_by": None,
        "supersedes": policy_id,
        "acknowledgments": [],
        "created_by": current_user["id"],
        "created_by_name": current_user.get("name"),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    await internal_policies_col.insert_one(new_doc)
    await internal_policies_col.update_one(
        {"id": policy_id},
        {"$set": {"status": "archived", "superseded_by": new_id, "updated_at": datetime.now(timezone.utc)}},
    )
    return _enrich_policy(new_doc, current_user["id"])
