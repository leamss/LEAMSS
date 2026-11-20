"""Unit test for GST toggle on Retainer and Package Tiers in Product Master."""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
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


@pytest.mark.asyncio
async def test_product_master_gst_applicable_toggle():
    app.dependency_overrides[get_current_user] = override_admin_user
    stored_master = {}

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
        return MagicMock(matched_count=0)

    mock_steps_cursor = MagicMock()
    mock_steps_cursor.sort.return_value.to_list = AsyncMock(return_value=[])

    try:
        with patch("routers.product_master.product_master_col.insert_one", side_effect=mock_master_insert), \
             patch("routers.product_master.product_master_col.find_one", side_effect=mock_master_find_one), \
             patch("routers.product_master.product_master_col.update_one", side_effect=mock_master_update), \
             patch("routers.product_master.products_col.find_one", return_value=None), \
             patch("routers.product_master.products_col.insert_one", new_callable=AsyncMock), \
             patch("routers.product_master.products_col.update_one", new_callable=AsyncMock), \
             patch("routers.product_master.workflow_steps_col.find", return_value=mock_steps_cursor), \
             patch("routers.product_master._sync_existing_products", new_callable=AsyncMock), \
             patch("routers.product_master.log_activity", new_callable=AsyncMock):

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                # 1. Create with GST disabled for packages and retainer
                create_payload = {
                    "name": "Australia Subclass 189 Visa",
                    "country": "AU",
                    "visa_subclass": "189",
                    "status": "active",
                    "service_price": 150000,
                    "base_fee": 150000,
                    "gst_applicable": False,
                    "package_gst_applicable": False,
                    "packages": [
                        {
                            "package_type": "standard",
                            "name": "Standard Package",
                            "price": 150000,
                            "gst_applicable": False,
                            "is_active": True,
                        },
                        {
                            "package_type": "smart",
                            "name": "Smart Package",
                            "price": 187500,
                            "gst_applicable": False,
                            "is_active": True,
                        }
                    ]
                }

                res = await ac.post("/api/product-master", json=create_payload)
                assert res.status_code == 200, res.text
                prod_id = res.json()["id"]

                # Fetch and verify initial GST flags
                get_init = await ac.get(f"/api/product-master/{prod_id}")
                assert get_init.status_code == 200
                initial_product = get_init.json()
                assert initial_product["gst_applicable"] is False
                assert initial_product["package_gst_applicable"] is False
                assert initial_product["packages"][0]["gst_applicable"] is False
                assert initial_product["packages"][1]["gst_applicable"] is False

                # 2. Update via PUT with GST enabled for retainer and package tiers
                update_payload = {
                    "gst_applicable": True,
                    "package_gst_applicable": True,
                    "packages": [
                        {
                            "package_type": "standard",
                            "name": "Standard Package",
                            "price": 150000,
                            "gst_applicable": True,
                            "is_active": True,
                        },
                        {
                            "package_type": "smart",
                            "name": "Smart Package",
                            "price": 187500,
                            "gst_applicable": True,
                            "is_active": True,
                        }
                    ]
                }

                put_res = await ac.put(f"/api/product-master/{prod_id}", json=update_payload)
                assert put_res.status_code == 200, put_res.text

                # 3. Retrieve product by ID and verify updated GST flags
                get_updated = await ac.get(f"/api/product-master/{prod_id}")
                assert get_updated.status_code == 200
                updated_product = get_updated.json()
                assert updated_product["gst_applicable"] is True
                assert updated_product["package_gst_applicable"] is True
                assert updated_product["packages"][0]["gst_applicable"] is True
                assert updated_product["packages"][1]["gst_applicable"] is True
    finally:
        app.dependency_overrides.clear()
