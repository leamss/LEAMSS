"""Phase 4C.1 — Vendor Categories + Vendor Master Router.

Endpoints:
  Categories:
    GET    /api/vendors/categories
    POST   /api/vendors/categories               (admin)
    PATCH  /api/vendors/categories/{key}         (admin)

  Vendors:
    GET    /api/vendors                          (filters: category, status, vendor_type, q)
    GET    /api/vendors/{id}
    POST   /api/vendors                          (admin)
    PATCH  /api/vendors/{id}                     (admin)
    POST   /api/vendors/{id}/deactivate          (admin)
    POST   /api/vendors/{id}/activate            (admin)
    POST   /api/vendors/{id}/send-portal-invite  (admin — magic-link/email)
    GET    /api/vendors/{id}/earnings-summary    (lifetime stats, lazy until 4C.3 lands)
"""
import uuid
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field
from fastapi import APIRouter, Depends, HTTPException, Query

from core.auth import get_current_user
from core.database import db, users_col, notifications_col

router = APIRouter(prefix="/vendors", tags=["Phase 4C - Vendors"])

vendor_categories_col = db["vendor_categories"]
vendors_col = db["vendors"]
vendor_counters_col = db["vendor_counters"]
magic_col = db["magic_links"]


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────
def _is_admin(u: dict) -> bool:
    return u.get("role") in ("admin", "admin_owner") or u.get("rbac_role") in ("admin", "admin_owner")


def _can_view_vendors(u: dict) -> bool:
    """Admin, HR head, Accounts head can view all vendors."""
    if _is_admin(u):
        return True
    perms = u.get("permissions") or []
    return "vendor.view.all" in perms or "vendor.create.any" in perms


def _can_manage_vendors(u: dict) -> bool:
    if _is_admin(u):
        return True
    return "vendor.create.any" in (u.get("permissions") or [])


def _mask_account_number(acc: Optional[str]) -> Optional[str]:
    if not acc:
        return None
    s = str(acc).strip()
    if len(s) <= 4:
        return "*" * len(s)
    return ("*" * (len(s) - 4)) + s[-4:]


def _strip_sensitive_bank(vendor: dict, current_user: dict) -> dict:
    """Returns a vendor dict with bank_details masked unless the requester is admin/finance OR the vendor themselves."""
    if not vendor:
        return vendor
    is_self = vendor.get("user_id") and vendor["user_id"] == current_user.get("id")
    is_admin_finance = _is_admin(current_user) or "vendor.view.all" in (current_user.get("permissions") or [])
    bank = vendor.get("bank_details") or {}
    if not (is_self or is_admin_finance):
        vendor["bank_details"] = {
            "account_holder": bank.get("account_holder"),
            "account_number": _mask_account_number(bank.get("account_number")),
            "ifsc": bank.get("ifsc"),
            "bank_name": bank.get("bank_name"),
        }
    return vendor


def _clean(d: dict) -> dict:
    if not d:
        return d
    d.pop("_id", None)
    for k in ("created_at", "updated_at", "joined_at", "last_payment_at"):
        v = d.get(k)
        if isinstance(v, datetime):
            d[k] = v.isoformat()
    return d


async def _next_vendor_code() -> str:
    """Atomic sequential code: VND-2026-0001, VND-2026-0002 ..."""
    year = datetime.now(timezone.utc).year
    res = await vendor_counters_col.find_one_and_update(
        {"year": year},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
    )
    seq = res["seq"] if res and "seq" in res else 1
    return f"VND-{year}-{seq:04d}"


# ──────────────────────────────────────────────────────────────
# Models
# ──────────────────────────────────────────────────────────────
class VendorCategoryCreate(BaseModel):
    key: str = Field(..., pattern=r"^[a-z_]+$", max_length=40)
    name: str
    description: Optional[str] = ""
    icon: Optional[str] = "Briefcase"  # lucide-react icon name
    color: Optional[str] = "slate"
    default_payment_type: str = "flat"  # flat | percentage | hourly | per_document
    is_internal: bool = False
    linked_role: Optional[str] = None


class VendorCategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    default_payment_type: Optional[str] = None
    is_internal: Optional[bool] = None
    linked_role: Optional[str] = None
    is_active: Optional[bool] = None


class BankDetailsModel(BaseModel):
    account_holder: Optional[str] = None
    account_number: Optional[str] = None  # stored as-is; masked on read for non-privileged
    ifsc: Optional[str] = None
    bank_name: Optional[str] = None


class PaymentTermsModel(BaseModel):
    payment_type: str = "flat"  # flat | percentage | hourly | per_document
    default_amount: float = 0
    currency: str = "INR"


