"""Phase 10: Admin Superpowers Router
- 10A: Unified Approval Center
- 10B: Refund Manager (Enhanced)
- 10C: Revenue Dashboard Enhanced
- 10D: Custom Report Builder
"""
import uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from core.database import (
    db, sales_col, cases_col, users_col, products_col,
    refunds_col, audit_logs_col, documents_col, tickets_col,
    pre_assessments_col, notifications_col
)
from core.auth import get_current_user

router = APIRouter(prefix="/admin-super", tags=["Admin Superpowers"])

payment_transactions_col = db["payment_transactions"]


def serialize_datetime(obj):
    """Helper to convert datetime fields to ISO strings"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj


def serialize_doc(doc):
    """Serialize a MongoDB document, converting datetimes"""
    if not doc:
        return doc
    result = {}
    for k, v in doc.items():
        if k == "_id":
            continue
        if isinstance(v, datetime):
            result[k] = v.isoformat()
        else:
            result[k] = v
    return result


# ===================== 10A: UNIFIED APPROVAL CENTER =====================

@router.get("/approval-center")
async def get_approval_center(current_user: dict = Depends(get_current_user)):
    """Get all pending items that need admin approval"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    # 1. Pending Sales
    pending_sales_raw = await sales_col.find(
        {"status": "pending"}, {"_id": 0}
    ).sort("created_at", -1).to_list(200)

    pending_sales = []
    for s in pending_sales_raw:
        partner = await users_col.find_one({"id": s.get("partner_id")}, {"_id": 0, "name": 1})
        product = await products_col.find_one({"id": s.get("product_id")}, {"_id": 0, "name": 1})
        pending_sales.append({
            "id": s["id"],
            "type": "sale",
            "title": f"Sale: {s.get('client_name', 'N/A')}",
            "subtitle": f"{product['name'] if product else 'Unknown'} - {partner['name'] if partner else 'Unknown'}",
            "amount": s.get("fee_amount", 0),
            "client_name": s.get("client_name", ""),
            "client_email": s.get("client_email", ""),
            "partner_name": partner["name"] if partner else "Unknown",
            "product_name": product["name"] if product else "Unknown",
            "created_at": serialize_datetime(s.get("created_at")),
            "priority": "high" if s.get("fee_amount", 0) > 100000 else "medium",
        })

    # 2. Pre-Assessments under review
    pa_items_raw = await pre_assessments_col.find(
        {"stage": {"$in": ["under_review", "documents_submitted"]}}, {"_id": 0}
    ).sort("submitted_at", -1).to_list(200)

    pending_pa = []
    for pa in pa_items_raw:
        pending_pa.append({
            "id": pa["id"],
            "type": "pre_assessment",
            "title": f"Pre-Assessment: {pa.get('client_name', 'N/A')}",
            "subtitle": f"{pa.get('country', '')} - {pa.get('service_type', '')} | Partner: {pa.get('partner_name', '')}",
            "amount": pa.get("pre_assessment_fee", 5100),
            "client_name": pa.get("client_name", ""),
            "client_email": pa.get("client_email", ""),
            "partner_name": pa.get("partner_name", ""),
            "product_name": pa.get("product_name", ""),
            "pa_number": pa.get("pa_number", ""),
            "country": pa.get("country", ""),
            "service_type": pa.get("service_type", ""),
            "created_at": serialize_datetime(pa.get("created_at")),
            "submitted_at": serialize_datetime(pa.get("submitted_at")),
            "priority": "high",
        })

    # 3. Pending document verifications
    pending_docs_raw = await documents_col.find(
        {"status": "pending"}, {"_id": 0}
    ).sort("created_at", -1).to_list(200)

    pending_docs = []
    for d in pending_docs_raw:
        case = await cases_col.find_one({"id": d.get("case_id")}, {"_id": 0, "case_id": 1, "client_name": 1})
        pending_docs.append({
            "id": d.get("id", ""),
            "type": "document",
            "title": f"Document: {d.get('filename', d.get('document_type', 'Unknown'))}",
            "subtitle": f"Case: {case['case_id'] if case else 'N/A'} - {case.get('client_name', '') if case else ''}",
            "case_id": d.get("case_id", ""),
            "case_display_id": case["case_id"] if case else "N/A",
            "client_name": case.get("client_name", "") if case else "",
            "document_type": d.get("document_type", d.get("step_name", "")),
            "filename": d.get("filename", ""),
            "created_at": serialize_datetime(d.get("created_at")),
            "priority": "low",
        })

    # 4. Open tickets (urgent/high only)
    urgent_tickets_raw = await tickets_col.find(
        {"status": {"$in": ["open"]}, "priority": {"$in": ["urgent", "high"]}}, {"_id": 0}
    ).sort("created_at", -1).to_list(50)

    urgent_tickets = []
    for t in urgent_tickets_raw:
        urgent_tickets.append({
            "id": t.get("id", ""),
            "type": "ticket",
            "title": f"Ticket: {t.get('subject', 'N/A')}",
            "subtitle": f"Priority: {t.get('priority', 'N/A')} - By: {t.get('created_by_name', 'Unknown')}",
            "priority": t.get("priority", "medium"),
            "created_at": serialize_datetime(t.get("created_at")),
        })

    all_items = pending_sales + pending_pa + pending_docs + urgent_tickets

    return {
        "items": all_items,
        "summary": {
            "pending_sales": len(pending_sales),
            "pending_pre_assessments": len(pending_pa),
            "pending_documents": len(pending_docs),
            "urgent_tickets": len(urgent_tickets),
            "total": len(all_items),
        }
    }


