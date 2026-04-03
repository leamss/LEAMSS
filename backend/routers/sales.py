"""Sales Router"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from typing import List, Optional
from core.database import (
    sales_col, sale_documents_col, users_col, products_col,
    cases_col, case_steps_col, workflow_steps_col, notifications_col, audit_logs_col
)
from core.auth import get_current_user, get_password_hash
from pydantic import BaseModel
import uuid, os, shutil
from datetime import datetime, timezone

router = APIRouter(prefix="/sales", tags=["Sales"])

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "./uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


class SaleApproval(BaseModel):
    sale_id: str
    status: str
    case_manager_id: Optional[str] = None
    notes: Optional[str] = ""


async def _log(user_id, action, entity_type, entity_id=None, details=None):
    await audit_logs_col.insert_one({
        "id": str(uuid.uuid4()), "user_id": user_id, "action": action,
        "entity_type": entity_type, "entity_id": entity_id,
        "new_value": details, "created_at": datetime.now(timezone.utc)
    })


def _serialize_sale(sale):
    s = {k: v for k, v in sale.items() if k != "_id"}
    for f in ["created_at", "approved_at"]:
        if isinstance(s.get(f), datetime):
            s[f] = s[f].isoformat()
    return s


@router.get("")
async def get_sales(status: str = None, current_user: dict = Depends(get_current_user)):
    query = {}
    if status:
        query["status"] = status
    
    if current_user["role"] == "partner":
        query["partner_id"] = current_user["id"]
    elif current_user["role"] == "client":
        query["client_email"] = current_user["email"]
    
    sales = await sales_col.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    
    for sale in sales:
        partner = await users_col.find_one({"id": sale.get("partner_id")}, {"_id": 0, "password": 0})
        product = await products_col.find_one({"id": sale.get("product_id")}, {"_id": 0})
        sale["partner_name"] = partner["name"] if partner else "N/A"
        sale["product_name"] = product["name"] if product else "N/A"
        for f in ["created_at", "approved_at"]:
            if isinstance(sale.get(f), datetime):
                sale[f] = sale[f].isoformat()
    
    return sales


@router.get("/pending")
async def get_pending_sales(current_user: dict = Depends(get_current_user)):
    """Get pending sales - alias for frontend compatibility"""
    query = {"status": "pending"}
    
    if current_user["role"] == "partner":
        query["partner_id"] = current_user["id"]
    
    sales = await sales_col.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    
    for sale in sales:
        partner = await users_col.find_one({"id": sale.get("partner_id")}, {"_id": 0, "password": 0})
        product = await products_col.find_one({"id": sale.get("product_id")}, {"_id": 0})
        sale["partner_name"] = partner["name"] if partner else "N/A"
        sale["product_name"] = product["name"] if product else "N/A"
        for f in ["created_at", "approved_at"]:
            if isinstance(sale.get(f), datetime):
                sale[f] = sale[f].isoformat()
    
    return sales


@router.get("/my-sales")
async def get_my_sales(current_user: dict = Depends(get_current_user)):
    """Get sales for current partner"""
    query = {"partner_id": current_user["id"]}
    
    sales = await sales_col.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    
    for sale in sales:
        partner = await users_col.find_one({"id": sale.get("partner_id")}, {"_id": 0, "password": 0})
        product = await products_col.find_one({"id": sale.get("product_id")}, {"_id": 0})
        sale["partner_name"] = partner["name"] if partner else "N/A"
        sale["product_name"] = product["name"] if product else "N/A"
        for f in ["created_at", "approved_at"]:
            if isinstance(sale.get(f), datetime):
                sale[f] = sale[f].isoformat()
    
    return sales


@router.post("")
async def create_sale(
    client_name: str = Form(...),
    client_email: str = Form(...),
    client_mobile: str = Form(...),
    product_id: str = Form(...),
    fee_amount: float = Form(...),
    amount_received: float = Form(0),
    payment_method: str = Form("cash"),
    payment_reference: str = Form(""),
    commission_rate: Optional[float] = Form(None),
    agreement_signed: bool = Form(True),
    documents: List[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user)
):
    product = await products_col.find_one({"id": product_id}, {"_id": 0})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    rate = commission_rate if commission_rate is not None else current_user.get("commission_rate", 0)
    
    sale = {
        "id": str(uuid.uuid4()), "partner_id": current_user["id"],
        "client_name": client_name, "client_email": client_email,
        "client_mobile": client_mobile, "product_id": product_id,
        "fee_amount": fee_amount, "amount_received": amount_received,
        "payment_method": payment_method, "payment_reference": payment_reference,
        "commission_rate": rate,
        "commission_amount": fee_amount * (rate / 100) if rate else 0,
        "agreement_signed": agreement_signed, "status": "pending",
        "payment_status": "pending",
        "created_at": datetime.now(timezone.utc)
    }
    await sales_col.insert_one(sale)
    
    if documents:
        for doc_file in documents:
            if doc_file and doc_file.filename:
                file_id = str(uuid.uuid4())
                file_ext = os.path.splitext(doc_file.filename)[1]
                file_path = os.path.join(UPLOAD_DIR, f"{file_id}{file_ext}")
                
                with open(file_path, "wb") as f:
                    content = await doc_file.read()
                    f.write(content)
                
                doc_record = {
                    "id": file_id, "sale_id": sale["id"],
                    "filename": doc_file.filename, "file_path": file_path,
                    "file_size": len(content), "content_type": doc_file.content_type,
                    "uploaded_at": datetime.now(timezone.utc)
                }
                await sale_documents_col.insert_one(doc_record)
    
    await _log(current_user["id"], "create_sale", "sale", sale["id"], {"client_name": client_name, "fee_amount": fee_amount})
    
    return {"id": sale["id"], "message": "Sale created successfully"}


@router.get("/{sale_id}/documents")
async def get_sale_documents(sale_id: str, current_user: dict = Depends(get_current_user)):
    docs = await sale_documents_col.find({"sale_id": sale_id}, {"_id": 0}).to_list(100)
    for d in docs:
        if isinstance(d.get("uploaded_at"), datetime):
            d["uploaded_at"] = d["uploaded_at"].isoformat()
    return docs


@router.post("/approve")
async def approve_sale(request: SaleApproval, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    sale = await sales_col.find_one({"id": request.sale_id}, {"_id": 0})
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    
    if request.status == "approved":
        rate = sale.get("commission_rate", 0) or 0
        commission = sale["fee_amount"] * (rate / 100)
        
        await sales_col.update_one({"id": request.sale_id}, {"$set": {
            "status": "approved", "approved_by": current_user["id"],
            "approved_at": datetime.now(timezone.utc),
            "commission_amount": commission
        }})
        
        # Create or get client
        client = await users_col.find_one({"email": sale["client_email"]}, {"_id": 0})
        client_password = "Client@123"
        client_is_new = False
        
        if not client:
            client_is_new = True
            client = {
                "id": str(uuid.uuid4()), "email": sale["client_email"],
                "password": get_password_hash(client_password),
                "name": sale["client_name"], "role": "client",
                "mobile": sale.get("client_mobile", ""), "status": "active",
                "commission_rate": 0.0, "created_at": datetime.now(timezone.utc)
            }
            await users_col.insert_one(client)
        
        # Create case
        product = await products_col.find_one({"id": sale["product_id"]}, {"_id": 0})
        steps = await workflow_steps_col.find({"product_id": sale["product_id"]}, {"_id": 0}).sort("step_order", 1).to_list(100)
        first_step = steps[0]["step_name"] if steps else "Registration"
        
        case_number = f"CASE-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:4].upper()}"
        case = {
            "id": str(uuid.uuid4()), "case_id": case_number,
            "sale_id": sale["id"], "client_id": client["id"],
            "product_id": sale["product_id"],
            "case_manager_id": request.case_manager_id,
            "partner_id": sale["partner_id"],
            "status": "active", "current_step": first_step,
            "current_step_order": 1,
            "created_at": datetime.now(timezone.utc)
        }
        await cases_col.insert_one(case)
        
        # Create case steps
        for step in steps:
            case_step = {
                "id": str(uuid.uuid4()), "case_id": case["id"],
                "step_name": step["step_name"], "step_order": step["step_order"],
                "status": "pending", "description": step.get("description", ""),
                "required_documents": step.get("required_documents", []),
                "created_at": datetime.now(timezone.utc)
            }
            await case_steps_col.insert_one(case_step)
        
        # Notify
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()), "user_id": client["id"],
            "title": "Case Created", "message": f"Your case {case_number} has been created",
            "type": "case_created", "related_id": case["id"],
            "read": False, "created_at": datetime.now(timezone.utc)
        })
        
        await _log(current_user["id"], "sale_approved", "sale", request.sale_id, {"client_name": sale["client_name"]})
        
        response = {"message": "Sale approved successfully"}
        if client_is_new:
            response["client_credentials"] = {
                "email": sale["client_email"], "password": client_password,
                "name": sale["client_name"],
                "message": "New client account created. Share these login credentials with the client."
            }
        return response
    
    elif request.status == "rejected":
        await sales_col.update_one({"id": request.sale_id}, {"$set": {"status": "rejected", "rejection_notes": request.notes}})
        await _log(current_user["id"], "sale_rejected", "sale", request.sale_id, {"client_name": sale["client_name"]})
        return {"message": "Sale rejected"}
    
    raise HTTPException(status_code=400, detail="Invalid status")


@router.get("/partner-report")
async def get_partner_report(partner_id: str = None, period: str = "lifetime", current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    query = {}
    if partner_id:
        query["partner_id"] = partner_id
    
    sales = await sales_col.find(query, {"_id": 0}).to_list(1000)
    
    total = len(sales)
    approved = [s for s in sales if s.get("status") == "approved"]
    revenue = sum(s["fee_amount"] for s in approved)
    commission = sum(s.get("commission_amount", 0) for s in approved)
    
    sales_data = []
    for s in sales:
        partner = await users_col.find_one({"id": s.get("partner_id")}, {"_id": 0, "password": 0})
        product = await products_col.find_one({"id": s.get("product_id")}, {"_id": 0})
        sd = {
            "id": s["id"], "client_name": s["client_name"], "client_email": s["client_email"],
            "partner_name": partner["name"] if partner else "N/A",
            "product_name": product["name"] if product else "N/A",
            "fee_amount": s["fee_amount"], "commission_amount": s.get("commission_amount", 0),
            "commission_rate": s.get("commission_rate", 0), "status": s["status"],
            "payment_method": s.get("payment_method", ""), "payment_reference": s.get("payment_reference", ""),
            "date": s.get("created_at", "").isoformat() if isinstance(s.get("created_at"), datetime) else str(s.get("created_at", ""))
        }
        sales_data.append(sd)
    
    return {
        "total_sales": total, "approved_sales": len(approved),
        "total_revenue": revenue, "total_commission": commission,
        "sales": sales_data, "partner_breakdown": []
    }


@router.get("/stats")
async def get_sales_stats(current_user: dict = Depends(get_current_user)):
    total = await sales_col.count_documents({})
    pending = await sales_col.count_documents({"status": "pending"})
    approved = await sales_col.count_documents({"status": "approved"})
    
    approved_sales = await sales_col.find({"status": "approved"}, {"_id": 0}).to_list(1000)
    revenue = sum(s["fee_amount"] for s in approved_sales)
    commission = sum(s.get("commission_amount", 0) for s in approved_sales)
    
    return {
        "total_sales": total, "pending_sales": pending,
        "approved_sales": approved, "total_revenue": revenue,
        "total_commission": commission
    }
