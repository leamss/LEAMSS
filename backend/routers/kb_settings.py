"""Phase 6.9.4 — Knowledge Base settings + status enforcement helpers.

  • GET  /api/kb/settings — current threshold + verification gate state
  • PUT  /api/kb/settings — admin updates threshold (months) and enforce_verified_only
  • POST /api/occupation-master/auto-flag-outdated — sweep verified records older
    than the configured threshold and flip them to 'outdated'.
  • POST /api/kb/polish-text — generic AI-polish endpoint (used by 3-panel editor)
"""
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.auth import get_current_user
from core.database import db
from core.kb_ai import polish_text

router = APIRouter(prefix="/kb", tags=["kb-settings"])

KB_SETTINGS = db["kb_settings"]
OCCUPATION_MASTER = db["occupation_master"]
SKILL_BODY_MASTER = db["skill_body_master"]
ADMIN_ROLES = {"admin", "admin_owner"}

DEFAULT_THRESHOLD_MONTHS = 6
DEFAULT_VERIFICATION_GATE_PERCENT = 90  # When ≥ this % verified, hide drafts from sales
SETTINGS_DOC_ID = "global"


def _is_admin(user: dict) -> bool:
    role = user.get("rbac_role") or user.get("role")
    return role in ADMIN_ROLES or "*" in (user.get("permissions") or [])


async def _get_settings() -> dict:
    doc = await KB_SETTINGS.find_one({"_id": SETTINGS_DOC_ID})
    if not doc:
        doc = {
            "_id": SETTINGS_DOC_ID,
            "outdated_threshold_months": DEFAULT_THRESHOLD_MONTHS,
            "verification_gate_percent": DEFAULT_VERIFICATION_GATE_PERCENT,
            "enforce_verified_only": False,  # transition policy default off
            "updated_at": datetime.now(timezone.utc),
            "updated_by": None,
        }
        await KB_SETTINGS.insert_one(doc)
    doc.pop("_id", None)
    return doc


class SettingsUpdate(BaseModel):
    outdated_threshold_months: Optional[int] = Field(None, ge=1, le=60)
    verification_gate_percent: Optional[int] = Field(None, ge=50, le=100)
    enforce_verified_only: Optional[bool] = None


@router.get("/settings")
async def get_settings(current_user: dict = Depends(get_current_user)):
    return await _get_settings()


@router.put("/settings")
async def update_settings(req: SettingsUpdate, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    update_doc = {k: v for k, v in req.model_dump(exclude_unset=True).items() if v is not None}
    update_doc["updated_at"] = datetime.now(timezone.utc)
    update_doc["updated_by"] = current_user["id"]
    await KB_SETTINGS.update_one({"_id": SETTINGS_DOC_ID}, {"$set": update_doc}, upsert=True)
    return await _get_settings()


# ─────────────────────────────────────────────────────────────────────────────
# Auto-flag outdated — admin trigger
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/auto-flag-outdated")
async def auto_flag_outdated(current_user: dict = Depends(get_current_user)):
    """Sweep verified records older than the configured threshold and mark outdated."""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    settings = await _get_settings()
    months = settings.get("outdated_threshold_months", DEFAULT_THRESHOLD_MONTHS)
    cutoff = datetime.now(timezone.utc) - timedelta(days=int(months * 30.5))
    # Verified records with last_reviewed_at older than cutoff → outdated
    result_occ = await OCCUPATION_MASTER.update_many(
        {
            "status": "verified",
            "$or": [
                {"last_reviewed_at": {"$lt": cutoff}},
                {"last_reviewed_at": None},
                {"last_reviewed_at": {"$exists": False}},
            ],
            "verification.verified_at": {"$lt": cutoff},
        },
        {"$set": {"status": "outdated", "updated_at": datetime.now(timezone.utc)}},
    )
    result_body = await SKILL_BODY_MASTER.update_many(
        {
            "status": "verified",
            "$or": [
                {"last_reviewed_at": {"$lt": cutoff}},
                {"last_reviewed_at": None},
                {"last_reviewed_at": {"$exists": False}},
            ],
            "verification.verified_at": {"$lt": cutoff},
        },
        {"$set": {"status": "outdated", "updated_at": datetime.now(timezone.utc)}},
    )
    return {
        "ok": True,
        "occupations_flagged_outdated": result_occ.modified_count,
        "bodies_flagged_outdated": result_body.modified_count,
        "threshold_months": months,
        "cutoff_date": cutoff.isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Polish with AI (generic — used by 3-panel editor on any text field)
# ─────────────────────────────────────────────────────────────────────────────
class PolishRequest(BaseModel):
    text: str
    field_label: Optional[str] = None
    context: Optional[str] = None


@router.post("/polish-text")
async def polish(req: PolishRequest, current_user: dict = Depends(get_current_user)):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="Empty text")
    polished = await polish_text(req.text, field_label=req.field_label, context=req.context)
    return {"ok": True, "original": req.text, "polished": polished, "field_label": req.field_label}