class QuickApproveRequest(BaseModel):
    item_id: str
    item_type: str  # "sale", "pre_assessment", "document"
    action: str  # "approve", "reject"
    notes: str = ""
    case_manager_id: str = ""


@router.post("/approval-center/action")
async def quick_approval_action(data: QuickApproveRequest, current_user: dict = Depends(get_current_user)):
    """Quick approve/reject from the unified approval center"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    if data.item_type == "sale":
        from routers.sales import sales_col as s_col
        from core.database import workflow_steps_col, case_steps_col
        from core.auth import get_password_hash
        from core.services import log_activity, create_notification
        from core.email_service import send_sale_approval_email, send_sale_rejection_email

        sale = await sales_col.find_one({"id": data.item_id}, {"_id": 0})
        if not sale:
            raise HTTPException(status_code=404, detail="Sale not found")

        if data.action == "approve":
            rate = sale.get("commission_rate", 0) or 0
            received = sale.get("amount_received", 0) or 0
            commission = round(received * (rate / 100), 2)

            await sales_col.update_one({"id": data.item_id}, {"$set": {
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

            # Create case
            steps = await workflow_steps_col.find({"product_id": sale["product_id"]}, {"_id": 0}).sort("step_order", 1).to_list(100)
            first_step = steps[0]["step_name"] if steps else "Registration"
            case_manager_id = data.case_manager_id or None
            case_number = f"CASE-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:4].upper()}"
            case = {
                "id": str(uuid.uuid4()), "case_id": case_number,
                "sale_id": sale["id"], "client_id": client["id"],
                "product_id": sale["product_id"],
                "case_manager_id": case_manager_id,
                "partner_id": sale.get("partner_id"),
                "status": "active" if case_manager_id else "pending_assignment",
                "current_step": first_step, "current_step_order": 1,
                "created_at": datetime.now(timezone.utc)
            }
            await cases_col.insert_one(case)
            for step in steps:
                await case_steps_col.insert_one({
                    "id": str(uuid.uuid4()), "case_id": case["id"],
                    "step_name": step["step_name"], "step_order": step["step_order"],
                    "status": "pending", "description": step.get("description", ""),
                    "required_documents": step.get("required_documents", []),
                    "created_at": datetime.now(timezone.utc)
                })

            await notifications_col.insert_one({
                "id": str(uuid.uuid4()), "user_id": client["id"],
                "title": "Case Created", "message": f"Your case {case_number} has been created",
                "type": "case_created", "related_id": case["id"],
                "read": False, "created_at": datetime.now(timezone.utc)
            })
            if case_manager_id:
                await notifications_col.insert_one({
                    "id": str(uuid.uuid4()), "user_id": case_manager_id,
                    "title": "New Case Assigned", "message": f"Case {case_number} for {sale['client_name']}",
                    "type": "case_assigned", "read": False, "created_at": datetime.now(timezone.utc)
                })

            await audit_logs_col.insert_one({
                "id": str(uuid.uuid4()), "user_id": current_user["id"],
                "action": "sale_approved_via_approval_center", "entity_type": "sale",
                "entity_id": data.item_id, "new_value": {"client": sale["client_name"], "case": case_number, "notes": data.notes},
                "created_at": datetime.now(timezone.utc)
            })

            try:
                await send_sale_approval_email(sale["client_email"], sale["client_name"], sale.get("product_name", ""), data.item_id)
            except Exception:
                pass

            result = {"message": "Sale approved", "case_id": case_number}
            if not case_manager_id:
                result["assignment_pending"] = True
            if client_is_new:
                result["client_credentials"] = {"email": sale["client_email"], "password": client_password, "name": sale["client_name"]}
            return result

        else:
            if not data.notes or len(data.notes.strip()) < 5:
                raise HTTPException(status_code=400, detail="Rejection reason required (min 5 chars)")
            await sales_col.update_one({"id": data.item_id}, {"$set": {
                "status": "rejected", "rejection_reason": data.notes.strip(),
                "approved_by": current_user["id"], "approved_at": datetime.now(timezone.utc)
            }})
            await audit_logs_col.insert_one({
                "id": str(uuid.uuid4()), "user_id": current_user["id"],
                "action": "sale_rejected", "entity_type": "sale",
                "entity_id": data.item_id, "new_value": {"reason": data.notes},
                "created_at": datetime.now(timezone.utc)
            })
            try:
                await send_sale_rejection_email(sale["client_email"], sale["client_name"], sale.get("product_name", ""), data.notes)
            except Exception:
                pass
            return {"message": "Sale rejected"}

    elif data.item_type == "pre_assessment":
        pa = await pre_assessments_col.find_one({"id": data.item_id}, {"_id": 0})
        if not pa:
            raise HTTPException(status_code=404, detail="Pre-assessment not found")

        new_stage = "approved" if data.action == "approve" else "rejected"
        await pre_assessments_col.update_one({"id": data.item_id}, {"$set": {
            "stage": new_stage,
            "admin_decision": data.action + "d",
            "admin_reason": data.notes,
            "admin_reviewed_by": current_user["id"],
            "admin_reviewed_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }})
        # Notify partner
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()), "user_id": pa["partner_id"],
            "title": f"Pre-Assessment {new_stage.title()}",
            "message": f"{pa['client_name']}: {new_stage.upper()}. {data.notes}",
            "type": "pre_assessment_decision", "read": False,
            "created_at": datetime.now(timezone.utc)
        })
        if data.action == "reject":
            await pre_assessments_col.update_one({"id": data.item_id}, {"$set": {"stage": "refund_initiated"}})

        return {"message": f"Pre-assessment {new_stage}"}

    elif data.item_type == "document":
        doc = await documents_col.find_one({"id": data.item_id}, {"_id": 0})
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        new_status = "verified" if data.action == "approve" else "rejected"
        await documents_col.update_one({"id": data.item_id}, {"$set": {
            "status": new_status,
            "verified_by": current_user["id"],
            "verified_at": datetime.now(timezone.utc),
            "rejection_reason": data.notes if data.action == "reject" else ""
        }})
        return {"message": f"Document {new_status}"}

    else:
        raise HTTPException(status_code=400, detail="Invalid item type")



# --- Client-wise Progressive View ---
@router.get("/approval-center/client-pipeline")
async def get_client_pipeline(current_user: dict = Depends(get_current_user)):
    """Get client-wise progressive pipeline: PA → Sale → Case → CM Assignment"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    # Get all case managers for assignment dropdown
    cms = await users_col.find({"role": "case_manager", "status": "active"}, {"_id": 0, "id": 1, "name": 1, "email": 1}).to_list(50)

    # Build client pipeline by email
    pipeline = {}

    # 1. Pre-assessments
    all_pa = await pre_assessments_col.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    for pa in all_pa:
        email = pa.get("client_email", "")
        if not email:
            continue
        if email not in pipeline:
            pipeline[email] = {
                "client_name": pa.get("client_name", ""),
                "client_email": email,
                "client_mobile": pa.get("client_mobile", ""),
                "partner_name": pa.get("partner_name", ""),
                "partner_id": pa.get("partner_id", ""),
                "pre_assessments": [],
                "sales": [],
                "cases": [],
                "documents": [],
            }
        pipeline[email]["pre_assessments"].append({
            "id": pa["id"],
            "pa_number": pa.get("pa_number", ""),
            "stage": pa.get("stage", ""),
            "country": pa.get("country", ""),
            "service_type": pa.get("service_type", ""),
            "fee_payment_status": pa.get("fee_payment_status", ""),
            "admin_decision": pa.get("admin_decision", ""),
            "admin_reason": pa.get("admin_reason", ""),
            "created_at": serialize_datetime(pa.get("created_at")),
            "submitted_at": serialize_datetime(pa.get("submitted_at")),
            "uploaded_documents": pa.get("uploaded_documents", []),
        })

    # 2. Sales
    all_sales_data = await sales_col.find({}, {"_id": 0}).sort("created_at", -1).to_list(2000)
    for s in all_sales_data:
        email = s.get("client_email", "")
        if not email:
            continue
        if email not in pipeline:
            partner = await users_col.find_one({"id": s.get("partner_id")}, {"_id": 0, "name": 1})
            pipeline[email] = {
                "client_name": s.get("client_name", ""),
                "client_email": email,
                "client_mobile": s.get("client_mobile", ""),
                "partner_name": partner["name"] if partner else s.get("partner_name", ""),
                "partner_id": s.get("partner_id", ""),
                "pre_assessments": [],
                "sales": [],
                "cases": [],
                "documents": [],
            }
        product = await products_col.find_one({"id": s.get("product_id")}, {"_id": 0, "name": 1})
        pipeline[email]["sales"].append({
            "id": s["id"],
            "status": s.get("status", ""),
            "product_name": product["name"] if product else s.get("product_name", ""),
            "product_id": s.get("product_id", ""),
            "fee_amount": s.get("fee_amount", 0),
            "amount_received": s.get("amount_received", 0),
            "payment_method": s.get("payment_method", ""),
            "rejection_reason": s.get("rejection_reason", ""),
            "created_at": serialize_datetime(s.get("created_at")),
        })

    # 3. Cases
    all_cases_data = await cases_col.find({}, {"_id": 0}).sort("created_at", -1).to_list(2000)
    for c in all_cases_data:
        client = await users_col.find_one({"id": c.get("client_id")}, {"_id": 0, "email": 1})
        if not client:
            continue
        email = client.get("email", "")
        if email in pipeline:
            cm = await users_col.find_one({"id": c.get("case_manager_id")}, {"_id": 0, "name": 1})
            pipeline[email]["cases"].append({
                "id": c["id"],
                "case_id": c.get("case_id", ""),
                "status": c.get("status", ""),
                "case_manager_id": c.get("case_manager_id"),
                "case_manager_name": cm["name"] if cm else None,
                "current_step": c.get("current_step", ""),
                "product_name": c.get("product_name", ""),
                "created_at": serialize_datetime(c.get("created_at")),
            })

    # 4. Add pending docs per client
    for email, data_item in pipeline.items():
        for s in data_item["sales"]:
            docs = await documents_col.find(
                {"case_id": {"$in": [c["id"] for c in data_item["cases"]]}}, {"_id": 0}
            ).to_list(200)
            for d in docs:
                data_item["documents"].append({
                    "id": d.get("id", ""),
                    "filename": d.get("filename", ""),
                    "document_type": d.get("document_type", d.get("step_name", "")),
                    "status": d.get("status", ""),
                    "file_url": d.get("file_url", d.get("file_path", "")),
                    "case_id": d.get("case_id", ""),
                    "created_at": serialize_datetime(d.get("created_at")),
                })
            break  # Only fetch docs once per client

    # Determine current step for each client
    result = []
    for email, p in pipeline.items():
        # Determine pipeline stage
        has_pending_pa = any(pa["stage"] in ["new", "payment_pending", "under_review", "documents_submitted"] for pa in p["pre_assessments"])
        has_pending_sale = any(s["status"] == "pending" for s in p["sales"])
        has_unassigned_case = any(c["case_manager_id"] is None or c["status"] == "pending_assignment" for c in p["cases"])
        has_pending_docs = any(d["status"] in ["pending", "uploaded"] for d in p["documents"])

        needs_action = has_pending_pa or has_pending_sale or has_unassigned_case or has_pending_docs
        if not needs_action and not p["pre_assessments"] and not p["sales"]:
            continue

        current_stage = "completed"
        if has_pending_pa:
            current_stage = "pre_assessment"
        elif has_pending_sale:
            current_stage = "sale_review"
        elif has_unassigned_case:
            current_stage = "assign_cm"
        elif has_pending_docs:
            current_stage = "document_review"
        elif p["cases"]:
            current_stage = "in_progress"

        result.append({
            **p,
            "current_stage": current_stage,
            "needs_action": needs_action,
        })

    # Sort: needs_action first, then by stage priority
    stage_priority = {"pre_assessment": 0, "sale_review": 1, "assign_cm": 2, "document_review": 3, "in_progress": 4, "completed": 5}
    result.sort(key=lambda x: (0 if x["needs_action"] else 1, stage_priority.get(x["current_stage"], 9)))

    return {"clients": result, "case_managers": [{"id": cm["id"], "name": cm["name"]} for cm in cms]}


