"""Unit and Integration Tests for Refund Policy Master in Admin Product Master.

Verifies:
  1. Default and custom refund policy structure (Protection Policy, Standard, No Refund).
  2. Component configuration: refundable service fee %, govt fees, GST treatment,
     negative skills assessment guarantee, visa refusal guarantee, claim window, payout SLA.
  3. Product Master update endpoint persists refund_policy and version.
  4. Sale confirmation snapshot: sale locks agreed refund policy; subsequent product edits do not alter confirmed sales.
  5. Maker-checker enforcement (Rule 6): refund initiator cannot approve payout.
  6. Finance Contingent Liability & Monthly Loss Report endpoint (/api/refunds/finance-report).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient, ASGITransport

from server import app
from core.database import db, product_master_col, products_col, sales_col, refunds_col, audit_logs_col
from core.auth import get_current_user


ADMIN_USER_A = {
    "id": "admin-refund-maker-01",
    "email": "admin.maker@leamss.com",
    "name": "Admin Maker",
    "role": "admin",
    "permissions": ["all"],
}

ADMIN_USER_B = {
    "id": "admin-refund-checker-02",
    "email": "admin.checker@leamss.com",
    "name": "Admin Checker",
    "role": "admin",
    "permissions": ["all"],
}

PARTNER_USER = {
    "id": "partner-seller-01",
    "email": "partner.sales@leamss.com",
    "name": "Partner Sales Rep",
    "role": "partner",
    "commission_rate": 15.0,
    "permissions": ["sales.create", "sales.read"],
}

CLIENT_USER = {
    "id": "client-user-01",
    "email": "client@example.com",
    "name": "Client User",
    "role": "client",
    "permissions": [],
}


@pytest.fixture(autouse=True)
async def cleanup_test_records():
    """Cleanup test records before and after tests."""
    yield
    test_ids = ["test-prod-refund-01", "test-prod-refund-02"]
    await product_master_col.delete_many({"id": {"$in": test_ids}})
    await products_col.delete_many({"id": {"$in": test_ids}})
    await sales_col.delete_many({"partner_id": {"$in": [PARTNER_USER["id"], ADMIN_USER_A["id"]]}})
    await refunds_col.delete_many({"initiated_by": {"$in": [ADMIN_USER_A["id"], ADMIN_USER_B["id"]]}})


@pytest.mark.asyncio
async def test_default_refund_policy_configuration():
    """Test creating product master without explicit policy assigns default Protection Policy."""
    prod_id = "test-prod-refund-01"
    
    app.dependency_overrides[get_current_user] = lambda: ADMIN_USER_A
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.post("/api/product-master", json={
                "id": prod_id,
                "name": "Australia Subclass 189 Skilled Independent",
                "country": "Australia",
                "visa_type": "Permanent Residency",
                "visa_subclass": "189",
                "service_price": 150000,
            })
            assert res.status_code == 200, res.text
            
            # Fetch from DB
            doc = await product_master_col.find_one({"id": prod_id}, {"_id": 0})
            assert doc is not None
            assert "refund_policy" in doc
            pol = doc["refund_policy"]
            assert pol["enabled"] is True
            assert pol["policy_type"] == "protection"
            assert pol["refundable_service_fee_pct"] == 100
            assert pol["is_service_fee_refundable"] is True
            assert pol["govt_fees_handling"] == "non_refundable"
            assert pol["gst_treatment"] == "credit_note"
            assert pol["negative_skills_assessment_guarantee"] is True
            assert pol["visa_refusal_guarantee"] is True
            assert pol["voluntary_withdrawal_milestones"] is True
            assert pol["claim_window_days"] == 30
            assert pol["payout_time_days"] == 14
            assert len(pol["conditions"]) >= 2
            assert len(pol["exclusions"]) >= 3
            assert "standard" in pol["package_overrides"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_update_product_master_refund_policy():
    """Test updating product master with custom refund policy and disabling policy."""
    prod_id = "test-prod-refund-02"
    
    # Pre-insert product
    await product_master_col.insert_one({
        "id": prod_id,
        "name": "Canada Express Entry Federal Skilled Worker",
        "country": "Canada",
        "visa_type": "Permanent Residency",
        "visa_subclass": "FSW",
        "service_price": 120000,
        "version": 1,
        "refund_policy": {
            "enabled": True,
            "policy_type": "protection",
            "refundable_service_fee_pct": 100,
        }
    })
    
    app.dependency_overrides[get_current_user] = lambda: ADMIN_USER_A
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # Update to standard milestone policy with 70% refund
            custom_policy = {
                "enabled": True,
                "policy_type": "standard",
                "name": "Tiered Milestone Refund Policy",
                "refundable_service_fee_pct": 70,
                "is_service_fee_refundable": True,
                "govt_fees_handling": "non_refundable",
                "gst_treatment": "credit_note",
                "negative_skills_assessment_guarantee": True,
                "visa_refusal_guarantee": False,
                "claim_window_days": 45,
                "payout_time_days": 10,
                "custom_fee_components": [
                    {"id": "fee_1", "name": "Admin File Charge", "type": "deduct_flat", "value": 15000, "description": "Processing fee"}
                ],
                "custom_guaranteed_triggers": [
                    {"id": "trig_1", "name": "State Nomination Rejection Guarantee", "enabled": True, "refund_pct": 100, "description": "State EOI rejection"}
                ],
                "package_overrides": {
                    "standard": {"name": "Standard Tier", "enabled": True, "refundable_pct": 70},
                    "custom_pkg_1": {"name": "Executive VIP Tier", "enabled": True, "refundable_pct": 100, "is_custom": True}
                },
                "version": 2
            }
            res = await ac.put(f"/api/product-master/{prod_id}", json={
                "refund_policy": custom_policy
            })
            assert res.status_code == 200, res.text
            
            # Check DB updated
            updated = await product_master_col.find_one({"id": prod_id}, {"_id": 0})
            assert updated["refund_policy"]["policy_type"] == "standard"
            assert updated["refund_policy"]["refundable_service_fee_pct"] == 70
            assert updated["refund_policy"]["claim_window_days"] == 45
            assert len(updated["refund_policy"]["custom_fee_components"]) == 1
            assert updated["refund_policy"]["custom_fee_components"][0]["name"] == "Admin File Charge"
            assert len(updated["refund_policy"]["custom_guaranteed_triggers"]) == 1
            assert updated["refund_policy"]["custom_guaranteed_triggers"][0]["name"] == "State Nomination Rejection Guarantee"
            assert "custom_pkg_1" in updated["refund_policy"]["package_overrides"]
            assert updated["refund_policy"]["package_overrides"]["custom_pkg_1"]["name"] == "Executive VIP Tier"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_sale_creation_locks_refund_policy():
    """Test that creating a sale snapshots locked_refund_policy which remains unchanged if product master is edited."""
    prod_id = "test-prod-refund-01"
    
    # Seed product with Protection Policy
    initial_policy = {
        "enabled": True,
        "policy_type": "protection",
        "refundable_service_fee_pct": 100,
        "negative_skills_assessment_guarantee": True,
        "visa_refusal_guarantee": True,
        "claim_window_days": 30,
        "version": 1
    }
    await product_master_col.update_one(
        {"id": prod_id},
        {"$set": {
            "id": prod_id,
            "name": "Australia 189",
            "service_price": 150000,
            "base_fee": 150000,
            "refund_policy": initial_policy
        }},
        upsert=True
    )
    await products_col.update_one(
        {"id": prod_id},
        {"$set": {
            "id": prod_id,
            "name": "Australia 189",
            "service_price": 150000,
            "base_fee": 150000,
            "refund_policy": initial_policy
        }},
        upsert=True
    )
    
    # Create sale as partner
    app.dependency_overrides[get_current_user] = lambda: PARTNER_USER
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.post("/api/sales", data={
                "client_name": "Rohan Deshmukh",
                "client_email": "rohan.deshmukh@example.com",
                "client_mobile": "+919876543210",
                "product_id": prod_id,
                "fee_amount": 150000,
                "amount_received": 60000,
                "payment_method": "upi",
                "payment_reference": "UPI-123456",
                "bypass_pre_assessment": "true",
                "bypass_reason": "Walk-in client with verified docs",
            })
            assert res.status_code == 200, res.text
            sale_data = res.json()
            sale_id = sale_data["id"]
            
            # Verify locked_refund_policy in sale record
            sale_doc = await sales_col.find_one({"id": sale_id}, {"_id": 0})
            assert sale_doc is not None
            assert "locked_refund_policy" in sale_doc
            assert sale_doc["locked_refund_policy"]["policy_type"] == "protection"
            assert sale_doc["locked_refund_policy"]["refundable_service_fee_pct"] == 100
            assert "policy_locked_at" in sale_doc
            
            # Now alter product master to "no_refund"
            await product_master_col.update_one(
                {"id": prod_id},
                {"$set": {"refund_policy": {"enabled": False, "policy_type": "no_refund", "refundable_service_fee_pct": 0}}}
            )
            
            # Re-read sale: the sale's policy MUST remain 100% Protection Policy (immutable snapshot)
            sale_after_edit = await sales_col.find_one({"id": sale_id}, {"_id": 0})
            assert sale_after_edit["locked_refund_policy"]["policy_type"] == "protection"
            assert sale_after_edit["locked_refund_policy"]["refundable_service_fee_pct"] == 100
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_maker_checker_enforcement_on_refund():
    """Test Maker-Checker (Rule 6): Admin A who initiates refund cannot approve it; Admin B can approve."""
    # Create test sale
    sale_id = f"test-sale-{uuid.uuid4()}"
    await sales_col.insert_one({
        "id": sale_id,
        "partner_id": PARTNER_USER["id"],
        "client_name": "Amit Sharma",
        "client_email": "amit@example.com",
        "fee_amount": 100000,
        "amount_received": 100000,
        "pending_amount": 0,
        "commission_rate": 10.0,
        "commission_amount": 10000,
        "status": "approved",
        "payment_status": "paid",
        "created_at": datetime.now(timezone.utc)
    })
    
    # 1. Admin A initiates refund
    app.dependency_overrides[get_current_user] = lambda: ADMIN_USER_A
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            init_res = await ac.post("/api/refunds", json={
                "sale_id": sale_id,
                "amount": 50000,
                "reason": "Negative skills assessment outcome under Protection Policy guarantee",
                "category": "service_issue",
                "refund_method": "original_payment"
            })
            assert init_res.status_code == 200, init_res.text
            refund_id = init_res.json()["refund_id"]
            
            # 2. Admin A attempts to self-approve -> MUST BE REJECTED (403 Maker-checker violation)
            self_approve_res = await ac.post("/api/refunds/review", json={
                "refund_id": refund_id,
                "action": "approve",
                "review_notes": "Self approving my refund"
            })
            assert self_approve_res.status_code == 403
            assert "Maker-checker violation" in self_approve_res.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        
    # 3. Admin B reviews and approves -> MUST SUCCEED (200 OK)
    app.dependency_overrides[get_current_user] = lambda: ADMIN_USER_B
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            approve_res = await ac.post("/api/refunds/review", json={
                "refund_id": refund_id,
                "action": "approve",
                "review_notes": "Verified assessment outcome letter. Approving 50k refund."
            })
            assert approve_res.status_code == 200, approve_res.text
            
            # Check sale balance recalculated
            updated_sale = await sales_col.find_one({"id": sale_id}, {"_id": 0})
            assert updated_sale["amount_received"] == 50000
            assert updated_sale["pending_amount"] == 50000
            assert updated_sale["commission_amount"] == 5000  # 10% of 50k
            assert updated_sale["payment_status"] == "partial"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_finance_report_endpoint():
    """Test GET /api/refunds/finance-report computes contingent liabilities and monthly losses."""
    app.dependency_overrides[get_current_user] = lambda: ADMIN_USER_A
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.get("/api/refunds/finance-report")
            assert res.status_code == 200, res.text
            data = res.json()
            assert "summary" in data
            summary = data["summary"]
            assert "total_refund_contingent_liability" in summary
            assert "total_actual_loss_to_date" in summary
            assert "protection_coverage_count" in summary
            assert "monthly_losses" in data
            assert isinstance(data["monthly_losses"], list)
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        
    # Check non-admin/non-finance role is blocked
    app.dependency_overrides[get_current_user] = lambda: CLIENT_USER
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.get("/api/refunds/finance-report")
            assert res.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_independent_policy_type_percentages_persistence():
    """Test that Protection Policy (90%) and Standard Policy (80%) maintain independent percentages in DB."""
    prod_id = f"test_prod_dual_{uuid.uuid4().hex[:8]}"
    await product_master_col.insert_one({
        "id": prod_id,
        "name": "Independent Policy Test Product",
        "country": "Australia",
        "visa_type": "Skilled Independent",
        "visa_subclass": "189",
        "service_price": 100000,
        "version": 1,
        "refund_policy": {
            "enabled": True,
            "policy_type": "protection",
            "refundable_service_fee_pct": 100,
        }
    })

    app.dependency_overrides[get_current_user] = lambda: ADMIN_USER_A
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # 1. Update with Protection = 90% and Standard = 80% stored in policy_type_configs
            policy_payload = {
                "enabled": True,
                "policy_type": "standard",
                "name": "LEAMSS Milestone-Based Refund Policy",
                "refundable_service_fee_pct": 80,
                "is_service_fee_refundable": True,
                "package_overrides": {
                    "standard": {"name": "Standard Tier", "enabled": True, "refundable_pct": 80},
                    "smart": {"name": "Smart Tier", "enabled": True, "refundable_pct": 80},
                    "premium": {"name": "Premium Tier", "enabled": True, "refundable_pct": 80}
                },
                "policy_type_configs": {
                    "protection": {
                        "refundable_service_fee_pct": 90,
                        "is_service_fee_refundable": True,
                        "negative_skills_assessment_guarantee": True,
                        "visa_refusal_guarantee": True,
                        "package_overrides": {
                            "standard": {"name": "Standard Tier", "enabled": True, "refundable_pct": 90},
                            "smart": {"name": "Smart Tier", "enabled": True, "refundable_pct": 90},
                            "premium": {"name": "Premium Tier", "enabled": True, "refundable_pct": 90}
                        }
                    },
                    "standard": {
                        "refundable_service_fee_pct": 80,
                        "is_service_fee_refundable": True,
                        "negative_skills_assessment_guarantee": True,
                        "visa_refusal_guarantee": False,
                        "package_overrides": {
                            "standard": {"name": "Standard Tier", "enabled": True, "refundable_pct": 80},
                            "smart": {"name": "Smart Tier", "enabled": True, "refundable_pct": 80},
                            "premium": {"name": "Premium Tier", "enabled": True, "refundable_pct": 80}
                        }
                    },
                    "no_refund": {
                        "refundable_service_fee_pct": 0,
                        "is_service_fee_refundable": False,
                        "negative_skills_assessment_guarantee": False,
                        "visa_refusal_guarantee": False,
                    }
                }
            }

            res = await ac.put(f"/api/product-master/{prod_id}", json={
                "refund_policy": policy_payload
            })
            assert res.status_code == 200, res.text

            # 2. Check DB document has active 80% for standard AND retained 90% for protection
            doc = await product_master_col.find_one({"id": prod_id}, {"_id": 0})
            assert doc["refund_policy"]["policy_type"] == "standard"
            assert doc["refund_policy"]["refundable_service_fee_pct"] == 80
            assert doc["refund_policy"]["policy_type_configs"]["standard"]["refundable_service_fee_pct"] == 80
            assert doc["refund_policy"]["policy_type_configs"]["protection"]["refundable_service_fee_pct"] == 90

            # 3. Now switch active to Protection Policy (90%) and save
            policy_payload["policy_type"] = "protection"
            policy_payload["refundable_service_fee_pct"] = 90
            policy_payload["name"] = "LEAMSS Protection Policy Guarantee"
            policy_payload["package_overrides"] = {
                "standard": {"name": "Standard Tier", "enabled": True, "refundable_pct": 90},
                "smart": {"name": "Smart Tier", "enabled": True, "refundable_pct": 90},
                "premium": {"name": "Premium Tier", "enabled": True, "refundable_pct": 90}
            }

            res2 = await ac.put(f"/api/product-master/{prod_id}", json={
                "refund_policy": policy_payload
            })
            assert res2.status_code == 200, res2.text

            doc2 = await product_master_col.find_one({"id": prod_id}, {"_id": 0})
            assert doc2["refund_policy"]["policy_type"] == "protection"
            assert doc2["refund_policy"]["refundable_service_fee_pct"] == 90
            assert doc2["refund_policy"]["policy_type_configs"]["standard"]["refundable_service_fee_pct"] == 80
            assert doc2["refund_policy"]["policy_type_configs"]["protection"]["refundable_service_fee_pct"] == 90
    finally:
        app.dependency_overrides.pop(get_current_user, None)

