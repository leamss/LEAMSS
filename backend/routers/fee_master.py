"""Skill-Assessment Fee Master (Australia).

Central place to manage each assessing authority's skill-assessment fee. Supports
MULTIPLE fee components per authority (e.g. TRA = Document Evidence + Technical
Interview + Practical Interview). Occupations are matched occupation-code-wise via
the assessing authority stored on occupation_master, so setting a fee here flows to
every occupation using that authority, and into every bulk Pre-Assessment report.

Storage: skill_assessment_fee_overrides (canon key -> {authority_name, components}).
Base defaults derive from skill_body_master when no override exists.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.auth import get_current_user
from routers.bulk_assessments import (
    FEE_OVERRIDES,
    _authority_catalog,
    _can,
    _fee_components_of,
    _fee_master_map,
    _totals,
)

router = APIRouter(prefix="/fee-master", tags=["fee-master"])


class FeeComponent(BaseModel):
    label: str = "Skill Assessment Fee"
    amount: Optional[float] = None
    currency: str = "INR"


class FeeMasterSaveRequest(BaseModel):
    authority_name: Optional[str] = None
    components: List[FeeComponent] = []


@router.get("")
async def list_fee_master(current_user: dict = Depends(get_current_user)):
    """Every assessing authority present in occupation_master, with its current fee components."""
    if not _can(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    catalog = await _authority_catalog()
    fee_map = await _fee_master_map(force=True)
    overrides: Dict[str, Dict[str, Any]] = {}
    async for doc in FEE_OVERRIDES.find({}, {"_id": 0}):
        if doc.get("key"):
            overrides[doc["key"]] = doc

    seen = set()
    out: List[Dict[str, Any]] = []
    for a in catalog:
        key = a["key"]
        seen.add(key)
        fm = fee_map.get(key) or {}
        ov = overrides.get(key) or {}
        comps = fm.get("components") or []
        out.append({
            "key": key,
            "authority_name": a["authority_name"],
            "occupation_count": a["occupation_count"],
            "components": comps,
            "total_by_currency": _totals(comps),
            "source": fm.get("source") or ("fee_master" if ov else "none"),
            "is_set": bool(comps),
            "updated_at": (ov.get("updated_at").isoformat() if ov.get("updated_at") else None),
        })
    # Include any override for an authority not currently in occupation_master
    for key, ov in overrides.items():
        if key in seen:
            continue
        comps = _fee_components_of(ov)
        out.append({
            "key": key,
            "authority_name": ov.get("authority_name") or key,
            "occupation_count": 0,
            "components": comps,
            "total_by_currency": _totals(comps),
            "source": "fee_master",
            "is_set": bool(comps),
            "updated_at": (ov.get("updated_at").isoformat() if ov.get("updated_at") else None),
        })

    total = len(out)
    return {
        "authorities": out,
        "total": total,
        "configured": sum(1 for a in out if a["is_set"]),
        "missing": sum(1 for a in out if not a["is_set"]),
    }


@router.put("/{key}")
async def save_fee_master(key: str, req: FeeMasterSaveRequest,
                          current_user: dict = Depends(get_current_user)):
    """Save (upsert) the fee components for one assessing authority."""
    if not _can(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    if not key or key == "unknown":
        raise HTTPException(status_code=400, detail="Invalid authority key")

    comps = _fee_components_of({"components": [c.model_dump() for c in req.components]})
    if not comps:
        raise HTTPException(status_code=400, detail="Add at least one fee component with an amount")

    await FEE_OVERRIDES.update_one({"key": key}, {"$set": {
        "key": key,
        "authority_name": req.authority_name,
        "components": comps,
        "updated_at": datetime.now(timezone.utc),
        "updated_by": current_user.get("id"),
    }, "$unset": {"amount": "", "currency": ""}}, upsert=True)
    fee_map = await _fee_master_map(force=True)
    fm = fee_map.get(key) or {}
    return {"ok": True, "key": key, "components": comps, "total_by_currency": _totals(comps),
            "authority_name": fm.get("authority_name") or req.authority_name}


@router.delete("/{key}")
async def reset_fee_master(key: str, current_user: dict = Depends(get_current_user)):
    """Remove the admin override for one authority (falls back to skill_body default)."""
    if not _can(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    await FEE_OVERRIDES.delete_one({"key": key})
    await _fee_master_map(force=True)
    return {"ok": True, "key": key, "reset": True}
