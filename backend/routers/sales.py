"""Sales Router"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from typing import List, Optional
from core.database import (
    sales_col, sale_documents_col, users_col, products_col,
    cases_col, case_steps_col, workflow_steps_col, notifications_col, audit_logs_col,
    partner_product_commissions_col, settings_col
)
from core.auth import get_current_user, get_password_hash
from core.services import create_notification, notify_role, notify_users, log_activity
from core.email_service import send_sale_approval_email, send_sale_rejection_email
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uuid
import os
import shutil
from datetime import datetime, timezone

router = APIRouter(prefix="/sales", tags=["Sales"])

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "./uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


class SaleApproval(BaseModel):
    sale_id: str
    status: str
    case_manager_id: Optional[str] = None
    notes: Optional[str] = ""
    rejection_reason: Optional[str] = ""


class RecordPayment(BaseModel):
    sale_id: str
    amount: float
    payment_method: str = "cash"
    payment_reference: str = ""
    notes: str = ""


async def _log(user_id, action, entity_type, entity_id=None, details=None):
    await audit_logs_col.insert_one({
        "id": str(uuid.uuid4()), "user_id": user_id, "action": action,
        "entity_type": entity_type, "entity_id": entity_id,
        "new_value": details, "created_at": datetime.now(timezone.utc)
    })


def _serialize_sale(sale):
    s = {k: v for k, v in sale.items() if k != "_id"}
    for f in ["created_at", "approved_at", "collection_deadline"]:
        if isinstance(s.get(f), datetime):
            s[f] = s[f].isoformat()
    fee = s.get("fee_amount", 0) or 0
    received = s.get("amount_received", 0) or 0
    s["pending_amount"] = round(fee - received, 2)
    # Ensure currency fields present
    s.setdefault("original_currency", "INR")
    s.setdefault("exchange_rate_used", 1.0)
    s.setdefault("original_fee_amount", fee)
    s.setdefault("original_amount_received", received)
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
    
    if not sales:
        return sales
    
    # Batch-fetch partners and products to avoid N+1
    partner_ids = list(set(s.get("partner_id") for s in sales if s.get("partner_id")))
    product_ids = list(set(s.get("product_id") for s in sales if s.get("product_id")))
    partners_list = await users_col.find({"id": {"$in": partner_ids}}, {"_id": 0, "password": 0}).to_list(500)
    products_list = await products_col.find({"id": {"$in": product_ids}}, {"_id": 0}).to_list(500)
    partners_map = {p["id"]: p for p in partners_list}
    products_map = {p["id"]: p for p in products_list}
    
    for sale in sales:
        partner = partners_map.get(sale.get("partner_id"))
        product = products_map.get(sale.get("product_id"))
        sale["partner_name"] = partner["name"] if partner else "N/A"
        sale["product_name"] = product["name"] if product else "N/A"
        sale["product_category"] = product.get("category", "N/A") if product else "N/A"
        # Compute pending amount
        fee = sale.get("fee_amount", 0) or 0
        received = sale.get("amount_received", 0) or 0
        sale["pending_amount"] = round(fee - received, 2)
        for f in ["created_at", "approved_at", "collection_deadline"]:
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
    
    if not sales:
        return sales
    
    partner_ids = list(set(s.get("partner_id") for s in sales if s.get("partner_id")))
    product_ids = list(set(s.get("product_id") for s in sales if s.get("product_id")))
    partners_list = await users_col.find({"id": {"$in": partner_ids}}, {"_id": 0, "password": 0}).to_list(500)
    products_list = await products_col.find({"id": {"$in": product_ids}}, {"_id": 0}).to_list(500)
    partners_map = {p["id"]: p for p in partners_list}
    products_map = {p["id"]: p for p in products_list}
    
    for sale in sales:
        partner = partners_map.get(sale.get("partner_id"))
        product = products_map.get(sale.get("product_id"))
        sale["partner_name"] = partner["name"] if partner else "N/A"
        sale["product_name"] = product["name"] if product else "N/A"
        sale["product_category"] = product.get("category", "N/A") if product else "N/A"
        fee = sale.get("fee_amount", 0) or 0
        received = sale.get("amount_received", 0) or 0
        sale["pending_amount"] = round(fee - received, 2)
        for f in ["created_at", "approved_at", "collection_deadline"]:
            if isinstance(sale.get(f), datetime):
                sale[f] = sale[f].isoformat()
    
    return sales


@router.get("/my-sales")
async def get_my_sales(current_user: dict = Depends(get_current_user)):
    """Get sales for current partner"""
    query = {"partner_id": current_user["id"]}
    
    sales = await sales_col.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    
    if not sales:
        return sales
    
    product_ids = list(set(s.get("product_id") for s in sales if s.get("product_id")))
    products_list = await products_col.find({"id": {"$in": product_ids}}, {"_id": 0}).to_list(500)
    products_map = {p["id"]: p for p in products_list}
    
    for sale in sales:
        product = products_map.get(sale.get("product_id"))
        sale["partner_name"] = current_user.get("name", "N/A")
        sale["product_name"] = product["name"] if product else "N/A"
        sale["product_category"] = product.get("category", "N/A") if product else "N/A"
        fee = sale.get("fee_amount", 0) or 0
        received = sale.get("amount_received", 0) or 0
        sale["pending_amount"] = round(fee - received, 2)
        for f in ["created_at", "approved_at", "collection_deadline"]:
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
    collection_deadline: Optional[str] = Form(None),
    agreement_signed: bool = Form(True),
    currency: str = Form("INR"),
    promo_code: Optional[str] = Form(None),
    discount_percentage: Optional[float] = Form(None),
    documents: List[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user)
):
    from core.database import db
    promo_codes_col = db["promo_codes"]

    product = await products_col.find_one({"id": product_id}, {"_id": 0})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # --- Resolve commission rate ---
    if commission_rate is not None:
        rate = commission_rate
    else:
        custom = await partner_product_commissions_col.find_one(
            {"partner_id": current_user["id"], "product_id": product_id}, {"_id": 0}
        )
        if custom:
            rate = custom["commission_rate"]
        elif product.get("commission_rate") is not None and product.get("commission_rate", 0) > 0:
            rate = product["commission_rate"]
        else:
            rate = current_user.get("commission_rate", 0)
    
    # --- Currency conversion to INR ---
    original_currency = currency.upper() if currency else "INR"
    original_fee = fee_amount
    original_received = amount_received or 0
    exchange_rate_used = 1.0

    if original_currency != "INR":
        settings = await settings_col.find_one({"key": "global"}, {"_id": 0})
        default_rates = {"USD": 83.50, "AUD": 55.00, "CAD": 62.00, "GBP": 106.00, "EUR": 91.00}
        rates = settings.get("exchange_rates", default_rates) if settings else default_rates
        exchange_rate_used = rates.get(original_currency, 1.0)
        fee_amount = round(original_fee * exchange_rate_used, 2)
        amount_received_inr = round(original_received * exchange_rate_used, 2)
    else:
        amount_received_inr = original_received

    # --- Promo Code & Discount Calculation ---
    fee_before_discount = fee_amount
    promo_discount_amount = 0.0
    promo_discount_type = None
    promo_discount_value = 0.0
    applied_promo_code = None
    additional_discount_amount = 0.0
    additional_discount_pct = discount_percentage or 0.0

    # Validate and apply promo code
    if promo_code and promo_code.strip():
        code_upper = promo_code.strip().upper()
        promo = await promo_codes_col.find_one({"code": code_upper, "is_active": True}, {"_id": 0})
        if promo:
            if promo.get("current_uses", 0) < promo.get("max_uses", 100):
                promo_discount_type = promo["discount_type"]
                promo_discount_value = promo["discount_value"]
                if promo_discount_type == "percentage":
                    promo_discount_amount = round(fee_amount * (promo_discount_value / 100), 2)
                else:
                    promo_discount_amount = round(min(promo_discount_value, fee_amount), 2)
                applied_promo_code = code_upper
                # Increment promo usage
                await promo_codes_col.update_one({"code": code_upper}, {"$inc": {"current_uses": 1}})

    fee_after_promo = round(fee_amount - promo_discount_amount, 2)

    # Apply additional partner discount
    if additional_discount_pct > 0:
        additional_discount_amount = round(fee_after_promo * (additional_discount_pct / 100), 2)

    final_fee = round(fee_after_promo - additional_discount_amount, 2)
    total_discount = round(promo_discount_amount + additional_discount_amount, 2)

    received = amount_received_inr
    # Commission calculated on amount_received in INR (on final discounted fee basis)
    commission = round(received * (rate / 100), 2) if rate else 0
    pending = round(final_fee - received, 2)

    # Parse collection deadline
    deadline_dt = None
    if collection_deadline:
        try:
            deadline_dt = datetime.fromisoformat(collection_deadline)
        except (ValueError, TypeError):
            pass

    # Determine payment status
    if received >= final_fee:
        pay_status = "paid"
    elif received > 0:
        pay_status = "partial"
    else:
        pay_status = "pending"

    sale = {
        "id": str(uuid.uuid4()), "partner_id": current_user["id"],
        "client_name": client_name, "client_email": client_email,
        "client_mobile": client_mobile, "product_id": product_id,
        "fee_before_discount": fee_before_discount,
        "fee_amount": final_fee, "amount_received": received,
        "pending_amount": pending,
        "original_currency": original_currency,
        "original_fee_amount": original_fee,
        "original_amount_received": original_received,
        "exchange_rate_used": exchange_rate_used,
        # Discount tracking
        "promo_code": applied_promo_code,
        "promo_discount_type": promo_discount_type,
        "promo_discount_value": promo_discount_value,
        "promo_discount_amount": promo_discount_amount,
        "additional_discount_percentage": additional_discount_pct,
        "additional_discount_amount": additional_discount_amount,
        "total_discount_amount": total_discount,
        # Payment & commission
        "payment_method": payment_method, "payment_reference": payment_reference,
        "commission_rate": rate,
        "commission_amount": commission,
        "commission_source": "custom_product" if commission_rate is None and (await partner_product_commissions_col.find_one({"partner_id": current_user["id"], "product_id": product_id})) else ("product_default" if commission_rate is None and product.get("commission_rate", 0) > 0 else "partner_default"),
        "collection_deadline": deadline_dt,
        "agreement_signed": agreement_signed, "status": "pending",
        "payment_status": pay_status,
        "payment_history": [
            {"amount": received, "method": payment_method, "reference": payment_reference,
             "date": datetime.now(timezone.utc).isoformat(), "recorded_by": current_user["id"]}
        ] if received > 0 else [],
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
    
    await _log(current_user["id"], "create_sale", "sale", sale["id"], {"client_name": client_name, "fee_amount": final_fee})
    
    # Build notification message with discount info
    discount_info = ""
    if total_discount > 0:
        discount_parts = []
        if promo_discount_amount > 0:
            discount_parts.append(f"Promo '{applied_promo_code}': -₹{promo_discount_amount:,.0f}")
        if additional_discount_amount > 0:
            discount_parts.append(f"Additional {additional_discount_pct}%: -₹{additional_discount_amount:,.0f}")
        discount_info = f" [Discounts: {', '.join(discount_parts)}]"

    await notify_role("admin", "New Sale Submitted",
        f"Partner {current_user['name']} submitted a sale for {client_name} (₹{final_fee:,.0f}){discount_info}",
        "sale_created", sale["id"])
    await log_activity(current_user["id"], current_user["name"], "created", "sale", sale["id"],
        f"New sale for {client_name} — ₹{final_fee:,.0f}{discount_info}")

    # Notify client as a proposal (email notification)
    from core.email_service import send_email
    proposal_msg = f"Dear {client_name}, a service proposal has been created for you"
    if total_discount > 0:
        proposal_msg += f" with a special discount of ₹{total_discount:,.0f}"
    proposal_msg += f". Total fee: ₹{final_fee:,.0f}. Our team will contact you shortly."
    await send_email(client_email, "Your LEAMSS Service Proposal", proposal_msg, "proposal", sale["id"])

    return {"id": sale["id"], "message": "Sale created successfully", "discount_applied": total_discount > 0, "final_fee": final_fee}


@router.get("/{sale_id}/documents")
async def get_sale_documents(sale_id: str, current_user: dict = Depends(get_current_user)):
    docs = await sale_documents_col.find({"sale_id": sale_id}, {"_id": 0}).to_list(100)
    for d in docs:
        if isinstance(d.get("uploaded_at"), datetime):
            d["uploaded_at"] = d["uploaded_at"].isoformat()
    return docs


@router.get("/document/download/{file_id}")
async def download_sale_document(file_id: str, current_user: dict = Depends(get_current_user)):
    """Download a sale-attached document"""
    doc = await sale_documents_col.find_one({"id": file_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not os.path.exists(doc["file_path"]):
        raise HTTPException(status_code=404, detail="File not found on server")
    
    return FileResponse(
        doc["file_path"],
        filename=doc["filename"],
        media_type=doc.get("content_type", "application/octet-stream")
    )


@router.post("/approve")
async def approve_sale(request: SaleApproval, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    sale = await sales_col.find_one({"id": request.sale_id}, {"_id": 0})
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    
    if request.status == "approved":
        rate = sale.get("commission_rate", 0) or 0
        received = sale.get("amount_received", 0) or 0
        # Commission calculated on amount_received, NOT fee_amount
        commission = round(received * (rate / 100), 2)
        
        await sales_col.update_one({"id": request.sale_id}, {"$set": {
            "status": "approved", "approved_by": current_user["id"],
            "approved_at": datetime.now(timezone.utc),
            "commission_amount": commission,
            "pending_amount": round(sale["fee_amount"] - received, 2)
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
        
        # Create case — case_manager_id is optional (can be assigned later)
        steps = await workflow_steps_col.find({"product_id": sale["product_id"]}, {"_id": 0}).sort("step_order", 1).to_list(100)
        first_step = steps[0]["step_name"] if steps else "Registration"
        
        case_manager_id = request.case_manager_id  # Can be None
        case_number = f"CASE-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:4].upper()}"
        case = {
            "id": str(uuid.uuid4()), "case_id": case_number,
            "sale_id": sale["id"], "client_id": client["id"],
            "product_id": sale["product_id"],
            "case_manager_id": case_manager_id,
            "partner_id": sale["partner_id"],
            "status": "active" if case_manager_id else "pending_assignment",
            "current_step": first_step,
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
        
        # If case manager assigned, notify them too
        if case_manager_id:
            await notifications_col.insert_one({
                "id": str(uuid.uuid4()), "user_id": case_manager_id,
                "title": "New Case Assigned", "message": f"Case {case_number} for {sale['client_name']} has been assigned to you",
                "type": "case_assigned", "related_id": case["id"],
                "read": False, "created_at": datetime.now(timezone.utc)
            })

        await _log(current_user["id"], "sale_approved", "sale", request.sale_id, {"client_name": sale["client_name"]})
        
        # Notify partner that sale was approved
        await create_notification(sale["partner_id"], "Sale Approved",
            f"Your sale for {sale['client_name']} has been approved! Case created.",
            "sale_approved", request.sale_id)
        await log_activity(current_user["id"], current_user["name"], "approved", "sale", request.sale_id,
            f"Approved sale for {sale['client_name']}")
        
        # Email notification to client
        await send_sale_approval_email(
            sale["client_email"], sale["client_name"],
            sale.get("product_name", "Immigration Service"), request.sale_id
        )
        
        response = {"message": "Sale approved successfully", "case_id": case_number}
        if not case_manager_id:
            response["assignment_pending"] = True
            response["message"] = "Sale approved! Case created — please assign a case manager from the Pending Assignment tab."
        if client_is_new:
            response["client_credentials"] = {
                "email": sale["client_email"], "password": client_password,
                "name": sale["client_name"],
                "message": "New client account created. Share these login credentials with the client."
            }
        return response
    
    elif request.status == "rejected":
        reason = request.rejection_reason or request.notes or ""
        if not reason or len(reason.strip()) < 5:
            raise HTTPException(status_code=400, detail="Rejection reason is required (minimum 5 characters)")
        await sales_col.update_one({"id": request.sale_id}, {"$set": {
            "status": "rejected", "rejection_reason": reason.strip(),
            "rejection_notes": reason.strip(), "rejected_by": current_user["id"],
            "rejected_at": datetime.now(timezone.utc)
        }})
        await _log(current_user["id"], "sale_rejected", "sale", request.sale_id, {"client_name": sale["client_name"], "reason": reason.strip()})
        
        # Notify partner that sale was rejected
        await create_notification(sale["partner_id"], "Sale Rejected",
            f"Your sale for {sale['client_name']} was rejected. Reason: {reason.strip()}",
            "sale_rejected", request.sale_id)
        await log_activity(current_user["id"], current_user["name"], "rejected", "sale", request.sale_id,
            f"Rejected sale for {sale['client_name']}: {reason.strip()}")
        
        # Email notification to client
        await send_sale_rejection_email(
            sale["client_email"], sale["client_name"],
            sale.get("product_name", "Immigration Service"), reason.strip(), request.sale_id
        )
        
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
    total_received = sum(s.get("amount_received", 0) for s in approved)
    total_pending = sum(s.get("pending_amount", s["fee_amount"] - s.get("amount_received", 0)) for s in approved)
    commission = sum(s.get("commission_amount", 0) for s in approved)
    
    # Batch fetch partners and products
    partner_ids = list(set(s.get("partner_id") for s in sales if s.get("partner_id")))
    product_ids = list(set(s.get("product_id") for s in sales if s.get("product_id")))
    partners_list = await users_col.find({"id": {"$in": partner_ids}}, {"_id": 0, "password": 0}).to_list(500) if partner_ids else []
    products_list = await products_col.find({"id": {"$in": product_ids}}, {"_id": 0}).to_list(500) if product_ids else []
    partners_map = {p["id"]: p for p in partners_list}
    products_map = {p["id"]: p for p in products_list}
    
    sales_data = []
    for s in sales:
        partner = partners_map.get(s.get("partner_id"))
        product = products_map.get(s.get("product_id"))
        sd = {
            "id": s["id"], "client_name": s["client_name"], "client_email": s["client_email"],
            "partner_name": partner["name"] if partner else "N/A",
            "product_name": product["name"] if product else "N/A",
            "product_category": product.get("category", "N/A") if product else "N/A",
            "fee_amount": s["fee_amount"],
            "amount_received": s.get("amount_received", 0),
            "pending_amount": round(s["fee_amount"] - s.get("amount_received", 0), 2),
            "commission_amount": s.get("commission_amount", 0),
            "commission_rate": s.get("commission_rate", 0), "status": s["status"],
            "rejection_reason": s.get("rejection_reason", ""),
            "payment_method": s.get("payment_method", ""), "payment_reference": s.get("payment_reference", ""),
            "payment_status": s.get("payment_status", "pending"),
            "date": s.get("created_at", "").isoformat() if isinstance(s.get("created_at"), datetime) else str(s.get("created_at", ""))
        }
        sales_data.append(sd)
    
    return {
        "total_sales": total, "approved_sales": len(approved),
        "total_revenue": revenue, "total_received": total_received,
        "total_pending": total_pending, "total_commission": commission,
        "sales": sales_data, "partner_breakdown": []
    }


@router.get("/stats")
async def get_sales_stats(current_user: dict = Depends(get_current_user)):
    total = await sales_col.count_documents({})
    pending = await sales_col.count_documents({"status": "pending"})
    approved = await sales_col.count_documents({"status": "approved"})
    rejected = await sales_col.count_documents({"status": "rejected"})
    
    approved_sales = await sales_col.find({"status": "approved"}, {"_id": 0}).to_list(1000)
    revenue = sum(s["fee_amount"] for s in approved_sales)
    total_received = sum(s.get("amount_received", 0) for s in approved_sales)
    total_pending_amount = round(revenue - total_received, 2)
    commission = sum(s.get("commission_amount", 0) for s in approved_sales)
    
    return {
        "total_sales": total, "pending_sales": pending,
        "approved_sales": approved, "rejected_sales": rejected,
        "total_revenue": revenue, "total_received": total_received,
        "total_pending_amount": total_pending_amount,
        "total_commission": commission
    }


@router.post("/record-payment")
async def record_payment(data: RecordPayment, current_user: dict = Depends(get_current_user)):
    """Record an additional payment against a sale"""
    if current_user["role"] not in ["admin", "partner"]:
        raise HTTPException(status_code=403, detail="Admin or Partner only")
    
    sale = await sales_col.find_one({"id": data.sale_id}, {"_id": 0})
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    
    if data.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    
    old_received = sale.get("amount_received", 0) or 0
    new_received = round(old_received + data.amount, 2)
    fee = sale.get("fee_amount", 0)
    new_pending = round(fee - new_received, 2)
    
    # Recalculate commission on new amount received
    rate = sale.get("commission_rate", 0) or 0
    new_commission = round(new_received * (rate / 100), 2) if rate else 0
    
    # Determine payment status
    if new_received >= fee:
        pay_status = "paid"
    else:
        pay_status = "partial"
    
    payment_entry = {
        "amount": data.amount, "method": data.payment_method,
        "reference": data.payment_reference, "notes": data.notes,
        "date": datetime.now(timezone.utc).isoformat(),
        "recorded_by": current_user["id"]
    }
    
    await sales_col.update_one({"id": data.sale_id}, {
        "$set": {
            "amount_received": new_received,
            "pending_amount": new_pending,
            "commission_amount": new_commission,
            "payment_status": pay_status
        },
        "$push": {"payment_history": payment_entry}
    })
    
    await _log(current_user["id"], "record_payment", "sale", data.sale_id, {
        "amount": data.amount, "new_total_received": new_received, "new_commission": new_commission
    })
    
    return {
        "message": "Payment recorded successfully",
        "amount_received": new_received,
        "pending_amount": new_pending,
        "commission_amount": new_commission,
        "payment_status": pay_status
    }


@router.get("/tracker/payment-deadlines")
async def get_payment_deadlines(current_user: dict = Depends(get_current_user)):
    """Get sales with payment deadlines for the collection tracker widget"""
    if current_user["role"] not in ["admin", "case_manager", "partner"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    query = {"payment_status": {"$in": ["pending", "partial"]}}
    if current_user["role"] == "partner":
        query["partner_id"] = current_user["id"]
    
    sales = await sales_col.find(query, {"_id": 0}).sort("collection_deadline", 1).to_list(200)
    
    now = datetime.now(timezone.utc)
    result = []
    for sale in sales:
        fee = sale.get("fee_amount", 0) or 0
        received = sale.get("amount_received", 0) or 0
        pending = round(fee - received, 2)
        
        if pending <= 0:
            continue
        
        deadline = sale.get("collection_deadline")
        urgency = "upcoming"  # green
        days_until = None
        
        if deadline:
            if isinstance(deadline, str):
                try:
                    deadline = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    deadline = None
            
            if deadline:
                # Ensure both datetimes are timezone-aware
                if deadline.tzinfo is None:
                    deadline = deadline.replace(tzinfo=timezone.utc)
                delta = (deadline - now).days
                days_until = delta
                if delta < 0:
                    urgency = "overdue"  # red
                elif delta <= 7:
                    urgency = "due_soon"  # amber
        
        partner = await users_col.find_one({"id": sale.get("partner_id")}, {"_id": 0, "password": 0})
        
        result.append({
            "sale_id": sale["id"],
            "client_name": sale.get("client_name", "N/A"),
            "client_email": sale.get("client_email", ""),
            "partner_name": partner["name"] if partner else "N/A",
            "fee_amount": fee,
            "amount_received": received,
            "pending_amount": pending,
            "collection_deadline": deadline.isoformat() if isinstance(deadline, datetime) else sale.get("collection_deadline"),
            "days_until_deadline": days_until,
            "urgency": urgency,
            "payment_status": sale.get("payment_status", "pending"),
            "created_at": sale.get("created_at").isoformat() if isinstance(sale.get("created_at"), datetime) else str(sale.get("created_at", ""))
        })
    
    # Sort: overdue first, then due_soon, then upcoming
    urgency_order = {"overdue": 0, "due_soon": 1, "upcoming": 2}
    result.sort(key=lambda x: urgency_order.get(x["urgency"], 3))
    
    summary = {
        "total_pending": sum(r["pending_amount"] for r in result),
        "overdue_count": len([r for r in result if r["urgency"] == "overdue"]),
        "overdue_amount": sum(r["pending_amount"] for r in result if r["urgency"] == "overdue"),
        "due_soon_count": len([r for r in result if r["urgency"] == "due_soon"]),
        "due_soon_amount": sum(r["pending_amount"] for r in result if r["urgency"] == "due_soon"),
        "upcoming_count": len([r for r in result if r["urgency"] == "upcoming"]),
        "upcoming_amount": sum(r["pending_amount"] for r in result if r["urgency"] == "upcoming")
    }
    
    return {"summary": summary, "items": result}


@router.get("/{sale_id}")
async def get_sale_detail(sale_id: str, current_user: dict = Depends(get_current_user)):
    """Get single sale with full details"""
    sale = await sales_col.find_one({"id": sale_id}, {"_id": 0})
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    
    partner = await users_col.find_one({"id": sale.get("partner_id")}, {"_id": 0, "password": 0})
    product = await products_col.find_one({"id": sale.get("product_id")}, {"_id": 0})
    sale["partner_name"] = partner["name"] if partner else "N/A"
    sale["product_name"] = product["name"] if product else "N/A"
    sale["product_category"] = product.get("category", "N/A") if product else "N/A"
    
    fee = sale.get("fee_amount", 0) or 0
    received = sale.get("amount_received", 0) or 0
    sale["pending_amount"] = round(fee - received, 2)
    
    for f in ["created_at", "approved_at", "rejected_at", "collection_deadline"]:
        if isinstance(sale.get(f), datetime):
            sale[f] = sale[f].isoformat()
    
    return sale
