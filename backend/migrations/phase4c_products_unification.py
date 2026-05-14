"""Phase 4C — Products Unification Migration.

Merges `product_cost_structures` collection into `products` so there is ONE
source of truth. Idempotent — running again has no side effects.

Strategy:
  • For each cost-structure doc, find the matching product by:
      1. exact `product_id` link (if set)
      2. case-insensitive name match
      3. country + visa_type pair match
  • If match found, extend that product with cost-structure fields.
  • If no match, create a NEW product (carrying over name/country/visa_type).
  • Mark cost-structure doc with `migrated_to_product_id` so we never re-migrate.

Adds the following fields to `products`:
  - country: str
  - visa_type: str
  - service_price: float  (mirrors base_fee — kept synchronized)
  - cost_allocations: list[dict]
  - success_bonuses: list[dict]
  - cost_structure_meta: dict  (description, default_currency, last_recomputed_at)
"""
import asyncio
import logging
import uuid
from datetime import datetime, timezone

from core.database import db

logger = logging.getLogger(__name__)
products_col = db["products"]
cs_col = db["product_cost_structures"]


async def _find_matching_product(cs: dict):
    pid = cs.get("product_id")
    if pid:
        p = await products_col.find_one({"id": pid}, {"_id": 0})
        if p:
            return p
    # Name match (case-insensitive)
    name = (cs.get("product_name") or "").strip()
    if name:
        import re
        p = await products_col.find_one({"name": {"$regex": f"^{re.escape(name)}$", "$options": "i"}}, {"_id": 0})
        if p:
            return p
    # Country + visa_type pair
    country = (cs.get("country") or "").strip()
    visa = (cs.get("visa_type") or "").strip()
    if country and visa:
        p = await products_col.find_one({"country": country, "visa_type": visa}, {"_id": 0})
        if p:
            return p
    return None


def _compute_margin(service_price: float, cost_allocations: list, success_bonuses: list) -> dict:
    """Replicate the cost-structure margin computation for product overview."""
    sp = float(service_price or 0)
    base_cost = 0.0
    for a in (cost_allocations or []):
        if a.get("is_optional"):
            continue
        ptype = a.get("payment_type", "flat")
        if ptype == "percentage":
            base_cost += sp * float(a.get("rate", 0) or 0) / 100.0
        else:
            base_cost += float(a.get("amount", 0) or 0)
    margin = sp - base_cost
    return {
        "expected_base_cost": round(base_cost, 2),
        "expected_margin": round(margin, 2),
        "expected_margin_pct": round((margin / sp * 100), 2) if sp > 0 else 0,
        "max_bonus_payout": round(sum(float(b.get("amount", 0) or 0) for b in (success_bonuses or [])), 2),
    }


async def run() -> dict:
    """Returns counts: {migrated, matched, created, skipped, legacy_backfilled}."""
    stats = {"matched": 0, "created": 0, "skipped": 0, "total": 0, "legacy_backfilled": 0}

    # ── Backfill legacy products that lack the unified shape ──
    default_fields = {
        "country": "",
        "visa_type": "",
        "service_price": 0,
        "cost_allocations": [],
        "success_bonuses": [],
        "computed": {"expected_base_cost": 0, "expected_margin": 0, "expected_margin_pct": 0, "max_bonus_payout": 0},
        "cost_structure_meta": {},
    }
    # First $set defaults only on docs missing `country` field
    legacy_filter = {"country": {"$exists": False}}
    res = await products_col.update_many(legacy_filter, {"$set": default_fields})
    stats["legacy_backfilled"] = res.modified_count
    # Mirror base_fee into service_price for products where service_price stayed 0 but base_fee>0
    res2 = await products_col.update_many(
        {"$or": [{"service_price": 0}, {"service_price": {"$exists": False}}], "base_fee": {"$gt": 0}},
        [{"$set": {"service_price": "$base_fee"}}],
    )
    stats["legacy_backfilled"] += res2.modified_count

    # ── Merge cost-structure docs into matching/new products ──
    cursor = cs_col.find({}, {"_id": 0})
    async for cs in cursor:
        stats["total"] += 1
        if cs.get("migrated_to_product_id"):
            stats["skipped"] += 1
            continue

        product = await _find_matching_product(cs)
        now = datetime.now(timezone.utc)
        cost_payload = {
            "country": cs.get("country") or "",
            "visa_type": cs.get("visa_type") or "",
            "service_price": float(cs.get("service_price") or 0),
            "cost_allocations": cs.get("cost_allocations") or [],
            "success_bonuses": cs.get("success_bonuses") or [],
            "cost_structure_meta": {
                "description": cs.get("description") or "",
                "default_currency": cs.get("default_currency") or "INR",
                "is_active": cs.get("is_active", True),
                "migrated_from_cs_id": cs.get("id"),
                "migrated_at": now,
            },
            "computed": _compute_margin(
                cs.get("service_price"), cs.get("cost_allocations"), cs.get("success_bonuses")
            ),
            "updated_at": now,
        }

        if product:
            # Update existing product
            await products_col.update_one({"id": product["id"]}, {"$set": cost_payload})
            await cs_col.update_one({"id": cs["id"]}, {"$set": {"migrated_to_product_id": product["id"], "migrated_at": now}})
            stats["matched"] += 1
            logger.info(f"Migration: matched CS '{cs.get('product_name')}' → product '{product.get('name')}' ({product['id']})")
        else:
            # Create a new product from the cost structure
            new_product = {
                "id": str(uuid.uuid4()),
                "name": cs.get("product_name") or f"{cost_payload['country']} {cost_payload['visa_type']}",
                "description": (cs.get("description") or "").strip(),
                "category": "immigration",
                "base_fee": cost_payload["service_price"],
                "commission_rate": 0,
                "commission_type": "percentage",
                "status": "active",
                "created_at": now,
                "created_via_migration": True,
                **cost_payload,
            }
            await products_col.insert_one(new_product)
            await cs_col.update_one({"id": cs["id"]}, {"$set": {"migrated_to_product_id": new_product["id"], "migrated_at": now}})
            stats["created"] += 1
            logger.info(f"Migration: created NEW product '{new_product['name']}' ({new_product['id']}) from CS")

    return stats


if __name__ == "__main__":
    asyncio.run(run())
