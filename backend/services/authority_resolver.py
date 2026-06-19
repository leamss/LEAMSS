"""Phase 19.7 — Country-aware assessing-authority resolver.

Single read-side helper used by every downstream consumer (Atlas SSG,
Smart Sales Helper, Pre-Assessment Report, admin views).

Contract — back-compat shape (32+ existing readers depend on this):
    Returns a dict with at minimum:
        {short_name: str, name: str, url: str}
    Plus optional new fields layered ON TOP:
        {processing: {...}, fees: {...}, documents_required: [...],
         _id: str, _status: str, _tbd: bool, _aliases_used: list,
         _override_msa_fee_aud: int|None, _override_processing_days_min/max}

Countries:
    AU → look up `assessing_authority_id` FK → merge defaults + occupation-level overrides
    NZ / CA → pass-through existing inline-fee dict unchanged (Phase 19.10 will refactor)
    Else → return back-compat empty dict {short_name:'', name:'', url:''}
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

AUTHORITY_COLLECTION = "assessing_authorities"

# In-process cache (refreshed on every resolve — cheap Mongo find_one)
# Could be hooked into Redis if hot-path becomes a bottleneck.


def _empty_back_compat() -> Dict[str, Any]:
    return {"short_name": "", "name": "", "url": "", "_tbd": True}


def _normalise_legacy_au_dict(aa: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy AU shape `{short_name, name, url}` — return as-is + _legacy flag."""
    out = {
        "short_name": aa.get("short_name") or "",
        "name": aa.get("name") or aa.get("full_name") or "",
        "url": aa.get("url") or aa.get("website") or "",
        "_legacy_pre_phase_197": True,
    }
    if not out["short_name"] and not out["name"]:
        out["_tbd"] = True
    return out


def _merge_authority_into_occupation_shape(
    auth_doc: Dict[str, Any], occ: Dict[str, Any],
) -> Dict[str, Any]:
    """Merge an `assessing_authorities` doc + occupation-level overrides into
    the back-compat dict shape expected by 32+ existing readers.

    Back-compat keys preserved: short_name, name, url.
    New keys added under simple names: processing, fees, documents_required,
    methodology_summary, validity_period_months, _id, _status, _aliases.
    """
    # Back-compat top-level
    short = auth_doc.get("code") or ""
    full = auth_doc.get("full_name") or ""
    site = auth_doc.get("website") or ""

    # Compute effective processing (override > default)
    eff_processing = dict(auth_doc.get("processing") or {})
    override_proc_min = occ.get("custom_processing_days_min")
    override_proc_max = occ.get("custom_processing_days_max")
    if override_proc_min is not None:
        eff_processing["standard_days_min"] = override_proc_min
        eff_processing["_override_min"] = True
    if override_proc_max is not None:
        eff_processing["standard_days_max"] = override_proc_max
        eff_processing["_override_max"] = True

    # Compute effective fees (override > default)
    eff_fees = dict(auth_doc.get("fees") or {})
    override_msa = occ.get("custom_msa_fee_aud")
    if override_msa is not None:
        eff_fees["msa_fee_aud"] = override_msa
        eff_fees["_override_msa"] = True

    return {
        # Back-compat trio
        "short_name": short,
        "name": full,
        "url": site,
        # New layered fields
        "_id": auth_doc.get("id") or str(auth_doc.get("_id") or ""),
        "_status": auth_doc.get("status") or "draft",
        "_seed_source": auth_doc.get("_seed_source"),
        "code": short,
        "full_name": full,
        "website": site,
        "processing": eff_processing,
        "fees": eff_fees,
        "documents_required_common": auth_doc.get("documents_required_common") or [],
        "methodology_summary": auth_doc.get("methodology_summary"),
        "validity_period_months": auth_doc.get("validity_period_months"),
        "appeal_process": auth_doc.get("appeal_process"),
        "occupation_override_notes": occ.get("assessing_authority_override_notes"),
        "_resolver_version": "phase_19.7",
    }


async def resolve_authority(
    db: AsyncIOMotorDatabase, occ: Dict[str, Any],
) -> Dict[str, Any]:
    """Resolve the assessing_authority view for a single occupation_master doc.

    Args:
        db: Motor database instance.
        occ: A single occupation_master document.
    Returns:
        Back-compat dict (always has short_name/name/url keys) + new layered
        fields when authority is mapped.
    """
    cc = (occ.get("country_code") or "").upper()
    aa_raw = occ.get("assessing_authority")

    if cc != "AU":
        # NZ / CA / other — pass through existing dict shape unchanged.
        if isinstance(aa_raw, dict) and aa_raw:
            return {
                "short_name": aa_raw.get("name") or aa_raw.get("short_name") or "",
                "name": aa_raw.get("full_name") or aa_raw.get("name") or "",
                "url": aa_raw.get("website") or aa_raw.get("url") or aa_raw.get("body_url") or "",
                # Pass through inline NZ/CA fee data unchanged
                **{k: v for k, v in aa_raw.items() if k not in {"short_name", "name", "url"}},
                "_country_legacy_pass_through": True,
            }
        return _empty_back_compat()

    # AU path
    authority_id = occ.get("assessing_authority_id")
    if authority_id:
        auth = await db[AUTHORITY_COLLECTION].find_one({"id": authority_id})
        if auth:
            return _merge_authority_into_occupation_shape(auth, occ)
        logger.warning("Authority FK %s not found in collection for occ %s",
                       authority_id, occ.get("occupation_id"))

    # Fallback: legacy dict still present from pre-migration
    if isinstance(aa_raw, dict) and aa_raw and (aa_raw.get("short_name") or aa_raw.get("name")):
        return _normalise_legacy_au_dict(aa_raw)

    # Truly empty AU → Authority TBD (Phase 19.8 enrichment target)
    return _empty_back_compat()


def resolve_authority_sync(
    db_sync, occ: Dict[str, Any],
) -> Dict[str, Any]:
    """Sync variant for non-async contexts (SSG renderer, pytest helpers).

    Args:
        db_sync: pymongo Database (sync).
    """
    cc = (occ.get("country_code") or "").upper()
    aa_raw = occ.get("assessing_authority")

    if cc != "AU":
        if isinstance(aa_raw, dict) and aa_raw:
            return {
                "short_name": aa_raw.get("name") or aa_raw.get("short_name") or "",
                "name": aa_raw.get("full_name") or aa_raw.get("name") or "",
                "url": aa_raw.get("website") or aa_raw.get("url") or aa_raw.get("body_url") or "",
                **{k: v for k, v in aa_raw.items() if k not in {"short_name", "name", "url"}},
                "_country_legacy_pass_through": True,
            }
        return _empty_back_compat()

    authority_id = occ.get("assessing_authority_id")
    if authority_id:
        auth = db_sync[AUTHORITY_COLLECTION].find_one({"id": authority_id})
        if auth:
            return _merge_authority_into_occupation_shape(auth, occ)

    if isinstance(aa_raw, dict) and aa_raw and (aa_raw.get("short_name") or aa_raw.get("name")):
        return _normalise_legacy_au_dict(aa_raw)
    return _empty_back_compat()
