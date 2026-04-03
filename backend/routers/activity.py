"""Activity / Audit Logs Router"""
from fastapi import APIRouter, Depends, Query
from core.database import audit_logs_col, users_col
from core.auth import get_current_user
from datetime import datetime, timedelta, timezone

router = APIRouter(prefix="/activity", tags=["Activity"])


@router.get("/logs")
async def get_logs(
    entity_type: str = None,
    action: str = None,
    user_id: str = None,
    days: int = Query(30),
    limit: int = Query(100),
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] != "admin":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Admin only")
    
    query = {}
    if entity_type:
        query["entity_type"] = entity_type
    if action:
        query["action"] = action
    if user_id:
        query["user_id"] = user_id
    
    if days:
        query["created_at"] = {"$gte": datetime.now(timezone.utc) - timedelta(days=days)}
    
    logs = await audit_logs_col.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    
    for log in logs:
        user = await users_col.find_one({"id": log.get("user_id")}, {"_id": 0, "password": 0})
        log["user_name"] = user["name"] if user else "Unknown"
        log["user_role"] = user["role"] if user else "unknown"
        if isinstance(log.get("created_at"), datetime):
            log["created_at"] = log["created_at"].isoformat()
    
    return logs


@router.get("/stats")
async def get_stats(days: int = Query(7), current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Admin only")
    
    since = datetime.now(timezone.utc) - timedelta(days=days)
    query = {"created_at": {"$gte": since}}
    
    total = await audit_logs_col.count_documents(query)
    
    # By type
    pipeline = [
        {"$match": query},
        {"$group": {"_id": "$entity_type", "count": {"$sum": 1}}}
    ]
    by_type_cursor = audit_logs_col.aggregate(pipeline)
    by_type = {}
    async for item in by_type_cursor:
        by_type[item["_id"]] = item["count"]
    
    # By action
    pipeline2 = [
        {"$match": query},
        {"$group": {"_id": "$action", "count": {"$sum": 1}}}
    ]
    by_action_cursor = audit_logs_col.aggregate(pipeline2)
    by_action = {}
    async for item in by_action_cursor:
        by_action[item["_id"]] = item["count"]
    
    # By date
    pipeline3 = [
        {"$match": query},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}}
    ]
    by_date_cursor = audit_logs_col.aggregate(pipeline3)
    by_date = []
    async for item in by_date_cursor:
        by_date.append({"date": item["_id"], "count": item["count"]})
    
    # Most active users
    pipeline4 = [
        {"$match": query},
        {"$group": {"_id": "$user_id", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    active_users_cursor = audit_logs_col.aggregate(pipeline4)
    active_users = []
    async for item in active_users_cursor:
        user = await users_col.find_one({"id": item["_id"]}, {"_id": 0, "password": 0})
        active_users.append({
            "user_id": item["_id"],
            "user_name": user["name"] if user else "Unknown",
            "user_role": user["role"] if user else "unknown",
            "count": item["count"]
        })
    
    return {
        "total_activities": total,
        "activities_by_type": by_type,
        "activities_by_action": by_action,
        "activities_by_date": by_date,
        "most_active_users": active_users,
        "period_days": days
    }