class VendorCreate(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = ""
    category: str  # FK key in vendor_categories
    specialization: List[str] = []
    vendor_type: str = "external"  # internal | external | freelancer
    user_id: Optional[str] = None  # link to users collection (internal vendors)

    default_payment_terms: Optional[PaymentTermsModel] = None
    bank_details: Optional[BankDetailsModel] = None
    pan_number: Optional[str] = None
    gst_number: Optional[str] = None

    tds_applicable: bool = True
    tds_rate: float = 10.0

    can_login: bool = False
    notes: Optional[str] = ""


class VendorUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    category: Optional[str] = None
    specialization: Optional[List[str]] = None
    vendor_type: Optional[str] = None
    default_payment_terms: Optional[PaymentTermsModel] = None
    bank_details: Optional[BankDetailsModel] = None
    pan_number: Optional[str] = None
    gst_number: Optional[str] = None
    tds_applicable: Optional[bool] = None
    tds_rate: Optional[float] = None
    can_login: Optional[bool] = None
    notes: Optional[str] = None


# ══════════════════════════════════════════════════════════════
# CATEGORIES
# ══════════════════════════════════════════════════════════════
@router.get("/categories")
async def list_categories(current_user: dict = Depends(get_current_user)):
    items = await vendor_categories_col.find({"is_active": True}, {"_id": 0}).sort("name", 1).to_list(200)
    return {"categories": [_clean(c) for c in items], "count": len(items)}


@router.post("/categories")
async def create_category(req: VendorCategoryCreate, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    existing = await vendor_categories_col.find_one({"key": req.key}, {"_id": 0, "key": 1})
    if existing:
        raise HTTPException(status_code=409, detail=f"Category '{req.key}' already exists")
    now = datetime.now(timezone.utc)
    doc = {
        "id": str(uuid.uuid4()),
        **req.model_dump(),
        "is_active": True,
        "is_system": False,
        "created_at": now,
        "created_by": current_user["id"],
    }
    await vendor_categories_col.insert_one(doc)
    return {"ok": True, "category": _clean(doc)}


@router.patch("/categories/{key}")
async def update_category(key: str, req: VendorCategoryUpdate, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    update = {k: v for k, v in req.model_dump(exclude_unset=True).items() if v is not None}
    if not update:
        return {"ok": True, "no_change": True}
    update["updated_at"] = datetime.now(timezone.utc)
    res = await vendor_categories_col.update_one({"key": key}, {"$set": update})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"ok": True}


# ══════════════════════════════════════════════════════════════
# VENDORS — LIST + CRUD
# ══════════════════════════════════════════════════════════════
@router.get("")
async def list_vendors(
    category: Optional[str] = None,
    status: Optional[str] = None,
    vendor_type: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = Query(100, le=500),
    current_user: dict = Depends(get_current_user),
):
    if not _can_view_vendors(current_user):
        raise HTTPException(status_code=403, detail="Not authorized to view vendors")
    qry: Dict[str, Any] = {}
    if category:
        qry["category"] = category
    if status:
        qry["status"] = status
    if vendor_type:
        qry["vendor_type"] = vendor_type
    if q:
        qry["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"email": {"$regex": q, "$options": "i"}},
            {"vendor_code": {"$regex": q, "$options": "i"}},
        ]
    cursor = vendors_col.find(qry, {"_id": 0}).sort("created_at", -1).limit(limit)
    items = await cursor.to_list(length=limit)
    cleaned = [_strip_sensitive_bank(_clean(v), current_user) for v in items]

    # Summary stats
    total = await vendors_col.count_documents({})
    active = await vendors_col.count_documents({"status": "active"})
    by_category: Dict[str, int] = {}
    async for v in vendors_col.find({}, {"_id": 0, "category": 1}):
        by_category[v["category"]] = by_category.get(v["category"], 0) + 1

    return {
        "vendors": cleaned,
        "count": len(cleaned),
        "stats": {"total": total, "active": active, "by_category": by_category},
    }


@router.get("/{vendor_id}")
async def get_vendor(vendor_id: str, current_user: dict = Depends(get_current_user)):
    if not _can_view_vendors(current_user):
        raise HTTPException(status_code=403, detail="Not authorized")
    v = await vendors_col.find_one({"id": vendor_id}, {"_id": 0})
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return _strip_sensitive_bank(_clean(v), current_user)


@router.post("")
async def create_vendor(req: VendorCreate, current_user: dict = Depends(get_current_user)):
    if not _can_manage_vendors(current_user):
        raise HTTPException(status_code=403, detail="Admin only")

    cat = await vendor_categories_col.find_one({"key": req.category, "is_active": True}, {"_id": 0, "key": 1, "default_payment_type": 1, "is_internal": 1, "name": 1})
    if not cat:
        raise HTTPException(status_code=400, detail=f"Unknown or inactive category '{req.category}'")

    existing_email = await vendors_col.find_one({"email": req.email.lower()}, {"_id": 0, "id": 1})
    if existing_email:
        raise HTTPException(status_code=409, detail=f"Vendor with email '{req.email}' already exists")

    if req.user_id:
        linked = await users_col.find_one({"id": req.user_id}, {"_id": 0, "id": 1})
        if not linked:
            raise HTTPException(status_code=400, detail="Linked user_id not found")

    code = await _next_vendor_code()
    now = datetime.now(timezone.utc)

    # ─────────────────────────────────────────────────────────
    # Phase 4C — Auto-create user account for INTERNAL vendors
    # If vendor_type='internal' AND no user_id provided AND user with this
    # email does not already exist, we create a User record with the right
    # role so they automatically appear in their respective portal.
    # ─────────────────────────────────────────────────────────
    auto_created_user_id: Optional[str] = None
    auto_created_user_temp_password: Optional[str] = None
    if req.vendor_type == "internal" and not req.user_id and cat.get("is_internal"):
        existing_user = await users_col.find_one({"email": req.email.lower()}, {"_id": 0, "id": 1})
        if existing_user:
            auto_created_user_id = existing_user["id"]
        else:
            # Map vendor category → user role
            CATEGORY_TO_ROLE = {
                "case_manager": "case_manager",
                "sales_commission": "sales_executive",
            }
            target_role = CATEGORY_TO_ROLE.get(req.category)
            if target_role:
                import secrets as _secrets
                from core.auth import get_password_hash
                # Auto-generate a temp password — admin will see it on screen
                auto_created_user_temp_password = f"Welcome@{_secrets.token_urlsafe(6)}"
                user_doc = {
                    "id": str(uuid.uuid4()),
                    "name": req.name.strip(),
                    "email": req.email.lower(),
                    "mobile": req.phone or "",
                    "password": get_password_hash(auto_created_user_temp_password),
                    "role": target_role,
                    "rbac_role": target_role,
                    "user_type": "internal",
                    "department": None,
                    "permissions": [],
                    "ui_modules": [],
                    "status": "active",
                    "must_change_password_on_next_login": True,
                    "auto_created_from_vendor": True,
                    "password_changed_at": now,
                    "created_at": now,
                    "created_by": current_user["id"],
                }
                await users_col.insert_one(user_doc)
                auto_created_user_id = user_doc["id"]

    payment_terms = req.default_payment_terms.model_dump() if req.default_payment_terms else {
        "payment_type": cat.get("default_payment_type") or "flat",
        "default_amount": 0,
        "currency": "INR",
    }

    doc = {
        "id": str(uuid.uuid4()),
        "vendor_code": code,
        "name": req.name.strip(),
        "email": req.email.lower(),
        "phone": req.phone or "",
        "category": req.category,
        "specialization": req.specialization or [],
        "vendor_type": req.vendor_type,
        "user_id": auto_created_user_id or req.user_id,
        "default_payment_terms": payment_terms,
        "bank_details": (req.bank_details.model_dump() if req.bank_details else {}),
        "pan_number": req.pan_number or "",
        "gst_number": req.gst_number or "",
        "tds_applicable": bool(req.tds_applicable),
        "tds_rate": float(req.tds_rate),
        "performance": {"total_cases_handled": 0, "total_paid_lifetime": 0.0, "rating": 0.0},
        "status": "active",
        "joined_at": now,
        "last_payment_at": None,
        "can_login": bool(req.can_login) or bool(auto_created_user_id),
        "portal_credentials_sent": False,
        "notes": req.notes or "",
        "created_at": now,
        "updated_at": now,
        "created_by": current_user["id"],
    }
    await vendors_col.insert_one(doc)
    response: Dict[str, Any] = {"ok": True, "vendor": _clean(doc)}
    if auto_created_user_temp_password:
        response["auto_created_user"] = {
            "user_id": auto_created_user_id,
            "email": req.email.lower(),
            "temp_password": auto_created_user_temp_password,
            "role": doc["vendor_type"],
            "message": f"User account auto-created for {cat.get('name')}. Share these temp credentials with the user — they will be asked to change the password on first login.",
        }
    elif auto_created_user_id:
        response["auto_created_user"] = {
            "user_id": auto_created_user_id,
            "email": req.email.lower(),
            "message": "Existing user with this email was linked to the vendor.",
        }
    return response


@router.patch("/{vendor_id}")
async def update_vendor(vendor_id: str, req: VendorUpdate, current_user: dict = Depends(get_current_user)):
    if not _can_manage_vendors(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    v = await vendors_col.find_one({"id": vendor_id}, {"_id": 0, "id": 1})
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found")

    update = {}
    for k, val in req.model_dump(exclude_unset=True).items():
        if val is None:
            continue
        if k == "default_payment_terms":
            update[k] = val
        elif k == "bank_details":
            update[k] = val
        elif k == "email":
            update[k] = val.lower()
        else:
            update[k] = val

    if not update:
        return {"ok": True, "no_change": True}
    update["updated_at"] = datetime.now(timezone.utc)
    await vendors_col.update_one({"id": vendor_id}, {"$set": update})
    return {"ok": True}


@router.post("/{vendor_id}/deactivate")
async def deactivate_vendor(vendor_id: str, current_user: dict = Depends(get_current_user)):
    if not _can_manage_vendors(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    res = await vendors_col.update_one(
        {"id": vendor_id},
        {"$set": {"status": "inactive", "deactivated_by": current_user["id"], "deactivated_at": datetime.now(timezone.utc)}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return {"ok": True, "status": "inactive"}


@router.post("/{vendor_id}/activate")
async def activate_vendor(vendor_id: str, current_user: dict = Depends(get_current_user)):
    if not _can_manage_vendors(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    res = await vendors_col.update_one(
        {"id": vendor_id},
        {"$set": {"status": "active", "activated_by": current_user["id"], "activated_at": datetime.now(timezone.utc)}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return {"ok": True, "status": "active"}


# ══════════════════════════════════════════════════════════════
# PORTAL INVITE
# ══════════════════════════════════════════════════════════════
@router.post("/{vendor_id}/send-portal-invite")
async def send_portal_invite(vendor_id: str, current_user: dict = Depends(get_current_user)):
    """Generates a 72h magic link for the vendor. Email dispatch is mocked (Resend not live)."""
    if not _can_manage_vendors(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    v = await vendors_col.find_one({"id": vendor_id}, {"_id": 0})
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found")
    if v.get("status") != "active":
        raise HTTPException(status_code=400, detail="Vendor must be active to receive a portal invite")

    # Reuse the magic_links collection (already used for client logins)
    token = secrets.token_urlsafe(28)
    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=72)

    # If vendor has no linked user_id, we create a placeholder lookup record (so the magic-link consumer
    # can resolve to a user once they accept). For now, store vendor_id + intended_role.
    await magic_col.insert_one({
        "id": str(uuid.uuid4()),
        "token": token,
        "user_id": v.get("user_id"),  # may be null — consumer creates user record on first use
        "vendor_id": vendor_id,
        "kind": "vendor_invite",
        "expires_at": expires,
        "used": False,
        "is_preview": False,
        "issued_by": current_user["id"],
        "created_at": now,
    })

    # Update vendor record
    await vendors_col.update_one(
        {"id": vendor_id},
        {"$set": {"portal_credentials_sent": True, "last_invite_sent_at": now}},
    )

    # MOCK email — log only. Real Resend integration is a future task.
    frontend_url = (await db["app_config"].find_one({"key": "frontend_url"}, {"_id": 0, "value": 1}) or {}).get("value")
    base = frontend_url or ""
    invite_url = f"{base}/vendor/accept-invite/{token}" if base else f"/vendor/accept-invite/{token}"

    # In-app notification to the issuing admin so they can see + share the link
    await notifications_col.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "title": f"Portal invite for {v.get('name')}",
        "message": f"Magic link valid for 72h: {invite_url}",
        "type": "vendor_invite",
        "read": False,
        "link": "/admin/vendors",
        "created_at": now,
    })

    return {
        "ok": True,
        "invite_url": invite_url,
        "expires_at": expires.isoformat(),
        "mock_email_sent": True,
        "message": "Portal invite created. Email integration is MOCKED — share the URL directly for now.",
    }


# ══════════════════════════════════════════════════════════════
# Earnings summary (Stub — full impl in 4C.3)
# ══════════════════════════════════════════════════════════════
@router.get("/{vendor_id}/earnings-summary")
async def vendor_earnings_summary(vendor_id: str, current_user: dict = Depends(get_current_user)):
    if not _can_view_vendors(current_user):
        raise HTTPException(status_code=403, detail="Not authorized")
    v = await vendors_col.find_one({"id": vendor_id}, {"_id": 0, "id": 1, "performance": 1, "last_payment_at": 1})
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return {
        "vendor_id": vendor_id,
        "lifetime_paid": (v.get("performance") or {}).get("total_paid_lifetime", 0),
        "total_cases_handled": (v.get("performance") or {}).get("total_cases_handled", 0),
        "rating": (v.get("performance") or {}).get("rating", 0),
        "last_payment_at": v.get("last_payment_at").isoformat() if isinstance(v.get("last_payment_at"), datetime) else None,
        # Detailed allocation data will be wired in Sub-phase 4C.3
        "note": "Allocation-level earnings will activate after Sub-phase 4C.3 (Auto-Allocation Engine)",
    }
