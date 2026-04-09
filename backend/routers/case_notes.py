"""Case Notes & Tags Router"""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from core.database import case_notes_col, cases_col
from core.auth import get_current_user
from core.services import log_activity

router = APIRouter(prefix="/case-notes", tags=["Case Notes"])


class NoteCreate(BaseModel):
    case_id: str
    content: str
    color: str = "yellow"
    is_pinned: bool = False


class TagUpdate(BaseModel):
    case_id: str
    tags: List[str]


@router.post("")
async def create_note(request: NoteCreate, current_user: dict = Depends(get_current_user)):
    """Add a sticky note to a case"""
    if current_user["role"] not in ["admin", "case_manager"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    note = {
        "id": str(uuid.uuid4()), "case_id": request.case_id,
        "content": request.content, "color": request.color,
        "is_pinned": request.is_pinned,
        "author_id": current_user["id"], "author_name": current_user["name"],
        "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc)
    }
    await case_notes_col.insert_one(note)
    note.pop("_id", None)
    note["created_at"] = note["created_at"].isoformat()
    note["updated_at"] = note["updated_at"].isoformat()
    await log_activity(current_user["id"], current_user["name"], "add_case_note", "case", request.case_id, {"color": request.color})
    return note


@router.get("/case/{case_id}")
async def get_notes(case_id: str, current_user: dict = Depends(get_current_user)):
    """Get all notes for a case"""
    notes = await case_notes_col.find({"case_id": case_id}, {"_id": 0}).sort("created_at", -1).to_list(100)
    for n in notes:
        for f in ["created_at", "updated_at"]:
            if isinstance(n.get(f), datetime):
                n[f] = n[f].isoformat()
    return notes


@router.put("/{note_id}")
async def update_note(note_id: str, request: NoteCreate, current_user: dict = Depends(get_current_user)):
    """Update a note"""
    if current_user["role"] not in ["admin", "case_manager"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    await case_notes_col.update_one({"id": note_id}, {"$set": {
        "content": request.content, "color": request.color,
        "is_pinned": request.is_pinned, "updated_at": datetime.now(timezone.utc)
    }})
    return {"message": "Updated"}


@router.delete("/{note_id}")
async def delete_note(note_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a note"""
    if current_user["role"] not in ["admin", "case_manager"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    await case_notes_col.delete_one({"id": note_id})
    return {"message": "Deleted"}


# ============ TAGS ============

@router.post("/tags")
async def update_case_tags(request: TagUpdate, current_user: dict = Depends(get_current_user)):
    """Set tags for a case"""
    if current_user["role"] not in ["admin", "case_manager"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    await cases_col.update_one({"id": request.case_id}, {"$set": {"tags": request.tags}})
    await log_activity(current_user["id"], current_user["name"], "update_case_tags", "case", request.case_id, {"tags": request.tags})
    return {"message": "Tags updated", "tags": request.tags}


@router.get("/tags/{case_id}")
async def get_case_tags(case_id: str, current_user: dict = Depends(get_current_user)):
    """Get tags for a case"""
    case = await cases_col.find_one({"id": case_id}, {"_id": 0, "tags": 1})
    return {"tags": case.get("tags", []) if case else []}
