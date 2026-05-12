"""RBAC Phase 1 Migration — idempotent.

Seeds:
- 8 departments
- ~150 permissions
- 16 system roles

Backfills existing users with:
- user_type, department, rbac_role (from legacy role mapping)
- employee_id (LMS-2026-NNNN) for internal users
- partner_code (PRT-NNNN) for external users
- date_of_joining (from created_at)
- cached permissions[] and ui_modules[] from their role
- security fields (two_fa_enabled=false, etc.)

Creates indexes for the new collections + extended users fields.

Migration is safe to run multiple times. Each run is logged in
the 'migrations' collection.
"""
import uuid
from datetime import datetime, timezone
from core.database import db, users_col
from core.rbac.seed_data import DEPARTMENTS, PERMISSIONS, ROLES

departments_col = db["departments"]
permissions_col = db["permissions"]
roles_col = db["roles"]
teams_col = db["teams"]
user_role_history_col = db["user_role_history"]
migrations_col = db["migrations"]

MIGRATION_KEY = "rbac_phase1_v1"


# ─────────────────────────────────────────────────────────
# Legacy role mapping
# ─────────────────────────────────────────────────────────
LEGACY_ROLE_MAP = {
    "admin":        {"rbac_role": "admin_owner",  "user_type": "internal", "department": "admin"},
    "partner":      {"rbac_role": "partner",      "user_type": "external", "department": "sales"},
    "case_manager": {"rbac_role": "case_manager", "user_type": "internal", "department": "operations"},
    "client":       {"rbac_role": "client",       "user_type": "client",   "department": None},

    # Forward-compat: users whose legacy 'role' already holds a new RBAC key
    "admin_owner":         {"rbac_role": "admin_owner",         "user_type": "internal", "department": "admin"},
    "compliance_officer":  {"rbac_role": "compliance_officer",  "user_type": "internal", "department": "compliance"},
    "sales_head":          {"rbac_role": "sales_head",          "user_type": "internal", "department": "sales"},
    "sales_manager":       {"rbac_role": "sales_manager",       "user_type": "internal", "department": "sales"},
    "sr_sales_executive":  {"rbac_role": "sr_sales_executive",  "user_type": "internal", "department": "sales"},
    "sales_executive":     {"rbac_role": "sales_executive",     "user_type": "internal", "department": "sales"},
    "marketing_head":      {"rbac_role": "marketing_head",      "user_type": "internal", "department": "marketing"},
    "marketing_executive": {"rbac_role": "marketing_executive", "user_type": "internal", "department": "marketing"},
    "ops_head":            {"rbac_role": "ops_head",            "user_type": "internal", "department": "operations"},
    "doc_verifier":        {"rbac_role": "doc_verifier",        "user_type": "internal", "department": "operations"},
    "hr_head":             {"rbac_role": "hr_head",             "user_type": "internal", "department": "hr"},
    "hr_executive":        {"rbac_role": "hr_executive",        "user_type": "internal", "department": "hr"},
    "accounts_head":       {"rbac_role": "accounts_head",       "user_type": "internal", "department": "accounts"},
    "accounts_executive":  {"rbac_role": "accounts_executive",  "user_type": "internal", "department": "accounts"},
    "it_admin":            {"rbac_role": "it_admin",            "user_type": "internal", "department": "it"},
}


# ─────────────────────────────────────────────────────────
# Counters for employee_id / partner_code
# ─────────────────────────────────────────────────────────
async def _next_employee_id() -> str:
    year = datetime.now(timezone.utc).year
    prefix = f"LMS-{year}-"
    # Find current max
    cursor = users_col.find({"employee_id": {"$regex": f"^{prefix}"}}, {"_id": 0, "employee_id": 1})
    existing_nums = []
    async for u in cursor:
        try:
            existing_nums.append(int(u["employee_id"].split("-")[-1]))
        except (ValueError, IndexError):
            continue
    next_num = (max(existing_nums) + 1) if existing_nums else 1
    return f"{prefix}{next_num:04d}"


async def _next_partner_code() -> str:
    cursor = users_col.find({"partner_code": {"$regex": "^PRT-"}}, {"_id": 0, "partner_code": 1})
    existing_nums = []
    async for u in cursor:
        try:
            existing_nums.append(int(u["partner_code"].split("-")[-1]))
        except (ValueError, IndexError):
            continue
    next_num = (max(existing_nums) + 1) if existing_nums else 1
    return f"PRT-{next_num:04d}"


