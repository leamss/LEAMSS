"""Phase 7.1 — KB Unification: Excel Import + Verification Hub.

Endpoints under /api/kb-unified:
  POST   /import-anzsco-excel       — multipart upload of Feb 2026 ABS Excel
  POST   /import-anzsco-default     — admin one-click import using bundled file (/tmp/anzsco_feb2026.xlsx)
  GET    /verification-hub          — unified count of draft/verified items across 4 entity types
  GET    /anzsco/{four_digit_code}  — single 4-digit profile (joined view)
  GET    /occupation-full/{code}    — 6-digit occupation_master + 4-digit profile joined
"""
import logging
import os
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from core.anzsco_excel_importer import (
    ANZSCO_4DIGIT, import_anzsco_excel, get_4digit_parent_code,
)
from core.auth import get_current_user
from core.database import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/kb-unified", tags=["kb-unified"])

OCCUPATIONS = db["occupation_master"]
COUNTRY_TEMPLATES = db["country_templates"]
COUNTRY_GUIDES = db["country_guides"]
POLICIES = db["protection_policies"]

ADMIN_ROLES = {"admin", "admin_owner"}
DEFAULT_EXCEL_PATH = "/tmp/anzsco_feb2026.xlsx"


def _is_admin(user: dict) -> bool:
    role = user.get("rbac_role") or user.get("role")
    return role in ADMIN_ROLES or "*" in (user.get("permissions") or [])


@router.post("/import-anzsco-excel")
async def upload_and_import(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Admin uploads the Feb 2026 ABS ANZSCO Excel; we import to anzsco_4digit_master."""
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(400, "Only .xlsx files supported")

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        contents = await file.read()
        tmp.write(contents)
        tmp_path = tmp.name
    try:
        summary = await import_anzsco_excel(tmp_path, imported_by=current_user.get("id") or "admin")
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
    return summary


@router.post("/import-anzsco-default")
async def import_default(current_user: dict = Depends(get_current_user)):
    """Admin one-click — uses Sir's already-uploaded Feb 2026 Excel at DEFAULT_EXCEL_PATH."""
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")
    if not os.path.exists(DEFAULT_EXCEL_PATH):
        raise HTTPException(
            404,
            f"Default Excel file not found at {DEFAULT_EXCEL_PATH}. Use /import-anzsco-excel to upload.",
        )
    return await import_anzsco_excel(DEFAULT_EXCEL_PATH, imported_by=current_user.get("id") or "admin")


@router.get("/verification-hub")
async def verification_hub(current_user: dict = Depends(get_current_user)):
    """Unified counts of pending verifications across all 4 KB entity types."""
    if not _is_admin(current_user):
        raise HTTPException(403, "Admin only")

    async def count_by_status(coll, status_field="status"):
        out: Dict[str, int] = {}
        async for d in coll.aggregate([
            {"$group": {"_id": f"${status_field}", "count": {"$sum": 1}}},
        ]):
            out[d["_id"] or "none"] = d["count"]
        return out

    occ_counts = await count_by_status(OCCUPATIONS)
    template_counts = await count_by_status(COUNTRY_TEMPLATES)
    guide_counts = await count_by_status(COUNTRY_GUIDES)
    policy_counts = await count_by_status(POLICIES)
    anzsco_total = await ANZSCO_4DIGIT.count_documents({})

    # Pending lists (top 10 drafts per entity)
    pending_occupations = await OCCUPATIONS.find(
        {"status": {"$in": ["draft", None]}},
        {"_id": 0, "occupation_id": 1, "code": 1, "title": 1, "country_code": 1, "status": 1, "updated_at": 1},
    ).sort("updated_at", -1).to_list(10)
    pending_templates = await COUNTRY_TEMPLATES.find(
        {"status": {"$ne": "verified"}},
        {"_id": 0, "country_code": 1, "country_name": 1, "status": 1, "updated_at": 1},
    ).sort("updated_at", -1).to_list(10)
    pending_guides = await COUNTRY_GUIDES.find(
        {"status": {"$ne": "verified"}},
        {"_id": 0, "country_code": 1, "name": 1, "status": 1, "updated_at": 1},
    ).sort("updated_at", -1).to_list(10)
    pending_policies = await POLICIES.find(
        {"status": {"$ne": "verified"}},
        {"_id": 0, "policy_id": 1, "title": 1, "status": 1, "updated_at": 1},
    ).sort("updated_at", -1).to_list(10)

    return {
        "summary": {
            "occupation_master": {
                "counts": occ_counts,
                "verified_pct": _pct(occ_counts.get("verified", 0), sum(occ_counts.values()) or 1),
            },
            "country_templates": {
                "counts": template_counts,
                "verified_pct": _pct(template_counts.get("verified", 0), sum(template_counts.values()) or 1),
            },
            "country_guides": {
                "counts": guide_counts,
                "verified_pct": _pct(guide_counts.get("verified", 0), sum(guide_counts.values()) or 1),
            },
            "protection_policies": {
                "counts": policy_counts,
                "verified_pct": _pct(policy_counts.get("verified", 0), sum(policy_counts.values()) or 1),
            },
            "anzsco_4digit_master": {
                "total_codes": anzsco_total,
                "data_source": "ABS Feb 2026",
            },
        },
        "pending_lists": {
            "occupations": pending_occupations,
            "country_templates": pending_templates,
            "country_guides": pending_guides,
            "protection_policies": pending_policies,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _pct(num: int, denom: int) -> float:
    if not denom:
        return 0.0
    return round((num / denom) * 100, 1)


@router.get("/anzsco/{four_digit_code}")
async def get_anzsco_profile(four_digit_code: str):
    """Public-readable 4-digit ANZSCO profile. Used by report renderer + occupation viewer."""
    doc = await ANZSCO_4DIGIT.find_one({"code": four_digit_code}, {"_id": 0})
    if not doc:
        raise HTTPException(404, f"ANZSCO 4-digit code {four_digit_code} not found")
    return doc


@router.get("/occupation-full/{code}")
async def get_occupation_full(code: str, current_user: dict = Depends(get_current_user)):
    """Returns a 6-digit occupation_master document joined with:
      - its 4-digit ANZSCO parent profile
      - linked country_template
      - linked country_guide
    One call → everything report renderer needs.
    """
    if not _is_admin(current_user) and not current_user:
        raise HTTPException(401, "Auth required")

    occ = await OCCUPATIONS.find_one({"code": code}, {"_id": 0})
    if not occ:
        raise HTTPException(404, f"Occupation code {code} not found")

    parent_code = await get_4digit_parent_code(code)
    anzsco_profile = None
    if parent_code:
        anzsco_profile = await ANZSCO_4DIGIT.find_one({"code": parent_code}, {"_id": 0})

    country_code = occ.get("country_code")
    template = None
    guide = None
    if country_code:
        template = await COUNTRY_TEMPLATES.find_one({"country_code": country_code}, {"_id": 0})
        guide = await COUNTRY_GUIDES.find_one({"country_code": country_code}, {"_id": 0})

    return {
        "occupation": occ,
        "anzsco_4digit_parent": anzsco_profile,
        "country_template": template,
        "country_guide": guide,
    }
