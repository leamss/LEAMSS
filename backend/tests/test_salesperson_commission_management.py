"""Automated Test Suite for Salesperson Incentive & Commission Management.

Covers:
1. Automatic salesperson discovery: Newly created salesperson appears in Admin Commission Management.
2. Admin individual rate configuration: Switching between tiered slabs and flat percentage with history & audit logs.
3. Automatic commission calculation on verified CRM payments.
4. Duplicate prevention & idempotency.
5. Salesperson view-only security: Rep can only view /my and is blocked (403) from Admin endpoints.
6. Maker-checker and payout lifecycle: Pending -> Approved -> Paid (with transaction ref) -> Reversed.
"""
import uuid
from datetime import datetime, timezone
import pytest
from httpx import ASGITransport, AsyncClient

from server import app
from core.database import db, users_col
from core.auth import create_access_token, get_password_hash
from core.commission_logic import (
    slabs_col, entries_col, ensure_default_slabs,
    apply_commission_for_crm_payment,
)


@pytest.fixture(autouse=True)
async def setup_data():
    """Ensure default slabs exist and cleanup test entities after run."""
    await ensure_default_slabs()
    yield
    # Cleanup test entries created during tests
    await entries_col.delete_many({"user_id": {"$regex": "^test_sales_"}})
    await users_col.delete_many({"id": {"$regex": "^test_sales_"}})
    await db["audit_logs"].delete_many({"entity_id": {"$regex": "^test_sales_"}})


def _token_for(user: dict) -> str:
    return create_access_token(data={
        "sub": user["id"],
        "id": user["id"],
        "email": user["email"],
        "role": user.get("role", "sales_executive"),
        "rbac_role": user.get("rbac_role", "sales_executive"),
        "permissions": user.get("permissions", []),
    })