# ─────────────────────────────────────────────────────────
# Seed helpers — upsert by unique key
# ─────────────────────────────────────────────────────────
async def _seed_departments():
    now = datetime.now(timezone.utc)
    seeded, updated = 0, 0
    for d in DEPARTMENTS:
        existing = await departments_col.find_one({"key": d["key"]}, {"_id": 0})
        if existing:
            # Refresh display fields but preserve head_user_id
            await departments_col.update_one(
                {"key": d["key"]},
                {"$set": {
                    "name": d["name"], "icon": d["icon"], "color": d["color"],
                    "description": d["description"], "is_system": True,
                }}
            )
            updated += 1
        else:
            doc = {
                "id": str(uuid.uuid4()),
                **d,
                "head_user_id": None,
                "is_active": True,
                "is_system": True,
                "created_at": now,
            }
            await departments_col.insert_one(doc)
            seeded += 1
    return {"seeded": seeded, "updated": updated, "total": len(DEPARTMENTS)}


async def _seed_permissions():
    now = datetime.now(timezone.utc)
    seeded, updated = 0, 0
    for p in PERMISSIONS:
        existing = await permissions_col.find_one({"key": p["key"]}, {"_id": 0})
        if existing:
            await permissions_col.update_one(
                {"key": p["key"]},
                {"$set": {**p, "is_system": True}}
            )
            updated += 1
        else:
            doc = {
                "id": str(uuid.uuid4()),
                **p,
                "is_system": True,
                "created_at": now,
            }
            await permissions_col.insert_one(doc)
            seeded += 1
    return {"seeded": seeded, "updated": updated, "total": len(PERMISSIONS)}


async def _seed_roles():
    now = datetime.now(timezone.utc)
    seeded, updated = 0, 0
    for r in ROLES:
        existing = await roles_col.find_one({"key": r["key"]}, {"_id": 0})
        if existing:
            await roles_col.update_one(
                {"key": r["key"]},
                {"$set": {**r, "is_system": True, "is_active": True, "updated_at": now}}
            )
            updated += 1
        else:
            doc = {
                "id": str(uuid.uuid4()),
                **r,
                "is_system": True,
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            }
            await roles_col.insert_one(doc)
            seeded += 1
    return {"seeded": seeded, "updated": updated, "total": len(ROLES)}


# ─────────────────────────────────────────────────────────
# Backfill users
# ─────────────────────────────────────────────────────────
async def _backfill_users():
    backfilled = 0
    skipped = 0
    errors = []

    # Build role lookup once
    role_docs = {}
    async for r in roles_col.find({}, {"_id": 0}):
        role_docs[r["key"]] = r

    cursor = users_col.find({}, {"_id": 0})
    async for user in cursor:
        try:
            legacy_role = user.get("role")
            mapping = LEGACY_ROLE_MAP.get(legacy_role)
            if not mapping:
                errors.append(f"User {user.get('email')}: unknown role '{legacy_role}'")
                skipped += 1
                continue

            updates = {}

            # Core RBAC fields — only set if missing
            if not user.get("rbac_role"):
                updates["rbac_role"] = mapping["rbac_role"]
            if not user.get("user_type"):
                updates["user_type"] = mapping["user_type"]
            if "department" not in user or user.get("department") is None and mapping["department"]:
                updates["department"] = mapping["department"]

            # Cached permissions & ui_modules from role
            role_doc = role_docs.get(mapping["rbac_role"])
            if role_doc:
                if not user.get("permissions") or user.get("permissions") == []:
                    updates["permissions"] = role_doc.get("permissions", [])
                if not user.get("ui_modules") or user.get("ui_modules") == []:
                    updates["ui_modules"] = role_doc.get("ui_modules", [])

            # Defaults for arrays
            if "custom_permissions_granted" not in user:
                updates["custom_permissions_granted"] = []
            if "custom_permissions_revoked" not in user:
                updates["custom_permissions_revoked"] = []

            # Internal employee fields
            if mapping["user_type"] == "internal" and not user.get("employee_id"):
                updates["employee_id"] = await _next_employee_id()
            if mapping["user_type"] == "internal":
                if not user.get("date_of_joining"):
                    updates["date_of_joining"] = user.get("created_at") or datetime.now(timezone.utc)
                if not user.get("employment_status"):
                    updates["employment_status"] = "active"
                if not user.get("employment_type"):
                    updates["employment_type"] = "full_time"
                if not user.get("work_mode"):
                    updates["work_mode"] = "onsite"

            # External partner fields
            if mapping["user_type"] == "external" and not user.get("partner_code"):
                updates["partner_code"] = await _next_partner_code()
            if mapping["user_type"] == "external":
                if not user.get("commission_tier"):
                    updates["commission_tier"] = "bronze"
                if "partner_agreement_signed" not in user:
                    updates["partner_agreement_signed"] = False

            # Security defaults
            if "two_fa_enabled" not in user:
                updates["two_fa_enabled"] = False
            if "two_fa_secret" not in user:
                updates["two_fa_secret"] = None
            if "failed_login_count" not in user:
                updates["failed_login_count"] = 0

            if updates:
                await users_col.update_one({"id": user["id"]}, {"$set": updates})
                backfilled += 1
            else:
                skipped += 1

        except Exception as e:
            errors.append(f"User {user.get('email', user.get('id'))}: {str(e)}")

    return {"backfilled": backfilled, "skipped_no_changes": skipped, "errors": errors}


