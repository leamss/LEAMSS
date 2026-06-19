"""Phase 19.9 — Diff Audit Service.

Given a body's proposed_changes, simulate the impact on linked occupations BEFORE
committing — so admin can see exactly what changes downstream:
    - How many occupations affected
    - Atlas pages affected (list)
    - Sales-flow pages affected (count)
    - Sample SEO meta description before/after redline diffs

Performance: caches per-body resolver result; samples top 5 by code; <2s response.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


async def compute_diff_audit(
    db: AsyncIOMotorDatabase,
    code: str,
    proposed_changes: Dict[str, Any],
) -> Dict[str, Any]:
    """Simulate impact of patching an authority with `proposed_changes`.

    Args:
        code: Authority `code` (e.g. "ACS")
        proposed_changes: Dict of fields to patch — only checks fees/processing/full_name keys.
    """
    coll = db["assessing_authorities"]
    occ_coll = db["occupation_master"]
    auth = await coll.find_one({"code": code})
    if not auth:
        return {"error": f"Authority {code} not found",
                "affected_occupation_count": 0,
                "atlas_pages_affected": [],
                "sales_flow_pages_affected": 0,
                "meta_description_diffs": [],
                "estimated_seo_impact": "none"}

    auth_id = auth["id"]
    n_linked = await occ_coll.count_documents(
        {"country_code": "AU", "assessing_authority_id": auth_id},
    )
    if n_linked == 0:
        return {
            "authority_code": code,
            "affected_occupation_count": 0,
            "atlas_pages_affected": [],
            "sales_flow_pages_affected": 0,
            "meta_description_diffs": [],
            "estimated_seo_impact": "none",
            "note": "No occupations linked to this authority — change has zero downstream impact.",
        }

    # Sample up to 5 linked occupations for diff
    samples = await (occ_coll
                    .find({"country_code": "AU", "assessing_authority_id": auth_id},
                          {"_id": 0, "code": 1, "title": 1, "description": 1,
                           "occupation_id": 1, "country_code": 1, "anzsco_profile": 1,
                           "assessing_authority": 1, "abs_data": 1, "jsa_data": 1})
                    .sort("code", 1).limit(5).to_list(5))

    # Build "before" and "after" meta descriptions by invoking the Phase 19.5 builder
    # with current vs simulated authority data.
    from routers.public_atlas import _build_meta_description, _country_meta
    from services.authority_resolver import _merge_authority_into_occupation_shape

    # Simulated patched authority doc
    sim_auth = dict(auth)
    for k, v in (proposed_changes or {}).items():
        if k in {"full_name", "website", "aliases"}:
            sim_auth[k] = v
        elif k in {"fees", "processing"}:
            # Merge nested dicts
            current = dict(sim_auth.get(k) or {})
            for sub_k, sub_v in (v or {}).items():
                current[sub_k] = sub_v
            sim_auth[k] = current

    # Phase 19.9.1 — also detect identity-field changes (name/aliases) and surface
    # samples even if Phase 19.5 meta-description builder doesn't differ.
    identity_changed = (
        "full_name" in (proposed_changes or {})
        or "aliases" in (proposed_changes or {})
    )

    diffs: List[Dict[str, Any]] = []
    atlas_pages: List[str] = []
    char_diff_total = 0

    cm = _country_meta("AU")
    country_name = cm["name"]

    for occ in samples:
        code_str = occ.get("code", "")
        title = occ.get("title", "")

        # Current state
        occ_before = dict(occ)
        occ_before["assessing_authority"] = _merge_authority_into_occupation_shape(auth, occ)
        meta_before = _build_meta_description("AU", occ_before, code_str, title, country_name)

        # Simulated patched state
        occ_after = dict(occ)
        occ_after["assessing_authority"] = _merge_authority_into_occupation_shape(sim_auth, occ)
        meta_after = _build_meta_description("AU", occ_after, code_str, title, country_name)

        if meta_before != meta_after:
            char_diff = len(meta_after) - len(meta_before)
            char_diff_total += abs(char_diff)
            diffs.append({
                "code": code_str, "title": title,
                "before": meta_before,
                "after": meta_after,
                "char_diff": char_diff,
                "atlas_url": f"/atlas/au/{code_str}",
                "diff_type": "seo_meta_description",
            })
            atlas_pages.append(f"/atlas/au/{code_str}")
        elif identity_changed:
            # Identity-field change but Phase 19.5 builder didn't surface it
            # (uses short_name = body code, which is locked). Still surface
            # the change because it WILL show on Atlas detail pages directly.
            old_id = (occ_before["assessing_authority"].get("name") or "")
            new_id = (occ_after["assessing_authority"].get("name") or "")
            old_aliases = (auth.get("aliases") or [])
            new_aliases = (proposed_changes.get("aliases") or auth.get("aliases") or [])
            char_diff = len(new_id) - len(old_id)
            char_diff_total += abs(char_diff)
            diffs.append({
                "code": code_str, "title": title,
                "before": f"Authority displayed as: {old_id}",
                "after": f"Authority displayed as: {new_id}",
                "char_diff": char_diff,
                "atlas_url": f"/atlas/au/{code_str}",
                "diff_type": "identity_field",
                "field_changes": {
                    "full_name": {"old": auth.get("full_name"), "new": sim_auth.get("full_name")} if "full_name" in (proposed_changes or {}) else None,
                    "aliases": {"old": old_aliases, "new": new_aliases} if "aliases" in (proposed_changes or {}) else None,
                },
            })
            atlas_pages.append(f"/atlas/au/{code_str}")

    # Determine SEO impact
    if char_diff_total == 0:
        impact = "none"
    elif char_diff_total < 30:
        impact = "low"
    elif char_diff_total < 100:
        impact = "medium"
    else:
        impact = "high"

    # Also fetch full list of affected atlas page paths (for "view all" link)
    all_linked = await (occ_coll
                       .find({"country_code": "AU", "assessing_authority_id": auth_id},
                             {"_id": 0, "code": 1}).sort("code", 1).limit(50).to_list(50))
    all_atlas_paths = [f"/atlas/au/{o['code']}" for o in all_linked]

    return {
        "authority_code": code,
        "authority_name": auth.get("full_name"),
        "proposed_changes": proposed_changes,
        "affected_occupation_count": n_linked,
        "atlas_pages_affected": all_atlas_paths,
        "atlas_pages_affected_count": n_linked,  # all atlas pages cleanly affected
        "sales_flow_pages_affected": n_linked,   # sales compare reads same resolver
        "meta_description_diffs": diffs,
        "char_diff_total": char_diff_total,
        "estimated_seo_impact": impact,
    }
