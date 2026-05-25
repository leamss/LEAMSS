"""Phase 7.3.5 — Tier Auto-Advance Hook.

Sir's request: When a Pre-Assessment stage advances (PA fee paid, Main Fee paid, Case Created),
the linked Assessment Report snapshots should AUTOMATICALLY upgrade their `render_tier` so
the client sees the right content without manual admin intervention.

Stage → Tier mapping:
  payment_received / under_review / documents_submitted / approved → teaser (unchanged)
  proposal_sent                                                    → teaser (still pre-payment)
  proposal_paid / awaiting_final_approval                           → full     (Main Fee paid → unlock 15-page detailed report)
  case_created                                                      → proposal (case active → final proposal-tier PDF)

Idempotent + safe:
  - Skips snapshots already at target tier or higher
  - Logs each upgrade with payment_ref
  - Never downgrades a tier (e.g., proposal stays proposal even if PA goes back to draft)
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from core.database import db

logger = logging.getLogger(__name__)

REPORT_SNAPSHOTS = db["report_snapshots"]
PRE_ASSESSMENTS = db["pre_assessments"]

# Ordered tiers (higher index = higher tier)
TIER_RANK = {"teaser": 0, "full": 1, "proposal": 2}

# PA stage → target render tier
STAGE_TO_TARGET_TIER = {
    "proposal_paid": "full",
    "awaiting_final_approval": "full",
    "case_created": "proposal",
}


async def auto_upgrade_report_tiers_for_pa(pa_id: str, new_stage: str, payment_ref: Optional[str] = None) -> dict:
    """Upgrade all snapshots attached to PA's assessment to the right tier per stage.

    Args:
        pa_id: Pre-Assessment ID.
        new_stage: The stage just transitioned to.
        payment_ref: Optional payment reference for audit trail.

    Returns:
        {upgraded: int, skipped: int, target_tier: str|None, assessment_id: str|None}
    """
    target_tier = STAGE_TO_TARGET_TIER.get(new_stage)
    if not target_tier:
        return {"upgraded": 0, "skipped": 0, "target_tier": None, "reason": "stage_not_mapped"}

    # Find linked assessment
    pa = await PRE_ASSESSMENTS.find_one(
        {"id": pa_id}, {"_id": 0, "assessment_id": 1, "linked_assessment_id": 1, "id": 1},
    )
    if not pa:
        return {"upgraded": 0, "skipped": 0, "target_tier": target_tier, "reason": "pa_not_found"}

    assessment_id = pa.get("assessment_id") or pa.get("linked_assessment_id")
    if not assessment_id:
        return {
            "upgraded": 0, "skipped": 0, "target_tier": target_tier,
            "reason": "pa_has_no_linked_assessment",
        }

    # Find all snapshots for this assessment
    snapshots_cursor = REPORT_SNAPSHOTS.find(
        {"assessment_id": assessment_id},
        {"_id": 0, "snapshot_id": 1, "render_tier": 1},
    )
    snapshots = await snapshots_cursor.to_list(length=100)
    upgraded = 0
    skipped = 0
    target_rank = TIER_RANK[target_tier]
    now = datetime.now(timezone.utc)

    for snap in snapshots:
        current_tier = snap.get("render_tier") or "teaser"
        current_rank = TIER_RANK.get(current_tier, 0)
        if current_rank >= target_rank:
            skipped += 1
            continue
        # Upgrade
        await REPORT_SNAPSHOTS.update_one(
            {"snapshot_id": snap["snapshot_id"]},
            {"$set": {
                "render_tier": target_tier,
                "tier_upgraded_at": now,
                "tier_upgraded_by": "auto:pa_stage_hook",
                "tier_payment_ref": payment_ref,
                "tier_upgraded_from": current_tier,
                "tier_upgrade_trigger_stage": new_stage,
            }},
        )
        upgraded += 1
        logger.info(
            "Auto-upgraded snapshot %s: %s → %s (PA %s reached stage %s)",
            snap["snapshot_id"], current_tier, target_tier, pa_id, new_stage,
        )

    return {
        "upgraded": upgraded,
        "skipped": skipped,
        "target_tier": target_tier,
        "assessment_id": assessment_id,
        "total_snapshots": len(snapshots),
    }