# ─────────────────────────────────────────────────────────
# Indexes
# ─────────────────────────────────────────────────────────
async def _create_indexes():
    """Idempotent — Mongo silently skips if index already exists."""
    # users — new compound + sparse unique indexes
    await users_col.create_index([("user_type", 1), ("department", 1), ("rbac_role", 1)], name="rbac_user_type_dept_role")
    await users_col.create_index("reports_to", sparse=True, name="rbac_reports_to")
    await users_col.create_index("team_id", sparse=True, name="rbac_team_id")
    await users_col.create_index("employment_status", sparse=True, name="rbac_employment_status")
    await users_col.create_index("employee_id", unique=True, sparse=True, name="rbac_employee_id_unique")
    await users_col.create_index("partner_code", unique=True, sparse=True, name="rbac_partner_code_unique")
    await users_col.create_index("rbac_role", sparse=True, name="rbac_role_idx")

    # roles
    await roles_col.create_index("key", unique=True, name="role_key_unique")
    await roles_col.create_index([("department", 1), ("hierarchy_level", 1)], name="role_dept_level")

    # permissions
    await permissions_col.create_index("key", unique=True, name="perm_key_unique")
    await permissions_col.create_index([("resource", 1), ("action", 1)], name="perm_resource_action")

    # departments
    await departments_col.create_index("key", unique=True, name="dept_key_unique")

    # teams
    await teams_col.create_index("department", name="team_dept")
    await teams_col.create_index("manager_id", sparse=True, name="team_manager")

    # user_role_history
    await user_role_history_col.create_index([("user_id", 1), ("effective_date", -1)], name="urh_user_date")

    return True


# ─────────────────────────────────────────────────────────
# Main entry
# ─────────────────────────────────────────────────────────
async def run_migration(force: bool = False) -> dict:
    """Execute the full migration. Returns a detailed report."""
    started_at = datetime.now(timezone.utc)
    report = {
        "key": MIGRATION_KEY,
        "started_at": started_at.isoformat(),
        "departments": None,
        "permissions": None,
        "roles": None,
        "users_backfill": None,
        "indexes_created": False,
        "warnings": [],
        "completed_at": None,
        "status": "running",
    }

    try:
        # Seed catalogs FIRST (roles need to exist before user backfill caches their perms)
        report["departments"] = await _seed_departments()
        report["permissions"] = await _seed_permissions()
        report["roles"] = await _seed_roles()

        # Create indexes
        await _create_indexes()
        report["indexes_created"] = True

        # Backfill users
        report["users_backfill"] = await _backfill_users()
        if report["users_backfill"]["errors"]:
            report["warnings"].extend(report["users_backfill"]["errors"])

        report["completed_at"] = datetime.now(timezone.utc).isoformat()
        report["status"] = "completed"

    except Exception as e:
        report["status"] = "failed"
        report["error"] = str(e)
        report["completed_at"] = datetime.now(timezone.utc).isoformat()

    # Log migration run
    try:
        await migrations_col.insert_one({
            "id": str(uuid.uuid4()),
            **report,
            "created_at": datetime.now(timezone.utc),
        })
    except Exception:
        pass

    return report


async def has_already_run() -> bool:
    """Check if migration has run successfully at least once."""
    last = await migrations_col.find_one(
        {"key": MIGRATION_KEY, "status": "completed"},
        {"_id": 0},
        sort=[("created_at", -1)],
    )
    return last is not None
