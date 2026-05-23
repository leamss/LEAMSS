"""Phase 6.10 Part 2 — Professional Assessment Report Engine.

Distinct from `reports.py` (which serves sales analytics). This module owns the
client-facing branded Assessment Report PDFs generated from frozen snapshots.

Route prefix: /api/assessment-reports

Endpoints:
  POST   /generate                   — create immutable snapshot + return metadata
  GET    /                           — list reports (admin sees all, sales own)
  GET    /{snapshot_id}              — metadata
  GET    /{snapshot_id}/pdf          — stream the branded PDF
  POST   /{snapshot_id}/share        — create / refresh a public share token
  DELETE /{snapshot_id}/share        — revoke (admin / owner)
  POST   /{snapshot_id}/email        — mocked email send (logs to DB)
  GET    /public/{share_token}       — public metadata (no auth)
  GET    /public/{share_token}/pdf   — public PDF stream (no auth)
"""
import hashlib
import json
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

from core.auth import get_current_user
from core.database import db
from core.report_renderer import now_human, render_pdf

router = APIRouter(prefix="/assessment-reports", tags=["assessment-reports"])

REPORT_SNAPSHOTS = db["report_snapshots"]
REPORT_SHARES = db["report_shares"]
REPORT_EMAILS = db["report_emails"]
ASSESSMENTS = db["sales_assessments"]
OCCUPATION_MASTER = db["occupation_master"]
COUNTRY_TEMPLATES = db["country_templates"]
ADMIN_ROLES = {"admin", "admin_owner"}


def _is_admin(user: dict) -> bool:
    role = user.get("rbac_role") or user.get("role")
    return role in ADMIN_ROLES or "*" in (user.get("permissions") or [])


def _strip(d: dict) -> dict:
    if d and "_id" in d:
        d.pop("_id", None)
    return d


def _hash(payload: Any) -> str:
    s = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


async def _build_snapshot(
    assessment: Dict[str, Any], *,
    persona: str = "client", mode: str = "combined",
    include_unverified: bool = False,
) -> Dict[str, Any]:
    warnings: List[str] = []
    countries_data: List[Dict[str, Any]] = []
    results = assessment.get("results") or []
    targets = assessment.get("targets") or []

    for tgt in targets:
        cc = (tgt.get("country") or "").upper()
        result = next((r for r in results if (r.get("country_code") or "").upper() == cc), None)
        if not result:
            continue

        template = await COUNTRY_TEMPLATES.find_one({"country_code": cc}, {"_id": 0})
        if template and template.get("status") != "verified" and not include_unverified:
            warnings.append(
                f"Country template for {cc} is '{template.get('status')}' — admin verification pending."
            )
        country_name = (template or {}).get("country_name") or cc
        flag = (template or {}).get("flag") or ""
        pass_mark = (template or {}).get("pass_mark") or result.get("pass_mark")

        occ_doc: Optional[Dict[str, Any]] = None
        occ_block = assessment.get("occupation") or {}
        if occ_block and (occ_block.get("country_code") or "").upper() == cc:
            full = await OCCUPATION_MASTER.find_one(
                {"country_code": cc, "code": occ_block.get("code")}, {"_id": 0}
            )
            if full:
                if full.get("status") != "verified" and not include_unverified:
                    warnings.append(
                        f"Occupation {cc} · {full.get('code')} ({full.get('title')}) is "
                        f"'{full.get('status')}' — verify before sending to clients."
                    )
                occ_doc = full
            else:
                occ_doc = occ_block

        countries_data.append({
            "country_code": cc,
            "country_name": country_name,
            "flag": flag,
            "pass_mark": pass_mark,
            "visa_subclass": result.get("visa_subclass"),
            "total": result.get("total"),
            "breakdown": result.get("breakdown") or {},
            "visa_eligibility": result.get("visa_eligibility") or {},
            "recommendation": result.get("recommendation"),
            "template_status": (template or {}).get("status") or "none",
            "occupation": occ_doc,
        })

    best = max(countries_data, key=lambda c: (c.get("total") or 0)) if countries_data else None

    snap_data = {
        "assessment_id": assessment.get("id"),
        "persona": persona,
        "mode": mode,
        "client": {
            "name": assessment.get("client_name"),
            "email": assessment.get("client_email"),
            "phone": assessment.get("client_phone"),
        },
        "profile_snapshot": assessment.get("profile_snapshot") or {},
        "countries": countries_data,
        "best_country": best,
        "warnings": warnings,
        "generated_at_iso": datetime.now(timezone.utc).isoformat(),
        "generated_on_human": now_human(),
    }
    snap_data["data_integrity_hash"] = _hash(snap_data)
    return snap_data


