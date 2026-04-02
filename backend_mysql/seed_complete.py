import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.database import sync_engine
from core.models import (
    User, UserRole, UserStatus, 
    Product, WorkflowStep, DocumentRequirement, CommissionType,
    Sale, SaleStatus,
    Case, CaseStatus, CaseStep, StepStatus,
    Ticket, TicketMessage, TicketAttachment, TicketActivityLog, TicketTarget,
    Document, Notification,
    SystemSetting
)
from sqlalchemy.orm import Session
from sqlalchemy import text
from passlib.context import CryptContext
import uuid
from datetime import datetime, timedelta

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

with Session(sync_engine) as session:
    
    # ============ DISABLE FOREIGN KEY CHECKS ============
    print("Disabling foreign key checks...")
    session.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
    
    # ============ CLEAR ALL TABLES ============
    print("Clearing all existing data...")
    
    tables_to_clear = [
        "ticket_activity_log",
        "ticket_attachments", 
        "ticket_messages",
        "ticket_targets",
        "tickets",
        "documents",
        "notifications",
        "case_steps",
        "cases",
        "sales",
        "document_requirements",
        "workflow_steps",
        "products",
        "system_settings",
        "users"
    ]
    
    for table in tables_to_clear:
        try:
            session.execute(text(f"DELETE FROM {table}"))
            print(f"  Cleared: {table}")
        except Exception as e:
            print(f"  Skipped: {table} ({e})")
    
    session.commit()
    
    # ============ RE-ENABLE FOREIGN KEY CHECKS ============
    session.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
    print("Foreign key checks re-enabled.")
    print("")
    
    # ============ CREATE USERS ============
    print("Creating users...")
    
    admin = User(
        id=str(uuid.uuid4()),
        email="admin@leamss.com",
        password=get_password_hash("Admin@123"),
        name="Admin User",
        role=UserRole.admin,
        status=UserStatus.active
    )
    session.add(admin)
    
    manager = User(
        id=str(uuid.uuid4()),
        email="manager@leamss.com",
        password=get_password_hash("Manager@123"),
        name="Case Manager",
        role=UserRole.case_manager,
        status=UserStatus.active
    )
    session.add(manager)
    
    partner = User(
        id=str(uuid.uuid4()),
        email="partner@leamss.com",
        password=get_password_hash("Partner@123"),
        name="Partner User",
        role=UserRole.partner,
        status=UserStatus.active,
        commission_rate=10.0
    )
    session.add(partner)
    
    client = User(
        id=str(uuid.uuid4()),
        email="client@leamss.com",
        password=get_password_hash("Client@123"),
        name="Client User",
        role=UserRole.client,
        status=UserStatus.active
    )
    session.add(client)
    
    client2 = User(
        id=str(uuid.uuid4()),
        email="client2@leamss.com",
        password=get_password_hash("Client@123"),
        name="Jane Smith",
        role=UserRole.client,
        status=UserStatus.active
    )
    session.add(client2)
    
    session.flush()
    print("  Created 5 users")
    
    # ============ CREATE PRODUCTS WITH WORKFLOW ============
    print("Creating products with workflow steps...")
    
    # Product 1: Australia PR
    product1 = Product(
        id=str(uuid.uuid4()),
        name="Australia PR - Permanent Residency",
        description="Complete assistance for Australia Permanent Residency visa application including skills assessment, EOI, and visa lodgement.",
        fee=150000.00,
        commission_rate=10.0,
        commission_type=CommissionType.percentage,
        status="active"
    )
    session.add(product1)
    session.flush()
    
    steps_data = [
        ("Registration", 1, "Initial registration and document collection", 7),
        ("Document Collection", 2, "Collect all required documents from client", 14),
        ("Skills Assessment", 3, "Skills assessment submission and processing", 30),
        ("EOI Submission", 4, "Expression of Interest submission", 7),
        ("ITA Received", 5, "Invitation to Apply received", 60),
        ("Visa Application", 6, "Final visa application submission", 14),
        ("Medical & PCC", 7, "Medical examination and Police Clearance Certificate", 21),
        ("Visa Grant", 8, "Visa granted - Process complete", 90),
    ]
    
    workflow_steps_product1 = []
    for step_name, order, desc, days in steps_data:
        step = WorkflowStep(
            id=str(uuid.uuid4()),
            product_id=product1.id,
            step_name=step_name,
            step_order=order,
            description=desc,
            duration_days=days
        )
        session.add(step)
        workflow_steps_product1.append(step)
    
    session.flush()
    
    doc_requirements = [
        (workflow_steps_product1[0].id, "Passport Copy", True, "Clear scanned copy of passport bio page"),
        (workflow_steps_product1[0].id, "Photograph", True, "Recent passport size photograph"),
        (workflow_steps_product1[1].id, "Education Certificates", True, "All education certificates and transcripts"),
        (workflow_steps_product1[1].id, "Work Experience Letters", True, "Experience letters from all employers"),
        (workflow_steps_product1[2].id, "Skills Assessment Result", True, "Positive skills assessment outcome"),
        (workflow_steps_product1[6].id, "Medical Report", True, "HAP ID and medical examination results"),
        (workflow_steps_product1[6].id, "Police Clearance", True, "Police clearance certificate from all countries"),
    ]
    
    for workflow_step_id, doc_name, mandatory, desc in doc_requirements:
        doc_req = DocumentRequirement(
            id=str(uuid.uuid4()),
            workflow_step_id=workflow_step_id,
            doc_name=doc_name,
            is_mandatory=mandatory,
            description=desc
        )
        session.add(doc_req)
    
    # Product 2: Canada PR
    product2 = Product(
        id=str(uuid.uuid4()),
        name="Canada PR - Express Entry",
        description="Canada Permanent Residency through Express Entry program including profile creation and application.",
        fee=120000.00,
        commission_rate=12.0,
        commission_type=CommissionType.percentage,
        status="active"
    )
    session.add(product2)
    session.flush()
    
    canada_steps = [
        ("Profile Creation", 1, "Create Express Entry profile", 7),
        ("Document Preparation", 2, "Prepare all required documents", 21),
        ("ECA Assessment", 3, "Educational Credential Assessment", 45),
        ("IELTS/Language Test", 4, "Language proficiency test", 30),
        ("ITA Wait", 5, "Waiting for Invitation to Apply", 90),
        ("Application Submit", 6, "Submit PR application", 14),
        ("Biometrics", 7, "Biometrics collection", 30),
        ("PR Approval", 8, "PR visa approved", 120),
    ]
    
    for step_name, order, desc, days in canada_steps:
        step = WorkflowStep(
            id=str(uuid.uuid4()),
            product_id=product2.id,
            step_name=step_name,
            step_order=order,
            description=desc,
            duration_days=days
        )
        session.add(step)
    
    # Product 3: UK Visit Visa
    product3 = Product(
        id=str(uuid.uuid4()),
        name="UK Visit Visa",
        description="UK Standard Visitor Visa for tourism, business, or family visits.",
        fee=25000.00,
        commission_rate=15.0,
        commission_type=CommissionType.fixed,
        status="active"
    )
    session.add(product3)
    
    session.flush()
    print("  Created 3 products with workflow steps")
    
    # ============ CREATE SAMPLE SALES ============
    print("Creating sample sales...")
    
    sale1 = Sale(
        id=str(uuid.uuid4()),
        partner_id=partner.id,
        product_id=product1.id,
        client_name="John Doe",
        client_email="john.doe@email.com",
        client_mobile="+91 9876543210",
        fee_amount=150000.00,
        commission_amount=15000.00,
        status=SaleStatus.approved,
        approved_by=admin.id,
        approved_at=datetime.utcnow() - timedelta(days=5)
    )
    session.add(sale1)
    
    sale2 = Sale(
        id=str(uuid.uuid4()),
        partner_id=partner.id,
        product_id=product2.id,
        client_name="Jane Smith",
        client_email="jane.smith@email.com",
        client_mobile="+91 9876543211",
        fee_amount=120000.00,
        commission_amount=14400.00,
        status=SaleStatus.pending
    )
    session.add(sale2)
    
    session.flush()
    print("  Created 2 sales (1 approved, 1 pending)")
    
    # ============ CREATE SAMPLE CASE ============
    print("Creating sample case...")
    
    case1 = Case(
        id=str(uuid.uuid4()),
        case_id="LEAMSS-2024-0001",
        sale_id=sale1.id,
        product_id=product1.id,
        client_id=client.id,
        partner_id=partner.id,
        case_manager_id=manager.id,
        status=CaseStatus.active,
        current_step="Document Collection",
        current_step_order=2,
        notes="Client referred by existing customer"
    )
    session.add(case1)
    session.flush()
    
    for i, ws in enumerate(workflow_steps_product1):
        if i == 0:
            status = StepStatus.completed
            started = datetime.utcnow() - timedelta(days=30)
            completed = datetime.utcnow() - timedelta(days=23)
        elif i == 1:
            status = StepStatus.in_progress
            started = datetime.utcnow() - timedelta(days=23)
            completed = None
        else:
            status = StepStatus.locked
            started = None
            completed = None
            
        case_step = CaseStep(
            id=str(uuid.uuid4()),
            case_id=case1.id,
            step_id=ws.id,
            step_order=i + 1,
            status=status,
            started_at=started,
            completed_at=completed
        )
        session.add(case_step)
    
    print("  Created 1 case with 8 workflow steps")
    
    # ============ CREATE SAMPLE TICKET ============
    print("Creating sample ticket...")
    
    ticket = Ticket(
        id=str(uuid.uuid4()),
        ticket_number="TKT-2024-0001",
        subject="Document clarification needed",
        description="I need clarification on which format is acceptable for the passport copy.",
        category="document",
        priority="medium",
        status="open",
        created_by=client.id,
        target_role="case_manager"
    )
    session.add(ticket)
    session.flush()
    
    ticket_msg = TicketMessage(
        id=str(uuid.uuid4()),
        ticket_id=ticket.id,
        user_id=client.id,
        message="Please let me know if PDF format is acceptable or do I need to upload JPG?",
        is_internal=False
    )
    session.add(ticket_msg)
    print("  Created 1 ticket with message")
    
    # ============ CREATE NOTIFICATIONS ============
    print("Creating sample notifications...")
    
    notifications = [
        (client.id, "Welcome to LEAMSS Portal", "Your account has been created successfully.", "info"),
        (client.id, "Document Required", "Please upload your passport copy.", "warning"),
        (manager.id, "New Case Assigned", "A new case LEAMSS-2024-0001 has been assigned to you.", "info"),
        (partner.id, "Sale Approved", "Your sale for John Doe has been approved.", "success"),
        (admin.id, "New Sale Pending", "A new sale from Partner User is pending approval.", "info"),
    ]
    
    for user_id, title, message, ntype in notifications:
        notif = Notification(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=title,
            message=message,
            type=ntype,
            is_read=False
        )
        session.add(notif)
    
    print("  Created 5 notifications")
    
    # ============ CREATE SYSTEM SETTINGS ============
    print("Creating system settings...")
    
    settings = [
        ("allow_case_manager_workflow_customization", "true", "boolean", "Allow case managers to customize workflow"),
        ("default_commission_rate", "10", "number", "Default commission rate for partners"),
        ("notification_email_enabled", "true", "boolean", "Enable email notifications"),
        ("max_file_upload_size", "10485760", "number", "Maximum file upload size in bytes (10MB)"),
    ]
    
    for key, value, stype, desc in settings:
        setting = SystemSetting(
            id=str(uuid.uuid4()),
            setting_key=key,
            setting_value=value,
            setting_type=stype,
            description=desc
        )
        session.add(setting)
    
    print("  Created 4 system settings")
    
    # ============ COMMIT ALL ============
    session.commit()
    
    print("")
    print("=" * 65)
    print("✅ COMPLETE DATABASE SEEDED SUCCESSFULLY!")
    print("=" * 65)
    print("")
    print("Summary:")
    print("  • 5 Users (Admin, Case Manager, Partner, 2 Clients)")
    print("  • 3 Products with Workflow Steps & Document Requirements")
    print("  • 2 Sales (1 Approved, 1 Pending)")
    print("  • 1 Active Case with Progress")
    print("  • 1 Support Ticket")
    print("  • 5 Notifications")
    print("  • 4 System Settings")
    print("")
    print("Login Credentials:")
    print("-" * 65)
    print("Admin:        admin@leamss.com      / Admin@123")
    print("Case Manager: manager@leamss.com    / Manager@123")
    print("Partner:      partner@leamss.com    / Partner@123")
    print("Client:       client@leamss.com     / Client@123")
    print("Client 2:     client2@leamss.com    / Client@123")
    print("-" * 65)
