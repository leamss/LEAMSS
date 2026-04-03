"""Analytics Router"""
from fastapi import APIRouter, Depends, Query
from core.database import sales_col, cases_col, users_col, products_col
from core.auth import get_current_user
from datetime import datetime, timedelta, timezone

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/sales-trend")
async def sales_trend(days: int = Query(30), current_user: dict = Depends(get_current_user)):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    pipeline = [
        {"$match": {"created_at": {"$gte": since}}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
            "count": {"$sum": 1},
            "revenue": {"$sum": {"$cond": [{"$eq": ["$status", "approved"]}, "$fee_amount", 0]}}
        }},
        {"$sort": {"_id": 1}}
    ]
    cursor = sales_col.aggregate(pipeline)
    data = []
    async for item in cursor:
        data.append({"date": item["_id"], "count": item["count"], "revenue": item["revenue"]})
    return {"data": data, "period_days": days}


@router.get("/sales-by-status")
async def sales_by_status(current_user: dict = Depends(get_current_user)):
    pipeline = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}, "total": {"$sum": "$fee_amount"}}}
    ]
    cursor = sales_col.aggregate(pipeline)
    data = []
    async for item in cursor:
        data.append({"status": item["_id"], "count": item["count"], "total": item["total"]})
    return {"data": data}


@router.get("/top-products")
async def top_products(current_user: dict = Depends(get_current_user)):
    pipeline = [
        {"$group": {"_id": "$product_id", "count": {"$sum": 1}, "revenue": {"$sum": "$fee_amount"}}},
        {"$sort": {"revenue": -1}}, {"$limit": 10}
    ]
    cursor = sales_col.aggregate(pipeline)
    data = []
    async for item in cursor:
        product = await products_col.find_one({"id": item["_id"]}, {"_id": 0})
        data.append({
            "product_name": product["name"] if product else "Unknown",
            "count": item["count"], "revenue": item["revenue"]
        })
    return {"data": data}


@router.get("/top-partners")
async def top_partners(current_user: dict = Depends(get_current_user)):
    pipeline = [
        {"$match": {"status": "approved"}},
        {"$group": {"_id": "$partner_id", "count": {"$sum": 1}, "revenue": {"$sum": "$fee_amount"}, "commission": {"$sum": "$commission_amount"}}},
        {"$sort": {"revenue": -1}}, {"$limit": 10}
    ]
    cursor = sales_col.aggregate(pipeline)
    data = []
    async for item in cursor:
        partner = await users_col.find_one({"id": item["_id"]}, {"_id": 0, "password": 0})
        data.append({
            "partner_name": partner["name"] if partner else "Unknown",
            "count": item["count"], "revenue": item["revenue"], "commission": item.get("commission", 0)
        })
    return {"data": data}


@router.get("/document-status")
async def document_status(current_user: dict = Depends(get_current_user)):
    from core.database import documents_col
    pipeline = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]
    cursor = documents_col.aggregate(pipeline)
    data = []
    async for item in cursor:
        data.append({"status": item["_id"], "count": item["count"]})
    return {"data": data}
