"""AU Classification Versions (ANZSCO 2013 vs OSCA 2022) & Subclass Rules.

Allows consultants and AI to evaluate Australian occupations against both:
  1) ANZSCO 2013: Traditional General Skilled Migration (GSM) points-tested framework (Subclasses 189, 190, 491, 494).
  2) OSCA 2022: Modernised ABS & JSA Core Skills framework for employer-sponsored and temporary visas (Subclasses 482, 186, 407, 485).

Admins can dynamically add or remove subclasses linked to either version.
Mutating operations write audit trail events via services/audit_service.py.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from core.auth import get_current_user
from core.database import db
from services.audit_service import log_legacy_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sales/au-classification-versions", tags=["AU Classification Versions"])

COLLECTION_NAME = "au_classification_versions"
DOC_KEY = "au_classification_versions"

ADMIN_ROLES = {"admin", "admin_owner"}
SALES_ROLES = {
    "admin", "admin_owner", "sales_executive", "sr_sales_executive",
    "sales_manager", "sales_head", "partner", "case_manager", "client",
}


def _is_admin(user: dict) -> bool:
    role = user.get("rbac_role") or user.get("role") or ""
    return role in ADMIN_ROLES or "*" in (user.get("permissions") or [])


def _can_read(user: dict) -> bool:
    role = user.get("rbac_role") or user.get("role") or ""
    return role in SALES_ROLES or "*" in (user.get("permissions") or [])


DEFAULT_AU_CLASSIFICATIONS: Dict[str, Any] = {
    "key": DOC_KEY,
    "versions": {
        "ANZSCO_2013": {
            "version_key": "ANZSCO_2013",
            "name": "ANZSCO 2013",
            "label": "ANZSCO 2013 (GSM Framework)",
            "framework": "Points-tested General Skilled Migration",
            "description": "General Skilled Migration framework governing points-tested independent, state nominated, and regional visas.",
            "subclasses": ["189", "190", "491", "494"],
            "notes": "Department of Home Affairs legislative instruments for GSM points-tested visas rely on ANZSCO 2013.",
            "is_active": True,
        },
        "OSCA_2022": {
            "version_key": "OSCA_2022",
            "name": "OSCA 2022",
            "label": "OSCA 2022 / CSOL (Skills in Demand)",
            "framework": "Core Skills & Employer-Sponsored",
            "description": "Modernised ABS & Jobs and Skills Australia (JSA) classification governing Skills in Demand and Employer Nomination.",
            "subclasses": ["482", "186", "407", "485"],
            "notes": "Employer-sponsored and temporary shortage streams align with modernized OSCA / ANZSCO 2022+ CSOL frameworks.",
            "is_active": True,
        },
    },
    "subclass_metadata": {
        "189": {"subclass": "189", "name": "Skilled Independent (Permanent)", "type": "Points-Tested"},
        "190": {"subclass": "190", "name": "Skilled Nominated (Permanent)", "type": "State-Nominated"},
        "491": {"subclass": "491", "name": "Skilled Work Regional (Provisional)", "type": "Regional / State"},
        "494": {"subclass": "494", "name": "Skilled Employer Sponsored Regional (Provisional)", "type": "Employer Regional"},
        "482": {"subclass": "482", "name": "Skills in Demand (Temporary Core Skills)", "type": "Employer Sponsored"},
        "186": {"subclass": "186", "name": "Employer Nomination Scheme (Direct Entry)", "type": "Employer Permanent"},
        "407": {"subclass": "407", "name": "Training Visa", "type": "Temporary Training"},
        "485": {"subclass": "485", "name": "Temporary Graduate", "type": "Graduate Work"},
    },
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "updated_by": "system",
}


async def get_active_classification_versions() -> Dict[str, Any]:
    """Retrieves current AU classification versions config from MongoDB, seeding defaults if needed."""
    doc = await db[COLLECTION_NAME].find_one({"key": DOC_KEY}, {"_id": 0})
    if not doc or "versions" not in doc:
        seed = dict(DEFAULT_AU_CLASSIFICATIONS)
        await db[COLLECTION_NAME].update_one(
            {"key": DOC_KEY},
            {"$set": seed},
            upsert=True,
        )
        return seed
    return doc


class SubclassActionRequest(BaseModel):
    version_key: str = Field(..., description="Classification version key: ANZSCO_2013 or OSCA_2022")
    subclass: str = Field(..., min_length=2, max_length=12, description="Subclass number e.g. 189, 482, 491")
    action: str = Field(..., pattern="^(add|remove)$", description="'add' or 'remove'")

    model_config = {"extra": "forbid"}


class UpdateVersionConfigRequest(BaseModel):
    versions: Dict[str, Any] = Field(..., description="Full updated versions dictionary")

    model_config = {"extra": "forbid"}


@router.get("", response_model=Dict[str, Any])
async def get_classification_versions(current_user: dict = Depends(get_current_user)):
    """Retrieve active AU classification versions and their configured subclasses."""
    if not _can_read(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorised to view classification versions")
    return await get_active_classification_versions()


@router.post("/subclasses")
async def modify_subclass(
    req: SubclassActionRequest,
    current_user: dict = Depends(get_current_user),
):
    """Admin endpoint to add or remove a visa subclass from ANZSCO 2013 or OSCA 2022."""
    if not _is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin permissions required to modify subclasses")

    norm_version = req.version_key.strip().upper()
    if norm_version not in ("ANZSCO_2013", "OSCA_2022"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="version_key must be ANZSCO_2013 or OSCA_2022")

    clean_subclass = req.subclass.strip()
    if not clean_subclass:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Subclass cannot be empty")

    cfg = await get_active_classification_versions()
    versions = cfg.get("versions") or {}
    ver_obj = versions.get(norm_version) or {}
    subclasses = list(ver_obj.get("subclasses") or [])

    if req.action == "add":
        if clean_subclass in subclasses:
            return {"status": "ok", "message": f"Subclass {clean_subclass} already present in {norm_version}", "subclasses": subclasses}
        subclasses.append(clean_subclass)
    elif req.action == "remove":
        if clean_subclass not in subclasses:
            return {"status": "ok", "message": f"Subclass {clean_subclass} was not in {norm_version}", "subclasses": subclasses}
        subclasses = [s for s in subclasses if s != clean_subclass]

    ver_obj["subclasses"] = subclasses
    versions[norm_version] = ver_obj
    now_iso = datetime.now(timezone.utc).isoformat()
    actor_id = str(current_user.get("id") or current_user.get("_id") or "admin")

    await db[COLLECTION_NAME].update_one(
        {"key": DOC_KEY},
        {
            "$set": {
                f"versions.{norm_version}.subclasses": subclasses,
                "updated_at": now_iso,
                "updated_by": actor_id,
            }
        },
        upsert=True,
    )

    await log_legacy_event(
        db=db,
        user_id=actor_id,
        action=f"au_classification_subclass_{req.action}",
        entity_type="au_classification_versions",
        entity_id=norm_version,
        details={
            "version_key": norm_version,
            "subclass": clean_subclass,
            "action": req.action,
            "resulting_subclasses": subclasses,
        },
    )

    return {
        "status": "ok",
        "message": f"Subclass {clean_subclass} {req.action}ed successfully in {norm_version}",
        "version_key": norm_version,
        "subclasses": subclasses,
    }


@router.put("")
async def update_classification_versions(
    req: UpdateVersionConfigRequest,
    current_user: dict = Depends(get_current_user),
):
    """Admin endpoint to update full classification configuration."""
    if not _is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin permissions required")

    actor_id = str(current_user.get("id") or current_user.get("_id") or "admin")
    now_iso = datetime.now(timezone.utc).isoformat()

    await db[COLLECTION_NAME].update_one(
        {"key": DOC_KEY},
        {
            "$set": {
                "versions": req.versions,
                "updated_at": now_iso,
                "updated_by": actor_id,
            }
        },
        upsert=True,
    )

    await log_legacy_event(
        db=db,
        user_id=actor_id,
        action="au_classification_versions_bulk_update",
        entity_type="au_classification_versions",
        entity_id="global",
        details={"versions_updated": list(req.versions.keys())},
    )

    return await get_active_classification_versions()


def evaluate_occupation_classification_versions(
    occ_doc: Dict[str, Any],
    classification_cfg: Dict[str, Any],
) -> Dict[str, Any]:
    """Helper to evaluate an Australian occupation against active ANZSCO 2013 and OSCA 2022 subclasses.

    Returns rich dual-framework eligibility summary with active subclasses.
    """
    visa_pathways = occ_doc.get("visa_pathways") or {}
    visa_eligibility = visa_pathways.get("visa_eligibility") or []

    # Map of subclass -> eligible boolean & details from occupation doc
    occ_eligible_subclasses: Dict[str, Dict[str, Any]] = {}
    for ve in visa_eligibility:
        if isinstance(ve, dict) and ve.get("visa_subclass"):
            sc = str(ve["visa_subclass"]).strip()
            if ve.get("eligible") is not False:
                occ_eligible_subclasses[sc] = ve

    # Also check legacy pathway arrays
    for sc in (visa_pathways.get("gsm_pathways") or []):
        sc_str = str(sc).strip()
        if sc_str not in occ_eligible_subclasses:
            occ_eligible_subclasses[sc_str] = {"visa_subclass": sc_str, "eligible": True}
    for sc in (visa_pathways.get("employer_pathways") or []):
        sc_str = str(sc).strip()
        if sc_str not in occ_eligible_subclasses:
            occ_eligible_subclasses[sc_str] = {"visa_subclass": sc_str, "eligible": True}

    versions = classification_cfg.get("versions") or {}
    meta = classification_cfg.get("subclass_metadata") or {}

    out: Dict[str, Any] = {}

    for v_key in ("ANZSCO_2013", "OSCA_2022"):
        v_def = versions.get(v_key) or {}
        conf_subclasses = v_def.get("subclasses") or []
        active_for_occ = []
        unavailable_for_occ = []

        for sc in conf_subclasses:
            sc_str = str(sc).strip()
            m = meta.get(sc_str) or {}
            sc_name = m.get("name") or f"Subclass {sc_str}"
            if sc_str in occ_eligible_subclasses:
                active_for_occ.append({
                    "subclass": sc_str,
                    "name": sc_name,
                    "eligible": True,
                    "list": occ_eligible_subclasses[sc_str].get("list"),
                })
            else:
                unavailable_for_occ.append({
                    "subclass": sc_str,
                    "name": sc_name,
                    "eligible": False,
                })

        is_eligible = len(active_for_occ) > 0
        v_name = v_def.get("name") or v_key
        subclass_names = [f"Subclass {a['subclass']}" for a in active_for_occ]
        
        summary_text = (
            f"Eligible for {', '.join(subclass_names)} under {v_name}."
            if is_eligible
            else f"No active subclasses available under {v_name} for this occupation."
        )

        out[v_key.lower()] = {
            "version_key": v_key,
            "version_name": v_name,
            "label": v_def.get("label") or v_name,
            "framework": v_def.get("framework") or "",
            "is_eligible": is_eligible,
            "active_subclasses": [a["subclass"] for a in active_for_occ],
            "subclasses_detail": active_for_occ,
            "unavailable_subclasses": [u["subclass"] for u in unavailable_for_occ],
            "summary": summary_text,
        }

    return out
