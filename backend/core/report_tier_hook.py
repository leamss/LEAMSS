"""Phase 7.3.5 — Tier Auto-Advance Hook + Client Notification.

Sir's request: When a Pre-Assessment stage advances (PA fee paid, Main Fee paid, Case Created),
the linked Assessment Report snapshots should AUTOMATICALLY upgrade their `render_tier` so
the client sees the right content without manual admin intervention.

Phase 7.3.5+ enhancement: ALSO push a client notification (in-app + WhatsApp template
+ email queue) so the client feels the upgrade instantly — "🎉 Full report unlocked".

Stage → Tier mapping:
  proposal_paid / awaiting_final_approval   → full     (Main Fee paid → unlock 15-page detailed report)
  case_created                              → proposal (case active → final proposal-tier PDF)

Idempotent + safe:
  - Skips snapshots already at target tier or higher
  - Logs each upgrade with payment_ref
  - Never downgrades a tier (e.g., proposal stays proposal even if PA goes back to draft)
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from core.database import db

logger = logging.getLogger(__name__)

REPORT_SNAPSHOTS = db["report_snapshots"]
REPORT_SHARES = db["report_shares"]
PRE_ASSESSMENTS = db["pre_assessments"]
NOTIFICATIONS = db["notifications"]
USERS = db["users"]

# Ordered tiers (higher index = higher tier)
TIER_RANK = {"teaser": 0, "full": 1, "proposal": 2}

# PA stage → target render tier
STAGE_TO_TARGET_TIER = {
    "proposal_paid": "full",
    "awaiting_final_approval": "full",
    "case_created": "proposal",
}

# Per-tier notification copy (Hinglish-aware, respectful)
TIER_NOTIFY_COPY = {
    "full": {
        "title": "🎉 Full Assessment Report Unlocked!",
        "message": (
            "Aapka payment receive ho gaya hai. Ab aapko 15-page detailed Assessment Report mil gayi hai — "
            "Occupation Deep-Dive, Cost Breakdown, Country Guide, sab kuch include."
        ),
        "wa_template": (
            "Hi {client_name},\n\n"
            "Thank you for trusting LEAMSS. Your *Full Assessment Report* is now unlocked.\n\n"
            "📄 View here: {link}\n\n"
            "We Value Emotions ❤️\n— Team LEAMSS"
        ),
    },
    "proposal": {
        "title": "🛡️ Case Active — Proposal Engagement Confirmed",
        "message": (
            "Aapka case officially activate ho gaya hai. Aapko ek dedicated Case Manager assign kiya jaayega "
            "aur poora engagement proposal aapke report mein dikhega."
        ),
        "wa_template": (
            "Hi {client_name},\n\n"
            "🎊 Your case is officially ACTIVE with LEAMSS. Your engagement proposal & final tier "
            "are now visible in the Assessment Report.\n\n"
            "📄 {link}\n\n"
            "— Team LEAMSS"
        ),
    },
}


async def _create_client_notification(
    client_user_id: Optional[str],
    client_name: str,
    new_tier: str,
    assessment_id: str,
    snapshot_id: str,
    pa_id: str,
) -> dict:
    """Drop an in-app notification + queue a WhatsApp template for downstream sending.

    Returns the notification doc summary.
    """
    copy = TIER_NOTIFY_COPY.get(new_tier)
    if not copy:
        return {"created": False, "reason": "no_copy_for_tier"}

    # Find existing share link for this snapshot, or hint client to login
    share = await REPORT_SHARES.find_one(
        {"snapshot_id": snapshot_id, "revoked": {"$ne": True}},
        {"_id": 0, "share_token": 1},
        sort=[("created_at", -1)],
    )
    link = (
        f"/reports/view/{share['share_token']}"
        if share else f"/client?assessment={assessment_id}"
    )

    notification = {
        "id": str(uuid.uuid4()),
        "user_id": client_user_id,        # may be None — admin can still send WA externally
        "title": copy["title"],
        "message": copy["message"],
        "type": "report_tier_upgraded",
        "link": link,
        "read": False,
        "created_at": datetime.now(timezone.utc),
        "meta": {
            "assessment_id": assessment_id,
            "snapshot_id": snapshot_id,
            "pa_id": pa_id,
            "tier": new_tier,
            "wa_template": copy["wa_template"].format(
                client_name=client_name or "there",
                link=link,
            ),
        },
    }
    if client_user_id:
        await NOTIFICATIONS.insert_one(notification)
        logger.info("Tier-upgrade notification created for user %s (tier=%s)", client_user_id, new_tier)
    else:
        # Queue without user — admin can review and forward
        notification["pending_external_dispatch"] = True
        await NOTIFICATIONS.insert_one(notification)
        logger.info("Tier-upgrade notification queued (no client user_id) for PA %s", pa_id)
    return {"created": True, "notification_id": notification["id"], "link": link}


async def auto_upgrade_report_tiers_for_pa(pa_id: str, new_stage: str, payment_ref: Optional[str] = None) -> dict:
    """Upgrade all snapshots attached to PA's assessment to the right tier per stage.

    Args:
        pa_id: Pre-Assessment ID.
        new_stage: The stage just transitioned to.
        payment_ref: Optional payment reference for audit trail.

    Returns:
        {upgraded: int, skipped: int, target_tier: str|None, assessment_id: str|None, notifications: list}
    """
    target_tier = STAGE_TO_TARGET_TIER.get(new_stage)
    if not target_tier:
        return {"upgraded": 0, "skipped": 0, "target_tier": None, "reason": "stage_not_mapped"}

    pa = await PRE_ASSESSMENTS.find_one(
        {"id": pa_id},
        {"_id": 0, "assessment_id": 1, "linked_assessment_id": 1, "id": 1,
         "client_id": 1, "client_user_id": 1, "client_name": 1},
    )
    if not pa:
        return {"upgraded": 0, "skipped": 0, "target_tier": target_tier, "reason": "pa_not_found"}

    assessment_id = pa.get("assessment_id") or pa.get("linked_assessment_id")
    if not assessment_id:
        return {
            "upgraded": 0, "skipped": 0, "target_tier": target_tier,
            "reason": "pa_has_no_linked_assessment",
        }

    snapshots_cursor = REPORT_SNAPSHOTS.find(
        {"assessment_id": assessment_id},
        {"_id": 0, "snapshot_id": 1, "render_tier": 1},
    )
    snapshots = await snapshots_cursor.to_list(length=100)
    upgraded = 0
    skipped = 0
    notification_results = []
    target_rank = TIER_RANK[target_tier]
    now = datetime.now(timezone.utc)
    client_user_id = pa.get("client_user_id") or pa.get("client_id")
    client_name = pa.get("client_name") or ""

    for snap in snapshots:
        current_tier = snap.get("render_tier") or "teaser"
        current_rank = TIER_RANK.get(current_tier, 0)
        if current_rank >= target_rank:
            skipped += 1
            continue
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
        # Notify client about the upgrade
        notif = await _create_client_notification(
            client_user_id=client_user_id,
            client_name=client_name,
            new_tier=target_tier,
            assessment_id=assessment_id,
            snapshot_id=snap["snapshot_id"],
            pa_id=pa_id,
        )
        notification_results.append(notif)

    return {
        "upgraded": upgraded,
        "skipped": skipped,
        "target_tier": target_tier,
        "assessment_id": assessment_id,
        "total_snapshots": len(snapshots),
        "notifications": notification_results,
    }
