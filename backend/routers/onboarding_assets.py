"""Phase 21.D — Onboarding Workflows + Assets Management.

Onboarding:
- Template CRUD (HR/admin)
- Workflow start for new employee
- Per-step completion with evidence

Assets:
- Asset master CRUD
- Issue/return flow with audit history
- Per-employee asset listing
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.database import db, users_col
from core.auth import get_current_user

router = APIRouter(prefix="", tags=["Onboarding & Assets"])

onb_templates_col = db["onboarding_templates"]
onb_workflows_col = db["onboarding_workflows"]
assets_col = db["assets"]
activity_col = db["activity_log"]


def _is_manager_or_admin(user: dict) -> bool:
    role = (user.get("role") or "").lower()
    rbac = (user.get("rbac_role") or "").lower()
    if role == "admin" or "*" in (user.get("permissions") or []):
        return True
    return any(k in rbac for k in ["admin", "owner", "head", "hr", "it"])


def _serialize(d: dict) -> dict:
    out = dict(d)
    out.pop("_id", None)
    for k in ("created_at", "updated_at", "started_at", "completed_at", "completed_at",
              "issued_at", "expected_return_date", "returned_at", "purchase_date"):
        if isinstance(out.get(k), datetime):
            out[k] = out[k].isoformat()
    return out


# ════════════════════════════════════════════════════
# ONBOARDING
# ════════════════════════════════════════════════════

VALID_STEP_TYPES = {"form", "document_upload", "acknowledgment", "manual_check"}
VALID_STEP_ROLES = {"employee", "hr", "it", "manager"}


class OnboardingStepTemplate(BaseModel):
    step_number: int
    name: str
    description: Optional[str] = ""
    type: str = "manual_check"
    assigned_to_role: str = "employee"
    required_fields: List[str] = Field(default_factory=list)


class TemplateCreate(BaseModel):
    name: str
    department_id: Optional[str] = None
    role_key: Optional[str] = None
    steps: List[OnboardingStepTemplate]


class WorkflowStart(BaseModel):
    employee_id: str
    template_id: str


class StepCompletion(BaseModel):
    evidence_url: Optional[str] = None
    notes: Optional[str] = ""


@router.get("/onboarding/templates")
async def list_templates(current_user: dict = Depends(get_current_user)):
    items = []
    async for t in onb_templates_col.find({"is_active": True}, {"_id": 0}).sort("name", 1):
        items.append(_serialize(t))
    return items


@router.post("/onboarding/templates")
async def create_template(payload: TemplateCreate, current_user: dict = Depends(get_current_user)):
    if not _is_manager_or_admin(current_user):
        raise HTTPException(status_code=403, detail="HR/admin only")
    if not payload.steps:
        raise HTTPException(status_code=400, detail="At least one step required")
    for step in payload.steps:
        if step.type not in VALID_STEP_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid step type: {step.type}")
        if step.assigned_to_role not in VALID_STEP_ROLES:
            raise HTTPException(status_code=400, detail=f"Invalid step role: {step.assigned_to_role}")
    tpl = {
        "id": str(uuid.uuid4()),
        "name": payload.name.strip(),
        "department_id": payload.department_id,
        "role_key": payload.role_key,
        "steps": [s.model_dump() for s in payload.steps],
        "is_active": True,
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc),
    }
    await onb_templates_col.insert_one(tpl)
    return _serialize(tpl)


@router.post("/onboarding/start")
async def start_workflow(payload: WorkflowStart, current_user: dict = Depends(get_current_user)):
    if not _is_manager_or_admin(current_user):
        raise HTTPException(status_code=403, detail="HR/admin only")
    emp = await users_col.find_one({"id": payload.employee_id}, {"_id": 0, "id": 1, "name": 1})
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    tpl = await onb_templates_col.find_one({"id": payload.template_id}, {"_id": 0})
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")

    steps = []
    for s in tpl.get("steps", []):
        steps.append({**s, "status": "pending", "completed_by": None, "completed_at": None, "evidence_url": None})

    wf = {
        "id": str(uuid.uuid4()),
        "employee_id": payload.employee_id,
        "employee_name": emp.get("name"),
        "template_id": payload.template_id,
        "template_name": tpl.get("name"),
        "status": "in_progress",
        "steps": steps,
        "started_by": current_user["id"],
        "started_at": datetime.now(timezone.utc),
        "completed_at": None,
        "audit_log": [{
            "action": "started",
            "actor_id": current_user["id"],
            "actor_name": current_user.get("name"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }],
    }
    await onb_workflows_col.insert_one(wf)
    return _serialize(wf)


@router.get("/onboarding/{workflow_id}")
async def get_workflow(workflow_id: str, current_user: dict = Depends(get_current_user)):
    wf = await onb_workflows_col.find_one({"id": workflow_id}, {"_id": 0})
    if not wf:
        raise HTTPException(status_code=404, detail="Not found")
    if wf["employee_id"] != current_user["id"] and not _is_manager_or_admin(current_user):
        raise HTTPException(status_code=403, detail="No access")
    return _serialize(wf)


@router.patch("/onboarding/{workflow_id}/step/{step_number}/complete")
async def complete_step(
    workflow_id: str,
    step_number: int,
    payload: StepCompletion,
    current_user: dict = Depends(get_current_user),
):
    wf = await onb_workflows_col.find_one({"id": workflow_id}, {"_id": 0})
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if wf["employee_id"] != current_user["id"] and not _is_manager_or_admin(current_user):
        raise HTTPException(status_code=403, detail="No access")

    steps = wf.get("steps", [])
    target_idx = next((i for i, s in enumerate(steps) if s.get("step_number") == step_number), None)
    if target_idx is None:
        raise HTTPException(status_code=404, detail=f"Step {step_number} not found")

    steps[target_idx]["status"] = "completed"
    steps[target_idx]["completed_by"] = current_user["id"]
    steps[target_idx]["completed_at"] = datetime.now(timezone.utc).isoformat()
    steps[target_idx]["evidence_url"] = payload.evidence_url
    steps[target_idx]["notes"] = payload.notes or ""

    all_done = all(s.get("status") == "completed" for s in steps)
    new_status = "completed" if all_done else "in_progress"
    updates = {
        "steps": steps,
        "status": new_status,
    }
    if all_done:
        updates["completed_at"] = datetime.now(timezone.utc)

    await onb_workflows_col.update_one(
        {"id": workflow_id},
        {"$set": updates, "$push": {"audit_log": {
            "action": f"step_{step_number}_completed",
            "actor_id": current_user["id"],
            "actor_name": current_user.get("name"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }}},
    )
    updated = await onb_workflows_col.find_one({"id": workflow_id}, {"_id": 0})
    return _serialize(updated)


@router.get("/employees/{employee_id}/onboarding")
async def employee_onboarding(employee_id: str, current_user: dict = Depends(get_current_user)):
    if employee_id != current_user["id"] and not _is_manager_or_admin(current_user):
        raise HTTPException(status_code=403, detail="No access")
    items = []
    async for w in onb_workflows_col.find({"employee_id": employee_id}, {"_id": 0}).sort("started_at", -1):
        items.append(_serialize(w))
    return items


# ════════════════════════════════════════════════════
# ASSETS
# ════════════════════════════════════════════════════

VALID_ASSET_TYPES = {"laptop", "phone", "access_card", "sim", "monitor", "headset", "tablet", "other"}
VALID_ASSET_STATUS = {"available", "issued", "in_repair", "retired"}
VALID_CONDITION = {"new", "good", "fair", "poor"}


class AssetCreate(BaseModel):
    asset_tag: str
    asset_type: str
    brand: Optional[str] = ""
    model: Optional[str] = ""
    serial_number: Optional[str] = ""
    purchase_date: Optional[str] = None
    purchase_cost_inr: Optional[int] = 0
    condition: str = "new"


class AssetIssue(BaseModel):
    employee_id: str
    expected_return_date: Optional[str] = None
    notes: Optional[str] = ""


class AssetReturn(BaseModel):
    condition: str = "good"
    notes: Optional[str] = ""


@router.get("/assets")
async def list_assets(
    status: Optional[str] = None,
    asset_type: Optional[str] = None,
    holder_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    if not _is_manager_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin/HR/IT only")
    q: dict = {}
    if status:
        q["status"] = status
    if asset_type:
        q["asset_type"] = asset_type
    if holder_id:
        q["current_holder_id"] = holder_id
    items = []
    async for a in assets_col.find(q, {"_id": 0}).sort("asset_tag", 1):
        items.append(_serialize(a))
    return items


@router.post("/assets")
async def create_asset(payload: AssetCreate, current_user: dict = Depends(get_current_user)):
    if not _is_manager_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin/HR/IT only")
    if payload.asset_type not in VALID_ASSET_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid asset_type")
    if payload.condition not in VALID_CONDITION:
        raise HTTPException(status_code=400, detail="Invalid condition")
    # Uniqueness check
    exist = await assets_col.find_one({"asset_tag": payload.asset_tag.strip().upper()})
    if exist:
        raise HTTPException(status_code=400, detail=f"asset_tag '{payload.asset_tag}' already exists")
    asset = {
        "id": str(uuid.uuid4()),
        "asset_tag": payload.asset_tag.strip().upper(),
        "asset_type": payload.asset_type,
        "brand": payload.brand or "",
        "model": payload.model or "",
        "serial_number": payload.serial_number or "",
        "purchase_date": payload.purchase_date,
        "purchase_cost_inr": payload.purchase_cost_inr or 0,
        "condition": payload.condition,
        "status": "available",
        "current_holder_id": None,
        "current_holder_name": None,
        "issued_at": None,
        "expected_return_date": None,
        "audit_log": [{
            "action": "created",
            "actor_id": current_user["id"],
            "actor_name": current_user.get("name"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    await assets_col.insert_one(asset)
    return _serialize(asset)


@router.post("/assets/{asset_id}/issue")
async def issue_asset(asset_id: str, payload: AssetIssue, current_user: dict = Depends(get_current_user)):
    if not _is_manager_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin/HR/IT only")
    asset = await assets_col.find_one({"id": asset_id}, {"_id": 0})
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    if asset.get("status") != "available":
        raise HTTPException(status_code=400, detail=f"Asset not available (current status: {asset.get('status')})")
    emp = await users_col.find_one({"id": payload.employee_id}, {"_id": 0, "id": 1, "name": 1})
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    updates = {
        "status": "issued",
        "current_holder_id": payload.employee_id,
        "current_holder_name": emp.get("name"),
        "issued_at": datetime.now(timezone.utc),
        "expected_return_date": payload.expected_return_date,
        "updated_at": datetime.now(timezone.utc),
    }
    await assets_col.update_one(
        {"id": asset_id},
        {"$set": updates, "$push": {"audit_log": {
            "action": "issued",
            "actor_id": current_user["id"],
            "actor_name": current_user.get("name"),
            "employee_id": payload.employee_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "notes": payload.notes or "",
        }}},
    )
    updated = await assets_col.find_one({"id": asset_id}, {"_id": 0})
    return _serialize(updated)


@router.post("/assets/{asset_id}/return")
async def return_asset(asset_id: str, payload: AssetReturn, current_user: dict = Depends(get_current_user)):
    if not _is_manager_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin/HR/IT only")
    asset = await assets_col.find_one({"id": asset_id}, {"_id": 0})
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    if asset.get("status") != "issued":
        raise HTTPException(status_code=400, detail="Asset is not currently issued")
    if payload.condition not in VALID_CONDITION:
        raise HTTPException(status_code=400, detail="Invalid condition")
    prev_holder = asset.get("current_holder_id")
    updates = {
        "status": "available",
        "current_holder_id": None,
        "current_holder_name": None,
        "issued_at": None,
        "expected_return_date": None,
        "condition": payload.condition,
        "updated_at": datetime.now(timezone.utc),
    }
    await assets_col.update_one(
        {"id": asset_id},
        {"$set": updates, "$push": {"audit_log": {
            "action": "returned",
            "actor_id": current_user["id"],
            "actor_name": current_user.get("name"),
            "prev_holder_id": prev_holder,
            "condition": payload.condition,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "notes": payload.notes or "",
        }}},
    )
    updated = await assets_col.find_one({"id": asset_id}, {"_id": 0})
    return _serialize(updated)


@router.get("/employees/{employee_id}/assets")
async def employee_assets(employee_id: str, current_user: dict = Depends(get_current_user)):
    if employee_id != current_user["id"] and not _is_manager_or_admin(current_user):
        raise HTTPException(status_code=403, detail="No access")
    items = []
    async for a in assets_col.find({"current_holder_id": employee_id}, {"_id": 0}).sort("issued_at", -1):
        items.append(_serialize(a))
    return items
