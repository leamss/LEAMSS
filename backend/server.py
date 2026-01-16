from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
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

class ProductBase(BaseModel):
    name: str
    description: str
    fee: float
    commission_rate: float

class ProductCreate(ProductBase):
    pass

class WorkflowStep(BaseModel):
    step_name: str
    step_order: int
    description: Optional[str] = None

class ProductResponse(ProductBase):
    id: str
    workflow_steps: List[WorkflowStep] = []

class WorkflowStepCreate(BaseModel):
    product_id: str
    step_name: str
    step_order: int
    description: Optional[str] = None

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
    documents: List[str] = []

class SaleApproval(BaseModel):
    sale_id: str
    status: str
    case_manager_id: Optional[str] = None

class CaseResponse(BaseModel):
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
    created_at: str
    steps: List[Dict] = []

class DocumentResponse(BaseModel):
    id: str
    filename: str
    case_id: str
    uploaded_by: str
    upload_date: str
    status: str
    step_name: Optional[str] = None
    review_comment: Optional[str] = None

class DocumentReview(BaseModel):
    document_id: str
    status: str
    comment: Optional[str] = None

class StepUpdate(BaseModel):
    case_id: str
    step_name: str
    status: str
    notes: Optional[str] = None

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
        "description": step.description
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
    
    commission_amount = sale.fee_amount * (product["commission_rate"] / 100)
    
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
        "commission_rate": product["commission_rate"],
        "commission_amount": commission_amount,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "documents": []
    }
    
    await db.sales.insert_one(sale_doc)
    sale_doc.pop("_id")
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
async def approve_sale(approval: SaleApproval, user: dict = Depends(require_role([UserRole.ADMIN]))):
    sale = await db.sales.find_one({"id": approval.sale_id})
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    
    await db.sales.update_one(
        {"id": approval.sale_id},
        {"$set": {"status": approval.status}}
    )
    
    if approval.status == "approved":
        client_doc = {
            "id": str(ObjectId()),
            "name": sale["client_name"],
            "email": sale["client_email"],
            "mobile": sale["client_mobile"],
            "role": UserRole.CLIENT,
            "password": pwd_context.hash("Welcome@123"),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.users.insert_one(client_doc)
        
        product = await db.products.find_one({"id": sale["product_id"]})
        case_manager = await db.users.find_one({"id": approval.case_manager_id})
        
        case_steps = []
        if product and "workflow_steps" in product:
            for step in product["workflow_steps"]:
                case_steps.append({
                    "step_name": step["step_name"],
                    "step_order": step["step_order"],
                    "status": "pending",
                    "notes": ""
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
            "steps": case_steps,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.cases.insert_one(case_doc)
    
    return {"message": f"Sale {approval.status}"}

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
    
    return CaseResponse(**case)

@api_router.post("/cases/update-step")
async def update_case_step(update: StepUpdate, user: dict = Depends(require_role([UserRole.CASE_MANAGER, UserRole.ADMIN]))):
    case = await db.cases.find_one({"id": update.case_id})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    await db.cases.update_one(
        {"id": update.case_id, "steps.step_name": update.step_name},
        {"$set": {
            "steps.$.status": update.status,
            "steps.$.notes": update.notes,
            "current_step": update.step_name
        }}
    )
    
    return {"message": "Step updated"}

@api_router.post("/documents/upload")
async def upload_document(
    case_id: str = Form(...),
    step_name: str = Form(...),
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    case = await db.cases.find_one({"id": case_id})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    file_content = await file.read()
    file_id = await fs.upload_from_stream(
        file.filename,
        io.BytesIO(file_content),
        metadata={
            "case_id": case_id,
            "step_name": step_name,
            "uploaded_by": user["id"],
            "upload_date": datetime.now(timezone.utc).isoformat(),
            "status": "pending_review"
        }
    )
    
    doc_entry = {
        "id": str(file_id),
        "filename": file.filename,
        "case_id": case_id,
        "uploaded_by": user["id"],
        "upload_date": datetime.now(timezone.utc).isoformat(),
        "status": "pending_review",
        "step_name": step_name
    }
    await db.documents.insert_one(doc_entry)
    
    return {"message": "Document uploaded", "file_id": str(file_id)}

@api_router.get("/documents/case/{case_id}", response_model=List[DocumentResponse])
async def get_case_documents(case_id: str, user: dict = Depends(get_current_user)):
    documents = await db.documents.find({"case_id": case_id}, {"_id": 0}).to_list(1000)
    return [DocumentResponse(**d) for d in documents]

@api_router.post("/documents/review")
async def review_document(review: DocumentReview, user: dict = Depends(require_role([UserRole.CASE_MANAGER, UserRole.ADMIN]))):
    await db.documents.update_one(
        {"id": review.document_id},
        {"$set": {
            "status": review.status,
            "review_comment": review.comment,
            "reviewed_by": user["id"],
            "reviewed_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    return {"message": "Document reviewed"}

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
        
        stats = {
            "pending_sales": pending_sales,
            "active_cases": active_cases,
            "total_revenue": total_revenue
        }
    elif user["role"] == UserRole.CASE_MANAGER:
        my_cases = await db.cases.count_documents({"case_manager_id": user["id"]})
        pending_docs = await db.documents.count_documents({"status": "pending_review"})
        stats = {
            "my_cases": my_cases,
            "pending_documents": pending_docs
        }
    elif user["role"] == UserRole.PARTNER:
        my_sales = await db.sales.count_documents({"partner_id": user["id"]})
        approved_sales = await db.sales.count_documents({"partner_id": user["id"], "status": "approved"})
        sales = await db.sales.find({"partner_id": user["id"], "status": "approved"}).to_list(1000)
        total_commission = sum(s["commission_amount"] for s in sales)
        stats = {
            "total_sales": my_sales,
            "approved_sales": approved_sales,
            "total_commission": total_commission
        }
    elif user["role"] == UserRole.CLIENT:
        my_case = await db.cases.find_one({"client_id": user["id"]}, {"_id": 0})
        if my_case:
            pending_steps = len([s for s in my_case.get("steps", []) if s["status"] == "pending"])
            completed_steps = len([s for s in my_case.get("steps", []) if s["status"] == "completed"])
            stats = {
                "case_id": my_case.get("case_id"),
                "current_step": my_case.get("current_step"),
                "pending_steps": pending_steps,
                "completed_steps": completed_steps
            }
    
    return stats

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
