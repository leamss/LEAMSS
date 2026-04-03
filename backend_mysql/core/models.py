"""
SQLAlchemy Models for LEAMSS Portal
"""
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, DateTime, Enum, ForeignKey, JSON, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
import uuid
import enum


def generate_uuid():
    return str(uuid.uuid4())


# ==================== ENUMS ====================

class UserRole(enum.Enum):
    admin = "admin"
    case_manager = "case_manager"
    partner = "partner"
    client = "client"


class UserStatus(enum.Enum):
    active = "active"
    inactive = "inactive"
    suspended = "suspended"


class CommissionType(enum.Enum):
    fixed = "fixed"
    percentage = "percentage"
    tiered = "tiered"


class PaymentMethod(enum.Enum):
    cash = "cash"
    bank_transfer = "bank_transfer"
    card = "card"
    cheque = "cheque"
    check = "check"
    upi = "upi"
    online = "online"
    other = "other"


class SaleStatus(enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    completed = "completed"


class CaseStatus(enum.Enum):
    active = "active"
    in_progress = "in_progress"
    on_hold = "on_hold"
    completed = "completed"
    cancelled = "cancelled"


class StepStatus(enum.Enum):
    locked = "locked"
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"


class DocumentStatus(enum.Enum):
    pending = "pending"
    uploaded = "uploaded"
    pending_review = "pending_review"
    approved = "approved"
    rejected = "rejected"


class TicketCategory(enum.Enum):
    general = "general"
    technical = "technical"
    document = "document"
    payment = "payment"
    complaint = "complaint"
    other = "other"


class TicketPriority(enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class TicketStatus(enum.Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"
    closed = "closed"


# ==================== MODELS ====================

class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, index=True)
    mobile = Column(String(20))
    status = Column(Enum(UserStatus), default=UserStatus.active, index=True)
    commission_rate = Column(Float, default=0.0)
    profile_image = Column(String(500))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    sales = relationship("Sale", back_populates="partner", foreign_keys="Sale.partner_id")
    cases_as_client = relationship("Case", back_populates="client", foreign_keys="Case.client_id")
    cases_as_manager = relationship("Case", back_populates="case_manager", foreign_keys="Case.case_manager_id")
    notifications = relationship("Notification", back_populates="user")
    tickets_created = relationship("Ticket", back_populates="created_by_user", foreign_keys="Ticket.created_by")


class Product(Base):
    __tablename__ = "products"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    fee = Column(Float, nullable=False, default=0.0)
    commission_rate = Column(Float, nullable=False, default=0.0)
    commission_type = Column(Enum(CommissionType), default=CommissionType.fixed)
    commission_effective_from = Column(Date)
    status = Column(String(20), default="active", index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    workflow_steps = relationship("WorkflowStep", back_populates="product", cascade="all, delete-orphan")
    commission_tiers = relationship("CommissionTier", back_populates="product", cascade="all, delete-orphan")
    commission_history = relationship("CommissionHistory", back_populates="product", cascade="all, delete-orphan")
    sales = relationship("Sale", back_populates="product")
    cases = relationship("Case", back_populates="product")


class CommissionTier(Base):
    __tablename__ = "commission_tiers"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    min_sales = Column(Integer, nullable=False, default=0)
    max_sales = Column(Integer)
    commission_rate = Column(Float, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    
    product = relationship("Product", back_populates="commission_tiers")


class CommissionHistory(Base):
    __tablename__ = "commission_history"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    commission_rate = Column(Float, nullable=False)
    commission_type = Column(Enum(CommissionType), nullable=False)
    effective_from = Column(Date, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    
    product = relationship("Product", back_populates="commission_history")


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    step_name = Column(String(255), nullable=False)
    step_order = Column(Integer, nullable=False)
    description = Column(Text)
    duration_days = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    product = relationship("Product", back_populates="workflow_steps")
    document_requirements = relationship("DocumentRequirement", back_populates="workflow_step", cascade="all, delete-orphan")


class DocumentRequirement(Base):
    __tablename__ = "document_requirements"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    workflow_step_id = Column(String(36), ForeignKey("workflow_steps.id", ondelete="CASCADE"), nullable=False, index=True)
    doc_name = Column(String(255), nullable=False)
    description = Column(Text)
    is_mandatory = Column(Boolean, default=True)
    has_expiry = Column(Boolean, default=False)
    validity_months = Column(Integer)
    doc_type = Column(String(100))
    created_at = Column(DateTime, server_default=func.now())
    
    workflow_step = relationship("WorkflowStep", back_populates="document_requirements")


class Sale(Base):
    __tablename__ = "sales"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    partner_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    client_name = Column(String(255), nullable=False)
    client_email = Column(String(255), nullable=False)
    client_mobile = Column(String(20))
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False)
    fee_amount = Column(Float, nullable=False)
    amount_received = Column(Float, nullable=False, default=0.0)
    payment_method = Column(Enum(PaymentMethod), default=PaymentMethod.bank_transfer)
    payment_reference = Column(String(255))
    payment_status = Column(String(50), default="unpaid")  # unpaid, partial, paid
    agreement_signed = Column(Boolean, default=False)
    status = Column(Enum(SaleStatus), default=SaleStatus.pending, index=True)
    commission_rate = Column(Float)
    commission_amount = Column(Float)
    approved_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    approved_at = Column(DateTime)
    rejection_reason = Column(Text)
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    partner = relationship("User", back_populates="sales", foreign_keys=[partner_id])
    product = relationship("Product", back_populates="sales")
    documents = relationship("SaleDocument", back_populates="sale", cascade="all, delete-orphan")
    case = relationship("Case", back_populates="sale", uselist=False)


class SaleDocument(Base):
    __tablename__ = "sale_documents"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    sale_id = Column(String(36), ForeignKey("sales.id", ondelete="CASCADE"), nullable=False, index=True)
    document_type = Column(String(100), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500))
    file_size = Column(Integer)
    content_type = Column(String(100))
    uploaded_at = Column(DateTime, server_default=func.now())
    
    sale = relationship("Sale", back_populates="documents")


class Case(Base):
    __tablename__ = "cases"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(50), unique=True, nullable=False, index=True)
    sale_id = Column(String(36), ForeignKey("sales.id", ondelete="SET NULL"))
    client_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False)
    case_manager_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), index=True)
    partner_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    status = Column(Enum(CaseStatus), default=CaseStatus.active, index=True)
    current_step = Column(String(255))
    current_step_order = Column(Integer, default=1)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime)
    
    sale = relationship("Sale", back_populates="case")
    client = relationship("User", back_populates="cases_as_client", foreign_keys=[client_id])
    case_manager = relationship("User", back_populates="cases_as_manager", foreign_keys=[case_manager_id])
    product = relationship("Product", back_populates="cases")
    steps = relationship("CaseStep", back_populates="case", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="case", cascade="all, delete-orphan")
    additional_doc_requests = relationship("AdditionalDocRequest", back_populates="case", cascade="all, delete-orphan")
    tickets = relationship("Ticket", back_populates="case")


