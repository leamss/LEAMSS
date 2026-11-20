"""Tests for Dedicated Product Master Router (/api/product-master)."""
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


def override_staff_user():
    return {
        "id": "stf-001",
        "name": "Case Manager",
        "role": "case_manager",
        "email": "cm@leamss.com",
        "permissions": ["cases:read"]
    }


@pytest.mark.asyncio
async def test_non_admin_forbidden():
    app.dependency_overrides[get_current_user] = override_staff_user
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(
                "/api/product-master",
                headers={"Authorization": "Bearer fake_token"},
                json={"name": "Test Visa"}
            )
            assert res.status_code == 403

            res_ai = await ac.post(
                "/api/product-master/ai-research",
                headers={"Authorization": "Bearer fake_token"},
                json={"country": "Australia", "visa_name": "PR"}
            )
            assert res_ai.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_product_master_crud_verify_and_clone():
    app.dependency_overrides[get_current_user] = override_admin_user
    stored_master = {}
    stored_products = {}

    async def mock_master_insert(doc):
        stored_master[doc["id"]] = dict(doc)
        m = MagicMock()
        m.inserted_id = doc["id"]
        return m

    async def mock_master_find_one(q, projection=None):
        pid = q.get("id")
        doc = stored_master.get(pid)
        return dict(doc) if doc else None

    async def mock_master_update(q, update, upsert=False):
        pid = q.get("id")
        if pid in stored_master:
            if "$set" in update:
                stored_master[pid].update(update["$set"])
            m = MagicMock()
            m.matched_count = 1
            return m
        elif upsert:
            stored_master[pid] = dict(update.get("$set", {}))
            m = MagicMock()
            m.matched_count = 1
            return m
        m = MagicMock()
        m.matched_count = 0
        return m

    async def mock_master_count(q):
        status = q.get("status")
        if status == "active":
            return len([d for d in stored_master.values() if d.get("status") == "active"])
        if status == "draft":
            return len([d for d in stored_master.values() if d.get("status") == "draft"])
        if isinstance(status, dict) and "$ne" in status:
            return len([d for d in stored_master.values() if d.get("status") != status["$ne"]])
        return len(stored_master)

    async def mock_master_distinct(field, q):
        return list({d.get(field) for d in stored_master.values() if d.get(field)})

    mock_cursor = MagicMock()
    mock_cursor.sort.return_value.to_list = AsyncMock(side_effect=lambda length: list(stored_master.values()))

    try:
        with patch("routers.product_master.product_master_col.insert_one", side_effect=mock_master_insert), \
             patch("routers.product_master.product_master_col.find_one", side_effect=mock_master_find_one), \
             patch("routers.product_master.product_master_col.update_one", side_effect=mock_master_update), \
             patch("routers.product_master.product_master_col.find", return_value=mock_cursor), \
             patch("routers.product_master.product_master_col.count_documents", side_effect=mock_master_count), \
             patch("routers.product_master.product_master_col.distinct", side_effect=mock_master_distinct), \
             patch("routers.product_master.products_col.insert_one", new_callable=AsyncMock), \
             patch("routers.product_master.products_col.update_one", new_callable=AsyncMock), \
             patch("routers.product_master.workflow_steps_col.find", return_value=mock_cursor), \
             patch("routers.product_master._sync_existing_products", new_callable=AsyncMock), \
             patch("routers.product_master.log_activity", new_callable=AsyncMock):

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                # 1. Create Product Master
                payload = {
                    "name": "Australia Global Talent Visa (Subclass 858)",
                    "country": "Australia",
                    "category": "skilled_migration",
                    "visa_type": "Permanent Residency",
                    "visa_subclass": "858",
                    "service_price": 250000,
                    "summary": "Direct PR pathway for high-achieving individuals in target sectors.",
                    "migrate_page_url": "https://leamss.com/migrate/australia/858",
                    "official_urls": ["https://immi.homeaffairs.gov.au/visas/getting-a-visa/visa-listing/global-talent-visa-858"],
                    "official_domains": ["immi.homeaffairs.gov.au"],
                    "eligibility_criteria": {
                        "mandatory": [{"criterion": "International recognition", "description": "Prominent achievements in sector"}],
                        "optional": [],
                        "points_based": {"is_points_tested": False, "minimum_points": 0, "scoring_factors": []}
                    },
                    "government_costs": {
                        "currency": "AUD",
                        "line_items": [{"applicant_type": "Primary", "amount": 4710, "currency": "AUD", "inr_approx": 259050}],
                        "effective_date": "2025-07-01",
                        "source_link": "https://immi.homeaffairs.gov.au"
                    },
                    "sales_playbook": {
                        "target_client": "Senior researchers, tech leaders, PhD holders",
                        "pitch_points": ["Priority processing direct PR"],
                        "key_benefits": ["Permanent residency with no age cap in exceptional cases"]
                    },
                    "objections_rebuttals": [
                        {"objection": "Nominator requirement is difficult", "rebuttal": "We assist with peak national body identification"}
                    ],
                    "faqs": [
                        {"question": "Is salary threshold strict?", "answer": "Demonstrated ability to meet threshold is accepted"}
                    ],
                    "document_checklist_template": [
                        {"category": "Work Experience", "document_name": "International Awards", "required_for": "primary_applicant", "description": "Evidence of prominence"}
                    ]
                }

                create_res = await ac.post(
                    "/api/product-master",
                    headers={"Authorization": "Bearer fake_token"},
                    json=payload
                )
                assert create_res.status_code == 200
                pid = create_res.json()["id"]

                # 2. Get single product master
                get_res = await ac.get(
                    f"/api/product-master/{pid}",
                    headers={"Authorization": "Bearer fake_token"}
                )
                assert get_res.status_code == 200
                data = get_res.json()
                assert data["name"] == payload["name"]
                assert data["visa_subclass"] == "858"
                assert len(data["document_checklist_template"]) == 1

                # 3. Summary stats
                stats_res = await ac.get(
                    "/api/product-master/summary-stats",
                    headers={"Authorization": "Bearer fake_token"}
                )
                assert stats_res.status_code == 200
                stats = stats_res.json()
                assert stats["total"] >= 1

                # 4. List product masters
                list_res = await ac.get(
                    "/api/product-master",
                    headers={"Authorization": "Bearer fake_token"}
                )
                assert list_res.status_code == 200
                assert list_res.json()["count"] >= 1

                # 5. Verify Product Master
                verify_res = await ac.post(
                    f"/api/product-master/{pid}/verify",
                    headers={"Authorization": "Bearer fake_token"}
                )
                assert verify_res.status_code == 200
                assert "last_verified_at" in verify_res.json()
                assert stored_master[pid]["status"] == "active"

                # 6. Clone Product Master
                clone_res = await ac.post(
                    f"/api/product-master/{pid}/clone",
                    headers={"Authorization": "Bearer fake_token"}
                )
                assert clone_res.status_code == 200
                clone_id = clone_res.json()["id"]
                assert clone_id != pid
                assert "(Copy)" in clone_res.json()["name"]

                # 7. Archive / Soft-delete
                del_res = await ac.delete(
                    f"/api/product-master/{pid}",
                    headers={"Authorization": "Bearer fake_token"}
                )
                assert del_res.status_code == 200
                assert stored_master[pid]["status"] == "archived"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
