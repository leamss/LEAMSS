"""Phase 20.8 — Coupons collection + admin CRUD + validation engine."""
from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from core.auth import get_current_user
from core.database import db
from services import import_batch_service as ibs
from services.audit_service import log_action

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/coupons", tags=["Phase 20.8 Coupons"])
COLL = "coupons"
ADMIN_ROLES = {"admin", "admin_owner", "super_admin"}
SALES_ROLES = ADMIN_ROLES | {"sales", "sales_executive", "sr_sales_executive",
                              "sales_manager", "sales_head", "partner",
                              "case_manager", "case_manager_lead"}


def _is_admin(u): r = (u.get("rbac_role") or u.get("role") or "").lower(); return r in ADMIN_ROLES or "*" in (u.get("permissions") or [])
def _is_sales(u): r = (u.get("rbac_role") or u.get("role") or "").lower(); return r in SALES_ROLES or "*" in (u.get("permissions") or [])


class CouponCreate(BaseModel):
    code: str = Field(..., min_length=3, max_length=30, pattern=r"^[A-Z0-9_]+$")
    description: str = Field(..., max_length=300)
    discount_type: str = Field(..., pattern=r"^(pct|fixed)$")
    discount_value: float = Field(..., gt=0)
    applicable_currency: str = Field(default="INR")
    applicable_to: str = Field(default="any", pattern=r"^(professional_fees|addon_products|any)$")
    min_order_value_inr: Optional[int] = Field(None, ge=0)
    applicable_products: Optional[List[str]] = None
    applicable_countries: Optional[List[str]] = None
    applicable_visa_categories: Optional[List[str]] = None
    valid_from: datetime
    valid_until: datetime
    usage_limit_total: Optional[int] = Field(None, ge=1)
    usage_limit_per_client: int = Field(default=1, ge=1)
    stackable: bool = False

    @field_validator("code")
    @classmethod
    def upper(cls, v): return v.upper().strip()


class CouponPatch(BaseModel):
    description: Optional[str] = None
    discount_value: Optional[float] = Field(None, gt=0)
    valid_until: Optional[datetime] = None
    usage_limit_total: Optional[int] = Field(None, ge=1)
    status: Optional[str] = Field(None, pattern=r"^(active|expired|exhausted|archived)$")


def _serialise(d: Dict[str, Any]) -> Dict[str, Any]:
    d.pop("_id", None)
    for k, v in list(d.items()):
        if isinstance(v, datetime):
            d[k] = v.isoformat()
    return d


def _check_status(c: Dict[str, Any]) -> str:
    """Compute current status based on usage + validity, not just stored field."""
    if c.get("status") == "archived":
        return "archived"
    now = datetime.now(timezone.utc)
    vu = c.get("valid_until")
    if isinstance(vu, str):
        vu = datetime.fromisoformat(vu.replace("Z", "+00:00"))
    # Mongo returns naive datetimes; coerce to UTC-aware for safe comparison
    if isinstance(vu, datetime) and vu.tzinfo is None:
        vu = vu.replace(tzinfo=timezone.utc)
    if vu and vu < now:
        return "expired"
    if c.get("usage_limit_total") and c.get("used_count", 0) >= c["usage_limit_total"]:
        return "exhausted"
    return "active"


