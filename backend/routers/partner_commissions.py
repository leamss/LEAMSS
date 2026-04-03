"""Partner Product Commissions Router — per-partner, per-product custom rates"""
from fastapi import APIRouter, HTTPException, Depends
from core.database import partner_product_commissions_col, users_col, products_col
from core.auth import get_current_user
import uuid
from datetime import datetime, timezone

router = APIRouter(prefix="/partner-commissions", tags=["Partner Commissions"])


@router.get("")
async def get_all_partner_commissions(current_user: dict = Depends(get_current_user)):
    """Get all custom partner-product commission mappings"""
    if current_user["role"] not in ["admin"]:
        raise HTTPException(status_code=403, detail="Admin only")

    mappings = await partner_product_commissions_col.find({}, {"_id": 0}).to_list(1000)

    # Batch-fetch partner and product names
    partner_ids = list({m["partner_id"] for m in mappings})
    product_ids = list({m["product_id"] for m in mappings})
    partners = await users_col.find({"id": {"$in": partner_ids}}, {"_id": 0, "password": 0}).to_list(500) if partner_ids else []
    products = await products_col.find({"id": {"$in": product_ids}}, {"_id": 0}).to_list(500) if product_ids else []
    partners_map = {p["id"]: p["name"] for p in partners}
    products_map = {p["id"]: p["name"] for p in products}

    for m in mappings:
        m["partner_name"] = partners_map.get(m["partner_id"], "Unknown")
        m["product_name"] = products_map.get(m["product_id"], "Unknown")
        if isinstance(m.get("updated_at"), datetime):
            m["updated_at"] = m["updated_at"].isoformat()
    return mappings


@router.get("/partner/{partner_id}")
async def get_partner_commissions(partner_id: str, current_user: dict = Depends(get_current_user)):
    """Get all custom commission rates for a specific partner"""
    if current_user["role"] not in ["admin", "partner"]:
        raise HTTPException(status_code=403, detail="Admin or Partner only")
    if current_user["role"] == "partner" and current_user["id"] != partner_id:
        raise HTTPException(status_code=403, detail="Cannot view other partner's commissions")

    mappings = await partner_product_commissions_col.find(
        {"partner_id": partner_id}, {"_id": 0}
    ).to_list(100)

    product_ids = [m["product_id"] for m in mappings]
    products = await products_col.find({"id": {"$in": product_ids}}, {"_id": 0}).to_list(100) if product_ids else []
    products_map = {p["id"]: p["name"] for p in products}

    for m in mappings:
        m["product_name"] = products_map.get(m["product_id"], "Unknown")
        if isinstance(m.get("updated_at"), datetime):
            m["updated_at"] = m["updated_at"].isoformat()
    return mappings


@router.post("")
async def set_partner_commission(data: dict, current_user: dict = Depends(get_current_user)):
    """Set a custom commission rate for a partner on a specific product"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    partner_id = data.get("partner_id")
    product_id = data.get("product_id")
    rate = data.get("commission_rate")

    if not partner_id or not product_id or rate is None:
        raise HTTPException(status_code=400, detail="partner_id, product_id, and commission_rate are required")
    if rate < 0 or rate > 100:
        raise HTTPException(status_code=400, detail="Commission rate must be between 0 and 100")

    # Verify partner and product exist
    partner = await users_col.find_one({"id": partner_id, "role": "partner"})
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    product = await products_col.find_one({"id": product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    existing = await partner_product_commissions_col.find_one(
        {"partner_id": partner_id, "product_id": product_id}
    )
    if existing:
        await partner_product_commissions_col.update_one(
            {"partner_id": partner_id, "product_id": product_id},
            {"$set": {"commission_rate": rate, "updated_at": datetime.now(timezone.utc), "updated_by": current_user["id"]}}
        )
        return {"message": f"Commission rate updated to {rate}% for {partner['name']} on {product['name']}"}
    else:
        await partner_product_commissions_col.insert_one({
            "id": str(uuid.uuid4()),
            "partner_id": partner_id,
            "product_id": product_id,
            "commission_rate": rate,
            "updated_at": datetime.now(timezone.utc),
            "updated_by": current_user["id"]
        })
        return {"message": f"Custom commission rate {rate}% set for {partner['name']} on {product['name']}"}


@router.delete("")
async def delete_partner_commission(data: dict, current_user: dict = Depends(get_current_user)):
    """Remove a custom commission rate (falls back to partner default)"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    partner_id = data.get("partner_id")
    product_id = data.get("product_id")
    if not partner_id or not product_id:
        raise HTTPException(status_code=400, detail="partner_id and product_id are required")

    result = await partner_product_commissions_col.delete_one(
        {"partner_id": partner_id, "product_id": product_id}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Custom commission not found")
    return {"message": "Custom commission removed. Partner's default rate will be used."}


@router.get("/resolve/{partner_id}/{product_id}")
async def resolve_commission_rate(partner_id: str, product_id: str, current_user: dict = Depends(get_current_user)):
    """Resolve the effective commission rate for a partner + product combination.
    Priority: custom rate > partner default rate > global default rate."""
    custom = await partner_product_commissions_col.find_one(
        {"partner_id": partner_id, "product_id": product_id}, {"_id": 0}
    )
    if custom:
        return {"rate": custom["commission_rate"], "source": "custom_product"}

    partner = await users_col.find_one({"id": partner_id}, {"_id": 0, "password": 0})
    if partner and partner.get("commission_rate", 0) > 0:
        return {"rate": partner["commission_rate"], "source": "partner_default"}

    from core.database import settings_col
    settings = await settings_col.find_one({"key": "global"}, {"_id": 0})
    default_rate = settings.get("default_commission_rate", 10) if settings else 10
    return {"rate": default_rate, "source": "global_default"}
