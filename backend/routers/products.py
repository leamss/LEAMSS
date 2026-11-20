"""Products Router — Phase 4C Unified.

A unified product carries both workflow-builder fields AND cost-structure fields
(country, visa_type, service_price, cost_allocations, success_bonuses, computed margin).
"""
import os
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from core.database import products_col, workflow_steps_col, db
from core.auth import get_current_user
from core.services import log_activity
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
router = APIRouter(prefix="/products", tags=["Products"])


def _extract_commissions_v2(cost_allocations: list, explicit_v2: Optional[dict] = None) -> dict:
    """Extracts or derives commissions_v2 mapping for the 4 core commission roles:
    salesperson / sales_user, case_manager, partner_internal, partner_external.
    """
    comm = dict(explicit_v2 or {})
    for a in (cost_allocations or []):
        cat = str(a.get("vendor_category") or "").strip().lower()
        ptype = a.get("payment_type", "percentage")
        if ptype == "flat":
            val = float(a.get("amount") if a.get("amount") is not None and str(a.get("amount")) != "" else (a.get("rate") or 0))
        else:
            val = float(a.get("rate") if a.get("rate") is not None and str(a.get("rate")) != "" else (a.get("amount") or 0))
        entry = {
            "type": ptype,
            "rate": val if ptype == "percentage" else 0.0,
            "amount": val if ptype == "flat" else 0.0,
            "flat_amount": val if ptype == "flat" else 0.0,
            "label": a.get("label") or cat,
            "is_optional": bool(a.get("is_optional", False))
        }
        if cat in ("sales_commission", "salesperson", "sales_user"):
            comm["sales_user"] = entry
            comm["salesperson"] = entry
        elif cat in ("case_manager", "cm"):
            comm["case_manager"] = entry
        elif cat in ("internal_partner", "partner_internal"):
            comm["partner_internal"] = entry
            comm["internal_partner"] = entry
        elif cat in ("external_partner", "partner_external"):
            comm["partner_external"] = entry
            comm["external_partner"] = entry
    return comm


def _compute_margin(service_price: float, cost_allocations: list, success_bonuses: list) -> dict:
    sp = float(service_price or 0)
    base = 0.0
    for a in (cost_allocations or []):
        if a.get("is_optional"):
            continue
        # Percentage and flat both store the value in `amount` (rate is a fallback alias)
        val = float(a.get("rate") if a.get("rate") is not None else a.get("amount", 0) or 0)
        if a.get("payment_type") == "percentage":
            base += sp * val / 100.0
        else:
            base += val
    margin = sp - base
    # Phase 4C — Success bonus field is `bonus_amount` (matches allocations_logic), fall back to `amount`
    max_bonus = sum(
        float((b.get("bonus_amount") if b.get("bonus_amount") is not None else b.get("amount", 0)) or 0)
        for b in (success_bonuses or [])
    )
    return {
        "expected_base_cost": round(base, 2),
        "expected_margin": round(margin, 2),
        "expected_margin_pct": round((margin / sp * 100), 2) if sp > 0 else 0,
        "max_bonus_payout": round(max_bonus, 2),
    }



@router.get("")
async def get_products(
    include_archived: bool = False,
    category: Optional[str] = None,
    country: Optional[str] = None,
    is_pre_assessment: Optional[bool] = None,
    current_user: dict = Depends(get_current_user)
):
    """Phase 20.2 — extended with filters + archived exclusion by default."""
    q: Dict[str, Any] = {}
    if not include_archived:
        q["archived_at"] = None
    if category:
        q["$or"] = [{"category": category}, {"_category_v2": category}]
    if country:
        q["country"] = country
    if is_pre_assessment is not None:
        q["is_pre_assessment"] = bool(is_pre_assessment)
    products = await products_col.find(q, {"_id": 0}).to_list(200)
    for p in products:
        steps = await workflow_steps_col.find({"product_id": p["id"]}, {"_id": 0}).sort("step_order", 1).to_list(100)
        p["workflow_steps"] = steps
        for k in ("created_at", "updated_at", "archived_at"):
            if isinstance(p.get(k), datetime):
                p[k] = p[k].isoformat()
    return products


