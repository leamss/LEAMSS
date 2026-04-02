"""
Search Router for LEAMSS Portal (MySQL)
Global search across entities
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from typing import List, Optional
from core.database import get_db
from core.models import (
    User, UserRole, Sale, Case, Ticket, Product, Document
)
from core.auth import get_current_user, require_role

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("/global", response_model=dict)
async def global_search(
    q: str,
    limit: int = 10,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Global search across all entities
    Returns categorized results
    """
    if len(q) < 2:
        raise HTTPException(status_code=400, detail="Search query must be at least 2 characters")
    
    search_term = f"%{q}%"
    results = {
        "users": [],
        "cases": [],
        "sales": [],
        "tickets": [],
        "products": [],
        "total_count": 0
    }
    
    user_role = current_user["role"]
    user_id = current_user["id"]
    
    # Search Users (Admin only)
    if user_role == "admin":
        users_result = await db.execute(
            select(User)
            .where(
                or_(
                    User.name.ilike(search_term),
                    User.email.ilike(search_term)
                )
            )
            .limit(limit)
        )
        users = users_result.scalars().all()
        results["users"] = [
            {
                "id": u.id,
                "name": u.name,
                "email": u.email,
                "role": u.role.value,
                "type": "user"
            }
            for u in users
        ]
    
    # Search Cases
    cases_query = select(Case).where(
        or_(
            Case.case_id.ilike(search_term),
            Case.notes.ilike(search_term) if Case.notes else False
        )
    )
    
    # Role-based filtering
    if user_role == "client":
        cases_query = cases_query.where(Case.client_id == user_id)
    elif user_role == "case_manager":
        cases_query = cases_query.where(Case.case_manager_id == user_id)
    elif user_role == "partner":
        cases_query = cases_query.where(Case.partner_id == user_id)
    
    cases_result = await db.execute(cases_query.limit(limit))
    cases = cases_result.scalars().all()
    
    # Get client names for cases
    client_ids = set(c.client_id for c in cases)
    client_map = {}
    if client_ids:
        clients_result = await db.execute(
            select(User).where(User.id.in_(client_ids))
        )
        for client in clients_result.scalars().all():
            client_map[client.id] = client.name
    
    results["cases"] = [
        {
            "id": c.id,
            "case_id": c.case_id,
            "client_name": client_map.get(c.client_id, "Unknown"),
            "status": c.status.value if c.status else "unknown",
            "type": "case"
        }
        for c in cases
    ]
    
    # Search Sales (Admin and Partner)
    if user_role in ["admin", "partner"]:
        sales_query = select(Sale).where(
            or_(
                Sale.client_name.ilike(search_term),
                Sale.client_email.ilike(search_term)
            )
        )
        
        if user_role == "partner":
            sales_query = sales_query.where(Sale.partner_id == user_id)
        
        sales_result = await db.execute(sales_query.limit(limit))
        sales = sales_result.scalars().all()
        results["sales"] = [
            {
                "id": s.id,
                "client_name": s.client_name,
                "client_email": s.client_email,
                "status": s.status.value if s.status else "unknown",
                "fee_amount": s.fee_amount,
                "type": "sale"
            }
            for s in sales
        ]
    
    # Search Tickets
    tickets_query = select(Ticket).where(
        or_(
            Ticket.subject.ilike(search_term),
            Ticket.description.ilike(search_term)
        )
    )
    
    # Role-based filtering for tickets
    if user_role == "client":
        tickets_query = tickets_query.where(Ticket.created_by == user_id)
    elif user_role != "admin":
        tickets_query = tickets_query.where(
            or_(
                Ticket.created_by == user_id,
                Ticket.target_role == user_role
            )
        )
    
    tickets_result = await db.execute(tickets_query.limit(limit))
    tickets = tickets_result.scalars().all()
    results["tickets"] = [
        {
            "id": t.id,
            "subject": t.subject,
            "status": t.status.value if t.status else "unknown",
            "priority": t.priority.value if t.priority else "medium",
            "type": "ticket"
        }
        for t in tickets
    ]
    
    # Search Products (All users)
    products_result = await db.execute(
        select(Product)
        .where(
            or_(
                Product.name.ilike(search_term),
                Product.description.ilike(search_term)
            )
        )
        .where(Product.status == "active")
        .limit(limit)
    )
    products = products_result.scalars().all()
    results["products"] = [
        {
            "id": p.id,
            "name": p.name,
            "fee": p.fee,
            "type": "product"
        }
        for p in products
    ]
    
    # Calculate total count
    results["total_count"] = (
        len(results["users"]) +
        len(results["cases"]) +
        len(results["sales"]) +
        len(results["tickets"]) +
        len(results["products"])
    )
    
    return results


@router.get("/quick", response_model=List[dict])
async def quick_search(
    q: str,
    limit: int = 5,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Quick search for autocomplete/suggestions
    Returns flat list of results
    """
    if len(q) < 2:
        return []
    
    search_term = f"%{q}%"
    results = []
    user_role = current_user["role"]
    user_id = current_user["id"]
    
    # Search cases
    cases_query = select(Case).where(Case.case_id.ilike(search_term))
    if user_role == "client":
        cases_query = cases_query.where(Case.client_id == user_id)
    elif user_role == "case_manager":
        cases_query = cases_query.where(Case.case_manager_id == user_id)
    elif user_role == "partner":
        cases_query = cases_query.where(Case.partner_id == user_id)
    
    cases_result = await db.execute(cases_query.limit(limit))
    for case in cases_result.scalars().all():
        results.append({
            "id": case.id,
            "title": case.case_id,
            "subtitle": f"Case - {case.status.value}" if case.status else "Case",
            "type": "case",
            "url": f"/cases/{case.id}"
        })
    
    # Search tickets
    tickets_query = select(Ticket).where(Ticket.subject.ilike(search_term))
    if user_role == "client":
        tickets_query = tickets_query.where(Ticket.created_by == user_id)
    
    tickets_result = await db.execute(tickets_query.limit(limit))
    for ticket in tickets_result.scalars().all():
        results.append({
            "id": ticket.id,
            "title": ticket.subject,
            "subtitle": f"Ticket - {ticket.status.value}" if ticket.status else "Ticket",
            "type": "ticket",
            "url": f"/tickets/{ticket.id}"
        })
    
    # Search users (Admin only)
    if user_role == "admin":
        users_result = await db.execute(
            select(User)
            .where(or_(
                User.name.ilike(search_term),
                User.email.ilike(search_term)
            ))
            .limit(limit)
        )
        for user in users_result.scalars().all():
            results.append({
                "id": user.id,
                "title": user.name,
                "subtitle": f"{user.role.value} - {user.email}",
                "type": "user",
                "url": f"/users/{user.id}"
            })
    
    # Search products
    products_result = await db.execute(
        select(Product)
        .where(Product.name.ilike(search_term))
        .where(Product.status == "active")
        .limit(limit)
    )
    for product in products_result.scalars().all():
        results.append({
            "id": product.id,
            "title": product.name,
            "subtitle": f"Product - ₹{product.fee:,.0f}" if product.fee else "Product",
            "type": "product",
            "url": f"/products/{product.id}"
        })
    
    return results[:limit]
