from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, UploadFile, File, Form, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional, Dict, Any
from bson import ObjectId
import os
import logging
from pathlib import Path
import io

# Import email service
from email_service import email_service

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]
fs = AsyncIOMotorGridFSBucket(db)

app = FastAPI()
api_router = APIRouter(prefix="/api")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

SECRET_KEY = os.environ.get("JWT_SECRET", "immigration-portal-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440

class UserRole:
    ADMIN = "admin"
    CASE_MANAGER = "case_manager"
    CLIENT = "client"
    PARTNER = "partner"

class UserBase(BaseModel):
    email: EmailStr
    name: str
    role: str
    mobile: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: str
    created_at: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    token: str
    user: UserResponse

class DocumentRequirement(BaseModel):
    doc_name: str
    description: str
    is_mandatory: bool = True

class WorkflowStepDetail(BaseModel):
    step_name: str
    step_order: int
    description: Optional[str] = None
    duration_days: Optional[int] = None
    required_documents: List[DocumentRequirement] = []

class ProductBase(BaseModel):
    name: str
    description: str
    fee: float
    commission_rate: float
    commission_type: str = "fixed"  # fixed, tiered, custom
    commission_tiers: Optional[List[Dict[str, Any]]] = None  # For tiered commissions
    commission_effective_from: Optional[str] = None  # When commission changes take effect

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    fee: Optional[float] = None
    commission_rate: Optional[float] = None
    commission_type: Optional[str] = None
    commission_tiers: Optional[List[Dict[str, Any]]] = None
    commission_effective_from: Optional[str] = None

class ProductResponse(ProductBase):
    model_config = ConfigDict(extra="ignore")
    id: str
    workflow_steps: List[Dict[str, Any]] = []
    commission_type: str = "fixed"
    commission_tiers: List[Dict[str, Any]] = []
    commission_history: List[Dict[str, Any]] = []  # Track commission changes

class WorkflowStepCreate(BaseModel):
    product_id: str
    step_name: str
    step_order: int
    description: Optional[str] = None
    duration_days: Optional[int] = None
    required_documents: List[DocumentRequirement] = []

class SaleCreate(BaseModel):
    client_name: str
    client_email: EmailStr
    client_mobile: str
    product_id: str
    fee_amount: float
    amount_received: float
    payment_method: str
    payment_reference: str
    agreement_signed: bool

class SaleResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str
    partner_id: str
    partner_name: str
    client_name: str
    client_email: str
    client_mobile: str
    product_id: str
    product_name: str
    fee_amount: float
    amount_received: float
    payment_method: str
    payment_reference: str
    status: str
    commission_rate: float
    commission_amount: float
    created_at: str
    documents: List[Dict[str, Any]] = []

class SaleApproval(BaseModel):
    sale_id: str
    status: str
    case_manager_id: Optional[str] = None

class CaseStepStatus(BaseModel):
    step_name: str
    step_order: int
    status: str
    notes: str = ""
    uploaded_documents: List[str] = []
    required_documents: List[DocumentRequirement] = []
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    is_locked: bool = True

class CaseResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    case_id: str
    client_id: str
    client_name: str
    client_email: str
    product_id: str
    product_name: str
    case_manager_id: str
    case_manager_name: str
    partner_id: str
    partner_name: str
    status: str
    current_step: str
    current_step_order: int = 1
    created_at: str
    steps: List[Dict[str, Any]] = []
    additional_doc_requests: List[Dict[str, Any]] = []

class DocumentResponse(BaseModel):
    id: str
    filename: str
    case_id: str
    uploaded_by: str
    upload_date: str
    status: str
    step_name: Optional[str] = None
    document_type: Optional[str] = None
    review_comment: Optional[str] = None
    file_size: Optional[int] = None

class DocumentReview(BaseModel):
    document_id: str
    status: str
    comment: Optional[str] = None

class StepUpdate(BaseModel):
    case_id: str
    step_name: str
    status: str
    notes: Optional[str] = None

class AdditionalDocRequest(BaseModel):
    case_id: str
    document_name: str
    description: str
    due_date: Optional[str] = None

class TicketCreate(BaseModel):
    case_id: Optional[str] = None
    subject: str
    category: str
    priority: str
    description: str

class TicketResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    case_id: Optional[str] = None
    created_by: str
    created_by_name: str
    created_by_role: str
    subject: str
    category: str
    priority: str
    description: str
    status: str
    created_at: str
    messages: List[Dict[str, Any]] = []

class TicketMessage(BaseModel):
    ticket_id: str
    message: str

class NotificationResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    user_id: str
    title: str
    message: str
    type: str
    related_id: Optional[str] = None
    is_read: bool = False
    created_at: str

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = await db.users.find_one({"email": email}, {"_id": 0})
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def require_role(allowed_roles: List[str]):
    async def role_checker(user: dict = Depends(get_current_user)):
        if user["role"] not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return role_checker

async def create_notification(user_id: str, title: str, message: str, notification_type: str, related_id: Optional[str] = None):
    notification = {
        "id": str(ObjectId()),
        "user_id": user_id,
        "title": title,
        "message": message,
        "type": notification_type,
        "related_id": related_id,
        "is_read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.notifications.insert_one(notification)

@api_router.post("/auth/register", response_model=UserResponse)
async def register(user: UserCreate):
    existing = await db.users.find_one({"email": user.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = pwd_context.hash(user.password)
    user_doc = {
        "id": str(ObjectId()),
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "mobile": user.mobile,
        "password": hashed_password,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user_doc)
    user_doc.pop("password")
    return UserResponse(**user_doc)

@api_router.post("/auth/login", response_model=LoginResponse)
async def login(login_req: LoginRequest):
    user = await db.users.find_one({"email": login_req.email})
    if not user or not pwd_context.verify(login_req.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token({"sub": user["email"], "role": user["role"]})
    user.pop("password")
    user.pop("_id")
    return LoginResponse(token=token, user=UserResponse(**user))

@api_router.post("/products", response_model=ProductResponse)
async def create_product(product: ProductCreate, user: dict = Depends(require_role([UserRole.ADMIN]))):
    product_doc = {
        "id": str(ObjectId()),
        "name": product.name,
        "description": product.description,
        "fee": product.fee,
        "commission_rate": product.commission_rate,
        "commission_type": product.commission_type,
        "commission_tiers": product.commission_tiers or [],
        "workflow_steps": [],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.products.insert_one(product_doc)
    product_doc.pop("_id")
    return ProductResponse(**product_doc)

@api_router.get("/products", response_model=List[ProductResponse])
async def get_products(user: dict = Depends(get_current_user)):
    products = await db.products.find({}, {"_id": 0}).to_list(1000)
    return [ProductResponse(**p) for p in products]

@api_router.post("/products/workflow-step")
async def add_workflow_step(step: WorkflowStepCreate, user: dict = Depends(require_role([UserRole.ADMIN]))):
    product = await db.products.find_one({"id": step.product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    step_doc = {
        "step_name": step.step_name,
        "step_order": step.step_order,
        "description": step.description,
        "duration_days": step.duration_days,
        "required_documents": [doc.model_dump() for doc in step.required_documents]
    }
    
    await db.products.update_one(
        {"id": step.product_id},
        {"$push": {"workflow_steps": step_doc}}
    )
    return {"message": "Workflow step added"}

@api_router.post("/sales", response_model=SaleResponse)
async def create_sale(sale: SaleCreate, user: dict = Depends(require_role([UserRole.PARTNER]))):
    product = await db.products.find_one({"id": sale.product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Calculate commission based on commission type
    commission_rate = product["commission_rate"]
    commission_type = product.get("commission_type", "fixed")
    
    if commission_type == "tiered":
        # Count partner's approved sales for tiered calculation
        partner_sales_count = await db.sales.count_documents({
            "partner_id": user["id"],
            "status": "approved"
        })
        
        tiers = product.get("commission_tiers", [])
        for tier in sorted(tiers, key=lambda x: x.get("min_sales", 0)):
            if tier.get("min_sales", 0) <= partner_sales_count <= tier.get("max_sales", 999999):
                commission_rate = tier.get("rate", commission_rate)
                break
    elif commission_type == "custom":
        # Check if partner has custom rate
        partner = await db.users.find_one({"id": user["id"]})
        custom_rates = partner.get("custom_commission_rates", {})
        if sale.product_id in custom_rates:
            commission_rate = custom_rates[sale.product_id]
    
    commission_amount = sale.fee_amount * (commission_rate / 100)
    
    sale_doc = {
        "id": str(ObjectId()),
        "partner_id": user["id"],
        "partner_name": user["name"],
        "client_name": sale.client_name,
        "client_email": sale.client_email,
        "client_mobile": sale.client_mobile,
        "product_id": sale.product_id,
        "product_name": product["name"],
        "fee_amount": sale.fee_amount,
        "amount_received": sale.amount_received,
        "payment_method": sale.payment_method,
        "payment_reference": sale.payment_reference,
        "status": "pending",
        "commission_type": commission_type,
        "commission_rate": commission_rate,
        "commission_amount": commission_amount,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "documents": []
    }
    
    await db.sales.insert_one(sale_doc)
    sale_doc.pop("_id")
    
    admin_users = await db.users.find({"role": UserRole.ADMIN}, {"_id": 0}).to_list(100)
    for admin in admin_users:
        await create_notification(
            admin["id"],
            "New Sale Pending Approval",
            f"New sale from {user['name']} for {sale.client_name} - {product['name']}",
            "sale_created",
            sale_doc["id"]
        )
    
    return SaleResponse(**sale_doc)

@api_router.post("/sales/{sale_id}/upload-document")
async def upload_sale_document(
    sale_id: str,
    file: UploadFile = File(...),
    document_type: str = Form(...),
    user: dict = Depends(require_role([UserRole.PARTNER]))
):
    sale = await db.sales.find_one({"id": sale_id, "partner_id": user["id"]})
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    
    file_content = await file.read()
    file_id = await fs.upload_from_stream(
        file.filename,
        io.BytesIO(file_content),
        metadata={
            "sale_id": sale_id,
            "document_type": document_type,
            "uploaded_by": user["id"],
            "upload_date": datetime.now(timezone.utc).isoformat()
        }
    )
    
    await db.sales.update_one(
        {"id": sale_id},
        {"$push": {"documents": {"file_id": str(file_id), "type": document_type, "filename": file.filename}}}
    )
    
    return {"message": "Document uploaded", "file_id": str(file_id)}

@api_router.get("/sales/my-sales", response_model=List[SaleResponse])
async def get_my_sales(user: dict = Depends(require_role([UserRole.PARTNER]))):
    sales = await db.sales.find({"partner_id": user["id"]}, {"_id": 0}).to_list(1000)
    return [SaleResponse(**s) for s in sales]

@api_router.get("/sales/pending", response_model=List[SaleResponse])
async def get_pending_sales(user: dict = Depends(require_role([UserRole.ADMIN]))):
    sales = await db.sales.find({"status": "pending"}, {"_id": 0}).to_list(1000)
    return [SaleResponse(**s) for s in sales]

@api_router.post("/sales/approve")
async def approve_sale(approval: SaleApproval, background_tasks: BackgroundTasks, user: dict = Depends(require_role([UserRole.ADMIN]))):
    sale = await db.sales.find_one({"id": approval.sale_id})
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    
    await db.sales.update_one(
        {"id": approval.sale_id},
        {"$set": {"status": approval.status}}
    )
    
    if approval.status == "approved":
        temp_password = "Welcome@123"
        client_doc = {
            "id": str(ObjectId()),
            "name": sale["client_name"],
            "email": sale["client_email"],
            "mobile": sale["client_mobile"],
            "role": UserRole.CLIENT,
            "password": pwd_context.hash(temp_password),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.users.insert_one(client_doc)
        
        product = await db.products.find_one({"id": sale["product_id"]})
        case_manager = await db.users.find_one({"id": approval.case_manager_id})
        
        case_steps = []
        if product and "workflow_steps" in product:
            for idx, step in enumerate(sorted(product["workflow_steps"], key=lambda x: x["step_order"])):
                case_steps.append({
                    "step_name": step["step_name"],
                    "step_order": step["step_order"],
                    "status": "in_progress" if idx == 0 else "locked",
                    "notes": "",
                    "uploaded_documents": [],
                    "required_documents": step.get("required_documents", []),
                    "approved_by": None,
                    "approved_at": None,
                    "is_locked": False if idx == 0 else True
                })
        
        case_doc = {
            "id": str(ObjectId()),
            "case_id": f"CASE-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{str(ObjectId())[:6].upper()}",
            "client_id": client_doc["id"],
            "client_name": sale["client_name"],
            "client_email": sale["client_email"],
            "product_id": sale["product_id"],
            "product_name": sale["product_name"],
            "case_manager_id": approval.case_manager_id,
            "case_manager_name": case_manager["name"] if case_manager else "",
            "partner_id": sale["partner_id"],
            "partner_name": sale["partner_name"],
            "sale_id": sale["id"],
            "status": "active",
            "current_step": case_steps[0]["step_name"] if case_steps else "Onboarding",
            "current_step_order": 1,
            "steps": case_steps,
            "additional_doc_requests": [],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.cases.insert_one(case_doc)
        
        await create_notification(
            case_manager["id"],
            "New Case Assigned",
            f"New case {case_doc['case_id']} for {sale['client_name']} has been assigned to you",
            "case_assigned",
            case_doc["id"]
        )
        
        await create_notification(
            client_doc["id"],
            "Welcome to LEAMSS Portal",
            f"Your case {case_doc['case_id']} has been created. Login with password: Welcome@123",
            "case_created",
            case_doc["id"]
        )
        
        # Send email notifications
        background_tasks.add_task(
            email_service.send_welcome_email,
            sale["client_email"],
            sale["client_name"],
            temp_password,
            case_doc["case_id"]
        )
        
        # Notify partner about approved sale
        partner = await db.users.find_one({"id": sale["partner_id"]})
        if partner:
            background_tasks.add_task(
                email_service.send_sale_approved_email,
                partner["email"],
                partner["name"],
                sale["client_name"],
                sale["product_name"],
                sale.get("commission_amount", 0)
            )
    else:
        # Sale rejected - notify partner
        partner = await db.users.find_one({"id": sale["partner_id"]})
        if partner:
            background_tasks.add_task(
                email_service.send_sale_rejected_email,
                partner["email"],
                partner["name"],
                sale["client_name"],
                sale["product_name"]
            )
    
    return {"message": f"Sale {approval.status}"}

# ==================== SALES REPORTS & COMMISSION ENDPOINTS ====================

@api_router.get("/sales/all")
async def get_all_sales(
    partner_id: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    period: Optional[str] = None,  # lifetime, weekly, monthly, yearly
    user: dict = Depends(require_role([UserRole.ADMIN]))
):
    """Get all sales with filtering options"""
    query = {}
    
    if partner_id:
        query["partner_id"] = partner_id
    if status:
        query["status"] = status
    
    # Handle date filtering
    if period:
        now = datetime.now(timezone.utc)
        if period == "weekly":
            start_date = now - timedelta(days=7)
        elif period == "monthly":
            start_date = now - timedelta(days=30)
        elif period == "yearly":
            start_date = now - timedelta(days=365)
        else:  # lifetime
            start_date = None
        
        if start_date:
            query["created_at"] = {"$gte": start_date.isoformat()}
    elif date_from or date_to:
        date_query = {}
        if date_from:
            date_query["$gte"] = date_from
        if date_to:
            date_query["$lte"] = date_to
        if date_query:
            query["created_at"] = date_query
    
    sales = await db.sales.find(query, {"_id": 0}).sort("created_at", -1).to_list(10000)
    return sales

@api_router.get("/sales/partner-report/{partner_id}")
async def get_partner_sales_report(
    partner_id: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    period: Optional[str] = None,
    user: dict = Depends(require_role([UserRole.ADMIN]))
):
    """Get detailed sales report for a specific partner"""
    query = {"partner_id": partner_id}
    
    # Handle date filtering
    if period:
        now = datetime.now(timezone.utc)
        if period == "weekly":
            start_date = now - timedelta(days=7)
        elif period == "monthly":
            start_date = now - timedelta(days=30)
        elif period == "yearly":
            start_date = now - timedelta(days=365)
        else:
            start_date = None
        
        if start_date:
            query["created_at"] = {"$gte": start_date.isoformat()}
    elif date_from or date_to:
        date_query = {}
        if date_from:
            date_query["$gte"] = date_from
        if date_to:
            date_query["$lte"] = date_to
        if date_query:
            query["created_at"] = date_query
    
    sales = await db.sales.find(query, {"_id": 0}).to_list(10000)
    partner = await db.users.find_one({"id": partner_id}, {"_id": 0, "password": 0})
    
    # Calculate totals
    total_sales = len(sales)
    approved_sales = [s for s in sales if s["status"] == "approved"]
    pending_sales = [s for s in sales if s["status"] == "pending"]
    rejected_sales = [s for s in sales if s["status"] == "rejected"]
    
    total_revenue = sum(s.get("fee_amount", 0) for s in approved_sales)
    total_commission = sum(s.get("commission_amount", 0) for s in approved_sales)
    
    return {
        "partner": partner,
        "summary": {
            "total_sales": total_sales,
            "approved_sales": len(approved_sales),
            "pending_sales": len(pending_sales),
            "rejected_sales": len(rejected_sales),
            "total_revenue": total_revenue,
            "total_commission_payable": total_commission
        },
        "sales": sales
    }

@api_router.get("/reports/partner-commissions")
async def get_all_partner_commissions(user: dict = Depends(require_role([UserRole.ADMIN]))):
    """Get commission summary for all partners"""
    partners = await db.users.find({"role": UserRole.PARTNER}, {"_id": 0, "password": 0}).to_list(1000)
    
    result = []
    for partner in partners:
        approved_sales = await db.sales.find({
            "partner_id": partner["id"],
            "status": "approved"
        }, {"_id": 0}).to_list(10000)
        
        total_revenue = sum(s.get("fee_amount", 0) for s in approved_sales)
        total_commission = sum(s.get("commission_amount", 0) for s in approved_sales)
        
        # Calculate by period
        now = datetime.now(timezone.utc)
        weekly_commission = sum(
            s.get("commission_amount", 0) for s in approved_sales 
            if s.get("created_at", "") >= (now - timedelta(days=7)).isoformat()
        )
        monthly_commission = sum(
            s.get("commission_amount", 0) for s in approved_sales 
            if s.get("created_at", "") >= (now - timedelta(days=30)).isoformat()
        )
        yearly_commission = sum(
            s.get("commission_amount", 0) for s in approved_sales 
            if s.get("created_at", "") >= (now - timedelta(days=365)).isoformat()
        )
        
        result.append({
            "partner_id": partner["id"],
            "partner_name": partner["name"],
            "partner_email": partner["email"],
            "total_sales_count": len(approved_sales),
            "total_revenue_generated": total_revenue,
            "lifetime_commission": total_commission,
            "weekly_commission": weekly_commission,
            "monthly_commission": monthly_commission,
            "yearly_commission": yearly_commission
        })
    
    return result

@api_router.get("/reports/sales-summary")
async def get_sales_summary(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    period: Optional[str] = None,
    user: dict = Depends(require_role([UserRole.ADMIN]))
):
    """Get overall sales summary with filters"""
    query = {}
    
    if period:
        now = datetime.now(timezone.utc)
        if period == "weekly":
            start_date = now - timedelta(days=7)
        elif period == "monthly":
            start_date = now - timedelta(days=30)
        elif period == "yearly":
            start_date = now - timedelta(days=365)
        else:
            start_date = None
        
        if start_date:
            query["created_at"] = {"$gte": start_date.isoformat()}
    elif date_from or date_to:
        date_query = {}
        if date_from:
            date_query["$gte"] = date_from
        if date_to:
            date_query["$lte"] = date_to
        if date_query:
            query["created_at"] = date_query
    
    all_sales = await db.sales.find(query, {"_id": 0}).to_list(10000)
    approved_sales = [s for s in all_sales if s["status"] == "approved"]
    
    return {
        "total_sales": len(all_sales),
        "approved_sales": len(approved_sales),
        "pending_sales": len([s for s in all_sales if s["status"] == "pending"]),
        "rejected_sales": len([s for s in all_sales if s["status"] == "rejected"]),
        "total_revenue": sum(s.get("fee_amount", 0) for s in approved_sales),
        "total_commission_payable": sum(s.get("commission_amount", 0) for s in approved_sales)
    }

# ==================== ENHANCED TICKET ENDPOINTS ====================

@api_router.get("/tickets/all")
async def get_all_tickets(
    ticket_status: Optional[str] = None,
    priority: Optional[str] = None,
    created_by_role: Optional[str] = None,
    user: dict = Depends(require_role([UserRole.ADMIN]))
):
    """Get all tickets with filtering options (Admin only)"""
    query = {}
    if ticket_status:
        query["status"] = ticket_status
    if priority:
        query["priority"] = priority
    if created_by_role:
        query["created_by_role"] = created_by_role
    
    tickets = await db.tickets.find(query, {"_id": 0}).sort("created_at", -1).to_list(10000)
    return tickets

@api_router.put("/tickets/{ticket_id}/status")
async def update_ticket_status(
    ticket_id: str,
    new_status: str,
    resolution_note: Optional[str] = None,
    background_tasks: BackgroundTasks = None,
    user: dict = Depends(require_role([UserRole.ADMIN, UserRole.CASE_MANAGER]))
):
    """Update ticket status (open, in_progress, resolved, closed)"""
    ticket = await db.tickets.find_one({"id": ticket_id})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    update_data = {
        "status": status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": user["id"],
        "updated_by_name": user["name"]
    }
    
    if status in ["resolved", "closed"] and resolution_note:
        update_data["resolution_note"] = resolution_note
        update_data["resolved_at"] = datetime.now(timezone.utc).isoformat()
        update_data["resolved_by"] = user["id"]
        update_data["resolved_by_name"] = user["name"]
    
    await db.tickets.update_one(
        {"id": ticket_id},
        {"$set": update_data}
    )
    
    # Notify the ticket creator
    status_messages = {
        "in_progress": "Your ticket is now being processed",
        "resolved": "Your ticket has been resolved",
        "closed": "Your ticket has been closed"
    }
    
    if status in status_messages:
        await create_notification(
            ticket["created_by"],
            f"Ticket Update: {ticket['subject']}",
            status_messages[status] + (f". Note: {resolution_note}" if resolution_note else ""),
            "ticket_status_update",
            ticket_id
        )
        
        # Send email notification if resolved
        if status == "resolved" and background_tasks:
            ticket_creator = await db.users.find_one({"id": ticket["created_by"]})
            if ticket_creator:
                background_tasks.add_task(
                    email_service.send_email,
                    ticket_creator["email"],
                    f"Ticket Resolved: {ticket['subject']}",
                    email_service.get_base_template(f"""
                        <h2>Your Ticket Has Been Resolved</h2>
                        <p>Hello {ticket_creator['name']},</p>
                        <div class="success-box">
                            <p>Your support ticket has been resolved.</p>
                        </div>
                        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                            <tr>
                                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;"><strong>Subject:</strong></td>
                                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">{ticket['subject']}</td>
                            </tr>
                            <tr>
                                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;"><strong>Resolution Note:</strong></td>
                                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">{resolution_note or 'Issue has been resolved.'}</td>
                            </tr>
                            <tr>
                                <td style="padding: 10px;"><strong>Resolved By:</strong></td>
                                <td style="padding: 10px;">{user['name']}</td>
                            </tr>
                        </table>
                        <p>If you have any further questions, please create a new ticket.</p>
                    """)
                )
    
    return {"message": f"Ticket status updated to {status}"}

@api_router.get("/tickets/{ticket_id}")
async def get_ticket_details(ticket_id: str, user: dict = Depends(get_current_user)):
    """Get detailed ticket information"""
    ticket = await db.tickets.find_one({"id": ticket_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Check access
    if user["role"] not in [UserRole.ADMIN, UserRole.CASE_MANAGER]:
        if ticket["created_by"] != user["id"]:
            raise HTTPException(status_code=403, detail="Not authorized")
    
    return ticket

@api_router.get("/tickets/stats")
async def get_ticket_stats(user: dict = Depends(require_role([UserRole.ADMIN]))):
    """Get ticket statistics"""
    all_tickets = await db.tickets.find({}, {"_id": 0}).to_list(10000)
    
    return {
        "total": len(all_tickets),
        "open": len([t for t in all_tickets if t["status"] == "open"]),
        "in_progress": len([t for t in all_tickets if t["status"] == "in_progress"]),
        "resolved": len([t for t in all_tickets if t["status"] == "resolved"]),
        "closed": len([t for t in all_tickets if t["status"] == "closed"]),
        "by_priority": {
            "urgent": len([t for t in all_tickets if t["priority"] == "urgent"]),
            "high": len([t for t in all_tickets if t["priority"] == "high"]),
            "medium": len([t for t in all_tickets if t["priority"] == "medium"]),
            "low": len([t for t in all_tickets if t["priority"] == "low"])
        },
        "by_role": {
            "client": len([t for t in all_tickets if t["created_by_role"] == UserRole.CLIENT]),
            "partner": len([t for t in all_tickets if t["created_by_role"] == UserRole.PARTNER]),
            "case_manager": len([t for t in all_tickets if t["created_by_role"] == UserRole.CASE_MANAGER])
        }
    }

@api_router.get("/cases/my-cases", response_model=List[CaseResponse])
async def get_my_cases(user: dict = Depends(get_current_user)):
    query = {}
    if user["role"] == UserRole.CASE_MANAGER:
        query = {"case_manager_id": user["id"]}
    elif user["role"] == UserRole.CLIENT:
        query = {"client_id": user["id"]}
    elif user["role"] == UserRole.PARTNER:
        query = {"partner_id": user["id"]}
    
    cases = await db.cases.find(query, {"_id": 0}).to_list(1000)
    return [CaseResponse(**c) for c in cases]

@api_router.get("/cases", response_model=List[CaseResponse])
async def get_all_cases(user: dict = Depends(require_role([UserRole.ADMIN]))):
    cases = await db.cases.find({}, {"_id": 0}).to_list(1000)
    return [CaseResponse(**c) for c in cases]

@api_router.get("/cases/{case_id}", response_model=CaseResponse)
async def get_case(case_id: str, user: dict = Depends(get_current_user)):
    case = await db.cases.find_one({"id": case_id}, {"_id": 0})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    if user["role"] == UserRole.CASE_MANAGER and case["case_manager_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    elif user["role"] == UserRole.CLIENT and case["client_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    elif user["role"] == UserRole.PARTNER and case["partner_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return CaseResponse(**case)

@api_router.post("/cases/update-step")
async def update_case_step(update: StepUpdate, background_tasks: BackgroundTasks, user: dict = Depends(require_role([UserRole.CASE_MANAGER, UserRole.ADMIN]))):
    case = await db.cases.find_one({"id": update.case_id})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    steps = case.get("steps", [])
    current_step_index = next((i for i, s in enumerate(steps) if s["step_name"] == update.step_name), None)
    
    if current_step_index is None:
        raise HTTPException(status_code=404, detail="Step not found")
    
    next_step_name = None
    if update.status == "completed":
        steps[current_step_index]["status"] = "completed"
        steps[current_step_index]["approved_by"] = user["id"]
        steps[current_step_index]["approved_at"] = datetime.now(timezone.utc).isoformat()
        steps[current_step_index]["is_locked"] = True
        
        if current_step_index + 1 < len(steps):
            steps[current_step_index + 1]["status"] = "in_progress"
            steps[current_step_index + 1]["is_locked"] = False
            next_step_name = steps[current_step_index + 1]["step_name"]
            
            await db.cases.update_one(
                {"id": update.case_id},
                {"$set": {
                    "steps": steps,
                    "current_step": next_step_name,
                    "current_step_order": current_step_index + 2
                }}
            )
        else:
            await db.cases.update_one(
                {"id": update.case_id},
                {"$set": {"steps": steps, "status": "completed"}}
            )
        
        # Send email notification for step completion
        background_tasks.add_task(
            email_service.send_step_completed_email,
            case["client_email"],
            case["client_name"],
            update.step_name,
            next_step_name or "",
            case["case_id"]
        )
    else:
        steps[current_step_index]["status"] = update.status
        steps[current_step_index]["notes"] = update.notes or ""
        
        await db.cases.update_one(
            {"id": update.case_id},
            {"$set": {"steps": steps}}
        )
    
    await create_notification(
        case["client_id"],
        "Case Update",
        f"Step '{update.step_name}' has been updated to {update.status}",
        "step_updated",
        case["id"]
    )
    
    return {"message": "Step updated"}

@api_router.post("/cases/request-additional-document")
async def request_additional_document(request: AdditionalDocRequest, background_tasks: BackgroundTasks, user: dict = Depends(require_role([UserRole.CASE_MANAGER, UserRole.ADMIN]))):
    case = await db.cases.find_one({"id": request.case_id})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    doc_request = {
        "id": str(ObjectId()),
        "document_name": request.document_name,
        "description": request.description,
        "requested_by": user["id"],
        "requested_by_name": user["name"],
        "requested_at": datetime.now(timezone.utc).isoformat(),
        "due_date": request.due_date,
        "status": "pending",
        "uploaded_file_id": None
    }
    
    await db.cases.update_one(
        {"id": request.case_id},
        {"$push": {"additional_doc_requests": doc_request}}
    )
    
    await create_notification(
        case["client_id"],
        "Additional Document Required",
        f"Case Manager has requested: {request.document_name}",
        "doc_requested",
        case["id"]
    )
    
    # Send email notification
    background_tasks.add_task(
        email_service.send_additional_doc_request_email,
        case["client_email"],
        case["client_name"],
        request.document_name,
        request.description,
        request.due_date or "",
        case["case_id"]
    )
    
    return {"message": "Document request created", "request_id": doc_request["id"]}

@api_router.post("/documents/upload")
async def upload_document(
    case_id: str = Form(...),
    step_name: str = Form(...),
    document_type: str = Form("general"),
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    case = await db.cases.find_one({"id": case_id})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    if user["role"] == UserRole.CLIENT:
        current_step = next((s for s in case.get("steps", []) if s["status"] == "in_progress" and not s["is_locked"]), None)
        if not current_step or current_step["step_name"] != step_name:
            raise HTTPException(status_code=403, detail="Cannot upload documents for locked or future steps")
    
    file_content = await file.read()
    file_size = len(file_content)
    
    file_id = await fs.upload_from_stream(
        file.filename,
        io.BytesIO(file_content),
        metadata={
            "case_id": case_id,
            "step_name": step_name,
            "document_type": document_type,
            "uploaded_by": user["id"],
            "upload_date": datetime.now(timezone.utc).isoformat(),
            "status": "pending_review",
            "file_size": file_size
        }
    )
    
    doc_entry = {
        "id": str(file_id),
        "filename": file.filename,
        "case_id": case_id,
        "uploaded_by": user["id"],
        "upload_date": datetime.now(timezone.utc).isoformat(),
        "status": "pending_review",
        "step_name": step_name,
        "document_type": document_type,
        "file_size": file_size
    }
    await db.documents.insert_one(doc_entry)
    
    await db.cases.update_one(
        {"id": case_id, "steps.step_name": step_name},
        {"$push": {"steps.$.uploaded_documents": str(file_id)}}
    )
    
    await create_notification(
        case["case_manager_id"],
        "New Document Uploaded",
        f"Client {case['client_name']} uploaded {file.filename} for step {step_name}",
        "doc_uploaded",
        case_id
    )
    
    return {"message": "Document uploaded", "file_id": str(file_id)}

@api_router.get("/documents/download/{file_id}")
async def download_document(file_id: str, user: dict = Depends(get_current_user)):
    try:
        grid_out = await fs.open_download_stream(ObjectId(file_id))
        metadata = grid_out.metadata or {}
        
        case_id = metadata.get("case_id")
        if case_id:
            case = await db.cases.find_one({"id": case_id})
            if case:
                if user["role"] == UserRole.CLIENT and case["client_id"] != user["id"]:
                    raise HTTPException(status_code=403, detail="Not authorized")
                elif user["role"] == UserRole.CASE_MANAGER and case["case_manager_id"] != user["id"]:
                    raise HTTPException(status_code=403, detail="Not authorized")
                elif user["role"] == UserRole.PARTNER and case["partner_id"] != user["id"]:
                    raise HTTPException(status_code=403, detail="Not authorized")
        
        contents = await grid_out.read()
        filename = grid_out.filename or "document"
        
        return StreamingResponse(
            io.BytesIO(contents),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Document not found: {str(e)}")

@api_router.get("/documents/case/{case_id}", response_model=List[DocumentResponse])
async def get_case_documents(case_id: str, user: dict = Depends(get_current_user)):
    documents = await db.documents.find({"case_id": case_id}, {"_id": 0}).to_list(1000)
    return [DocumentResponse(**d) for d in documents]

@api_router.post("/documents/review")
async def review_document(review: DocumentReview, background_tasks: BackgroundTasks, user: dict = Depends(require_role([UserRole.CASE_MANAGER, UserRole.ADMIN]))):
    doc = await db.documents.find_one({"id": review.document_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    await db.documents.update_one(
        {"id": review.document_id},
        {"$set": {
            "status": review.status,
            "review_comment": review.comment,
            "reviewed_by": user["id"],
            "reviewed_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    case = await db.cases.find_one({"id": doc["case_id"]})
    if case:
        await create_notification(
            case["client_id"],
            "Document Reviewed",
            f"Your document '{doc['filename']}' has been {review.status}",
            "doc_reviewed",
            case["id"]
        )
        
        # Send email notification to client
        if review.status == "approved":
            background_tasks.add_task(
                email_service.send_document_approved_email,
                case["client_email"],
                case["client_name"],
                doc["filename"],
                doc.get("step_name", "N/A"),
                case["case_id"]
            )
        elif review.status == "rejected":
            background_tasks.add_task(
                email_service.send_document_rejected_email,
                case["client_email"],
                case["client_name"],
                doc["filename"],
                review.comment or "",
                case["case_id"]
            )
    
    return {"message": "Document reviewed"}

@api_router.post("/tickets", response_model=TicketResponse)
async def create_ticket(ticket: TicketCreate, user: dict = Depends(get_current_user)):
    ticket_doc = {
        "id": str(ObjectId()),
        "case_id": ticket.case_id,
        "created_by": user["id"],
        "created_by_name": user["name"],
        "created_by_role": user["role"],
        "subject": ticket.subject,
        "category": ticket.category,
        "priority": ticket.priority,
        "description": ticket.description,
        "status": "open",
        "messages": [],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.tickets.insert_one(ticket_doc)
    ticket_doc.pop("_id")
    
    admin_users = await db.users.find({"role": UserRole.ADMIN}, {"_id": 0}).to_list(100)
    for admin in admin_users:
        await create_notification(
            admin["id"],
            f"New Ticket: {ticket.subject}",
            f"Ticket raised by {user['name']} ({user['role']})",
            "ticket_created",
            ticket_doc["id"]
        )
    
    if ticket.case_id:
        case = await db.cases.find_one({"id": ticket.case_id})
        if case and case["case_manager_id"] != user["id"]:
            await create_notification(
                case["case_manager_id"],
                f"New Ticket: {ticket.subject}",
                f"Ticket raised by {user['name']} for case {case['case_id']}",
                "ticket_created",
                ticket_doc["id"]
            )
    
    return TicketResponse(**ticket_doc)

@api_router.get("/tickets/my-tickets", response_model=List[TicketResponse])
async def get_my_tickets(user: dict = Depends(get_current_user)):
    if user["role"] == UserRole.ADMIN:
        tickets = await db.tickets.find({}, {"_id": 0}).to_list(1000)
    else:
        tickets = await db.tickets.find({"created_by": user["id"]}, {"_id": 0}).to_list(1000)
    return [TicketResponse(**t) for t in tickets]

@api_router.post("/tickets/{ticket_id}/message")
async def add_ticket_message(ticket_id: str, message: TicketMessage, user: dict = Depends(get_current_user)):
    ticket = await db.tickets.find_one({"id": ticket_id})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    msg = {
        "user_id": user["id"],
        "user_name": user["name"],
        "user_role": user["role"],
        "message": message.message,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.tickets.update_one(
        {"id": ticket_id},
        {"$push": {"messages": msg}}
    )
    
    if ticket["created_by"] != user["id"]:
        await create_notification(
            ticket["created_by"],
            f"New message on ticket: {ticket['subject']}",
            f"{user['name']} replied to your ticket",
            "ticket_message",
            ticket_id
        )
    
    return {"message": "Message added"}

@api_router.get("/notifications", response_model=List[NotificationResponse])
async def get_notifications(user: dict = Depends(get_current_user)):
    notifications = await db.notifications.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return [NotificationResponse(**n) for n in notifications]

@api_router.post("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, user: dict = Depends(get_current_user)):
    await db.notifications.update_one(
        {"id": notification_id, "user_id": user["id"]},
        {"$set": {"is_read": True}}
    )
    return {"message": "Notification marked as read"}

@api_router.get("/users/case-managers")
async def get_case_managers(user: dict = Depends(require_role([UserRole.ADMIN]))):
    managers = await db.users.find({"role": UserRole.CASE_MANAGER}, {"_id": 0, "password": 0}).to_list(1000)
    return managers

@api_router.get("/stats/dashboard")
async def get_dashboard_stats(user: dict = Depends(get_current_user)):
    stats = {}
    
    if user["role"] == UserRole.ADMIN:
        pending_sales = await db.sales.count_documents({"status": "pending"})
        active_cases = await db.cases.count_documents({"status": "active"})
        total_revenue = 0
        sales = await db.sales.find({"status": "approved"}).to_list(1000)
        total_revenue = sum(s["amount_received"] for s in sales)
        unread_notifications = await db.notifications.count_documents({"user_id": user["id"], "is_read": False})
        
        stats = {
            "pending_sales": pending_sales,
            "active_cases": active_cases,
            "total_revenue": total_revenue,
            "unread_notifications": unread_notifications
        }
    elif user["role"] == UserRole.CASE_MANAGER:
        my_cases = await db.cases.count_documents({"case_manager_id": user["id"]})
        pending_docs = await db.documents.count_documents({"status": "pending_review"})
        unread_notifications = await db.notifications.count_documents({"user_id": user["id"], "is_read": False})
        stats = {
            "my_cases": my_cases,
            "pending_documents": pending_docs,
            "unread_notifications": unread_notifications
        }
    elif user["role"] == UserRole.PARTNER:
        my_sales = await db.sales.count_documents({"partner_id": user["id"]})
        approved_sales = await db.sales.count_documents({"partner_id": user["id"], "status": "approved"})
        sales = await db.sales.find({"partner_id": user["id"], "status": "approved"}).to_list(1000)
        total_commission = sum(s["commission_amount"] for s in sales)
        unread_notifications = await db.notifications.count_documents({"user_id": user["id"], "is_read": False})
        stats = {
            "total_sales": my_sales,
            "approved_sales": approved_sales,
            "total_commission": total_commission,
            "unread_notifications": unread_notifications
        }
    elif user["role"] == UserRole.CLIENT:
        my_case = await db.cases.find_one({"client_id": user["id"]}, {"_id": 0})
        unread_notifications = await db.notifications.count_documents({"user_id": user["id"], "is_read": False})
        if my_case:
            pending_steps = len([s for s in my_case.get("steps", []) if s["status"] in ["pending", "in_progress"]])
            completed_steps = len([s for s in my_case.get("steps", []) if s["status"] == "completed"])
            pending_doc_requests = len([r for r in my_case.get("additional_doc_requests", []) if r["status"] == "pending"])
            stats = {
                "case_id": my_case.get("case_id"),
                "current_step": my_case.get("current_step"),
                "pending_steps": pending_steps,
                "completed_steps": completed_steps,
                "pending_doc_requests": pending_doc_requests,
                "unread_notifications": unread_notifications
            }
    
    return stats


# Admin - Edit Product
@api_router.put("/products/{product_id}")
async def update_product(product_id: str, product: ProductUpdate, user: dict = Depends(require_role([UserRole.ADMIN]))):
    existing_product = await db.products.find_one({"id": product_id})
    if not existing_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    update_data = {}
    
    # Check if commission structure is changing
    commission_changed = False
    if product.commission_type is not None and product.commission_type != existing_product.get("commission_type"):
        commission_changed = True
    if product.commission_rate is not None and product.commission_rate != existing_product.get("commission_rate"):
        commission_changed = True
    if product.commission_tiers is not None and product.commission_tiers != existing_product.get("commission_tiers"):
        commission_changed = True
    
    # Build update data
    if product.name is not None:
        update_data["name"] = product.name
    if product.description is not None:
        update_data["description"] = product.description
    if product.fee is not None:
        update_data["fee"] = product.fee
    if product.commission_rate is not None:
        update_data["commission_rate"] = product.commission_rate
    if product.commission_type is not None:
        update_data["commission_type"] = product.commission_type
    if product.commission_tiers is not None:
        update_data["commission_tiers"] = product.commission_tiers
    
    # If commission changed, add to history
    if commission_changed:
        effective_from = product.commission_effective_from or datetime.now(timezone.utc).isoformat()
        commission_history_entry = {
            "changed_at": datetime.now(timezone.utc).isoformat(),
            "effective_from": effective_from,
            "changed_by": user["id"],
            "previous_type": existing_product.get("commission_type", "fixed"),
            "previous_rate": existing_product.get("commission_rate", 0),
            "previous_tiers": existing_product.get("commission_tiers", []),
            "new_type": product.commission_type or existing_product.get("commission_type"),
            "new_rate": product.commission_rate or existing_product.get("commission_rate"),
            "new_tiers": product.commission_tiers or existing_product.get("commission_tiers", [])
        }
        
        await db.products.update_one(
            {"id": product_id},
            {"$push": {"commission_history": commission_history_entry}}
        )
        
        update_data["commission_effective_from"] = effective_from
    
    if update_data:
        await db.products.update_one(
            {"id": product_id},
            {"$set": update_data}
        )
    
    return {"message": "Product updated"}

# Admin - Delete Product
@api_router.delete("/products/{product_id}")
async def delete_product(product_id: str, user: dict = Depends(require_role([UserRole.ADMIN]))):
    result = await db.products.delete_one({"id": product_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product deleted"}

# Admin - Update Workflow Step
@api_router.put("/products/{product_id}/workflow-step/{step_order}")
async def update_workflow_step(product_id: str, step_order: int, step: WorkflowStepCreate, user: dict = Depends(require_role([UserRole.ADMIN]))):
    product = await db.products.find_one({"id": product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    steps = product.get("workflow_steps", [])
    updated = False
    for i, s in enumerate(steps):
        if s["step_order"] == step_order:
            steps[i] = {
                "step_name": step.step_name,
                "step_order": step.step_order,
                "description": step.description,
                "duration_days": step.duration_days,
                "required_documents": [doc.model_dump() for doc in step.required_documents]
            }
            updated = True
            break
    
    if not updated:
        raise HTTPException(status_code=404, detail="Step not found")
    
    await db.products.update_one(
        {"id": product_id},
        {"$set": {"workflow_steps": steps}}
    )
    return {"message": "Workflow step updated"}

# Admin - Delete Workflow Step
@api_router.delete("/products/{product_id}/workflow-step/{step_order}")
async def delete_workflow_step(product_id: str, step_order: int, user: dict = Depends(require_role([UserRole.ADMIN]))):
    product = await db.products.find_one({"id": product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    steps = [s for s in product.get("workflow_steps", []) if s["step_order"] != step_order]
    
    await db.products.update_one(
        {"id": product_id},
        {"$set": {"workflow_steps": steps}}
    )
    return {"message": "Workflow step deleted"}

# Admin - Get All Users
@api_router.get("/users")
async def get_all_users(user: dict = Depends(require_role([UserRole.ADMIN]))):
    users = await db.users.find({}, {"_id": 0, "password": 0}).to_list(1000)
    return users

# Admin - Update User
@api_router.put("/users/{user_id}")
async def update_user(user_id: str, update_data: dict, user: dict = Depends(require_role([UserRole.ADMIN]))):
    if "password" in update_data:
        update_data["password"] = pwd_context.hash(update_data["password"])
    
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": update_data}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User updated"}

# Admin - Delete User
@api_router.delete("/users/{user_id}")
async def delete_user(user_id: str, user: dict = Depends(require_role([UserRole.ADMIN]))):
    result = await db.users.delete_one({"id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted"}

# Admin - Update Case Manager Assignment
@api_router.put("/cases/{case_id}/assign-manager")
async def reassign_case_manager(case_id: str, case_manager_id: str, user: dict = Depends(require_role([UserRole.ADMIN]))):
    case_manager = await db.users.find_one({"id": case_manager_id, "role": UserRole.CASE_MANAGER})
    if not case_manager:
        raise HTTPException(status_code=404, detail="Case manager not found")
    
    result = await db.cases.update_one(
        {"id": case_id},
        {"$set": {
            "case_manager_id": case_manager_id,
            "case_manager_name": case_manager["name"]
        }}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Case not found")
    
    case = await db.cases.find_one({"id": case_id})
    await create_notification(
        case_manager_id,
        "Case Reassigned",
        f"Case {case['case_id']} for {case['client_name']} has been reassigned to you",
        "case_assigned",
        case_id
    )
    
    return {"message": "Case manager updated"}

# Admin - Impersonate User (Get Token)
@api_router.post("/admin/impersonate/{user_id}")
async def impersonate_user(user_id: str, admin: dict = Depends(require_role([UserRole.ADMIN]))):
    target_user = await db.users.find_one({"id": user_id})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    token = create_access_token({"sub": target_user["email"], "role": target_user["role"]})
    target_user.pop("password")
    target_user.pop("_id")
    return {
        "token": token,
        "user": UserResponse(**target_user)
    }

# Get Sale Documents (for admin approval view)
@api_router.get("/sales/{sale_id}/documents")
async def get_sale_documents(sale_id: str, user: dict = Depends(require_role([UserRole.ADMIN, UserRole.PARTNER]))):
    sale = await db.sales.find_one({"id": sale_id})
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    
    if user["role"] == UserRole.PARTNER and sale["partner_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return sale.get("documents", [])


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
