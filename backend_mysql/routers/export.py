"""
Export Router for LEAMSS Portal (MySQL)
PDF and CSV report generation
"""
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional
from datetime import datetime, timedelta
from io import BytesIO, StringIO
import csv
from core.database import get_db
from core.models import (
    Sale, SaleStatus, User, Product, Case, CaseStatus,
    Ticket, TicketStatus, UserRole
)
from core.auth import get_current_user, require_role

router = APIRouter(prefix="/export", tags=["Export"])


def generate_html_report(title: str, headers: list, rows: list, summary: dict = None) -> str:
    """Generate HTML report that can be converted to PDF"""
    
    header_html = "".join(f"<th style='border: 1px solid #ddd; padding: 8px; background: #4f46e5; color: white;'>{h}</th>" for h in headers)
    
    rows_html = ""
    for row in rows:
        cells = "".join(f"<td style='border: 1px solid #ddd; padding: 8px;'>{cell}</td>" for cell in row)
        rows_html += f"<tr>{cells}</tr>"
    
    summary_html = ""
    if summary:
        summary_items = "".join(f"<p><strong>{k}:</strong> {v}</p>" for k, v in summary.items())
        summary_html = f"""
        <div style="margin-top: 20px; padding: 15px; background: #f3f4f6; border-radius: 8px;">
            <h3>Summary</h3>
            {summary_items}
        </div>
        """
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>{title}</title>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 20px; }}
            h1 {{ color: #4f46e5; }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
            th, td {{ text-align: left; }}
            tr:nth-child(even) {{ background: #f9fafb; }}
            .header {{ display: flex; justify-content: space-between; align-items: center; }}
            .date {{ color: #6b7280; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>{title}</h1>
            <p class="date">Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
        </div>
        <table>
            <thead><tr>{header_html}</tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
        {summary_html}
        <p style="margin-top: 30px; color: #6b7280; font-size: 12px;">
            LEAMSS Immigration Portal - Confidential Report
        </p>
    </body>
    </html>
    """


@router.get("/sales/csv")
async def export_sales_csv(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[str] = None,
    current_user: dict = Depends(require_role([UserRole.admin, UserRole.partner])),
    db: AsyncSession = Depends(get_db)
):
    """Export sales report as CSV"""
    query = select(Sale).order_by(Sale.created_at.desc())
    
    filters = []
    if current_user["role"] == "partner":
        filters.append(Sale.partner_id == current_user["id"])
    if status:
        filters.append(Sale.status == SaleStatus(status))
    if start_date:
        filters.append(Sale.created_at >= datetime.fromisoformat(start_date))
    if end_date:
        filters.append(Sale.created_at <= datetime.fromisoformat(end_date))
    
    if filters:
        query = query.where(and_(*filters))
    
    result = await db.execute(query)
    sales = result.scalars().all()
    
    # Get related data
    partner_ids = set(s.partner_id for s in sales)
    product_ids = set(s.product_id for s in sales)
    
    partners = {}
    if partner_ids:
        p_result = await db.execute(select(User).where(User.id.in_(partner_ids)))
        for p in p_result.scalars().all():
            partners[p.id] = p.name
    
    products = {}
    if product_ids:
        pr_result = await db.execute(select(Product).where(Product.id.in_(product_ids)))
        for pr in pr_result.scalars().all():
            products[pr.id] = pr.name
    
    # Generate CSV
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Client Name", "Client Email", "Product", "Partner", "Fee", "Commission", "Status"])
    
    for sale in sales:
        writer.writerow([
            sale.created_at.strftime('%Y-%m-%d') if sale.created_at else "",
            sale.client_name,
            sale.client_email,
            products.get(sale.product_id, ""),
            partners.get(sale.partner_id, ""),
            f"{sale.fee_amount:.2f}",
            f"{sale.commission_amount:.2f}" if sale.commission_amount else "0.00",
            sale.status.value if sale.status else ""
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=sales_report_{datetime.utcnow().strftime('%Y%m%d')}.csv"}
    )


@router.get("/sales/html")
async def export_sales_html(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[str] = None,
    current_user: dict = Depends(require_role([UserRole.admin, UserRole.partner])),
    db: AsyncSession = Depends(get_db)
):
    """Export sales report as HTML (printable/PDF)"""
    query = select(Sale).order_by(Sale.created_at.desc())
    
    filters = []
    if current_user["role"] == "partner":
        filters.append(Sale.partner_id == current_user["id"])
    if status:
        filters.append(Sale.status == SaleStatus(status))
    if start_date:
        filters.append(Sale.created_at >= datetime.fromisoformat(start_date))
    if end_date:
        filters.append(Sale.created_at <= datetime.fromisoformat(end_date))
    
    if filters:
        query = query.where(and_(*filters))
    
    result = await db.execute(query)
    sales = result.scalars().all()
    
    # Get related data
    partner_ids = set(s.partner_id for s in sales)
    product_ids = set(s.product_id for s in sales)
    
    partners = {}
    if partner_ids:
        p_result = await db.execute(select(User).where(User.id.in_(partner_ids)))
        for p in p_result.scalars().all():
            partners[p.id] = p.name
    
    products = {}
    if product_ids:
        pr_result = await db.execute(select(Product).where(Product.id.in_(product_ids)))
        for pr in pr_result.scalars().all():
            products[pr.id] = pr.name
    
    headers = ["Date", "Client", "Product", "Partner", "Fee (₹)", "Commission (₹)", "Status"]
    rows = []
    total_fee = 0
    total_commission = 0
    
    for sale in sales:
        rows.append([
            sale.created_at.strftime('%Y-%m-%d') if sale.created_at else "",
            sale.client_name,
            products.get(sale.product_id, ""),
            partners.get(sale.partner_id, ""),
            f"{sale.fee_amount:,.2f}",
            f"{sale.commission_amount:,.2f}" if sale.commission_amount else "0.00",
            sale.status.value.upper() if sale.status else ""
        ])
        total_fee += sale.fee_amount or 0
        total_commission += sale.commission_amount or 0
    
    summary = {
        "Total Sales": len(sales),
        "Total Fee": f"₹{total_fee:,.2f}",
        "Total Commission": f"₹{total_commission:,.2f}"
    }
    
    html = generate_html_report("Sales Report", headers, rows, summary)
    return Response(content=html, media_type="text/html")


@router.get("/cases/csv")
async def export_cases_csv(
    status: Optional[str] = None,
    current_user: dict = Depends(require_role([UserRole.admin, UserRole.case_manager])),
    db: AsyncSession = Depends(get_db)
):
    """Export cases report as CSV"""
    query = select(Case).order_by(Case.created_at.desc())
    
    filters = []
    if current_user["role"] == "case_manager":
        filters.append(Case.case_manager_id == current_user["id"])
    if status:
        filters.append(Case.status == CaseStatus(status))
    
    if filters:
        query = query.where(and_(*filters))
    
    result = await db.execute(query)
    cases = result.scalars().all()
    
    # Get related data
    client_ids = set(c.client_id for c in cases)
    product_ids = set(c.product_id for c in cases)
    manager_ids = set(c.case_manager_id for c in cases if c.case_manager_id)
    
    clients = {}
    managers = {}
    user_ids = client_ids | manager_ids
    if user_ids:
        u_result = await db.execute(select(User).where(User.id.in_(user_ids)))
        for u in u_result.scalars().all():
            if u.id in client_ids:
                clients[u.id] = u.name
            if u.id in manager_ids:
                managers[u.id] = u.name
    
    products = {}
    if product_ids:
        pr_result = await db.execute(select(Product).where(Product.id.in_(product_ids)))
        for pr in pr_result.scalars().all():
            products[pr.id] = pr.name
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Case ID", "Client", "Product", "Case Manager", "Status", "Current Step", "Created"])
    
    for case in cases:
        writer.writerow([
            case.case_id,
            clients.get(case.client_id, ""),
            products.get(case.product_id, ""),
            managers.get(case.case_manager_id, "Unassigned"),
            case.status.value if case.status else "",
            case.current_step or "",
            case.created_at.strftime('%Y-%m-%d') if case.created_at else ""
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=cases_report_{datetime.utcnow().strftime('%Y%m%d')}.csv"}
    )


@router.get("/cases/html")
async def export_cases_html(
    status: Optional[str] = None,
    current_user: dict = Depends(require_role([UserRole.admin, UserRole.case_manager])),
    db: AsyncSession = Depends(get_db)
):
    """Export cases report as HTML"""
    query = select(Case).order_by(Case.created_at.desc())
    
    filters = []
    if current_user["role"] == "case_manager":
        filters.append(Case.case_manager_id == current_user["id"])
    if status:
        filters.append(Case.status == CaseStatus(status))
    
    if filters:
        query = query.where(and_(*filters))
    
    result = await db.execute(query)
    cases = result.scalars().all()
    
    # Get related data
    client_ids = set(c.client_id for c in cases)
    product_ids = set(c.product_id for c in cases)
    manager_ids = set(c.case_manager_id for c in cases if c.case_manager_id)
    
    clients = {}
    managers = {}
    user_ids = client_ids | manager_ids
    if user_ids:
        u_result = await db.execute(select(User).where(User.id.in_(user_ids)))
        for u in u_result.scalars().all():
            if u.id in client_ids:
                clients[u.id] = u.name
            if u.id in manager_ids:
                managers[u.id] = u.name
    
    products = {}
    if product_ids:
        pr_result = await db.execute(select(Product).where(Product.id.in_(product_ids)))
        for pr in pr_result.scalars().all():
            products[pr.id] = pr.name
    
    headers = ["Case ID", "Client", "Product", "Case Manager", "Status", "Current Step"]
    rows = []
    status_counts = {}
    
    for case in cases:
        status_val = case.status.value if case.status else "unknown"
        status_counts[status_val] = status_counts.get(status_val, 0) + 1
        rows.append([
            case.case_id,
            clients.get(case.client_id, ""),
            products.get(case.product_id, ""),
            managers.get(case.case_manager_id, "Unassigned"),
            status_val.upper(),
            case.current_step or ""
        ])
    
    summary = {"Total Cases": len(cases)}
    summary.update({f"{k.title()} Cases": v for k, v in status_counts.items()})
    
    html = generate_html_report("Cases Report", headers, rows, summary)
    return Response(content=html, media_type="text/html")


@router.get("/commission/csv")
async def export_commission_csv(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(require_role([UserRole.admin, UserRole.partner])),
    db: AsyncSession = Depends(get_db)
):
    """Export commission report as CSV"""
    query = select(Sale).where(Sale.status == SaleStatus.approved)
    
    filters = []
    if current_user["role"] == "partner":
        filters.append(Sale.partner_id == current_user["id"])
    if start_date:
        filters.append(Sale.approved_at >= datetime.fromisoformat(start_date))
    if end_date:
        filters.append(Sale.approved_at <= datetime.fromisoformat(end_date))
    
    if filters:
        query = query.where(and_(*filters))
    
    result = await db.execute(query.order_by(Sale.approved_at.desc()))
    sales = result.scalars().all()
    
    # Get partner names
    partner_ids = set(s.partner_id for s in sales)
    partners = {}
    if partner_ids:
        p_result = await db.execute(select(User).where(User.id.in_(partner_ids)))
        for p in p_result.scalars().all():
            partners[p.id] = p.name
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Approval Date", "Partner", "Client", "Fee Amount", "Commission Rate", "Commission Amount"])
    
    for sale in sales:
        rate = (sale.commission_amount / sale.fee_amount * 100) if sale.fee_amount else 0
        writer.writerow([
            sale.approved_at.strftime('%Y-%m-%d') if sale.approved_at else "",
            partners.get(sale.partner_id, ""),
            sale.client_name,
            f"{sale.fee_amount:.2f}",
            f"{rate:.1f}%",
            f"{sale.commission_amount:.2f}" if sale.commission_amount else "0.00"
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=commission_report_{datetime.utcnow().strftime('%Y%m%d')}.csv"}
    )


@router.get("/tickets/csv")
async def export_tickets_csv(
    status: Optional[str] = None,
    current_user: dict = Depends(require_role([UserRole.admin, UserRole.case_manager])),
    db: AsyncSession = Depends(get_db)
):
    """Export tickets report as CSV"""
    query = select(Ticket).order_by(Ticket.created_at.desc())
    
    if status:
        query = query.where(Ticket.status == TicketStatus(status))
    
    result = await db.execute(query)
    tickets = result.scalars().all()
    
    # Get user names
    user_ids = set(t.created_by for t in tickets)
    users = {}
    if user_ids:
        u_result = await db.execute(select(User).where(User.id.in_(user_ids)))
        for u in u_result.scalars().all():
            users[u.id] = u.name
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Subject", "Created By", "Category", "Priority", "Status", "Created"])
    
    for ticket in tickets:
        writer.writerow([
            ticket.id[:8],
            ticket.subject,
            users.get(ticket.created_by, ""),
            ticket.category.value if ticket.category else "",
            ticket.priority.value if ticket.priority else "",
            ticket.status.value if ticket.status else "",
            ticket.created_at.strftime('%Y-%m-%d') if ticket.created_at else ""
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=tickets_report_{datetime.utcnow().strftime('%Y%m%d')}.csv"}
    )
