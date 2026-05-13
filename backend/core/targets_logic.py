"""Phase 4B — Sales Targets Logic (Pure functions, no router).

Centralises:
  - Period boundary calculation (monthly + quarterly)
  - Achievement recalculation from closed PAs
  - Status auto-update (active / completed / exceeded / missed)
  - Milestone detection for notifications (50%, 75%, 100%, exceeded)

Used by:
  - routers/targets.py (CRUD + manual recalc)
  - routers/pre_assess_portal.py (auto-recalc on case_created)
"""
import uuid
from datetime import datetime, timezone, date, timedelta
from calendar import monthrange
from typing import Tuple, Optional, Dict, Any

from core.database import db, pre_assessments_col, notifications_col

sales_targets_col = db["sales_targets"]
target_templates_col = db["target_templates"]


def _aware(dt):
    """Coerce naive datetimes from MongoDB to UTC-aware. Pass-through for already-aware."""
    if dt is None:
        return None
    if isinstance(dt, datetime) and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# ────────────────────────────────────────────────────────────
# Period boundaries
# ────────────────────────────────────────────────────────────
def get_period_bounds(
    period_type: str,
    year: int,
    month: Optional[int] = None,
    quarter: Optional[int] = None,
) -> Tuple[datetime, datetime]:
    """Returns (start, end) datetimes for a period. End is exclusive (first day of next period)."""
    if period_type == "monthly":
        if not month or not (1 <= month <= 12):
            raise ValueError("Monthly target requires month 1-12")
        start = datetime(year, month, 1, tzinfo=timezone.utc)
        if month == 12:
            end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            end = datetime(year, month + 1, 1, tzinfo=timezone.utc)
        return start, end

    if period_type == "quarterly":
        if not quarter or not (1 <= quarter <= 4):
            raise ValueError("Quarterly target requires quarter 1-4")
        start_month = (quarter - 1) * 3 + 1
        start = datetime(year, start_month, 1, tzinfo=timezone.utc)
        end_month = start_month + 3
        if end_month > 12:
            end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            end = datetime(year, end_month, 1, tzinfo=timezone.utc)
        return start, end

    raise ValueError(f"Unknown period_type: {period_type}")