class CaseStep(Base):
    __tablename__ = "case_steps"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    step_name = Column(String(255), nullable=False)
    step_order = Column(Integer, nullable=False)
    status = Column(Enum(StepStatus), default=StepStatus.locked, index=True)
    notes = Column(Text)
    is_locked = Column(Boolean, default=True)
    approved_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    approved_at = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    case = relationship("Case", back_populates="steps")
    requirements = relationship("CaseStepRequirement", back_populates="case_step", cascade="all, delete-orphan")


class CaseStepRequirement(Base):
    __tablename__ = "case_step_requirements"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_step_id = Column(String(36), ForeignKey("case_steps.id", ondelete="CASCADE"), nullable=False, index=True)
    doc_name = Column(String(255), nullable=False)
    description = Column(Text)
    is_mandatory = Column(Boolean, default=True)
    has_expiry = Column(Boolean, default=False)
    expiry_date = Column(Date)
    validity_months = Column(Integer)
    doc_type = Column(String(100))
    status = Column(Enum(DocumentStatus), default=DocumentStatus.pending)
    created_at = Column(DateTime, server_default=func.now())
    
    case_step = relationship("CaseStep", back_populates="requirements")


class Document(Base):
    __tablename__ = "documents"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    case_step_id = Column(String(36), ForeignKey("case_steps.id", ondelete="SET NULL"))
    requirement_id = Column(String(36), ForeignKey("case_step_requirements.id", ondelete="SET NULL"))
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255))
    file_path = Column(String(500))
    file_size = Column(Integer)
    content_type = Column(String(100))
    document_type = Column(String(100))
    step_name = Column(String(255))
    status = Column(Enum(DocumentStatus), default=DocumentStatus.uploaded, index=True)
    uploaded_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    reviewed_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    review_comment = Column(Text)
    expiry_date = Column(Date, index=True)
    reviewed_at = Column(DateTime)
    uploaded_at = Column(DateTime, server_default=func.now())
    
    case = relationship("Case", back_populates="documents")


class AdditionalDocRequest(Base):
    __tablename__ = "additional_doc_requests"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    step_order = Column(Integer)
    document_name = Column(String(255), nullable=False)
    description = Column(Text)
    due_date = Column(Date)
    expiry_date = Column(Date)
    validity_months = Column(Integer)
    doc_type = Column(String(100))
    status = Column(Enum(DocumentStatus), default=DocumentStatus.pending, index=True)
    requested_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    uploaded_document_id = Column(String(36), ForeignKey("documents.id", ondelete="SET NULL"))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    case = relationship("Case", back_populates="additional_doc_requests")


class Ticket(Base):
    __tablename__ = "tickets"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="SET NULL"))
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    subject = Column(String(255), nullable=False)
    category = Column(Enum(TicketCategory), default=TicketCategory.general)
    priority = Column(Enum(TicketPriority), default=TicketPriority.medium, index=True)
    description = Column(Text, nullable=False)
    status = Column(Enum(TicketStatus), default=TicketStatus.open, index=True)
    target_role = Column(String(50))
    resolution_note = Column(Text)
    resolved_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    resolved_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    case = relationship("Case", back_populates="tickets")
    created_by_user = relationship("User", back_populates="tickets_created", foreign_keys=[created_by])
    messages = relationship("TicketMessage", back_populates="ticket", cascade="all, delete-orphan")
    attachments = relationship("TicketAttachment", back_populates="ticket", cascade="all, delete-orphan")
    activity_log = relationship("TicketActivityLog", back_populates="ticket", cascade="all, delete-orphan")
    targets = relationship("TicketTarget", back_populates="ticket", cascade="all, delete-orphan")


