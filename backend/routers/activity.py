"""Activity / Audit Logs Router — Comprehensive Activity Tracking"""
from fastapi import APIRouter, Depends, Query
from core.database import audit_logs_col, users_col, cases_col
from core.auth import get_current_user
from datetime import datetime, timedelta, timezone

router = APIRouter(prefix="/activity", tags=["Activity"])


@router.get("/logs")
async def get_logs(
    entity_type: str = None,
    action: str = None,
    user_id: str = None,
    case_id: str = None,
    days: int = Query(30),
    limit: int = Query(100),
    skip: int = Query(0),
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
    if case_id:
        query["case_id"] = case_id
    if days:
        query["created_at"] = {"$gte": datetime.now(timezone.utc) - timedelta(days=days)}
    
    total = await audit_logs_col.count_documents(query)
    logs = await audit_logs_col.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).to_list(limit)
    
    # Enrich with user info
    user_cache = {}
    for log in logs:
        uid = log.get("user_id")
        if uid and uid not in user_cache:
            user = await users_col.find_one({"id": uid}, {"_id": 0, "name": 1, "role": 1, "email": 1})
            user_cache[uid] = user or {}
        u = user_cache.get(uid, {})
        log["user_name"] = log.get("user_name") or u.get("name", "Unknown")
        log["user_role"] = u.get("role", "unknown")
        log["user_email"] = u.get("email", "")
        if isinstance(log.get("created_at"), datetime):
            log["created_at"] = log["created_at"].isoformat()
    
    return {"logs": logs, "total": total}


@router.get("/live-feed")
async def get_live_feed(
    limit: int = Query(20),
    current_user: dict = Depends(get_current_user)
):
    """Get the most recent activity events for live dashboard feed"""
    if current_user["role"] != "admin":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Admin only")
    
    logs = await audit_logs_col.find({}, {"_id": 0}).sort("created_at", -1).to_list(limit)
    
    user_cache = {}
    for log in logs:
        uid = log.get("user_id")
        if uid and uid not in user_cache:
            user = await users_col.find_one({"id": uid}, {"_id": 0, "name": 1, "role": 1})
            user_cache[uid] = user or {}
        u = user_cache.get(uid, {})
        log["user_name"] = log.get("user_name") or u.get("name", "Unknown")
        log["user_role"] = u.get("role", "unknown")
        if isinstance(log.get("created_at"), datetime):
            log["created_at"] = log["created_at"].isoformat()
    
    return logs


@router.get("/case/{case_id}")
async def get_case_activity(
    case_id: str,
    limit: int = Query(100),
    current_user: dict = Depends(get_current_user)
):
    """Get all activity for a specific case"""
    if current_user["role"] not in ["admin", "case_manager"]:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Admin or Case Manager only")
    
    # Search by case_id field OR entity_id matching the case
    query = {"$or": [
        {"case_id": case_id},
        {"entity_id": case_id, "entity_type": "case"}
    ]}
    
    logs = await audit_logs_col.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    
    for log in logs:
        if isinstance(log.get("created_at"), datetime):
            log["created_at"] = log["created_at"].isoformat()
    
    return logs


@router.get("/user/{user_id}")
async def get_user_activity(
    user_id: str,
    days: int = Query(30),
    limit: int = Query(100),
    current_user: dict = Depends(get_current_user)
):
    """Get all activity for a specific user"""
    if current_user["role"] != "admin":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Admin only")
    
    query = {"user_id": user_id}
    if days:
        query["created_at"] = {"$gte": datetime.now(timezone.utc) - timedelta(days=days)}
    
    logs = await audit_logs_col.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    
    user = await users_col.find_one({"id": user_id}, {"_id": 0, "name": 1, "role": 1, "email": 1})
    
    for log in logs:
        if isinstance(log.get("created_at"), datetime):
            log["created_at"] = log["created_at"].isoformat()
    
    return {
        "user": user or {},
        "logs": logs,
        "total": len(logs)
    }


@router.get("/stats")
async def get_stats(days: int = Query(7), current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Admin only")
    
    since = datetime.now(timezone.utc) - timedelta(days=days)
    query = {"created_at": {"$gte": since}}
    
    total = await audit_logs_col.count_documents(query)
    
    pipeline = [
        {"$match": query},
        {"$group": {"_id": "$entity_type", "count": {"$sum": 1}}}
    ]
    by_type_cursor = audit_logs_col.aggregate(pipeline)
    by_type = {}
    async for item in by_type_cursor:
        by_type[item["_id"] or "other"] = item["count"]
    
    pipeline2 = [
        {"$match": query},
        {"$group": {"_id": "$action", "count": {"$sum": 1}}}
    ]
    by_action_cursor = audit_logs_col.aggregate(pipeline2)
    by_action = {}
    async for item in by_action_cursor:
        by_action[item["_id"] or "other"] = item["count"]
    
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
    
    pipeline4 = [
        {"$match": query},
        {"$group": {"_id": "$user_id", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    active_users_cursor = audit_logs_col.aggregate(pipeline4)
    active_users = []
    async for item in active_users_cursor:
        user = await users_col.find_one({"id": item["_id"]}, {"_id": 0, "name": 1, "role": 1})
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


@router.get("/email-logs")
async def get_email_logs(
    limit: int = Query(50),
    current_user: dict = Depends(get_current_user)
):
    """Get email notification logs (admin only)"""
    if current_user["role"] != "admin":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Admin only")
    
    from core.database import db
    email_logs_col = db["email_logs"]
    logs = await email_logs_col.find({}, {"_id": 0}).sort("sent_at", -1).to_list(limit)
    for log in logs:
        if isinstance(log.get("sent_at"), datetime):
            log["sent_at"] = log["sent_at"].isoformat()
    return logs
