"""Stats Router"""
from fastapi import APIRouter, Depends
from core.database import sales_col, cases_col, tickets_col, users_col, documents_col
from core.auth import get_current_user
from datetime import datetime

router = APIRouter(prefix="/stats", tags=["Stats"])


@router.get("/dashboard")
async def dashboard(current_user: dict = Depends(get_current_user)):
    """Alias for admin-dashboard - used by frontend"""
    pending_sales = await sales_col.count_documents({"status": "pending"})
    active_cases = await cases_col.count_documents({"status": "active"})
    open_tickets = await tickets_col.count_documents({"status": "open"})
    total_users = await users_col.count_documents({})
    
    approved = await sales_col.find({"status": "approved"}, {"_id": 0}).to_list(1000)
    revenue = sum(s["fee_amount"] for s in approved)
    commission = sum(s.get("commission_amount", 0) for s in approved)
    
    return {
        "pending_sales": pending_sales, "active_cases": active_cases,
        "open_tickets": open_tickets, "total_users": total_users,
        "total_revenue": revenue, "total_commission": commission
    }


@router.get("/admin-dashboard")
async def admin_dashboard(current_user: dict = Depends(get_current_user)):
    pending_sales = await sales_col.count_documents({"status": "pending"})
    active_cases = await cases_col.count_documents({"status": "active"})
    open_tickets = await tickets_col.count_documents({"status": "open"})
    total_users = await users_col.count_documents({})
    
    approved = await sales_col.find({"status": "approved"}, {"_id": 0}).to_list(1000)
    revenue = sum(s["fee_amount"] for s in approved)
    commission = sum(s.get("commission_amount", 0) for s in approved)
    
    return {
        "pending_sales": pending_sales, "active_cases": active_cases,
        "open_tickets": open_tickets, "total_users": total_users,
        "total_revenue": revenue, "total_commission": commission
    }


@router.get("/case-manager-dashboard")
async def case_manager_dashboard(current_user: dict = Depends(get_current_user)):
    query = {"case_manager_id": current_user["id"]}
    total = await cases_col.count_documents(query)
    active = await cases_col.count_documents({**query, "status": "active"})
    completed = await cases_col.count_documents({**query, "status": "completed"})
    
    pending_docs = await documents_col.count_documents({"status": "pending"})
    
    return {
        "total_cases": total, "my_cases": total,
        "active_cases": active, "completed_cases": completed,
        "pending_reviews": pending_docs
    }


@router.get("/partner-dashboard")
async def partner_dashboard(current_user: dict = Depends(get_current_user)):
    query = {"partner_id": current_user["id"]}
    total = await sales_col.count_documents(query)
    approved = await sales_col.count_documents({**query, "status": "approved"})
    pending = await sales_col.count_documents({**query, "status": "pending"})
    
    approved_sales = await sales_col.find({**query, "status": "approved"}, {"_id": 0}).to_list(1000)
    commission = sum(s.get("commission_amount", 0) for s in approved_sales)
    
    return {
        "total_sales": total, "approved_sales": approved,
        "pending_sales": pending, "total_commission": commission
    }


@router.get("/client-dashboard")
async def client_dashboard(current_user: dict = Depends(get_current_user)):
    total = await cases_col.count_documents({"client_id": current_user["id"]})
    active = await cases_col.count_documents({"client_id": current_user["id"], "status": "active"})
    pending_docs = await documents_col.count_documents({"uploaded_by": current_user["id"], "status": "pending"})
    
    return {
        "total_cases": total, "active_cases": active,
        "pending_documents": pending_docs
    }
