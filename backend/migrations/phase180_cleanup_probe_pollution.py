"""Phase 18.0 — Cleanup probe/placeholder pollution on `occupation_master`.

Background
==========
Earlier patches (Phase 17.1.3 + tester rounds) left placeholder strings in the
top-level editable fields while the official-grade content survived on the
`ai_draft.*` sub-block. This migration restores them.

Patch 18.0.1 broadens the original regex set to catch:
  • ``Tester probe …`` / ``probe task …`` / ``test_…`` / ``demo_…``
  • ``Phase 17.1.3 description update marker`` (any ``Phase X(.Y…)?`` placeholder)
  • Heuristic: top-level description shorter than 80 chars while
    ``ai_draft.description`` has 200+ chars (strong signal the top-level was
    wiped or placeholder'd while the AI baseline is intact)
  • Heuristic: top-level ``typical_tasks`` shorter than 3 items while
    ``ai_draft.typical_tasks`` has 5+ items

For each matching record this migration restores:
  • description     ← ai_draft.description (when available)
  • typical_tasks   ← ai_draft.typical_tasks (when available)
  • qualification_rules ← ai_draft.qualification_rules (when top-level is empty
    AND the AI block has content). Phase 18.1 made this a first-class field;
    restoring it here closes the data-loss gap from earlier patches.

Idempotent: subsequent runs report 0 changes once content has been promoted.

Wired into ``server.py`` startup AFTER the Phase 17.1.3 ``occupation_id``
backfill so pollution gets cleaned on every boot.
"""
from __future__ import annotations
import re
from datetime import datetime, timezone
from typing import Any, Dict

# Patterns that mark a polluted / placeholder top-level field.
_POLLUTION_PATTERNS = [
    re.compile(r"^Tester probe\b", re.IGNORECASE),
    re.compile(r"^probe task\b", re.IGNORECASE),
    re.compile(r"^test_", re.IGNORECASE),
    re.compile(r"^demo_", re.IGNORECASE),
    # Patch 18.0.1 — "Phase 17.1.3 description update marker", "Phase 18.1 …", etc.
    re.compile(r"^Phase\s+\d+(\.\d+)*\b", re.IGNORECASE),
]

# Heuristic thresholds (Patch 18.0.1)
_MIN_GOOD_DESC_LEN = 80          # top-level desc shorter than this AND
_MIN_AI_DESC_LEN = 200           # ai_draft desc longer than this → restore
_MIN_GOOD_TASKS_COUNT = 3        # fewer top-level tasks AND
_MIN_AI_TASKS_COUNT = 5          # 5+ ai_draft tasks → restore


def _matches_pollution(text: Any) -> bool:
    if not isinstance(text, str):
        return False
    s = text.strip()
    return any(p.match(s) for p in _POLLUTION_PATTERNS)


def _tasks_match_pollution(tasks: Any) -> bool:
    if not isinstance(tasks, list):
        return False
    return any(_matches_pollution(t) for t in tasks)


async def run_cleanup_probe_pollution(db) -> Dict[str, Any]:
    coll = db["occupation_master"]
    now = datetime.now(timezone.utc).isoformat()
    cleaned_by_country: Dict[str, int] = {}
    cleaned_total = 0
    scanned = 0

    cur = coll.find(
        {},
        {
            "_id": 0,
            "occupation_id": 1,
            "country_code": 1,
            "code": 1,
            "description": 1,
            "typical_tasks": 1,
            "qualification_rules": 1,
            "ai_draft": 1,
        },
    )
    async for d in cur:
        scanned += 1
        desc = d.get("description") or ""
        tasks = d.get("typical_tasks") or []
        qual = d.get("qualification_rules") or ""
        ai = d.get("ai_draft") or {}
        ai_desc = ai.get("description") or ""
        ai_tasks = ai.get("typical_tasks") or []
        ai_qual = ai.get("qualification_rules") or ""

        # --- Decide per-field whether a restore is warranted ----------------
        desc_needs_restore = (
            _matches_pollution(desc)
            or (len(desc.strip()) < _MIN_GOOD_DESC_LEN and len(ai_desc.strip()) >= _MIN_AI_DESC_LEN)
        )
        tasks_need_restore = (
            _tasks_match_pollution(tasks)
            or (len(tasks) < _MIN_GOOD_TASKS_COUNT and len(ai_tasks) >= _MIN_AI_TASKS_COUNT)
        )
        # qualification_rules is a Phase 18.1 first-class field — restore only
        # when it's empty AND the AI block has substantive content (>100 chars).
        qual_needs_restore = (not qual.strip()) and (len(ai_qual.strip()) >= 100)

        if not (desc_needs_restore or tasks_need_restore or qual_needs_restore):
            continue

        set_payload: Dict[str, Any] = {"updated_at": now}
        if desc_needs_restore and ai_desc:
            set_payload["description"] = ai_desc
        if tasks_need_restore and ai_tasks:
            set_payload["typical_tasks"] = ai_tasks
        if qual_needs_restore and ai_qual:
            set_payload["qualification_rules"] = ai_qual

        # Skip if no actual write would happen (AI block was also empty).
        if len(set_payload) == 1:  # only updated_at
            continue

        # Match by canonical occupation_id when present, else (cc, code)
        if d.get("occupation_id"):
            q = {"occupation_id": d["occupation_id"]}
        else:
            q = {"country_code": d.get("country_code"), "code": d.get("code")}

        await coll.update_one(q, {"$set": set_payload})
        cc = (d.get("country_code") or "?").upper()
        cleaned_by_country[cc] = cleaned_by_country.get(cc, 0) + 1
        cleaned_total += 1

    return {
        "status": "ok",
        "scanned": scanned,
        "cleaned": cleaned_total,
        "by_country": cleaned_by_country,
    }
