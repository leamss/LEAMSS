"""
Reports and analytics routes for LEAMSS Portal
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from datetime import datetime, timezone
from typing import Optional
import io
import csv

from core.database import db
from core.auth import get_current_user, require_role, UserRole
from services.commission_service import get_applicable_commission

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/sales")
async def get_sales_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[str] = None,
    partner_id: Optional[str] = None,
    product_id: Optional[str] = None,
    format: Optional[str] = "json",
    user: dict = Depends(require_role([UserRole.ADMIN]))
):
    """Get sales report with optional filters"""
    query = {}
    
    if start_date:
        query["created_at"] = {"$gte": start_date}
    if end_date:
        if "created_at" in query:
            query["created_at"]["$lte"] = end_date
        else:
            query["created_at"] = {"$lte": end_date}
    if status:
        query["status"] = status
    if partner_id:
        query["partner_id"] = partner_id
    if product_id:
        query["product_id"] = product_id
    
    sales = await db.sales.find(query, {"_id": 0}).sort("created_at", -1).to_list(10000)
    
    # Calculate totals
    total_fee = sum(s.get("fee_amount", 0) for s in sales)
    total_received = sum(s.get("amount_received", 0) for s in sales)
    total_commission = sum(s.get("commission_amount", 0) for s in sales)
    
    if format == "csv":
        # Generate CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "Date", "Partner", "Client", "Product", "Fee Amount", 
            "Amount Received", "Commission", "Status"
        ])
        
        # Data rows
        for sale in sales:
            writer.writerow([
                sale.get("created_at", "")[:10],
                sale.get("partner_name", ""),
                sale.get("client_name", ""),
                sale.get("product_name", ""),
                sale.get("fee_amount", 0),
                sale.get("amount_received", 0),
                sale.get("commission_amount", 0),
                sale.get("status", "")
            ])
        
        # Totals row
        writer.writerow([])
        writer.writerow(["TOTALS", "", "", "", total_fee, total_received, total_commission, ""])
        
        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=sales_report_{datetime.now().strftime('%Y%m%d')}.csv"}
        )
    
    return {
        "sales": sales,
        "summary": {
            "total_sales": len(sales),
            "total_fee": total_fee,
            "total_received": total_received,
            "total_commission": total_commission
        }
    }


@router.get("/partner-commissions")
async def get_partner_commissions(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user: dict = Depends(require_role([UserRole.ADMIN]))
):
    """Get commission report by partner"""
    query = {"status": "approved"}
    
    if start_date:
        query["created_at"] = {"$gte": start_date}
    if end_date:
        if "created_at" in query:
            query["created_at"]["$lte"] = end_date
        else:
            query["created_at"] = {"$lte": end_date}
    
    # Aggregate by partner
    pipeline = [
        {"$match": query},
        {"$group": {
            "_id": "$partner_id",
            "partner_name": {"$first": "$partner_name"},
            "total_sales": {"$sum": 1},
            "total_fee": {"$sum": "$fee_amount"},
            "total_commission": {"$sum": "$commission_amount"}
        }},
        {"$sort": {"total_commission": -1}}
    ]
    
    results = await db.sales.aggregate(pipeline).to_list(1000)
    
    return {
        "commissions": results,
        "grand_total": sum(r.get("total_commission", 0) for r in results)
    }