@router.post("/approval-center/assign-cm")
async def assign_case_manager(case_id: str = "", case_manager_id: str = "", current_user: dict = Depends(get_current_user)):
    """Assign case manager to a case"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    case = await cases_col.find_one({"id": case_id}, {"_id": 0})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    cm = await users_col.find_one({"id": case_manager_id}, {"_id": 0, "name": 1})
    if not cm:
        raise HTTPException(status_code=404, detail="Case Manager not found")

    await cases_col.update_one({"id": case_id}, {"$set": {
        "case_manager_id": case_manager_id,
        "status": "active",
    }})

    await notifications_col.insert_one({
        "id": str(uuid.uuid4()), "user_id": case_manager_id,
        "title": "New Case Assigned", "message": f"Case {case.get('case_id', '')} assigned to you",
        "type": "case_assigned", "read": False, "created_at": datetime.now(timezone.utc)
    })

    await audit_logs_col.insert_one({
        "id": str(uuid.uuid4()), "user_id": current_user["id"],
        "action": "cm_assigned", "entity_type": "case", "entity_id": case_id,
        "new_value": {"case_manager": cm["name"]},
        "created_at": datetime.now(timezone.utc)
    })

    return {"message": f"Case Manager '{cm['name']}' assigned to {case.get('case_id', '')}"}



# ===================== 10B: REFUND MANAGER ENHANCED =====================

@router.get("/refund-manager")
async def get_refund_manager(current_user: dict = Depends(get_current_user)):
    """Get enhanced refund manager data"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    # Get all refunds
    all_refunds = await refunds_col.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)

    refund_list = []
    total_refunded = 0
    monthly_refunds = {}

    for r in all_refunds:
        sale = await sales_col.find_one({"id": r.get("sale_id")}, {"_id": 0})
        processor = await users_col.find_one({"id": r.get("processed_by")}, {"_id": 0, "name": 1})

        ca = r.get("created_at")
        month_key = ""
        if isinstance(ca, datetime):
            month_key = ca.strftime("%Y-%m")
        elif isinstance(ca, str):
            month_key = ca[:7]

        if month_key:
            monthly_refunds[month_key] = monthly_refunds.get(month_key, 0) + r.get("amount", 0)

        total_refunded += r.get("amount", 0)

        refund_list.append({
            "id": r.get("id", ""),
            "sale_id": r.get("sale_id", ""),
            "amount": r.get("amount", 0),
            "reason": r.get("reason", ""),
            "refund_method": r.get("refund_method", ""),
            "status": r.get("status", ""),
            "notes": r.get("notes", ""),
            "client_name": sale.get("client_name", "N/A") if sale else "N/A",
            "client_email": sale.get("client_email", "N/A") if sale else "N/A",
            "original_fee": sale.get("fee_amount", 0) if sale else 0,
            "product_name": sale.get("product_name", "") if sale else "",
            "partner_name": sale.get("partner_name", "") if sale else "",
            "processed_by_name": processor["name"] if processor else "System",
            "created_at": serialize_datetime(r.get("created_at")),
            "processed_at": serialize_datetime(r.get("processed_at")),
        })

    # Pre-assessment refunds pending
    pa_refund_pending = await pre_assessments_col.find(
        {"stage": "refund_initiated"}, {"_id": 0}
    ).to_list(100)

    pa_refunds = []
    for pa in pa_refund_pending:
        pa_refunds.append({
            "id": pa["id"],
            "client_name": pa.get("client_name", ""),
            "client_email": pa.get("client_email", ""),
            "amount": pa.get("pre_assessment_fee", 5100),
            "partner_name": pa.get("partner_name", ""),
            "reason": pa.get("admin_reason", "Eligibility rejected"),
            "type": "pre_assessment",
            "pa_number": pa.get("pa_number", ""),
            "created_at": serialize_datetime(pa.get("created_at")),
        })

    # Eligible sales for refund (approved/pending with received amount > 0)
    eligible_sales = await sales_col.find(
        {"status": {"$in": ["approved", "pending"]}, "amount_received": {"$gt": 0}}, {"_id": 0}
    ).to_list(500)

    eligible_for_refund = []
    for s in eligible_sales:
        existing_refunds = await refunds_col.find(
            {"sale_id": s["id"], "status": {"$ne": "cancelled"}}, {"_id": 0}
        ).to_list(100)
        total_already_refunded = sum(r.get("amount", 0) for r in existing_refunds)
        refundable = (s.get("amount_received", 0) or 0) - total_already_refunded
        if refundable > 0:
            eligible_for_refund.append({
                "sale_id": s["id"],
                "client_name": s.get("client_name", ""),
                "client_email": s.get("client_email", ""),
                "fee_amount": s.get("fee_amount", 0),
                "amount_received": s.get("amount_received", 0),
                "already_refunded": total_already_refunded,
                "max_refundable": round(refundable, 2),
                "product_name": s.get("product_name", ""),
                "partner_name": s.get("partner_name", ""),
            })

    monthly_trend = [{"month": k, "amount": round(v, 2)} for k, v in sorted(monthly_refunds.items())]

    return {
        "refunds": refund_list,
        "pa_refunds_pending": pa_refunds,
        "eligible_for_refund": eligible_for_refund,
        "stats": {
            "total_refunded": round(total_refunded, 2),
            "total_count": len(refund_list),
            "pa_pending_count": len(pa_refunds),
            "pa_pending_amount": sum(p["amount"] for p in pa_refunds),
        },
        "monthly_trend": monthly_trend,
    }