class TicketTarget(Base):
    __tablename__ = "ticket_targets"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    ticket_id = Column(String(36), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())
    
    ticket = relationship("Ticket", back_populates="targets")


class TicketMessage(Base):
    __tablename__ = "ticket_messages"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    ticket_id = Column(String(36), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    
    ticket = relationship("Ticket", back_populates="messages")


class TicketAttachment(Base):
    __tablename__ = "ticket_attachments"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    ticket_id = Column(String(36), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    uploaded_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500))
    file_size = Column(Integer)
    content_type = Column(String(100))
    uploaded_at = Column(DateTime, server_default=func.now())
    
    ticket = relationship("Ticket", back_populates="attachments")


class TicketActivityLog(Base):
    __tablename__ = "ticket_activity_log"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    ticket_id = Column(String(36), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    action = Column(String(100), nullable=False)
    details = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    
    ticket = relationship("Ticket", back_populates="activity_log")


class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(100), nullable=False)
    related_id = Column(String(36))
    related_type = Column(String(50))
    is_read = Column(Boolean, default=False, index=True)
    read_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now(), index=True)
    
    user = relationship("User", back_populates="notifications")


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    endpoint = Column(Text, nullable=False)
    p256dh_key = Column(String(500))
    auth_key = Column(String(500))
    created_at = Column(DateTime, server_default=func.now())


class SystemSetting(Base):
    __tablename__ = "system_settings"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    setting_key = Column(String(100), unique=True, nullable=False, index=True)
    setting_value = Column(Text)
    setting_type = Column(String(20), default="string")
    description = Column(Text)
    updated_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ExpiryNotificationSent(Base):
    __tablename__ = "expiry_notifications_sent"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    notification_type = Column(String(20), nullable=False)
    sent_at = Column(DateTime, server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_log"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    action = Column(String(100), nullable=False)
    entity_type = Column(String(100), nullable=False)
    entity_id = Column(String(36))
    old_value = Column(JSON)
    new_value = Column(JSON)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    created_at = Column(DateTime, server_default=func.now(), index=True)



class PaymentStatus(enum.Enum):
    initiated = "initiated"
    pending = "pending"
    paid = "paid"
    failed = "failed"
    expired = "expired"
    refunded = "refunded"


class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), index=True)
    sale_id = Column(String(36), ForeignKey("sales.id", ondelete="SET NULL"), index=True)
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="SET NULL"), index=True)
    
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="inr")
    
    payment_type = Column(String(50))  # fee_payment, commission_payout
    payment_method = Column(String(50))  # card, upi, etc.
    
    status = Column(Enum(PaymentStatus), default=PaymentStatus.initiated)
    payment_status = Column(String(50))  # Raw status from Stripe
    
    payment_metadata = Column("payment_metadata", JSON)
    stripe_payment_intent = Column(String(255))
    
    paid_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    sale = relationship("Sale", foreign_keys=[sale_id])
    case = relationship("Case", foreign_keys=[case_id])



class ClientInformationSheet(Base):
    """Stores client profile information collected by case managers"""
    __tablename__ = "client_information_sheets"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False, unique=True)
    client_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    
    # Personal Info
    full_name = Column(String(255))
    date_of_birth = Column(Date)
    gender = Column(String(20))
    nationality = Column(String(100))
    passport_number = Column(String(50))
    passport_expiry = Column(Date)
    
    # Contact
    phone = Column(String(20))
    email = Column(String(255))
    address = Column(Text)
    city = Column(String(100))
    state = Column(String(100))
    country = Column(String(100))
    postal_code = Column(String(20))
    
    # Education
    highest_education = Column(String(100))
    field_of_study = Column(String(255))
    institution_name = Column(String(255))
    graduation_year = Column(Integer)
    
    # Work Experience
    current_occupation = Column(String(255))
    employer_name = Column(String(255))
    years_of_experience = Column(Integer)
    job_title = Column(String(255))
    
    # Language
    primary_language = Column(String(100))
    english_proficiency = Column(String(50))
    ielts_score = Column(Float)
    other_languages = Column(Text)
    
    # Family
    marital_status = Column(String(50))
    spouse_name = Column(String(255))
    number_of_dependents = Column(Integer)
    
    # Immigration
    previous_visa_refusals = Column(Text)
    previous_travel_history = Column(Text)
    intended_destination = Column(String(255))
    purpose_of_immigration = Column(Text)
    
    # Additional
    additional_notes = Column(Text)
    custom_fields = Column(JSON)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    case = relationship("Case", foreign_keys=[case_id])
    client = relationship("User", foreign_keys=[client_id])