# ─────────────────────────────────────────────────────────────────────────────
# Generate
# ─────────────────────────────────────────────────────────────────────────────
class GenerateRequest(BaseModel):
    assessment_id: str
    persona: str = "client"
    mode: str = "combined"
    target_country: Optional[str] = None
    include_unverified: bool = Field(False)


@router.post("/generate")
async def generate_report(req: GenerateRequest, current_user: dict = Depends(get_current_user)):
    a = await ASSESSMENTS.find_one({"id": req.assessment_id})
    if not a:
        raise HTTPException(status_code=404, detail="Assessment not found")
    if not _is_admin(current_user) and a.get("created_by") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not the owner")

    if req.mode == "single":
        if not req.target_country:
            raise HTTPException(status_code=400, detail="target_country required for mode='single'")
        cc = req.target_country.upper()
        a = dict(a)
        a["targets"] = [t for t in (a.get("targets") or []) if (t.get("country") or "").upper() == cc]
        a["results"] = [r for r in (a.get("results") or []) if (r.get("country_code") or "").upper() == cc]
        if not a["targets"]:
            raise HTTPException(status_code=400, detail=f"Assessment has no target for {cc}")

    snap_data = await _build_snapshot(
        a, persona=req.persona, mode=req.mode, include_unverified=req.include_unverified,
    )

    snapshot_id = f"RPT-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
    doc = {
        "snapshot_id": snapshot_id,
        "assessment_id": a.get("id"),
        "client_name": a.get("client_name"),
        "persona": req.persona,
        "mode": req.mode,
        "include_unverified": req.include_unverified,
        "data": snap_data,
        "warnings": snap_data.get("warnings") or [],
        "data_integrity_hash": snap_data["data_integrity_hash"],
        "generated_at": datetime.now(timezone.utc),
        "generated_by": current_user["id"],
        "generated_by_name": current_user.get("name") or current_user.get("email"),
        "is_immutable": True,
    }
    await REPORT_SNAPSHOTS.insert_one(doc)
    await ASSESSMENTS.update_one(
        {"id": a.get("id")},
        {"$push": {"report_snapshot_ids": snapshot_id},
         "$set": {"latest_report_snapshot_id": snapshot_id,
                  "latest_report_generated_at": datetime.now(timezone.utc)}},
    )
    return _strip(doc)


# ─────────────────────────────────────────────────────────────────────────────
# List + Get
# ─────────────────────────────────────────────────────────────────────────────
@router.get("")
async def list_reports(
    assessment_id: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    current_user: dict = Depends(get_current_user),
):
    q: Dict[str, Any] = {}
    if assessment_id:
        q["assessment_id"] = assessment_id
    if not _is_admin(current_user):
        q["generated_by"] = current_user["id"]
    items = []
    async for d in REPORT_SNAPSHOTS.find(q, {"_id": 0, "data": 0}).sort("generated_at", -1).limit(limit):
        items.append(_strip(d))
    return {"items": items, "count": len(items)}


@router.get("/{snapshot_id}")
async def get_report(snapshot_id: str, current_user: dict = Depends(get_current_user)):
    d = await REPORT_SNAPSHOTS.find_one({"snapshot_id": snapshot_id}, {"_id": 0})
    if not d:
        raise HTTPException(status_code=404, detail="Report not found")
    if not _is_admin(current_user) and d.get("generated_by") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not the owner")
    return _strip(d)


@router.get("/{snapshot_id}/pdf")
async def stream_pdf(snapshot_id: str, current_user: dict = Depends(get_current_user)):
    d = await REPORT_SNAPSHOTS.find_one({"snapshot_id": snapshot_id})
    if not d:
        raise HTTPException(status_code=404, detail="Report not found")
    if not _is_admin(current_user) and d.get("generated_by") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not the owner")
    snap_data = d.get("data") or {}
    snap_data["snapshot_id"] = d.get("snapshot_id")
    pdf_bytes = render_pdf(snap_data)
    filename = f"LEAMSS_Report_{(d.get('client_name') or 'client').replace(' ', '_')}_{snapshot_id}.pdf"
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


# ─────────────────────────────────────────────────────────────────────────────
# Share — public read-only magic links
# ─────────────────────────────────────────────────────────────────────────────
class ShareRequest(BaseModel):
    expires_in_days: int = Field(30, ge=1, le=365)


