"""Deadline & SLA Tracker - Auto-tracks document expiry, visa deadlines, processing SLAs"""
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException

from core.auth import get_current_user
from core.database import (
    db, cases_col, case_deadlines_col, documents_col, notifications_col,
    case_steps_col, users_col
)

router = APIRouter(prefix="/deadlines", tags=["Deadline Tracker"])

# Standard validity periods for common documents (in days)
DOC_VALIDITY = {
    "passport": 3650,
    "ielts": 730, "celpip": 730, "pte": 730, "toefl": 730, "oet": 730,
    "medical": 365, "medical examination": 365, "health exam": 365, "chest x-ray": 365,
    "police clearance": 365, "pcc": 365, "police certificate": 365,
    "eca": 1825, "education credential": 1825, "nzqa": 1825,
    "skills assessment": 1095, "vetassess": 1095, "acs": 1095,
    "bank statement": 90, "proof of funds": 90,
    "employment reference": 730, "work experience": 730,
    "biometrics": 3650,
    "photo": 180, "photograph": 180,
}

DEADLINE_TYPES = ["document_expiry", "visa_deadline", "processing_sla", "task_due", "milestone", "custom"]
URGENCY_THRESHOLDS = {"critical": 7, "urgent": 30, "warning": 60, "safe": 999999}


class DeadlineCreate(BaseModel):
    case_id: str
    title: str
    deadline_type: str = "custom"
    due_date: str  # ISO date
    description: str = ""
    step_name: str = ""
    auto_remind: bool = True
    remind_days_before: int = 7


class DeadlineUpdate(BaseModel):
    title: Optional[str] = None
    due_date: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    auto_remind: Optional[bool] = None


def _calc_urgency(due_date_str: str) -> dict:
    """Calculate urgency level and days remaining"""
    try:
        due = datetime.fromisoformat(due_date_str.replace("Z", "+00:00")) if isinstance(due_date_str, str) else due_date_str
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        days_left = (due - now).days
        if days_left < 0:
            return {"level": "expired", "days_left": days_left, "color": "red", "label": f"Expired {abs(days_left)}d ago"}
        elif days_left <= URGENCY_THRESHOLDS["critical"]:
            return {"level": "critical", "days_left": days_left, "color": "red", "label": f"{days_left}d left"}
        elif days_left <= URGENCY_THRESHOLDS["urgent"]:
            return {"level": "urgent", "days_left": days_left, "color": "amber", "label": f"{days_left}d left"}
        elif days_left <= URGENCY_THRESHOLDS["warning"]:
            return {"level": "warning", "days_left": days_left, "color": "yellow", "label": f"{days_left}d left"}
        else:
            return {"level": "safe", "days_left": days_left, "color": "green", "label": f"{days_left}d left"}
    except Exception:
        return {"level": "unknown", "days_left": 0, "color": "gray", "label": "Unknown"}


def _guess_validity(doc_type: str) -> int:
    """Guess document validity in days based on type"""
    doc_lower = (doc_type or "").lower()
    for key, days in DOC_VALIDITY.items():
        if key in doc_lower:
            return days
    return 365  # Default 1 year


