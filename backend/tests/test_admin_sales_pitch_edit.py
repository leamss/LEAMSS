"""Tests for Admin Sales Pitch Editing and Role Enforcement in Product Master."""
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
        "name": "Consultant Jane",
        "role": "salesperson",
        "email": "sales@leamss.com",
        "permissions": ["lead.view.own"]
    }


@pytest.mark.asyncio
async def test_admin_can_update_sales_pitch():
    """Verify that an Admin can edit sales pitch writing and objection rebuttals."""
    app.dependency_overrides[get_current_user] = override_admin_user

    mock_product = {
        "id": "pm_au_190",
        "name": "Australia Subclass 190",
        "country": "Australia",
        "visa_subclass": "190",
        "sales_playbook": {
            "elevator_pitch": "Old pitch text.",
            "discovery_questions": ["Old question 1?"],
            "usps": ["Old USP"],
            "target_client": "General"
        },
        "objections_rebuttals": [
            {"objection": "Old objection", "rebuttal": "Old rebuttal"}
        ]
    }

    async def mock_find_one(q, proj=None):
        if q.get("id") == "pm_au_190":
            return dict(mock_product)
        return None

    async def mock_update_one(filter_q, update_q, upsert=False):
        set_vals = update_q.get("$set", {})
        if "sales_playbook" in set_vals:
            mock_product["sales_playbook"] = set_vals["sales_playbook"]
        if "objections_rebuttals" in set_vals:
            mock_product["objections_rebuttals"] = set_vals["objections_rebuttals"]
        if "government_costs" in set_vals:
            mock_product["government_costs"] = set_vals["government_costs"]
        if "document_checklist_template" in set_vals:
            mock_product["document_checklist_template"] = set_vals["document_checklist_template"]
        if "faqs" in set_vals:
            mock_product["faqs"] = set_vals["faqs"]
        res = MagicMock()
        res.matched_count = 1
        return res

    with patch("routers.product_master.product_master_col.find_one", side_effect=mock_find_one), \
         patch("routers.product_master.product_master_col.update_one", side_effect=mock_update_one), \
         patch("routers.product_master.products_col.find_one", side_effect=mock_find_one), \
         patch("routers.product_master.products_col.update_one", side_effect=mock_update_one), \
         patch("routers.product_master.log_activity", new_callable=AsyncMock):

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            patch_payload = {
                "elevator_pitch": "Updated 30-second elevator pitch written by Admin: Guaranteed direct Australian PR from Day 1.",
                "pitch_points": ["Direct PR", "Medicare access", "State nomination sponsorship"],
                "target_audience": "Senior IT and Healthcare Professionals under 45",
                "usps": [
                    "Direct PR visa with full work and study rights from day 1",
                    "Medicare public healthcare included"
                ],
                "discovery_questions": [
                    "What is your current points breakdown for Australia?",
                    "Have you completed your skills assessment?"
                ],
                "objections_rebuttals": [
                    {
                        "objection": "Consultancy fee is too expensive compared to local agents.",
                        "rebuttal": "We provide end-to-end MARA-supervised legal representation and document vetting."
                    }
                ],
                "government_costs": {
                    "currency": "AUD",
                    "primary_applicant": 4770,
                    "secondary_applicant_adult": 2385,
                    "secondary_applicant_child": 1190
                },
                "document_checklist_template": [
                    {"document_name": "Valid Passport", "description": "Color bio-data copy"},
                    {"document_name": "Degree Transcripts", "description": "Consolidated marks"}
                ],
                "faqs": [
                    {"question": "Can I bring my family?", "answer": "Yes, spouse and children receive PR."}
                ]
            }

            resp = await ac.patch("/api/product-master/pm_au_190/sales-pitch", json=patch_payload)
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
            data = resp.json()
            assert data["message"] == "Sales pitch updated successfully"
            assert data["product"]["sales_playbook"]["elevator_pitch"] == patch_payload["elevator_pitch"]
            assert len(data["product"]["sales_playbook"]["discovery_questions"]) == 2
            assert len(data["product"]["objections_rebuttals"]) == 1
            assert data["product"]["objections_rebuttals"][0]["objection"] == "Consultancy fee is too expensive compared to local agents."
            assert data["product"]["government_costs"]["primary_applicant"] == 4770
            assert len(data["product"]["document_checklist_template"]) == 2
            assert len(data["product"]["faqs"]) == 1
            assert data["product"]["faqs"][0]["question"] == "Can I bring my family?"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_salesperson_cannot_update_sales_pitch():
    """Verify that a Salesperson / non-admin receives 403 Forbidden when trying to edit the pitch."""
    app.dependency_overrides[get_current_user] = override_sales_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        patch_payload = {
            "elevator_pitch": "Unauthorized pitch change."
        }
        resp = await ac.patch("/api/product-master/pm_au_190/sales-pitch", json=patch_payload)
        assert resp.status_code == 403, f"Expected 403 Forbidden for salesperson, got {resp.status_code}"
        assert "Admin authorization required" in resp.text

    app.dependency_overrides.clear()
