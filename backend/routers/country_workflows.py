"""Sweep B.1 — Country Visa Workflows (Data Quality Hub).

Authoritative collection of verified immigration workflows per country/subclass.
When admin marks a workflow as "verified", `/api/ai-workflow/generate` returns
the seeded data instantly (no AI call needed) — guaranteeing accuracy + perf.

Endpoints (all `/api/country-workflows` prefix):
  GET    /                          List with filters
  GET    /{workflow_id}             Detail
  POST   /                          Create (manual or from AI draft)
  PATCH  /{workflow_id}             Edit (bumps version, audits)
  POST   /{workflow_id}/verify      Mark verified
  POST   /{workflow_id}/archive     Soft delete
  GET    /{workflow_id}/versions    Version history
  POST   /ai-draft                  Kick off AI draft job (returns job_id)
  GET    /ai-draft/status/{job_id}  Poll AI draft job
"""
import asyncio
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.database import db
from routers.auth import get_current_user
from core.services import log_activity

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/country-workflows", tags=["Sweep B - Country Workflows"])

workflows_col = db["country_visa_workflows"]
workflow_versions_col = db["country_visa_workflows_versions"]
ai_draft_jobs_col = db["country_workflow_ai_jobs"]


# ── RBAC helper ────────────────────────────────────────────────────────────────
def _can_manage(user: dict) -> bool:
    role = user.get("role")
    if role in ("admin", "admin_owner"):
        return True
    perms = user.get("permissions", []) or []
    if "*" in perms:
        return True
    return "country_workflows.manage" in perms


def _require_manage(user: dict):
    if not _can_manage(user):
        raise HTTPException(status_code=403, detail="Not authorized — needs country_workflows.manage")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _serialize(doc: Optional[dict]) -> dict:
    if not doc:
        return {}
    doc.pop("_id", None)
    return doc


# ── Pydantic models ────────────────────────────────────────────────────────────
class FeeBreakdownItem(BaseModel):
    component: str
    amount: float
    currency: str


class EligibilityCriterion(BaseModel):
    label: str
    value: str
    notes: Optional[str] = ""


class StepItem(BaseModel):
    step_number: int
    title: str
    description: str = ""
    estimated_days: int = 0
    documents_needed: List[str] = []
    tips: List[str] = []


class DocumentItem(BaseModel):
    doc_id: Optional[str] = None
    name: str
    mandatory: bool = True
    notes: Optional[str] = ""
    sample_url: Optional[str] = ""


class FaqItem(BaseModel):
    q: str
    a: str


class WorkflowCreate(BaseModel):
    country_code: str = Field(..., min_length=2, max_length=2)
    country_name: str
    subclass_id: str
    subclass_name: str
    service_type: str  # pr/work/student/visitor/partner/business
    category: Optional[str] = "immigration"
    description: str = ""
    eligibility_summary: str = ""
    eligibility_criteria: List[EligibilityCriterion] = []
    fees_local_currency_code: str = ""
    fees_local_currency_amount: float = 0
    fees_inr_approx: float = 0
    fees_breakdown: List[FeeBreakdownItem] = []
    processing_time_days_min: int = 0
    processing_time_days_max: int = 0
    step_by_step: List[StepItem] = []
    document_checklist: List[DocumentItem] = []
    common_rejection_reasons: List[str] = []
    success_tips: List[str] = []
    faqs: List[FaqItem] = []
    official_url: str = ""
    vfs_url: str = ""
    source_urls: List[str] = []


class WorkflowUpdate(BaseModel):
    country_name: Optional[str] = None
    subclass_name: Optional[str] = None
    service_type: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    eligibility_summary: Optional[str] = None
    eligibility_criteria: Optional[List[EligibilityCriterion]] = None
    fees_local_currency_code: Optional[str] = None
    fees_local_currency_amount: Optional[float] = None
    fees_inr_approx: Optional[float] = None
    fees_breakdown: Optional[List[FeeBreakdownItem]] = None
    processing_time_days_min: Optional[int] = None
    processing_time_days_max: Optional[int] = None
    step_by_step: Optional[List[StepItem]] = None
    document_checklist: Optional[List[DocumentItem]] = None
    common_rejection_reasons: Optional[List[str]] = None
    success_tips: Optional[List[str]] = None
    faqs: Optional[List[FaqItem]] = None
    official_url: Optional[str] = None
    vfs_url: Optional[str] = None
    source_urls: Optional[List[str]] = None


