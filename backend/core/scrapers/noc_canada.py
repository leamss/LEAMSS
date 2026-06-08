"""Phase 10.1 · Canada NOC 2021 V1.0 Bulk Importer.

Official source: Statistics Canada — https://www.statcan.gc.ca/en/subjects/standard/noc/2021/indexV1

NOC 2021 V1.0 hierarchy (5-level, 5-digit codes):
  Level 1 — Broad Category    (1-digit, 10 total)
  Level 2 — Major Group       (2-digit, 45 total)
  Level 3 — Sub-major Group   (3-digit, 89 total)
  Level 4 — Minor Group       (4-digit, 162 total)
  Level 5 — Unit Group        (5-digit, 516 total)  ← These are the "occupations"

TEER (Training, Education, Experience, Responsibility) — second digit of the 5-digit code:
  TEER 0 → Management
  TEER 1 → University degree (Bachelor/Master/PhD)
  TEER 2 → College / apprenticeship (2+ yrs) OR supervisor role
  TEER 3 → College / apprenticeship (<2 yrs) OR 6+ months training
  TEER 4 → High school + few weeks training
  TEER 5 → Short-term work demo / no formal education

Two CSV files used:
  1. classification-structure.csv  — 822 rows (10+45+89+162+516) with hierarchy
  2. elements.csv                  — 44,037 rows: examples, duties, requirements

This importer is IDEMPOTENT: re-runs only update changed fields, preserving:
  - status (draft → verified by admin)
  - linked_product_id
  - custom_qa
  - verification metadata
  - manually edited assessing_authority
"""
from __future__ import annotations

import csv
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

SOURCE_NAME = "statcan_noc_2021_v1.0"
SOURCE_URL = "https://www.statcan.gc.ca/en/subjects/standard/noc/2021/indexV1"

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "noc_2021"
STRUCTURE_CSV = DATA_DIR / "noc-2021-v1.0-classification-structure.csv"
ELEMENTS_CSV = DATA_DIR / "noc-2021-v1.0-elements.csv"

# Element-type → target field on occupation_master
ELEMENT_TYPE_MAP = {
    "All examples": "alternative_titles",
    "Illustrative example(s)": "illustrative_titles",
    "Main duties": "typical_tasks",
    "Employment requirements": "employment_requirements",
    "Exclusion(s)": "exclusions",
    "Inclusion(s)": "inclusions",
    "Additional information": "additional_info",
}


def _teer_label(teer: int) -> str:
    return {
        0: "Management",
        1: "University degree",
        2: "College/apprenticeship (2+ yrs) or supervisor",
        3: "College/apprenticeship (<2 yrs)",
        4: "Secondary school + brief training",
        5: "Short-term work demonstration",
    }.get(teer, "—")


