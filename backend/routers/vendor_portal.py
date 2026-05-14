"""Phase 4C.6 — External Vendor Portal.

External vendors (tutors, lawyers, freelancers) get a dedicated read-only portal.
They onboard via magic-link → set password → log in normally with their email.

Endpoints:
  POST /api/vendor-portal/accept-invite     (public — consumes magic link)
  GET  /api/vendor-portal/me                (vendor)
  GET  /api/vendor-portal/my-assignments    (vendor)
  GET  /api/vendor-portal/my-payments       (vendor)
  PATCH /api/vendor-portal/me               (vendor — update phone/bank)
"""
import secrets
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException

from core.auth import get_current_user, get_password_hash, validate_password_strength
from core.database import db, users_col

router = APIRouter(prefix="/vendor-portal", tags=["Phase 4C.6 - Vendor Portal"])

vendors_col = db["vendors"]
magic_col = db["magic_links"]
allocations_col = db["pa_cost_allocations"]


def _clean(d: dict) -> dict:
    if not d:
        return d
    d.pop("_id", None)
    for k in ("created_at", "updated_at", "joined_at", "last_payment_at", "expires_at", "issued_at"):
        v = d.get(k)
        if isinstance(v, datetime):
            d[k] = v.isoformat()
    return d


def _mask_account(acc: Optional[str]) -> Optional[str]:
    if not acc:
        return None
    s = str(acc)
    if len(s) <= 4:
        return "*" * len(s)
    return ("*" * (len(s) - 4)) + s[-4:]


async def _resolve_vendor_for_user(user: dict) -> Optional[Dict[str, Any]]:
    """Match a vendor record by user_id or email."""
    v = await vendors_col.find_one({"user_id": user["id"]}, {"_id": 0})
    if v:
        return v
    if user.get("email"):
        v = await vendors_col.find_one({"email": user["email"].lower()}, {"_id": 0})
    return v


# ──────────────────────────────────────────────────────────────
# 1) Magic-link acceptance (public)
# ──────────────────────────────────────────────────────────────
class AcceptInviteRequest(BaseModel):
    token: str
    password: str = Field(..., min_length=8)


@router.post("/accept-invite")
async def accept_invite(req: AcceptInviteRequest):
    """Consumes vendor invite magic link. Creates/updates user, links to vendor."""
    mlink = await magic_col.find_one({"token": req.token, "kind": "vendor_invite"}, {"_id": 0})
    if not mlink:
        raise HTTPException(status_code=404, detail="Invite token not found")
    if mlink.get("used"):
        raise HTTPException(status_code=410, detail="Invite already used")
    expires = mlink.get("expires_at")
    if isinstance(expires, datetime):
        # Mongo may return naive datetimes; normalize both sides
        exp_aware = expires if expires.tzinfo else expires.replace(tzinfo=timezone.utc)
        if exp_aware < datetime.now(timezone.utc):
            raise HTTPException(status_code=410, detail="Invite expired")

    vendor_id = mlink.get("vendor_id")
    if not vendor_id:
        raise HTTPException(status_code=400, detail="Invalid invite — no vendor linked")
    vendor = await vendors_col.find_one({"id": vendor_id}, {"_id": 0})
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor record missing")

    # Password strength
    is_ok, msg = validate_password_strength(req.password)
    if not is_ok:
        raise HTTPException(status_code=400, detail=msg)

    # Create / update user record
    existing_user = None
    if vendor.get("user_id"):
        existing_user = await users_col.find_one({"id": vendor["user_id"]}, {"_id": 0})
    if not existing_user and vendor.get("email"):
        existing_user = await users_col.find_one({"email": vendor["email"]}, {"_id": 0})

    now = datetime.now(timezone.utc)
    if existing_user:
        await users_col.update_one(
            {"id": existing_user["id"]},
            {"$set": {
                "password": get_password_hash(req.password),
                "password_changed_at": now,
                "must_change_password_on_next_login": False,
                "two_fa_enabled": False,
                "status": "active",
                "updated_at": now,
            }}
        )
        user_id = existing_user["id"]
    else:
        # Create new user record for the vendor
        import uuid as _uuid
        user_id = str(_uuid.uuid4())
        await users_col.insert_one({
            "id": user_id,
            "name": vendor["name"],
            "email": vendor["email"],
            "mobile": vendor.get("phone") or "",
            "password": get_password_hash(req.password),
            "role": "vendor",
            "rbac_role": "vendor",
            "user_type": "external",
            "department": None,
            "permissions": ["vendor.view.own", "allocation.view.own"],
            "ui_modules": ["vendor_dashboard"],
            "status": "active",
            "password_changed_at": now,
            "created_at": now,
        })

    await vendors_col.update_one(
        {"id": vendor_id},
        {"$set": {
            "user_id": user_id,
            "portal_activated_at": now,
            "updated_at": now,
        }}
    )
    await magic_col.update_one(
        {"token": req.token},
        {"$set": {"used": True, "used_at": now, "used_for_user_id": user_id}}
    )
    return {"ok": True, "vendor_id": vendor_id, "user_id": user_id, "message": "Account activated. You can now sign in with your email + password."}