@pytest.mark.asyncio
async def test_salesperson_commission_full_lifecycle():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create an Admin user and a Sales Executive
        admin_id = f"test_sales_admin_{uuid.uuid4().hex[:6]}"
        admin_user = {
            "id": admin_id,
            "email": f"{admin_id}@leamss.com",
            "name": "Super Admin",
            "role": "admin",
            "rbac_role": "admin",
            "password": get_password_hash("Admin@123"),
            "status": "active",
            "permissions": ["*"],
            "created_at": datetime.now(timezone.utc),
        }
        await users_col.insert_one(admin_user)
        admin_tok = _token_for(admin_user)
        admin_hdr = {"Authorization": f"Bearer {admin_tok}"}

        # 2. Admin creates a new salesperson via /api/users
        rep_id = f"test_sales_rep_{uuid.uuid4().hex[:6]}"
        rep_email = f"{rep_id}@leamss.com"
        create_resp = await client.post(
            "/api/users",
            headers=admin_hdr,
            json={
                "id": rep_id,
                "email": rep_email,
                "name": "Rajesh Sharma",
                "role": "sales_executive",
                "rbac_role": "sales_executive",
                "department": "sales",
            }
        )
        assert create_resp.status_code == 200, create_resp.text
        created_user_id = create_resp.json()["id"]

        # 3. Verify newly created salesperson auto-appears in /api/sales-commission/salespersons
        list_resp = await client.get("/api/sales-commission/salespersons", headers=admin_hdr)
        assert list_resp.status_code == 200
        salespersons = list_resp.json()["salespersons"]
        matching = next((sp for sp in salespersons if sp["id"] == created_user_id), None)
        assert matching is not None, "Newly created salesperson must automatically appear in commission list"
        assert matching["name"] == "Rajesh Sharma"
        assert matching["deal_count"] == 0
        assert matching["total_revenue"] == 0
        assert matching["total_commission"] == 0
        assert matching["commission_mode"] == "slab"
        assert matching["is_commission_active"] is True

        # 4. Admin configures individual flat commission rate for this salesperson
        config_resp = await client.put(
            f"/api/sales-commission/salespersons/{created_user_id}/config",
            headers=admin_hdr,
            json={
                "commission_mode": "flat",
                "commission_rate": 8.5,
                "is_commission_active": True,
                "reason": "Special Senior Incentive Agreement",
            }
        )
        assert config_resp.status_code == 200, config_resp.text
        assert config_resp.json()["ok"] is True

        # Verify updated salesperson configuration
        list_resp2 = await client.get("/api/sales-commission/salespersons", headers=admin_hdr)
        matching2 = next(sp for sp in list_resp2.json()["salespersons"] if sp["id"] == created_user_id)
        assert matching2["commission_mode"] == "flat"
        assert matching2["commission_rate"] == 8.5
        assert matching2["effective_rate_pct"] == 8.5

        # Verify audit log exists
        audit_log = await db["audit_logs"].find_one({
            "action": "salesperson_commission_config_updated",
            "entity_id": created_user_id,
        })
        assert audit_log is not None
        assert audit_log["details"]["new_rate"] == 8.5

        # 5. Record a verified CRM payment for this salesperson
        payment_doc = {
            "id": f"pay_{uuid.uuid4().hex[:8]}",
            "receipt_number": "RCP-202611-TEST01",
            "sales_person_id": created_user_id,
            "sales_person_name": "Rajesh Sharma",
            "client_name": "Acme Corp Visa Client",
            "paid_amount": 200000.0,
            "payment_status": "paid",
            "transaction_id": "TXN-BANK-0091",
            "created_at": datetime.now(timezone.utc),
        }
        entry = await apply_commission_for_crm_payment(payment_doc)
        assert entry is not None
        # 8.5% of 200,000 = 17,000.0
        assert entry["commission_amount"] == 17000.0
        assert entry["rate_pct"] == 8.5
        assert entry["rate_mode"] == "flat"
        assert entry["status"] == "pending"

        # 6. Test Idempotency: Duplicate payment trigger does NOT create duplicate entries
        duplicate_entry = await apply_commission_for_crm_payment(payment_doc)
        assert duplicate_entry["id"] == entry["id"], "Must return existing entry on duplicate call"
        entry_count = await entries_col.count_documents({"source_id": payment_doc["id"]})
        assert entry_count == 1, "Must not have duplicate entries for same payment"

        # 7. Salesperson View-Only Security
        rep_db_user = await users_col.find_one({"id": created_user_id})
        rep_tok = _token_for(rep_db_user)
        rep_hdr = {"Authorization": f"Bearer {rep_tok}"}

        # Salesperson CAN view their own commission
        my_resp = await client.get("/api/sales-commission/my", headers=rep_hdr)
        assert my_resp.status_code == 200
        my_data = my_resp.json()
        assert my_data["total_commission"] == 17000.0
        assert my_data["pending"] == 17000.0
        assert my_data["paid"] == 0
        assert len(my_data["entries"]) == 1

        # Salesperson CANNOT view admin salespersons list (403)
        sp_forbidden = await client.get("/api/sales-commission/salespersons", headers=rep_hdr)
        assert sp_forbidden.status_code == 403

        # Salesperson CANNOT configure rates (403)
        sp_put_forbidden = await client.put(
            f"/api/sales-commission/salespersons/{created_user_id}/config",
            headers=rep_hdr,
            json={"commission_rate": 15.0}
        )
        assert sp_put_forbidden.status_code == 403

        # 8. Maker-Checker: User cannot approve their own commission
        # If rep attempts to approve entry -> 403
        self_approve = await client.post(f"/api/sales-commission/entries/{entry['id']}/approve", headers=rep_hdr)
        assert self_approve.status_code == 403

        # 9. Admin Approves and Marks Paid
        approve_resp = await client.post(f"/api/sales-commission/entries/{entry['id']}/approve", headers=admin_hdr)
        assert approve_resp.status_code == 200
        assert approve_resp.json()["entry"]["status"] == "approved"

        # Mark paid with payment reference
        pay_resp = await client.post(
            f"/api/sales-commission/entries/{entry['id']}/mark-paid",
            headers=admin_hdr,
            json={"payment_reference": "NEFT-SALES-99214"}
        )
        assert pay_resp.status_code == 200
        paid_entry = pay_resp.json()["entry"]
        assert paid_entry["status"] == "paid"
        assert paid_entry["payment_reference"] == "NEFT-SALES-99214"

        # Check Salesperson view reflects "paid"
        my_resp_after = await client.get("/api/sales-commission/my", headers=rep_hdr)
        assert my_resp_after.json()["paid"] == 17000.0
        assert my_resp_after.json()["pending"] == 0.0

        # Reverse entry
        rev_resp = await client.post(f"/api/sales-commission/entries/{entry['id']}/reverse", headers=admin_hdr)
        assert rev_resp.status_code == 200
        assert rev_resp.json()["entry"]["status"] == "reversed"


