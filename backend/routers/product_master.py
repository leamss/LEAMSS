"""Product Master Router — Unified LEAMSS Portal Module A.

Dedicated standalone router managing the Single Source of Truth for all visa
products across 191 countries.

Endpoints:
  GET    /api/product-master                - List all product masters (with filters)
  GET    /api/product-master/summary-stats  - Aggregated stats (total, active, draft, countries)
  GET    /api/product-master/{product_id}   - Get single product master
  POST   /api/product-master                - Create new product master (Admin only)
  PUT    /api/product-master/{product_id}   - Update product master (Admin only)
  DELETE /api/product-master/{product_id}   - Archive product master (Admin only, soft delete)
  POST   /api/product-master/{product_id}/verify - Mark product as verified (Admin only)
  POST   /api/product-master/{product_id}/clone  - Clone product as new draft (Admin only)
  POST   /api/product-master/ai-research    - Official government AI web research (Admin only)
"""
from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from core.auth import get_current_user
from core.database import db, product_master_col, products_col, workflow_steps_col
from core.services import log_activity
from services.product_master_ai_service import research_product_with_ai

from services.product_master_seed_data import get_canonical_seeds
from core.occupation_intelligence import (
    detect_occupation_in_query,
    detect_country_and_visa_in_query,
    CountryVisaQueryIntent,
    get_full_occupation_profile,
    synthesize_complete_statutory_response,
    get_statutory_fees_and_commercials,
    generate_sales_qualification_questions,
    normalize_country,
)
from services.country_regulatory_authorities import (
    COUNTRY_REGULATORY_AUTHORITIES,
    COUNTRY_ALIASES,
    resolve_country_key,
    get_country_authority_info,
)
from routers.ai_workflow_builder import COUNTRY_REFERENCES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/product-master", tags=["Product Master"])


class ProductMasterAiResearchRequest(BaseModel):
    country: str
    visa_name: str
    category: Optional[str] = "skilled_migration"
    visa_subclass: Optional[str] = ""
    government_url: Optional[str] = None
    migrate_page_url: Optional[str] = None
    additional_context: Optional[str] = None

    class Config:
        extra = "forbid"


class SalesAiQueryRequest(BaseModel):
    product_id: Optional[str] = None
    country: Optional[str] = ""
    visa_name: Optional[str] = ""
    visa_subclass: Optional[str] = ""
    client_scenario_or_question: str

    class Config:
        extra = "forbid"


class SalesAiTranslateRequest(BaseModel):
    text: str
    target_language: str  # "English" | "Marathi" | "Hindi"
    source_language: Optional[str] = None
    country: Optional[str] = None
    visa_subclass: Optional[str] = None

    class Config:
        extra = "forbid"


def _require_admin(user: Dict[str, Any]) -> None:
    role = user.get("role") or user.get("rbac_role")
    permissions = user.get("permissions") or []
    if role not in ("admin", "admin_owner", "super_admin") and "product_cost.manage.any" not in permissions and "system.user_manage.any" not in permissions:
        raise HTTPException(status_code=403, detail="Admin authorization required")


