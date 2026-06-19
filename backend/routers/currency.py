"""Phase 19.10 — Currency rates router.

Endpoints:
  GET   /api/currency/rates         — public (sales/partner/admin/client)
  POST  /api/currency/rates         — admin only, updates DB-stored override
  GET   /api/currency/rates/history — admin only, audit history
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.auth import get_current_user
from core.database import db
from services import currency_service, import_batch_service as ibs
from services.audit_service import log_action

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/currency", tags=["currency"])

ADMIN_ROLES = {"admin", "admin_owner", "super_admin"}


def _is_admin(user: Dict[str, Any]) -> bool:
    role = user.get("rbac_role") or user.get("role")
    return role in ADMIN_ROLES or "*" in (user.get("permissions") or [])


class SetRateRequest(BaseModel):
    pair: str = Field(..., description="AUD_INR | NZD_INR | CAD_INR")
    rate: float = Field(..., gt=0, lt=1000)


@router.get("/rates")
async def get_rates(current_user: Dict[str, Any] = Depends(get_current_user)):
    """All 3 INR conversion rates. Available to any authenticated user."""
    return await currency_service.get_all_rates(db)


@router.post("/rates")
async def update_rate(
    payload: SetRateRequest, current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    try:
        # Register Phase 19.6 batch for audit + 24h revocation
        user_id = str(current_user.get("id") or current_user.get("email") or "admin")
        user_name = str(current_user.get("name") or current_user.get("email") or "admin")
        fake_body = f"phase_19.10_currency_{payload.pair}_{payload.rate}".encode()
        batch = await ibs.open_batch(
            db, ingestion_path=f"phase_19.10_currency.set_rate",
            endpoint="POST /api/currency/rates",
            uploaded_by=user_id, uploaded_by_name=user_name,
            file_name=f"currency_{payload.pair}", file_hash=ibs.file_sha256(fake_body),
            file_size_bytes=len(fake_body), target_collection="currency_rates",
        )
        existing = await db["currency_rates"].find_one({"pair": payload.pair})
        result = await currency_service.set_rate(
            db, payload.pair, payload.rate, user_id, user_name,
        )
        # Record update in batch (so revoke can restore prev rate)
        if existing:
            ibs.record_update(batch, payload.pair, {"pair": payload.pair},
                              {k: v for k, v in existing.items() if k != "_id"})
        else:
            ibs.record_create(batch, payload.pair, {"pair": payload.pair})
        await ibs.close_batch(db, batch, total_rows=1, status="committed")
        await log_action(db, action="currency.set_rate",
                         user_id=user_id, user_name=user_name,
                         severity="info",
                         summary={"pair": payload.pair, "new_rate": payload.rate,
                                  "previous_rate": result["previous_rate"],
                                  "batch_id": batch["batch_id"]})
        return {"ok": True, "batch_id": batch["batch_id"], **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/rates/history")
async def rates_history(current_user: Dict[str, Any] = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    cursor = db["audit_logs"].find(
        {"action": "currency.set_rate"}, {"_id": 0},
    ).sort("at", -1).limit(50)
    items = []
    async for d in cursor:
        if isinstance(d.get("at"), datetime):
            d["at"] = d["at"].isoformat()
        items.append(d)
    return {"items": items, "count": len(items)}
