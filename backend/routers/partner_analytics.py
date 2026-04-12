"""Partner Analytics & Performance Router"""
import os
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Query
from core.database import db
from routers.auth import get_current_user

router = APIRouter(prefix="/partner-analytics", tags=["Partner Analytics"])

sales_col = db["sales"]
pre_assessments_col = db["pre_assessments"]
cases_col = db["cases"]
users_col = db["users"]
surveys_col = db["surveys"]


@router.get("/performance")
async def get_performance(current_user: dict = Depends(get_current_user)):
    """Get partner performance metrics"""
    partner_id = current_user["id"]
    is_admin = current_user["role"] == "admin"
    query = {} if is_admin else {"partner_id": partner_id}

    # Sales stats
    total_sales = await sales_col.count_documents(query)
    approved_sales = await sales_col.count_documents({**query, "status": "approved"})
    pending_sales = await sales_col.count_documents({**query, "status": "pending"})
    rejected_sales = await sales_col.count_documents({**query, "status": "rejected"})

    # Revenue
    pipeline = [{"$match": {**query, "status": "approved"}},
                {"$group": {"_id": None, "total_fee": {"$sum": "$fee_amount"},
                            "total_received": {"$sum": "$amount_received"},
                            "total_commission": {"$sum": "$commission_amount"}}}]
    rev = await sales_col.aggregate(pipeline).to_list(1)
    rev_data = rev[0] if rev else {"total_fee": 0, "total_received": 0, "total_commission": 0}

    # Pre-assessment stats
    pa_query = {} if is_admin else {"partner_id": partner_id}
    total_leads = await pre_assessments_col.count_documents(pa_query)
    approved_leads = await pre_assessments_col.count_documents({**pa_query, "stage": {"$in": ["approved", "proposal_sent", "case_created"]}})
    rejected_leads = await pre_assessments_col.count_documents({**pa_query, "stage": {"$in": ["rejected", "refund_initiated", "refunded"]}})

    # Conversion rate
    conversion_rate = round((approved_sales / total_leads * 100) if total_leads > 0 else 0, 1)

    # Average deal size
    avg_deal = round(rev_data["total_fee"] / approved_sales) if approved_sales > 0 else 0

    # Monthly trend (last 6 months)
    monthly_trend = []
    for i in range(5, -1, -1):
        month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(days=30 * i)
        month_end = month_start + timedelta(days=32)
        month_end = month_end.replace(day=1)
        month_sales = await sales_col.count_documents({
            **query, "status": "approved",
            "created_at": {"$gte": month_start, "$lt": month_end}
        })
        month_rev_pipeline = [
            {"$match": {**query, "status": "approved", "created_at": {"$gte": month_start, "$lt": month_end}}},
            {"$group": {"_id": None, "revenue": {"$sum": "$fee_amount"}, "commission": {"$sum": "$commission_amount"}}}
        ]
        month_rev = await sales_col.aggregate(month_rev_pipeline).to_list(1)
        m_data = month_rev[0] if month_rev else {"revenue": 0, "commission": 0}
        monthly_trend.append({
            "month": month_start.strftime("%b %Y"),
            "sales": month_sales,
            "revenue": m_data.get("revenue", 0),
            "commission": m_data.get("commission", 0)
        })

    # Top products
    product_pipeline = [
        {"$match": {**query, "status": "approved"}},
        {"$group": {"_id": "$product_name", "count": {"$sum": 1}, "revenue": {"$sum": "$fee_amount"}}},
        {"$sort": {"count": -1}}, {"$limit": 5}
    ]
    top_products = await sales_col.aggregate(product_pipeline).to_list(5)

    # Top countries (from pre-assessments)
    country_pipeline = [
        {"$match": pa_query},
        {"$group": {"_id": "$country", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}, {"$limit": 5}
    ]
    top_countries = await pre_assessments_col.aggregate(country_pipeline).to_list(5)

    return {
        "sales": {
            "total": total_sales, "approved": approved_sales,
            "pending": pending_sales, "rejected": rejected_sales,
            "approval_rate": round((approved_sales / total_sales * 100) if total_sales > 0 else 0, 1)
        },
        "revenue": {
            "total_fee": rev_data.get("total_fee", 0),
            "total_received": rev_data.get("total_received", 0),
            "total_commission": rev_data.get("total_commission", 0),
            "avg_deal_size": avg_deal,
            "collection_rate": round((rev_data.get("total_received", 0) / rev_data.get("total_fee", 1)) * 100, 1) if rev_data.get("total_fee", 0) > 0 else 0
        },
        "leads": {
            "total": total_leads, "approved": approved_leads,
            "rejected": rejected_leads,
            "conversion_rate": conversion_rate
        },
        "monthly_trend": monthly_trend,
        "top_products": [{"name": p["_id"] or "Unknown", "count": p["count"], "revenue": p["revenue"]} for p in top_products],
        "top_countries": [{"name": c["_id"] or "Unknown", "count": c["count"]} for c in top_countries],
    }


@router.get("/leaderboard")
async def get_leaderboard(current_user: dict = Depends(get_current_user)):
    """Get partner leaderboard"""
    pipeline = [
        {"$match": {"status": "approved"}},
        {"$group": {
            "_id": "$partner_id",
            "partner_name": {"$first": "$partner_name"},
            "total_sales": {"$sum": 1},
            "total_revenue": {"$sum": "$fee_amount"},
            "total_commission": {"$sum": "$commission_amount"},
        }},
        {"$sort": {"total_revenue": -1}},
        {"$limit": 10}
    ]
    leaders = await sales_col.aggregate(pipeline).to_list(10)

    result = []
    for idx, leader in enumerate(leaders):
        # Get lead count
        leads = await pre_assessments_col.count_documents({"partner_id": leader["_id"]})
        result.append({
            "rank": idx + 1,
            "partner_id": leader["_id"],
            "partner_name": leader.get("partner_name", "Unknown"),
            "total_sales": leader["total_sales"],
            "total_revenue": leader["total_revenue"],
            "total_commission": leader["total_commission"],
            "total_leads": leads,
            "is_you": leader["_id"] == current_user["id"]
        })

    return result


@router.get("/targets")
async def get_targets(current_user: dict = Depends(get_current_user)):
    """Get partner monthly targets and progress"""
    partner_id = current_user["id"]
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    query = {"partner_id": partner_id, "created_at": {"$gte": month_start}}
    month_sales = await sales_col.count_documents({**query})
    month_approved = await sales_col.count_documents({**query, "status": "approved"})

    rev_pipeline = [
        {"$match": {**query, "status": "approved"}},
        {"$group": {"_id": None, "revenue": {"$sum": "$fee_amount"}, "commission": {"$sum": "$commission_amount"}}}
    ]
    rev = await sales_col.aggregate(rev_pipeline).to_list(1)
    rev_data = rev[0] if rev else {"revenue": 0, "commission": 0}

    month_leads = await pre_assessments_col.count_documents({"partner_id": partner_id, "created_at": {"$gte": month_start}})

    # Default targets (can be made configurable later)
    targets = {
        "monthly_sales_target": 10,
        "monthly_revenue_target": 500000,
        "monthly_leads_target": 15,
        "monthly_commission_target": 50000,
    }

    return {
        "current_month": now.strftime("%B %Y"),
        "targets": targets,
        "progress": {
            "sales": month_sales,
            "approved_sales": month_approved,
            "revenue": rev_data.get("revenue", 0),
            "commission": rev_data.get("commission", 0),
            "leads": month_leads,
        },
        "completion": {
            "sales": round((month_sales / targets["monthly_sales_target"]) * 100, 1) if targets["monthly_sales_target"] > 0 else 0,
            "revenue": round((rev_data.get("revenue", 0) / targets["monthly_revenue_target"]) * 100, 1) if targets["monthly_revenue_target"] > 0 else 0,
            "leads": round((month_leads / targets["monthly_leads_target"]) * 100, 1) if targets["monthly_leads_target"] > 0 else 0,
            "commission": round((rev_data.get("commission", 0) / targets["monthly_commission_target"]) * 100, 1) if targets["monthly_commission_target"] > 0 else 0,
        }
    }


@router.get("/pipeline-summary")
async def get_pipeline_summary(current_user: dict = Depends(get_current_user)):
    """Get pre-assessment pipeline summary grouped by stage"""
    query = {"partner_id": current_user["id"]} if current_user["role"] != "admin" else {}

    pipeline = [
        {"$match": query},
        {"$group": {
            "_id": "$stage",
            "count": {"$sum": 1},
            "items": {"$push": {
                "id": "$id", "pa_number": "$pa_number",
                "client_name": "$client_name", "country": "$country",
                "service_type": "$service_type", "created_at": "$created_at"
            }}
        }},
        {"$sort": {"_id": 1}}
    ]
    stages = await pre_assessments_col.aggregate(pipeline).to_list(20)

    result = {}
    for stage in stages:
        items = stage.get("items", [])
        for item in items:
            if item.get("created_at") and hasattr(item["created_at"], "isoformat"):
                item["created_at"] = item["created_at"].isoformat()
        result[stage["_id"]] = {"count": stage["count"], "items": items[:10]}

    return result
