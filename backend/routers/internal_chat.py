"""Phase 21 Slice 4 Sub-Slice B.1 — Internal Employee Chat.

Free-form internal team chat (DM + group) for HR/Marketing/IT/Sales.
Distinct from the pre-existing /api/chat client↔case-manager chat — uses
new collections (internal_chat_threads, internal_chat_messages) and
new namespace /api/internal-chat/* to preserve backward compatibility.
"""
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from core.database import db, users_col
from core.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/internal-chat", tags=["Internal Chat"])

threads_col = db["internal_chat_threads"]
messages_col = db["internal_chat_messages"]

EDIT_WINDOW_MIN = 15
ALLOWED_REACTIONS = {"👍", "❤️", "😂", "🎉", "👀", "✅"}


# ─────────────────────────── Models ────────────────────────────

class ThreadCreate(BaseModel):
    type: str = "dm"  # 'dm' | 'group'
    member_ids: List[str]
    title: Optional[str] = None


class MessageCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=5000)


class MessagePatch(BaseModel):
    body: str = Field(..., min_length=1, max_length=5000)


class ReactionToggle(BaseModel):
    emoji: str


class AddMembers(BaseModel):
    member_ids: List[str]


# ─────────────────────────── Helpers ────────────────────────────

def _is_admin(user: dict) -> bool:
    r = (user.get("rbac_role") or user.get("role") or "").lower()
    return r in ("admin_owner", "admin")


async def _thread_or_403(thread_id: str, user: dict, *, admin_can_read: bool = False) -> dict:
    t = await threads_col.find_one({"id": thread_id}, {"_id": 0})
    if not t:
        raise HTTPException(status_code=404, detail="Thread not found")
    if user["id"] not in (t.get("member_ids") or []):
        if not (admin_can_read and _is_admin(user)):
            raise HTTPException(status_code=403, detail="Not a member of this thread")
        logger.info("ADMIN-READ thread=%s by=%s", thread_id, user["id"])
    return t


async def _enrich_member(uid: str) -> dict:
    u = await users_col.find_one(
        {"id": uid},
        {"_id": 0, "id": 1, "name": 1, "email": 1, "designation": 1, "department": 1},
    )
    return u or {"id": uid, "name": "Unknown"}


# ─────────────────────────── Endpoints ────────────────────────────

@router.get("/threads")
async def list_threads(user: dict = Depends(get_current_user)):
    out = []
    async for t in threads_col.find({"member_ids": user["id"]}, {"_id": 0}).sort("last_message_at", -1).limit(200):
        t["members"] = [await _enrich_member(uid) for uid in (t.get("member_ids") or [])]
        out.append(t)
    return out


@router.post("/threads")
async def create_thread(payload: ThreadCreate, user: dict = Depends(get_current_user)):
    if payload.type not in ("dm", "group"):
        raise HTTPException(status_code=400, detail="type must be dm or group")
    members = list(dict.fromkeys([user["id"]] + payload.member_ids))
    if len(members) < 2:
        raise HTTPException(status_code=400, detail="Need at least 1 other member")

    if payload.type == "dm":
        if len(members) != 2:
            raise HTTPException(status_code=400, detail="DM must have exactly 2 members")
        existing = await threads_col.find_one(
            {"type": "dm", "member_ids": {"$all": members, "$size": 2}},
            {"_id": 0},
        )
        if existing:
            existing["members"] = [await _enrich_member(uid) for uid in existing["member_ids"]]
            return existing

    now = datetime.now(timezone.utc)
    thread_id = str(uuid.uuid4())
    doc = {
        "id": thread_id,
        "type": payload.type,
        "member_ids": members,
        "title": (payload.title or None) if payload.type == "group" else None,
        "created_by": user["id"],
        "created_at": now.isoformat(),
        "last_message_at": now.isoformat(),
        "last_message_preview": "",
        "unread_counts": {uid: 0 for uid in members},
    }
    await threads_col.insert_one(doc)
    doc.pop("_id", None)
    doc["members"] = [await _enrich_member(uid) for uid in members]
    return doc


@router.get("/threads/{thread_id}/messages")
async def list_messages(
    thread_id: str,
    before: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    user: dict = Depends(get_current_user),
):
    await _thread_or_403(thread_id, user, admin_can_read=True)
    flt: dict = {"thread_id": thread_id}
    if before:
        flt["created_at"] = {"$lt": before}
    out = []
    async for m in messages_col.find(flt, {"_id": 0}).sort("created_at", -1).limit(limit):
        out.append(m)
    return list(reversed(out))


@router.post("/threads/{thread_id}/messages")
async def send_message(thread_id: str, payload: MessageCreate, user: dict = Depends(get_current_user)):
    t = await _thread_or_403(thread_id, user)
    now = datetime.now(timezone.utc).isoformat()
    msg = {
        "id": str(uuid.uuid4()),
        "thread_id": thread_id,
        "sender_id": user["id"],
        "sender_name": user.get("name"),
        "body": payload.body.strip(),
        "reactions": [],
        "attachments": [],
        "created_at": now,
        "edited_at": None,
        "is_deleted": False,
    }
    await messages_col.insert_one(msg)
    unread_inc = {f"unread_counts.{uid}": 1 for uid in (t.get("member_ids") or []) if uid != user["id"]}
    set_part = {"last_message_at": now, "last_message_preview": payload.body.strip()[:120]}
    update = {"$set": set_part, "$inc": unread_inc} if unread_inc else {"$set": set_part}
    await threads_col.update_one({"id": thread_id}, update)
    msg.pop("_id", None)
    return msg


