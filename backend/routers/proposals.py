"""Phase 20.8 — Proposal Builder router (auto-populates from PA review approval).

A Proposal pulls together: PA Review (admin-approved required) + Product +
Professional Fees Policy + Add-on products + Applied Coupons + Admin special
discount → cascading totals → WeasyPrint PDF.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from core.auth import get_current_user
from core.database import db
from services import import_batch_service as ibs
from services.audit_service import log_action

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/proposals", tags=["Phase 20.8 Proposals"])
COLL = "proposals"
PA_COLL = "pre_assessments"
REVIEWS_COLL = "pre_assessment_reviews"
PRODUCTS_COLL = "products"

ADMIN_ROLES = {"admin", "admin_owner", "super_admin", "case_manager", "case_manager_lead"}
SALES_ROLES = ADMIN_ROLES | {"sales", "sales_executive", "sr_sales_executive",
                              "sales_manager", "sales_head", "partner"}

GST_PCT = 18


def _is_sales(u): r = (u.get("rbac_role") or u.get("role") or "").lower(); return r in SALES_ROLES or "*" in (u.get("permissions") or [])
def _is_admin(u): r = (u.get("rbac_role") or u.get("role") or "").lower(); return r in ADMIN_ROLES or "*" in (u.get("permissions") or [])


def _serialise(d: Dict[str, Any]) -> Dict[str, Any]:
    d.pop("_id", None)
    for k, v in list(d.items()):
        if isinstance(v, datetime):
            d[k] = v.isoformat()
    return d


class ProposalCreate(BaseModel):
    client_id: str
    product_id: str
    pa_review_id: Optional[str] = None
    base_fees_inr: int = Field(..., ge=0)
    addon_products: List[Dict[str, Any]] = Field(default_factory=list)
    applied_coupon_codes: List[str] = Field(default_factory=list)
    admin_special_discount_inr: int = Field(default=0, ge=0)
    admin_special_discount_reason: Optional[str] = Field(None, max_length=500)
    closing_message: Optional[str] = Field(None, max_length=2000)
    custom_terms: Optional[str] = Field(None, max_length=2000)


def _compute_totals(
    base_fees: int, addons: List[Dict[str, Any]],
    coupon_discounts: List[Dict[str, Any]], admin_discount: int,
) -> Dict[str, int]:
    addon_total = sum(int(a.get("price_inr") or 0) for a in addons)
    coupon_total = sum(int(c.get("discount_amount_inr") or 0) for c in coupon_discounts)
    subtotal_pre = base_fees + addon_total
    subtotal = max(0, subtotal_pre - coupon_total - admin_discount)
    gst = int(subtotal * GST_PCT / 100)
    total = subtotal + gst
    return {
        "addon_total_inr": addon_total,
        "coupon_total_inr": coupon_total,
        "admin_discount_inr": admin_discount,
        "subtotal_pre_discount_inr": subtotal_pre,
        "subtotal_inr": subtotal,
        "gst_inr": gst, "gst_pct": GST_PCT,
        "total_inr": total,
    }


@router.post("")
async def create_proposal(
    payload: ProposalCreate, current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not _is_sales(current_user):
        raise HTTPException(status_code=403, detail="Forbidden")

    # Validate references
    product = await db[PRODUCTS_COLL].find_one({"id": payload.product_id})
    if not product:
        raise HTTPException(status_code=400, detail=f"Unknown product_id: {payload.product_id}")

    # PA review optional but if provided, must be approved
    if payload.pa_review_id:
        rev = await db[REVIEWS_COLL].find_one({"id": payload.pa_review_id})
        if not rev:
            raise HTTPException(status_code=400, detail="PA review not found")
        if rev["status"] != "approved":
            raise HTTPException(status_code=400, detail=f"PA review must be approved (current: {rev['status']})")

    # Resolve coupons → discount amounts
    coupon_discounts: List[Dict[str, Any]] = []
    order_pre_coupon = payload.base_fees_inr + sum(int(a.get("price_inr") or 0) for a in payload.addon_products)
    for code in payload.applied_coupon_codes:
        c = await db["coupons"].find_one({"code": code.upper()})
        if not c:
            continue
        if c["discount_type"] == "pct":
            dval = int(order_pre_coupon * c["discount_value"] / 100)
        else:
            dval = min(int(c["discount_value"]), order_pre_coupon)
        coupon_discounts.append({
            "code": c["code"], "description": c["description"],
            "discount_amount_inr": dval,
        })

    totals = _compute_totals(
        payload.base_fees_inr, payload.addon_products,
        coupon_discounts, payload.admin_special_discount_inr,
    )

    user_id = str(current_user.get("id") or "system")
    now = datetime.now(timezone.utc)
    doc = {
        "id": str(uuid.uuid4()),
        "client_id": payload.client_id, "product_id": payload.product_id,
        "pa_review_id": payload.pa_review_id,
        "product_name": product.get("name"),
        "country": product.get("country"), "service_type": product.get("service_type"),
        "base_fees_inr": payload.base_fees_inr,
        "addon_products": payload.addon_products,
        "applied_coupons": coupon_discounts,
        "admin_special_discount_inr": payload.admin_special_discount_inr,
        "admin_special_discount_reason": payload.admin_special_discount_reason,
        **totals,
        "closing_message": payload.closing_message,
        "custom_terms": payload.custom_terms,
        "status": "draft",
        "sent_at": None, "viewed_at": None,
        "accepted_at": None, "declined_at": None,
        "expires_at": now + timedelta(days=30),
        "created_by": user_id, "created_at": now, "updated_at": now,
    }

    body = f"create_proposal_{doc['id']}".encode()
    batch = await ibs.open_batch(
        db, ingestion_path="phase_20.8_proposal.create",
        endpoint="POST /api/proposals",
        uploaded_by=user_id, uploaded_by_name=current_user.get("name") or user_id,
        file_name=f"proposal_{doc['id']}", file_hash=ibs.file_sha256(body),
        file_size_bytes=len(body), target_collection=COLL,
    )
    await db[COLL].insert_one(doc)
    ibs.record_create(batch, doc["id"], {"client_id": payload.client_id})
    await ibs.close_batch(db, batch, total_rows=1, status="committed")
    await log_action(db, action="proposal.create", user_id=user_id, severity="info",
                     summary={"proposal_id": doc["id"], "total_inr": totals["total_inr"],
                              "batch_id": batch["batch_id"]})
    return _serialise(doc)


@router.get("/{proposal_id}")
async def get_proposal(
    proposal_id: str, current_user: Dict[str, Any] = Depends(get_current_user),
):
    p = await db[COLL].find_one({"id": proposal_id})
    if not p:
        raise HTTPException(status_code=404, detail="Proposal not found")
    is_self = str(current_user.get("id")) == p.get("client_id")
    if not (_is_sales(current_user) or is_self):
        raise HTTPException(status_code=403, detail="Forbidden")
    return _serialise(p)


@router.post("/{proposal_id}/send")
async def send_proposal(
    proposal_id: str, current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not _is_sales(current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    p = await db[COLL].find_one({"id": proposal_id})
    if not p:
        raise HTTPException(status_code=404, detail="Proposal not found")
    if p["status"] not in ("draft",):
        raise HTTPException(status_code=400, detail=f"Cannot send from status: {p['status']}")
    now = datetime.now(timezone.utc)
    await db[COLL].update_one({"id": proposal_id},
                              {"$set": {"status": "sent", "sent_at": now,
                                        "updated_at": now}})
    logger.info(f"[Phase20.8] Proposal {proposal_id} sent (email preview — Resend API key pending)")
    return {"ok": True, "proposal_id": proposal_id, "status": "sent",
            "delivery": "EMAIL_PREVIEW_LOGGED", "expires_at": p.get("expires_at")}


@router.post("/{proposal_id}/accept")
async def accept_proposal(
    proposal_id: str, current_user: Dict[str, Any] = Depends(get_current_user),
):
    p = await db[COLL].find_one({"id": proposal_id})
    if not p:
        raise HTTPException(status_code=404, detail="Proposal not found")
    # Client or admin can accept
    is_self = str(current_user.get("id")) == p.get("client_id")
    if not (_is_admin(current_user) or is_self):
        raise HTTPException(status_code=403, detail="Forbidden")
    if p["status"] not in ("sent", "viewed"):
        raise HTTPException(status_code=400, detail=f"Cannot accept from status: {p['status']}")
    now = datetime.now(timezone.utc)
    await db[COLL].update_one({"id": proposal_id},
                              {"$set": {"status": "accepted", "accepted_at": now,
                                        "updated_at": now}})
    return {"ok": True, "proposal_id": proposal_id, "status": "accepted"}


class DeclineRequest(BaseModel):
    reason: str = Field(..., min_length=5, max_length=2000)


@router.post("/{proposal_id}/decline")
async def decline_proposal(
    proposal_id: str, payload: DeclineRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    p = await db[COLL].find_one({"id": proposal_id})
    if not p:
        raise HTTPException(status_code=404, detail="Proposal not found")
    is_self = str(current_user.get("id")) == p.get("client_id")
    if not (_is_admin(current_user) or is_self):
        raise HTTPException(status_code=403, detail="Forbidden")
    now = datetime.now(timezone.utc)
    await db[COLL].update_one({"id": proposal_id},
                              {"$set": {"status": "declined", "declined_at": now,
                                        "declined_reason": payload.reason,
                                        "updated_at": now}})
    return {"ok": True, "proposal_id": proposal_id, "status": "declined"}


@router.get("/{proposal_id}/pdf")
async def get_proposal_pdf(
    proposal_id: str, current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Render proposal as HTML (WeasyPrint PDF if available, else HTML download)."""
    p = await db[COLL].find_one({"id": proposal_id})
    if not p:
        raise HTTPException(status_code=404, detail="Proposal not found")
    is_self = str(current_user.get("id")) == p.get("client_id")
    if not (_is_sales(current_user) or is_self):
        raise HTTPException(status_code=403, detail="Forbidden")

    html = _render_proposal_html(p)
    try:
        from weasyprint import HTML
        pdf_bytes = HTML(string=html).write_pdf()
        return Response(content=pdf_bytes, media_type="application/pdf",
                       headers={"Content-Disposition": f"attachment; filename=proposal_{proposal_id}.pdf"})
    except Exception as e:
        logger.warning(f"WeasyPrint unavailable, returning HTML: {e}")
        return Response(content=html, media_type="text/html",
                       headers={"Content-Disposition": f"inline; filename=proposal_{proposal_id}.html"})