def current_period(period_type: str, ref: Optional[datetime] = None) -> Dict[str, int]:
    """Returns the current period dict (e.g., {year:2026, month:5} or {year:2026, quarter:2})."""
    now = ref or datetime.now(timezone.utc)
    if period_type == "monthly":
        return {"year": now.year, "month": now.month}
    if period_type == "quarterly":
        return {"year": now.year, "quarter": (now.month - 1) // 3 + 1}
    raise ValueError(f"Unknown period_type: {period_type}")


def days_remaining_in_period(period_end: datetime, ref: Optional[datetime] = None) -> int:
    """Calendar days left until period ends (exclusive end)."""
    now = ref or datetime.now(timezone.utc)
    period_end = _aware(period_end)
    if now >= period_end:
        return 0
    return max(0, (period_end - now).days)


# ────────────────────────────────────────────────────────────
# Achievement calculation
# ────────────────────────────────────────────────────────────
async def compute_achievement(target: Dict[str, Any]) -> Dict[str, Any]:
    """Re-queries closed deals in the target period for target.user_id.
    Sums revenue from BOTH:
      - pre_assessments where stage='case_created' (PA path — standard + express converge here)
      - sales records where status='approved'  (Direct Sale path — bypasses PA entirely)

    Returns achievement dict (does NOT persist — caller persists).
    """
    user_id = target["user_id"]
    period_start = _aware(target["period_start"])
    period_end = _aware(target["period_end"])

    revenue_total = 0.0
    pa_count = 0
    seen_sale_ids = set()

    # ─── (1) PA-driven revenue: stage=case_created ──────────────────
    pa_query = {
        "$or": [
            {"created_by_user_id": user_id},
            {"$and": [
                {"created_by_user_id": {"$exists": False}},
                {"partner_id": user_id},
            ]},
        ],
        "stage": "case_created",
        "final_approved_at": {"$gte": period_start, "$lt": period_end},
    }
    async for pa in pre_assessments_col.find(pa_query, {"_id": 0, "proposal_fee": 1, "final_amount": 1, "sale_id": 1}):
        amount = float(pa.get("proposal_fee") or pa.get("final_amount") or 0)
        revenue_total += amount
        pa_count += 1
        # Track linked sale_id so we don't double-count if same deal appears in sales_col
        if pa.get("sale_id"):
            seen_sale_ids.add(pa["sale_id"])

    # ─── (2) Direct Sale revenue: status=approved ───────────────────
    # Match by partner_id (Phase 4A: sales execs use their user_id as partner_id on sales too)
    sales_col = db["sales"]
    sale_query = {
        "partner_id": user_id,
        "status": "approved",
        "approved_at": {"$gte": period_start, "$lt": period_end},
    }
    async for s in sales_col.find(sale_query, {"_id": 0, "id": 1, "fee_amount": 1, "amount_received": 1}):
        if s.get("id") in seen_sale_ids:
            # Already counted via the PA path
            continue
        # Use amount_received if available (matches commission-calc convention), else fee_amount
        amount = float(s.get("amount_received") or s.get("fee_amount") or 0)
        revenue_total += amount
        pa_count += 1

    targets = target.get("targets", {})
    rev_target = float(targets.get("revenue", 0) or 0)
    pa_target = int(targets.get("pa_count", 0) or 0)

    rev_pct = round((revenue_total / rev_target * 100), 2) if rev_target > 0 else 0
    pa_pct = round((pa_count / pa_target * 100), 2) if pa_target > 0 else 0
    overall = max(rev_pct, pa_pct)

    return {
        "revenue": round(revenue_total, 2),
        "pa_count": pa_count,
        "revenue_percentage": rev_pct,
        "pa_count_percentage": pa_pct,
        "overall_percentage": round(overall, 2),
    }


def compute_status(target: Dict[str, Any], achievement: Dict[str, Any], now: Optional[datetime] = None) -> str:
    """Determines status based on achievement + period bounds.
    active   — current period, in progress
    completed — current/ended period at 100-149%
    exceeded — current/ended period at 150%+
    missed   — period ended at <100%
    """
    now = now or datetime.now(timezone.utc)
    overall = achievement.get("overall_percentage", 0)
    period_end = _aware(target["period_end"])
    ended = now >= period_end

    if overall >= 150:
        return "exceeded"
    if ended:
        return "completed" if overall >= 100 else "missed"
    return "completed" if overall >= 100 else "active"


def detect_milestones(prev_pct: float, new_pct: float) -> list:
    """Returns list of milestone keys crossed (e.g., ['50', '75', '100']).
    A milestone is 'crossed' when prev<threshold and new>=threshold.
    """
    crossed = []
    for threshold in [50, 75, 100, 150]:
        if prev_pct < threshold <= new_pct:
            crossed.append(str(threshold))
    return crossed


# ────────────────────────────────────────────────────────────
# Recalc + persist + notify (top-level orchestration)
# ────────────────────────────────────────────────────────────
async def recalc_target(target_id: str, notify: bool = True) -> Optional[Dict[str, Any]]:
    """Recalculates a single target's achievement, persists, optionally fires milestone notifications.
    Returns the updated target dict (without _id).
    """
    target = await sales_targets_col.find_one({"id": target_id}, {"_id": 0})
    if not target:
        return None

    prev_pct = (target.get("achievement") or {}).get("overall_percentage", 0)
    new_achievement = await compute_achievement(target)
    new_status = compute_status(target, new_achievement)
    new_pct = new_achievement["overall_percentage"]

    now = datetime.now(timezone.utc)
    await sales_targets_col.update_one(
        {"id": target_id},
        {"$set": {
            "achievement": new_achievement,
            "status": new_status,
            "last_recalc_at": now,
        }},
    )

    # Milestone notifications
    if notify:
        crossed = detect_milestones(prev_pct, new_pct)
        for milestone in crossed:
            await _fire_milestone_notification(target, milestone, new_achievement)

    target["achievement"] = new_achievement
    target["status"] = new_status
    return target


async def recalc_targets_for_user(user_id: str, notify: bool = True) -> int:
    """Recalculates all ACTIVE targets for a user. Used by PA approve-final hook.
    Returns count of targets recalculated.
    """
    now = datetime.now(timezone.utc)
    count = 0
    async for t in sales_targets_col.find(
        {"user_id": user_id, "period_end": {"$gt": now}, "deleted_at": None},
        {"_id": 0, "id": 1},
    ):
        await recalc_target(t["id"], notify=notify)
        count += 1
    return count


async def recalc_all_active(notify: bool = False) -> Dict[str, int]:
    """Admin manual trigger: recalc all active targets. Returns count summary."""
    now = datetime.now(timezone.utc)
    total = 0
    async for t in sales_targets_col.find(
        {"period_end": {"$gt": now}, "deleted_at": None},
        {"_id": 0, "id": 1},
    ):
        await recalc_target(t["id"], notify=notify)
        total += 1
    return {"recalculated": total}


# ────────────────────────────────────────────────────────────
# Notifications
# ────────────────────────────────────────────────────────────
_MILESTONE_MESSAGES = {
    "50":  ("🎉 50% Target Achieved!",  "You're halfway there! Keep pushing."),
    "75":  ("🚀 75% Target Achieved!",  "Almost there! Final push!"),
    "100": ("🏆 100% Target Achieved!", "Congratulations! Outstanding work."),
    "150": ("✨ 150%+ Exceeded!",        "Phenomenal performance — you're on fire!"),
}


async def _fire_milestone_notification(target: Dict[str, Any], milestone: str, achievement: Dict[str, Any]):
    title, base_msg = _MILESTONE_MESSAGES.get(milestone, (f"Milestone {milestone}%", ""))
    period_label = _format_period_label(target)
    msg = f"{base_msg} ({period_label}: ₹{achievement['revenue']:,.0f} / {achievement['pa_count']} PAs)"

    await notifications_col.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": target["user_id"],
        "title": title,
        "message": msg,
        "type": "target_milestone",
        "read": False,
        "link": "/sales/my-targets",
        "metadata": {"target_id": target["id"], "milestone": milestone},
        "created_at": datetime.now(timezone.utc),
    })


def _format_period_label(target: Dict[str, Any]) -> str:
    pt = target.get("period_type")
    if pt == "monthly":
        m = target.get("period_month") or 0
        names = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        return f"{names[m]} {target.get('period_year')}"
    if pt == "quarterly":
        return f"Q{target.get('period_quarter')} {target.get('period_year')}"
    return ""


# ────────────────────────────────────────────────────────────
# Helpers exposed to router
# ────────────────────────────────────────────────────────────
def format_period_label(target: Dict[str, Any]) -> str:
    """Public wrapper."""
    return _format_period_label(target)