@router.get("/{product_id}")
async def get_product(product_id: str, current_user: dict = Depends(get_current_user)):
    product = await products_col.find_one({"id": product_id}, {"_id": 0})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    steps = await workflow_steps_col.find({"product_id": product_id}, {"_id": 0}).sort("step_order", 1).to_list(100)
    product["workflow_steps"] = steps
    return product


class ProductAiResearchRequest(BaseModel):
    country: str
    visa_name: str
    category: Optional[str] = "skilled_migration"
    visa_subclass: Optional[str] = ""
    government_url: Optional[str] = None
    migrate_page_url: Optional[str] = None
    additional_context: Optional[str] = None

    class Config:
        extra = "forbid"


@router.post("/ai-research")
async def ai_research_product(
    payload: ProductAiResearchRequest,
    current_user: dict = Depends(get_current_user)
):
    role = current_user.get("role") or current_user.get("rbac_role")
    permissions = current_user.get("permissions") or []
    if role not in ("admin", "super_admin", "admin_owner") and "product_cost.manage.any" not in permissions and "system.user_manage.any" not in permissions:
        raise HTTPException(status_code=403, detail="Admin authorization required")
    try:
        from services.product_master_ai_service import research_product_with_ai
        result = await research_product_with_ai(
            country=payload.country,
            visa_name=payload.visa_name,
            category=payload.category or "skilled_migration",
            visa_subclass=payload.visa_subclass or "",
            government_url=payload.government_url,
            migrate_page_url=payload.migrate_page_url,
            additional_context=payload.additional_context,
        )
        return result
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("Product AI research failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{product_id}/verify")
async def verify_product_master(
    product_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Admin-only: Mark Product Master record as verified with audit trail."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    now_iso = datetime.now(timezone.utc).isoformat()
    res = await products_col.update_one(
        {"id": product_id},
        {"$set": {
            "last_verified_at": now_iso,
            "last_verified_by": current_user.get("name") or current_user.get("id"),
            "status": "active",
            "updated_at": datetime.now(timezone.utc),
        }}
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    await log_activity(
        current_user["id"],
        current_user.get("name", "Admin"),
        "verified",
        "product",
        product_id,
        f"Verified Product Master at {now_iso}"
    )
    return {"message": "Product verified successfully", "last_verified_at": now_iso}


@router.post("")
async def create_product(data: dict, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    sp = float(data.get("service_price") or data.get("base_fee") or 0)
    cost_allocations = data.get("cost_allocations") or []
    success_bonuses = data.get("success_bonuses") or []
    product = {
        "id": str(uuid.uuid4()),
        "name": data["name"],
        "description": data.get("description", ""),
        "category": data.get("category", "immigration"),
        "country": data.get("country") or "",
        "visa_type": data.get("visa_type") or "",
        "base_fee": sp,
        "service_price": sp,
        "commission_rate": data.get("commission_rate", 0),
        "commission_type": data.get("commission_type", "percentage"),
        "cost_allocations": cost_allocations,
        "success_bonuses": success_bonuses,
        "discount_coupons": data.get("discount_coupons") or [],  # 👈 NEW — admin-defined coupons for this product
        "packages": data.get("packages") or [   # NEW — default 3 package template
            {"id": str(uuid.uuid4()), "package_type": "standard", "name": "Standard Package", "price": 0, "description": "", "is_active": True,
            "payment_methods": {"full_payment": {"enabled": True}, "split_50_50": {"enabled": False, "first_pct": 50, "trigger_condition": ""}, "installments": {"enabled": False, "max_installments": 5}}},
            {"id": str(uuid.uuid4()), "package_type": "smart", "name": "Smart Package", "price": 0, "description": "", "is_active": True,
            "payment_methods": {"full_payment": {"enabled": True}, "split_50_50": {"enabled": False, "first_pct": 50, "trigger_condition": ""}, "installments": {"enabled": False, "max_installments": 5}}},
            {"id": str(uuid.uuid4()), "package_type": "premium", "name": "Premium Package", "price": 0, "description": "", "is_active": True,
            "payment_methods": {"full_payment": {"enabled": True}, "split_50_50": {"enabled": False, "first_pct": 50, "trigger_condition": ""}, "installments": {"enabled": False, "max_installments": 5}}},
        ],
        "requires_partner_info": bool(data.get("requires_partner_info", False)),
        # Phase 20.2 — Sales Flow Settings
        "is_pre_assessment": bool(data.get("is_pre_assessment", False)),
        "pre_assessment_fee_inr": (
            float(data["pre_assessment_fee_inr"])
            if data.get("is_pre_assessment", True) and data.get("pre_assessment_fee_inr") is not None and str(data.get("pre_assessment_fee_inr")).strip() != ""
            else None
        ),
        "pre_assessment_fee_currency": data.get("pre_assessment_fee_currency") or "INR",
        "visa_subclass": data.get("visa_subclass") or "",
        "assessing_body_code": data.get("assessing_body_code") or "",
        "workflow_id": data.get("workflow_id") or None,
        "workflow_steps_count": data.get("workflow_steps_count") or 0,
        "_category_v2": data.get("_category_v2") or data.get("category", "immigration"),
        "archived_at": None,
        "commissions_v2": _extract_commissions_v2(cost_allocations, data.get("commissions_v2")),
        "computed": _compute_margin(sp, cost_allocations, success_bonuses),
        "status": data.get("status") or "active",
        "created_at": datetime.now(timezone.utc),
        # Product Master — Module A extensions
        "summary": data.get("summary") or data.get("description", ""),
        "migrate_page_url": data.get("migrate_page_url") or "",
        "official_urls": data.get("official_urls") or [],
        "official_domains": data.get("official_domains") or [],
        "eligibility_criteria": data.get("eligibility_criteria") or {
            "mandatory": [],
            "optional": [],
            "points_based": {"is_points_tested": False, "minimum_points": 0, "scoring_factors": []}
        },
        "visa_conditions": data.get("visa_conditions") or [],
        "government_costs": data.get("government_costs") or {
            "currency": "INR",
            "line_items": [],
            "effective_date": None,
            "source_link": ""
        },
        "processing_timeline": data.get("processing_timeline") or {
            "standard_duration": "",
            "stages": []
        },
        "sales_playbook": data.get("sales_playbook") or {
            "target_client": "",
            "pitch_points": [],
            "key_benefits": []
        },
        "objections_rebuttals": data.get("objections_rebuttals") or [],
        "faqs": data.get("faqs") or [],
        "document_checklist_template": data.get("document_checklist_template") or [],
        "letters_required": data.get("letters_required") or [],
        "info_sheet_sections": data.get("info_sheet_sections") or [],
        "refund_options": data.get("refund_options") or [],
        "explore_services": data.get("explore_services") or {
            "show_in_explore": True,
            "direct_purchase_allowed": False,
            "suggested_next_products": []
        },
        "last_verified_at": data.get("last_verified_at"),
        "last_verified_by": data.get("last_verified_by"),
        "next_review_at": data.get("next_review_at"),
        "version": int(data.get("version") or 1),
    }
    await products_col.insert_one(product)
    for step_data in data.get("workflow_steps", []):
        step = {
            "id": str(uuid.uuid4()), "product_id": product["id"],
            "step_name": step_data["step_name"],
            "step_order": step_data["step_order"],
            "description": step_data.get("description", ""),
            "duration_days": step_data.get("duration_days", 7),
            "required_documents": step_data.get("required_documents", []),
        }
        await workflow_steps_col.insert_one(step)
    await log_activity(current_user["id"], current_user["name"], "created", "product", product["id"],
                    f"Created product: {data['name']}")
    return {"id": product["id"], "message": "Product created"}

@router.put("/{product_id}")
@router.patch("/{product_id}")
async def update_product(product_id: str, data: dict, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    update: Dict[str, Any] = {}
    for field in [
        "name", "description", "category", "status",
        "country", "visa_type",
        "commission_type", "commission_rate", "commission_tiers", "commission_effective_from",
        "cost_allocations", "success_bonuses", "cost_structure_meta",
        "packages", "discount_coupons",
        # Phase 20.2 — new fields
        "is_pre_assessment", "pre_assessment_fee_inr", "pre_assessment_fee_currency",
        "workflow_id", "workflow_steps_count",
        "visa_subclass", "assessing_body_code",
        "commissions_v2", "_category_v2",
        "requires_partner_info",
        # Product Master — Module A extensions
        "summary", "migrate_page_url", "official_urls", "official_domains",
        "eligibility_criteria", "visa_conditions", "government_costs",
        "processing_timeline", "sales_playbook", "objections_rebuttals",
        "faqs", "document_checklist_template", "letters_required",
        "info_sheet_sections", "refund_options", "explore_services",
        "last_verified_at", "last_verified_by", "next_review_at", "version"
    ]:
        if field in data:
            update[field] = data[field]

    # Ensure pre_assessment_fee_inr is numeric when set, or cleared if is_pre_assessment is explicitly False
    if "is_pre_assessment" in update and update["is_pre_assessment"] is False:
        update["pre_assessment_fee_inr"] = None
    elif "pre_assessment_fee_inr" in update and update["pre_assessment_fee_inr"] is not None and str(update["pre_assessment_fee_inr"]).strip() != "":
        update["pre_assessment_fee_inr"] = float(update["pre_assessment_fee_inr"])
        if "is_pre_assessment" not in update:
            update["is_pre_assessment"] = True

    # Phase 20.2 — validation rules
    if "assessing_body_code" in update and update["assessing_body_code"]:
        existing = await products_col.find_one({"id": product_id}, {"country": 1})
        country = (data.get("country") or (existing or {}).get("country") or "").upper()
        if country not in ("AU", "NZ", "AUSTRALIA", "NEW ZEALAND"):
            raise HTTPException(status_code=400,
                                detail=f"assessing_body_code only valid for AU/NZ products; got country={country}")
        aa = await db["assessing_authorities"].find_one(
            {"code": update["assessing_body_code"]}, {"_id": 0, "code": 1})
        if not aa:
            raise HTTPException(status_code=400,
                                detail=f"Unknown assessing_body_code: {update['assessing_body_code']}")

    if "workflow_id" in update and update["workflow_id"]:
        wf = await db["ai_workflow_templates"].find_one(
            {"id": update["workflow_id"], "verified": True}, {"_id": 0, "id": 1})
        if not wf:
            raise HTTPException(status_code=400,
                                detail=f"Unknown or unverified workflow_id: {update['workflow_id']}")

    # base_fee / service_price are mirrored
    if "service_price" in data:
        update["service_price"] = float(data["service_price"] or 0)
        update["base_fee"] = update["service_price"]
    elif "base_fee" in data:
        update["base_fee"] = float(data["base_fee"] or 0)
        update["service_price"] = update["base_fee"]
    elif "fee" in data:
        update["base_fee"] = float(data["fee"] or 0)
        update["service_price"] = update["base_fee"]

    if update:
        # Recompute margin & commissions_v2 if pricing or cost_allocations changed
        if any(k in update for k in ("service_price", "base_fee", "cost_allocations", "success_bonuses", "commissions_v2")):
            current = await products_col.find_one({"id": product_id}, {"_id": 0})
            if current:
                merged = {**current, **update}
                update["computed"] = _compute_margin(
                    merged.get("service_price") or merged.get("base_fee") or 0,
                    merged.get("cost_allocations") or [],
                    merged.get("success_bonuses") or [],
                )
                update["commissions_v2"] = _extract_commissions_v2(
                    merged.get("cost_allocations") or [],
                    merged.get("commissions_v2")
                )
        update["updated_at"] = datetime.now(timezone.utc)
        await products_col.update_one({"id": product_id}, {"$set": update})
    await log_activity(current_user["id"], current_user["name"], "updated", "product", product_id,
                    f"Updated product fields: {', '.join(k for k in update.keys() if k != 'updated_at')}")
    return {"message": "Product updated", "computed": update.get("computed")}


# ── Phase 20.2 — Soft-archive / restore / link workflow / commissions ─────────
class ArchiveRequest(BaseModel):
    reason: str = Field(..., min_length=2, max_length=300)


@router.post("/{product_id}/archive")
async def archive_product(product_id: str, req: ArchiveRequest,
                        current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    p = await products_col.find_one({"id": product_id}, {"id": 1, "name": 1, "archived_at": 1})
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    if p.get("archived_at"):
        return {"ok": True, "already_archived": True, "id": product_id}
    now = datetime.now(timezone.utc)
    await products_col.update_one({"id": product_id}, {"$set": {
        "archived_at": now, "archived_by": current_user.get("id"),
        "archived_by_email": current_user.get("email"),
        "archived_reason": req.reason,
    }})
    await log_activity(current_user["id"], current_user.get("name", ""), "archived", "product", product_id,
                    f"Archived '{p.get('name')}' · reason: {req.reason}")
    return {"ok": True, "id": product_id, "archived_at": now.isoformat()}


@router.post("/{product_id}/restore")
async def restore_product(product_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    p = await products_col.find_one({"id": product_id}, {"id": 1, "name": 1, "archived_at": 1})
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    if not p.get("archived_at"):
        return {"ok": True, "already_active": True, "id": product_id}
    await products_col.update_one({"id": product_id}, {"$set": {
        "archived_at": None, "archived_by": None,
        "archived_by_email": None, "archived_reason": None,
        "restored_at": datetime.now(timezone.utc),
        "restored_by": current_user.get("id"),
    }})
    await log_activity(current_user["id"], current_user.get("name", ""), "restored", "product", product_id,
                    f"Restored '{p.get('name')}'")
    return {"ok": True, "id": product_id}


class LinkWorkflowRequest(BaseModel):
    workflow_id: str
    steps_count: Optional[int] = None


@router.post("/{product_id}/link-workflow")
async def link_workflow(product_id: str, req: LinkWorkflowRequest,
                        current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    wf = await db["ai_workflow_templates"].find_one(
        {"id": req.workflow_id, "verified": True}, {"_id": 0})
    if not wf:
        raise HTTPException(status_code=400,
                            detail=f"Unknown or unverified workflow_id: {req.workflow_id}")
    steps = req.steps_count
    if steps is None:
        steps = len((wf.get("workflow_payload") or {}).get("steps") or [])
    await products_col.update_one({"id": product_id}, {"$set": {
        "workflow_id": req.workflow_id, "workflow_steps_count": steps,
        "updated_at": datetime.now(timezone.utc),
    }})
    await log_activity(current_user["id"], current_user.get("name", ""), "linked_workflow", "product", product_id,
                    f"Linked workflow {req.workflow_id} ({steps} steps)")
    return {"ok": True, "id": product_id, "workflow_id": req.workflow_id, "steps_count": steps}


@router.get("/{product_id}/commissions")
async def get_commissions(product_id: str, current_user: dict = Depends(get_current_user)):
    """Returns commissions_v2 filtered by caller's role.
    Sales user → only sales_user · Internal Partner → only partner_internal · External Partner → only partner_external · Admin → all.
    """
    p = await products_col.find_one({"id": product_id}, {"_id": 0, "id": 1, "name": 1, "commissions_v2": 1, "cost_allocations": 1})
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    v2 = p.get("commissions_v2")
    if not v2:
        v2 = _extract_commissions_v2(p.get("cost_allocations") or [])

    role = (current_user.get("rbac_role") or current_user.get("role") or "").lower()
    user_type = (current_user.get("user_type") or "").lower()
    partner_type = (current_user.get("partner_type") or "").lower()
    is_internal_partner = user_type == "internal" or partner_type == "internal" or current_user.get("is_internal") is True

    visible = {}
    if role in ("admin", "admin_owner", "super_admin") or "*" in (current_user.get("permissions") or []):
        visible = v2  # full view
    elif role in ("sales", "sales_executive", "sr_sales_executive", "sales_manager", "sales_head", "sales_rep", "sales_person"):
        if "sales_user" in v2:
            visible["sales_user"] = v2["sales_user"]
        elif "salesperson" in v2:
            visible["salesperson"] = v2["salesperson"]
    elif role in ("case_manager", "cm"):
        if "case_manager" in v2:
            visible["case_manager"] = v2["case_manager"]
    elif role == "partner":
        if is_internal_partner:
            if "partner_internal" in v2:
                visible["partner_internal"] = v2["partner_internal"]
            elif "internal_partner" in v2:
                visible["internal_partner"] = v2["internal_partner"]
        else:
            if "partner_external" in v2:
                visible["partner_external"] = v2["partner_external"]
            elif "external_partner" in v2:
                visible["external_partner"] = v2["external_partner"]
    return {
        "product_id": product_id,
        "name": p.get("name"),
        "commissions": visible,
        "role": role,
        "is_internal_partner": is_internal_partner if role == "partner" else None,
        "has_v2": bool(v2)
    }


@router.delete("/{product_id}")
async def delete_product(product_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    await products_col.delete_one({"id": product_id})
    await workflow_steps_col.delete_many({"product_id": product_id})
    await log_activity(current_user["id"], current_user["name"], "deleted", "product", product_id,
                    "Deleted product and workflow steps")
    return {"message": "Product deleted"}


# ──────────────────────────────────────────────────────────────
# Phase 4C — Cost preview / calculator on a Product
# ──────────────────────────────────────────────────────────────
class PreviewRequest(BaseModel):
    service_price: Optional[float] = None
    visa_approved: bool = False


@router.post("/{product_id}/preview")
async def preview_cost(product_id: str, req: PreviewRequest, current_user: dict = Depends(get_current_user)):
    """Compute allocations + margin breakdown for a hypothetical sale on this product."""
    p = await products_col.find_one({"id": product_id}, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    sp = float(req.service_price if req.service_price is not None else (p.get("service_price") or p.get("base_fee") or 0))
    cost_allocations = p.get("cost_allocations") or []
    success_bonuses = p.get("success_bonuses") or []

    rows = []
    for a in cost_allocations:
        val = float(a.get("rate") if a.get("rate") is not None else a.get("amount", 0) or 0)
        if a.get("payment_type") == "percentage":
            base = sp * val / 100.0
        else:
            base = val
        bonus = 0.0
        if req.visa_approved:
            match = next((b for b in success_bonuses if b.get("vendor_category") == a.get("vendor_category")), None)
            if match:
                bonus = float((match.get("bonus_amount") if match.get("bonus_amount") is not None else match.get("amount", 0)) or 0)
        rows.append({
            "label": a.get("label"),
            "vendor_category": a.get("vendor_category"),
            "payment_type": a.get("payment_type"),
            "base_amount": round(base, 2),
            "bonus_amount": round(bonus, 2),
            "total_amount": round(base + bonus, 2),
            "is_optional": a.get("is_optional", False),
        })

    total_cost = sum(r["total_amount"] for r in rows if not r["is_optional"])
    margin = sp - total_cost
    return {
        "service_price": sp,
        "rows": rows,
        "total_cost": round(total_cost, 2),
        "margin": round(margin, 2),
        "margin_pct": round((margin / sp * 100), 2) if sp > 0 else 0,
        "visa_approved_applied": req.visa_approved,
    }


# ──────────────────────────────────────────────────────────────
# Workflow Step CRUD (unchanged — kept for AI Workflow Builder)
# ──────────────────────────────────────────────────────────────
@router.post("/{product_id}/workflow-step")
async def create_workflow_step(product_id: str, data: dict, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    import re
    escaped_name = re.escape(data['step_name'].strip())
    existing = await workflow_steps_col.find_one({
        "product_id": product_id,
        "step_name": {"$regex": f"^{escaped_name}$", "$options": "i"}
    })
    if existing:
        raise HTTPException(status_code=400, detail=f"A workflow step named '{data['step_name']}' already exists for this product")
    order_exists = await workflow_steps_col.find_one({
        "product_id": product_id,
        "step_order": data["step_order"]
    })
    if order_exists:
        raise HTTPException(status_code=400, detail=f"Step order {data['step_order']} already exists for this product")
    step = {
        "id": str(uuid.uuid4()), "product_id": product_id,
        "step_name": data["step_name"].strip(), "step_order": data["step_order"],
        "description": data.get("description", ""),
        "duration_days": data.get("duration_days", 7),
        "required_documents": data.get("required_documents", [])
    }
    await workflow_steps_col.insert_one(step)
    return {"message": "Workflow step created"}


@router.put("/{product_id}/workflow-step/{step_order}")
async def update_workflow_step(product_id: str, step_order: int, data: dict, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    update = {}
    for field in ["step_name", "step_order", "description", "duration_days", "required_documents"]:
        if field in data:
            update[field] = data[field]
    await workflow_steps_col.update_one(
        {"product_id": product_id, "step_order": step_order},
        {"$set": update}
    )
    return {"message": "Workflow step updated"}


@router.delete("/{product_id}/workflow-step/{step_order}")
async def delete_workflow_step(product_id: str, step_order: int, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    await workflow_steps_col.delete_one({"product_id": product_id, "step_order": step_order})
    return {"message": "Workflow step deleted"}

# ──────────────────────────────────────────────────────────────
# Package Info Document Upload (PDF) — admin uploads a document
# describing a specific package (e.g. Standard/Smart/Premium/custom)
# ──────────────────────────────────────────────────────────────
PACKAGE_DOCS_DIR = os.environ.get("PACKAGE_DOCS_DIR") or os.path.join(os.environ.get("UPLOAD_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")), "product_packages")
os.makedirs(PACKAGE_DOCS_DIR, exist_ok=True)


@router.post("/packages/upload-document")
async def upload_package_document(
    package_id: str = Form(...),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Admin uploads a PDF describing a package. Returns a document_url the
    frontend stores on the package object (saved via the normal product PUT)."""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    pkg_dir = f"{PACKAGE_DOCS_DIR}/{package_id}"
    os.makedirs(pkg_dir, exist_ok=True)
    file_path = f"{pkg_dir}/{file.filename}"
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    document_url = f"/api/products/packages/{package_id}/document/{file.filename}"

    await log_activity(current_user["id"], current_user.get("name", ""), "uploaded_package_document",
                    "product_package", package_id, f"Uploaded '{file.filename}' for package {package_id}")

    return {"document_url": document_url, "file_name": file.filename}


@router.get("/packages/{package_id}/document/{filename}")
async def download_package_document(package_id: str, filename: str, current_user: dict = Depends(get_current_user)):
    """Serve the uploaded package PDF."""
    from fastapi.responses import FileResponse
    file_path = f"{PACKAGE_DOCS_DIR}/{package_id}/{filename}"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Document not found")
    return FileResponse(file_path, filename=filename, media_type="application/pdf")

# ──────────────────────────────────────────────────────────────
# Discount Coupons — admin defines per-product, partner sees active ones
# ──────────────────────────────────────────────────────────────
class DiscountCoupon(BaseModel):
    id: Optional[str] = None
    code: str
    discount_type: str  # "percentage" | "flat"
    discount_value: float
    is_active: bool = True
    notes: Optional[str] = ""


@router.get("/{product_id}/coupons")
async def get_product_coupons(product_id: str, active_only: bool = True, current_user: dict = Depends(get_current_user)):
    """Returns discount coupons for a product. Partners get only active ones by default;
    admin can pass active_only=false to see everything (for the management screen)."""
    p = await products_col.find_one({"id": product_id}, {"_id": 0, "discount_coupons": 1, "name": 1})
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    coupons = p.get("discount_coupons") or []
    is_admin = current_user.get("role") == "admin"
    if active_only or not is_admin:
        coupons = [c for c in coupons if c.get("is_active", True)]
    return {"product_id": product_id, "product_name": p.get("name"), "coupons": coupons}


@router.post("/{product_id}/coupons")
async def create_product_coupon(product_id: str, coupon: DiscountCoupon, current_user: dict = Depends(get_current_user)):
    """Admin adds a new discount coupon to a product."""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    p = await products_col.find_one({"id": product_id}, {"_id": 0, "discount_coupons": 1})
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")

    if coupon.discount_type not in ("percentage", "flat"):
        raise HTTPException(status_code=400, detail="discount_type must be 'percentage' or 'flat'")
    if coupon.discount_value <= 0:
        raise HTTPException(status_code=400, detail="discount_value must be greater than 0")
    if coupon.discount_type == "percentage" and coupon.discount_value > 100:
        raise HTTPException(status_code=400, detail="Percentage discount cannot exceed 100")

    code_upper = coupon.code.strip().upper()
    existing = p.get("discount_coupons") or []
    if any((c.get("code") or "").upper() == code_upper for c in existing):
        raise HTTPException(status_code=400, detail=f"Coupon code '{code_upper}' already exists on this product")

    new_coupon = {
        "id": str(uuid.uuid4()),
        "code": code_upper,
        "discount_type": coupon.discount_type,
        "discount_value": coupon.discount_value,
        "is_active": coupon.is_active,
        "notes": coupon.notes or "",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": current_user["id"],
    }
    existing.append(new_coupon)
    await products_col.update_one({"id": product_id}, {"$set": {
        "discount_coupons": existing, "updated_at": datetime.now(timezone.utc),
    }})
    await log_activity(current_user["id"], current_user.get("name", ""), "created_coupon", "product", product_id,
                    f"Added coupon '{code_upper}' ({coupon.discount_type} {coupon.discount_value})")
    return {"ok": True, "coupon": new_coupon}


@router.put("/{product_id}/coupons/{coupon_id}")
async def update_product_coupon(product_id: str, coupon_id: str, data: dict, current_user: dict = Depends(get_current_user)):
    """Admin edits/toggles a coupon (e.g. deactivate it)."""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    p = await products_col.find_one({"id": product_id}, {"_id": 0, "discount_coupons": 1})
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")

    coupons = p.get("discount_coupons") or []
    found = False
    for c in coupons:
        if c.get("id") == coupon_id:
            for field in ("code", "discount_type", "discount_value", "is_active", "notes"):
                if field in data:
                    c[field] = data[field]
            if "code" in data:
                c["code"] = str(data["code"]).strip().upper()
            found = True
            break
    if not found:
        raise HTTPException(status_code=404, detail="Coupon not found")

    await products_col.update_one({"id": product_id}, {"$set": {
        "discount_coupons": coupons, "updated_at": datetime.now(timezone.utc),
    }})
    await log_activity(current_user["id"], current_user.get("name", ""), "updated_coupon", "product", product_id,
                    f"Updated coupon {coupon_id}")
    return {"ok": True}


@router.delete("/{product_id}/coupons/{coupon_id}")
async def delete_product_coupon(product_id: str, coupon_id: str, current_user: dict = Depends(get_current_user)):
    """Admin removes a coupon entirely."""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    p = await products_col.find_one({"id": product_id}, {"_id": 0, "discount_coupons": 1})
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")

    coupons = [c for c in (p.get("discount_coupons") or []) if c.get("id") != coupon_id]
    await products_col.update_one({"id": product_id}, {"$set": {
        "discount_coupons": coupons, "updated_at": datetime.now(timezone.utc),
    }})
    await log_activity(current_user["id"], current_user.get("name", ""), "deleted_coupon", "product", product_id,
                    f"Deleted coupon {coupon_id}")
    return {"ok": True}
