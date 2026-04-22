"""Upsell Bundles — admin-managed add-on services for pre-assessment proposals.

Partners can attach selected bundles when sending a proposal, increasing deal size.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from core.auth import get_current_user
from core.database import db

router = APIRouter(prefix="/upsell-bundles", tags=["Upsell Bundles"])

bundles_col = db["upsell_bundles"]


class BundleBody(BaseModel):
    name: str
    amount: float = Field(gt=0)
    description: Optional[str] = ""
    category: Optional[str] = "general"  # general | processing | family | document | priority
    is_active: bool = True


def _now():
    return datetime.now(timezone.utc)


def _serialize(b):
    for k in ("created_at", "updated_at"):
        if isinstance(b.get(k), datetime):
            b[k] = b[k].isoformat()
    return b


async def _seed_if_empty():
    if await bundles_col.count_documents({}) > 0:
        return
    defaults = [
        {"name": "Priority Processing", "amount": 5000, "category": "priority",
         "description": "Case prioritised — reduced wait time for review and submission"},
        {"name": "Family Member Add-on", "amount": 15000, "category": "family",
         "description": "Include a spouse or dependent in the same application"},
        {"name": "Document Courier (International)", "amount": 3500, "category": "document",
         "description": "DHL pickup & tracked international document delivery"},
        {"name": "Extended Consultation (5 hours)", "amount": 8000, "category": "general",
         "description": "Five additional hours of 1-on-1 consultant time post-submission"},
        {"name": "Mock Visa Interview Prep", "amount": 4500, "category": "priority",
         "description": "Two mock interviews + personalised coaching notes"},
        {"name": "Landing Assistance Package", "amount": 12000, "category": "general",
         "description": "Airport pickup + 7 days accommodation search + SIM/bank guidance"},
    ]
    now = _now()
    for d in defaults:
        d.update({"id": str(uuid.uuid4()), "is_active": True, "created_at": now, "updated_at": now})
    await bundles_col.insert_many(defaults)


@router.get("")
async def list_bundles(current_user: dict = Depends(get_current_user)):
    await _seed_if_empty()
    active_only = current_user.get("role") not in ("admin",)
    q = {"is_active": True} if active_only else {}
    items = await bundles_col.find(q, {"_id": 0}).sort("amount", 1).to_list(200)
    return [_serialize(b) for b in items]


@router.post("")
async def create_bundle(data: BundleBody, current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    b = data.model_dump()
    b.update({"id": str(uuid.uuid4()), "created_at": _now(), "updated_at": _now()})
    await bundles_col.insert_one(b)
    return _serialize({k: v for k, v in b.items() if k != "_id"})


@router.put("/{bundle_id}")
async def update_bundle(bundle_id: str, data: BundleBody, current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    existing = await bundles_col.find_one({"id": bundle_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Bundle not found")
    payload = data.model_dump()
    payload["updated_at"] = _now()
    await bundles_col.update_one({"id": bundle_id}, {"$set": payload})
    return {"ok": True}


@router.delete("/{bundle_id}")
async def delete_bundle(bundle_id: str, current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    await bundles_col.delete_one({"id": bundle_id})
    return {"ok": True}


@router.post("/resolve")
async def resolve_bundles(bundle_ids: List[str], current_user: dict = Depends(get_current_user)):
    """Given a list of bundle_ids, return the bundle details + total amount.
    Used by Partner during proposal composition (client/API preview before save)."""
    if not bundle_ids:
        return {"items": [], "total": 0.0}
    items = await bundles_col.find(
        {"id": {"$in": bundle_ids}, "is_active": True}, {"_id": 0}
    ).to_list(100)
    total = sum(float(b.get("amount", 0)) for b in items)
    return {"items": [_serialize(b) for b in items], "total": round(total, 2)}
