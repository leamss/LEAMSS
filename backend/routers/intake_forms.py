"""Intake Form Builder - Admin manages product-specific intake forms with CM/Client role assignment"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException

from core.auth import get_current_user
from core.database import db, intake_forms_col, cases_col, notifications_col

router = APIRouter(prefix="/intake-forms", tags=["Intake Form Builder"])


class FieldModel(BaseModel):
    key: str
    label: str
    field_type: str = "text"  # text, select, date, textarea, file
    options: List[str] = []
    required: bool = False
    filled_by: str = "client"  # client, cm, both
    placeholder: str = ""
    help_text: str = ""


class SectionModel(BaseModel):
    id: str
    title: str
    fields: List[FieldModel]


class IntakeFormCreate(BaseModel):
    product_id: str
    product_name: str
    sections: List[SectionModel]


class IntakeFormUpdate(BaseModel):
    sections: List[SectionModel]


# ============ ADMIN: CRUD Intake Forms ============

@router.get("/product/{product_id}")
async def get_intake_form(product_id: str, current_user: dict = Depends(get_current_user)):
    """Get the custom intake form for a product"""
    form = await intake_forms_col.find_one({"product_id": product_id}, {"_id": 0})
    if not form:
        return {"product_id": product_id, "sections": [], "exists": False}
    if isinstance(form.get("updated_at"), datetime):
        form["updated_at"] = form["updated_at"].isoformat()
    if isinstance(form.get("created_at"), datetime):
        form["created_at"] = form["created_at"].isoformat()
    form["exists"] = True
    return form


@router.post("/save")
async def save_intake_form(data: IntakeFormCreate, current_user: dict = Depends(get_current_user)):
    """Create or update a product's intake form (Admin only)"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    sections_data = [s.dict() for s in data.sections]
    total_fields = sum(len(s["fields"]) for s in sections_data)

    existing = await intake_forms_col.find_one({"product_id": data.product_id})
    if existing:
        await intake_forms_col.update_one(
            {"product_id": data.product_id},
            {"$set": {
                "product_name": data.product_name,
                "sections": sections_data,
                "total_fields": total_fields,
                "updated_by": current_user["id"],
                "updated_at": datetime.now(timezone.utc),
            }}
        )
        return {"message": "Intake form updated", "total_fields": total_fields}
    else:
        await intake_forms_col.insert_one({
            "id": str(uuid.uuid4()),
            "product_id": data.product_id,
            "product_name": data.product_name,
            "sections": sections_data,
            "total_fields": total_fields,
            "created_by": current_user["id"],
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        })
        return {"message": "Intake form created", "total_fields": total_fields}


@router.get("/list")
async def list_intake_forms(current_user: dict = Depends(get_current_user)):
    """List all intake forms (Admin)"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    forms = await intake_forms_col.find({}, {"_id": 0, "sections": 0}).to_list(100)
    for f in forms:
        for dt_field in ["created_at", "updated_at"]:
            if isinstance(f.get(dt_field), datetime):
                f[dt_field] = f[dt_field].isoformat()
    return forms


# ============ CM + CLIENT: Fill Intake Data ============

@router.get("/case/{case_id}")
async def get_case_intake(case_id: str, current_user: dict = Depends(get_current_user)):
    """Get intake form + filled data for a case"""
    case = await cases_col.find_one({"id": case_id}, {"_id": 0})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if current_user["role"] == "client" and current_user["id"] != case.get("client_id"):
        raise HTTPException(status_code=403, detail="Access denied")

    product_id = case.get("product_id", "")

    # Get custom form for this product
    form = await intake_forms_col.find_one({"product_id": product_id}, {"_id": 0})

    # Get filled data from case
    intake_data = case.get("intake_data", {})
    intake_meta = case.get("intake_meta", {})  # {field_key: {filled_by, filled_by_name, filled_at}}

    sections = form.get("sections", []) if form else []

    # Filter fields based on role
    role = current_user["role"]
    for section in sections:
        for field in section.get("fields", []):
            fkey = field["key"]
            field["value"] = intake_data.get(fkey, "")
            meta = intake_meta.get(fkey, {})
            field["filled_by_user"] = meta.get("filled_by_name", "")
            field["filled_at"] = meta.get("filled_at", "")
            field["filled_by_role"] = meta.get("filled_by_role", "")

            # Determine editability
            if role == "admin":
                field["editable"] = True
            elif role == "case_manager":
                field["editable"] = field["filled_by"] in ("cm", "both")
            elif role == "client":
                field["editable"] = field["filled_by"] in ("client", "both")
            else:
                field["editable"] = False

    return {
        "case_id": case_id,
        "product_name": case.get("product_name", ""),
        "client_name": case.get("client_name", ""),
        "sections": sections,
        "has_form": bool(form),
    }


class IntakeDataSave(BaseModel):
    case_id: str
    data: dict  # {field_key: value}


@router.post("/case/save")
async def save_case_intake(payload: IntakeDataSave, current_user: dict = Depends(get_current_user)):
    """Save intake form data for a case (CM or Client based on field permissions)"""
    case = await cases_col.find_one({"id": payload.case_id}, {"_id": 0})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if current_user["role"] == "client" and current_user["id"] != case.get("client_id"):
        raise HTTPException(status_code=403, detail="Access denied")

    # Get form to validate permissions
    product_id = case.get("product_id", "")
    form = await intake_forms_col.find_one({"product_id": product_id}, {"_id": 0})

    # Build field permission map
    field_perms = {}
    if form:
        for section in form.get("sections", []):
            for field in section.get("fields", []):
                field_perms[field["key"]] = field.get("filled_by", "client")

    role = current_user["role"]
    existing_data = case.get("intake_data", {})
    existing_meta = case.get("intake_meta", {})
    now = datetime.now(timezone.utc).isoformat()

    updated_fields = []
    for key, value in payload.data.items():
        perm = field_perms.get(key, "both")
        allowed = (role == "admin" or
                   (role == "case_manager" and perm in ("cm", "both")) or
                   (role == "client" and perm in ("client", "both")))
        if allowed:
            existing_data[key] = value
            existing_meta[key] = {
                "filled_by": current_user["id"],
                "filled_by_name": current_user.get("name", ""),
                "filled_by_role": role,
                "filled_at": now,
            }
            updated_fields.append(key)

    await cases_col.update_one(
        {"id": payload.case_id},
        {"$set": {"intake_data": existing_data, "intake_meta": existing_meta}}
    )

    # Notify the other party
    if role == "case_manager" and case.get("client_id") and updated_fields:
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": case["client_id"],
            "title": "Case Information Updated",
            "message": f"Your Case Manager updated {len(updated_fields)} field(s) in your case information.",
            "type": "intake_update",
            "read": False,
            "created_at": datetime.now(timezone.utc),
        })

    return {"message": f"{len(updated_fields)} field(s) saved", "updated_fields": updated_fields}