def find_canonical_match(country: str, name: str, subclass: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Match a product by country, name, or subclass code to its canonical statutory specification."""
    c_norm = (country or "").strip().lower()
    seeds = get_canonical_seeds()

    # 1. Direct match on country + subclass code
    if subclass and str(subclass).strip():
        sc_str = str(subclass).strip().lower()
        for s in seeds:
            if s.get("country", "").lower() == c_norm:
                seed_sc = str(s.get("visa_subclass", "")).lower()
                if seed_sc == sc_str or sc_str in seed_sc or seed_sc in sc_str:
                    return s

    # 2. Match by keywords in name + country
    n_lower = (name or "").lower()
    for s in seeds:
        if s.get("country", "").lower() != c_norm:
            continue
        sc = str(s.get("visa_subclass", "")).lower()
        if sc and sc in n_lower:
            return s
        s_name_lower = s.get("name", "").lower()
        # Subclass number matches
        for code in ["189", "190", "491", "482", "500", "600", "820", "801"]:
            if code in n_lower and code in s_name_lower:
                return s
        if "express entry" in n_lower and "express entry" in s_name_lower:
            return s
        if "fsw" in n_lower and "fsw" in s_name_lower:
            return s
        if "pnp" in n_lower and "pnp" in s_name_lower:
            return s
        if ("study" in n_lower or "student" in n_lower) and ("study" in s_name_lower or "student" in s_name_lower):
            return s
        if ("visitor" in n_lower or "tourist" in n_lower) and ("visitor" in s_name_lower or "tourist" in s_name_lower):
            return s
        if "chancenkarte" in n_lower and "chancenkarte" in s_name_lower:
            return s
        if "blue card" in n_lower and "blue card" in s_name_lower:
            return s
        if "h-1b" in n_lower or "h1b" in n_lower:
            if "h-1b" in s_name_lower or "h1b" in s_name_lower:
                return s

    # 3. Fallback to default skilled migration seed for the country
    if any(k in n_lower for k in ["skilled", "pr", "permanent"]):
        for s in seeds:
            if s.get("country", "").lower() == c_norm and s.get("category") == "skilled_migration":
                return s

    return None


async def _seed_standard_subclasses():
    """Ensure verified canonical statutory subclasses exist in product_master_col."""
    now = datetime.now(timezone.utc)
    for seed in get_canonical_seeds():
        sid = seed["id"]
        existing = await product_master_col.find_one({"id": sid})
        if not existing:
            doc = {
                **seed,
                "created_at": now,
                "updated_at": now,
                "last_verified_at": now.isoformat(),
                "last_verified_by": "Statutory Authority Sync",
                "version": 1,
            }
            await product_master_col.insert_one(doc)
            await products_col.update_one(
                {"id": sid},
                {"$set": dict(doc)},
                upsert=True
            )


async def _deduplicate_products():
    """Soft-archive or remove duplicate products and normalize country names."""
    try:
        # 1. Soft-archive records containing "(Copy)" or "(copy)"
        await product_master_col.update_many(
            {"name": {"$regex": r"\(copy\)", "$options": "i"}, "status": {"$ne": "archived"}},
            {"$set": {"status": "archived", "archived_at": datetime.now(timezone.utc)}}
        )
        await products_col.update_many(
            {"name": {"$regex": r"\(copy\)", "$options": "i"}, "status": {"$ne": "archived"}},
            {"$set": {"status": "archived", "archived_at": datetime.now(timezone.utc)}}
        )

        # 2. Normalize country names in database
        await product_master_col.update_many({"country": {"$regex": r"^canada$", "$options": "i"}}, {"$set": {"country": "Canada", "country_code": "CA"}})
        await products_col.update_many({"country": {"$regex": r"^canada$", "$options": "i"}}, {"$set": {"country": "Canada", "country_code": "CA"}})

        await product_master_col.update_many({"country": {"$regex": r"^(usa|us|united states|united states of america)$", "$options": "i"}}, {"$set": {"country": "United States", "country_code": "US"}})
        await products_col.update_many({"country": {"$regex": r"^(usa|us|united states|united states of america)$", "$options": "i"}}, {"$set": {"country": "United States", "country_code": "US"}})

        await product_master_col.update_many({"country": {"$regex": r"^(uk|united kingdom|great britain)$", "$options": "i"}}, {"$set": {"country": "United Kingdom", "country_code": "GB"}})
        await products_col.update_many({"country": {"$regex": r"^(uk|united kingdom|great britain)$", "$options": "i"}}, {"$set": {"country": "United Kingdom", "country_code": "GB"}})

        await product_master_col.update_many({"country": {"$regex": r"^(nz|new zealand)$", "$options": "i"}}, {"$set": {"country": "New Zealand", "country_code": "NZ"}})
        await products_col.update_many({"country": {"$regex": r"^(nz|new zealand)$", "$options": "i"}}, {"$set": {"country": "New Zealand", "country_code": "NZ"}})

        # 3. Normalize categories in database
        await product_master_col.update_many({"category": {"$in": ["pr", "skilled", "skilled_worker"]}}, {"$set": {"category": "skilled_migration"}})
        await product_master_col.update_many({"category": {"$in": ["partner", "spouse"]}}, {"$set": {"category": "family"}})
        await product_master_col.update_many({"category": {"$in": ["investor", "investment"]}}, {"$set": {"category": "business"}})
        await products_col.update_many({"category": {"$in": ["pr", "skilled", "skilled_worker"]}}, {"$set": {"category": "skilled_migration"}})
        await products_col.update_many({"category": {"$in": ["partner", "spouse"]}}, {"$set": {"category": "family"}})
        await products_col.update_many({"category": {"$in": ["investor", "investment"]}}, {"$set": {"category": "business"}})

        # 4. Remove exact duplicate documents sharing identical 'id' string (keeping only first _id)
        id_pipeline = [
            {"$match": {"status": {"$ne": "archived"}}},
            {"$group": {
                "_id": "$id",
                "doc_ids": {"$push": "$_id"},
                "count": {"$sum": 1}
            }},
            {"$match": {"count": {"$gt": 1}}}
        ]
        dup_ids = await product_master_col.aggregate(id_pipeline).to_list(500)
        for grp in dup_ids:
            doc_ids = grp.get("doc_ids", [])
            for extra_id in doc_ids[1:]:
                await product_master_col.delete_one({"_id": extra_id})
                await products_col.delete_one({"_id": extra_id})

        # 5. Remove legacy duplicate entries where canonical pm_ exists
        await product_master_col.delete_many({"name": "USA H1B", "id": {"$ne": "pm_usa_h1b"}})
        await products_col.delete_many({"name": "USA H1B", "id": {"$ne": "pm_usa_h1b"}})

        # Remove legacy empty Australia duplicates where canonical pm_ exists
        await product_master_col.delete_many({
            "country": "Australia",
            "name": {"$in": ["Australia Skilled Migration Visa 189", "Australia PR Skilled Worker", "Australia PR Skilled Worker (Copy)"]},
            "id": {"$nin": ["pm_australia_189", "pm_australia_190", "pm_australia_491"]}
        })
        await products_col.delete_many({
            "country": "Australia",
            "name": {"$in": ["Australia Skilled Migration Visa 189", "Australia PR Skilled Worker", "Australia PR Skilled Worker (Copy)"]},
            "id": {"$nin": ["pm_australia_189", "pm_australia_190", "pm_australia_491"]}
        })

        # 6. Find duplicates by (country, name) for items with empty visa_subclass
        pipeline2 = [
            {"$match": {"status": {"$ne": "archived"}, "$or": [{"visa_subclass": ""}, {"visa_subclass": None}]}},
            {"$group": {
                "_id": {"country": "$country", "name": "$name"},
                "ids": {"$push": "$id"},
                "count": {"$sum": 1}
            }},
            {"$match": {"count": {"$gt": 1}}}
        ]
        dup_names = await product_master_col.aggregate(pipeline2).to_list(200)
        for grp in dup_names:
            ids = grp.get("ids", [])
            if len(ids) > 1:
                canonical_id = next((i for i in ids if str(i).startswith("pm_")), ids[0])
                for to_archive in ids:
                    if to_archive != canonical_id:
                        await product_master_col.update_one(
                            {"id": to_archive},
                            {"$set": {"status": "archived", "archived_at": datetime.now(timezone.utc)}}
                        )

        # 7. Auto-enrich active products that lack subclass code or summary
        active_unsubclassed = await product_master_col.find({
            "status": "active",
            "$or": [{"visa_subclass": ""}, {"visa_subclass": None}, {"summary": ""}, {"summary": None}]
        }).to_list(100)
        for prod in active_unsubclassed:
            m = find_canonical_match(prod.get("country", ""), prod.get("name", ""), prod.get("visa_subclass"))
            if m:
                await product_master_col.update_one(
                    {"id": prod["id"]},
                    {"$set": {
                        "visa_subclass": prod.get("visa_subclass") or m.get("visa_subclass", ""),
                        "summary": prod.get("summary") or m.get("summary", ""),
                        "description": prod.get("description") or m.get("description", ""),
                        "eligibility_criteria": prod.get("eligibility_criteria") or m.get("eligibility_criteria", {}),
                        "government_costs": prod.get("government_costs") or m.get("government_costs", {}),
                        "processing_timeline": prod.get("processing_timeline") or m.get("processing_timeline", {}),
                        "sales_playbook": prod.get("sales_playbook") or m.get("sales_playbook", {}),
                        "service_price": prod.get("service_price") or m.get("service_price", 125000),
                    }}
                )
    except Exception as e:
        logger.warning("Product Master deduplication error: %s", e)


async def _sync_existing_products():
    """Ensure canonical subclasses are seeded and existing products from products_col are available."""
    try:
        await _seed_standard_subclasses()
        await _deduplicate_products()

        existing_products = await products_col.find(
            {"status": {"$ne": "archived"}, "name": {"$not": {"$regex": r"\(copy\)", "$options": "i"}}},
            {"_id": 0}
        ).to_list(length=1000)

        for p in existing_products:
            pid = p.get("id")
            if not pid:
                continue
            exists = await product_master_col.find_one({"id": pid}, {"_id": 1})
            if not exists:
                doc = {
                    **p,
                    "summary": p.get("summary") or p.get("description", ""),
                    "description": p.get("description") or p.get("summary", ""),
                    "migrate_page_url": p.get("migrate_page_url") or "",
                    "official_urls": p.get("official_urls") or [],
                    "official_domains": p.get("official_domains") or [],
                    "eligibility_criteria": p.get("eligibility_criteria") or {
                        "mandatory": [],
                        "optional": [],
                        "points_based": {"is_points_tested": False, "minimum_points": 0, "scoring_factors": []}
                    },
                    "visa_conditions": p.get("visa_conditions") or [],
                    "government_costs": p.get("government_costs") or {
                        "currency": "INR",
                        "line_items": [],
                        "effective_date": None,
                        "source_link": ""
                    },
                    "processing_timeline": p.get("processing_timeline") or {
                        "standard_duration": "",
                        "stages": []
                    },
                    "sales_playbook": p.get("sales_playbook") or {
                        "target_client": "",
                        "pitch_points": [],
                        "key_benefits": []
                    },
                    "objections_rebuttals": p.get("objections_rebuttals") or [],
                    "faqs": p.get("faqs") or [],
                    "document_checklist_template": p.get("document_checklist_template") or [],
                    "version": int(p.get("version") or 1),
                }
                await product_master_col.insert_one(doc)
    except Exception as e:
        logger.warning("Product Master auto-sync error: %s", e)


@router.get("/summary-stats")
async def get_product_master_stats(current_user: dict = Depends(get_current_user)):
    """Summary counts for the Product Master dashboard cards."""
    await _sync_existing_products()
    total = await product_master_col.count_documents({"status": {"$ne": "archived"}})
    active = await product_master_col.count_documents({"status": "active"})
    draft = await product_master_col.count_documents({"status": "draft"})
    archived = await product_master_col.count_documents({"status": "archived"})
    verified = await product_master_col.count_documents({"last_verified_at": {"$ne": None}, "status": "active"})
    
    # Count unique countries
    countries = await product_master_col.distinct("country", {"status": {"$ne": "archived"}})
    unique_countries = len([c for c in countries if c])

    return {
        "total": total,
        "active": active,
        "draft": draft,
        "archived": archived,
        "verified": verified,
        "countries_count": unique_countries,
    }


@router.get("")
async def list_product_masters(
    country: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    include_archived: bool = False,
    current_user: dict = Depends(get_current_user),
):
    """List product masters with multi-dimensional filtering."""
    await _sync_existing_products()
    query: Dict[str, Any] = {}
    
    if not include_archived:
        if status:
            query["status"] = status
        else:
            query["status"] = {"$ne": "archived"}
    elif status:
        query["status"] = status

    if country and country != "all":
        query["country"] = country
    if category and category != "all":
        query["category"] = category
    if search:
        escaped = re.escape(search.strip())
        query["$or"] = [
            {"name": {"$regex": escaped, "$options": "i"}},
            {"country": {"$regex": escaped, "$options": "i"}},
            {"visa_type": {"$regex": escaped, "$options": "i"}},
            {"visa_subclass": {"$regex": escaped, "$options": "i"}},
        ]

    cursor = product_master_col.find(query, {"_id": 0}).sort("updated_at", -1)
    items = await cursor.to_list(length=300)

    # Format dates
    for item in items:
        for k in ("created_at", "updated_at", "last_verified_at", "next_review_at", "archived_at"):
            if isinstance(item.get(k), datetime):
                item[k] = item[k].isoformat()

    return {"items": items, "count": len(items)}


@router.get("/taxonomy")
async def get_product_master_taxonomy(current_user: dict = Depends(get_current_user)):
    """Returns unique countries, categories per country, and subclasses for structured hierarchical navigation."""
    await _sync_existing_products()
    items = await product_master_col.find(
        {"status": {"$ne": "archived"}},
        {
            "_id": 0, "id": 1, "name": 1, "country": 1, "country_code": 1, "flag": 1,
            "category": 1, "visa_subclass": 1, "visa_type": 1, "status": 1,
            "last_verified_at": 1, "summary": 1, "government_costs": 1,
            "authority_name": 1, "official_portal_url": 1
        }
    ).to_list(1000)

    category_meta = {
        "skilled_migration": {"name": "Skilled Migration / PR", "icon": "🌟"},
        "pr": {"name": "Skilled Migration / PR", "icon": "🌟"},
        "work": {"name": "Work Visas", "icon": "💼"},
        "student": {"name": "Student Visas", "icon": "🎓"},
        "visitor": {"name": "Visitor Visas", "icon": "✈️"},
        "family": {"name": "Family & Partner", "icon": "👨‍👩‍👧"},
        "partner": {"name": "Family & Partner", "icon": "👨‍👩‍👧"},
        "business": {"name": "Business & Investor", "icon": "🏢"},
        "investor": {"name": "Business & Investor", "icon": "🏢"},
    }

    country_iso_map = {
        "australia": "AU", "canada": "CA", "united kingdom": "GB", "uk": "GB",
        "germany": "DE", "united states": "US", "usa": "US", "new zealand": "NZ",
        "france": "FR", "italy": "IT", "spain": "ES", "switzerland": "CH",
        "netherlands": "NL", "uae": "AE", "singapore": "SG", "ireland": "IE",
    }

    country_flags = {
        "AU": "🇦🇺", "CA": "🇨🇦", "GB": "🇬🇧", "DE": "🇩🇪",
        "US": "🇺🇸", "NZ": "🇳🇿", "FR": "🇫🇷", "IT": "🇮🇹",
        "ES": "🇪🇸", "CH": "🇨🇭", "NL": "🇳🇱", "AE": "🇦🇪",
        "SG": "🇸🇬", "IE": "🇮🇪",
    }

    countries_map: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    country_info: Dict[str, Dict[str, Any]] = {}

    for it in items:
        raw_c = (it.get("country") or "Other").strip()
        c_lower = raw_c.lower()
        if c_lower in ("uk", "united kingdom", "great britain"):
            c = "United Kingdom"
        elif c_lower in ("usa", "united states", "united states of america", "us"):
            c = "United States"
        elif c_lower in ("nz", "new zealand"):
            c = "New Zealand"
        elif c_lower in ("uae", "united arab emirates"):
            c = "United Arab Emirates"
        else:
            c = raw_c.title()

        raw_cat = (it.get("category") or "skilled_migration").lower().strip()
        if raw_cat in ("pr", "skilled", "skilled_worker", "skilled_migration"):
            cat = "skilled_migration"
        elif raw_cat in ("work", "work_visa", "employment"):
            cat = "work"
        elif raw_cat in ("student", "education", "study"):
            cat = "student"
        elif raw_cat in ("visitor", "tourist", "visit"):
            cat = "visitor"
        elif raw_cat in ("family", "partner", "spouse"):
            cat = "family"
        elif raw_cat in ("business", "investor", "investment"):
            cat = "business"
        else:
            cat = raw_cat

        c_code = (it.get("country_code") or country_iso_map.get(c.lower(), "")).upper()
        flag = it.get("flag") or country_flags.get(c_code, "🌐")

        if c not in country_info:
            country_info[c] = {
                "id": c.lower().replace(" ", "_"),
                "name": c,
                "country_code": c_code,
                "flag": flag,
                "authority_name": it.get("authority_name") or "",
                "official_portal_url": it.get("official_portal_url") or "",
                "total_subclasses": 0,
                "categories": {}
            }

        if c not in countries_map:
            countries_map[c] = {}
        if cat not in countries_map[c]:
            countries_map[c][cat] = []

        # Fee display format
        gov_costs = it.get("government_costs") or {}
        curr = gov_costs.get("currency") or "INR"
        p_amt = gov_costs.get("primary_applicant")
        fee_str = f"{curr} {p_amt:,.0f}" if (p_amt and isinstance(p_amt, (int, float))) else ""

        subclass_summary = {
            "id": it.get("id"),
            "name": it.get("name"),
            "visa_subclass": it.get("visa_subclass") or "",
            "visa_type": it.get("visa_type") or "",
            "category": cat,
            "status": it.get("status") or "active",
            "is_verified": bool(it.get("last_verified_at")),
            "estimated_fees": fee_str,
            "summary": it.get("summary") or "",
        }

        countries_map[c][cat].append(subclass_summary)
        country_info[c]["total_subclasses"] += 1

        cat_meta = category_meta.get(cat, {"name": cat.replace("_", " ").title(), "icon": "📄"})
        if cat not in country_info[c]["categories"]:
            country_info[c]["categories"][cat] = {
                "id": cat,
                "name": cat_meta["name"],
                "icon": cat_meta["icon"],
                "count": 0,
                "subclasses": []
            }
        country_info[c]["categories"][cat]["count"] += 1
        country_info[c]["categories"][cat]["subclasses"].append(subclass_summary)

    # Sort priority countries first, then alphabetically
    priority_order = ["Australia", "Canada", "United Kingdom", "Germany", "United States", "New Zealand"]
    def _sort_key(name: str):
        if name in priority_order:
            return (0, priority_order.index(name))
        return (1, name)

    sorted_countries = [country_info[c] for c in sorted(country_info.keys(), key=_sort_key)]

    return {"countries": sorted_countries, "taxonomy": countries_map}


@router.get("/{product_id}")
async def get_single_product_master(
    product_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Retrieve complete Product Master record including all Module A sections and workflow steps."""
    item = await product_master_col.find_one({"id": product_id}, {"_id": 0})
    if not item:
        # Fallback to products_col if not yet in product_master_col
        item = await products_col.find_one({"id": product_id}, {"_id": 0})
        if not item:
            raise HTTPException(status_code=404, detail="Product Master record not found")

    # Attach workflow steps from workflow_steps_col
    steps = await workflow_steps_col.find({"product_id": product_id}, {"_id": 0}).sort("step_order", 1).to_list(100)
    for s in steps:
        if isinstance(s.get("created_at"), datetime):
            s["created_at"] = s["created_at"].isoformat()
    item["workflow_steps"] = steps

    # If document_checklist_template is empty or has fewer items, synthesize from workflow_steps
    if not item.get("document_checklist_template") and steps:
        synthesized_docs = []
        for s in steps:
            s_name = s.get("step_name") or s.get("name") or "Stage"
            for doc in s.get("required_documents") or []:
                d_name = doc.get("name") if isinstance(doc, dict) else str(doc)
                d_desc = doc.get("description") if isinstance(doc, dict) else ""
                d_mand = doc.get("mandatory", True) if isinstance(doc, dict) else True
                d_lock = doc.get("is_locked_until_paid", False) if isinstance(doc, dict) else False
                synthesized_docs.append({
                    "id": str(uuid.uuid4()),
                    "document_name": d_name,
                    "category": "Statutory Dossier",
                    "applicant_scope": "primary_applicant",
                    "is_mandatory": bool(d_mand),
                    "is_locked_until_paid": bool(d_lock),
                    "stage_name": s_name,
                    "step_order": s.get("step_order", 1),
                    "description": d_desc,
                })
        item["document_checklist_template"] = synthesized_docs

    # If processing_timeline is empty, synthesize from steps
    if not item.get("processing_timeline", {}).get("stages") and steps:
        item["processing_timeline"] = {
            "standard_duration": f"{len(steps) * 14} days",
            "stages": [
                {
                    "stage_order": s.get("step_order") or idx + 1,
                    "stage_name": s.get("step_name") or s.get("name") or f"Stage {idx + 1}",
                    "duration_days": s.get("duration_days") or 14,
                    "description": s.get("description") or "",
                    "government_fees": s.get("government_fees") or "",
                    "important_notes": s.get("important_notes") or "",
                }
                for idx, s in enumerate(steps)
            ]
        }

    for k in ("created_at", "updated_at", "last_verified_at", "next_review_at", "archived_at"):
        if isinstance(item.get(k), datetime):
            item[k] = item[k].isoformat()

    return item


@router.post("/ai-research")
async def ai_research_product_master(
    payload: ProductMasterAiResearchRequest,
    current_user: dict = Depends(get_current_user),
):
    """Admin-only: Trigger AI research on official government websites and migrate pages."""
    _require_admin(current_user)
    try:
        result = await research_product_with_ai(
            country=payload.country,
            visa_name=payload.visa_name,
            category=payload.category or "skilled_migration",
            visa_subclass=payload.visa_subclass or "",
            government_url=payload.government_url,
            migrate_page_url=payload.migrate_page_url,
            additional_context=payload.additional_context,
        )
        return result
    except Exception as e:
        logger.exception("Product Master AI research failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


async def _find_relevant_product(
    country: str,
    visa_name: str,
    visa_subclass: str,
    question: str,
    intent: Optional[CountryVisaQueryIntent] = None,
    product_id: Optional[str] = None,
):
    """Look up the most relevant Product Master record for grounding sales AI queries across all countries.
    
    Guarantees:
    - If product_id is provided, directly returns that verified Product Master record as the Single Source of Truth.
    - Never returns USA EB-2 NIW when query is for Australia PR or other countries.
    - Uses query-level country and subclass intent first.
    """
    if product_id and str(product_id).strip():
        pid = str(product_id).strip()
        doc = await product_master_col.find_one({"id": pid, "is_archived": {"$ne": True}})
        if doc:
            return doc
        doc = await products_col.find_one({"id": pid, "is_archived": {"$ne": True}})
        if doc:
            return doc

    if not intent:
        intent = detect_country_and_visa_in_query(question, fallback_country=country, fallback_subclass=visa_subclass)

    target_country = intent.detected_country
    target_subclass = intent.detected_subclass or ""
    q_lower = (question or "").lower()

    # Step 0: Check if an occupation code is detected
    det = detect_occupation_in_query(question, target_country)
    if det and det.is_mismatch:
        target_country = det.country

    # Step 1: Query Product Master for target_country
    if target_country == "Australia":
        # Check specific subclass
        if "189" in target_subclass or re.search(r"\b189\b", q_lower):
            doc = await product_master_col.find_one({"country": "Australia", "visa_subclass": {"$regex": "^189"}, "is_archived": {"$ne": True}})
            if doc: return doc
        if "190" in target_subclass or re.search(r"\b190\b", q_lower):
            doc = await product_master_col.find_one({"country": "Australia", "visa_subclass": {"$regex": "^190"}, "is_archived": {"$ne": True}})
            if doc: return doc
        if "491" in target_subclass or re.search(r"\b491\b", q_lower):
            doc = await product_master_col.find_one({"country": "Australia", "visa_subclass": {"$regex": "^491"}, "is_archived": {"$ne": True}})
            if doc: return doc
        for sc in ["482", "500", "600", "820", "801", "186"]:
            if sc in target_subclass or re.search(rf"\b{sc}\b", q_lower):
                doc = await product_master_col.find_one({"country": "Australia", "visa_subclass": {"$regex": rf"^{sc}"}, "is_archived": {"$ne": True}})
                if doc: return doc
        # Default for Australia PR: Subclass 189
        doc = await product_master_col.find_one({"country": "Australia", "visa_subclass": {"$regex": "^189"}, "is_archived": {"$ne": True}})
        if doc: return doc
        doc = await product_master_col.find_one({"country": "Australia", "is_archived": {"$ne": True}})
        if doc: return doc

    elif target_country == "Canada":
        if "fsw" in target_subclass.lower() or any(k in q_lower for k in ["fsw", "express entry", "crs"]):
            doc = await product_master_col.find_one({"country": "Canada", "visa_subclass": "FSW", "is_archived": {"$ne": True}})
            if doc: return doc
        if "pnp" in target_subclass.lower() or any(k in q_lower for k in ["pnp", "oinp", "bcpnp", "sinp"]):
            doc = await product_master_col.find_one({"country": "Canada", "visa_subclass": "PNP", "is_archived": {"$ne": True}})
            if doc: return doc
        if any(k in q_lower for k in ["study permit", "canada student", "pgwp"]):
            doc = await product_master_col.find_one({"country": "Canada", "visa_subclass": "Study Permit", "is_archived": {"$ne": True}})
            if doc: return doc
        if any(k in q_lower for k in ["super visa", "visitor"]):
            doc = await product_master_col.find_one({"country": "Canada", "visa_subclass": "Visitor Visa", "is_archived": {"$ne": True}})
            if doc: return doc
        doc = await product_master_col.find_one({"country": "Canada", "is_archived": {"$ne": True}})
        if doc: return doc

    elif target_country == "United States":
        if any(k in q_lower for k in ["h-1b", "h1b", "specialty occupation"]):
            doc = await product_master_col.find_one({"country": "United States", "visa_subclass": "H-1B", "is_archived": {"$ne": True}})
            if doc: return doc
        if any(k in q_lower for k in ["l-1", "l1", "intracompany"]):
            doc = await product_master_col.find_one({"country": "United States", "visa_subclass": "L-1", "is_archived": {"$ne": True}})
            if doc: return doc
        if any(k in q_lower for k in ["eb-1", "eb1"]):
            doc = await product_master_col.find_one({"country": "United States", "visa_subclass": "EB-1", "is_archived": {"$ne": True}})
            if doc: return doc
        if any(k in q_lower for k in ["eb-2", "eb2", "niw", "national interest waiver"]):
            doc = await product_master_col.find_one({"country": "United States", "visa_subclass": "EB-2", "is_archived": {"$ne": True}})
            if doc: return doc
        if any(k in q_lower for k in ["f-1", "f1", "opt", "cpt"]):
            doc = await product_master_col.find_one({"country": "United States", "visa_subclass": "F-1", "is_archived": {"$ne": True}})
            if doc: return doc
        if any(k in q_lower for k in ["b-1", "b-2", "b1", "b2", "visitor"]):
            doc = await product_master_col.find_one({"country": "United States", "visa_subclass": "B-1/B-2", "is_archived": {"$ne": True}})
            if doc: return doc
        doc = await product_master_col.find_one({"country": "United States", "is_archived": {"$ne": True}})
        if doc: return doc

    elif target_country == "Germany":
        if any(k in q_lower for k in ["chancenkarte", "opportunity", "chancen"]):
            doc = await product_master_col.find_one({"country": "Germany", "visa_subclass": "Chancenkarte", "is_archived": {"$ne": True}})
            if doc: return doc
        if any(k in q_lower for k in ["blue card", "blaue karte"]):
            doc = await product_master_col.find_one({"country": "Germany", "visa_subclass": "Blue Card", "is_archived": {"$ne": True}})
            if doc: return doc
        doc = await product_master_col.find_one({"country": "Germany", "is_archived": {"$ne": True}})
        if doc: return doc

    elif target_country == "United Kingdom":
        doc = await product_master_col.find_one({"country": "United Kingdom", "is_archived": {"$ne": True}})
        if doc: return doc

    elif target_country == "New Zealand":
        doc = await product_master_col.find_one({"country": "New Zealand", "is_archived": {"$ne": True}})
        if doc: return doc

    # Generic lookup for any other country
    norm_c = normalize_country(target_country)
    q_filter = {"country": {"$regex": f"^{re.escape(norm_c)}$", "$options": "i"}, "is_archived": {"$ne": True}}
    if target_subclass:
        q_filter["visa_subclass"] = {"$regex": re.escape(target_subclass), "$options": "i"}
        doc = await product_master_col.find_one(q_filter)
        if doc: return doc
    doc = await product_master_col.find_one({"country": {"$regex": f"^{re.escape(norm_c)}$", "$options": "i"}, "is_archived": {"$ne": True}})
    if doc: return doc

    # Fallback to verified Country Regulatory Authorities catalog (supports 45+ countries)
    auth_data = get_country_authority_info(norm_c)
    if auth_data:
        streams = auth_data.get("visa_streams", [])
        matched_stream = streams[0] if streams else None
        if matched_stream:
            return {
                "id": matched_stream.get("id"),
                "name": matched_stream.get("name"),
                "country": auth_data.get("country_name", norm_c),
                "visa_subclass": target_subclass or matched_stream.get("id", "").replace("subclass_", "").upper(),
                "category": matched_stream.get("category", "skilled_migration"),
                "authority_name": auth_data.get("authority_name"),
                "migrate_page_url": f"https://leamss.com/migrate/{norm_c.lower().replace(' ', '-')}",
                "official_urls": [matched_stream.get("official_url") or auth_data.get("official_portal_url")],
                "government_costs": {"primary_applicant": matched_stream.get("estimated_fees", "")},
                "service_price": 125000,
                "summary": matched_stream.get("description", ""),
                "is_synthetic": True,
            }

    # Absolute fallback: Return Australia 189 if question implies Australia, otherwise first active doc
    if target_country == "Australia":
        return await product_master_col.find_one({"country": "Australia", "is_archived": {"$ne": True}})
    return await product_master_col.find_one({"is_archived": {"$ne": True}})


def _synthesize_sales_response(
    doc: Optional[dict],
    payload: SalesAiQueryRequest,
    question: str,
    auth_info: Optional[dict] = None,
    profile: Optional[Any] = None,
    intent: Optional[CountryVisaQueryIntent] = None,
    det: Optional[Any] = None,
) -> str:
    """Synthesizes a short, punchy live-call statutory sales advisory from Product Master data."""
    country = (doc.get("country") if doc else (intent.detected_country if intent else payload.country)) or "Australia"
    c_norm = normalize_country(country)
    if not auth_info:
        auth_info = get_country_authority_info(c_norm) or {}
    subclass = (doc.get("visa_subclass") if doc else (intent.detected_subclass if intent else payload.visa_subclass)) or "189"
    v_name = (doc.get("name") if doc else payload.visa_name) or f"{c_norm} Skilled Visa ({subclass})"
    auth = (doc.get("authority_name") if doc else None) or (auth_info.get("authority_name") if auth_info else None) or "Statutory Immigration Authority"
    gov_portal = (auth_info.get("official_portal_url") if auth_info else None) or "https://immi.homeaffairs.gov.au"
    c_slug = c_norm.lower().replace(" ", "-")
    migrate_url = (doc.get("migrate_page_url") if doc else None) or f"https://leamss.com/migrate/{c_slug}"
    atlas_url = f"https://leamss.com/atlas/{profile.country_code.lower()}/{profile.code}" if (profile and getattr(profile, "code", None) and getattr(profile, "country_code", None)) else f"https://leamss.com/atlas"
    
    service_price = (doc.get("service_price") if doc else None) or (doc.get("base_fee") if doc else None) or 125000
    playbook = doc.get("sales_playbook", {}) if doc else {}
    elevator = playbook.get("elevator_pitch") or f"Direct settlement and work authorization in {c_norm} under official {subclass} criteria."
    elig = doc.get("eligibility_criteria", {}) if doc else {}
    pts_info = elig.get("points_based", {})
    min_pts = pts_info.get("minimum_points", 65) if pts_info.get("is_points_tested") else "Statutory qualification & points criteria"
    fees = get_statutory_fees_and_commercials(c_norm, subclass)

    objs = doc.get("objections_rebuttals") or [] if doc else []
    first_obj = objs[0] if objs else {}
    obj_q = first_obj.get("objection") or "Can you guarantee that I will get visa or PR approval?"
    obj_a = first_obj.get("rebuttal") or (
        "Under official immigration law, all visa decisions remain the statutory prerogative of government visa officers. "
        "No migration consultant can guarantee visa issuance. What LEAMSS guarantees is rigorous institutional compliance, "
        "ensuring your documentation, points optimization, and skills assessment petition satisfy 100% of official statutory benchmarks."
    )

    mismatch_header = ""
    if det and det.is_mismatch and det.mismatch_warning:
        mismatch_header = (
            f"> [!WARNING]\n"
            f"> **CRITICAL SYSTEM CLARIFICATION:** {det.mismatch_warning}\n"
        )
        if det.crosswalk_code and det.crosswalk_title:
            mismatch_header += (
                f"> \n"
                f"> **Equivalent Occupation in {det.selected_country}:** `{det.crosswalk_code}` — **{det.crosswalk_title}** "
                f"(Assessing Body: *{det.crosswalk_authority or 'Designated Authority'}*).\n\n"
            )

    topic = intent.query_topic if intent else "general"

    if intent and intent.is_unclear:
        pitch = intent.clarification_question or "Which destination country are you targeting — Australia (Subclass 189/190) or Canada (Express Entry)?"
        section_2 = (
            f"### ⚡ 2. Direct Quick Answer: Destination Clarification & Comparison (Small Sentences)\n"
            f"- **Australia General Skilled Migration (Subclass 189/190):** Direct permanent residency without a job offer via SkillSelect points grid (pass mark 65).\n"
            f"- **Canada Express Entry (Federal Skilled Worker):** Direct permanent residency without a job offer via Comprehensive Ranking System (CRS).\n"
            f"- **Consultant Action:** Clarify the preferred destination with the client to evaluate exact points benchmarks and eligibility."
        )
    elif topic == "benefits":
        if c_norm == "Australia":
            pitch = (
                "Australia Permanent Residency provides you and your family with world-class benefits. "
                "You receive unconditional rights to live and work anywhere in Australia, access to free universal healthcare under Medicare, "
                "free public schooling for your children, and a direct pathway to Australian citizenship and passport after 4 years."
            )
        elif c_norm == "Canada":
            pitch = (
                "Canada Permanent Residency grants you and your family permanent settlement and work rights across Canada, "
                "free universal healthcare through provincial healthcare plans, free public education for your children, "
                "and eligibility to apply for Canadian citizenship after 3 years."
            )
        else:
            pitch = (
                f"{c_norm} permanent residency grants you unconditional work rights, state-funded healthcare, "
                f"social security coverage, and a direct pathway to sovereign citizenship for you and your family."
            )
        section_2 = (
            f"### ⚡ 2. Direct Quick Answer: Key {c_norm} Permanent Residency Benefits (Small Sentences)\n"
            f"- **Unconditional Work & Settlement Rights:** Live, work, and establish a business anywhere in {c_norm} with full legal protections.\n"
            f"- **Universal Healthcare Protection:** Immediate access to subsidized medical and hospital care ({'Medicare' if c_norm == 'Australia' else 'provincial healthcare' if c_norm == 'Canada' else 'national healthcare'}).\n"
            f"- **Pathway to Sovereign Citizenship:** Eligible to apply for full {c_norm} citizenship and passport ({'after 4 years of lawful residence' if c_norm == 'Australia' else 'after 3 years of physical presence' if c_norm == 'Canada' else 'upon meeting statutory residence'}).\n"
            f"- **Family Sponsorship Privileges:** Sponsor spouse, dependent children, and eligible relatives for permanent status.\n"
            f"- **Education Entitlements:** Free public primary and secondary schooling for your children with domestic university fee status."
        )
    elif topic == "family":
        if c_norm == "Australia":
            pitch = (
                "Yes, you can include your eligible spouse or de facto partner and dependent children in your Australia Subclass 189 application. "
                "Family members receive Permanent Residency only if they are included in the application and their visas are approved. "
                "Dependent children must be under 18, or aged 18 to 23 and financially dependent. "
                "Your spouse must show genuine relationship evidence, and all family members must meet health and character requirements. "
                "Additional government visa charges apply for secondary applicants."
            )
            section_2 = (
                f"### ⚡ 2. Direct Quick Answer: Family Inclusion Rules for Australia Subclass 189 (Small Sentences)\n"
                f"- **Eligible Family Members:** You can include your legally married spouse or de facto partner and dependent children in your Subclass 189 application.\n"
                f"- **Permanent Residency Approval Condition:** Family members receive Permanent Residency only if they are included in the application and their visa applications are officially approved by the Department of Home Affairs.\n"
                f"- **Dependent Children Age & Dependency:** Children under 18 qualify automatically. Children aged 18 to 23 must be financially dependent (full-time students, unmarried). Children aged 23+ qualify only if incapacitated due to physical or mental disability.\n"
                f"- **Spouse Genuine Relationship Evidence:** Evidence of a genuine and continuing relationship is mandatory (marriage certificate or minimum 12 months de facto cohabitation).\n"
                f"- **Mandatory Health & Character Criteria:** All included secondary applicants must pass official Australian health examinations and police character clearances.\n"
                f"- **Statutory Government Charges:** Additional Department of Home Affairs visa application charges apply for secondary applicants (no fee breakdown provided unless requested)."
            )
        elif c_norm == "Canada":
            pitch = (
                "Yes, you can include your spouse or common-law partner and dependent children in your Canada Permanent Residency application. "
                "Family members receive PR only if they are included in your petition and approved by IRCC. "
                "Dependent children must be under 22 years of age and unmarried. "
                "Your spouse must provide genuine relationship proof, and all family members must complete mandatory medical and police clearances. "
                "Additional government processing fees apply for accompanying family members."
            )
            section_2 = (
                f"### ⚡ 2. Direct Quick Answer: Family Inclusion Rules for Canada Permanent Residency (Small Sentences)\n"
                f"- **Eligible Family Members:** Accompanying spouse or common-law partner and dependent children can be included in your Express Entry application.\n"
                f"- **Permanent Residency Approval Condition:** Family members receive PR only if included in the application and approved by IRCC.\n"
                f"- **Dependent Children Age & Dependency:** Dependent children must be under 22 years of age and unmarried (children 22+ qualify only if dependent due to physical or mental condition).\n"
                f"- **Spouse Genuine Relationship:** Proof of genuine relationship required (marriage certificate or 12 months continuous cohabitation).\n"
                f"- **Mandatory Health & Character Criteria:** All accompanying family members must pass IRCC immigration medical exams and police clearances.\n"
                f"- **Statutory Government Charges:** Additional IRCC processing fees and Right of Permanent Residence fees apply for accompanying dependents."
            )
        else:
            pitch = (
                f"Yes, you can include your eligible spouse and dependent children in your {c_norm} {v_name} application. "
                f"Family members receive Permanent Residency only if they are included in the application and approved by {auth}. "
                f"Dependent children must meet statutory age and dependency requirements, your spouse must show genuine relationship evidence, "
                f"and all applicants must satisfy mandatory health and character clearances. Additional government charges apply for secondary applicants."
            )
            section_2 = (
                f"### ⚡ 2. Direct Quick Answer: Family Inclusion Rules for {c_norm} {v_name} (Small Sentences)\n"
                f"- **Eligible Family Members:** Spouse and dependent children can be included in the primary application.\n"
                f"- **Permanent Residency Approval Condition:** Family members receive permanent status only if included and approved by {auth}.\n"
                f"- **Dependent Children Age Criteria:** Dependent children must satisfy national statutory age limits and dependency criteria.\n"
                f"- **Spouse Genuine Relationship Evidence:** Proof of valid legal marriage or qualifying cohabitation is required.\n"
                f"- **Mandatory Health & Character Clearances:** All included family members must meet sovereign health and security standards.\n"
                f"- **Statutory Government Charges:** Additional visa application charges apply for secondary applicants."
            )
    elif topic == "travel":
        pitch = (
            f"You do not need to travel abroad or visit {c_norm} to apply for your {v_name}. "
            f"Under official {auth} regulations, General Skilled Migration is a 100% offshore process completed entirely from your home country. "
            f"You only travel to {c_norm} after your permanent residency visa is approved to make your initial entry."
        )
        section_2 = (
            f"### ⚡ 2. Direct Quick Answer: Travel & Offshore Application Rules (Small Sentences)\n"
            f"- **100% Offshore Application:** You complete the entire process from your home country without international travel.\n"
            f"- **Zero Foreign Travel Prerequisite:** No visit visa, job hunting trip, or physical presence in {c_norm} is required to apply or be granted PR.\n"
            f"- **Home Country Assessments:** Educational verification, English exams (PTE/IELTS), and government visa lodgement are handled online from home.\n"
            f"- **Initial Entry Requirement:** You only travel to {c_norm} after your permanent resident visa is officially granted by {auth} before the initial entry date."
        )
    elif topic == "eligibility":
        pitch = (
            f"To qualify for {c_norm} {v_name}, you must meet statutory benchmarks established by {auth}. "
            f"This includes age under 45, formal qualification equivalence, positive skills assessment, and a minimum pass mark score. "
            f"Direct skilled PR does not require an employer job offer."
        )
        occ_line = f"- **Occupation Standard:** {profile.title} ({profile.code}) assessed by {profile.assessing_authority}.\n" if profile else ""
        section_2 = (
            f"### ⚡ 2. Direct Quick Answer: Core Eligibility Criteria & Points Benchmarks (Small Sentences)\n"
            f"{occ_line}"
            f"- **Age Criterion:** Must be under 45 years of age at the time of official invitation.\n"
            f"- **Skills & Credential Assessment:** Positive skills assessment required in an eligible occupation on the official skilled list.\n"
            f"- **Language Benchmark:** Minimum Competent English proficiency (e.g. IELTS 6.0 in each band or PTE Academic 50+).\n"
            f"- **Points Test Benchmark:** Pass mark of at least 65 points on the statutory points grid (calculated on age, education, experience, English).\n"
            f"- **No Job Offer Required:** Independent skilled migration allows you to secure PR without an employer job offer or sponsor."
        )
    elif topic == "process":
        pitch = (
            f"The application procedure for {c_norm} {v_name} follows a structured 4-stage statutory roadmap with {auth}. "
            f"It progresses from initial skills assessment through EOI registration to formal visa lodgement, typically taking 6 to 12 months."
        )
        section_2 = (
            f"### ⚡ 2. Direct Quick Answer: Application Steps & Processing Timeline (Small Sentences)\n"
            f"- **Stage 1 (Skills Assessment):** Formal evaluation of educational credentials and skilled work experience (approx 2 to 3 months).\n"
            f"- **Stage 2 (Language & EOI):** Securing benchmark test scores and submitting Expression of Interest in the government pool.\n"
            f"- **Stage 3 (Government Invitation):** Receiving official Invitation to Apply (ITA) or State Nomination from {auth}.\n"
            f"- **Stage 4 (Visa Lodgement):** Submitting final police clearances, medicals, and documentation for visa grant (approx 6 to 9 months).\n"
            f"- **Estimated Timeline:** Typically spans 6 to 12 months depending on invitation frequency and government processing queues."
        )
    elif topic == "fees":
        q_lower = (question or "").lower()
        p_base = float(doc.get("service_price") or doc.get("base_fee") or service_price) if doc else float(service_price)
        p_gst = round(p_base * 0.18)
        p_total = round(p_base + p_gst)
        rp = (doc.get("refund_policy") or {}) if doc else {}
        pkgs = (doc.get("packages") or []) if doc else []
        ms = ((doc.get("commercials") or {}).get("milestones") or []) if doc else []
        allocs = (doc.get("cost_allocations") or []) if doc else []

        if any(k in q_lower for k in ["refund", "money back", "protection guarantee"]):
            if rp.get("enabled") is False:
                pitch = f"For {c_norm} {v_name}, refund terms are subject to standard administrative review and statutory conditions."
                section_2 = (
                    f"### ⚡ 2. Direct Quick Answer: Refund Policy Status for {v_name} (Small Sentences)\n"
                    f"- **Policy Status:** Discretionary administrative review by Admin.\n"
                    f"- **Statutory Government Fees:** Non-refundable once paid to {auth}.\n"
                    f"- **Professional Retainer:** Evaluated on operational milestones delivered."
                )
            else:
                rp_model = rp.get("policy_type", "protection").title()
                rp_pct = rp.get("refundable_service_fee_pct", 100)
                rp_window = rp.get("claim_window_days", 30)
                rp_sla = rp.get("payout_time_days", 14)
                rp_gst = "Credit note issued for 100% GST" if rp.get("gst_treatment") == "credit_note" else "GST retained"
                triggers = []
                if rp.get("negative_skills_assessment_guarantee"): triggers.append("Negative Skills Assessment")
                if rp.get("visa_refusal_guarantee"): triggers.append("Official Visa Refusal")
                if rp.get("voluntary_withdrawal_milestones"): triggers.append("Voluntary Withdrawal Pre-Lodgement")
                for ct in rp.get("custom_guaranteed_triggers") or []:
                    triggers.append(ct.get("trigger_name", "Regional Nomination Guarantee"))
                trig_str = ", ".join(triggers) if triggers else "Institutional statutory compliance"
                pitch = (
                    f"LEAMSS provides an official {rp_model} Policy for {c_norm} {v_name}. "
                    f"You are protected with up to {rp_pct}% service fee refund if qualifying delivery criteria are not met. "
                    f"Claims have a {rp_window}-day window with a {rp_sla}-day payout SLA. "
                    f"Statutory government visa charges paid to {auth} remain non-refundable."
                )
                section_2 = (
                    f"### ⚡ 2. Direct Quick Answer: Verified Refund Safeguards for {v_name} (Small Sentences)\n"
                    f"- **Guarantee Model:** LEAMSS {rp_model} Guarantee ({rp_pct}% Service Fee Refundable).\n"
                    f"- **Guaranteed Triggers:** {trig_str}.\n"
                    f"- **Statutory Government Fees:** Non-refundable (paid directly to {auth}).\n"
                    f"- **GST Handling:** {rp_gst}.\n"
                    f"- **Claim & Payout Timelines:** {rp_window}-day claim submission window with {rp_sla}-day payout SLA.\n"
                    f"- **Mandatory Qualifying Conditions:** Client must supply 100% genuine documentation and respond to case manager queries within 7 days."
                )
        elif any(k in q_lower for k in ["package", "packages", "tier", "tiers", "smart", "premium"]) and pkgs:
            pkg_lines = []
            for p in pkgs:
                if p.get("is_active") is not False:
                    p_price = p.get("price") or p_base
                    p_desc = p.get("description") or "Core visa application guidance & assessment filing"
                    pkg_lines.append(f"- **{p.get('name', 'Package')}:** ₹{int(p_price):,} (+ 18% GST: ₹{round(p_price*0.18):,}) — {p_desc}.")
            pitch = (
                f"For {c_norm} {v_name}, LEAMSS offers structured client portal packages tailored to your requirements. "
                f"Our options include Standard, Smart, and Premium tiers with transparent pricing and milestone installments."
            )
            section_2 = (
                f"### ⚡ 2. Direct Quick Answer: Client Portal Package Tiers for {v_name} (Small Sentences)\n"
                + "\n".join(pkg_lines)
            )
        elif any(k in q_lower for k in ["milestone", "milestones", "tranche", "tranches", "installment"]) and ms:
            ms_lines = []
            for m in ms:
                m_pct = m.get("percentage") or 0
                m_amt = m.get("amount") or round(p_base * (m_pct / 100))
                m_trig = f" — Trigger: {m.get('trigger')}" if m.get("trigger") else ""
                ms_lines.append(f"- **{m.get('name', 'Milestone')}:** {m_pct}% (₹{int(m_amt):,}){m_trig}.")
            pitch = (
                f"LEAMSS professional consulting for {v_name} is structured in operational milestone tranches. "
                f"You only pay as each phase of your application is successfully completed."
            )
            section_2 = (
                f"### ⚡ 2. Direct Quick Answer: Retainer Milestone Payment Schedule (Small Sentences)\n"
                + "\n".join(ms_lines)
            )
        elif any(k in q_lower for k in ["commission", "commissions", "split", "splits", "incentive", "incentives"]) and allocs:
            alloc_lines = []
            for a in allocs:
                a_label = a.get("label") or a.get("vendor_category") or "Partner Split"
                a_val = a.get("rate") if a.get("payment_type") == "percentage" else a.get("amount")
                a_type = "% of Price" if a.get("payment_type") == "percentage" else "Flat ₹"
                alloc_lines.append(f"- **{a_label}:** {a_val} {a_type}.")
            pitch = f"Salesperson commissions and partner splits for {v_name} are configured directly in the verified Product Master."
            section_2 = (
                f"### ⚡ 2. Direct Quick Answer: Commissions & Partner Splits for {v_name} (Small Sentences)\n"
                + "\n".join(alloc_lines)
            )
        else:
            pitch = (
                f"For {c_norm} {v_name}, government visa charges are paid in transparent stages directly to {auth}. "
                f"The primary applicant government visa charge is {fees['gov_fee_foreign']} (approx {fees['gov_fee_inr_approx']}). "
                f"LEAMSS professional retainer is ₹{int(p_base):,} plus 18% statutory GST (Total: ₹{int(p_total):,}), structured in milestone tranches."
            )
            ms_note = f"{len(ms)}-Tranche Milestone Schedule" if ms else fees['leamss_milestones']
            pkg_count = len([p for p in pkgs if p.get('is_active') is not False]) if pkgs else 3
            section_2 = (
                f"### ⚡ 2. Direct Quick Answer: Statutory Government Fees & Commercial Investment (Small Sentences)\n"
                f"- **Official Government Visa Fee:** {fees['gov_fee_foreign']} (~{fees['gov_fee_inr_approx']}) paid directly to {auth}.\n"
                f"- **Secondary Applicant Charges:** {fees['gov_fee_breakdown']}.\n"
                f"- **LEAMSS Professional Retainer:** ₹{int(p_base):,} (+ 18% statutory GST = ₹{int(p_total):,}).\n"
                f"- **Payment Structure:** {ms_note} across verifiable delivery stages.\n"
                f"- **Available Service Tiers:** {pkg_count} active package tiers (Standard, Smart, Premium).\n"
                f"- **Required Settlement Reserve:** {fees['settlement_funds']}."
            )
    elif topic == "objection":
        pitch = (
            f"Under official immigration law, all visa decisions remain the statutory prerogative of government visa officers. "
            f"No legitimate firm can promise or guarantee a visa. What LEAMSS guarantees is 100% institutional compliance, ensuring "
            f"your paperwork and petition satisfy all legal requirements without procedural errors."
        )
        section_2 = (
            f"### ⚡ 2. Direct Quick Answer: Professional Objection Handling & Institutional Guarantee (Small Sentences)\n"
            f"- **Client Objection:** \"{obj_q}\"\n"
            f"- **Consultant Rebuttal:** \"{obj_a}\"\n"
            f"- **Institutional Risk Mitigation:** Rigorous pre-assessment audit of credentials, employment references, and tax records to prevent procedural refusal."
        )
    else:  # general
        pitch = (
            f"Hello, based on official statutory regulations from {auth}, the {v_name} represents your primary pathway. "
            f"{elevator} Our legal team prepares your petition with 100% institutional compliance to ensure a smooth process."
        )
        occ_line = f"- **Target Occupation:** {profile.title} ({profile.code}) under {profile.assessing_authority}.\n" if profile else ""
        section_2 = (
            f"### ⚡ 2. Direct Quick Answer & Key Facts (Small Sentences)\n"
            f"- **Direct Solution:** {v_name} under official {auth} regulatory guidelines.\n"
            f"{occ_line}"
            f"- **Core Answer:** Statutory criteria require verifiable educational equivalence, continuous skilled employment, and approved credential evaluation.\n"
            f"- **Pass Mark Benchmark:** {min_pts}.\n"
            f"- **Recommended Action:** Conduct formal credential and points evaluation to confirm eligibility."
        )

    return (
        f"{mismatch_header}"
        f"### 💬 1. Speaking Script for Live Call (Read directly to client)\n"
        f"> *\"{pitch}\"*\n\n"
        f"{section_2}\n\n"
        f"> **LEAMSS Statutory Disclaimer:** Immigration policies, points thresholds, and government visa charges are subject to official gazette notifications by sovereign immigration authorities. LEAMSS operates strictly under licensed consulting compliance and never guarantees visa approval."
    )


def _clean_ai_response(text: str) -> str:
    """Strips raw Perplexity web search sources dumps and link lists from response text."""
    if not text:
        return ""
    # Strip Perplexity trailing sources list (_Sources (Perplexity web search):_ ...)
    cleaned = re.sub(r"\n*[_*]*Sources(?:\s*\(.*?\))?:?[_*]*\s*\n+(?:[-*]\s*https?://\S+\n*)+", "", text, flags=re.IGNORECASE)
    # Strip any trailing list of raw URLs or standalone link lines
    cleaned = re.sub(r"\n+(?:[-*]\s*https?://\S+\s*)+$", "", cleaned)
    # Strip Section 6 official sources list from body text if model generated it
    cleaned = re.sub(r"\n*### 🔗\s*(?:6\.)?.*?(?=\n*###|\n*>|\Z)", "", cleaned, flags=re.DOTALL)
    return cleaned.strip()


@router.post("/sales-ai-query")
async def sales_ai_query(
    payload: SalesAiQueryRequest,
    current_user: dict = Depends(get_current_user),
):
    """Authenticated staff (Sales, Case Managers, Admin): Ask AI questions & client scenarios for sales pitch."""
    q = (payload.client_scenario_or_question or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="Question or client scenario is required")

    # 1. Run deterministic country, visa subclass, and query intent detector
    intent = detect_country_and_visa_in_query(q, fallback_country=payload.country, fallback_subclass=payload.visa_subclass)
    det = detect_occupation_in_query(q, intent.detected_country)
    profile = get_full_occupation_profile(det) if det else None

    # 2. Look up matching Product Master record for Ground Truth context across all countries
    product_doc = await _find_relevant_product(
        country=intent.detected_country,
        visa_name=payload.visa_name or "",
        visa_subclass=intent.detected_subclass or "",
        question=q,
        intent=intent,
        product_id=payload.product_id,
    )

    matched_country = intent.detected_country
    if det and det.is_mismatch:
        matched_country = det.country
    elif product_doc and product_doc.get("country"):
        matched_country = product_doc.get("country")

    matched_visa = (
        product_doc.get("name") if product_doc else (
            f"{matched_country} Skilled Visa ({intent.detected_subclass})" if intent.detected_subclass else (payload.visa_name or f"{matched_country} Skilled Visa")
        )
    )
    matched_subclass = product_doc.get("visa_subclass") if product_doc else (intent.detected_subclass or "")

    # Retrieve official country regulatory authority specifications & workflow references
    auth_data = get_country_authority_info(matched_country) or {}
    c_key = resolve_country_key(matched_country)
    auth_name = (
        (product_doc.get("authority_name") if product_doc else None)
        or (profile.assessing_authority if profile else None)
        or auth_data.get("authority_name")
        or f"{matched_country} Immigration Authority"
    )
    gov_url = (
        (auth_data.get("official_portal_url") if auth_data else None)
        or (profile.official_source_url if profile else None)
        or (product_doc.get("official_urls", [None])[0] if product_doc else None)
        or "https://immi.homeaffairs.gov.au"
    )
    vfs_url = (auth_data.get("vfs_url") if auth_data else None) or "https://visa.vfsglobal.com"
    c_slug = matched_country.lower().replace(" ", "-")
    migrate_url = (
        (product_doc.get("migrate_page_url") if product_doc else None)
        or f"https://leamss.com/migrate/{c_slug}"
    )
    atlas_url = (
        f"https://leamss.com/atlas/{profile.country_code.lower()}/{profile.code}"
        if (profile and getattr(profile, "code", None) and getattr(profile, "country_code", None))
        else f"https://leamss.com/atlas"
    )
    fees = get_statutory_fees_and_commercials(matched_country, matched_subclass)
    service_price = (
        (product_doc.get("service_price") if product_doc else None)
        or (product_doc.get("base_fee") if product_doc else None)
        or 125000
    )

    c_ref = COUNTRY_REFERENCES.get(c_key) or COUNTRY_REFERENCES.get(matched_country.lower()) or {}
    workflow_notes = ""
    if isinstance(c_ref, dict):
        workflow_notes = "\n".join([f"- {k.upper()} Stream: {v}" for k, v in c_ref.items()][:4])
    elif isinstance(c_ref, str):
        workflow_notes = c_ref

    doc_context = ""
    if product_doc:
        p_base = float(product_doc.get("service_price") or product_doc.get("base_fee") or service_price)
        p_gst = round(p_base * 0.18)
        p_total = round(p_base + p_gst)

        # Packages
        pkgs_list = product_doc.get("packages") or []
        pkgs_summary = []
        for p in pkgs_list:
            if p.get("is_active") is not False:
                p_p = p.get("price") or p_base
                pkgs_summary.append(f"  * {p.get('name')}: INR {int(p_p):,} (+ 18% GST: INR {round(p_p*0.18):,}) — {p.get('description', '')}")
        pkgs_text = "\n".join(pkgs_summary) if pkgs_summary else f"  * Standard Retainer: INR {int(p_base):,}"

        # Milestones
        ms_list = (product_doc.get("commercials") or {}).get("milestones") or []
        ms_summary = []
        for m in ms_list:
            ms_pct = m.get("percentage") or 0
            ms_amt = m.get("amount") or round(p_base * (ms_pct / 100))
            ms_trig = f" (Trigger: {m.get('trigger')})" if m.get("trigger") else ""
            ms_summary.append(f"  * {m.get('name', 'Milestone')}: {ms_pct}% (INR {int(ms_amt):,}){ms_trig}")
        ms_text = "\n".join(ms_summary) if ms_summary else "  * Standard 3-Tranche Milestone Plan (40% Onboarding / 30% Assessment / 30% Lodgement)"

        # Cost Allocations / Commissions
        allocs = product_doc.get("cost_allocations") or []
        alloc_summary = []
        for a in allocs:
            a_label = a.get("label") or a.get("vendor_category") or "Partner Split"
            a_val = a.get("rate") if a.get("payment_type") == "percentage" else a.get("amount")
            a_type = "% of Retainer" if a.get("payment_type") == "percentage" else "INR flat"
            alloc_summary.append(f"  * {a_label}: {a_val} {a_type}")
        alloc_text = "\n".join(alloc_summary) if alloc_summary else "  * Standard Sales Commission & Margin Economics"

        # Refund Policy
        rp = product_doc.get("refund_policy") or {}
        rp_enabled = rp.get("enabled", True)
        rp_model = rp.get("policy_type", "protection")
        rp_pct = rp.get("refundable_service_fee_pct", 100)
        rp_gst = rp.get("gst_treatment", "credit_note")
        rp_govt = rp.get("govt_fees_handling", "non_refundable")
        rp_window = rp.get("claim_window_days", 30)
        rp_sla = rp.get("payout_time_days", 14)
        rp_triggers = []
        if rp.get("negative_skills_assessment_guarantee"): rp_triggers.append("Negative Skills Assessment Guarantee")
        if rp.get("visa_refusal_guarantee"): rp_triggers.append("Official Visa Refusal Guarantee")
        if rp.get("voluntary_withdrawal_milestones"): rp_triggers.append("Voluntary Withdrawal Pre-Lodgement")
        for ct in rp.get("custom_guaranteed_triggers") or []:
            rp_triggers.append(ct.get("trigger_name", "Regional Nomination Guarantee"))

        refund_text = (
            f"  * Salesperson Visibility Status: {'Active for Sales' if rp_enabled else 'Restricted / Discretionary by Admin'}\n"
            f"  * Policy Model: {rp_model.upper()} ({rp_pct}% Service Fee Refundable)\n"
            f"  * GST Treatment: {rp_gst} | Government Fees: {rp_govt}\n"
            f"  * Claim Window: {rp_window} days | Payout SLA: {rp_sla} days\n"
            f"  * Guaranteed Triggers: {', '.join(rp_triggers) if rp_triggers else 'Statutory compliance'}\n"
            f"  * Mandatory Conditions: {'; '.join((rp.get('conditions') or [])[:3])}\n"
            f"  * Exclusions: {'; '.join((rp.get('exclusions') or [])[:3])}"
        )

        doc_context = (
            f"\nVERIFIED PRODUCT MASTER DATA (SINGLE SOURCE OF TRUTH):\n"
            f"- Destination Country: {matched_country}\n"
            f"- Visa Product: {matched_visa} (Subclass: {matched_subclass})\n"
            f"- Category: {product_doc.get('category')}\n"
            f"- Authority: {auth_name}\n"
            f"- Official Government Slabs: {product_doc.get('government_costs')}\n"
            f"- LEAMSS Base Retainer Fee: INR {p_base:,.0f} (+ 18% Statutory GST: INR {p_gst:,.0f} = Total Client Chargeable: INR {p_total:,.0f})\n"
            f"- Retainer Milestone Payment Schedule:\n{ms_text}\n"
            f"- Client Package Tiers:\n{pkgs_text}\n"
            f"- Partner Splits & Salesperson Commissions:\n{alloc_text}\n"
            f"- Refund Policy & Statutory Safeguards:\n{refund_text}\n"
            f"- Eligibility Criteria: {product_doc.get('eligibility_criteria')}\n"
            f"- Sales Playbook: {product_doc.get('sales_playbook')}\n"
        )

    occ_context = ""
    if profile:
        occ_context = (
            f"\nVERIFIED OCCUPATION INTELLIGENCE (OFFICIAL GOVERNMENT GROUND TRUTH):\n"
            f"- Code: {profile.code}\n"
            f"- Title: {profile.title}\n"
            f"- Classification System: {profile.classification_system}\n"
            f"- Country of Origin: {profile.country} ({profile.country_code})\n"
            f"- Skill Tier / Classification: {profile.skill_tier_label}\n"
            f"- Official Lead Duties:\n" + "\n".join([f"  * {d}" for d in profile.main_duties[:4]]) + "\n"
            f"- Assessing Authority: {profile.assessing_authority}\n"
            f"- Applicable Visa Pathways: {', '.join(profile.visa_pathways[:3])}\n"
            f"- Statutory Wage / Salary Threshold: {profile.statutory_salary_threshold}\n"
            f"- Official Portal: {profile.official_source_url}\n"
        )
        if det and det.is_mismatch:
            occ_context += (
                f"\n⚠️ CRITICAL COUNTRY & CLASSIFICATION MISMATCH ALERT:\n"
                f"- The salesperson currently has '{det.selected_country}' selected in the UI dropdown.\n"
                f"- HOWEVER, the queried code '{det.code}' belongs strictly to '{det.country}' ({det.classification_system}).\n"
                f"- You MUST explain {det.country}'s statutory rules for {det.code} ({profile.title}).\n"
                f"- You MUST prominently alert the salesperson: '{det.mismatch_warning}'.\n"
            )
            if det.crosswalk_code:
                occ_context += (
                    f"- Equivalent occupation in {det.selected_country}: {det.crosswalk_code} ({det.crosswalk_title}), "
                    f"Assessing Body: {det.crosswalk_authority}.\n"
                )

    # Cross-contamination prevention and query-specific instructions
    anti_cross_contamination = ""
    if matched_country == "Australia":
        anti_cross_contamination = (
            f"\nSTRICT REGULATORY ISOLATION ENFORCEMENT:\n"
            f"- Destination is strictly AUSTRALIA ({auth_name}).\n"
            f"- NEVER mention USA EB-2 NIW, Form I-140, PERM, USCIS, or US Department of State when answering for Australia.\n"
            f"- Use ONLY Department of Home Affairs (DHA) regulations, SkillSelect, and AUD 4,770 fees.\n"
        )
    elif matched_country == "Canada":
        anti_cross_contamination = (
            f"\nSTRICT REGULATORY ISOLATION ENFORCEMENT:\n"
            f"- Destination is strictly CANADA (IRCC).\n"
            f"- Use ONLY IRCC Express Entry (FSW/PNP/CEC) regulations and official CAD fees.\n"
        )

    travel_instruction = ""
    if intent.is_travel_abroad_pr_query:
        travel_instruction = (
            f"\nCRITICAL TRAVEL / OFFSHORE PR QUERY DETECTED:\n"
            f"- The client is asking whether they need to travel abroad or travel to {matched_country} for their PR application.\n"
            f"- {intent.offshore_onshore_explanation}\n"
            f"- In Section 1 Speaking Script, clearly and reassuringly tell the client that they DO NOT need to travel abroad to apply for {matched_country} PR, because it is 100% offshore from their home country.\n"
            f"- In Section 2 Key Facts, explain the offshore process steps.\n"
        )

    clarification_instruction = ""
    if intent.is_unclear:
        clarification_instruction = (
            f"\nAMBIGUOUS QUERY HANDLING:\n"
            f"- The client did not specify a destination country.\n"
            f"- In Section 1, ask the client this clarification question: '{intent.clarification_question}'\n"
            f"- In Section 2, provide a 1-line answer for both Australia (Subclass 189/190) and Canada (Express Entry).\n"
        )

    # 3. Attempt Perplexity Online LLM query
    try:
        from core.perplexity_client import call_perplexity

        system_msg = (
            "You are an expert immigration sales assistant for LEAMSS Immigration Consulting. "
            "Answer STRICTLY AND EXCLUSIVELY what the client asks. "
            "Provide SHORT, CLEAR, ACCURATE answers in SMALL SENTENCES (maximum 15-20 words per sentence) "
            "designed for a sales consultant to speak and explain to clients during live phone calls. "
            "NEVER add unrelated information, extra explanations, or unnecessary sections. "
            "CRITICAL RULE ON FEES: DO NOT provide government fees, LEAMSS charges, GST, payment details, or cost breakdowns "
            "UNLESS the client specifically asks about fees, pricing, or costs. "
            "ALWAYS show the SPEAKING SCRIPT FIRST in '### 💬 1. Speaking Script for Live Call (Read directly to client)' "
            "so the consultant can immediately read it out loud to the client in short, natural sentences. "
            "Ground your answer strictly in the provided VERIFIED PRODUCT MASTER DATA, REGULATORY AUTHORITY DETAILS, and OCCUPATION INTELLIGENCE. "
            "DO NOT include any sources list, web search citations, or raw URLs at the bottom of your response. "
            "Never invent information or guarantee PR/visa approval. Always end with the standard statutory disclaimer."
        )

        structure_instructions = ""
        if intent.is_unclear:
            structure_instructions = (
                f"- The client did not specify a destination country.\n"
                f"- FIRST SECTION: In '### 💬 1. Speaking Script for Live Call (Read directly to client)', write a 1-2 sentence script asking the client this exact clarification question: \"{intent.clarification_question}\"\n"
                f"- SECOND SECTION: In '### ❓ 2. Destination Clarification & Comparison (Small Sentences)', provide 1 short bullet for Australia (Subclass 189/190 without job offer) and 1 short bullet for Canada (Express Entry FSW without job offer).\n"
                f"- DO NOT output fees, retainers, process steps, or objection handling.\n"
            )
        elif intent.query_topic == "family":
            structure_instructions = (
                f"- The client is asking about including their spouse or children in {matched_country} {matched_visa} (Subclass 189).\n"
                f"- Answer STRICTLY AND ONLY about family inclusion rules, eligibility, child age limits, spouse genuine relationship proof, and health/character requirements.\n"
                f"- CRITICAL RULE ON FEES: DO NOT provide fee breakdowns, AUD/INR amounts, or commercial pricing unless the client specifically asks about fees. Mention only that additional government charges apply for secondary applicants.\n"
                f"- FIRST SECTION: '### 💬 1. Speaking Script for Live Call (Read directly to client)' — 3-4 short spoken sentences (max 15-20 words each): 1) Eligible spouse/de facto partner and dependent children can be included; 2) They receive PR only if included and their visas are approved; 3) Children must be under 18 or aged 18-23 and financially dependent; 4) Spouse requires genuine relationship evidence and all must meet health/character; 5) Additional government charges apply for secondary applicants.\n"
                f"- SECOND SECTION: '### ⚡ 2. Direct Quick Answer: Family Inclusion Rules for {matched_country} {matched_visa} (Small Sentences)' with concise bullets for: Eligible Family Members, Permanent Residency Approval Condition, Dependent Children Age & Dependency (<18 automatic, 18-23 dependent/unmarried, 23+ disability only), Spouse Genuine Relationship Evidence, Mandatory Health & Character Criteria, and Statutory Government Application Charges.\n"
            )
        elif intent.query_topic == "benefits":
            structure_instructions = (
                f"- The client is asking about the benefits of {matched_country} PR.\n"
                f"- Answer STRICTLY AND ONLY about benefits. DO NOT include government fees, LEAMSS pricing, GST, payment details, process steps, or objection rebuttals.\n"
                f"- FIRST SECTION: '### 💬 1. Speaking Script for Live Call (Read directly to client)' — 2-3 short, spoken sentences explaining the top benefits (Medicare/healthcare, unconditional work rights, citizenship pathway, schooling for kids).\n"
                f"- SECOND SECTION: '### 🌟 2. Key {matched_country} Permanent Residency Benefits (Small Sentences)' with 4-5 bullet points covering: Unconditional Work Rights, Universal Healthcare Protection (Medicare), Pathway to Citizenship, Family Sponsorship, and Education Entitlements.\n"
            )
        elif intent.query_topic == "travel":
            structure_instructions = (
                f"- The client is asking about travel abroad or traveling to {matched_country} for PR.\n"
                f"- Answer STRICTLY AND ONLY about travel requirements and offshore application rules.\n"
                f"- DO NOT include government fees, LEAMSS pricing, GST, payment details, or objection rebuttals.\n"
                f"- FIRST SECTION: '### 💬 1. Speaking Script for Live Call (Read directly to client)' — 2-3 short, reassuring sentences explaining that {matched_country} PR is 100% offshore and they DO NOT need to travel abroad to apply or secure PR.\n"
                f"- SECOND SECTION: '### ✈️ 2. Travel & Offshore Application Rules (Small Sentences)' with 4 short bullet points explaining: 100% Offshore Application, Zero Foreign Travel Prerequisite, Home Country Assessments (English/Skills), and Initial Entry Date.\n"
            )
        elif intent.query_topic == "eligibility":
            structure_instructions = (
                f"- The client is asking about eligibility criteria for {matched_country} {matched_visa}.\n"
                f"- Answer STRICTLY AND ONLY about eligibility criteria and benchmarks.\n"
                f"- DO NOT include government fees, LEAMSS pricing, GST, payment details, process steps, or objection rebuttals.\n"
                f"- FIRST SECTION: '### 💬 1. Speaking Script for Live Call (Read directly to client)' — 2-3 short sentences explaining the core eligibility criteria in spoken English.\n"
                f"- SECOND SECTION: '### ⚡ 2. Core Eligibility Criteria & Points Benchmarks (Small Sentences)' with bullet points for: Age Benchmark (<45), Skills Assessment, Language Benchmark, Points Benchmark (e.g. 65), and No Job Offer Requirement.\n"
            )
        elif intent.query_topic == "process":
            structure_instructions = (
                f"- The client is asking about the process, application steps, or timeline for {matched_country} {matched_visa}.\n"
                f"- Answer STRICTLY AND ONLY about application procedure stages and timeframes.\n"
                f"- DO NOT include government fees, LEAMSS pricing, GST, payment details, or objection rebuttals.\n"
                f"- FIRST SECTION: '### 💬 1. Speaking Script for Live Call (Read directly to client)' — 2-3 short sentences explaining the application roadmap and duration.\n"
                f"- SECOND SECTION: '### ⏱️ 2. Application Steps & Processing Timeline (Small Sentences)' with 4-5 short bullets covering Stage 1 (Skills Assessment), Stage 2 (Language & EOI), Stage 3 (Invitation), Stage 4 (Visa Lodgement), and Estimated Timeline.\n"
            )
        elif intent.query_topic == "fees":
            q_low = q.lower()
            if any(k in q_low for k in ["refund", "money back", "protection guarantee"]):
                structure_instructions = (
                    f"- The client or consultant is asking about the LEAMSS Refund Policy and guarantees for {matched_country} {matched_visa}.\n"
                    f"- FIRST SECTION: '### 💬 1. Speaking Script for Live Call (Read directly to client)' — 2-3 short, spoken sentences explaining the verified refund policy model, refundable service fee percentage, claim window, and statutory government fee rules from VERIFIED PRODUCT MASTER DATA.\n"
                    f"- SECOND SECTION: '### 🛡️ 2. Verified Refund Safeguards & Policy Terms (Small Sentences)' with bullets for: Guarantee Model, Refundable Service Fee %, Government Fees Handling (Non-refundable paid to authority), GST Treatment, Claim Window & Payout SLA, and Guaranteed Triggers.\n"
                )
            elif any(k in q_low for k in ["package", "packages", "tier", "tiers", "smart", "premium"]):
                structure_instructions = (
                    f"- The client is asking about service package options/tiers for {matched_country} {matched_visa}.\n"
                    f"- FIRST SECTION: '### 💬 1. Speaking Script for Live Call (Read directly to client)' — 2-3 short sentences introducing the structured package tiers (Standard, Smart, Premium) and milestone billing from VERIFIED PRODUCT MASTER DATA.\n"
                    f"- SECOND SECTION: '### 📦 2. Client Portal Package Tiers (Small Sentences)' with 1 short bullet for each active package from VERIFIED PRODUCT MASTER DATA detailing tier name, price in INR (+ 18% GST), and key deliverables.\n"
                )
            elif any(k in q_low for k in ["milestone", "milestones", "tranche", "tranches", "installment"]):
                structure_instructions = (
                    f"- The client is asking about payment milestones and installments for {matched_country} {matched_visa}.\n"
                    f"- FIRST SECTION: '### 💬 1. Speaking Script for Live Call (Read directly to client)' — 2-3 short sentences explaining that retainer fees are divided into milestone stages linked to delivery.\n"
                    f"- SECOND SECTION: '### 💳 2. Retainer Milestone Payment Schedule (Small Sentences)' with 1 short bullet for each milestone tranche from VERIFIED PRODUCT MASTER DATA detailing order, name, percentage, INR amount, and operational trigger.\n"
                )
            elif any(k in q_low for k in ["commission", "commissions", "split", "splits", "incentive"]):
                structure_instructions = (
                    f"- The consultant is inquiring about commissions and partner splits for {matched_country} {matched_visa}.\n"
                    f"- FIRST SECTION: '### 💬 1. Speaking Script for Live Call (Read directly to client)' — 2 short sentences outlining the verified commission structure.\n"
                    f"- SECOND SECTION: '### 💼 2. Product Master Commissions & Partner Splits (Small Sentences)' with bullets for Internal Salesperson, External Partner, and Case Manager allocations from VERIFIED PRODUCT MASTER DATA.\n"
                )
            else:
                structure_instructions = (
                    f"- The client is asking about fees, costs, or pricing for {matched_country} {matched_visa}.\n"
                    f"- FIRST SECTION: '### 💬 1. Speaking Script for Live Call (Read directly to client)' — 2-3 short sentences explaining official government charges and LEAMSS transparent retainer.\n"
                    f"- SECOND SECTION: '### 💰 2. Statutory Government Fees & Commercial Investment (Small Sentences)' with bullet points for: Official Government Visa Fee ({fees['gov_fee_foreign']} ~{fees['gov_fee_inr_approx']}), Fee Breakdown ({fees['gov_fee_breakdown']}), LEAMSS Professional Retainer (₹{int(service_price):,} + 18% GST), Milestone Schedule, and Required Settlement Funds.\n"
                )
        elif intent.query_topic == "objection":
            structure_instructions = (
                f"- The client has raised an objection or asked about guarantees or refusal.\n"
                f"- FIRST SECTION: '### 💬 1. Speaking Script for Live Call (Read directly to client)' — 2-3 short sentences with an approved consultant rebuttal.\n"
                f"- SECOND SECTION: '### 🛡️ 2. Professional Objection Handling & Institutional Guarantee (Small Sentences)' with bullets for: Client Objection, Sovereign Authority Prerogative, LEAMSS Institutional Compliance Guarantee, and Risk Mitigation.\n"
            )
        else:
            structure_instructions = (
                f"- Answer the client's scenario directly and concisely in small sentences.\n"
                f"- DO NOT include government fees or commercial breakdowns unless the question specifically asked for them.\n"
                f"- FIRST SECTION: '### 💬 1. Speaking Script for Live Call (Read directly to client)' — 2-3 short, spoken sentences directly answering the client's question.\n"
                f"- SECOND SECTION: '### ⚡ 2. Direct Quick Answer & Key Facts (Small Sentences)' with 3-4 short bullets covering: Direct Solution, Statutory Rule, and Recommended Action.\n"
            )

        prompt = (
            f"Client Query / Question: {q}\n"
            f"Destination Country: {matched_country}\n"
            f"Visa Product: {matched_visa} (Subclass: {matched_subclass})\n"
            f"Official Government Authority: {auth_name}\n"
            + (f"Official Fees Ground Truth: {fees['gov_fee_foreign']} (~{fees['gov_fee_inr_approx']}), Breakdown: {fees['gov_fee_breakdown']}\n" if intent.query_topic == "fees" else "")
            + (f"LEAMSS Retainer: INR {int(service_price):,} (+ 18% GST)\n" if intent.query_topic == "fees" else "")
            + f"{occ_context}\n"
            + f"{doc_context}\n"
            + (f"\nREGULATORY WORKFLOW INTELLIGENCE:\n{workflow_notes}\n" if workflow_notes else "")
            + anti_cross_contamination
            + travel_instruction
            + clarification_instruction
            + f"\nCRITICAL INSTRUCTIONS FOR LIVE-CALL FORMATTING:\n"
            f"- FIRST SECTION MUST BE THE SPEAKING SCRIPT to explain directly to the client in short, natural words.\n"
            f"- Write in SMALL, PUNCHY SENTENCES ONLY (max 15-20 words each).\n"
            f"- NO lengthy paragraphs or walls of text.\n"
            f"- DO NOT output any '_Sources (Perplexity web search):_' or lists of website URLs at the end.\n"
            f"{structure_instructions}\n"
            f"- ALWAYS end your response with:\n"
            f"> **LEAMSS Statutory Disclaimer:** Official immigration criteria, quotas, and government visa charges are subject to official gazette notifications by sovereign immigration authorities ({auth_name}). LEAMSS operates strictly under licensed consulting compliance and never guarantees visa approval."
        )

        answer, model_used = await call_perplexity(
            prompt=prompt,
            system_msg=system_msg,
            model="sonar",
            max_tokens=2000,
            temperature=0.2,
            timeout=40.0,
        )
        answer = _clean_ai_response(answer)
        if "LEAMSS Statutory Disclaimer" not in answer:
            answer = f"{answer.strip()}\n\n> **LEAMSS Statutory Disclaimer:** Official immigration criteria, quotas, and government visa charges are subject to official gazette notifications by sovereign immigration authorities ({auth_name}). LEAMSS operates strictly under licensed consulting compliance and never guarantees visa approval."
        elif auth_name and auth_name not in answer:
            answer = f"{answer.strip()}\n\n> **Regulatory Authority Reference:** {auth_name} ({matched_country})"

        return {
            "answer": answer,
            "model": model_used,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "target_country": matched_country,
            "target_subclass": matched_subclass,
            "target_product_id": product_doc.get("id") if product_doc else None,
            "verified_product": bool(product_doc),
            "is_travel_query": intent.is_travel_abroad_pr_query,
            "is_unclear": intent.is_unclear,
            "sources": {
                "government_portal": gov_url,
                "government_authority": auth_name,
                "migrate_page_url": migrate_url,
                "atlas_page_url": atlas_url,
                "vfs_url": vfs_url,
            },
            "occupation_detected": {
                "code": det.code,
                "title": det.title,
                "system": det.classification_system,
                "country": det.country,
                "is_mismatch": det.is_mismatch,
                "crosswalk_code": det.crosswalk_code,
                "crosswalk_title": det.crosswalk_title,
            } if det else None,
        }
    except Exception as e:
        logger.warning("Perplexity query failed or timed out, falling back to complete statutory synthesis: %s", e)
        answer = _synthesize_sales_response(
            product_doc,
            payload,
            q,
            auth_info=auth_data,
            profile=profile,
            intent=intent,
            det=det,
        )

        return {
            "answer": answer,
            "model": "leamss-regulatory-ai-v2",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "target_country": matched_country,
            "target_subclass": matched_subclass,
            "target_product_id": product_doc.get("id") if product_doc else None,
            "verified_product": bool(product_doc),
            "is_travel_query": intent.is_travel_abroad_pr_query,
            "is_unclear": intent.is_unclear,
            "sources": {
                "government_portal": gov_url,
                "government_authority": auth_name,
                "migrate_page_url": migrate_url,
                "atlas_page_url": atlas_url,
                "vfs_url": vfs_url,
            },
            "occupation_detected": {
                "code": det.code,
                "title": det.title,
                "system": det.classification_system,
                "country": det.country,
                "is_mismatch": det.is_mismatch,
                "crosswalk_code": det.crosswalk_code,
                "crosswalk_title": det.crosswalk_title,
            } if det else None,
        }




@router.post("/sales-ai-translate")
async def sales_ai_translate(
    payload: SalesAiTranslateRequest,
    current_user: dict = Depends(get_current_user),
):
    """Authenticated staff: Translate complete AI Salesperson answers into English, Marathi, or Hindi."""
    text = (payload.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text to translate is required")

    target_raw = (payload.target_language or "English").strip()
    target_lower = target_raw.lower()

    if target_lower in ("marathi", "mr", "मराठी"):
        target_lang = "Marathi"
        script_hint = "मराठी (Devanagari script)"
    elif target_lower in ("hindi", "hi", "हिंदी"):
        target_lang = "Hindi"
        script_hint = "हिंदी (Devanagari script)"
    else:
        target_lang = "English"
        script_hint = "English (Latin script)"

    # Fast detection: Check if the text is already primarily in the requested target language
    has_devanagari = bool(re.search(r"[\u0900-\u097F]", text))
    if target_lang == "English" and not has_devanagari:
        return {
            "translated_text": text,
            "target_language": "English",
            "model": "direct-passthrough",
        }

    # Attempt high-fidelity LLM translation via Perplexity
    try:
        from core.perplexity_client import call_perplexity

        system_msg = (
            f"You are an expert official immigration legal translator for LEAMSS Immigration Consulting. "
            f"Translate the provided immigration advisory text into {target_lang} ({script_hint}). "
            f"\nCRITICAL TRANSLATION RULES:\n"
            f"1. PRESERVE ACCURATE LEGAL & REGULATORY MEANING: Maintain exact statutory visa terms, visa subclass numbers "
            f"(e.g. Subclass 189, Subclass 190, F-1, H-1B, SSW), official government authority names "
            f"(Department of Home Affairs, USCIS, IRCC, SEVP, VFS), official form codes (DS-160, Form I-20), "
            f"test names (JLPT N4, IELTS, PTE), points marks (e.g. 65), and fee currency/numbers.\n"
            f"2. PRESERVE MARKDOWN & DOCUMENT STRUCTURE: Retain all markdown headings (### 💬 1. ..., ### ⚡ 2. ...), "
            f"bullet points, emojis, bolding, blockquotes (> *\"...\"*), and disclaimer sections exactly in place.\n"
            f"3. NATURAL PROFESSIONAL TONE: Provide fluent, natural translation that an Indian immigration sales consultant "
            f"can read and explain directly to a client over the phone.\n"
            f"4. NO UNRELATED CONTENT: Do not add translator commentary, notes, preambles, or explanations. "
            f"Return ONLY the translated document."
        )

        prompt = (
            f"Immigration Context: {payload.country or 'General Skilled Migration'} "
            f"{f'(Subclass: {payload.visa_subclass})' if payload.visa_subclass else ''}\n"
            f"Target Language: {target_lang}\n\n"
            f"Document To Translate:\n{text}"
        )

        translated, model_used = await call_perplexity(
            prompt=prompt,
            system_msg=system_msg,
            model="sonar",
            max_tokens=2500,
            temperature=0.1,
            timeout=35.0,
        )
        translated = _clean_ai_response(translated)
        return {
            "translated_text": translated,
            "target_language": target_lang,
            "model": model_used,
        }
    except Exception as e:
        logger.warning("Perplexity translation failed or timed out: %s", e)
        return {
            "translated_text": text,
            "target_language": target_lang,
            "model": "fallback-preservation",
        }




@router.post("")
async def create_product_master(
    data: dict,
    current_user: dict = Depends(get_current_user),
):
    """Admin-only: Create a new Product Master record."""
    _require_admin(current_user)
    
    if not data.get("name") or not str(data["name"]).strip():
        raise HTTPException(status_code=400, detail="Product name is required")

    prod_id = data.get("id") or str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    service_price = float(data.get("service_price") or data.get("base_fee") or 0)

    record = {
        "id": prod_id,
        "name": data["name"].strip(),
        "summary": data.get("summary") or data.get("description", ""),
        "description": data.get("description") or data.get("summary", ""),
        "country": (data.get("country") or "").strip(),
        "visa_type": (data.get("visa_type") or "").strip(),
        "visa_subclass": (data.get("visa_subclass") or "").strip(),
        "category": data.get("category") or "skilled_migration",
        "status": data.get("status") or "draft",
        "version": int(data.get("version") or 1),
        "service_price": service_price,
        "base_fee": service_price,
        
        # Module A — 19 Tabs Data Model
        "migrate_page_url": data.get("migrate_page_url") or "",
        "official_urls": data.get("official_urls") or [],
        "official_domains": data.get("official_domains") or [],
        "eligibility_criteria": data.get("eligibility_criteria") or {
            "mandatory": [],
            "optional": [],
            "points_based": {"is_points_tested": False, "minimum_points": 0, "scoring_factors": []}
        },
        "visa_conditions": data.get("visa_conditions") or [],
        "government_costs": data.get("government_costs") or {
            "currency": "INR",
            "line_items": [],
            "effective_date": None,
            "source_link": ""
        },
        "processing_timeline": data.get("processing_timeline") or {
            "standard_duration": "",
            "stages": []
        },
        "sales_playbook": data.get("sales_playbook") or {
            "target_client": "",
            "pitch_points": [],
            "key_benefits": []
        },
        "objections_rebuttals": data.get("objections_rebuttals") or [],
        "faqs": data.get("faqs") or [],
        "document_checklist_template": data.get("document_checklist_template") or [],
        "gst_applicable": data.get("gst_applicable", True),
        "package_gst_applicable": data.get("package_gst_applicable", False),
        "packages": data.get("packages") or [
            {"id": str(uuid.uuid4()), "package_type": "standard", "name": "Standard Package", "price": service_price, "description": "", "is_active": True, "gst_applicable": False},
            {"id": str(uuid.uuid4()), "package_type": "smart", "name": "Smart Package", "price": service_price, "description": "", "is_active": True, "gst_applicable": False},
            {"id": str(uuid.uuid4()), "package_type": "premium", "name": "Premium Package", "price": service_price, "description": "", "is_active": True, "gst_applicable": False},
        ],
        "cost_allocations": data.get("cost_allocations") or [],
        "success_bonuses": data.get("success_bonuses") or [],
        "discount_coupons": data.get("discount_coupons") or [],
        "letters_required": data.get("letters_required") or [],
        "info_sheet_sections": data.get("info_sheet_sections") or [],
        "refund_options": data.get("refund_options") or [],
        "refund_policy": data.get("refund_policy") or {
            "enabled": True,
            "policy_type": "protection",
            "name": "LEAMSS Protection Policy Guarantee",
            "refundable_service_fee_pct": 100,
            "is_service_fee_refundable": True,
            "govt_fees_handling": "non_refundable",
            "is_govt_fee_refundable": False,
            "gst_treatment": "credit_note",
            "negative_skills_assessment_guarantee": True,
            "visa_refusal_guarantee": True,
            "voluntary_withdrawal_milestones": True,
            "claim_window_days": 30,
            "payout_time_days": 14,
            "maker_checker_required": True,
            "custom_fee_components": [],
            "custom_guaranteed_triggers": [],
            "conditions": [
                "100% genuine documentation provided without omissions",
                "Client responds to case manager queries within 7 working days",
                "Medical examination and police clearance certificates passed without adverse records"
            ],
            "exclusions": [
                "Rejection caused by fraudulent, forged or misleading documents",
                "Undisclosed prior medical condition or criminal conviction",
                "Statutory quota exhaustion or material change in destination country immigration law",
                "Client voluntary withdrawal after release of document checklist and case dossier",
                "Failure to achieve required statutory English test scores (IELTS/PTE)"
            ],
            "package_overrides": {
                "standard": {"enabled": True, "refundable_pct": 100},
                "smart": {"enabled": True, "refundable_pct": 100},
                "premium": {"enabled": True, "refundable_pct": 100}
            },
            "version": 1
        },
        "explore_services": data.get("explore_services") or {
            "show_in_explore": True,
            "direct_purchase_allowed": False,
            "suggested_next_products": []
        },
        "commercials": data.get("commercials") or {},
        "last_verified_at": data.get("last_verified_at"),
        "last_verified_by": data.get("last_verified_by"),
        "next_review_at": data.get("next_review_at"),
        "created_by": current_user["id"],
        "created_at": now,
        "updated_at": now,
        "archived_at": None,
    }

    # Save to product_master collection
    await product_master_col.insert_one(record)

    # Seamless background sync to products_col for backward compatibility
    await products_col.update_one(
        {"id": prod_id},
        {"$set": record},
        upsert=True
    )

    await log_activity(
        current_user["id"],
        current_user.get("name", "Admin"),
        "created",
        "product_master",
        prod_id,
        f"Created Product Master: {record['name']}"
    )

    return {"id": prod_id, "message": "Product Master created successfully", "version": record["version"]}


@router.put("/{product_id}")
async def update_product_master(
    product_id: str,
    data: dict,
    current_user: dict = Depends(get_current_user),
):
    """Admin-only: Update existing Product Master record."""
    _require_admin(current_user)

    existing = await product_master_col.find_one({"id": product_id})
    if not existing:
        # Check products_col
        existing = await products_col.find_one({"id": product_id})
        if not existing:
            raise HTTPException(status_code=404, detail="Product Master record not found")

    now = datetime.now(timezone.utc)
    current_ver = int(existing.get("version") or 1)
    new_ver = current_ver + 1 if data.get("status") == "active" else current_ver

    update_fields: Dict[str, Any] = {
        "updated_at": now,
        "version": new_ver,
    }

    allowed_keys = [
        "name", "summary", "description", "country", "visa_type", "visa_subclass", "category",
        "status", "service_price", "base_fee", "migrate_page_url", "official_urls", "official_domains",
        "eligibility_criteria", "visa_conditions", "government_costs", "processing_timeline",
        "sales_playbook", "objections_rebuttals", "faqs", "document_checklist_template",
        "packages", "cost_allocations", "success_bonuses", "discount_coupons",
        "letters_required", "info_sheet_sections", "refund_options", "refund_policy", "refund_policy_version", "explore_services",
        "commercials", "last_verified_at", "last_verified_by", "next_review_at",
        "gst_applicable", "package_gst_applicable",
    ]

    for k in allowed_keys:
        if k in data:
            update_fields[k] = data[k]

    if "service_price" in update_fields:
        update_fields["service_price"] = float(update_fields["service_price"] or 0)
        update_fields["base_fee"] = update_fields["service_price"]

    # Update in product_master_col
    await product_master_col.update_one(
        {"id": product_id},
        {"$set": update_fields},
        upsert=True
    )

    # Sync to products_col
    await products_col.update_one(
        {"id": product_id},
        {"$set": update_fields},
        upsert=True
    )

    # If workflow_steps provided, update workflow_steps_col
    if "workflow_steps" in data and isinstance(data["workflow_steps"], list):
        await workflow_steps_col.delete_many({"product_id": product_id})
        for s in data["workflow_steps"]:
            step_doc = {
                "id": s.get("id") or str(uuid.uuid4()),
                "product_id": product_id,
                "step_name": s.get("step_name") or s.get("name") or "",
                "name": s.get("step_name") or s.get("name") or "",
                "step_order": int(s.get("step_order") or s.get("order") or 1),
                "order": int(s.get("step_order") or s.get("order") or 1),
                "description": s.get("description") or "",
                "duration_days": int(s.get("duration_days") or 7),
                "required_documents": s.get("required_documents") or [],
                "important_notes": s.get("important_notes") or "",
                "government_fees": s.get("government_fees") or "",
                "official_source_url": s.get("official_source_url") or "",
                "vfsglobal_url": s.get("vfsglobal_url") or "",
                "is_active": True,
                "created_at": now,
            }
            await workflow_steps_col.insert_one(step_doc)

    await log_activity(
        current_user["id"],
        current_user.get("name", "Admin"),
        "updated",
        "product_master",
        product_id,
        f"Updated Product Master: {update_fields.get('name') or existing.get('name')}"
    )

    updated_doc = await product_master_col.find_one({"id": product_id}, {"_id": 0})
    if updated_doc:
        steps = await workflow_steps_col.find({"product_id": product_id}, {"_id": 0}).sort("step_order", 1).to_list(100)
        for s in steps:
            if isinstance(s.get("created_at"), datetime):
                s["created_at"] = s["created_at"].isoformat()
        updated_doc["workflow_steps"] = steps

        for k in ("created_at", "updated_at", "last_verified_at", "next_review_at", "archived_at"):
            if isinstance(updated_doc.get(k), datetime):
                updated_doc[k] = updated_doc[k].isoformat()

    return {"message": "Product Master updated successfully", "version": new_ver, "product": updated_doc}


@router.patch("/{product_id}/sales-pitch")
async def update_sales_pitch(
    product_id: str,
    data: dict,
    current_user: dict = Depends(get_current_user),
):
    """Admin-only: Update sales pitch, discovery questions, USPs, and objections for a product."""
    _require_admin(current_user)

    existing = await product_master_col.find_one({"id": product_id})
    if not existing:
        existing = await products_col.find_one({"id": product_id})
        if not existing:
            raise HTTPException(status_code=404, detail="Product Master record not found")

    now = datetime.now(timezone.utc)
    current_playbook = existing.get("sales_playbook") or {}

    # Build updated sales_playbook
    new_playbook = {**current_playbook}
    if "elevator_pitch" in data:
        new_playbook["elevator_pitch"] = str(data["elevator_pitch"] or "").strip()
    if "pitch_points" in data and isinstance(data["pitch_points"], list):
        new_playbook["pitch_points"] = [str(p).strip() for p in data["pitch_points"] if str(p).strip()]
    if "target_audience" in data or "target_client" in data:
        tgt = str(data.get("target_audience") or data.get("target_client") or "").strip()
        new_playbook["target_audience"] = tgt
        new_playbook["target_client"] = tgt
    if "usps" in data and isinstance(data["usps"], list):
        clean_usps = [str(u).strip() for u in data["usps"] if str(u).strip()]
        new_playbook["usps"] = clean_usps
        new_playbook["key_benefits"] = clean_usps
    if "discovery_questions" in data and isinstance(data["discovery_questions"], list):
        new_playbook["discovery_questions"] = [str(q).strip() for q in data["discovery_questions"] if str(q).strip()]

    update_fields: Dict[str, Any] = {
        "updated_at": now,
        "sales_playbook": new_playbook,
    }

    if "objections_rebuttals" in data and isinstance(data["objections_rebuttals"], list):
        clean_objs = []
        for item in data["objections_rebuttals"]:
            if isinstance(item, dict):
                obj_text = str(item.get("objection") or "").strip()
                reb_text = str(item.get("rebuttal") or "").strip()
                if obj_text or reb_text:
                    clean_objs.append({"objection": obj_text, "rebuttal": reb_text})
        update_fields["objections_rebuttals"] = clean_objs

    if "faqs" in data and isinstance(data["faqs"], list):
        clean_faqs = []
        for item in data["faqs"]:
            if isinstance(item, dict):
                q = str(item.get("question") or "").strip()
                a = str(item.get("answer") or "").strip()
                if q or a:
                    clean_faqs.append({"question": q, "answer": a})
        update_fields["faqs"] = clean_faqs

    if "government_costs" in data and isinstance(data["government_costs"], dict):
        current_gov = existing.get("government_costs") or {}
        new_gov = {**current_gov}
        gov_data = data["government_costs"]
        if "currency" in gov_data:
            new_gov["currency"] = str(gov_data["currency"] or "AUD").strip().upper()
        if "primary_applicant" in gov_data:
            try:
                new_gov["primary_applicant"] = float(gov_data["primary_applicant"] or 0)
            except (ValueError, TypeError):
                pass
        if "secondary_applicant_adult" in gov_data:
            try:
                new_gov["secondary_applicant_adult"] = float(gov_data["secondary_applicant_adult"] or 0)
            except (ValueError, TypeError):
                pass
        if "secondary_applicant_child" in gov_data:
            try:
                new_gov["secondary_applicant_child"] = float(gov_data["secondary_applicant_child"] or 0)
            except (ValueError, TypeError):
                pass
        update_fields["government_costs"] = new_gov

    if "document_checklist_template" in data and isinstance(data["document_checklist_template"], list):
        clean_docs = []
        for item in data["document_checklist_template"]:
            if isinstance(item, dict):
                d_name = str(item.get("document_name") or item.get("name") or "").strip()
                d_desc = str(item.get("description") or "").strip()
                if d_name:
                    clean_docs.append({
                        "document_name": d_name,
                        "description": d_desc,
                        "category": str(item.get("category") or "General").strip(),
                        "required_for": str(item.get("required_for") or "primary_applicant").strip(),
                    })
        update_fields["document_checklist_template"] = clean_docs

    # Update in both collections
    await product_master_col.update_one(
        {"id": product_id},
        {"$set": update_fields},
        upsert=True
    )
    await products_col.update_one(
        {"id": product_id},
        {"$set": update_fields},
        upsert=True
    )

    await log_activity(
        current_user["id"],
        current_user.get("name", "Admin"),
        "updated",
        "product_master_sales_pitch",
        product_id,
        f"Admin edited sales pitch for: {existing.get('name')}"
    )

    # Return updated product
    updated_doc = await product_master_col.find_one({"id": product_id}, {"_id": 0})
    if not updated_doc:
        updated_doc = await products_col.find_one({"id": product_id}, {"_id": 0})

    return {
        "message": "Sales pitch updated successfully",
        "product": updated_doc
    }


@router.delete("/{product_id}")
async def archive_product_master(
    product_id: str,
    permanent: bool = False,
    current_user: dict = Depends(get_current_user),
):
    """Admin-only: Soft delete / archive or permanently delete Product Master record."""
    _require_admin(current_user)

    if permanent:
        res1 = await product_master_col.delete_one({"id": product_id})
        res2 = await products_col.delete_one({"id": product_id})
        await log_activity(
            current_user["id"],
            current_user.get("name", "Admin"),
            "deleted",
            "product_master",
            product_id,
            "Permanently Deleted Product Master"
        )
        return {"message": "Product Master permanently deleted", "id": product_id}

    now = datetime.now(timezone.utc)

    res = await product_master_col.update_one(
        {"id": product_id},
        {"$set": {"status": "archived", "archived_at": now, "updated_at": now}}
    )
    if res.matched_count == 0:
        # Check products_col
        res2 = await products_col.update_one(
            {"id": product_id},
            {"$set": {"status": "archived", "archived_at": now, "updated_at": now}}
        )
        if res2.matched_count == 0:
            raise HTTPException(status_code=404, detail="Product Master record not found")

    await products_col.update_one(
        {"id": product_id},
        {"$set": {"status": "archived", "archived_at": now, "updated_at": now}}
    )

    await log_activity(
        current_user["id"],
        current_user.get("name", "Admin"),
        "archived",
        "product_master",
        product_id,
        "Archived Product Master"
    )

    return {"message": "Product Master archived successfully"}


@router.post("/{product_id}/restore")
async def restore_product_master(
    product_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Admin-only: Restore an archived product master back to active status."""
    _require_admin(current_user)
    now = datetime.now(timezone.utc)

    res = await product_master_col.update_one(
        {"id": product_id},
        {"$set": {"status": "active", "updated_at": now}, "$unset": {"archived_at": ""}}
    )
    await products_col.update_one(
        {"id": product_id},
        {"$set": {"status": "active", "updated_at": now}, "$unset": {"archived_at": ""}}
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Product Master record not found")

    await log_activity(
        current_user["id"],
        current_user.get("name", "Admin"),
        "restored",
        "product_master",
        product_id,
        "Restored Product Master to Active"
    )

    return {"message": "Product Master restored successfully", "status": "active", "id": product_id}


@router.post("/{product_id}/auto-enrich")
async def auto_enrich_product_master(
    product_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Admin-only: Auto-enrich a draft or incomplete product master with canonical statutory specifications."""
    _require_admin(current_user)

    product = await product_master_col.find_one({"id": product_id})
    if not product:
        product = await products_col.find_one({"id": product_id})
        if not product:
            raise HTTPException(status_code=404, detail="Product Master record not found")

    country = product.get("country") or "Australia"
    name = product.get("name") or ""
    subclass = product.get("visa_subclass") or ""

    match = find_canonical_match(country, name, subclass)
    now = datetime.now(timezone.utc)

    if match:
        updates = {
            "visa_subclass": match.get("visa_subclass") or product.get("visa_subclass", ""),
            "summary": match.get("summary") or product.get("summary", ""),
            "description": match.get("description") or product.get("description", ""),
            "category": match.get("category") or product.get("category", "skilled_migration"),
            "eligibility_criteria": match.get("eligibility_criteria", {}),
            "government_costs": match.get("government_costs", {}),
            "processing_timeline": match.get("processing_timeline", {}),
            "sales_playbook": match.get("sales_playbook", {}),
            "faqs": match.get("faqs", []),
            "objections_rebuttals": match.get("objections_rebuttals", []),
            "document_checklist_template": match.get("document_checklist_template", []),
            "service_price": product.get("service_price") or match.get("service_price", 125000),
            "base_fee": product.get("base_fee") or match.get("service_price", 125000),
            "authority_name": match.get("authority_name") or product.get("authority_name", ""),
            "authority_website": match.get("authority_website") or product.get("authority_website", ""),
            "updated_at": now,
        }
    else:
        from core.occupation_intelligence import get_statutory_fees_and_commercials, normalize_country
        c_norm = normalize_country(country)
        fees = get_statutory_fees_and_commercials(c_norm, subclass)
        updates = {
            "visa_subclass": subclass or "Skilled",
            "summary": product.get("summary") or f"Official {country} {name} immigration program.",
            "description": product.get("description") or f"Detailed statutory immigration pathway for {name} in {country}.",
            "government_costs": {
                "currency": fees.get("statutory_currency", "INR"),
                "primary_applicant": fees.get("gov_fee_num", 0),
                "line_items": [{"description": "Statutory Government Application Fee", "amount": fees.get("gov_fee_num", 0)}]
            },
            "service_price": fees.get("leamss_retainer_num", 125000),
            "base_fee": fees.get("leamss_retainer_num", 125000),
            "updated_at": now,
        }

    await product_master_col.update_one({"id": product_id}, {"$set": updates})
    await products_col.update_one({"id": product_id}, {"$set": dict(updates)})

    await log_activity(
        current_user["id"],
        current_user.get("name", "Admin"),
        "auto_enriched",
        "product_master",
        product_id,
        f"Auto-enriched Product Master {product_id} with statutory specs"
    )

    updated = await product_master_col.find_one({"id": product_id}, {"_id": 0})
    return {"message": "Product Master auto-enriched successfully", "product": updated}


@router.post("/{product_id}/verify")
async def verify_product_master_record(
    product_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Admin-only: Mark Product Master record as compliance verified."""
    _require_admin(current_user)
    now_iso = datetime.now(timezone.utc).isoformat()
    now_dt = datetime.now(timezone.utc)
    verified_by = current_user.get("name") or current_user.get("id")

    res = await product_master_col.update_one(
        {"id": product_id},
        {"$set": {
            "last_verified_at": now_iso,
            "last_verified_by": verified_by,
            "status": "active",
            "updated_at": now_dt,
        }}
    )
    if res.matched_count == 0:
        res2 = await products_col.update_one(
            {"id": product_id},
            {"$set": {
                "last_verified_at": now_iso,
                "last_verified_by": verified_by,
                "status": "active",
                "updated_at": now_dt,
            }}
        )
        if res2.matched_count == 0:
            raise HTTPException(status_code=404, detail="Product Master record not found")

    # Sync verification to products_col
    await products_col.update_one(
        {"id": product_id},
        {"$set": {
            "last_verified_at": now_iso,
            "last_verified_by": verified_by,
            "status": "active",
            "updated_at": now_dt,
        }}
    )

    await log_activity(
        current_user["id"],
        verified_by,
        "verified",
        "product_master",
        product_id,
        f"Verified Product Master at {now_iso}"
    )

    return {"message": "Product Master verified successfully", "last_verified_at": now_iso, "last_verified_by": verified_by}


@router.post("/{product_id}/clone")
async def clone_product_master(
    product_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Admin-only: Clone an existing product master as a draft."""
    _require_admin(current_user)
    source = await product_master_col.find_one({"id": product_id}, {"_id": 0})
    if not source:
        source = await products_col.find_one({"id": product_id}, {"_id": 0})
        if not source:
            raise HTTPException(status_code=404, detail="Source product not found")

    now = datetime.now(timezone.utc)
    new_id = str(uuid.uuid4())
    cloned = dict(source)
    cloned["id"] = new_id
    cloned["name"] = f"{source['name']} (Copy)"
    cloned["status"] = "draft"
    cloned["version"] = 1
    cloned["last_verified_at"] = None
    cloned["last_verified_by"] = None
    cloned["created_at"] = now
    cloned["updated_at"] = now
    cloned["created_by"] = current_user["id"]

    await product_master_col.insert_one(cloned)
    await products_col.insert_one(dict(cloned))

    await log_activity(
        current_user["id"],
        current_user.get("name", "Admin"),
        "cloned",
        "product_master",
        new_id,
        f"Cloned Product Master from {source['name']}"
    )

    return {"id": new_id, "message": "Product Master cloned as draft", "name": cloned["name"]}
