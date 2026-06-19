"""Phase 20.3+ — Fee Policy Diff-Preview Service.

Computes the cascade impact of a proposed Pre-Assessment fee policy change
BEFORE the admin commits the update. Prevents accidental retroactive billing
disruptions by surfacing:
  - How many active PAs match this policy's (country + visa)
  - Of those, how many are unpaid vs paid vs in-progress
  - Old fee vs new fee + delta + delta_pct
  - A sample of 5 affected PAs (client name, stage, fee, paid_at)

Also provides the retroactive-apply executor that updates affected PAs
under a revocable Phase 19.6 import_batch.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from services import import_batch_service as ibs
from services.audit_service import log_action

logger = logging.getLogger(__name__)

POLICY_COLLECTION = "pre_assessment_fee_policies"
PA_COLLECTION = "pre_assessments"
DEFAULT_LOOKBACK_DAYS = 90

# Stages considered "unpaid" (fee can be safely retroactively updated)
UNPAID_STAGES = {"new", "payment_pending"}
# Stages where money has changed hands — retroactive update is dangerous
PAID_STAGES = {
    "payment_received", "documents_submitted",
    "admin_approved", "admin_rejected", "proposal_sent", "case_started",
    "completed", "refunded",
}


async def compute_diff(
    db: AsyncIOMotorDatabase,
    policy_id: str,
    proposed_changes: Dict[str, Any],
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> Dict[str, Any]:
    """Compute downstream impact of editing a policy.

    Args:
        policy_id: existing policy id
        proposed_changes: dict with at least `fee_inr` if it changed
        lookback_days: only count PAs created within this window

    Returns:
        {
            policy_id, policy_country, policy_visa,
            old_fee, new_fee, fee_delta_inr, fee_delta_pct,
            lookback_days, lookback_from,
            affected_pas_count,
            unpaid_count, paid_count, in_progress_count,
            sample_pas: [{id, client_name, stage, fee, source, created_at}],
            requires_diff_modal: bool,
            warnings: [str],
        }
    """
    policy = await db[POLICY_COLLECTION].find_one({"id": policy_id})
    if not policy:
        raise ValueError(f"Policy {policy_id} not found")

    country = policy["country_code"]
    visa = policy["visa_category"]
    old_fee = int(policy.get("fee_inr") or 0)
    new_fee = int(proposed_changes.get("fee_inr") or old_fee)
    fee_changed = new_fee != old_fee
    delta_inr = new_fee - old_fee
    delta_pct = round((delta_inr / old_fee) * 100, 1) if old_fee else 0.0

    lookback_from = datetime.now(timezone.utc) - timedelta(days=lookback_days)

    # Match PAs tied to this policy_id directly OR matching country+visa+source=country_visa_policy
    country_norm = country.upper()
    visa_norm = visa.upper()
    match_query: Dict[str, Any] = {
        "$or": [
            {"pre_assessment_fee_policy_id": policy_id},
            {
                "$and": [
                    {"country": {"$regex": f"^{country_norm[:2]}", "$options": "i"}},
                    {"service_type": {"$regex": f"^{visa_norm}$", "$options": "i"}},
                    {"pre_assessment_fee_source": "country_visa_policy"},
                ],
            },
        ],
        "created_at": {"$gte": lookback_from},
    }

    # GLOBAL fallback policies match the broader "global_fallback" source
    if country_norm == "GLOBAL" and visa_norm == "ANY":
        match_query = {
            "$or": [
                {"pre_assessment_fee_policy_id": policy_id},
                {"pre_assessment_fee_source": "global_fallback"},
            ],
            "created_at": {"$gte": lookback_from},
        }

    affected = []
    async for pa in db[PA_COLLECTION].find(
        match_query,
        {"_id": 0, "id": 1, "client_name": 1, "stage": 1, "country": 1,
         "service_type": 1, "pre_assessment_fee": 1, "pre_assessment_fee_source": 1,
         "created_at": 1, "paid_at": 1},
    ).sort("created_at", -1):
        affected.append(pa)

    unpaid_count = sum(1 for p in affected if (p.get("stage") or "") in UNPAID_STAGES)
    paid_count = sum(1 for p in affected if (p.get("stage") or "") in PAID_STAGES)
    in_progress_count = len(affected) - unpaid_count - paid_count

    sample = []
    for pa in affected[:5]:
        ca = pa.get("created_at")
        if isinstance(ca, datetime):
            ca = ca.isoformat()
        sample.append({
            "id": pa.get("id"),
            "client_name": pa.get("client_name"),
            "stage": pa.get("stage"),
            "country": pa.get("country"),
            "service_type": pa.get("service_type"),
            "current_fee": pa.get("pre_assessment_fee"),
            "fee_source": pa.get("pre_assessment_fee_source"),
            "created_at": ca,
        })

    warnings: List[str] = []
    if paid_count > 0:
        warnings.append(
            f"{paid_count} PAs already collected payment — retroactive update will NOT touch them by default."
        )
    if fee_changed and abs(delta_pct) >= 20:
        warnings.append(
            f"Fee change is {delta_pct:+.0f}% — large delta. Double-check intent."
        )

    # Sir's directive #4: show diff modal ONLY when fee_inr value actually changes
    requires_diff_modal = bool(fee_changed)

    return {
        "policy_id": policy_id,
        "policy_country": country,
        "policy_visa": visa,
        "old_fee": old_fee,
        "new_fee": new_fee,
        "fee_changed": fee_changed,
        "fee_delta_inr": delta_inr,
        "fee_delta_pct": delta_pct,
        "lookback_days": lookback_days,
        "lookback_from": lookback_from.isoformat(),
        "affected_pas_count": len(affected),
        "unpaid_count": unpaid_count,
        "paid_count": paid_count,
        "in_progress_count": in_progress_count,
        "sample_pas": sample,
        "requires_diff_modal": requires_diff_modal,
        "warnings": warnings,
    }


async def apply_retroactive(
    db: AsyncIOMotorDatabase,
    policy_id: str,
    reason: str,
    affect_unpaid_only: bool,
    user_id: str,
    user_name: str,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> Dict[str, Any]:
    """Update affected PAs to use the policy's current fee_inr.

    Registers a Phase 19.6 revocable batch so admin can undo within 24h.

    Args:
        policy_id: target policy id (uses its current fee_inr as the new value)
        reason: human reason (min 10 chars enforced by router)
        affect_unpaid_only: if True, only `new` + `payment_pending` PAs are updated
        user_id, user_name: actor
        lookback_days: only touch PAs within this window

    Returns:
        {ok, batch_id, updated_count, skipped_count, sample_updated}
    """
    policy = await db[POLICY_COLLECTION].find_one({"id": policy_id})
    if not policy:
        raise ValueError(f"Policy {policy_id} not found")

    country = policy["country_code"]
    visa = policy["visa_category"]
    new_fee = int(policy["fee_inr"])
    lookback_from = datetime.now(timezone.utc) - timedelta(days=lookback_days)

    country_norm = country.upper()
    visa_norm = visa.upper()

    # Same match logic as compute_diff
    if country_norm == "GLOBAL" and visa_norm == "ANY":
        match_query: Dict[str, Any] = {
            "$or": [
                {"pre_assessment_fee_policy_id": policy_id},
                {"pre_assessment_fee_source": "global_fallback"},
            ],
            "created_at": {"$gte": lookback_from},
        }
    else:
        match_query = {
            "$or": [
                {"pre_assessment_fee_policy_id": policy_id},
                {
                    "$and": [
                        {"country": {"$regex": f"^{country_norm[:2]}", "$options": "i"}},
                        {"service_type": {"$regex": f"^{visa_norm}$", "$options": "i"}},
                        {"pre_assessment_fee_source": "country_visa_policy"},
                    ],
                },
            ],
            "created_at": {"$gte": lookback_from},
        }

    if affect_unpaid_only:
        match_query["stage"] = {"$in": list(UNPAID_STAGES)}

    # Open Phase 19.6 batch
    body_bytes = f"retroactive_{policy_id}_{new_fee}_{int(affect_unpaid_only)}".encode()
    batch = await ibs.open_batch(
        db,
        ingestion_path="phase_20.3_fee_policy.retroactive_apply",
        endpoint=f"POST /api/pre-assessment-fee-policies/{policy_id}/apply-retroactive",
        uploaded_by=user_id, uploaded_by_name=user_name,
        file_name=f"retroactive_{policy_id}",
        file_hash=ibs.file_sha256(body_bytes),
        file_size_bytes=len(body_bytes),
        target_collection=PA_COLLECTION,
    )

    updated_count = 0
    skipped_count = 0
    sample_updated: List[Dict[str, Any]] = []

    async for pa in db[PA_COLLECTION].find(match_query):
        current_fee = int(pa.get("pre_assessment_fee") or 0)
        if current_fee == new_fee:
            skipped_count += 1
            continue
        # Snapshot pre-state for revoke
        pre = {
            "pre_assessment_fee": current_fee,
            "pre_assessment_fee_source": pa.get("pre_assessment_fee_source"),
            "pre_assessment_fee_policy_id": pa.get("pre_assessment_fee_policy_id"),
        }
        await db[PA_COLLECTION].update_one(
            {"id": pa["id"]},
            {"$set": {
                "pre_assessment_fee": new_fee,
                "pre_assessment_fee_policy_id": policy_id,
                "pre_assessment_fee_source": "retroactive_policy_apply",
                "pre_assessment_fee_retroactive_at": datetime.now(timezone.utc),
                "pre_assessment_fee_retroactive_reason": reason,
                "pre_assessment_fee_retroactive_by": user_id,
            }},
        )
        ibs.record_update(batch, pa["id"], {"id": pa["id"]}, pre)
        updated_count += 1
        if len(sample_updated) < 5:
            sample_updated.append({
                "id": pa.get("id"), "client_name": pa.get("client_name"),
                "stage": pa.get("stage"), "old_fee": current_fee, "new_fee": new_fee,
            })

    await ibs.close_batch(db, batch, total_rows=updated_count + skipped_count, status="committed")

    await log_action(
        db,
        action="fee_policy.retroactive_apply",
        user_id=user_id, user_name=user_name, severity="warn",
        summary={
            "policy_id": policy_id,
            "country": country, "visa": visa, "new_fee": new_fee,
            "affect_unpaid_only": affect_unpaid_only,
            "lookback_days": lookback_days,
            "updated_count": updated_count, "skipped_count": skipped_count,
            "reason": reason,
            "batch_id": batch["batch_id"],
        },
    )

    return {
        "ok": True,
        "batch_id": batch["batch_id"],
        "policy_id": policy_id,
        "updated_count": updated_count,
        "skipped_count": skipped_count,
        "sample_updated": sample_updated,
        "new_fee_inr": new_fee,
        "affect_unpaid_only": affect_unpaid_only,
        "is_revocable": True,
        "revocation_window_hours": 24,
    }