@pytest.mark.asyncio
async def test_tiered_slab_progression():
    """Verify standard salesperson without flat rate progresses through Bronze, Silver, Gold slabs based on revenue."""
    rep_id = f"test_sales_slab_{uuid.uuid4().hex[:6]}"
    rep_user = {
        "id": rep_id,
        "email": f"{rep_id}@leamss.com",
        "name": "Slab Progress Rep",
        "role": "sales_executive",
        "rbac_role": "sales_executive",
        "commission_mode": "slab",
        "is_commission_active": True,
        "created_at": datetime.now(timezone.utc),
    }
    await users_col.insert_one(rep_user)

    # Deal 1: ₹300,000 -> Should hit Bronze slab (0 - 500,000 @ 5%) -> Commission = ₹15,000
    pay1 = {
        "id": f"pay_{uuid.uuid4().hex[:8]}",
        "sales_person_id": rep_id,
        "paid_amount": 300000.0,
        "payment_status": "paid",
        "client_name": "Tier Client 1",
    }
    entry1 = await apply_commission_for_crm_payment(pay1)
    assert entry1 is not None
    assert entry1["rate_mode"] == "slab"
    assert entry1["rate_pct"] == 5.0
    assert entry1["commission_amount"] == 15000.0

    # Deal 2: ₹400,000 -> Cumulative revenue becomes ₹700,000 -> Upgraded to Silver slab (500,000 - 1,500,000 @ 7%) -> Commission = ₹28,000
    pay2 = {
        "id": f"pay_{uuid.uuid4().hex[:8]}",
        "sales_person_id": rep_id,
        "paid_amount": 400000.0,
        "payment_status": "paid",
        "client_name": "Tier Client 2",
    }
    entry2 = await apply_commission_for_crm_payment(pay2)
    assert entry2 is not None
    assert entry2["rate_mode"] == "slab"
    assert entry2["rate_pct"] == 7.0
    assert entry2["commission_amount"] == 28000.0


@pytest.mark.asyncio
async def test_deactivated_salesperson_no_commission():
    """Verify that if is_commission_active is False, no commission entries are generated."""
    rep_id = f"test_sales_inactive_{uuid.uuid4().hex[:6]}"
    rep_user = {
        "id": rep_id,
        "email": f"{rep_id}@leamss.com",
        "name": "Probation Rep",
        "role": "sales_executive",
        "rbac_role": "sales_executive",
        "is_commission_active": False,
        "created_at": datetime.now(timezone.utc),
    }
    await users_col.insert_one(rep_user)

    pay = {
        "id": f"pay_{uuid.uuid4().hex[:8]}",
        "sales_person_id": rep_id,
        "paid_amount": 50000.0,
        "payment_status": "paid",
        "client_name": "Probation Client",
    }
    entry = await apply_commission_for_crm_payment(pay)
    assert entry is None, "Deactivated salesperson must not receive commission"


@pytest.mark.asyncio
async def test_direct_sale_commission():
    """Verify direct sale payment creates commission entry correctly."""
    from core.commission_logic import apply_commission_for_direct_sale

    rep_id = f"test_sales_direct_{uuid.uuid4().hex[:6]}"
    rep_user = {
        "id": rep_id,
        "email": f"{rep_id}@leamss.com",
        "name": "Direct Sale Rep",
        "role": "sales_executive",
        "rbac_role": "sales_executive",
        "commission_mode": "flat",
        "commission_rate": 6.0,
        "is_commission_active": True,
        "created_at": datetime.now(timezone.utc),
    }
    await users_col.insert_one(rep_user)

    sale_doc = {
        "id": f"sale_{uuid.uuid4().hex[:8]}",
        "partner_id": rep_id,
        "client_name": "Direct Client",
        "service_type": "Student Visa",
        "amount_received": 150000.0,
        "status": "approved",
    }
    entry = await apply_commission_for_direct_sale(sale_doc)
    assert entry is not None
    assert entry["source_type"] == "direct_sale"
    # 6% of 150,000 = 9,000
    assert entry["commission_amount"] == 9000.0
    assert entry["rate_pct"] == 6.0