@router.post("/{snapshot_id}/share")
async def share_report(snapshot_id: str, req: ShareRequest, current_user: dict = Depends(get_current_user)):
    d = await REPORT_SNAPSHOTS.find_one({"snapshot_id": snapshot_id})
    if not d:
        raise HTTPException(status_code=404, detail="Report not found")
    if not _is_admin(current_user) and d.get("generated_by") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not the owner")
    token = secrets.token_urlsafe(24)
    now = datetime.now(timezone.utc)
    share_doc = {
        "share_token": token,
        "snapshot_id": snapshot_id,
        "assessment_id": d.get("assessment_id"),
        "client_name": d.get("client_name"),
        "created_by": current_user["id"],
        "created_at": now,
        "expires_at": now + timedelta(days=req.expires_in_days),
        "access_count": 0,
        "last_accessed_at": None,
        "revoked": False,
    }
    await REPORT_SHARES.insert_one(share_doc)
    return _strip(share_doc)


@router.delete("/{snapshot_id}/share")
async def revoke_share(snapshot_id: str, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        d = await REPORT_SNAPSHOTS.find_one({"snapshot_id": snapshot_id})
        if not d or d.get("generated_by") != current_user["id"]:
            raise HTTPException(status_code=403, detail="Admin or owner only")
    r = await REPORT_SHARES.update_many(
        {"snapshot_id": snapshot_id, "revoked": False},
        {"$set": {"revoked": True, "revoked_at": datetime.now(timezone.utc),
                  "revoked_by": current_user["id"]}},
    )
    return {"ok": True, "revoked_count": r.modified_count}


def _expired(share: dict) -> bool:
    exp = share.get("expires_at")
    if not exp:
        return False
    # Mongo returns naive datetimes — make tz-aware for safe comparison
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    return exp < datetime.now(timezone.utc)


@router.get("/public/{share_token}")
async def public_report_meta(share_token: str):
    share = await REPORT_SHARES.find_one({"share_token": share_token}, {"_id": 0})
    if not share:
        raise HTTPException(status_code=404, detail="Invalid share link")
    if share.get("revoked"):
        raise HTTPException(status_code=410, detail="Share link has been revoked")
    if _expired(share):
        raise HTTPException(status_code=410, detail="Share link expired")
    await REPORT_SHARES.update_one(
        {"share_token": share_token},
        {"$inc": {"access_count": 1}, "$set": {"last_accessed_at": datetime.now(timezone.utc)}},
    )
    d = await REPORT_SNAPSHOTS.find_one({"snapshot_id": share["snapshot_id"]}, {"_id": 0})
    if not d:
        raise HTTPException(status_code=404, detail="Report not found")
    return {
        "snapshot_id": d.get("snapshot_id"),
        "client_name": d.get("client_name"),
        "generated_at": d.get("generated_at"),
        "persona": d.get("persona"),
        "integrity_hash": d.get("data_integrity_hash"),
        "countries_count": len((d.get("data") or {}).get("countries") or []),
        "best_country": (d.get("data") or {}).get("best_country"),
        "pdf_url": f"/api/assessment-reports/public/{share_token}/pdf",
        "company": "Ladhani Education & Migration Services Pvt. Ltd.",
        "tagline": "We Value Emotions",
    }


@router.get("/public/{share_token}/pdf")
async def public_pdf(share_token: str):
    share = await REPORT_SHARES.find_one({"share_token": share_token})
    if not share:
        raise HTTPException(status_code=404, detail="Invalid share link")
    if share.get("revoked"):
        raise HTTPException(status_code=410, detail="Share link has been revoked")
    if _expired(share):
        raise HTTPException(status_code=410, detail="Share link expired")
    d = await REPORT_SNAPSHOTS.find_one({"snapshot_id": share["snapshot_id"]})
    if not d:
        raise HTTPException(status_code=404, detail="Report not found")
    snap_data = d.get("data") or {}
    snap_data["snapshot_id"] = d.get("snapshot_id")
    pdf_bytes = render_pdf(snap_data)
    filename = f"LEAMSS_Report_{(d.get('client_name') or 'client').replace(' ', '_')}.pdf"
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


class EmailRequest(BaseModel):
    to_email: str
    subject: Optional[str] = "Your LEAMSS Assessment Report"
    body: Optional[str] = None


@router.post("/{snapshot_id}/email")
async def email_report(snapshot_id: str, req: EmailRequest, current_user: dict = Depends(get_current_user)):
    d = await REPORT_SNAPSHOTS.find_one({"snapshot_id": snapshot_id})
    if not d:
        raise HTTPException(status_code=404, detail="Report not found")
    if not _is_admin(current_user) and d.get("generated_by") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not the owner")
    log = {
        "snapshot_id": snapshot_id,
        "to_email": req.to_email,
        "subject": req.subject,
        "body": req.body,
        "sent_by": current_user["id"],
        "sent_at": datetime.now(timezone.utc),
        "status": "mocked",
    }
    await REPORT_EMAILS.insert_one(log)
    return {"ok": True, "status": "mocked", "to_email": req.to_email,
            "note": "Email is MOCKED. Provide RESEND_API_KEY to enable live dispatch."}