@router.get("/case/{case_id}")
async def get_case_deadlines(case_id: str, current_user: dict = Depends(get_current_user)):
    """Get all deadlines for a case - merges custom deadlines + auto-detected from documents"""
    case = await cases_col.find_one({"id": case_id}, {"_id": 0})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Access check
    if current_user["role"] == "client" and current_user["id"] != case.get("client_id"):
        raise HTTPException(status_code=403, detail="Access denied")

    # 1. Get custom/manual deadlines
    custom_deadlines = await case_deadlines_col.find(
        {"case_id": case_id}, {"_id": 0}
    ).sort("due_date", 1).to_list(100)

    for d in custom_deadlines:
        if isinstance(d.get("created_at"), datetime):
            d["created_at"] = d["created_at"].isoformat()
        d["urgency"] = _calc_urgency(d.get("due_date", ""))

    # 2. Auto-detect document expiry deadlines
    docs = await documents_col.find(
        {"case_id": case_id}, {"_id": 0, "file_path": 0}
    ).to_list(200)

    doc_deadlines = []
    for doc in docs:
        expiry = doc.get("expiry_date")
        uploaded_at = doc.get("uploaded_at")

        if expiry:
            # Has explicit expiry
            exp_str = expiry.isoformat() if isinstance(expiry, datetime) else str(expiry)
            doc_deadlines.append({
                "id": f"doc_exp_{doc.get('id', '')}",
                "case_id": case_id,
                "title": f"{doc.get('document_type', doc.get('filename', 'Document'))} - Expiry",
                "deadline_type": "document_expiry",
                "due_date": exp_str,
                "description": f"Document expires. Re-upload required before this date.",
                "step_name": doc.get("step_name", ""),
                "status": "active",
                "source": "auto_detected",
                "urgency": _calc_urgency(exp_str),
                "document_id": doc.get("id", ""),
                "document_status": doc.get("status", ""),
            })
        elif uploaded_at:
            # Guess expiry from document type + upload date
            validity_days = _guess_validity(doc.get("document_type", ""))
            if isinstance(uploaded_at, str):
                try:
                    upload_dt = datetime.fromisoformat(uploaded_at.replace("Z", "+00:00"))
                except Exception:
                    continue
            elif isinstance(uploaded_at, datetime):
                upload_dt = uploaded_at
            else:
                continue

            estimated_expiry = upload_dt + timedelta(days=validity_days)
            exp_str = estimated_expiry.isoformat()
            doc_deadlines.append({
                "id": f"doc_est_{doc.get('id', '')}",
                "case_id": case_id,
                "title": f"{doc.get('document_type', doc.get('filename', 'Document'))} - Estimated Expiry",
                "deadline_type": "document_expiry",
                "due_date": exp_str,
                "description": f"Estimated {validity_days}-day validity from upload date.",
                "step_name": doc.get("step_name", ""),
                "status": "active",
                "source": "estimated",
                "urgency": _calc_urgency(exp_str),
                "document_id": doc.get("id", ""),
                "document_status": doc.get("status", ""),
            })

    # 3. Merge and sort all deadlines
    all_deadlines = custom_deadlines + doc_deadlines
    all_deadlines.sort(key=lambda x: x.get("urgency", {}).get("days_left", 9999))

    # 4. Calculate summary stats
    expired = [d for d in all_deadlines if d.get("urgency", {}).get("level") == "expired"]
    critical = [d for d in all_deadlines if d.get("urgency", {}).get("level") == "critical"]
    urgent = [d for d in all_deadlines if d.get("urgency", {}).get("level") == "urgent"]
    warning = [d for d in all_deadlines if d.get("urgency", {}).get("level") == "warning"]
    safe = [d for d in all_deadlines if d.get("urgency", {}).get("level") in ("safe", "unknown")]

    return {
        "case_id": case_id,
        "deadlines": all_deadlines,
        "summary": {
            "total": len(all_deadlines),
            "expired": len(expired),
            "critical": len(critical),
            "urgent": len(urgent),
            "warning": len(warning),
            "safe": len(safe),
        }
    }


@router.post("/create")
async def create_deadline(data: DeadlineCreate, current_user: dict = Depends(get_current_user)):
    """Create a manual deadline for a case"""
    if current_user["role"] not in ["admin", "case_manager"]:
        raise HTTPException(status_code=403, detail="Admin or CM only")

    case = await cases_col.find_one({"id": data.case_id}, {"_id": 0, "id": 1, "client_id": 1})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    deadline = {
        "id": str(uuid.uuid4()),
        "case_id": data.case_id,
        "title": data.title,
        "deadline_type": data.deadline_type,
        "due_date": data.due_date,
        "description": data.description,
        "step_name": data.step_name,
        "status": "active",
        "source": "manual",
        "auto_remind": data.auto_remind,
        "remind_days_before": data.remind_days_before,
        "created_by": current_user["id"],
        "created_by_name": current_user.get("name", ""),
        "created_at": datetime.now(timezone.utc),
    }

    await case_deadlines_col.insert_one(deadline)

    # Create notification for client
    if data.auto_remind and case.get("client_id"):
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": case["client_id"],
            "title": f"New Deadline: {data.title}",
            "message": f"Due by {data.due_date}. {data.description}",
            "type": "deadline",
            "read": False,
            "created_at": datetime.now(timezone.utc),
        })

    deadline.pop("_id", None)
    if isinstance(deadline.get("created_at"), datetime):
        deadline["created_at"] = deadline["created_at"].isoformat()
    deadline["urgency"] = _calc_urgency(data.due_date)

    return deadline


