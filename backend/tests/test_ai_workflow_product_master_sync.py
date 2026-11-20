"""Tests for AI Workflow Builder sync into Product Master and Deduplication."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport
from server import app
from core.auth import get_current_user


def override_admin_user():
    return {
        "id": "adm-001",
        "name": "Super Admin",
        "role": "admin",
        "email": "admin@leamss.com",
        "permissions": ["*"]
    }


def override_sales_user():
    return {
        "id": "sales-001",
        "name": "Senior Consultant",
        "role": "salesperson",
        "email": "sales@leamss.com",
        "permissions": ["lead.view.own"]
    }


@pytest.mark.asyncio
async def test_ai_workflow_save_syncs_to_product_master_and_deduplicates():
    """Verify that saving an AI workflow syncs to product_master_col and avoids duplicate records."""
    app.dependency_overrides[get_current_user] = override_admin_user

    mock_products = {}
    mock_product_master = {}
    mock_workflow_steps = {}

    async def mock_pm_find_one(q, proj=None):
        if "id" in q:
            return mock_product_master.get(q["id"])
        if "$or" in q:
            for sub_q in q["$or"]:
                for doc in mock_product_master.values():
                    match = True
                    for k, v in sub_q.items():
                        if isinstance(v, dict) and "$regex" in v:
                            import re
                            if not re.search(v["$regex"], str(doc.get(k, "")), re.IGNORECASE):
                                match = False
                                break
                        elif doc.get(k) != v:
                            match = False
                            break
                    if match:
                        return doc
        return None

    async def mock_pm_update_one(filter_q, update_q, upsert=False):
        doc_id = filter_q.get("id") or filter_q.get("_id")
        set_vals = update_q.get("$set", {})
        if doc_id:
            existing = mock_product_master.get(doc_id, {})
            existing.update(set_vals)
            existing["id"] = doc_id
            mock_product_master[doc_id] = existing
        m = MagicMock()
        m.modified_count = 1
        return m

    async def mock_pm_insert_one(doc):
        mock_product_master[doc["id"]] = dict(doc)
        m = MagicMock()
        m.inserted_id = doc["id"]
        return m

    async def mock_prod_find_one(q, proj=None):
        if "id" in q:
            return mock_products.get(q["id"])
        if "$or" in q:
            for sub_q in q["$or"]:
                for doc in mock_products.values():
                    match = True
                    for k, v in sub_q.items():
                        if isinstance(v, dict) and "$regex" in v:
                            import re
                            if not re.search(v["$regex"], str(doc.get(k, "")), re.IGNORECASE):
                                match = False
                                break
                        elif doc.get(k) != v:
                            match = False
                            break
                    if match:
                        return doc
        return None

    async def mock_prod_update_one(filter_q, update_q, upsert=False):
        doc_id = filter_q.get("id") or filter_q.get("_id")
        set_vals = update_q.get("$set", {})
        if doc_id:
            existing = mock_products.get(doc_id, {})
            existing.update(set_vals)
            existing["id"] = doc_id
            mock_products[doc_id] = existing
        m = MagicMock()
        m.modified_count = 1
        return m

    async def mock_prod_insert_one(doc):
        mock_products[doc["id"]] = dict(doc)
        m = MagicMock()
        m.inserted_id = doc["id"]
        return m

    async def mock_ws_delete_many(q):
        pid = q.get("product_id")
        to_del = [k for k, v in mock_workflow_steps.items() if v.get("product_id") == pid]
        for k in to_del:
            del mock_workflow_steps[k]
        m = MagicMock()
        m.deleted_count = len(to_del)
        return m

    async def mock_ws_insert_one(doc):
        mock_workflow_steps[doc.get("id", str(len(mock_workflow_steps)))] = dict(doc)
        m = MagicMock()
        return m

    with patch("routers.ai_workflow_builder.product_master_col.find_one", side_effect=mock_pm_find_one), \
         patch("routers.ai_workflow_builder.product_master_col.update_one", side_effect=mock_pm_update_one), \
         patch("routers.ai_workflow_builder.product_master_col.insert_one", side_effect=mock_pm_insert_one), \
         patch("routers.ai_workflow_builder.products_col.find_one", side_effect=mock_prod_find_one), \
         patch("routers.ai_workflow_builder.products_col.update_one", side_effect=mock_prod_update_one), \
         patch("routers.ai_workflow_builder.products_col.insert_one", side_effect=mock_prod_insert_one), \
         patch("routers.ai_workflow_builder.workflow_steps_col.delete_many", side_effect=mock_ws_delete_many), \
         patch("routers.ai_workflow_builder.workflow_steps_col.insert_one", side_effect=mock_ws_insert_one), \
         patch("routers.ai_workflow_builder.log_activity", new=AsyncMock()):

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # First save: Australia Subclass 189
            req_payload = {
                "product_name": "Australia Skilled Independent Visa Subclass 189",
                "description": "Comprehensive points-based direct permanent residency pathway.",
                "country": "Australia",
                "visa_type": "Skilled Independent",
                "visa_subclass": "189",
                "category": "skilled_migration",
                "service_price": 175000,
                "estimated_government_fees": "AUD 4,765",
                "estimated_total_duration_days": 240,
                "steps": [
                    {
                        "step_order": 1,
                        "name": "Skills Assessment Lodgement",
                        "description": "Submit skills dossier to ACS / Engineers Australia",
                        "duration_days": 60,
                        "required_documents": [
                            {"name": "Valid Passport", "mandatory": True, "description": "Color scan of bio-data"},
                            {"name": "Degree Certificate", "mandatory": True, "description": "Attested graduation degree"}
                        ]
                    },
                    {
                        "step_order": 2,
                        "name": "Expression of Interest (EOI)",
                        "description": "Lodge SkillSelect EOI with minimum 65 points",
                        "duration_days": 30,
                        "required_documents": [
                            {"name": "IELTS / PTE Scorecard", "mandatory": True}
                        ]
                    }
                ]
            }

            res = await ac.post("/api/ai-workflow/save", json=req_payload, headers={"Authorization": "Bearer fake"})
            assert res.status_code == 200, res.text
            data = res.json()
            assert "product_id" in data
            assert data["product_name"] == req_payload["product_name"]
            assert data["checklists_created"] == 3
            assert data["steps_created"] == 2
            prod_id = data["product_id"]

            # Verify dual-save happened
            assert prod_id in mock_product_master
            assert prod_id in mock_products
            pm_doc = mock_product_master[prod_id]
            assert pm_doc["visa_subclass"] == "189"
            assert pm_doc["country"] == "Australia"
            assert len(pm_doc["document_checklist_template"]) == 3
            assert len(pm_doc["processing_timeline"]["stages"]) == 2

            # Now save again with updated duration to test deduplication:
            req_payload["estimated_total_duration_days"] = 270
            res2 = await ac.post("/api/ai-workflow/save", json=req_payload, headers={"Authorization": "Bearer fake"})
            assert res2.status_code == 200
            data2 = res2.json()
            # Must reuse existing product_id, not duplicate!
            assert data2["product_id"] == prod_id
            assert len(mock_product_master) == 1, "Duplicate record created in product_master!"
            assert len(mock_products) == 1, "Duplicate record created in products!"

    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_product_master_taxonomy_hierarchy():
    """Verify that /api/product-master/taxonomy returns country -> category -> subclass hierarchy."""
    app.dependency_overrides[get_current_user] = override_sales_user

    mock_items = [
        {"id": "pm-1", "name": "Australia Subclass 189", "country": "Australia", "category": "skilled_migration", "visa_subclass": "189", "status": "active", "last_verified_at": "2026-01-01"},
        {"id": "pm-2", "name": "Australia Subclass 190", "country": "Australia", "category": "skilled_migration", "visa_subclass": "190", "status": "active", "last_verified_at": None},
        {"id": "pm-3", "name": "Canada Express Entry FSW", "country": "Canada", "category": "skilled_migration", "visa_subclass": "FSW", "status": "active", "last_verified_at": "2026-02-01"},
    ]

    mock_cursor = MagicMock()
    mock_cursor.to_list = AsyncMock(return_value=mock_items)

    with patch("routers.product_master.product_master_col.find", return_value=mock_cursor), \
         patch("routers.product_master._sync_existing_products", new=AsyncMock()):

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/api/product-master/taxonomy", headers={"Authorization": "Bearer fake"})
            assert res.status_code == 200
            tax = res.json()["taxonomy"]

            assert "Australia" in tax
            assert "skilled_migration" in tax["Australia"]
            subclasses = [x["visa_subclass"] for x in tax["Australia"]["skilled_migration"]]
            assert "189" in subclasses
            assert "190" in subclasses

            assert "Canada" in tax
            assert "FSW" in [x["visa_subclass"] for x in tax["Canada"]["skilled_migration"]]

            # Verify structured countries array
            countries = res.json()["countries"]
            assert len(countries) >= 2
            au = next(c for c in countries if c["name"] == "Australia")
            assert au["country_code"] == "AU"
            assert au["total_subclasses"] == 2
            assert "skilled_migration" in au["categories"]
            assert au["categories"]["skilled_migration"]["count"] == 2

    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_canonical_seed_data_integrity():
    """Verify that canonical seed data contains all key countries and full statutory criteria."""
    from services.product_master_seed_data import get_canonical_seeds
    seeds = get_canonical_seeds()
    assert len(seeds) >= 10

    # Australia Subclass 189
    sc189 = next(s for s in seeds if s["id"] == "pm_australia_189")
    assert sc189["country"] == "Australia"
    assert sc189["visa_subclass"] == "189"
    assert sc189["category"] == "skilled_migration"
    assert sc189["authority_name"] == "Department of Home Affairs (DHA)"
    assert sc189["eligibility_criteria"]["points_based"]["minimum_points"] == 65
    assert len(sc189["document_checklist_template"]) >= 5
    assert any("Form 80" in d["document_name"] for d in sc189["document_checklist_template"])
    assert sc189["government_costs"]["currency"] == "AUD"
    assert sc189["government_costs"]["primary_applicant"] == 4770.0
    assert len(sc189["sales_playbook"]["pitch_points"]) >= 3

    # Canada FSW
    fsw = next(s for s in seeds if s["id"] == "pm_canada_fsw")
    assert fsw["country"] == "Canada"
    assert fsw["visa_subclass"] == "FSW"
    assert any("IMM 0008" in d["document_name"] for d in fsw["document_checklist_template"])

    # UK Skilled Worker
    uk = next(s for s in seeds if s["id"] == "pm_uk_skilled_worker")
    assert uk["country"] == "United Kingdom"
    assert uk["government_costs"]["currency"] == "GBP"

    # Germany Blue Card
    de = next(s for s in seeds if s["id"] == "pm_germany_blue_card")
    assert de["country"] == "Germany"
    assert any("VIDEX" in d["document_name"] for d in de["document_checklist_template"])

    # United States Seeds
    us_seeds = [s for s in seeds if s["country"] == "United States"]
    assert len(us_seeds) >= 6
    us_subclasses = {s["visa_subclass"] for s in us_seeds}
    assert {"H-1B", "L-1", "EB-1", "EB-2", "F-1", "B-1/B-2"}.issubset(us_subclasses)
    h1b = next(s for s in us_seeds if s["visa_subclass"] == "H-1B")
    assert "USCIS" in h1b["authority_name"]
    assert h1b["government_costs"]["currency"] == "USD"


@pytest.mark.asyncio
async def test_sales_ai_query_grounds_in_product_master():
    """Verify that /api/product-master/sales-ai-query grounds responses in Product Master and handles synthesis."""
    app.dependency_overrides[get_current_user] = override_sales_user

    mock_doc = {
        "id": "pm_australia_189",
        "name": "Australia Skilled Independent Visa",
        "country": "Australia",
        "visa_subclass": "189",
        "authority_name": "Department of Home Affairs (DHA)",
        "service_price": 125000,
        "government_costs": {"currency": "AUD", "primary_applicant": 4770.0},
        "eligibility_criteria": {"points_based": {"is_points_tested": True, "minimum_points": 65}},
        "sales_playbook": {"pitch_points": ["Direct Permanent Residency with Medicare."]},
        "objections_rebuttals": [{"objection": "Processing time is long", "rebuttal": "189 grants unconditional PR directly."}],
    }

    with patch("routers.product_master.product_master_col.find_one", new=AsyncMock(return_value=mock_doc)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(
                "/api/product-master/sales-ai-query",
                json={
                    "country": "Australia",
                    "visa_name": "Australia Skilled Independent Visa",
                    "visa_subclass": "189",
                    "client_scenario_or_question": "Client is 29 years old with 5 years experience, will they qualify for Subclass 189?",
                },
                headers={"Authorization": "Bearer fake"}
            )
            assert res.status_code == 200
            data = res.json()
            assert "answer" in data
            assert "model" in data
            # Check statutory grounded content in answer
            ans = data["answer"]
            assert "189" in ans or "Australia" in ans
            assert "Regulatory Fact Check" in ans or "Department of Home Affairs" in ans

    app.dependency_overrides.pop(get_current_user, None)