def _render_proposal_html(p: Dict[str, Any]) -> str:
    """Branded WeasyPrint-compatible HTML template (leamss.teal/orange/red)."""
    # Brand tokens (inline since WeasyPrint doesn't know our Tailwind config)
    teal = "#0d9488"
    orange = "#ea580c"
    red = "#dc2626"
    bg = "#ffffff"
    total = p.get("total_inr", 0)
    coupons_html = ""
    for c in p.get("applied_coupons", []):
        coupons_html += f'<tr><td>Coupon: <span style="color:{teal}">{c["code"]}</span> — {c.get("description","")}</td><td style="text-align:right;color:{teal}">−₹{c.get("discount_amount_inr", 0):,}</td></tr>'

    addons_html = ""
    for a in p.get("addon_products", []):
        addons_html += f'<tr><td>+ {a.get("name", "Add-on")}</td><td style="text-align:right">₹{a.get("price_inr", 0):,}</td></tr>'

    admin_disc_html = ""
    if p.get("admin_special_discount_inr", 0) > 0:
        admin_disc_html = (
            f'<tr><td>Admin Special Discount<br/><small style="color:#666">{p.get("admin_special_discount_reason","")}</small></td>'
            f'<td style="text-align:right;color:{red}">−₹{p["admin_special_discount_inr"]:,}</td></tr>'
        )

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>LEAMSS Proposal {p["id"][:8]}</title>
<style>
@page {{ size: A4; margin: 1.5cm; }}
body {{ font-family: 'Inter', Arial, sans-serif; color: #1f2937; background: {bg}; }}
.hdr {{ border-bottom: 4px solid {teal}; padding-bottom: 12px; margin-bottom: 20px; }}
.hdr h1 {{ color: {teal}; margin: 0; font-size: 28px; }}
.hdr p {{ margin: 2px 0; color: #6b7280; font-size: 12px; }}
h2 {{ color: {teal}; font-size: 16px; border-bottom: 1px solid #e5e7eb; padding-bottom: 4px; margin-top: 20px; }}
table.fees {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
table.fees td {{ padding: 6px 0; border-bottom: 1px solid #f3f4f6; font-size: 12px; }}
.total-row td {{ font-weight: bold; font-size: 16px; color: {orange}; border-top: 2px solid {orange}; padding-top: 10px; }}
.cta {{ background: {orange}; color: white; padding: 14px 28px; display: inline-block;
       border-radius: 6px; font-weight: bold; margin-top: 16px; }}
.kpi {{ display: inline-block; padding: 8px 12px; margin: 4px; border: 1px solid {teal};
       border-radius: 6px; font-size: 11px; }}
.section-box {{ border-left: 4px solid {teal}; padding-left: 12px; margin: 16px 0;
                background: #f0fdfa; padding: 10px 12px; }}
.footer {{ margin-top: 40px; padding-top: 12px; border-top: 1px solid #e5e7eb;
          font-size: 10px; color: #9ca3af; text-align: center; }}
.brand-strip {{ background: {teal}; color: white; padding: 4px 8px; font-weight: bold;
              font-size: 10px; letter-spacing: 0.1em; }}
</style></head>
<body>
<div class="brand-strip">LEAMSS · CONFIDENTIAL · PRODUCT &amp; SALES OS</div>
<div class="hdr">
  <h1>Migration Service Proposal</h1>
  <p>Reference: <strong>{p["id"][:12].upper()}</strong> · Date: {(p.get('created_at') or '')[:10]}</p>
  <p>For: <strong>{p.get('client_id','')}</strong> · Country: <strong>{p.get('country','')}</strong> · Visa: <strong>{p.get('service_type','')}</strong></p>
</div>

<h2>1. Executive Summary</h2>
<div class="section-box">
  <strong>Recommended Pathway:</strong> {p.get('product_name','')}<br/>
  <strong>Validity:</strong> Proposal valid until {(p.get('expires_at') or '')[:10]}<br/>
  <strong>Status:</strong> {p.get('status','draft').upper()}
</div>

<h2>2. Investment Breakdown</h2>
<table class="fees">
  <tr><td>Professional Fees ({p.get('product_name','')})</td>
      <td style="text-align:right">₹{p.get('base_fees_inr', 0):,}</td></tr>
  {addons_html}
  <tr><td><strong>Subtotal (before discounts)</strong></td>
      <td style="text-align:right"><strong>₹{p.get('subtotal_pre_discount_inr', 0):,}</strong></td></tr>
  {coupons_html}
  {admin_disc_html}
  <tr><td><strong>Subtotal (after discounts)</strong></td>
      <td style="text-align:right"><strong>₹{p.get('subtotal_inr', 0):,}</strong></td></tr>
  <tr><td>GST @ {GST_PCT}%</td>
      <td style="text-align:right">₹{p.get('gst_inr', 0):,}</td></tr>
  <tr class="total-row"><td>FINAL TOTAL</td>
      <td style="text-align:right">₹{total:,}</td></tr>
</table>

<h2>3. Closing Message</h2>
<p style="font-size:12px">{p.get('closing_message') or 'Aap ka business hum se choose karne ke liye dhanyavaad! Hum aap ki migration journey ko smooth + transparent + on-time deliver karne ke liye committed hain.'}</p>

{f'<h2>4. Custom Terms</h2><p style="font-size:11px">{p.get("custom_terms","")}</p>' if p.get('custom_terms') else ''}

<h2>5. Next Steps</h2>
<p style="font-size:12px">Accept this proposal via your LEAMSS Mini Portal or contact your case manager.</p>
<a href="#" class="cta">Accept &amp; Pay Securely</a>

<div class="footer">
  LEAMSS Immigration Services · Generated on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} · Phase 20.8 Builder
</div>
</body></html>"""
