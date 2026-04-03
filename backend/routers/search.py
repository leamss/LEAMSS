"""Search Router"""
from fastapi import APIRouter, Depends, Query
from core.database import users_col, sales_col, cases_col, products_col, tickets_col
from core.auth import get_current_user
from datetime import datetime
import re

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("/global")
async def global_search(q: str = Query(..., min_length=1), current_user: dict = Depends(get_current_user)):
    regex = {"$regex": re.escape(q), "$options": "i"}
    
    users = await users_col.find(
        {"$or": [{"name": regex}, {"email": regex}]},
        {"_id": 0, "password": 0}
    ).to_list(10)
    for u in users:
        u["type"] = "user"
        if isinstance(u.get("created_at"), datetime):
            u["created_at"] = u["created_at"].isoformat()
    
    cases = await cases_col.find(
        {"$or": [{"case_id": regex}]},
        {"_id": 0}
    ).to_list(10)
    for c in cases:
        c["type"] = "case"
        for f in ["created_at"]:
            if isinstance(c.get(f), datetime):
                c[f] = c[f].isoformat()
    
    products = await products_col.find({"$or": [{"name": regex}, {"description": regex}]}, {"_id": 0}).to_list(10)
    for p in products:
        p["type"] = "product"
        if isinstance(p.get("created_at"), datetime):
            p["created_at"] = p["created_at"].isoformat()
    
    sales = await sales_col.find(
        {"$or": [{"client_name": regex}, {"client_email": regex}]},
        {"_id": 0}
    ).to_list(10)
    for s in sales:
        s["type"] = "sale"
        for f in ["created_at", "approved_at"]:
            if isinstance(s.get(f), datetime):
                s[f] = s[f].isoformat()
    
    return {
        "users": users, "cases": cases,
        "products": products, "sales": sales,
        "total_count": len(users) + len(cases) + len(products) + len(sales)
    }


@router.get("/quick")
async def quick_search(q: str = Query(..., min_length=1), current_user: dict = Depends(get_current_user)):
    regex = {"$regex": re.escape(q), "$options": "i"}
    results = []
    
    users = await users_col.find({"$or": [{"name": regex}, {"email": regex}]}, {"_id": 0, "password": 0}).to_list(5)
    for u in users:
        results.append({"id": u["id"], "title": u["name"], "subtitle": u["email"], "type": "user"})
    
    cases = await cases_col.find({"case_id": regex}, {"_id": 0}).to_list(5)
    for c in cases:
        results.append({"id": c["id"], "title": c["case_id"], "subtitle": c.get("status", ""), "type": "case"})
    
    products = await products_col.find({"name": regex}, {"_id": 0}).to_list(5)
    for p in products:
        results.append({"id": p["id"], "title": p["name"], "subtitle": p.get("category", ""), "type": "product"})
    
    return results[:15]
