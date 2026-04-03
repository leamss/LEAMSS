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


@router.get("/monthly-revenue")
async def monthly_revenue(current_user: dict = Depends(get_current_user)):
    """Get monthly revenue breakdown for the last 12 months"""
    pipeline = [
        {"$match": {"status": "approved"}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m", "date": "$created_at"}},
            "revenue": {"$sum": "$fee_amount"},
            "commission": {"$sum": "$commission_amount"},
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id": -1}},
        {"$limit": 12}
    ]
    try:
        cursor = sales_col.aggregate(pipeline)
        data = []
        async for item in cursor:
            data.append({
                "month": item["_id"],
                "revenue": item["revenue"],
                "commission": item["commission"],
                "count": item["count"]
            })
        return {"data": sorted(data, key=lambda x: x["month"])}
    except Exception:
        # Fallback if created_at is not a date type
        all_sales = await sales_col.find({"status": "approved"}, {"_id": 0}).to_list(5000)
        monthly = {}
        for s in all_sales:
            ca = s.get("created_at")
            if isinstance(ca, str):
                month_key = ca[:7]
            elif isinstance(ca, datetime):
                month_key = ca.strftime("%Y-%m")
            else:
                continue
            if month_key not in monthly:
                monthly[month_key] = {"revenue": 0, "commission": 0, "count": 0}
            monthly[month_key]["revenue"] += s.get("fee_amount", 0)
            monthly[month_key]["commission"] += s.get("commission_amount", 0)
            monthly[month_key]["count"] += 1
        data = [{"month": k, **v} for k, v in sorted(monthly.items())]
        return {"data": data}


@router.get("/case-completion-rate")
async def case_completion_rate(current_user: dict = Depends(get_current_user)):
    """Get case completion statistics"""
    total = await cases_col.count_documents({})
    completed = await cases_col.count_documents({"status": "completed"})
    active = await cases_col.count_documents({"status": {"$in": ["active", "in_progress"]}})
    rate = round((completed / total * 100), 1) if total > 0 else 0
    return {"total": total, "completed": completed, "active": active, "rate": rate}


@router.get("/dashboard")
async def analytics_dashboard(days: int = Query(30), current_user: dict = Depends(get_current_user)):
    """Comprehensive analytics data for the dashboard"""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Get all sales (handle both datetime and string created_at)
    all_sales = await sales_col.find({}, {"_id": 0}).to_list(10000)
    
    # Filter by date
    recent_sales = []
    for s in all_sales:
        ca = s.get("created_at")
        if isinstance(ca, datetime):
            if ca.tzinfo is None:
                ca = ca.replace(tzinfo=timezone.utc)
            if ca >= since:
                recent_sales.append(s)
        elif isinstance(ca, str):
            try:
                dt = datetime.fromisoformat(ca.replace('Z', '+00:00'))
                if dt >= since:
                    recent_sales.append(s)
            except (ValueError, TypeError):
                recent_sales.append(s)
        else:
            recent_sales.append(s)
    
    approved = [s for s in recent_sales if s.get("status") == "approved"]
    total_revenue = sum(s.get("fee_amount", 0) for s in approved)
    total_commission = sum(s.get("commission_amount", 0) for s in approved)
    
    # Cases
    total_cases = await cases_col.count_documents({})
    completed_cases = await cases_col.count_documents({"status": "completed"})
    completion_rate = round((completed_cases / total_cases * 100), 1) if total_cases > 0 else 0
    
    return {
        "total_revenue": total_revenue,
        "total_commission": total_commission,
        "total_sales": len(recent_sales),
        "approved_sales": len(approved),
        "completion_rate": completion_rate,
        "period_days": days
    }
