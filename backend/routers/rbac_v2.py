"""Phase 22 — RBAC v2 endpoints. Capability Packs + Feature Overrides + Templates + Audit log."""
import uuid
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from core.database import db
from core.auth import get_current_user
from core.rbac.capability_packs_data import (
    CAPABILITY_PACKS, FEATURE_CATALOG, DEPT_TO_PACKS,
)
from core.rbac.capability_service import CapabilityService, is_admin_actor

router = APIRouter(prefix="/rbac", tags=["RBAC v2 — Capability Packs"])

users_col = db["users"]
audit_col = db["rbac_audit_log"]
templates_col = db["rbac_role_templates"]
packs_col = db["capability_packs"]
feature_catalog_col = db["feature_catalog"]


# ─────────────────── Schemas ───────────────────

class PacksUpdate(BaseModel):
    packs: List[str]
    reason: str = Field(min_length=1)


class OverridesUpdate(BaseModel):
    granted: List[str] = []
    revoked: List[str] = []
    reason: str = Field(min_length=1)


class PromoteRequest(BaseModel):
    add_packs: List[str] = []
    add_features: List[str] = []
    reason: str = Field(min_length=1)


class DemoteRequest(BaseModel):
    remove_packs: List[str] = []
    remove_features: List[str] = []
    reason: str = Field(min_length=1)


class TemplateCreate(BaseModel):
    name: str
    description: str = ""
    capability_packs: List[str]
    feature_overrides: dict = {"granted": [], "revoked": []}


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    capability_packs: Optional[List[str]] = None
    feature_overrides: Optional[dict] = None


class ApplyTemplate(BaseModel):
    template_id: str
    reason: str = Field(min_length=1)


def _require_admin(user: dict):
    if not is_admin_actor(user):
        raise HTTPException(status_code=403, detail="admin / admin_owner role required")


# ─────────────────── Catalogs ───────────────────

@router.get("/packs")
async def list_packs(user: dict = Depends(get_current_user)):
    """All 9 packs with their feature_ids. Visible to any logged-in staff."""
    out = []
    for p in CAPABILITY_PACKS:
        feature_ids = [f["feature_id"] for f in FEATURE_CATALOG if p["pack_id"] in f["default_packs"]]
        out.append({**p, "feature_ids": sorted(feature_ids), "feature_count": len(feature_ids)})
    return out


