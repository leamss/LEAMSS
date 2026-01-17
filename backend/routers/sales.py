"""
Sales management routes for LEAMSS Portal
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from datetime import datetime, timezone
from typing import List, Optional
from bson import ObjectId
import io

from core.database import db, fs
from core.auth import get_current_user, require_role, UserRole, pwd_context, create_access_token
from core.models import SaleCreate, SaleResponse, SaleApproval
from services.notification_service import create_notification
from services.commission_service import get_applicable_commission

router = APIRouter(prefix="/sales", tags=["Sales"])


@router.get("", response_model=List[SaleResponse])
async def get_sales(user: dict = Depends(get_current_user)):
    """Get sales based on user role"""
    if user["role"] == UserRole.ADMIN:
        sales = await db.sales.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    elif user["role"] == UserRole.PARTNER:
        sales = await db.sales.find({"partner_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    else:
        sales = []
    return [SaleResponse(**s) for s in sales]


@router.post("", response_model=SaleResponse)
async def create_sale(
    client_name: str = Form(...),
    client_email: str = Form(...),
    client_mobile: str = Form(...),
    product_id: str = Form(...),
    fee_amount: float = Form(...),
    amount_received: float = Form(...),
    payment_method: str = Form(...),
    payment_reference: str = Form(...),
    agreement_signed: bool = Form(...),
    documents: List[UploadFile] = File(default=[]),
    user: dict = Depends(require_role([UserRole.PARTNER]))
):
    """Create a new sale (Partner only)"""
    product = await db.products.find_one({"id": product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get applicable commission for sale date (today)
    today_str = datetime.now(timezone.utc).isoformat()
    comm_rate, comm_type, comm_tiers = get_applicable_commission(product, today_str)
    
    # Calculate commission
    if comm_type == "tiered":
        commission_amount = 0
        for tier in comm_tiers:
            if fee_amount >= tier.get("min_amount", 0):
                if "max_amount" not in tier or fee_amount <= tier.get("max_amount", float('inf')):
                    commission_amount = fee_amount * (tier.get("rate", 0) / 100)
                    break
    else:
        commission_amount = fee_amount * (comm_rate / 100)
    
    # Upload documents
    doc_ids = []
    for doc in documents:
        content = await doc.read()
        file_id = await fs.upload_from_stream(
            doc.filename,
            io.BytesIO(content),
            metadata={"content_type": doc.content_type}
        )
        doc_ids.append({
            "file_id": str(file_id),
            "filename": doc.filename,
            "content_type": doc.content_type
        })
    
    sale_doc = {
        "id": str(ObjectId()),
        "partner_id": user["id"],
        "partner_name": user["name"],
        "client_name": client_name,
        "client_email": client_email,
        "client_mobile": client_mobile,
        "product_id": product_id,
        "product_name": product["name"],
        "fee_amount": fee_amount,
        "amount_received": amount_received,
        "payment_method": payment_method,
        "payment_reference": payment_reference,
        "agreement_signed": agreement_signed,
        "status": "pending",
        "commission_rate": comm_rate,
        "commission_type": comm_type,
        "commission_amount": commission_amount,
        "documents": doc_ids,
        "created_at": today_str
    }
    
    await db.sales.insert_one(sale_doc)
    
    # Notify admins
    admins = await db.users.find({"role": UserRole.ADMIN}).to_list(100)
    for admin in admins:
        await create_notification(
            admin["id"],
            "New Sale Submitted",
            f"Partner {user['name']} submitted a new sale for {client_name}",
            "sale_submitted",
            sale_doc["id"]
        )
    
    return SaleResponse(**sale_doc)


@router.get("/pending", response_model=List[SaleResponse])
async def get_pending_sales(user: dict = Depends(require_role([UserRole.ADMIN]))):
    """Get pending sales for approval (Admin only)"""
    sales = await db.sales.find({"status": "pending"}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return [SaleResponse(**s) for s in sales]


@router.post("/approve")
async def approve_sale(
    approval: SaleApproval, 
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_role([UserRole.ADMIN]))
):
    """Approve or reject a sale (Admin only)"""
    sale = await db.sales.find_one({"id": approval.sale_id})
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    
    await db.sales.update_one(
        {"id": approval.sale_id},
        {"$set": {"status": approval.status}}
    )
    
    # Notify partner
    await create_notification(
        sale["partner_id"],
        f"Sale {approval.status.title()}",
        f"Your sale for {sale['client_name']} has been {approval.status}",
        f"sale_{approval.status}",
        approval.sale_id
    )
    
    if approval.status == "approved" and approval.case_manager_id:
        # Create client user if not exists
        existing_client = await db.users.find_one({"email": sale["client_email"]})
        if not existing_client:
            client_password = f"Client@{ObjectId().binary.hex()[:6]}"
            client_doc = {
                "id": str(ObjectId()),
                "email": sale["client_email"],
                "name": sale["client_name"],
                "mobile": sale["client_mobile"],
                "role": UserRole.CLIENT,
                "password_hash": pwd_context.hash(client_password),
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.users.insert_one(client_doc)
            client_id = client_doc["id"]
            
            # Import email service here to avoid circular imports
            from email_service import email_service
            background_tasks.add_task(
                email_service.send_welcome_email,
                sale["client_email"],
                sale["client_name"],
                client_password
            )
        else:
            client_id = existing_client["id"]
        
        # Get product and case manager
        product = await db.products.find_one({"id": sale["product_id"]})
        case_manager = await db.users.find_one({"id": approval.case_manager_id})
        
        if not product or not case_manager:
            raise HTTPException(status_code=400, detail="Product or case manager not found")
        
        # Create case with workflow steps
        steps = []
        for ws in product.get("workflow_steps", []):
            steps.append({
                "step_name": ws["step_name"],
                "step_order": ws["step_order"],
                "description": ws.get("description"),
                "duration_days": ws.get("duration_days"),
                "status": "pending",
                "notes": "",
                "uploaded_documents": [],
                "required_documents": ws.get("required_documents", []),
                "is_locked": ws["step_order"] != 1
            })
        
        case_doc = {
            "id": str(ObjectId()),
            "case_id": f"CASE-{ObjectId().binary.hex()[:8].upper()}",
            "sale_id": approval.sale_id,
            "client_id": client_id,
            "client_name": sale["client_name"],
            "client_email": sale["client_email"],
            "product_id": sale["product_id"],
            "product_name": sale["product_name"],
            "case_manager_id": approval.case_manager_id,
            "case_manager_name": case_manager["name"],
            "partner_id": sale["partner_id"],
            "partner_name": sale["partner_name"],
            "status": "active",
            "current_step": steps[0]["step_name"] if steps else "No steps defined",
            "current_step_order": 1,
            "steps": steps,
            "additional_doc_requests": [],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.cases.insert_one(case_doc)
        
        # Notify case manager
        await create_notification(
            approval.case_manager_id,
            "New Case Assigned",
            f"You have been assigned case {case_doc['case_id']} for {sale['client_name']}",
            "case_assigned",
            case_doc["id"]
        )
        
        # Notify client
        await create_notification(
            client_id,
            "Welcome to LEAMSS Portal",
            f"Your case {case_doc['case_id']} has been created. Please login to upload required documents.",
            "case_created",
            case_doc["id"]
        )
    
    return {"message": f"Sale {approval.status}"}


@router.get("/{sale_id}/documents")
async def get_sale_documents(sale_id: str, user: dict = Depends(require_role([UserRole.ADMIN, UserRole.PARTNER]))):
    """Get documents for a sale"""
    sale = await db.sales.find_one({"id": sale_id})
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    
    if user["role"] == UserRole.PARTNER and sale["partner_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return sale.get("documents", [])
