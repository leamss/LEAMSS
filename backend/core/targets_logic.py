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
    week: Optional[int] = None,
    date_str: Optional[str] = None,
) -> Tuple[datetime, datetime]:
    """Returns (start, end) datetimes for a period. End is exclusive (first day of next period)."""
    if period_type == "daily":
        if date_str:
            d = datetime.strptime(date_str, "%Y-%m-%d").date()
        elif month and (1 <= month <= 12):
            day = week or 1
            d = date(year, month, day)
        else:
            raise ValueError("Daily target requires date_str (YYYY-MM-DD)")
        start = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=timezone.utc)
        end = start + timedelta(days=1)
        return start, end

    if period_type == "weekly":
        if not week or not (1 <= week <= 53):
            raise ValueError("Weekly target requires week 1-53")
        start = datetime.fromisocalendar(year, week, 1).replace(tzinfo=timezone.utc)
        end = start + timedelta(days=7)
        return start, end

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

    if period_type == "yearly":
        start = datetime(year, 1, 1, tzinfo=timezone.utc)
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        return start, end

    raise ValueError(f"Unknown period_type: {period_type}")


def current_period(period_type: str, ref: Optional[datetime] = None) -> Dict[str, Any]:
    """Returns the current period dict (e.g., {year:2026, month:5} or {year:2026, week:44} or {year:2026, date:'...'})."""
    now = ref or datetime.now(timezone.utc)
    if period_type == "daily":
        return {
            "year": now.year,
            "month": now.month,
            "day": now.day,
            "date": now.strftime("%Y-%m-%d"),
        }
    if period_type == "weekly":
        iso_year, iso_week, _ = now.isocalendar()
        return {"year": iso_year, "week": iso_week}
    if period_type == "monthly":
        return {"year": now.year, "month": now.month}
    if period_type == "quarterly":
        return {"year": now.year, "quarter": (now.month - 1) // 3 + 1}
    if period_type == "yearly":
        return {"year": now.year}
    raise ValueError(f"Unknown period_type: {period_type}")


def days_remaining_in_period(period_end: datetime, ref: Optional[datetime] = None) -> int:
    """Calendar days left until period ends (exclusive end)."""
    now = ref or datetime.now(timezone.utc)
    period_end = _aware(period_end)
    if now >= period_end:
        return 0
    import math
    diff_seconds = (period_end - now).total_seconds()
    if diff_seconds <= 0:
        return 0
    return max(0, math.ceil(diff_seconds / 86400))


# ────────────────────────────────────────────────────────────
# Achievement calculation
# ────────────────────────────────────────────────────────────
async def compute_achievement(target: Dict[str, Any]) -> Dict[str, Any]:
    """Re-queries closed deals and CRM activities in the target period for target.user_id.
    Measures:
      - leads assigned/created
      - calls logged
      - follow-ups completed or created
      - conversions (won/converted leads + case_created PAs + approved sales)
      - revenue (PAs stage='case_created' + sales status='approved')
      - pa_count (count of deals)

    Returns achievement dict (does NOT persist — caller persists).
    """
    user_id = target["user_id"]
    period_start = _aware(target["period_start"])
    period_end = _aware(target["period_end"])

    revenue_total = 0.0
    closed_deals_count = 0
    seen_lead_ids = set()
    seen_sale_ids = set()

    # ─── (1) PA-driven revenue & deals: stage=case_created ──────────
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
    async for pa in pre_assessments_col.find(pa_query, {"_id": 0, "id": 1, "lead_id": 1, "proposal_fee": 1, "final_amount": 1, "sale_id": 1}):
        amount = float(pa.get("proposal_fee") or pa.get("final_amount") or 0)
        revenue_total += amount
        closed_deals_count += 1
        if pa.get("lead_id"):
            seen_lead_ids.add(pa["lead_id"])
        if pa.get("sale_id"):
            seen_sale_ids.add(pa["sale_id"])

    # ─── (2) Direct Sale revenue & deals: status=approved ───────────
    sales_col = db["sales"]
    sale_query = {
        "partner_id": user_id,
        "status": "approved",
        "approved_at": {"$gte": period_start, "$lt": period_end},
    }
    async for s in sales_col.find(sale_query, {"_id": 0, "id": 1, "lead_id": 1, "fee_amount": 1, "amount_received": 1}):
        if s.get("id") in seen_sale_ids:
            continue
        amount = float(s.get("amount_received") or s.get("fee_amount") or 0)
        revenue_total += amount
        closed_deals_count += 1
        if s.get("lead_id"):
            seen_lead_ids.add(s["lead_id"])

    # ─── (3) CRM Deals: stage=won or closed_won ─────────────────────
    deals_col = db["crm_deals"]
    deals_query = {
        "$and": [
            {"sales_person_id": user_id},
            {"stage": {"$in": ["won", "closed_won"]}},
            {
                "$or": [
                    {"closed_at": {"$gte": period_start, "$lt": period_end}},
                    {"closed_at": {"$gte": period_start.isoformat(), "$lt": period_end.isoformat()}},
                    {"updated_at": {"$gte": period_start, "$lt": period_end}},
                    {"updated_at": {"$gte": period_start.isoformat(), "$lt": period_end.isoformat()}},
                ]
            }
        ]
    }
    async for d in deals_col.find(deals_query, {"_id": 0, "id": 1, "lead_id": 1, "deal_value": 1}):
        lead_id = d.get("lead_id")
        if lead_id and lead_id in seen_lead_ids:
            continue
        if lead_id:
            seen_lead_ids.add(lead_id)
        val = float(d.get("deal_value") or 0)
        revenue_total += val
        closed_deals_count += 1

    # ─── (4) CRM Leads marked Won / Converted / Closed Won ──────────
    leads_col = db["leads"]
    leads_user_q = {"$or": [{"assigned_to": user_id}, {"created_by": user_id}]}
    won_leads_query = {
        "$and": [
            leads_user_q,
            {
                "$or": [
                    {"stage": {"$in": ["won", "closed_won", "converted"]}},
                    {"status": {"$in": ["won", "closed_won", "converted"]}},
                    {"converted": True}
                ]
            },
            {
                "$or": [
                    {"converted_at": {"$gte": period_start, "$lt": period_end}},
                    {"converted_at": {"$gte": period_start.isoformat(), "$lt": period_end.isoformat()}},
                    {"closed_at": {"$gte": period_start, "$lt": period_end}},
                    {"closed_at": {"$gte": period_start.isoformat(), "$lt": period_end.isoformat()}},
                    {"updated_at": {"$gte": period_start, "$lt": period_end}},
                    {"updated_at": {"$gte": period_start.isoformat(), "$lt": period_end.isoformat()}},
                ]
            }
        ]
    }
    def _parse_amount(val) -> float:
        if val is None or val == "":
            return 0.0
        if isinstance(val, (int, float)):
            return float(val)
        import re
        cleaned = re.sub(r"[^\d.]", "", str(val))
        try:
            return float(cleaned) if cleaned else 0.0
        except ValueError:
            return 0.0

    async for l in leads_col.find(won_leads_query, {"_id": 0, "id": 1, "deal_value": 1, "budget": 1, "amount": 1, "paid_amount": 1}):
        lid = l.get("id")
        if lid in seen_lead_ids:
            continue
        seen_lead_ids.add(lid)
        val = float(l.get("deal_value") or l.get("amount") or l.get("paid_amount") or _parse_amount(l.get("budget")) or 0)
        revenue_total += val
        closed_deals_count += 1

    # ─── (5) Direct CRM Payments recorded in period ─────────────────
    payments_col = db["crm_payments"]
    payments_query = {
        "$and": [
            {"sales_person_id": user_id},
            {"payment_status": {"$in": ["paid", "partially_paid"]}},
            {
                "$or": [
                    {"created_at": {"$gte": period_start, "$lt": period_end}},
                    {"created_at": {"$gte": period_start.isoformat(), "$lt": period_end.isoformat()}},
                ]
            }
        ]
    }
    async for p in payments_col.find(payments_query, {"_id": 0, "id": 1, "lead_id": 1, "paid_amount": 1}):
        lid = p.get("lead_id")
        if lid and lid in seen_lead_ids:
            continue
        paid = float(p.get("paid_amount") or 0)
        revenue_total += paid

    pa_count = closed_deals_count
    conversions_count = closed_deals_count

    # ─── (5) Activity metrics: Leads, Calls, Follow-ups ─────────────
    calls_col = db["crm_calls"]
    fu_col = db["follow_ups"]

    # Leads assigned or created in period
    leads_time_q = {
        "$or": [
            {"created_at": {"$gte": period_start, "$lt": period_end}},
            {"created_at": {"$gte": period_start.isoformat(), "$lt": period_end.isoformat()}},
            {"assigned_at": {"$gte": period_start, "$lt": period_end}},
            {"assigned_at": {"$gte": period_start.isoformat(), "$lt": period_end.isoformat()}},
        ]
    }
    leads_count = await leads_col.count_documents({"$and": [leads_user_q, leads_time_q]})

    # Calls logged in period
    calls_user_q = {"$or": [{"sales_person_id": user_id}, {"created_by": user_id}, {"user_id": user_id}]}
    calls_time_q = {
        "$or": [
            {"created_at": {"$gte": period_start, "$lt": period_end}},
            {"created_at": {"$gte": period_start.isoformat(), "$lt": period_end.isoformat()}},
            {"call_date": {"$gte": period_start, "$lt": period_end}},
            {"call_date": {"$gte": period_start.isoformat(), "$lt": period_end.isoformat()}}
        ]
    }
    calls_count = await calls_col.count_documents({"$and": [calls_user_q, calls_time_q]})

    # Follow-ups completed in period (ONLY counted when marked Completed)
    fu_user_q = {"$or": [{"assigned_to": user_id}, {"created_by": user_id}, {"completed_by": user_id}]}
    fu_status_q = {"status": "completed"}
    fu_time_q = {
        "$or": [
            {"completed_at": {"$gte": period_start, "$lt": period_end}},
            {"completed_at": {"$gte": period_start.isoformat(), "$lt": period_end.isoformat()}},
        ]
    }
    follow_ups_count = await fu_col.count_documents({"$and": [fu_user_q, fu_status_q, fu_time_q]})


    # ─── Targets & Achievements & Pending ───
    targets = target.get("targets", {})
    t_leads = int(targets.get("leads", 0) or 0)
    t_calls = int(targets.get("calls", 0) or 0)
    t_fu = int(targets.get("follow_ups", 0) or 0)
    t_conv = int(targets.get("conversions", 0) or 0)
    t_rev = float(targets.get("revenue", 0) or 0)
    t_pa = int(targets.get("pa_count", 0) or 0)

    rev_pct = round((revenue_total / t_rev * 100), 2) if t_rev > 0 else 0.0
    pa_pct = round((pa_count / t_pa * 100), 2) if t_pa > 0 else 0.0
    leads_pct = round((leads_count / t_leads * 100), 2) if t_leads > 0 else 0.0
    calls_pct = round((calls_count / t_calls * 100), 2) if t_calls > 0 else 0.0
    fu_pct = round((follow_ups_count / t_fu * 100), 2) if t_fu > 0 else 0.0
    conv_pct = round((conversions_count / t_conv * 100), 2) if t_conv > 0 else 0.0

    active_percentages = []
    if t_leads > 0: active_percentages.append(leads_pct)
    if t_calls > 0: active_percentages.append(calls_pct)
    if t_fu > 0: active_percentages.append(fu_pct)
    if t_conv > 0: active_percentages.append(conv_pct)
    if t_rev > 0: active_percentages.append(rev_pct)
    if t_pa > 0: active_percentages.append(pa_pct)

    if active_percentages:
        overall = round(sum(active_percentages) / len(active_percentages), 2)
    else:
        overall = max(rev_pct, pa_pct)

    pending = {
        "leads": max(0, t_leads - leads_count),
        "calls": max(0, t_calls - calls_count),
        "follow_ups": max(0, t_fu - follow_ups_count),
        "conversions": max(0, t_conv - conversions_count),
        "revenue": round(max(0.0, t_rev - revenue_total), 2),
        "pa_count": max(0, t_pa - pa_count),
    }

    return {
        "revenue": round(revenue_total, 2),
        "pa_count": pa_count,
        "leads": leads_count,
        "calls": calls_count,
        "follow_ups": follow_ups_count,
        "conversions": conversions_count,
        "revenue_percentage": rev_pct,
        "pa_count_percentage": pa_pct,
        "leads_percentage": leads_pct,
        "calls_percentage": calls_pct,
        "follow_ups_percentage": fu_pct,
        "conversions_percentage": conv_pct,
        "overall_percentage": round(overall, 2),
        "pending": pending,
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
    if pt == "daily":
        d_str = target.get("period_date")
        if d_str:
            try:
                return datetime.strptime(d_str, "%Y-%m-%d").strftime("%d %b %Y")
            except Exception:
                return d_str
        y = target.get("period_year")
        m = target.get("period_month")
        d = target.get("period_day") or 1
        if y and m:
            names = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            return f"{d} {names[m]} {y}"
        return "Daily"
    if pt == "weekly":
        return f"Week {target.get('period_week')}, {target.get('period_year')}"
    if pt == "monthly":
        m = target.get("period_month") or 0
        names = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        return f"{names[m]} {target.get('period_year')}"
    if pt == "quarterly":
        return f"Q{target.get('period_quarter')} {target.get('period_year')}"
    if pt == "yearly":
        return f"Year {target.get('period_year')}"
    return ""


# ────────────────────────────────────────────────────────────
# Helpers exposed to router
# ────────────────────────────────────────────────────────────
def format_period_label(target: Dict[str, Any]) -> str:
    """Public wrapper."""
    return _format_period_label(target)
