"""
Pydantic models for LEAMSS Portal API
"""
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional, Dict, Any


# ==================== AUTH MODELS ====================

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


# ==================== PRODUCT MODELS ====================

class DocumentRequirement(BaseModel):
    doc_name: str
    description: str
    is_mandatory: bool = True
    has_expiry: bool = False
    expiry_date: Optional[str] = None
    validity_months: Optional[int] = None
    doc_type: Optional[str] = None


class WorkflowStepDetail(BaseModel):
    step_name: str
    step_order: int
    description: Optional[str] = None
    duration_days: Optional[int] = None
    required_documents: List[DocumentRequirement] = []


class CommissionHistoryEntry(BaseModel):
    commission_rate: float
    commission_type: str
    commission_tiers: Optional[List[Dict[str, Any]]] = None
    effective_from: str
    created_at: str
    created_by: Optional[str] = None
    created_by_name: Optional[str] = None


class ProductBase(BaseModel):
    name: str
    description: str
    fee: float
    commission_rate: float
    commission_type: str = "fixed"
    commission_tiers: Optional[List[Dict[str, Any]]] = None
    commission_effective_from: Optional[str] = None
    commission_history: Optional[List[Dict[str, Any]]] = None


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
    commission_history: List[Dict[str, Any]] = []


class WorkflowStepCreate(BaseModel):
    product_id: str
    step_name: str
    step_order: int
    description: Optional[str] = None
    duration_days: Optional[int] = None
    required_documents: List[DocumentRequirement] = []


# ==================== SALES MODELS ====================

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


# ==================== CASE MODELS ====================

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


class StepUpdate(BaseModel):
    case_id: str
    step_name: str
    status: str
    notes: Optional[str] = None


class AdditionalDocRequest(BaseModel):
    case_id: str
    step_order: int
    document_name: str
    description: Optional[str] = None
    due_date: Optional[str] = None
    expiry_date: Optional[str] = None
    validity_months: Optional[int] = None
    doc_type: Optional[str] = None


# ==================== DOCUMENT MODELS ====================

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


# ==================== TICKET MODELS ====================

class TicketCreate(BaseModel):
    case_id: Optional[str] = None
    subject: str
    category: str
    priority: str
    description: str
    target_user_ids: Optional[List[str]] = None
    target_role: Optional[str] = None


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
    target_user_ids: List[str] = []
    target_role: Optional[str] = None
    activity_log: List[Dict[str, Any]] = []
    attachments: List[Dict[str, Any]] = []
    resolution_note: Optional[str] = None
    resolved_by: Optional[str] = None
    resolved_by_name: Optional[str] = None
    resolved_at: Optional[str] = None


class TicketMessage(BaseModel):
    message: str


class TicketUpdate(BaseModel):
    description: Optional[str] = None
    resolution_note: Optional[str] = None


class TicketStatusUpdate(BaseModel):
    status: str
    resolution_note: Optional[str] = None


# ==================== NOTIFICATION MODELS ====================

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


class PushSubscription(BaseModel):
    endpoint: str
    keys: Dict[str, str]


class PushSubscriptionResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    user_id: str
    endpoint: str
    created_at: str


# ==================== SETTINGS MODELS ====================

class SystemSettings(BaseModel):
    allow_case_manager_workflow_customization: bool = False
