"""Phase 4B (Part 2) — Express Sale Logic.

Pure functions:
  - Default sales_settings document + per-role monthly limits
  - Monthly usage counting (express sales created by a user in a given month)
  - Limit-exceeded check
  - Express reason validation
"""
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict, Any

from core.database import db

sales_settings_col = db["sales_settings"]
pre_assessments_col = db["pre_assessments"]

# Default limits (admin can override via /api/sales/express-settings)
DEFAULT_EXPRESS_SETTINGS = {
    "key": "express_sales",
    "express_sale_enabled": True,
    "express_monthly_limits": {
        "sales_executive": 5,
        "sr_sales_executive": 8,
        "sales_manager": 15,
        "sales_head": None,      # unlimited
        "admin_owner": None,
        "admin": None,
        "partner": 3,             # External partners — small limit
    },
    # Per-user overrides — { user_id: limit }. Value rules:
    #   N (int > 0)  → custom monthly limit for this user (overrides role default)
    #    0            → user is BLOCKED from express sales this month
    #   -1           → UNLIMITED (no monthly cap) for this user
    # Absence in this dict → fall back to role-based limit.
    "express_user_limit_overrides": {},
    "express_auto_approve_for_roles": ["sales_head", "admin_owner", "admin"],
    "express_max_value": 5000000,  # ₹50L cap on express PA proposal_fee
    "express_min_justification_chars": 30,
}

EXPRESS_REASONS = {
    "repeat_client",
    "pre_qualified_referral",
    "vip_customer",
    "direct_walkin",
    "partner_channel",
    "renewal_upgrade",
    "other",
}


async def get_express_settings() -> Dict[str, Any]:
    """Return current settings doc, falling back to defaults (and seeding if missing)."""
    doc = await sales_settings_col.find_one({"key": "express_sales"}, {"_id": 0})
    if not doc:
        await sales_settings_col.insert_one(dict(DEFAULT_EXPRESS_SETTINGS, created_at=datetime.now(timezone.utc)))
        doc = dict(DEFAULT_EXPRESS_SETTINGS)
    return doc


async def update_express_settings(updates: Dict[str, Any], updated_by: str) -> Dict[str, Any]:
    """Patch settings (admin-only validated at caller)."""
    safe = {k: v for k, v in updates.items() if k in (
        "express_sale_enabled", "express_monthly_limits", "express_user_limit_overrides",
        "express_auto_approve_for_roles", "express_max_value", "express_min_justification_chars",
    )}
    safe["updated_by"] = updated_by
    safe["updated_at"] = datetime.now(timezone.utc)
    await sales_settings_col.update_one(
        {"key": "express_sales"},
        {"$set": safe},
        upsert=True,
    )
    return await get_express_settings()


async def count_express_this_month(user_id: str, ref: Optional[datetime] = None) -> int:
    """Count express PAs created by user_id in the current calendar month.
    Counts ALL non-rejected statuses (pending/approved/proposal/case_created) so that
    rejected ones don't consume the quota.
    """
    now = ref or datetime.now(timezone.utc)
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    if now.month == 12:
        month_end = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        month_end = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)
    q = {
        "sale_type": "express",
        "created_by_user_id": user_id,
        "created_at": {"$gte": month_start, "$lt": month_end},
        "express_sale_approval_status": {"$ne": "rejected"},
    }
    return await pre_assessments_col.count_documents(q)


async def check_limit(user: Dict[str, Any]) -> Tuple[bool, int, Optional[int], str]:
    """Returns (allowed, used_count, limit_or_None, reason_message).
    None limit = unlimited.

    Lookup order:
      1. Per-user override (express_user_limit_overrides[user_id])
         - -1 → unlimited
         -  0 → blocked
         - >0 → custom monthly limit
      2. Role-based limit (express_monthly_limits[rbac_role | role])
      3. None → unlimited
    """
    settings = await get_express_settings()
    if not settings.get("express_sale_enabled", True):
        return False, 0, 0, "Express Sales are currently disabled by Admin"

    used = await count_express_this_month(user["id"])

    # 1) Per-user override
    overrides = settings.get("express_user_limit_overrides") or {}
    if user["id"] in overrides:
        ov = overrides[user["id"]]
        if ov == -1 or ov is None:
            return True, used, None, "OK — unlimited (admin override)"
        if ov == 0:
            return False, used, 0, "Express Sales blocked for this user by Admin"
        try:
            ov_int = int(ov)
        except (TypeError, ValueError):
            ov_int = None
        if ov_int is not None and ov_int > 0:
            if used >= ov_int:
                return False, used, ov_int, (
                    f"You have reached your monthly Express Sale limit ({used}/{ov_int}). "
                    f"Use Standard Sale or wait until next month."
                )
            return True, used, ov_int, "OK (admin custom limit)"

    # 2) Role-based limit
    rbac_role = user.get("rbac_role") or user.get("role")
    limits = settings.get("express_monthly_limits", {})
    limit = limits.get(rbac_role)
    if limit is None:
        # No explicit entry → try legacy 'role' fallback
        limit = limits.get(user.get("role"))

    if limit is None:
        return True, used, None, "OK — unlimited"
    if used >= limit:
        return False, used, limit, (
            f"You have reached your monthly Express Sale limit ({used}/{limit}). "
            f"Use Standard Sale or wait until next month."
        )
    return True, used, limit, "OK"


def validate_express_request(reason: str, justification: str, min_chars: int = 30) -> Optional[str]:
    """Returns error message if invalid, None if OK."""
    if reason not in EXPRESS_REASONS:
        return f"Reason must be one of: {sorted(EXPRESS_REASONS)}"
    if not justification or len(justification.strip()) < min_chars:
        return f"Justification must be at least {min_chars} characters"
    return None


def should_auto_approve(user: Dict[str, Any], settings: Dict[str, Any]) -> bool:
    """True if user's role is on the auto-approve list."""
    auto = set(settings.get("express_auto_approve_for_roles") or [])
    return bool(
        (user.get("rbac_role") in auto)
        or (user.get("role") in auto)
    )
