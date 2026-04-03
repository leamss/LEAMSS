"""
Sales Router for LEAMSS Portal (MySQL)
"""
from fastapi import APIRouter, Depends, HTTPException, status, Form, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime
import os
import uuid
from core.database import get_db
from core.models import (
    Sale, SaleDocument, SaleStatus, User, Product, Case, CaseStep, 
    CaseStepRequirement, WorkflowStep, DocumentRequirement, UserRole, 
    UserStatus, Notification, PaymentMethod, AuditLog
)
from core.auth import get_current_user, require_role, get_password_hash
from core.schemas import SaleApproval

router = APIRouter(prefix="/sales", tags=["Sales"])

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


async def _log(db, user_id, action, entity_type, entity_id=None, new_value=None):
    try:
        db.add(AuditLog(user_id=user_id, action=action, entity_type=entity_type, entity_id=entity_id, new_value=new_value))
    except Exception:
        pass


def serialize_sale(sale: Sale) -> dict:
    """Convert sale model to dict"""
    return {
        "id": sale.id,
        "partner_id": sale.partner_id,
        "partner_name": sale.partner.name if sale.partner else "Unknown",
        "client_name": sale.client_name,
        "client_email": sale.client_email,
        "client_mobile": sale.client_mobile,
        "product_id": sale.product_id,
        "product_name": sale.product.name if sale.product else "Unknown",
        "fee_amount": sale.fee_amount,
        "amount_received": sale.amount_received,
        "payment_method": sale.payment_method.value if sale.payment_method else "bank_transfer",
        "payment_reference": sale.payment_reference,
        "agreement_signed": sale.agreement_signed,
        "status": sale.status.value if sale.status else "pending",
        "commission_rate": sale.commission_rate,
        "commission_amount": sale.commission_amount,
        "created_at": sale.created_at.isoformat() if sale.created_at else None,
        "documents": [
            {
                "id": doc.id,
                "document_type": doc.document_type,
                "filename": doc.filename,
                "file_size": doc.file_size
            }
            for doc in sale.documents
        ] if sale.documents else []
    }


@router.get("", response_model=List[dict])
async def get_all_sales(
    status: str = None,
    current_user: dict = Depends(require_role([UserRole.admin])),
    db: AsyncSession = Depends(get_db)
):
    """Get all sales (Admin only)"""
    query = select(Sale).options(
        selectinload(Sale.partner),
        selectinload(Sale.product),
        selectinload(Sale.documents)
    )
    
    if status:
        query = query.where(Sale.status == SaleStatus(status))
    
    result = await db.execute(query.order_by(Sale.created_at.desc()))
    sales = result.scalars().all()
    
    return [serialize_sale(s) for s in sales]


@router.get("/pending", response_model=List[dict])
async def get_pending_sales(
    current_user: dict = Depends(require_role([UserRole.admin])),
    db: AsyncSession = Depends(get_db)
):
    """Get pending sales for approval (Admin only)"""
    result = await db.execute(
        select(Sale)
        .options(
            selectinload(Sale.partner),
            selectinload(Sale.product),
            selectinload(Sale.documents)
        )
        .where(Sale.status == SaleStatus.pending)
        .order_by(Sale.created_at.desc())
    )
    sales = result.scalars().all()
    
    return [serialize_sale(s) for s in sales]