class VerifyRequest(BaseModel):
    notes: Optional[str] = ""


class AiDraftRequest(BaseModel):
    country_code: str
    country_name: str
    subclass_id: str
    subclass_name: str = ""
    service_type: str
    custom_instructions: Optional[str] = ""


# ── List + Detail ──────────────────────────────────────────────────────────────
@router.get("")
async def list_workflows(
    country_code: Optional[str] = None,
    status: Optional[str] = None,
    service_type: Optional[str] = None,
    limit: int = 200,
    current_user: dict = Depends(get_current_user),
):
    _require_manage(current_user)
    q: Dict[str, Any] = {}
    if country_code:
        q["country_code"] = country_code.upper()
    if status:
        q["status"] = status
    if service_type:
        q["service_type"] = service_type
    cursor = workflows_col.find(q, {"_id": 0}).sort([("country_code", 1), ("subclass_id", 1)]).limit(min(limit, 500))
    items = await cursor.to_list(length=limit)
    return {"items": items, "count": len(items)}


@router.get("/stats")
async def workflow_stats(current_user: dict = Depends(get_current_user)):
    _require_manage(current_user)
    pipe = [
        {"$group": {"_id": {"country_code": "$country_code", "status": "$status"}, "count": {"$sum": 1}}},
    ]
    rows = await workflows_col.aggregate(pipe).to_list(length=1000)
    by_country: Dict[str, Dict[str, int]] = {}
    for r in rows:
        cc = (r["_id"].get("country_code") or "??").upper()
        st = r["_id"].get("status") or "draft"
        by_country.setdefault(cc, {"draft": 0, "ai_drafted": 0, "verified": 0, "archived": 0, "total": 0})
        by_country[cc][st] = r["count"]
        by_country[cc]["total"] += r["count"]
    totals = {"draft": 0, "ai_drafted": 0, "verified": 0, "archived": 0, "total": 0}
    for v in by_country.values():
        for k in totals.keys():
            totals[k] += v.get(k, 0)
    return {"by_country": by_country, "totals": totals}


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str, current_user: dict = Depends(get_current_user)):
    _require_manage(current_user)
    doc = await workflows_col.find_one({"workflow_id": workflow_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return doc


@router.get("/{workflow_id}/versions")
async def list_versions(workflow_id: str, current_user: dict = Depends(get_current_user)):
    _require_manage(current_user)
    cursor = workflow_versions_col.find({"workflow_id": workflow_id}, {"_id": 0}).sort("version", -1).limit(50)
    items = await cursor.to_list(length=50)
    return {"items": items, "count": len(items)}


# ── Create / Update / Verify / Archive ─────────────────────────────────────────
@router.post("")
async def create_workflow(body: WorkflowCreate, current_user: dict = Depends(get_current_user)):
    _require_manage(current_user)
    workflow_id = str(uuid.uuid4())
    now = _now_iso()
    doc = body.model_dump()
    doc.update({
        "workflow_id": workflow_id,
        "country_code": doc["country_code"].upper(),
        "version": 1,
        "status": "draft",
        "verified_by": None,
        "verified_by_name": None,
        "verified_at": None,
        "verified_notes": "",
        "source_verified_at": None,
        "created_at": now,
        "created_by": current_user["id"],
        "created_by_name": current_user.get("name", ""),
        "updated_at": now,
        "updated_by": current_user["id"],
        "updated_by_name": current_user.get("name", ""),
    })
    await workflows_col.insert_one(doc.copy())
    await log_activity(current_user["id"], current_user.get("name", ""), "country_workflow_created",
                       "country_workflow", workflow_id,
                       f"{doc['country_code']} {doc['subclass_id']} {doc['service_type']}")
    return {"ok": True, "workflow_id": workflow_id, "workflow": _serialize(doc)}


@router.patch("/{workflow_id}")
async def update_workflow(workflow_id: str, body: WorkflowUpdate, current_user: dict = Depends(get_current_user)):
    _require_manage(current_user)
    existing = await workflows_col.find_one({"workflow_id": workflow_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Workflow not found")

    updates = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    if not updates:
        return {"ok": True, "workflow_id": workflow_id, "no_changes": True}

    # Snapshot current version before changes
    existing_for_snapshot = {**existing}
    existing_for_snapshot["snapshot_taken_at"] = _now_iso()
    await workflow_versions_col.insert_one(existing_for_snapshot)

    new_version = (existing.get("version") or 1) + 1
    updates.update({
        "version": new_version,
        "updated_at": _now_iso(),
        "updated_by": current_user["id"],
        "updated_by_name": current_user.get("name", ""),
        # Editing a verified workflow demotes it back to ai_drafted (admin must re-verify)
        "status": "ai_drafted" if existing.get("status") == "verified" else existing.get("status", "draft"),
    })
    await workflows_col.update_one({"workflow_id": workflow_id}, {"$set": updates})
    await log_activity(current_user["id"], current_user.get("name", ""), "country_workflow_updated",
                       "country_workflow", workflow_id,
                       f"v{new_version} — {len(updates)} fields changed")
    return {"ok": True, "workflow_id": workflow_id, "version": new_version}


@router.post("/{workflow_id}/verify")
async def verify_workflow(workflow_id: str, body: VerifyRequest, current_user: dict = Depends(get_current_user)):
    _require_manage(current_user)
    existing = await workflows_col.find_one({"workflow_id": workflow_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Workflow not found")
    now = _now_iso()
    await workflows_col.update_one(
        {"workflow_id": workflow_id},
        {"$set": {
            "status": "verified",
            "verified_by": current_user["id"],
            "verified_by_name": current_user.get("name", ""),
            "verified_at": now,
            "verified_notes": body.notes or "",
            "source_verified_at": now,
            "updated_at": now,
        }},
    )
    await log_activity(current_user["id"], current_user.get("name", ""), "country_workflow_verified",
                       "country_workflow", workflow_id,
                       f"{existing.get('country_code')} {existing.get('subclass_id')} · {body.notes or 'no notes'}")
    return {"ok": True, "workflow_id": workflow_id, "status": "verified", "verified_at": now}


@router.post("/{workflow_id}/archive")
async def archive_workflow(workflow_id: str, current_user: dict = Depends(get_current_user)):
    _require_manage(current_user)
    existing = await workflows_col.find_one({"workflow_id": workflow_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Workflow not found")
    now = _now_iso()
    await workflows_col.update_one(
        {"workflow_id": workflow_id},
        {"$set": {"status": "archived", "updated_at": now, "updated_by": current_user["id"]}},
    )
    await log_activity(current_user["id"], current_user.get("name", ""), "country_workflow_archived",
                       "country_workflow", workflow_id,
                       f"{existing.get('country_code')} {existing.get('subclass_id')}")
    return {"ok": True, "workflow_id": workflow_id, "status": "archived"}


# ── AI Draft (reuses Sweep A.2 background job pattern) ─────────────────────────
AI_DRAFT_TIMEOUT = 240


async def _execute_ai_draft(job_id: str, req: AiDraftRequest, user_id: str, user_name: str):
    from services import ai_workflow_service as ai_svc

    async def _update(patch: dict):
        patch["updated_at"] = _now_iso()
        await ai_draft_jobs_col.update_one({"job_id": job_id}, {"$set": patch})

    started_at = datetime.now(timezone.utc)
    await _update({"status": "running", "started_at": started_at.isoformat(), "progress": 15, "current_step": "analyzing"})

    try:
        system_msg = (
            "You are an expert immigration consultant. Output STRICT JSON only — no markdown, no preamble. "
            "Your task: generate a comprehensive, verified-quality immigration workflow for the requested country+visa subclass. "
            "Reference ONLY official .gov / regulatory sources. Be specific with fees (in local currency for Feb 2026) and processing times."
        )

        prompt = f"""Generate a complete, verified-quality immigration workflow for:
Country: {req.country_name} ({req.country_code})
Visa subclass: {req.subclass_id} {req.subclass_name}
Service type: {req.service_type}
{f"Additional context: {req.custom_instructions}" if req.custom_instructions else ""}

Return a JSON object with this EXACT structure:
{{
  "description": "2-3 paragraph rich overview of this visa pathway",
  "eligibility_summary": "Concise eligibility summary in 1 paragraph",
  "eligibility_criteria": [
    {{"label": "Age", "value": "18-45", "notes": "Points reduce after 40"}},
    {{"label": "English", "value": "IELTS 6.0+ overall", "notes": ""}},
    {{"label": "Points", "value": "Minimum 65 for invitation", "notes": ""}}
  ],
  "fees_local_currency_code": "AUD",
  "fees_local_currency_amount": 4640,
  "fees_inr_approx": 256000,
  "fees_breakdown": [
    {{"component": "Visa Application Charge - Primary", "amount": 4640, "currency": "AUD"}},
    {{"component": "Biometric collection (VFS)", "amount": 2200, "currency": "INR"}}
  ],
  "processing_time_days_min": 90,
  "processing_time_days_max": 365,
  "step_by_step": [
    {{"step_number": 1, "title": "Skills Assessment", "description": "Get your occupation assessed by relevant authority", "estimated_days": 30,
      "documents_needed": ["Passport", "Resume", "Degree certificate", "Transcripts", "Employment letters"],
      "tips": ["Apply early as queues fluctuate", "Use exact occupation name from ANZSCO list"]}}
  ],
  "document_checklist": [
    {{"name": "Passport (current + old)", "mandatory": true, "notes": "Must be valid for 6+ months"}},
    {{"name": "IELTS / PTE score report", "mandatory": true, "notes": "Within 3 years"}},
    {{"name": "Skills assessment outcome letter", "mandatory": true, "notes": ""}},
    {{"name": "Form 80 - Personal Particulars", "mandatory": true, "notes": ""}}
  ],
  "common_rejection_reasons": [
    "Insufficient English proficiency",
    "Skills assessment occupation mismatch",
    "Health/character requirements not met"
  ],
  "success_tips": [
    "Submit complete biometrics within 14 days of invitation",
    "Keep all original documents ready for verification"
  ],
  "faqs": [
    {{"q": "Can my spouse join me on this visa?", "a": "Yes, on dependent visa stream..."}}
  ],
  "official_url": "https://immi.homeaffairs.gov.au/...",
  "vfs_url": "https://visa.vfsglobal.com/...",
  "source_urls": ["https://...", "https://..."]
}}

Be comprehensive. At least 5 steps. At least 6 documents in checklist. At least 3 eligibility criteria, 3 rejection reasons, 3 tips, 2 FAQs."""

        await _update({"progress": 35, "current_step": "generating"})

        # Sweep B.1 hotfix — single-pass with extended budget:
        # call_ai_with_fallback now caps Sonnet at 120s + Haiku at 50s = ~170s worst case.
        # Country drafts have larger schemas than ai-workflow generate, so Sonnet needs more headroom.
        # Our outer asyncio.wait_for adds 10s safety margin.
        parsed: Dict[str, Any] = {}
        model_used: str = "unknown"
        last_exc: Optional[Exception] = None
        try:
            response, model_used = await asyncio.wait_for(
                ai_svc.call_ai_with_fallback(
                    prompt, system_msg, session_prefix="country_draft",
                    primary_timeout=120, fallback_timeout=50,
                ),
                timeout=180,
            )
            try:
                parsed = ai_svc.parse_json_response(response) or {}
            except Exception as parse_e:  # noqa: BLE001
                # Sweep B.1 hotfix Fix 4 — Save partial output even if JSON didn't parse cleanly
                logger.warning("AI draft JSON parse failed for job %s: %s — saving partial", job_id, parse_e)
                parsed = {"description": (response or "")[:1500], "_partial_raw": True}
                last_exc = parse_e
        except asyncio.TimeoutError:
            last_exc = TimeoutError("Outer 180s job budget exceeded (Sonnet+Haiku combined)")
            logger.exception("AI draft job %s outer timeout", job_id)
        except Exception as e:  # noqa: BLE001
            last_exc = e
            logger.exception("AI draft job %s AI-call failed", job_id)

        # If both attempts failed AND no parsed content → mark failed with meaningful message
        if not parsed:
            err_msg = f"{type(last_exc).__name__}: {str(last_exc)[:400]}" if last_exc else "AI generation failed (no result)"
            await _update({
                "status": "failed", "progress": 100, "current_step": "failed",
                "error": err_msg, "completed_at": _now_iso(),
                "model_used": model_used if model_used != "unknown" else None,
            })
            await log_activity(user_id, user_name, "country_workflow_ai_draft_failed",
                               "country_workflow", job_id,
                               f"{req.country_code} {req.subclass_id} · {err_msg}")
            return

        await _update({"progress": 85, "current_step": "formatting"})

        # Compose full workflow doc
        workflow_id = str(uuid.uuid4())
        now = _now_iso()
        doc = {
            "workflow_id": workflow_id,
            "country_code": req.country_code.upper(),
            "country_name": req.country_name,
            "subclass_id": req.subclass_id,
            "subclass_name": req.subclass_name or req.subclass_id,
            "service_type": req.service_type,
            "category": "immigration",
            "description": parsed.get("description", ""),
            "eligibility_summary": parsed.get("eligibility_summary", ""),
            "eligibility_criteria": parsed.get("eligibility_criteria", []) or [],
            "fees_local_currency_code": parsed.get("fees_local_currency_code", ""),
            "fees_local_currency_amount": parsed.get("fees_local_currency_amount", 0) or 0,
            "fees_inr_approx": parsed.get("fees_inr_approx", 0) or 0,
            "fees_breakdown": parsed.get("fees_breakdown", []) or [],
            "processing_time_days_min": parsed.get("processing_time_days_min", 0) or 0,
            "processing_time_days_max": parsed.get("processing_time_days_max", 0) or 0,
            "step_by_step": parsed.get("step_by_step", []) or [],
            "document_checklist": parsed.get("document_checklist", []) or [],
            "common_rejection_reasons": parsed.get("common_rejection_reasons", []) or [],
            "success_tips": parsed.get("success_tips", []) or [],
            "faqs": parsed.get("faqs", []) or [],
            "official_url": parsed.get("official_url", ""),
            "vfs_url": parsed.get("vfs_url", ""),
            "source_urls": parsed.get("source_urls", []) or [],
            "version": 1,
            "status": "ai_drafted",
            "verified_by": None,
            "verified_by_name": None,
            "verified_at": None,
            "verified_notes": "",
            "source_verified_at": None,
            "ai_draft_model": model_used,
            "ai_draft_job_id": job_id,
            "created_at": now,
            "created_by": user_id,
            "created_by_name": user_name,
            "updated_at": now,
            "updated_by": user_id,
            "updated_by_name": user_name,
        }
        await workflows_col.insert_one(doc.copy())

        completed_at = datetime.now(timezone.utc)
        await _update({
            "status": "complete",
            "progress": 100,
            "current_step": "done",
            "workflow_id": workflow_id,
            "completed_at": completed_at.isoformat(),
            "duration_ms": int((completed_at - started_at).total_seconds() * 1000),
            "model_used": model_used,
        })
        await log_activity(user_id, user_name, "country_workflow_ai_drafted",
                           "country_workflow", workflow_id,
                           f"{req.country_code} {req.subclass_id} via {model_used}")
    except Exception as e:  # noqa: BLE001
        logger.exception(f"AI draft job {job_id} crashed")
        # Sweep B.1 hotfix — consistent error formatting with type prefix (matches inner branch)
        err_msg = f"{type(e).__name__}: {str(e)[:400]}"
        await _update({
            "status": "failed",
            "progress": 100,
            "current_step": "failed",
            "error": err_msg,
            "completed_at": _now_iso(),
        })


@router.post("/ai-draft")
async def ai_draft(req: AiDraftRequest, current_user: dict = Depends(get_current_user)):
    _require_manage(current_user)
    if not req.country_code or not req.subclass_id or not req.service_type:
        raise HTTPException(status_code=400, detail="country_code, subclass_id, service_type required")
    job_id = str(uuid.uuid4())
    now = _now_iso()
    await ai_draft_jobs_col.insert_one({
        "job_id": job_id,
        "user_id": current_user["id"],
        "user_name": current_user.get("name", ""),
        "country_code": req.country_code.upper(),
        "country_name": req.country_name,
        "subclass_id": req.subclass_id,
        "subclass_name": req.subclass_name,
        "service_type": req.service_type,
        "status": "queued",
        "progress": 0,
        "current_step": "queued",
        "workflow_id": None,
        "model_used": None,
        "error": None,
        "created_at": now,
        "updated_at": now,
        "started_at": None,
        "completed_at": None,
        "duration_ms": None,
    })

    async def _runner():
        try:
            await asyncio.wait_for(
                _execute_ai_draft(job_id, req, current_user["id"], current_user.get("name", "")),
                timeout=AI_DRAFT_TIMEOUT,
            )
        except asyncio.TimeoutError:
            await ai_draft_jobs_col.update_one(
                {"job_id": job_id},
                {"$set": {"status": "failed", "error": f"Job exceeded {AI_DRAFT_TIMEOUT}s overall timeout", "completed_at": _now_iso()}},
            )

    asyncio.create_task(_runner())
    return {"job_id": job_id, "status": "queued", "poll_url": f"/api/country-workflows/ai-draft/status/{job_id}"}


@router.get("/ai-draft/status/{job_id}")
async def ai_draft_status(job_id: str, current_user: dict = Depends(get_current_user)):
    _require_manage(current_user)
    job = await ai_draft_jobs_col.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


# ── Public helper: lookup verified workflow (used by /api/ai-workflow/generate) ─
#
# B.2 HOTFIX (Feb 27, 2026) — Liberal input acceptance to prevent fastpath misses
# Frontend may send country as full name ("Australia"), ISO code ("AU"), or alias.
# service_type may arrive title-cased ("Pr"), as a phrase ("Permanent Residency"),
# or as a known synonym ("family", "spouse"). Conservative canonical mapping below
# normalises both inputs before MongoDB lookup. NO aggressive keyword fallback —
# unrecognised tokens cleanly fall through to the AI generation path.

COUNTRY_ALIAS_MAP: Dict[str, str] = {
    # Australia
    "australia": "AU", "au": "AU", "aus": "AU",
    # Canada
    "canada": "CA", "ca": "CA", "can": "CA",
    # New Zealand
    "new zealand": "NZ", "nz": "NZ", "newzealand": "NZ", "aotearoa": "NZ",
    # United Kingdom
    "united kingdom": "UK", "uk": "UK", "gb": "UK", "gbr": "UK",
    "great britain": "UK", "britain": "UK", "england": "UK",
    # India (Sweep B.4.2 — Feb 27, 2026)
    "india": "IN", "in": "IN", "ind": "IN", "bharat": "IN",
    # United States (Sweep B.4.7 — Feb 27, 2026)
    "united states": "US", "us": "US", "usa": "US", "u.s.": "US", "u.s.a.": "US",
    "united states of america": "US", "america": "US",
    # Germany (Sweep B.4.8 — Feb 27, 2026)
    "germany": "DE", "de": "DE", "deutschland": "DE", "german": "DE",
    "federal republic of germany": "DE", "brd": "DE",
    # Schengen Area (Sweep B.4.9 — Feb 27, 2026 — MEGA DISPATCH FINAL)
    "schengen": "EU", "schengen area": "EU", "eu": "EU", "europe": "EU",
    "european union": "EU", "schengen zone": "EU",
}

SERVICE_TYPE_CANONICAL_MAP: Dict[str, str] = {
    # Canonical (already lowercased — pass-through)
    "pr": "pr", "work": "work", "student": "student", "visitor": "visitor", "partner": "partner",
    # Common variants/phrases (lowercased keys)
    "permanent residency": "pr", "permanent residence": "pr",
    "permanent resident": "pr", "residency": "pr", "immigration": "pr",
    "skilled migration": "pr", "skilled migrant": "pr",
    "work permit": "work", "work visa": "work", "employment": "work",
    "study": "student", "study permit": "student", "study visa": "student", "education": "student",
    "tourist": "visitor", "visit": "visitor", "tourism": "visitor", "business visit": "visitor",
    "family": "partner", "spouse": "partner", "spousal": "partner",
    "marriage": "partner", "spouse/family": "partner", "family/partner": "partner",
    # Sweep B.4.2 — India-specific canonical tokens (Feb 27, 2026)
    "oci": "oci", "overseas citizen of india": "oci", "overseas citizen": "oci",
    "pio": "pio", "person of indian origin": "pio",
    "business": "business", "business visa": "business",
    "medical": "medical", "medical visa": "medical", "medical attendant": "medical",
    "conference": "conference", "conference visa": "conference",
    "journalist": "journalist", "journalist visa": "journalist", "media": "journalist",
    "research": "research", "research visa": "research",
    "entry_x": "entry_x", "entry x": "entry_x", "entry-x": "entry_x", "x visa": "entry_x", "x-visa": "entry_x",
    "transit": "transit", "transit visa": "transit",
}


def _normalise_country(country: str) -> Dict[str, Optional[str]]:
    """Resolve country input to (country_code, country_name_pattern).

    Returns dict with keys 'code' (if alias matched) and 'name_regex' (always).
    """
    raw = (country or "").strip()
    lowered = raw.lower()
    code = COUNTRY_ALIAS_MAP.get(lowered)
    return {"code": code, "name_regex": re.escape(raw)}


def _normalise_service_type(service_type: str) -> Optional[str]:
    """Resolve service_type input to canonical token (pr|work|student|visitor|partner).

    Conservative — only exact matches against canonical map (case-insensitive).
    Returns None if no canonical match (caller should fall through to AI path).
    """
    raw = (service_type or "").strip().lower()
    return SERVICE_TYPE_CANONICAL_MAP.get(raw)


async def find_verified_workflow(country_name: str, service_type: str, subclass_id: Optional[str] = None) -> Optional[dict]:
    """Returns first verified workflow matching country + service_type.

    Liberal input acceptance:
      - country: full name ("Australia"), ISO code ("AU"), or common alias ("UK"/"GB")
      - service_type: canonical token ("pr") OR title-cased ("Pr") OR synonym ("family"→"partner")

    If subclass_id given, prefers exact match; otherwise returns any verified for
    country+service. Returns None if no verified entry exists OR if service_type
    isn't a canonical immigration category (AI path will handle).
    """
    country_resolved = _normalise_country(country_name)
    canonical_svc = _normalise_service_type(service_type)

    if not canonical_svc:
        # Unrecognised service_type — let AI path handle it
        return None

    base_q: Dict[str, Any] = {
        "status": "verified",
        "service_type": canonical_svc,
    }
    if country_resolved["code"]:
        # Strong match via ISO code (canonical)
        base_q["country_code"] = country_resolved["code"]
    else:
        # Fallback: case-insensitive country_name regex
        base_q["country_name"] = {"$regex": f"^{country_resolved['name_regex']}$", "$options": "i"}

    if subclass_id:
        q = {**base_q, "subclass_id": subclass_id}
        doc = await workflows_col.find_one(q, {"_id": 0})
        if doc:
            return doc
        # Fallback: drop subclass filter to return any verified for country+service
    return await workflows_col.find_one(base_q, {"_id": 0})