@router.patch("/messages/{message_id}")
async def edit_message(message_id: str, payload: MessagePatch, user: dict = Depends(get_current_user)):
    m = await messages_col.find_one({"id": message_id}, {"_id": 0})
    if not m:
        raise HTTPException(status_code=404, detail="Message not found")
    if m["sender_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Can only edit your own messages")
    if m.get("is_deleted"):
        raise HTTPException(status_code=400, detail="Cannot edit a deleted message")
    created_str = m["created_at"] if isinstance(m["created_at"], str) else m["created_at"].isoformat()
    created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
    if datetime.now(timezone.utc) - created > timedelta(minutes=EDIT_WINDOW_MIN):
        raise HTTPException(status_code=400, detail=f"Edit window of {EDIT_WINDOW_MIN} minutes elapsed")
    now = datetime.now(timezone.utc).isoformat()
    await messages_col.update_one(
        {"id": message_id},
        {"$set": {"body": payload.body.strip(), "edited_at": now}},
    )
    return await messages_col.find_one({"id": message_id}, {"_id": 0})


@router.delete("/messages/{message_id}")
async def delete_message(message_id: str, user: dict = Depends(get_current_user)):
    m = await messages_col.find_one({"id": message_id}, {"_id": 0})
    if not m:
        raise HTTPException(status_code=404, detail="Message not found")
    if m["sender_id"] != user["id"] and not _is_admin(user):
        raise HTTPException(status_code=403, detail="Can only delete your own messages")
    await messages_col.update_one(
        {"id": message_id},
        {"$set": {"is_deleted": True, "body": "[deleted]", "reactions": []}},
    )
    return {"ok": True}


@router.post("/threads/{thread_id}/read")
async def mark_read(thread_id: str, user: dict = Depends(get_current_user)):
    await _thread_or_403(thread_id, user)
    await threads_col.update_one(
        {"id": thread_id},
        {"$set": {f"unread_counts.{user['id']}": 0}},
    )
    return {"ok": True}


@router.post("/threads/{thread_id}/members")
async def add_members(thread_id: str, payload: AddMembers, user: dict = Depends(get_current_user)):
    t = await _thread_or_403(thread_id, user)
    if t.get("type") != "group":
        raise HTTPException(status_code=400, detail="Can only add members to group threads")
    if t.get("created_by") != user["id"] and not _is_admin(user):
        raise HTTPException(status_code=403, detail="Only the creator or admin can add members")
    new_ids = [uid for uid in payload.member_ids if uid not in (t.get("member_ids") or [])]
    if not new_ids:
        return {"added": 0}
    unread_init = {f"unread_counts.{uid}": 0 for uid in new_ids}
    await threads_col.update_one(
        {"id": thread_id},
        {"$push": {"member_ids": {"$each": new_ids}}, "$set": unread_init},
    )
    return {"added": len(new_ids), "new_ids": new_ids}


@router.post("/messages/{message_id}/reactions")
async def toggle_reaction(message_id: str, payload: ReactionToggle, user: dict = Depends(get_current_user)):
    if payload.emoji not in ALLOWED_REACTIONS:
        raise HTTPException(status_code=400, detail=f"Emoji must be one of {sorted(ALLOWED_REACTIONS)}")
    m = await messages_col.find_one({"id": message_id}, {"_id": 0})
    if not m:
        raise HTTPException(status_code=404, detail="Message not found")
    await _thread_or_403(m["thread_id"], user)
    reactions = m.get("reactions") or []
    target = next((r for r in reactions if r["emoji"] == payload.emoji), None)
    if target:
        if user["id"] in target["user_ids"]:
            target["user_ids"].remove(user["id"])
            if not target["user_ids"]:
                reactions = [r for r in reactions if r["emoji"] != payload.emoji]
        else:
            target["user_ids"].append(user["id"])
    else:
        reactions.append({"emoji": payload.emoji, "user_ids": [user["id"]]})
    await messages_col.update_one({"id": message_id}, {"$set": {"reactions": reactions}})
    return {"reactions": reactions}


@router.get("/unread-count")
async def total_unread(user: dict = Depends(get_current_user)):
    total = 0
    async for t in threads_col.find({"member_ids": user["id"]}, {"_id": 0, "unread_counts": 1}):
        total += (t.get("unread_counts") or {}).get(user["id"], 0)
    return {"total": total}


@router.get("/directory")
async def employee_directory(q: Optional[str] = Query(None), user: dict = Depends(get_current_user)):
    """Lightweight employee picker used by chat composer (autocomplete)."""
    flt: dict = {"id": {"$ne": user["id"]}}
    if q:
        flt["name"] = {"$regex": q, "$options": "i"}
    out = []
    async for u in users_col.find(flt, {"_id": 0, "id": 1, "name": 1, "email": 1, "designation": 1, "department": 1}).limit(50):
        out.append(u)
    return out
