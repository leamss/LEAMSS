"""Payment History Timeline + Milestone Payments.

Endpoints:
  GET  /api/payment-history/pa/{pa_id}        — unified timeline for a pre-assessment
  GET  /api/payment-history/case/{case_id}    — unified timeline for a case (includes milestones)
  GET  /api/milestones/case/{case_id}         — list milestones for a case
  POST /api/milestones/case/{case_id}/create  — partner/admin creates milestone
  POST /api/milestones/{mid}/mock-pay         — client mock-pays a milestone
  POST /api/milestones/{mid}/mark-paid        — partner/admin marks milestone paid (manual)
  DELETE /api/milestones/{mid}                — delete milestone (partner/admin)
"""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from core.database import db
from routers.auth import get_current_user
from core.services import log_activity

router = APIRouter(tags=["Payment History & Milestones"])

pa_col = db["pre_assessments"]
cases_col = db["cases"]
milestones_col = db["case_milestones"]
invoices_col = db["pa_invoices"]
notifications_col = db["notifications"]


def _iso(v):
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return v


async def _load_pa(pa_id: str):
    pa = await pa_col.find_one({"id": pa_id}, {"_id": 0})
    if not pa:
        raise HTTPException(status_code=404, detail="Pre-assessment not found")
    return pa


async def _load_case(case_id: str):
    c = await cases_col.find_one({"id": case_id}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Case not found")
    return c


def _authz_pa(pa: dict, current_user: dict):
    role = current_user.get("role")
    if role == "admin":
        return
    if role == "partner" and pa.get("partner_id") == current_user["id"]:
        return
    if role == "case_manager":
        return
    if role == "client":
        if (pa.get("client_email") or "").lower() == (current_user.get("email") or "").lower():
            return
        if pa.get("client_user_id") == current_user["id"]:
            return
    raise HTTPException(status_code=403, detail="Not authorized")


def _authz_case(case: dict, current_user: dict):
    role = current_user.get("role")
    if role == "admin":
        return
    if role == "partner" and case.get("partner_id") == current_user["id"]:
        return
    if role == "case_manager" and case.get("case_manager_id") == current_user["id"]:
        return
    if role == "client" and (case.get("client_id") == current_user["id"] or (case.get("client_email") or "").lower() == (current_user.get("email") or "").lower()):
        return
    raise HTTPException(status_code=403, detail="Not authorized")


# ==================== PAYMENT HISTORY ROUTER ====================
history_router = APIRouter(prefix="/payment-history", tags=["Payment History"])


def _pa_events(pa: dict) -> list:
    events = []
    if pa.get("fee_payment_status") == "paid":
        events.append({
            "ts": _iso(pa.get("updated_at")),
            "kind": "pre_assessment_fee",
            "label": "Pre-Assessment Fee Paid",
            "amount": float(pa.get("pre_assessment_fee") or 5100),
            "direction": "in",
            "meta": {"reference": pa.get("pa_number")},
        })
    if pa.get("proposal_status") == "sent":
        events.append({
            "ts": _iso(pa.get("updated_at")),
            "kind": "proposal_sent",
            "label": "Proposal Sent to Client",
            "amount": float(pa.get("proposal_fee") or 0),
            "direction": "pending",
            "meta": {"promo_code": pa.get("proposal_promo_code"), "upsells": len(pa.get("proposal_upsells") or [])},
        })
    if pa.get("stage") in ("proposal_paid", "awaiting_final_approval", "case_created"):
        events.append({
            "ts": _iso(pa.get("updated_at")),
            "kind": "main_fee_paid",
            "label": "Main Service Fee Paid",
            "amount": float(pa.get("proposal_fee") or 0),
            "direction": "in",
            "meta": {"final_amount": float(pa.get("proposal_fee") or 0)},
        })
    return events


@history_router.get("/pa/{pa_id}")
async def history_for_pa(pa_id: str, current_user: dict = Depends(get_current_user)):
    pa = await _load_pa(pa_id)
    _authz_pa(pa, current_user)
    events = _pa_events(pa)
    # If case exists, pull milestones too
    case = None
    if pa.get("case_id"):
        case = await cases_col.find_one({"id": pa["case_id"]}, {"_id": 0})
        if case:
            ms = await milestones_col.find({"case_id": case["id"]}, {"_id": 0}).sort("created_at", 1).to_list(200)
            for m in ms:
                events.append({
                    "ts": _iso(m.get("paid_at") or m.get("created_at")),
                    "kind": "milestone",
                    "label": f"Milestone: {m.get('title', 'Milestone')}",
                    "amount": float(m.get("amount") or 0),
                    "direction": "in" if m.get("status") == "paid" else "pending",
                    "meta": {"milestone_id": m["id"], "status": m.get("status")},
                })
    invs = await invoices_col.find({"pre_assessment_id": pa_id}, {"_id": 0}).to_list(100)
    events.extend([{
        "ts": _iso(i.get("sent_at")),
        "kind": "invoice",
        "label": f"Invoice {i.get('reference_id')} sent",
        "amount": float(i.get("amount_received_total") or 0),
        "direction": "info",
        "meta": {"reference": i.get("reference_id"), "channel": i.get("channel")},
    } for i in invs])

    # Dedupe nothing; sort desc
    events.sort(key=lambda e: (e.get("ts") or ""), reverse=True)

    total_in = sum(e["amount"] for e in events if e.get("direction") == "in")
    total_pending = sum(e["amount"] for e in events if e.get("direction") == "pending")
    return {"events": events, "totals": {"received": total_in, "pending": total_pending}}


@history_router.get("/case/{case_id}")
async def history_for_case(case_id: str, current_user: dict = Depends(get_current_user)):
    case = await _load_case(case_id)
    _authz_case(case, current_user)
    events = []
    # Any attached PA?
    pa = await pa_col.find_one({"case_id": case_id}, {"_id": 0})
    if pa:
        events.extend(_pa_events(pa))
    ms = await milestones_col.find({"case_id": case_id}, {"_id": 0}).sort("created_at", 1).to_list(200)
    for m in ms:
        events.append({
            "ts": _iso(m.get("paid_at") or m.get("created_at")),
            "kind": "milestone",
            "label": f"Milestone: {m.get('title', 'Milestone')}",
            "amount": float(m.get("amount") or 0),
            "direction": "in" if m.get("status") == "paid" else "pending",
            "meta": {"milestone_id": m["id"], "status": m.get("status")},
        })
    events.sort(key=lambda e: (e.get("ts") or ""), reverse=True)
    total_in = sum(e["amount"] for e in events if e.get("direction") == "in")
    total_pending = sum(e["amount"] for e in events if e.get("direction") == "pending")
    return {"events": events, "totals": {"received": total_in, "pending": total_pending}}


# ==================== MILESTONES ROUTER ====================
milestones_router = APIRouter(prefix="/milestones", tags=["Milestones"])


class MilestoneCreate(BaseModel):
    title: str
    amount: float
    description: str = ""
    due_date: Optional[str] = None  # ISO date string


@milestones_router.post("/case/{case_id}/create")
async def create_milestone(case_id: str, body: MilestoneCreate, current_user: dict = Depends(get_current_user)):
    case = await _load_case(case_id)
    if current_user["role"] not in ["partner", "admin"] and not (current_user["role"] == "case_manager" and case.get("case_manager_id") == current_user["id"]):
        raise HTTPException(status_code=403, detail="Only partner / case manager / admin can create milestones")
    if body.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be > 0")
    mid = str(uuid.uuid4())
    rec = {
        "id": mid,
        "case_id": case_id,
        "client_id": case.get("client_id"),
        "client_email": case.get("client_email"),
        "title": body.title.strip(),
        "amount": float(body.amount),
        "description": body.description,
        "due_date": body.due_date,
        "status": "pending",  # pending | paid | cancelled
        "paid_at": None,
        "paid_method": None,
        "created_by": current_user["id"],
        "created_by_name": current_user.get("name", ""),
        "created_at": datetime.now(timezone.utc),
    }
    await milestones_col.insert_one(rec)
    rec.pop("_id", None)
    rec["created_at"] = rec["created_at"].isoformat()
    if case.get("client_id"):
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()), "user_id": case["client_id"],
            "title": "New Milestone Payment",
            "message": f"'{body.title}' — INR {body.amount:,.0f} due. Open your case to pay.",
            "type": "milestone", "read": False,
            "created_at": datetime.now(timezone.utc)
        })
    await log_activity(current_user["id"], current_user.get("name", ""), "milestone_create",
                       "case", case_id, f"Milestone '{body.title}' INR {body.amount:,.0f} created")
    return rec