# ──────────────────────────────────────────────────────────────
# 2) Self-service endpoints
# ──────────────────────────────────────────────────────────────
@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    vendor = await _resolve_vendor_for_user(current_user)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor record not found for this user")
    # Always show full bank details to vendor themselves
    return _clean(vendor)


class UpdateProfileReq(BaseModel):
    phone: Optional[str] = None
    bank_details: Optional[Dict[str, Any]] = None
    pan_number: Optional[str] = None
    gst_number: Optional[str] = None


@router.patch("/me")
async def update_me(req: UpdateProfileReq, current_user: dict = Depends(get_current_user)):
    vendor = await _resolve_vendor_for_user(current_user)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor record not found")
    update: Dict[str, Any] = {}
    for k, v in req.model_dump(exclude_unset=True).items():
        if v is None:
            continue
        update[k] = v
    if not update:
        return {"ok": True, "no_change": True}
    update["updated_at"] = datetime.now(timezone.utc)
    await vendors_col.update_one({"id": vendor["id"]}, {"$set": update})
    return {"ok": True}


@router.get("/my-assignments")
async def my_assignments(current_user: dict = Depends(get_current_user)):
    """List all allocations across PAs where this vendor is assigned."""
    vendor = await _resolve_vendor_for_user(current_user)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor record not found")

    uid = current_user["id"]
    vendor_id = vendor["id"]
    qry = {"allocations": {"$elemMatch": {"$or": [{"vendor_id": uid}, {"vendor_master_id": vendor_id}]}}}
    cursor = allocations_col.find(qry, {"_id": 0})

    rows = []
    totals = {"pending": 0.0, "approved": 0.0, "paid": 0.0, "disputed": 0.0}
    async for doc in cursor:
        for a in (doc.get("allocations") or []):
            if a.get("vendor_id") != uid and a.get("vendor_master_id") != vendor_id:
                continue
            amt = float(a.get("total_amount") or 0)
            st = a.get("status") or "pending"
            if st in totals:
                totals[st] += amt
            rows.append({
                "pa_id": doc.get("pa_id"),
                "pa_number": doc.get("pa_number"),
                "client_name": doc.get("client_name"),
                "label": a.get("label"),
                "vendor_category": a.get("vendor_category"),
                "amount": amt,
                "status": st,
                "bonus_amount": float(a.get("bonus_amount") or 0),
                "assigned_at": a.get("assigned_at"),
                "approved_at": a.get("approved_at"),
                "paid_at": a.get("paid_at"),
                "payment_reference": a.get("payment_reference"),
            })
    rows.sort(key=lambda x: x.get("paid_at") or x.get("approved_at") or x.get("assigned_at") or "", reverse=True)
    return {
        "vendor_id": vendor_id,
        "vendor_code": vendor.get("vendor_code"),
        "vendor_name": vendor.get("name"),
        "assignments": rows,
        "count": len(rows),
        "totals": {k: round(v, 2) for k, v in totals.items()},
        "lifetime_paid": round(totals["paid"], 2),
    }


@router.get("/my-payments")
async def my_payments(current_user: dict = Depends(get_current_user)):
    """Lifetime payment history (paid status only)."""
    vendor = await _resolve_vendor_for_user(current_user)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor record not found")
    uid = current_user["id"]
    vid = vendor["id"]
    qry = {"allocations": {"$elemMatch": {"status": "paid", "$or": [{"vendor_id": uid}, {"vendor_master_id": vid}]}}}
    cursor = allocations_col.find(qry, {"_id": 0})
    rows = []
    async for doc in cursor:
        for a in (doc.get("allocations") or []):
            if a.get("status") != "paid":
                continue
            if a.get("vendor_id") != uid and a.get("vendor_master_id") != vid:
                continue
            rows.append({
                "pa_number": doc.get("pa_number"),
                "client_name": doc.get("client_name"),
                "amount": float(a.get("total_amount") or 0),
                "paid_at": a.get("paid_at"),
                "payment_reference": a.get("payment_reference"),
            })
    rows.sort(key=lambda x: x.get("paid_at") or "", reverse=True)
    return {"payments": rows, "count": len(rows), "lifetime_total": round(sum(r["amount"] for r in rows), 2)}