class ProcessPARefund(BaseModel):
    pa_id: str
    notes: str = ""


@router.post("/refund-manager/process-pa-refund")
async def process_pa_refund(data: ProcessPARefund, current_user: dict = Depends(get_current_user)):
    """Process refund for rejected pre-assessment"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    pa = await pre_assessments_col.find_one({"id": data.pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Pre-assessment not found")
    if pa["stage"] != "refund_initiated":
        raise HTTPException(status_code=400, detail="Refund not in initiated state")

    await pre_assessments_col.update_one({"id": data.pa_id}, {"$set": {
        "stage": "refunded",
        "refund_processed_by": current_user["id"],
        "refund_processed_at": datetime.now(timezone.utc),
        "refund_notes": data.notes,
        "updated_at": datetime.now(timezone.utc)
    }})

    await audit_logs_col.insert_one({
        "id": str(uuid.uuid4()), "user_id": current_user["id"],
        "action": "pa_refund_processed", "entity_type": "pre_assessment",
        "entity_id": data.pa_id, "new_value": {
            "amount": pa.get("pre_assessment_fee", 5100),
            "client_name": pa.get("client_name", ""),
            "notes": data.notes
        }, "created_at": datetime.now(timezone.utc)
    })

    # Notify partner
    await notifications_col.insert_one({
        "id": str(uuid.uuid4()), "user_id": pa["partner_id"],
        "title": "Refund Processed",
        "message": f"₹{pa.get('pre_assessment_fee', 5100)} refund processed for {pa['client_name']}",
        "type": "refund", "read": False,
        "created_at": datetime.now(timezone.utc)
    })

    return {"message": f"Refund of ₹{pa.get('pre_assessment_fee', 5100)} processed for {pa['client_name']}"}


# ===================== 10C: ENHANCED REVENUE DASHBOARD =====================

@router.get("/revenue-dashboard")
async def get_revenue_dashboard(
    period: str = Query("12months"),
    current_user: dict = Depends(get_current_user)
):
    """Get enhanced revenue dashboard data"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    # All approved sales
    all_sales = await sales_col.find({"status": "approved"}, {"_id": 0}).to_list(10000)

    # Monthly revenue
    monthly_data = {}
    total_revenue = 0
    total_received = 0
    total_commission = 0
    total_pending = 0

    for s in all_sales:
        fee = s.get("fee_amount", 0) or 0
        received = s.get("amount_received", 0) or 0
        commission = s.get("commission_amount", 0) or 0
        pending = fee - received

        total_revenue += fee
        total_received += received
        total_commission += commission
        total_pending += pending

        ca = s.get("created_at")
        if isinstance(ca, datetime):
            month_key = ca.strftime("%Y-%m")
        elif isinstance(ca, str):
            month_key = ca[:7]
        else:
            continue

        if month_key not in monthly_data:
            monthly_data[month_key] = {"revenue": 0, "received": 0, "commission": 0, "count": 0}
        monthly_data[month_key]["revenue"] += fee
        monthly_data[month_key]["received"] += received
        monthly_data[month_key]["commission"] += commission
        monthly_data[month_key]["count"] += 1

    monthly_trend = [
        {"month": k, **{kk: round(vv, 2) for kk, vv in v.items()}}
        for k, v in sorted(monthly_data.items())
    ]

    # Partner-wise revenue
    partner_revenue = {}
    for s in all_sales:
        pid = s.get("partner_id", "")
        if not pid:
            continue
        if pid not in partner_revenue:
            partner = await users_col.find_one({"id": pid}, {"_id": 0, "name": 1})
            partner_revenue[pid] = {
                "partner_id": pid,
                "partner_name": partner["name"] if partner else "Unknown",
                "revenue": 0, "received": 0, "commission": 0, "sales_count": 0
            }
        partner_revenue[pid]["revenue"] += s.get("fee_amount", 0) or 0
        partner_revenue[pid]["received"] += s.get("amount_received", 0) or 0
        partner_revenue[pid]["commission"] += s.get("commission_amount", 0) or 0
        partner_revenue[pid]["sales_count"] += 1

    # Service/Product-wise revenue
    product_revenue = {}
    for s in all_sales:
        pid = s.get("product_id", "")
        if pid not in product_revenue:
            product = await products_col.find_one({"id": pid}, {"_id": 0, "name": 1})
            product_revenue[pid] = {
                "product_id": pid,
                "product_name": product["name"] if product else s.get("product_name", "Unknown"),
                "revenue": 0, "received": 0, "commission": 0, "sales_count": 0
            }
        product_revenue[pid]["revenue"] += s.get("fee_amount", 0) or 0
        product_revenue[pid]["received"] += s.get("amount_received", 0) or 0
        product_revenue[pid]["commission"] += s.get("commission_amount", 0) or 0
        product_revenue[pid]["sales_count"] += 1

    # Pre-assessment revenue
    pa_paid = await pre_assessments_col.count_documents({"fee_payment_status": "paid"})
    pa_revenue = pa_paid * 5100

    # Payment method distribution
    payment_methods = {}
    for s in all_sales:
        method = s.get("payment_method", "unknown")
        if method not in payment_methods:
            payment_methods[method] = {"method": method, "count": 0, "amount": 0}
        payment_methods[method]["count"] += 1
        payment_methods[method]["amount"] += s.get("fee_amount", 0) or 0

    # Refund totals
    total_refunded_amount = 0
    all_refunds = await refunds_col.find({}, {"_id": 0, "amount": 1}).to_list(5000)
    total_refunded_amount = sum(r.get("amount", 0) for r in all_refunds)

    return {
        "summary": {
            "total_revenue": round(total_revenue, 2),
            "total_received": round(total_received, 2),
            "total_pending": round(total_pending, 2),
            "total_commission": round(total_commission, 2),
            "total_refunded": round(total_refunded_amount, 2),
            "net_revenue": round(total_received - total_refunded_amount, 2),
            "pa_revenue": pa_revenue,
            "total_sales": len(all_sales),
        },
        "monthly_trend": monthly_trend,
        "by_partner": sorted(
            [{**v, "revenue": round(v["revenue"], 2), "received": round(v["received"], 2), "commission": round(v["commission"], 2)}
             for v in partner_revenue.values()],
            key=lambda x: x["revenue"], reverse=True
        ),
        "by_product": sorted(
            [{**v, "revenue": round(v["revenue"], 2), "received": round(v["received"], 2), "commission": round(v["commission"], 2)}
             for v in product_revenue.values()],
            key=lambda x: x["revenue"], reverse=True
        ),
        "payment_methods": sorted(
            [{**v, "amount": round(v["amount"], 2)} for v in payment_methods.values()],
            key=lambda x: x["amount"], reverse=True
        ),
    }