@milestones_router.get("/case/{case_id}")
async def list_milestones(case_id: str, current_user: dict = Depends(get_current_user)):
    case = await _load_case(case_id)
    _authz_case(case, current_user)
    items = await milestones_col.find({"case_id": case_id}, {"_id": 0}).sort("created_at", 1).to_list(200)
    for m in items:
        for f in ("created_at", "paid_at"):
            if f in m and hasattr(m[f], "isoformat"):
                m[f] = m[f].isoformat()
    return items


@milestones_router.post("/{mid}/mock-pay")
async def mock_pay_milestone(mid: str, current_user: dict = Depends(get_current_user)):
    m = await milestones_col.find_one({"id": mid}, {"_id": 0})
    if not m:
        raise HTTPException(status_code=404, detail="Milestone not found")
    case = await _load_case(m["case_id"])
    _authz_case(case, current_user)
    if m.get("status") == "paid":
        raise HTTPException(status_code=400, detail="Already paid")
    await milestones_col.update_one({"id": mid}, {"$set": {
        "status": "paid",
        "paid_at": datetime.now(timezone.utc),
        "paid_method": "mock",
    }})
    if case.get("partner_id"):
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()), "user_id": case["partner_id"],
            "title": "Milestone Paid!", "type": "milestone_paid",
            "message": f"{case.get('client_name', 'Client')} paid '{m['title']}' — INR {m['amount']:,.0f} (mock)",
            "read": False, "created_at": datetime.now(timezone.utc)
        })
    await log_activity(current_user["id"], current_user.get("name", ""), "milestone_paid",
                       "case", m["case_id"], f"Milestone '{m['title']}' paid (mock)")
    return {"ok": True, "mode": "mock"}


@milestones_router.post("/{mid}/mark-paid")
async def mark_milestone_paid(mid: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["partner", "admin", "case_manager"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    m = await milestones_col.find_one({"id": mid}, {"_id": 0})
    if not m:
        raise HTTPException(status_code=404, detail="Milestone not found")
    await milestones_col.update_one({"id": mid}, {"$set": {
        "status": "paid",
        "paid_at": datetime.now(timezone.utc),
        "paid_method": "manual",
    }})
    return {"ok": True}


@milestones_router.delete("/{mid}")
async def delete_milestone(mid: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["partner", "admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    await milestones_col.delete_one({"id": mid})
    return {"ok": True}
