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


STAGE_MAPPING = {
    "payment_done": "payment_received",
    "paid": "payment_received",
    "converted": "case_created",
}


@router.get("/pipeline-summary")
async def get_pipeline_summary(current_user: dict = Depends(get_current_user)):
    """Get lead and pre-assessment pipeline summary grouped by stage with full contact details for follow-up."""
    role = current_user.get("role") or ""
    rbac_role = current_user.get("rbac_role") or ""
    is_admin = role in ("admin", "admin_owner") or rbac_role in ("admin", "admin_owner") or "*" in (current_user.get("permissions") or [])

    if is_admin:
        pa_query = {}
        lead_query = {}
    else:
        uid = current_user["id"]
        uemail = (current_user.get("email") or "").lower()
        pid = current_user.get("partner_id") or (uid if role == "partner" or rbac_role == "partner" else None)
        
        user_matches = [
            {"partner_id": uid},
            {"assigned_to": uid},
            {"created_by_user_id": uid},
            {"created_by": uid},
        ]
        if uemail:
            user_matches.extend([
                {"partner_id": uemail},
                {"assigned_to": uemail},
                {"created_by_email": uemail},
            ])
        if pid:
            user_matches.append({"partner_id": pid})
            
        pa_query = {"$or": user_matches}

        lead_matches = [
            {"partner_id": uid},
            {"assigned_to": uid},
            {"created_by": uid},
        ]
        if uemail:
            lead_matches.extend([
                {"partner_id": uemail},
                {"assigned_to": uemail},
            ])
        if pid:
            lead_matches.append({"partner_id": pid})
        lead_query = {"$or": lead_matches}

    # 1. Fetch PAs
    pas = await pre_assessments_col.find(pa_query, {"_id": 0}).sort("created_at", -1).to_list(2000)
    
    # 2. Fetch Leads
    leads = await db["leads"].find(lead_query, {"_id": 0}).sort("created_at", -1).to_list(2000)

    # 3. Merge without duplicates
    items_by_id = {}
    linked_lead_ids = set()

    for pa in pas:
        pa_id = pa.get("id")
        lead_id = pa.get("lead_id")
        if lead_id:
            linked_lead_ids.add(lead_id)
        
        raw_stage = pa.get("stage") or "new"
        stage = STAGE_MAPPING.get(raw_stage, raw_stage)
        
        created_at = pa.get("created_at")
        if isinstance(created_at, datetime):
            created_at = created_at.isoformat()

        item = {
            "id": pa_id,
            "pa_number": pa.get("pa_number") or f"PA-{pa_id[:6].upper() if pa_id else 'N/A'}",
            "client_name": pa.get("client_name") or "Unnamed Client",
            "client_email": pa.get("client_email"),
            "client_mobile": pa.get("client_mobile") or pa.get("client_phone"),
            "country": pa.get("country") or "Global",
            "service_type": pa.get("service_type") or "PR",
            "stage": stage,
            "raw_stage": raw_stage,
            "lead_id": lead_id,
            "fee_payment_status": pa.get("fee_payment_status"),
            "notes": pa.get("notes") or "",
            "education": pa.get("education") or "",
            "work_experience": pa.get("work_experience") or "",
            "created_at": created_at,
            "assigned_to": pa.get("assigned_to"),
            "assigned_to_name": pa.get("assigned_to_name"),
            "partner_id": pa.get("partner_id"),
            "partner_name": pa.get("partner_name"),
            "item_type": "pre_assessment"
        }
        items_by_id[pa_id] = item

    for l in leads:
        l_id = l.get("id")
        if l_id in linked_lead_ids or l.get("pa_id") in items_by_id:
            target_pa_id = l.get("pa_id")
            if target_pa_id and target_pa_id in items_by_id:
                if not items_by_id[target_pa_id].get("client_mobile"):
                    items_by_id[target_pa_id]["client_mobile"] = l.get("mobile_number") or l.get("mobile_full") or l.get("phone")
                if not items_by_id[target_pa_id].get("education"):
                    items_by_id[target_pa_id]["education"] = l.get("qualification")
                if not items_by_id[target_pa_id].get("work_experience"):
                    items_by_id[target_pa_id]["work_experience"] = l.get("experience")
            continue

        raw_stage = l.get("stage") or "new"
        stage = STAGE_MAPPING.get(raw_stage, raw_stage)
        
        created_at = l.get("created_at")
        if isinstance(created_at, datetime):
            created_at = created_at.isoformat()

        item = {
            "id": l_id,
            "pa_number": l.get("lead_number") or l.get("unique_id") or "LEAD",
            "client_name": l.get("name") or l.get("client_name") or l.get("full_name") or "Unnamed Lead",
            "client_email": l.get("email") or l.get("client_email"),
            "client_mobile": l.get("mobile_number") or l.get("mobile_full") or l.get("phone") or l.get("client_mobile"),
            "country": l.get("country") or l.get("destination_country") or "Global",
            "service_type": l.get("service_type") or l.get("visa_type") or "PR",
            "stage": stage,
            "raw_stage": raw_stage,
            "lead_id": l_id,
            "fee_payment_status": l.get("payment_status") or ("paid" if stage == "payment_received" else "unpaid"),
            "notes": l.get("notes") if isinstance(l.get("notes"), str) else "",
            "education": l.get("qualification") or l.get("education") or "",
            "work_experience": l.get("experience") or l.get("work_experience") or "",
            "created_at": created_at,
            "assigned_to": l.get("assigned_to"),
            "assigned_to_name": l.get("assigned_to_name"),
            "partner_id": l.get("partner_id"),
            "partner_name": l.get("partner_name"),
            "item_type": "lead"
        }
        items_by_id[f"lead_{l_id}"] = item

    result = {}
    for item in items_by_id.values():
        st = item["stage"]
        if st not in result:
            result[st] = {"count": 0, "items": []}
        result[st]["count"] += 1
        result[st]["items"].append(item)

    return result
