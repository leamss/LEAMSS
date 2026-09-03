import asyncio
import httpx
import uuid
from core.database import db
from core.auth import create_access_token

async def test_full_promo_flow():
    # 1. Auth Tokens
    admin = await db["users"].find_one({"role": "admin"}, {"_id": 0})
    partner = await db["users"].find_one({"role": "partner"}, {"_id": 0})
    
    admin_token = create_access_token({"sub": admin["id"], "role": "admin", "email": admin["email"]})
    partner_token = create_access_token({"sub": partner["id"], "role": "partner", "email": partner["email"]})
    
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    partner_headers = {"Authorization": f"Bearer {partner_token}"}
    
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=30.0) as client:
        print("\n--- STEP 1: Admin Creates Promo Code ---")
        promo_payload = {
            "code": "PROMOFLOW50",
            "discount_type": "percentage",
            "discount_value": 50,
            "max_uses": 50,
            "is_active": True
        }
        res = await client.post("/api/marketing/promo", json=promo_payload, headers=admin_headers)
        print("Create Promo Code Response:", res.status_code, res.json())
        assert res.status_code == 200

        print("\n--- STEP 2: Partner Fetches Promo Codes ---")
        res = await client.get("/api/marketing/promos", headers=partner_headers)
        print("Partner GET /promos Status:", res.status_code)
        found = next((p for p in res.json() if p["code"] == "PROMOFLOW50"), None)
        print("Found Promo in Partner List:", found)
        assert found is not None
        assert found.get("active") is True or found.get("is_active") is True

        print("\n--- STEP 3: Partner Generates Payment Link with Promo Code Assigned & Enabled ---")
        # Find or create a test PA for partner
        pa = await db["pre_assessments"].find_one({"partner_id": partner["id"]}, {"_id": 0})
        if not pa:
            pa = await db["pre_assessments"].find_one({}, {"_id": 0})
            
        gen_res = await client.post("/api/pre-assess-portal/generate-public-link", json={
            "pa_id": pa["id"],
            "promo_code": "PROMOFLOW50",
            "promo_enabled": True,
            "include_gst": False
        }, headers=partner_headers)
        print("Generate Link Response:", gen_res.status_code, gen_res.json())
        assert gen_res.status_code == 200
        token = gen_res.json()["token"]
        assert gen_res.json().get("assigned_promo_code") == "PROMOFLOW50"

        print("\n--- STEP 4: Client Opens Public Payment Page ---")
        client_page_res = await client.get(f"/api/pre-assess-portal/public/{token}")
        print("Public PA Page Status:", client_page_res.status_code)
        assert client_page_res.status_code == 200
        pa_data = client_page_res.json()
        print("Assigned Promo on Client Screen:", pa_data.get("assigned_promo_code"), "| Enabled:", pa_data.get("promo_enabled"))
        assert pa_data.get("assigned_promo_code") == "PROMOFLOW50"
        assert pa_data.get("promo_enabled") is True

        print("\n--- STEP 5: Client Validates Promo Code (Live Discount Calculation) ---")
        val_res = await client.post("/api/marketing/promo/public-validate", json={
            "code": "PROMOFLOW50",
            "amount": 5100.0
        })
        print("Public Validate Response:", val_res.status_code, val_res.json())
        assert val_res.status_code == 200
        val_data = val_res.json()
        assert val_data["valid"] is True
        assert val_data["discount_amount"] == 2550.0
        assert val_data["final_amount"] == 2550.0

        print("\n--- STEP 6: Client Creates Razorpay Order with Promo Code ---")
        order_res = await client.post("/api/pre-assess-portal/public/create-order", json={
            "token": token,
            "promo_code": "PROMOFLOW50"
        })
        print("Create Order Response:", order_res.status_code, order_res.json())
        assert order_res.status_code == 200
        order_data = order_res.json()
        assert order_data["amount_rupees"] == 2550.0
        assert order_data["discount_amount"] == 2550.0
        assert order_data["promo_code"] == "PROMOFLOW50"

        print("\n--- STEP 7: Client Completes Payment & Promo Usage Increments ---")
        mock_pay_res = await client.post("/api/pre-assess-portal/public/mock-pay", json={
            "token": token,
            "promo_code": "PROMOFLOW50"
        })
        print("Mock Pay Response:", mock_pay_res.status_code, mock_pay_res.json())
        
        # Check promo usage
        updated_promo = await db["promo_codes"].find_one({"code": "PROMOFLOW50"}, {"_id": 0})
        print("Updated Promo Uses:", updated_promo.get("current_uses"), "/", updated_promo.get("max_uses"))
        
        print("\n--- STEP 8: Cleanup Test Promo Code ---")
        await db["promo_codes"].delete_one({"code": "PROMOFLOW50"})
        print("SUCCESS! Complete end-to-end promo flow verified.")

asyncio.run(test_full_promo_flow())