@router.put("/{deadline_id}")
async def update_deadline(deadline_id: str, data: DeadlineUpdate, current_user: dict = Depends(get_current_user)):
    """Update a manual deadline"""
    if current_user["role"] not in ["admin", "case_manager"]:
        raise HTTPException(status_code=403, detail="Admin or CM only")

    update_data = {k: v for k, v in data.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    update_data["updated_at"] = datetime.now(timezone.utc)
    result = await case_deadlines_col.update_one(
        {"id": deadline_id}, {"$set": update_data}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Deadline not found")

    return {"message": "Deadline updated"}


@router.delete("/{deadline_id}")
async def delete_deadline(deadline_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a manual deadline"""
    if current_user["role"] not in ["admin", "case_manager"]:
        raise HTTPException(status_code=403, detail="Admin or CM only")

    result = await case_deadlines_col.delete_one({"id": deadline_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Deadline not found")

    return {"message": "Deadline deleted"}


@router.get("/overview")
async def get_deadlines_overview(current_user: dict = Depends(get_current_user)):
    """Get overview of all deadlines across cases (Admin/CM view)"""
    if current_user["role"] not in ["admin", "case_manager"]:
        raise HTTPException(status_code=403, detail="Admin or CM only")

    # Get all active cases
    query = {} if current_user["role"] == "admin" else {"case_manager_id": current_user["id"]}
    cases = await cases_col.find(query, {"_id": 0, "id": 1, "case_id": 1, "client_name": 1, "product_name": 1, "status": 1}).to_list(500)
    if not cases:
        return {"alerts": [], "summary": {"total": 0, "expired": 0, "critical": 0, "urgent": 0}}

    case_ids = [c["id"] for c in cases]
    case_map = {c["id"]: c for c in cases}

    # Get custom deadlines
    custom = await case_deadlines_col.find(
        {"case_id": {"$in": case_ids}, "status": "active"}, {"_id": 0}
    ).to_list(1000)

    # Get document expiry data
    docs = await documents_col.find(
        {"case_id": {"$in": case_ids}}, {"_id": 0, "id": 1, "case_id": 1, "document_type": 1, "expiry_date": 1, "uploaded_at": 1, "status": 1, "step_name": 1}
    ).to_list(2000)

    alerts = []

    # Process custom deadlines
    for d in custom:
        if isinstance(d.get("created_at"), datetime):
            d["created_at"] = d["created_at"].isoformat()
        urg = _calc_urgency(d.get("due_date", ""))
        if urg["level"] in ("expired", "critical", "urgent", "warning"):
            c = case_map.get(d["case_id"], {})
            alerts.append({
                **d, "urgency": urg,
                "case_display": c.get("case_id", ""),
                "client_name": c.get("client_name", ""),
                "product_name": c.get("product_name", ""),
            })

    # Process document expiries
    for doc in docs:
        expiry = doc.get("expiry_date")
        uploaded_at = doc.get("uploaded_at")
        exp_str = None

        if expiry:
            exp_str = expiry.isoformat() if isinstance(expiry, datetime) else str(expiry)
        elif uploaded_at:
            validity = _guess_validity(doc.get("document_type", ""))
            if isinstance(uploaded_at, datetime):
                exp_str = (uploaded_at + timedelta(days=validity)).isoformat()
            elif isinstance(uploaded_at, str):
                try:
                    upload_dt = datetime.fromisoformat(uploaded_at.replace("Z", "+00:00"))
                    exp_str = (upload_dt + timedelta(days=validity)).isoformat()
                except Exception:
                    continue

        if exp_str:
            urg = _calc_urgency(exp_str)
            if urg["level"] in ("expired", "critical", "urgent", "warning"):
                c = case_map.get(doc["case_id"], {})
                alerts.append({
                    "id": f"doc_{doc.get('id', '')}",
                    "case_id": doc["case_id"],
                    "title": f"{doc.get('document_type', 'Document')} Expiry",
                    "deadline_type": "document_expiry",
                    "due_date": exp_str,
                    "step_name": doc.get("step_name", ""),
                    "status": "active",
                    "source": "auto_detected" if expiry else "estimated",
                    "urgency": urg,
                    "case_display": c.get("case_id", ""),
                    "client_name": c.get("client_name", ""),
                    "product_name": c.get("product_name", ""),
                })

    alerts.sort(key=lambda x: x.get("urgency", {}).get("days_left", 9999))

    expired = sum(1 for a in alerts if a.get("urgency", {}).get("level") == "expired")
    critical = sum(1 for a in alerts if a.get("urgency", {}).get("level") == "critical")
    urgent = sum(1 for a in alerts if a.get("urgency", {}).get("level") == "urgent")

    return {
        "alerts": alerts[:50],  # Top 50 most urgent
        "summary": {
            "total": len(alerts),
            "expired": expired,
            "critical": critical,
            "urgent": urgent,
        }
    }