# ===================== 10D: CUSTOM REPORT BUILDER =====================

class ReportRequest(BaseModel):
    report_type: str  # "cases", "revenue", "partners", "clients", "pre_assessments"
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    partner_id: Optional[str] = None
    product_id: Optional[str] = None
    status: Optional[str] = None
    group_by: Optional[str] = None  # "month", "partner", "product", "status"


@router.get("/report-templates")
async def get_report_templates(current_user: dict = Depends(get_current_user)):
    """Get available report templates"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    return [
        {
            "id": "revenue_summary",
            "name": "Revenue Summary",
            "description": "Total revenue, received, pending with monthly breakdown",
            "report_type": "revenue",
            "icon": "trending-up",
        },
        {
            "id": "partner_performance",
            "name": "Partner Performance",
            "description": "Sales, revenue and commission per partner",
            "report_type": "partners",
            "icon": "users",
        },
        {
            "id": "case_status",
            "name": "Case Status Report",
            "description": "All cases with current status and progress",
            "report_type": "cases",
            "icon": "briefcase",
        },
        {
            "id": "client_list",
            "name": "Client Directory",
            "description": "All clients with their case and payment status",
            "report_type": "clients",
            "icon": "user",
        },
        {
            "id": "pre_assessment_report",
            "name": "Pre-Assessment Pipeline",
            "description": "All pre-assessments with stage and conversion data",
            "report_type": "pre_assessments",
            "icon": "clipboard-list",
        },
        {
            "id": "refund_report",
            "name": "Refund Report",
            "description": "All refunds processed with amounts and reasons",
            "report_type": "refunds",
            "icon": "rotate-ccw",
        },
    ]


@router.post("/report-builder/generate")
async def generate_report(req: ReportRequest, current_user: dict = Depends(get_current_user)):
    """Generate a custom report based on filters"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    date_filter = {}
    if req.date_from:
        try:
            date_filter["$gte"] = datetime.fromisoformat(req.date_from)
        except ValueError:
            pass
    if req.date_to:
        try:
            date_filter["$lte"] = datetime.fromisoformat(req.date_to + "T23:59:59")
        except ValueError:
            pass

    if req.report_type == "revenue":
        query = {"status": "approved"}
        if date_filter:
            query["created_at"] = date_filter
        if req.partner_id:
            query["partner_id"] = req.partner_id
        if req.product_id:
            query["product_id"] = req.product_id

        sales = await sales_col.find(query, {"_id": 0}).sort("created_at", -1).to_list(10000)

        rows = []
        for s in sales:
            rows.append({
                "Date": serialize_datetime(s.get("created_at", "")),
                "Client": s.get("client_name", ""),
                "Product": s.get("product_name", ""),
                "Partner": s.get("partner_name", ""),
                "Fee": s.get("fee_amount", 0),
                "Received": s.get("amount_received", 0),
                "Pending": round((s.get("fee_amount", 0) or 0) - (s.get("amount_received", 0) or 0), 2),
                "Commission": s.get("commission_amount", 0),
                "Payment Status": s.get("payment_status", ""),
                "Method": s.get("payment_method", ""),
            })

        total_fee = sum(r["Fee"] for r in rows)
        total_received = sum(r["Received"] for r in rows)
        total_pending = sum(r["Pending"] for r in rows)
        total_commission = sum(r["Commission"] for r in rows)

        return {
            "title": "Revenue Report",
            "rows": rows,
            "summary": {
                "total_fee": round(total_fee, 2),
                "total_received": round(total_received, 2),
                "total_pending": round(total_pending, 2),
                "total_commission": round(total_commission, 2),
                "record_count": len(rows),
            },
            "columns": ["Date", "Client", "Product", "Partner", "Fee", "Received", "Pending", "Commission", "Payment Status", "Method"],
        }

    elif req.report_type == "cases":
        query = {}
        if date_filter:
            query["created_at"] = date_filter
        if req.status:
            query["status"] = req.status
        if req.product_id:
            query["product_id"] = req.product_id

        cases_data = await cases_col.find(query, {"_id": 0}).sort("created_at", -1).to_list(10000)

        rows = []
        for c in cases_data:
            cm = await users_col.find_one({"id": c.get("case_manager_id")}, {"_id": 0, "name": 1})
            rows.append({
                "Case ID": c.get("case_id", ""),
                "Client": c.get("client_name", ""),
                "Product": c.get("product_name", ""),
                "Case Manager": cm["name"] if cm else "Unassigned",
                "Status": c.get("status", ""),
                "Current Step": c.get("current_step", ""),
                "Created": serialize_datetime(c.get("created_at", "")),
            })

        return {
            "title": "Case Status Report",
            "rows": rows,
            "summary": {
                "total": len(rows),
                "active": sum(1 for r in rows if r["Status"] == "active"),
                "completed": sum(1 for r in rows if r["Status"] == "completed"),
            },
            "columns": ["Case ID", "Client", "Product", "Case Manager", "Status", "Current Step", "Created"],
        }

    elif req.report_type == "partners":
        partners = await users_col.find({"role": "partner"}, {"_id": 0, "password": 0}).to_list(100)

        rows = []
        for p in partners:
            query = {"partner_id": p["id"], "status": "approved"}
            if date_filter:
                query["created_at"] = date_filter
            sales = await sales_col.find(query, {"_id": 0}).to_list(5000)
            total_rev = sum(s.get("fee_amount", 0) for s in sales)
            total_comm = sum(s.get("commission_amount", 0) for s in sales)
            total_rec = sum(s.get("amount_received", 0) for s in sales)
            rows.append({
                "Partner": p.get("name", ""),
                "Email": p.get("email", ""),
                "Total Sales": len(sales),
                "Revenue": round(total_rev, 2),
                "Received": round(total_rec, 2),
                "Commission": round(total_comm, 2),
                "Commission Rate": f"{p.get('commission_rate', 0)}%",
                "Status": p.get("status", ""),
            })

        return {
            "title": "Partner Performance Report",
            "rows": rows,
            "summary": {
                "total_partners": len(rows),
                "total_revenue": round(sum(r["Revenue"] for r in rows), 2),
                "total_commission": round(sum(r["Commission"] for r in rows), 2),
            },
            "columns": ["Partner", "Email", "Total Sales", "Revenue", "Received", "Commission", "Commission Rate", "Status"],
        }

    elif req.report_type == "clients":
        clients = await users_col.find({"role": "client"}, {"_id": 0, "password": 0}).to_list(1000)

        rows = []
        for cl in clients:
            client_cases = await cases_col.find({"client_id": cl["id"]}, {"_id": 0}).to_list(50)
            active_cases = sum(1 for c in client_cases if c.get("status") == "active")
            completed_cases = sum(1 for c in client_cases if c.get("status") == "completed")
            rows.append({
                "Client": cl.get("name", ""),
                "Email": cl.get("email", ""),
                "Mobile": cl.get("mobile", ""),
                "Total Cases": len(client_cases),
                "Active": active_cases,
                "Completed": completed_cases,
                "Status": cl.get("status", ""),
                "Joined": serialize_datetime(cl.get("created_at", "")),
            })

        return {
            "title": "Client Directory Report",
            "rows": rows,
            "summary": {"total_clients": len(rows)},
            "columns": ["Client", "Email", "Mobile", "Total Cases", "Active", "Completed", "Status", "Joined"],
        }

    elif req.report_type == "pre_assessments":
        query = {}
        if date_filter:
            query["created_at"] = date_filter
        if req.status:
            query["stage"] = req.status

        pa_data = await pre_assessments_col.find(query, {"_id": 0}).sort("created_at", -1).to_list(5000)

        rows = []
        for pa in pa_data:
            rows.append({
                "PA Number": pa.get("pa_number", ""),
                "Client": pa.get("client_name", ""),
                "Partner": pa.get("partner_name", ""),
                "Country": pa.get("country", ""),
                "Service": pa.get("service_type", ""),
                "Stage": pa.get("stage", ""),
                "Fee Status": pa.get("fee_payment_status", ""),
                "Decision": pa.get("admin_decision", "Pending"),
                "Created": serialize_datetime(pa.get("created_at", "")),
            })

        return {
            "title": "Pre-Assessment Pipeline Report",
            "rows": rows,
            "summary": {
                "total": len(rows),
                "approved": sum(1 for r in rows if r["Stage"] in ["approved", "proposal_sent", "case_created"]),
                "rejected": sum(1 for r in rows if r["Stage"] in ["rejected", "refund_initiated", "refunded"]),
                "pending": sum(1 for r in rows if r["Stage"] in ["new", "payment_pending", "under_review", "documents_submitted"]),
            },
            "columns": ["PA Number", "Client", "Partner", "Country", "Service", "Stage", "Fee Status", "Decision", "Created"],
        }

    elif req.report_type == "refunds":
        all_refunds_data = await refunds_col.find({}, {"_id": 0}).sort("created_at", -1).to_list(5000)

        rows = []
        for r in all_refunds_data:
            sale = await sales_col.find_one({"id": r.get("sale_id")}, {"_id": 0})
            rows.append({
                "Date": serialize_datetime(r.get("created_at", "")),
                "Client": sale.get("client_name", "N/A") if sale else "N/A",
                "Original Fee": sale.get("fee_amount", 0) if sale else 0,
                "Refund Amount": r.get("amount", 0),
                "Reason": r.get("reason", ""),
                "Method": r.get("refund_method", ""),
                "Status": r.get("status", ""),
            })

        return {
            "title": "Refund Report",
            "rows": rows,
            "summary": {
                "total_refunds": len(rows),
                "total_amount": round(sum(r["Refund Amount"] for r in rows), 2),
            },
            "columns": ["Date", "Client", "Original Fee", "Refund Amount", "Reason", "Method", "Status"],
        }

    else:
        raise HTTPException(status_code=400, detail="Invalid report type")
