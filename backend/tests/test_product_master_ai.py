"""Tests for Product Master Module A AI Research and Verification endpoints."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport
from server import app
from core.auth import get_current_user


def override_admin_user():
    return {
        "id": "adm-001",
        "name": "Admin Tester",
        "role": "admin",
        "email": "admin@leamss.com",
        "permissions": ["*"]
    }


def override_staff_user():
    return {
        "id": "stf-001",
        "name": "Sales Rep",
        "role": "sales",
        "email": "sales@leamss.com",
        "permissions": ["leads:read"]
    }


@pytest.mark.asyncio
async def test_ai_research_endpoint_forbidden_for_non_admin():
    app.dependency_overrides[get_current_user] = override_staff_user
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(
                "/api/products/ai-research",
                headers={"Authorization": "Bearer fake_token"},
                json={
                    "country": "Australia",
                    "visa_name": "Skilled Independent 189"
                }
            )
            assert res.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_ai_research_endpoint_success():
    app.dependency_overrides[get_current_user] = override_admin_user
    mock_product = {
        "name": "Australia Skilled Independent Visa (Subclass 189)",
        "country": "Australia",
        "category": "skilled_migration",
        "visa_subclass": "189",
        "summary": "Permanent residency visa for invited points-tested workers.",
        "official_urls": ["https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/skilled-independent-189"],
        "official_domains": ["immi.homeaffairs.gov.au"],
        "eligibility_criteria": {
            "mandatory": [{"criterion": "Age under 45", "description": "Must be under 45"}],
            "optional": [],
            "points_based": {"is_points_tested": True, "minimum_points": 65, "scoring_factors": []}
        },
        "visa_conditions": ["Permanent Resident"],
        "government_costs": {
            "currency": "AUD",
            "line_items": [{"applicant_type": "Primary Applicant", "amount": 4765, "currency": "AUD", "inr_approx": 262075}],
            "effective_date": "2025-07-01",
            "source_link": "https://immi.homeaffairs.gov.au"
        },
        "processing_timeline": {"standard_duration": "6-12 months", "stages": []},
        "sales_playbook": {"target_client": "IT and Engineering professionals", "pitch_points": ["Direct PR"], "key_benefits": ["Full work rights"]},
        "objections_rebuttals": [{"objection": "Too expensive", "rebuttal": "Direct lifetime benefit"}],
        "faqs": [{"question": "Can family join?", "answer": "Yes"}],
        "document_checklist_template": [{"category": "Identity", "document_name": "Passport", "required_for": "all_applicants", "description": "Valid passport"}],
        "info_sheet_sections": [{"section_key": "personal", "title": "Personal Details", "required": True}],
        "_ai_generated": True,
        "_ai_model": "sonar-pro",
        "status": "draft"
    }

    try:
        with patch("services.product_master_ai_service.research_product_with_ai", new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = mock_product
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                res = await ac.post(
                    "/api/products/ai-research",
                    headers={"Authorization": "Bearer fake_token"},
                    json={
                        "country": "Australia",
                        "visa_name": "Skilled Independent 189",
                        "category": "skilled_migration",
                        "visa_subclass": "189",
                        "government_url": "https://immi.homeaffairs.gov.au",
                        "migrate_page_url": "https://leamss.com/migrate/australia/189"
                    }
                )
                assert res.status_code == 200
                data = res.json()
                assert data["name"] == mock_product["name"]
                assert data["government_costs"]["currency"] == "AUD"
                assert len(data["document_checklist_template"]) == 1
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_product_master_create_verify_and_get():
    app.dependency_overrides[get_current_user] = override_admin_user
    stored_docs = {}

    async def mock_insert_one(doc):
        stored_docs[doc["id"]] = dict(doc)
        m = MagicMock()
        m.inserted_id = doc["id"]
        return m

    async def mock_find_one(q, projection=None):
        pid = q.get("id")
        doc = stored_docs.get(pid)
        return dict(doc) if doc else None

    async def mock_update_one(q, update):
        pid = q.get("id")
        if pid in stored_docs:
            if "$set" in update:
                stored_docs[pid].update(update["$set"])
            m = MagicMock()
            m.matched_count = 1
            return m
        m = MagicMock()
        m.matched_count = 0
        return m

    mock_wf_cursor = MagicMock()
    mock_wf_cursor.sort.return_value.to_list = AsyncMock(return_value=[])

    try:
        with patch("routers.products.products_col.insert_one", side_effect=mock_insert_one), \
             patch("routers.products.products_col.find_one", side_effect=mock_find_one), \
             patch("routers.products.products_col.update_one", side_effect=mock_update_one), \
             patch("routers.products.workflow_steps_col.find", return_value=mock_wf_cursor), \
             patch("routers.products.log_activity", new_callable=AsyncMock):

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                payload = {
                    "name": "Canada Express Entry FSW Test",
                    "country": "Canada",
                    "category": "skilled_migration",
                    "visa_type": "Permanent Residency",
                    "visa_subclass": "FSW",
                    "service_price": 150000,
                    "summary": "Federal Skilled Worker program test",
                    "migrate_page_url": "https://leamss.com/migrate/canada/express-entry",
                    "official_urls": ["https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry.html"],
                    "official_domains": ["canada.ca"],
                    "eligibility_criteria": {
                        "mandatory": [{"criterion": "CLB 7", "description": "Minimum language score"}],
                        "optional": [],
                        "points_based": {"is_points_tested": True, "minimum_points": 67, "scoring_factors": []}
                    },
                    "government_costs": {
                        "currency": "CAD",
                        "line_items": [{"applicant_type": "Primary", "amount": 1525, "currency": "CAD", "inr_approx": 94550}],
                        "effective_date": "2025-05-01",
                        "source_link": "https://www.canada.ca"
                    },
                    "sales_playbook": {
                        "target_client": "Educated professionals",
                        "pitch_points": ["Fast-track Canadian PR"],
                        "key_benefits": ["Free healthcare"]
                    },
                    "objections_rebuttals": [
                        {"objection": "CRS cut-offs are high", "rebuttal": "Category-based draws offer lower thresholds"}
                    ],
                    "faqs": [
                        {"question": "How long does it take?", "answer": "6 months after ITA"}
                    ],
                    "document_checklist_template": [
                        {"category": "Education", "document_name": "ECA Report", "required_for": "primary_applicant", "description": "WES/IQAS evaluation"}
                    ]
                }

                create_res = await ac.post(
                    "/api/products",
                    headers={"Authorization": "Bearer fake_token"},
                    json=payload
                )
                assert create_res.status_code == 200
                prod_id = create_res.json()["id"]

                # Fetch product
                get_res = await ac.get(
                    f"/api/products/{prod_id}",
                    headers={"Authorization": "Bearer fake_token"}
                )
                assert get_res.status_code == 200
                prod_data = get_res.json()
                assert prod_data["summary"] == payload["summary"]
                assert prod_data["migrate_page_url"] == payload["migrate_page_url"]
                assert prod_data["government_costs"]["currency"] == "CAD"
                assert len(prod_data["objections_rebuttals"]) == 1

                # Verify product
                verify_res = await ac.post(
                    f"/api/products/{prod_id}/verify",
                    headers={"Authorization": "Bearer fake_token"}
                )
                assert verify_res.status_code == 200
                assert "last_verified_at" in verify_res.json()
    finally:
        app.dependency_overrides.pop(get_current_user, None)
