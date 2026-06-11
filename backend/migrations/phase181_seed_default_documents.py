"""Phase 18.1 — Seed default `required_documents[]` on `occupation_master`.

For every doc where `required_documents` is missing OR an empty list, this
migration writes the canonical 16-doc checklist (mirrors the hardcoded list
that `sales_occupations._build_doc_checklist` historically returned). Admin
can then curate per-occupation via the new Admin Edit UI.

Item shape: `{id, name, category, required, country_override}` where
`country_override` is `null` (applies to all countries unless overridden).

Idempotent: only touches records whose field is missing/empty.
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List


def _default_required_documents() -> List[Dict[str, Any]]:
    """Canonical 16-document baseline used by every occupation by default."""
    items_raw = [
        # Identity & Personal (3)
        ("Valid passport (bio page)", "Identity", True),
        ("Passport-sized photographs", "Identity", True),
        ("Birth certificate", "Identity", True),
        # Education (3)
        ("Degree certificate(s)", "Education", True),
        ("Academic transcripts (all years)", "Education", True),
        ("Equivalency certificate (if relevant)", "Education", False),
        # Employment (6)
        ("Employment reference letters on company letterhead", "Employment", True),
        ("Detailed role & responsibilities document", "Employment", True),
        ("Payslips (recent 6 months)", "Employment", True),
        ("Bank statements showing salary credit", "Employment", True),
        ("Tax returns / Form 16 (if applicable)", "Employment", True),
        ("PF / EPF statements", "Employment", False),
        # Character & Health (2)
        ("Police clearance certificate", "Character", True),
        ("Medical examination report", "Health", True),
        # English Proficiency (1)
        ("English language test results (IELTS/PTE/TOEFL)", "English", True),
        # Professional (1)
        ("Resume / CV (chronological)", "Professional", True),
    ]
    return [
        {
            "id": str(uuid.uuid4()),
            "name": name,
            "category": category,
            "required": required,
            "country_override": None,
        }
        for (name, category, required) in items_raw
    ]


async def run_seed_default_documents(db) -> Dict[str, Any]:
    coll = db["occupation_master"]
    now = datetime.now(timezone.utc).isoformat()
    seeded = 0
    skipped = 0

    cur = coll.find(
        {
            "$or": [
                {"required_documents": {"$exists": False}},
                {"required_documents": None},
                {"required_documents": []},
            ]
        },
        {"_id": 0, "occupation_id": 1, "country_code": 1, "code": 1},
    )
    async for d in cur:
        defaults = _default_required_documents()
        if d.get("occupation_id"):
            q = {"occupation_id": d["occupation_id"]}
        else:
            q = {"country_code": d.get("country_code"), "code": d.get("code")}
        res = await coll.update_one(q, {"$set": {"required_documents": defaults, "updated_at": now}})
        if res.modified_count:
            seeded += 1
        else:
            skipped += 1

    return {"status": "ok", "seeded": seeded, "skipped": skipped}