@router.get("")
async def list_coupons(
    status: Optional[str] = None, limit: int = 100,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not _is_sales(current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    q: Dict[str, Any] = {}
    if status and status != "all":
        q["status"] = status
    rows: List[Dict[str, Any]] = []
    async for c in db[COLL].find(q).sort("created_at", -1).limit(limit):
        c = _serialise(c)
        c["computed_status"] = _check_status(c)
        rows.append(c)
    return {"coupons": rows, "count": len(rows)}


@router.get("/validate")
async def validate_coupon(
    code: str, product_id: Optional[str] = None,
    client_id: Optional[str] = None, order_value_inr: Optional[int] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Eligibility + final discount computation. Sales/Partner-callable."""
    if not _is_sales(current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    c = await db[COLL].find_one({"code": code.upper().strip()})
    if not c:
        raise HTTPException(status_code=404, detail=f"Unknown coupon code: {code}")
    status = _check_status(c)
    if status != "active":
        return {"eligible": False, "reason": f"Coupon is {status}", "code": code, "status": status}

    # Per-client usage check
    if client_id and c.get("usage_limit_per_client"):
        usage = await db["coupon_usages"].count_documents({
            "coupon_id": c["id"], "client_id": client_id,
        })
        if usage >= c["usage_limit_per_client"]:
            return {"eligible": False, "reason": "Per-client usage limit exhausted", "code": code}

    # Min order check
    if c.get("min_order_value_inr") and order_value_inr and order_value_inr < c["min_order_value_inr"]:
        return {"eligible": False,
                "reason": f"Min order ₹{c['min_order_value_inr']} required",
                "code": code}

    # Product eligibility
    if c.get("applicable_products") and product_id and product_id not in c["applicable_products"]:
        return {"eligible": False, "reason": "Not applicable to this product", "code": code}

    # Country / visa eligibility — best-effort, requires product lookup
    if product_id and (c.get("applicable_countries") or c.get("applicable_visa_categories")):
        prod = await db["products"].find_one({"id": product_id},
                                             {"country": 1, "service_type": 1, "_id": 0})
        if prod:
            if c.get("applicable_countries"):
                pc = (prod.get("country") or "").upper()
                allowed = [x.upper() for x in c["applicable_countries"]]
                if not any(pc.startswith(a[:2]) for a in allowed):
                    return {"eligible": False, "reason": f"Coupon not valid for {prod.get('country')}", "code": code}
            if c.get("applicable_visa_categories"):
                pv = (prod.get("service_type") or "").upper()
                if pv not in [x.upper() for x in c["applicable_visa_categories"]]:
                    return {"eligible": False, "reason": f"Coupon not valid for visa {prod.get('service_type')}", "code": code}

    # Compute discount
    discount_amount = 0
    if order_value_inr is not None:
        if c["discount_type"] == "pct":
            discount_amount = int(order_value_inr * c["discount_value"] / 100)
        else:
            discount_amount = min(int(c["discount_value"]), order_value_inr)
    return {
        "eligible": True, "code": code,
        "discount_type": c["discount_type"], "discount_value": c["discount_value"],
        "discount_amount_inr": discount_amount,
        "applicable_to": c["applicable_to"],
        "stackable": c.get("stackable", False),
        "description": c["description"],
    }


@router.post("")
async def create_coupon(
    payload: CouponCreate, current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    existing = await db[COLL].find_one({"code": payload.code})
    if existing:
        raise HTTPException(status_code=409, detail=f"Coupon {payload.code} already exists")
    now = datetime.now(timezone.utc)
    user_id = str(current_user.get("id") or "admin")
    doc = {"id": str(uuid.uuid4()), **payload.dict(), "used_count": 0,
           "status": "active", "created_by": user_id,
           "created_at": now, "updated_at": now}

    body = f"create_coupon_{payload.code}".encode()
    batch = await ibs.open_batch(db, ingestion_path="phase_20.8_coupon.create",
                                 endpoint="POST /api/coupons",
                                 uploaded_by=user_id,
                                 uploaded_by_name=current_user.get("name") or user_id,
                                 file_name=f"coupon_{payload.code}",
                                 file_hash=ibs.file_sha256(body),
                                 file_size_bytes=len(body), target_collection=COLL)
    await db[COLL].insert_one(doc)
    ibs.record_create(batch, doc["id"], {"code": payload.code})
    await ibs.close_batch(db, batch, total_rows=1, status="committed")
    await log_action(db, action="coupon.create", user_id=user_id,
                     severity="info", summary={"code": payload.code, "batch_id": batch["batch_id"]})
    return _serialise(doc)


@router.patch("/{coupon_id}")
async def patch_coupon(
    coupon_id: str, payload: CouponPatch,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    c = await db[COLL].find_one({"id": coupon_id})
    if not c:
        raise HTTPException(status_code=404, detail="Coupon not found")
    updates = {k: v for k, v in payload.dict(exclude_none=True).items()}
    if not updates:
        return {"ok": True, "no_change": True}
    updates["updated_at"] = datetime.now(timezone.utc)
    await db[COLL].update_one({"id": coupon_id}, {"$set": updates})
    return {"ok": True, "id": coupon_id}


@router.delete("/{coupon_id}")
async def archive_coupon(
    coupon_id: str, current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    await db[COLL].update_one(
        {"id": coupon_id},
        {"$set": {"status": "archived", "archived_at": datetime.now(timezone.utc)}},
    )
    return {"ok": True, "id": coupon_id, "status": "archived"}


@router.post("/{code}/apply")
async def apply_coupon(
    code: str, client_id: str, product_id: str, order_value_inr: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Record coupon usage atomically. Returns final price after discount."""
    if not _is_sales(current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    code = code.upper().strip()
    c = await db[COLL].find_one({"code": code})
    if not c or _check_status(c) != "active":
        raise HTTPException(status_code=400, detail=f"Coupon not active: {code}")

    # Idempotent: check if this exact usage already recorded
    existing = await db["coupon_usages"].find_one({
        "coupon_id": c["id"], "client_id": client_id, "product_id": product_id,
    })
    if existing:
        return {"ok": True, "already_applied": True,
                "discount_amount_inr": existing["discount_amount_inr"],
                "final_price_inr": existing["final_price_inr"]}

    # Compute discount
    if c["discount_type"] == "pct":
        discount = int(order_value_inr * c["discount_value"] / 100)
    else:
        discount = min(int(c["discount_value"]), order_value_inr)
    final_price = max(0, order_value_inr - discount)

    now = datetime.now(timezone.utc)
    await db["coupon_usages"].insert_one({
        "id": str(uuid.uuid4()), "coupon_id": c["id"], "code": code,
        "client_id": client_id, "product_id": product_id,
        "order_value_inr": order_value_inr,
        "discount_amount_inr": discount, "final_price_inr": final_price,
        "applied_by": str(current_user.get("id")), "applied_at": now,
    })
    await db[COLL].update_one({"id": c["id"]}, {"$inc": {"used_count": 1}})

    return {"ok": True, "code": code, "discount_amount_inr": discount,
            "final_price_inr": final_price,
            "order_value_inr": order_value_inr}


@router.post("/seed")
async def seed_coupons(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Idempotent seed of Sir's 3 default coupons."""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    now = datetime.now(timezone.utc)
    far_future = datetime(2030, 12, 31, tzinfo=timezone.utc)
    seeds = [
        {"code": "LUMPSUM20", "description": "20% off professional fees (Sir's brochure offer)",
         "discount_type": "pct", "discount_value": 20.0, "applicable_to": "professional_fees"},
        {"code": "WELCOME5000", "description": "₹5,000 off any product (first-time clients)",
         "discount_type": "fixed", "discount_value": 5000.0, "applicable_to": "any"},
        {"code": "STUDENT15", "description": "15% off Student visa products",
         "discount_type": "pct", "discount_value": 15.0, "applicable_to": "any",
         "applicable_visa_categories": ["Student", "STUDENT"]},
    ]
    user_id = str(current_user.get("id") or "admin")
    created = []
    skipped = []
    for s in seeds:
        if await db[COLL].find_one({"code": s["code"]}):
            skipped.append(s["code"])
            continue
        doc = {"id": str(uuid.uuid4()), "applicable_currency": "INR",
               "valid_from": now, "valid_until": far_future,
               "usage_limit_total": None, "usage_limit_per_client": 1,
               "used_count": 0, "status": "active", "stackable": False,
               "created_by": user_id, "created_at": now, "updated_at": now,
               **s}
        await db[COLL].insert_one(doc)
        created.append(s["code"])
    return {"ok": True, "created": created, "skipped": skipped}