@router.get("/feature-catalog")
async def list_features(
    category: Optional[str] = None,
    search: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """Full feature catalog. Optional filters: category, search."""
    items = FEATURE_CATALOG
    if category:
        items = [f for f in items if f["category"] == category]
    if search:
        q = search.lower()
        items = [f for f in items if q in f["feature_id"].lower() or q in f["name"].lower() or q in f.get("description", "").lower()]
    # Group by category
    by_cat: dict = {}
    for f in items:
        by_cat.setdefault(f["category"], []).append(f)
    return {"total": len(items), "by_category": by_cat, "items": items}


@router.get("/smart-defaults")
async def smart_defaults(
    department: Optional[str] = None,
    legacy_role: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """Recommended pack list when creating/changing a user."""
    return {
        "department": department,
        "legacy_role": legacy_role,
        "recommended_packs": CapabilityService.smart_default_packs(department, legacy_role),
        "dept_mapping": DEPT_TO_PACKS,
    }


# ─────────────────── Effective state ───────────────────

@router.get("/users/{user_id}/effective-capabilities")
async def get_effective(user_id: str, user: dict = Depends(get_current_user)):
    """Compute live effective state. Admin OR self."""
    if not is_admin_actor(user) and user.get("id") != user_id:
        raise HTTPException(status_code=403, detail="admin or self only")
    return await CapabilityService.get_effective_state(user_id)


# ─────────────────── Mutations ───────────────────

@router.patch("/users/{user_id}/capability-packs")
async def update_packs(user_id: str, payload: PacksUpdate, user: dict = Depends(get_current_user)):
    return await CapabilityService.apply_packs(user, user_id, payload.packs, payload.reason)


@router.patch("/users/{user_id}/feature-overrides")
async def update_overrides(user_id: str, payload: OverridesUpdate, user: dict = Depends(get_current_user)):
    return await CapabilityService.apply_overrides(user, user_id, payload.granted, payload.revoked, payload.reason)


@router.post("/users/{user_id}/promote")
async def promote(user_id: str, payload: PromoteRequest, user: dict = Depends(get_current_user)):
    return await CapabilityService.promote(user, user_id, payload.add_packs, payload.add_features, payload.reason)


@router.post("/users/{user_id}/demote")
async def demote(user_id: str, payload: DemoteRequest, user: dict = Depends(get_current_user)):
    return await CapabilityService.demote(user, user_id, payload.remove_packs, payload.remove_features, payload.reason)


# ─────────────────── Audit ───────────────────

@router.get("/audit-log")
async def list_audit(
    target_user_id: Optional[str] = None,
    actor_id: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = Query(50, le=200),
    skip: int = 0,
    user: dict = Depends(get_current_user),
):
    _require_admin(user)
    query = {}
    if target_user_id:
        query["target_user_id"] = target_user_id
    if actor_id:
        query["actor_id"] = actor_id
    if action:
        query["action"] = action
    items = []
    async for e in audit_col.find(query, {"_id": 0}).sort("timestamp", -1).skip(skip).limit(limit):
        items.append(e)
    total = await audit_col.count_documents(query)
    return {"total": total, "items": items}


# ─────────────────── Templates ───────────────────

@router.get("/templates")
async def list_templates(user: dict = Depends(get_current_user)):
    _require_admin(user)
    items = []
    async for t in templates_col.find({"is_active": {"$ne": False}}, {"_id": 0}).sort("name", 1):
        items.append(t)
    return items


@router.post("/templates", status_code=201)
async def create_template(payload: TemplateCreate, user: dict = Depends(get_current_user)):
    _require_admin(user)
    CapabilityService._validate_packs(payload.capability_packs, user)
    overrides = payload.feature_overrides or {"granted": [], "revoked": []}
    CapabilityService._validate_features((overrides.get("granted") or []) + (overrides.get("revoked") or []))
    now = datetime.now(timezone.utc)
    tpl = {
        "id": str(uuid.uuid4()),
        "name": payload.name,
        "description": payload.description,
        "capability_packs": payload.capability_packs,
        "feature_overrides": overrides,
        "created_by": user.get("id"),
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "is_active": True,
    }
    await templates_col.insert_one(tpl)
    return tpl


@router.patch("/templates/{template_id}")
async def update_template(template_id: str, payload: TemplateUpdate, user: dict = Depends(get_current_user)):
    _require_admin(user)
    set_doc = {k: v for k, v in payload.model_dump(exclude_unset=True).items()}
    if "capability_packs" in set_doc:
        CapabilityService._validate_packs(set_doc["capability_packs"], user)
    if "feature_overrides" in set_doc:
        overrides = set_doc["feature_overrides"] or {"granted": [], "revoked": []}
        CapabilityService._validate_features((overrides.get("granted") or []) + (overrides.get("revoked") or []))
    set_doc["updated_at"] = datetime.now(timezone.utc).isoformat()
    res = await templates_col.update_one({"id": template_id}, {"$set": set_doc})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    return await templates_col.find_one({"id": template_id}, {"_id": 0})


@router.delete("/templates/{template_id}")
async def delete_template(template_id: str, user: dict = Depends(get_current_user)):
    _require_admin(user)
    res = await templates_col.update_one({"id": template_id}, {"$set": {"is_active": False}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"ok": True}


@router.post("/users/{user_id}/apply-template")
async def apply_template_endpoint(user_id: str, payload: ApplyTemplate, user: dict = Depends(get_current_user)):
    return await CapabilityService.apply_template(user, user_id, payload.template_id, payload.reason)
