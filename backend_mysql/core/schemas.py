"""
Pydantic schemas for API request/response validation
"""
from pydantic import BaseModel, EmailStr, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime, date


# ==================== AUTH SCHEMAS ====================

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    token: str
    user: dict


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str
    mobile: Optional[str] = None
    commission_rate: Optional[float] = 0.0


class UserUpdate(BaseModel):
    name: Optional[str] = None
    mobile: Optional[str] = None
    status: Optional[str] = None
    commission_rate: Optional[float] = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    email: str
    name: str
    role: str
    mobile: Optional[str] = None
    status: str
    commission_rate: Optional[float] = 0.0
    created_at: datetime


# ==================== PRODUCT SCHEMAS ====================

class DocumentRequirementSchema(BaseModel):
    doc_name: str
    description: Optional[str] = None
    is_mandatory: bool = True
    has_expiry: bool = False
    validity_months: Optional[int] = None
    doc_type: Optional[str] = None


class WorkflowStepCreate(BaseModel):
    step_name: str
    step_order: int
    description: Optional[str] = None
    duration_days: Optional[int] = None
    required_documents: List[DocumentRequirementSchema] = []


class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    fee: float
    commission_rate: float
    commission_type: str = "fixed"
    commission_tiers: Optional[List[Dict[str, Any]]] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    fee: Optional[float] = None
    commission_rate: Optional[float] = None
    commission_type: Optional[str] = None
    commission_tiers: Optional[List[Dict[str, Any]]] = None


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    name: str
    description: Optional[str] = None
    fee: float
    commission_rate: float
    commission_type: str
    workflow_steps: List[Dict[str, Any]] = []
    commission_tiers: List[Dict[str, Any]] = []
    commission_history: List[Dict[str, Any]] = []


# ==================== SALES SCHEMAS ====================

class SaleCreate(BaseModel):
    client_name: str
    client_email: EmailStr
    client_mobile: str
    product_id: str
    fee_amount: float
    amount_received: float
    payment_method: str = "bank_transfer"
    payment_reference: str
    agreement_signed: bool = True


class SaleApproval(BaseModel):
    sale_id: str
    status: str
    case_manager_id: Optional[str] = None
    rejection_reason: Optional[str] = None


class SaleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    partner_id: str
    partner_name: str
    client_name: str
    client_email: str
    client_mobile: Optional[str] = None
    product_id: str
    product_name: str
    fee_amount: float
    amount_received: float
    payment_method: str
    payment_reference: Optional[str] = None
    status: str
    commission_rate: Optional[float] = None
    commission_amount: Optional[float] = None
    created_at: datetime
    documents: List[Dict[str, Any]] = []


# ==================== CASE SCHEMAS ====================

class CaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    case_id: str
    client_id: str
    client_name: str
    client_email: str
    product_id: str
    product_name: str
    case_manager_id: Optional[str] = None
    case_manager_name: Optional[str] = None
    partner_id: Optional[str] = None
    partner_name: Optional[str] = None
    status: str
    current_step: Optional[str] = None
    current_step_order: int = 1
    created_at: datetime
    steps: List[Dict[str, Any]] = []
    additional_doc_requests: List[Dict[str, Any]] = []


class StepUpdate(BaseModel):
    case_id: str
    step_name: str
    status: str
    notes: Optional[str] = None


class AdditionalDocRequest(BaseModel):
    case_id: str
    step_order: Optional[int] = None
    document_name: str
    description: Optional[str] = None
    due_date: Optional[str] = None
    expiry_date: Optional[str] = None
    validity_months: Optional[int] = None
    doc_type: Optional[str] = None


# ==================== DOCUMENT SCHEMAS ====================

class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    file_id: Optional[str] = None
    filename: str
    case_id: str
    uploaded_by: str
    uploaded_by_name: Optional[str] = None
    upload_date: str
    uploaded_at: Optional[str] = None
    status: str
    step_name: Optional[str] = None
    document_type: Optional[str] = None
    review_comment: Optional[str] = None
    file_size: Optional[int] = None
    expiry_date: Optional[str] = None


class DocumentReview(BaseModel):
    document_id: str
    status: str
    comment: Optional[str] = None


# ==================== TICKET SCHEMAS ====================

class TicketCreate(BaseModel):
    case_id: Optional[str] = None
    subject: str
    category: str = "general"
    priority: str = "medium"
    description: str
    target_user_ids: Optional[List[str]] = None
    target_role: Optional[str] = None


class TicketMessage(BaseModel):
    message: str


class TicketStatusUpdate(BaseModel):
    status: str
    resolution_note: Optional[str] = None


class TicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
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
    created_at: datetime
    messages: List[Dict[str, Any]] = []
    target_user_ids: List[str] = []
    target_role: Optional[str] = None
    activity_log: List[Dict[str, Any]] = []
    attachments: List[Dict[str, Any]] = []
    resolution_note: Optional[str] = None
    resolved_by: Optional[str] = None
    resolved_by_name: Optional[str] = None
    resolved_at: Optional[datetime] = None


# ==================== NOTIFICATION SCHEMAS ====================

class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    user_id: str
    title: str
    message: str
    type: str
    related_id: Optional[str] = None
    is_read: bool = False
    created_at: datetime


class PushSubscriptionCreate(BaseModel):
    endpoint: str
    keys: Dict[str, str]


# ==================== SETTINGS SCHEMAS ====================

class SystemSettings(BaseModel):
    allow_case_manager_workflow_customization: bool = False