@router.get("/my-sales", response_model=List[dict])
async def get_my_sales(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's sales (for partners)"""
    result = await db.execute(
        select(Sale)
        .options(
            selectinload(Sale.partner),
            selectinload(Sale.product),
            selectinload(Sale.documents)
        )
        .where(Sale.partner_id == current_user["id"])
        .order_by(Sale.created_at.desc())
    )
    sales = result.scalars().all()
    
    return [serialize_sale(s) for s in sales]


@router.post("", response_model=dict)
async def create_sale(
    client_name: str = Form(...),
    client_email: str = Form(...),
    client_mobile: str = Form(...),
    product_id: str = Form(...),
    fee_amount: float = Form(...),
    amount_received: float = Form(...),
    payment_method: str = Form("bank_transfer"),
    payment_reference: str = Form(""),
    agreement_signed: bool = Form(True),
    documents: List[UploadFile] = File(default=[]),
    current_user: dict = Depends(require_role([UserRole.partner])),
    db: AsyncSession = Depends(get_db)
):
    """Create a new sale (Partner only)"""
    # Get product to fetch commission rate
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    sale = Sale(
        partner_id=current_user["id"],
        client_name=client_name,
        client_email=client_email,
        client_mobile=client_mobile,
        product_id=product_id,
        fee_amount=fee_amount,
        amount_received=amount_received,
        payment_method=PaymentMethod(payment_method) if payment_method else PaymentMethod.bank_transfer,
        payment_reference=payment_reference,
        agreement_signed=agreement_signed,
        status=SaleStatus.pending,
        commission_rate=product.commission_rate
    )
    
    db.add(sale)
    await db.flush()
    
    # Save uploaded documents
    for doc in documents:
        if doc.filename:
            file_ext = os.path.splitext(doc.filename)[1]
            file_name = f"{uuid.uuid4()}{file_ext}"
            file_path = os.path.join(UPLOAD_DIR, "sales", file_name)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            content = await doc.read()
            with open(file_path, "wb") as f:
                f.write(content)
            
            sale_doc = SaleDocument(
                sale_id=sale.id,
                document_type="sale_document",
                filename=doc.filename,
                file_path=file_path,
                file_size=len(content),
                content_type=doc.content_type
            )
            db.add(sale_doc)
    
    # Create notification for admin
    admin_result = await db.execute(select(User).where(User.role == UserRole.admin))
    admins = admin_result.scalars().all()
    
    for admin in admins:
        notification = Notification(
            user_id=admin.id,
            title="New Sale Submitted",
            message=f"Partner {current_user['name']} submitted a new sale for {client_name}",
            type="sale_pending",
            related_id=sale.id
        )
        db.add(notification)
    
    await _log(db, current_user["id"], "create_sale", "sale", sale.id, {"client_name": client_name, "product_id": product_id, "fee_amount": fee_amount})
    
    await db.commit()
    await db.refresh(sale)
    
    return {"id": sale.id, "message": "Sale created successfully"}


@router.post("/approve", response_model=dict)
async def approve_sale(
    request: SaleApproval,
    current_user: dict = Depends(require_role([UserRole.admin])),
    db: AsyncSession = Depends(get_db)
):
    """Approve or reject a sale (Admin only). Approval and case manager assignment are separate steps."""
    result = await db.execute(
        select(Sale)
        .options(selectinload(Sale.product).selectinload(Product.workflow_steps).selectinload(WorkflowStep.document_requirements))
        .where(Sale.id == request.sale_id)
    )
    sale = result.scalar_one_or_none()
    
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    
    if request.status == "approved":
        sale.status = SaleStatus.approved
        sale.approved_by = current_user["id"]
        sale.approved_at = datetime.utcnow()
        
        # Calculate commission
        sale.commission_amount = sale.fee_amount * ((sale.commission_rate or 0) / 100)
        
        # Create or get client user
        client_result = await db.execute(select(User).where(User.email == sale.client_email))
        client = client_result.scalar_one_or_none()
        
        client_password = "Client@123"
        client_is_new = False
        
        if not client:
            client_is_new = True
            client = User(
                email=sale.client_email,
                password=get_password_hash(client_password),
                name=sale.client_name,
                role=UserRole.client,
                mobile=sale.client_mobile,
                status=UserStatus.active
            )
            db.add(client)
            await db.flush()
        
        # Create case (without case_manager_id - will be assigned separately)
        case_number = f"CASE-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:4].upper()}"
        
        first_step = None
        if sale.product.workflow_steps:
            sorted_steps = sorted(sale.product.workflow_steps, key=lambda s: s.step_order)
            first_step = sorted_steps[0].step_name if sorted_steps else "Registration"
        
        case = Case(
            case_id=case_number,
            sale_id=sale.id,
            client_id=client.id,
            product_id=sale.product_id,
            case_manager_id=request.case_manager_id,  # Can be None
            partner_id=sale.partner_id,
            status="active",
            current_step=first_step,
            current_step_order=1
        )
        db.add(case)
        await db.flush()
        
        # Create case steps from workflow
        for i, step in enumerate(sorted(sale.product.workflow_steps, key=lambda s: s.step_order)):
            case_step = CaseStep(
                case_id=case.id,
                step_name=step.step_name,
                step_order=step.step_order,
                status="pending" if i == 0 else "locked",
                is_locked=i != 0
            )
            db.add(case_step)
            await db.flush()
            
            # Create document requirements
            for doc_req in step.document_requirements:
                req = CaseStepRequirement(
                    case_step_id=case_step.id,
                    doc_name=doc_req.doc_name,
                    description=doc_req.description,
                    is_mandatory=doc_req.is_mandatory,
                    has_expiry=doc_req.has_expiry,
                    validity_months=doc_req.validity_months,
                    doc_type=doc_req.doc_type
                )
                db.add(req)
        
        # Notify partner
        notification = Notification(
            user_id=sale.partner_id,
            title="Sale Approved",
            message=f"Your sale for {sale.client_name} has been approved!",
            type="sale_approved",
            related_id=sale.id
        )
        db.add(notification)
        
    elif request.status == "rejected":
        sale.status = SaleStatus.rejected
        sale.rejection_reason = request.rejection_reason
        
        # Notify partner
        notification = Notification(
            user_id=sale.partner_id,
            title="Sale Rejected",
            message=f"Your sale for {sale.client_name} has been rejected. Reason: {request.rejection_reason}",
            type="sale_rejected",
            related_id=sale.id
        )
        db.add(notification)
    
    await _log(db, current_user["id"], f"sale_{request.status}", "sale", request.sale_id, {"status": request.status, "client_name": sale.client_name})
    
    await db.commit()
    
    response = {"message": f"Sale {request.status} successfully"}
    
    # Include client credentials if a new client was created
    if request.status == "approved" and client_is_new:
        response["client_credentials"] = {
            "email": sale.client_email,
            "password": client_password,
            "name": sale.client_name,
            "message": "New client account created. Please share these login credentials with the client."
        }
    
    return response


@router.get("/{sale_id}/documents", response_model=list)
async def get_sale_documents(
    sale_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get documents for a specific sale"""
    result = await db.execute(
        select(Sale)
        .options(selectinload(Sale.documents))
        .where(Sale.id == sale_id)
    )
    sale = result.scalar_one_or_none()
    
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    
    return [
        {
            "id": doc.id,
            "file_id": doc.id,
            "document_type": doc.document_type,
            "type": doc.document_type,
            "filename": doc.filename,
            "file_size": doc.file_size,
            "content_type": doc.content_type,
            "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None
        }
        for doc in (sale.documents or [])
    ]


@router.get("/stats", response_model=dict)
async def get_sales_stats(
    current_user: dict = Depends(require_role([UserRole.admin, UserRole.partner])),
    db: AsyncSession = Depends(get_db)
):
    """Get sales statistics"""
    if current_user["role"] == "admin":
        # Admin sees all stats
        total_result = await db.execute(select(func.count(Sale.id)))
        total = total_result.scalar()
        
        pending_result = await db.execute(select(func.count(Sale.id)).where(Sale.status == SaleStatus.pending))
        pending = pending_result.scalar()
        
        approved_result = await db.execute(select(func.count(Sale.id)).where(Sale.status == SaleStatus.approved))
        approved = approved_result.scalar()
        
        total_commission_result = await db.execute(
            select(func.sum(Sale.commission_amount))
            .where(Sale.status == SaleStatus.approved)
        )
        total_commission = total_commission_result.scalar() or 0
        
        return {
            "total_sales": total,
            "pending_sales": pending,
            "approved_sales": approved,
            "total_commission": total_commission
        }
    else:
        # Partner sees only their stats
        total_result = await db.execute(
            select(func.count(Sale.id)).where(Sale.partner_id == current_user["id"])
        )
        total = total_result.scalar()
        
        approved_result = await db.execute(
            select(func.count(Sale.id))
            .where(Sale.partner_id == current_user["id"])
            .where(Sale.status == SaleStatus.approved)
        )
        approved = approved_result.scalar()
        
        commission_result = await db.execute(
            select(func.sum(Sale.commission_amount))
            .where(Sale.partner_id == current_user["id"])
            .where(Sale.status == SaleStatus.approved)
        )
        commission = commission_result.scalar() or 0
        
        return {
            "total_sales": total,
            "approved_sales": approved,
            "total_commission": commission
        }


@router.get("/partner-report", response_model=dict)
async def get_partner_report(
    partner_id: Optional[str] = None,
    period: Optional[str] = "lifetime",
    current_user: dict = Depends(require_role([UserRole.admin])),
    db: AsyncSession = Depends(get_db)
):
    """Get partner-wise sales report (Admin only)"""
    from sqlalchemy import and_
    
    query = select(Sale).options(
        selectinload(Sale.partner),
        selectinload(Sale.product)
    )
    
    if partner_id:
        query = query.where(Sale.partner_id == partner_id)
    
    if period and period != "lifetime":
        from datetime import timedelta
        now = datetime.utcnow()
        if period == "month":
            query = query.where(Sale.created_at >= now - timedelta(days=30))
        elif period == "quarter":
            query = query.where(Sale.created_at >= now - timedelta(days=90))
        elif period == "year":
            query = query.where(Sale.created_at >= now - timedelta(days=365))
    
    result = await db.execute(query.order_by(Sale.created_at.desc()))
    sales = result.scalars().all()
    
    total_sales = len(sales)
    approved_sales = len([s for s in sales if s.status == SaleStatus.approved])
    total_revenue = sum(s.fee_amount for s in sales if s.status == SaleStatus.approved)
    total_commission = sum((s.commission_amount or 0) for s in sales if s.status == SaleStatus.approved)
    
    sales_data = []
    for sale in sales:
        sales_data.append({
            "id": sale.id,
            "date": sale.created_at.isoformat() if sale.created_at else None,
            "client_name": sale.client_name,
            "client_email": sale.client_email,
            "partner_name": sale.partner.name if sale.partner else "N/A",
            "product_name": sale.product.name if sale.product else "N/A",
            "fee_amount": sale.fee_amount,
            "commission_amount": sale.commission_amount or 0,
            "commission_rate": sale.commission_rate or 0,
            "status": sale.status.value if hasattr(sale.status, 'value') else str(sale.status),
            "payment_method": sale.payment_method,
            "payment_reference": sale.payment_reference
        })
    
    # Get partner breakdown
    partner_breakdown = {}
    for sale in sales:
        pid = sale.partner_id
        pname = sale.partner.name if sale.partner else "Unknown"
        if pid not in partner_breakdown:
            partner_breakdown[pid] = {"name": pname, "total_sales": 0, "approved": 0, "revenue": 0, "commission": 0}
        partner_breakdown[pid]["total_sales"] += 1
        if sale.status == SaleStatus.approved:
            partner_breakdown[pid]["approved"] += 1
            partner_breakdown[pid]["revenue"] += sale.fee_amount
            partner_breakdown[pid]["commission"] += (sale.commission_amount or 0)
    
    return {
        "total_sales": total_sales,
        "approved_sales": approved_sales,
        "total_revenue": total_revenue,
        "total_commission": total_commission,
        "sales": sales_data,
        "partner_breakdown": list(partner_breakdown.values())
    }