def _parse_structure(path: Path) -> Dict[str, Any]:
    """Parse structure CSV → returns {hierarchy_lookup, unit_groups_by_code}."""
    lookup: Dict[str, Dict[str, Any]] = {}  # code → {level, title, definition}
    with open(path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            code = (row["Code - NOC 2021 V1.0"] or "").strip()
            if not code:
                continue
            lookup[code] = {
                "level": int(row["Level"]),
                "hierarchy_label": row["Hierarchical structure"].strip(),
                "title": row["Class title"].strip(),
                "definition": (row["Class definition"] or "").strip(),
            }
    return lookup


def _parse_elements(path: Path) -> Dict[str, Dict[str, List[str]]]:
    """Parse elements CSV → returns {code → {field → [items]}}."""
    bucket: Dict[str, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))
    with open(path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            code = (row["Code - NOC 2021 V1.0"] or "").strip()
            etype = row["Element Type Label English"].strip()
            desc = (row["Element Description English"] or "").strip()
            field = ELEMENT_TYPE_MAP.get(etype)
            if not field or not desc:
                continue
            bucket[code][field].append(desc)
    return bucket


def _build_hierarchy_meta(code: str, lookup: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """For a 5-digit unit-group code, build the hierarchy chain."""
    broad = code[:1]
    major = code[:2]
    submajor = code[:3]
    minor = code[:4]
    return {
        "broad_category": {
            "code": broad,
            "title": (lookup.get(broad) or {}).get("title") or "—",
        },
        "major_group": {
            "code": major,
            "title": (lookup.get(major) or {}).get("title") or "—",
        },
        "sub_major_group": {
            "code": submajor,
            "title": (lookup.get(submajor) or {}).get("title") or "—",
        },
        "minor_group": {
            "code": minor,
            "title": (lookup.get(minor) or {}).get("title") or "—",
        },
    }


def _build_doc(code: str, lookup: Dict[str, Any], elements: Dict[str, Dict[str, List[str]]], now: datetime) -> Dict[str, Any]:
    """Construct a full occupation_master document for a 5-digit unit group."""
    meta = lookup[code]
    teer = int(code[1])  # 2nd digit is TEER (0-5)
    elems = elements.get(code, {})

    # Clean + dedupe alternative_titles (combine "All examples" + "Illustrative example(s)")
    alt_pool: List[str] = []
    for src in ("alternative_titles", "illustrative_titles"):
        for t in elems.get(src) or []:
            t = t.strip()
            if t and t not in alt_pool:
                alt_pool.append(t)

    # Main duties → typical_tasks (list)
    typical_tasks = [t.strip() for t in (elems.get("typical_tasks") or []) if t.strip()]

    # Employment requirements joined into a single readable string
    emp_req = " ".join((elems.get("employment_requirements") or [])).strip()

    return {
        "country_code": "CA",
        "code": code,
        "occupation_id": f"ca-{code}",
        "title": meta["title"],
        "classification_type": "NOC",
        "classification_version": "2021_V1.0",
        "skill_level": teer,           # for legacy field compatibility
        "teer_category": teer,
        "teer_label": _teer_label(teer),
        "hierarchy": _build_hierarchy_meta(code, lookup),
        "description": meta["definition"],
        "alternative_titles": alt_pool[:30],  # cap to 30 to control doc size
        "typical_tasks": typical_tasks[:25],
        "employment_requirements": emp_req or None,
        "exclusions": (elems.get("exclusions") or [])[:10],
        "additional_info": (elems.get("additional_info") or [])[:5],
        "data_source": SOURCE_NAME,
        "data_source_url": SOURCE_URL,
        "last_enriched_at": now,
        "updated_at": now,
    }


# Fields that this scraper OWNS (will overwrite on re-run).
# Other fields (status, verification, linked_product_id, custom_qa, assessing_authority, etc.)
# are NEVER touched, preserving admin edits.
SCRAPER_OWNED_FIELDS = {
    "title",
    "classification_type",
    "classification_version",
    "skill_level",
    "teer_category",
    "teer_label",
    "hierarchy",
    "description",
    "alternative_titles",
    "typical_tasks",
    "employment_requirements",
    "exclusions",
    "additional_info",
    "data_source",
    "data_source_url",
    "last_enriched_at",
    "updated_at",
}


async def apply_to_db(db, dry_run: bool = True, actor: str = "system") -> Dict[str, Any]:
    """Run the NOC 2021 import against `occupation_master`.

    Returns counts: {created, updated, skipped_unchanged, total_unit_groups}
    """
    if not STRUCTURE_CSV.exists():
        raise FileNotFoundError(f"Missing NOC structure CSV at {STRUCTURE_CSV}")
    if not ELEMENTS_CSV.exists():
        raise FileNotFoundError(f"Missing NOC elements CSV at {ELEMENTS_CSV}")

    lookup = _parse_structure(STRUCTURE_CSV)
    elements = _parse_elements(ELEMENTS_CSV)

    # 5-digit unit-group codes only
    unit_codes = [c for c, m in lookup.items() if m["level"] == 5]
    now = datetime.now(timezone.utc)

    coll = db["occupation_master"]
    created = 0
    updated = 0
    skipped_unchanged = 0
    sample_codes_changed: List[str] = []

    for code in unit_codes:
        new_doc = _build_doc(code, lookup, elements, now)
        existing = await coll.find_one({"country_code": "CA", "code": code}, {"_id": 0})

        if existing is None:
            # INSERT — set status=draft and creation metadata
            insert_doc = {
                **new_doc,
                "status": "draft",
                "created_at": now,
                "created_by": actor,
            }
            if not dry_run:
                await coll.insert_one(insert_doc)
            created += 1
            if len(sample_codes_changed) < 5:
                sample_codes_changed.append(code)
        else:
            # UPDATE — only scraper-owned fields, keep status/verification intact.
            # Exclude timestamps from change-detection (they always differ on re-run).
            content_fields = SCRAPER_OWNED_FIELDS - {"last_enriched_at", "updated_at"}
            if all(existing.get(f) == new_doc[f] for f in content_fields if f in new_doc):
                skipped_unchanged += 1
                continue
            patch = {f: new_doc[f] for f in SCRAPER_OWNED_FIELDS if f in new_doc}
            if not dry_run:
                await coll.update_one(
                    {"country_code": "CA", "code": code},
                    {"$set": patch},
                )
            updated += 1
            if len(sample_codes_changed) < 5:
                sample_codes_changed.append(code)

    return {
        "source": SOURCE_NAME,
        "source_url": SOURCE_URL,
        "dry_run": dry_run,
        "total_unit_groups_in_csv": len(unit_codes),
        "counts": {
            "created": created,
            "updated": updated,
            "skipped_unchanged": skipped_unchanged,
        },
        "sample_codes_changed": sample_codes_changed,
        "teer_distribution_in_csv": _teer_distribution(unit_codes),
        "ran_at": now.isoformat(),
        "actor": actor,
    }


def _teer_distribution(codes: List[str]) -> Dict[int, int]:
    dist: Dict[int, int] = defaultdict(int)
    for c in codes:
        try:
            dist[int(c[1])] += 1
        except (IndexError, ValueError):
            pass
    return dict(sorted(dist.items()))
