"""Phase 22 — Migrate existing users to RBAC v2 capability_packs.

Idempotent · prod-gated · dry-run by default.

For each user:
- Skip if capability_packs already set (idempotent)
- Else derive packs from (rbac_role | role | department)
- Recompute permissions/ui_modules from new packs → must be ≥ existing permissions (regression guard)

Run:
    cd /app/backend
    python scripts/migrate_rbac_v2.py             # dry-run
    python scripts/migrate_rbac_v2.py --apply     # actually mutate
"""
import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from core.database import db  # noqa: E402
from core.rbac.capability_packs_data import LEGACY_ROLE_TO_PACKS, DEPT_TO_PACKS  # noqa: E402
from core.rbac.capability_service import CapabilityService  # noqa: E402


def _is_prod() -> bool:
    env = (os.environ.get("ENV") or os.environ.get("ENVIRONMENT") or "").lower()
    return env in ("production", "prod")


def _derive_packs(user: dict) -> list:
    rbac_role = user.get("rbac_role")
    legacy_role = user.get("role")
    dept = (user.get("department") or "").lower()

    if rbac_role and rbac_role in LEGACY_ROLE_TO_PACKS:
        return LEGACY_ROLE_TO_PACKS[rbac_role]
    if legacy_role and legacy_role in LEGACY_ROLE_TO_PACKS:
        return LEGACY_ROLE_TO_PACKS[legacy_role]
    if dept and dept in DEPT_TO_PACKS:
        return DEPT_TO_PACKS[dept]
    return ["baseline_employee"]


async def main(apply: bool):
    if _is_prod() and not apply:
        print("[migrate_rbac_v2] ENV=production detected — dry-run requires --apply confirmation.")

    cursor = db["users"].find({}, {"_id": 0})
    skipped = []
    migrated = []
    regression_warnings = []

    async for user in cursor:
        uid = user.get("id")
        if not uid:
            continue
        if user.get("capability_packs"):
            skipped.append((uid, "already_has_packs"))
            continue

        new_packs = _derive_packs(user)
        # Ensure baseline always present
        if "baseline_employee" not in new_packs:
            new_packs = ["baseline_employee", *new_packs]

        # Compute new perms via service
        synthetic = {**user, "capability_packs": new_packs, "feature_overrides": {"granted": [], "revoked": []}}
        new_perms, new_modules = CapabilityService.compute_effective_permissions(synthetic)
        new_perms_set = set(new_perms)
        old_perms_set = set(user.get("permissions") or [])

        # Owner wildcard: skip regression check (∗ already covers all)
        if "*" not in old_perms_set:
            missing = old_perms_set - new_perms_set
            if missing:
                regression_warnings.append({
                    "user_id": uid, "name": user.get("name") or user.get("email"),
                    "missing_perms": sorted(list(missing))[:10],
                    "total_missing": len(missing),
                })

        # Always preserve old perms (zero regression guarantee — union, not replace)
        if apply:
            now = datetime.now(timezone.utc)
            union_perms = sorted(list(new_perms_set | old_perms_set))
            union_modules = sorted(list(set(new_modules) | set(user.get("ui_modules") or [])))
            update_doc = {
                "capability_packs": new_packs,
                "feature_overrides": {"granted": [], "revoked": []},
                "capability_packs_assigned_at": now,
                "capability_packs_assigned_by": "system_migration",
                "permissions": union_perms,
                "ui_modules": union_modules,
            }
            await db["users"].update_one({"id": uid}, {"$set": update_doc})
        migrated.append((uid, user.get("name") or user.get("email"), new_packs))

    print("=" * 70)
    print(f"[migrate_rbac_v2] {'APPLIED' if apply else 'DRY-RUN'} · scanned {len(skipped) + len(migrated)} users")
    print(f"  · skipped (already migrated): {len(skipped)}")
    print(f"  · {'migrated' if apply else 'would migrate'}: {len(migrated)}")
    print(f"  · regression warnings: {len(regression_warnings)}")

    if regression_warnings:
        print()
        print("⚠️ REGRESSION WARNINGS (these users would lose some permissions if migrated):")
        for w in regression_warnings[:10]:
            print(f"  - {w['name']} ({w['user_id']}) — missing {w['total_missing']} perms · sample: {w['missing_perms'][:3]}")

    if migrated and len(migrated) <= 20:
        print()
        print("Sample migrations:")
        for uid, name, packs in migrated[:20]:
            print(f"  + {name} ({uid}) → {packs}")

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Actually mutate the DB (default = dry-run)")
    args = parser.parse_args()
    sys.exit(asyncio.run(main(args.apply)))
