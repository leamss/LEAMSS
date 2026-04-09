"""Canned Responses Router — Pre-saved reply templates"""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from core.database import canned_responses_col
from core.auth import get_current_user

router = APIRouter(prefix="/canned-responses", tags=["Canned Responses"])


class CannedResponseCreate(BaseModel):
    title: str
    content: str
    category: str = "general"
    shortcut: str = ""
    is_shared: bool = False


@router.post("")
async def create_response(request: CannedResponseCreate, current_user: dict = Depends(get_current_user)):
    """Create a canned response"""
    if current_user["role"] not in ["admin", "case_manager"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    resp = {
        "id": str(uuid.uuid4()), "title": request.title,
        "content": request.content, "category": request.category,
        "shortcut": request.shortcut, "is_shared": request.is_shared,
        "user_id": current_user["id"], "user_name": current_user["name"],
        "usage_count": 0, "created_at": datetime.now(timezone.utc)
    }
    await canned_responses_col.insert_one(resp)
    resp.pop("_id", None)
    resp["created_at"] = resp["created_at"].isoformat()
    return resp


@router.get("")
async def list_responses(current_user: dict = Depends(get_current_user)):
    """List canned responses (own + shared)"""
    query = {"$or": [{"user_id": current_user["id"]}, {"is_shared": True}]}
    responses = await canned_responses_col.find(query, {"_id": 0}).sort("usage_count", -1).to_list(200)
    for r in responses:
        if isinstance(r.get("created_at"), datetime):
            r["created_at"] = r["created_at"].isoformat()
    return responses


@router.put("/{resp_id}")
async def update_response(resp_id: str, request: CannedResponseCreate, current_user: dict = Depends(get_current_user)):
    """Update a canned response"""
    existing = await canned_responses_col.find_one({"id": resp_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Not found")
    if existing.get("user_id") != current_user["id"] and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    await canned_responses_col.update_one({"id": resp_id}, {"$set": {
        "title": request.title, "content": request.content,
        "category": request.category, "shortcut": request.shortcut,
        "is_shared": request.is_shared
    }})
    return {"message": "Updated"}


@router.delete("/{resp_id}")
async def delete_response(resp_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a canned response"""
    existing = await canned_responses_col.find_one({"id": resp_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Not found")
    if existing.get("user_id") != current_user["id"] and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    await canned_responses_col.delete_one({"id": resp_id})
    return {"message": "Deleted"}


@router.post("/{resp_id}/use")
async def use_response(resp_id: str, current_user: dict = Depends(get_current_user)):
    """Increment usage count when a canned response is used"""
    await canned_responses_col.update_one({"id": resp_id}, {"$inc": {"usage_count": 1}})
    resp = await canned_responses_col.find_one({"id": resp_id}, {"_id": 0})
    if not resp:
        raise HTTPException(status_code=404, detail="Not found")
    if isinstance(resp.get("created_at"), datetime):
        resp["created_at"] = resp["created_at"].isoformat()
    return resp
