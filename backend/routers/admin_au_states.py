"""Phase 19.4d — Admin AU States router.

Admin-only endpoints to seed + refresh AU state aggregations.
All writes register Phase 19.6 revocable batches.
"""
from __future__ import annotations

import os
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient

from core.auth import get_current_user
from seeds.au_states import seed_au_states
from services.state_aggregation_service import (
    refresh_all_states,
    refresh_state_data,
)

_db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
router = APIRouter(prefix="/admin/au-states", tags=["admin-au-states"])


def _ensure_admin(user: Dict[str, Any]) -> None:
    role = (user.get("rbac_role") or user.get("role") or "").lower()
    if role not in {"admin", "admin_owner", "super_admin"}:
        raise HTTPException(403, "Admin only")


@router.post("/seed")
async def seed_states(current_user: Dict[str, Any] = Depends(get_current_user)):
    _ensure_admin(current_user)
    return await seed_au_states(_db)


@router.post("/{state_code}/refresh")
async def refresh_one(
    state_code: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    _ensure_admin(current_user)
    result = await refresh_state_data(_db, state_code)
    if not result.get("ok"):
        raise HTTPException(404, result.get("error", "Refresh failed"))
    return result


@router.post("/refresh-all")
async def refresh_all(current_user: Dict[str, Any] = Depends(get_current_user)):
    _ensure_admin(current_user)
    return {"results": await refresh_all_states(_db)}


@router.get("/")
async def list_states(current_user: Dict[str, Any] = Depends(get_current_user)):
    _ensure_admin(current_user)
    items = []
    async for s in _db["au_states_master"].find({}, {"_id": 0}).sort("state_code", 1):
        items.append(s)
    return {"items": items, "total": len(items)}
