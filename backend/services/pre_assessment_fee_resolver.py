"""Phase 20.3 — Pre-Assessment Fee Resolver.

3-tier priority resolution + hardcoded safety net.

  P1. Per-product override (Phase 20.2 products.pre_assessment_fee_inr)
  P2. Per-country + visa_category active policy
  P3. GLOBAL fallback policy (country=GLOBAL, visa=ANY)
  P4. Hardcoded ₹5,100 (last-resort safety net if DB empty)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

COLLECTION = "pre_assessment_fee_policies"
HARDCODED_SAFETY_NET_INR = 5100


async def resolve_pre_assessment_fee(
    db: AsyncIOMotorDatabase,
    product_id: Optional[str] = None,
    country_code: Optional[str] = None,
    visa_category: Optional[str] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Resolve the Pre-Assessment fee with audit trail.

    Returns dict: {amount, currency, source, policy_id?, product_id?, raw_match?}
    """
    now = now or datetime.now(timezone.utc)
    country = (country_code or "").upper()
    visa = (visa_category or "").upper()

    # P1 — product override
    if product_id:
        p = await db["products"].find_one(
            {"id": product_id, "archived_at": None},
            {"_id": 0, "id": 1, "pre_assessment_fee_inr": 1, "pre_assessment_fee_currency": 1,
             "country": 1, "visa_type": 1},
        )
        if p and p.get("pre_assessment_fee_inr") is not None:
            return {
                "amount": int(p["pre_assessment_fee_inr"]),
                "currency": p.get("pre_assessment_fee_currency", "INR"),
                "source": "product_override",
                "product_id": product_id,
                "resolved_at": now.isoformat(),
            }

    # P2 — per country + visa
    if country and visa:
        q = {
            "country_code": country, "visa_category": visa, "status": "active",
            "$or": [{"effective_until": None}, {"effective_until": {"$gte": now}}],
            "effective_from": {"$lte": now},
        }
        policy = await db[COLLECTION].find_one(q, {"_id": 0}, sort=[("effective_from", -1)])
        if policy:
            return {
                "amount": int(policy["fee_inr"]),
                "currency": policy.get("currency", "INR"),
                "source": "country_visa_policy",
                "policy_id": policy.get("id"),
                "policy_name": policy.get("policy_name"),
                "country_code": country, "visa_category": visa,
                "resolved_at": now.isoformat(),
            }

    # P3 — GLOBAL fallback
    global_q = {
        "country_code": "GLOBAL", "visa_category": "ANY", "status": "active",
        "$or": [{"effective_until": None}, {"effective_until": {"$gte": now}}],
        "effective_from": {"$lte": now},
    }
    g = await db[COLLECTION].find_one(global_q, {"_id": 0}, sort=[("effective_from", -1)])
    if g:
        return {
            "amount": int(g["fee_inr"]),
            "currency": g.get("currency", "INR"),
            "source": "global_fallback",
            "policy_id": g.get("id"),
            "policy_name": g.get("policy_name"),
            "resolved_at": now.isoformat(),
        }

    # P4 — last-resort hardcoded safety net
    return {
        "amount": HARDCODED_SAFETY_NET_INR,
        "currency": "INR",
        "source": "hardcoded_safety_net",
        "warning": "No DB policies matched — using hardcoded fallback. Add a GLOBAL policy via /admin/fee-policies.",
        "resolved_at": now.isoformat(),
    }
