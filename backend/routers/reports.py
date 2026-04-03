"""Reports Router"""
from fastapi import APIRouter, Depends
from core.database import sales_col, users_col, products_col
from core.auth import get_current_user
from datetime import datetime

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/sales")
async def get_sales_report(current_user: dict = Depends(get_current_user)):
    sales = await sales_col.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    
    if not sales:
        return []
    
    # Batch fetch
    partner_ids = list(set(s.get("partner_id") for s in sales if s.get("partner_id")))
    product_ids = list(set(s.get("product_id") for s in sales if s.get("product_id")))
    partners_list = await users_col.find({"id": {"$in": partner_ids}}, {"_id": 0, "password": 0}).to_list(500) if partner_ids else []
    products_list = await products_col.find({"id": {"$in": product_ids}}, {"_id": 0}).to_list(500) if product_ids else []
    partners_map = {p["id"]: p for p in partners_list}
    products_map = {p["id"]: p for p in products_list}
    
    result = []
    for s in sales:
        partner = partners_map.get(s.get("partner_id"))
        product = products_map.get(s.get("product_id"))
        fee = s.get("fee_amount", 0) or 0
        received = s.get("amount_received", 0) or 0
        result.append({
            "id": s["id"], "client_name": s["client_name"], "client_email": s["client_email"],
            "partner_name": partner["name"] if partner else "N/A",
            "product_name": product["name"] if product else "N/A",
            "product_category": product.get("category", "N/A") if product else "N/A",
            "fee_amount": fee,
            "amount_received": received,
            "pending_amount": round(fee - received, 2),
            "commission_amount": s.get("commission_amount", 0),
            "commission_rate": s.get("commission_rate", 0),
            "status": s["status"],
            "rejection_reason": s.get("rejection_reason", ""),
            "payment_method": s.get("payment_method", ""),
            "payment_status": s.get("payment_status", "pending"),
            "created_at": s.get("created_at", "").isoformat() if isinstance(s.get("created_at"), datetime) else str(s.get("created_at", "")),
            "approved_at": s.get("approved_at", "").isoformat() if isinstance(s.get("approved_at"), datetime) else str(s.get("approved_at", ""))
        })
    return result


@router.get("/partner-commissions")
async def get_partner_commissions(current_user: dict = Depends(get_current_user)):
    partners = await users_col.find({"role": "partner"}, {"_id": 0, "password": 0}).to_list(100)
    result = []
    for p in partners:
        sales = await sales_col.find({"partner_id": p["id"], "status": "approved"}, {"_id": 0}).to_list(1000)
        total_sales = len(sales)
        total_revenue = sum(s["fee_amount"] for s in sales)
        total_received = sum(s.get("amount_received", 0) for s in sales)
        total_commission = sum(s.get("commission_amount", 0) for s in sales)
        result.append({
            "partner_id": p["id"], "partner_name": p["name"],
            "commission_rate": p.get("commission_rate", 0),
            "total_sales": total_sales, "total_revenue": total_revenue,
            "total_received": total_received,
            "total_pending": round(total_revenue - total_received, 2),
            "total_commission": total_commission
        })
    return result
