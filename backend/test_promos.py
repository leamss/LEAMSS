import asyncio
import httpx
from core.database import db
from core.auth import create_access_token

async def test_promo_flow():
    admin = await db["users"].find_one({"role": "admin"}, {"_id": 0})
    token = create_access_token({"sub": admin["id"], "role": "admin", "email": admin["email"]})
    headers = {"Authorization": f"Bearer {token}"}
    
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000") as client:
        # Test 1: Get existing promos
        res = await client.get("/api/marketing/promos", headers=headers)
        print("Existing Promos:")
        for p in res.json():
            print(" -", p.get("code"), "| active:", p.get("active"), "| is_active:", p.get("is_active"), "| uses:", p.get("used_count"), "/", p.get("max_uses"))

        # Test 2: Create a new active promo
        new_promo = {
            "code": "ACTIVE2026",
            "discount_type": "percentage",
            "discount_value": 25,
            "max_uses": 50,
            "is_active": True
        }
        create_res = await client.post("/api/marketing/promo", json=new_promo, headers=headers)
        print("Create Promo Status:", create_res.status_code, create_res.json())

        # Test 3: Verify it returns as active
        res2 = await client.get("/api/marketing/promos", headers=headers)
        print("Updated Promos List:")
        for p in res2.json():
            print(" -", p.get("code"), "| active:", p.get("active"), "| is_active:", p.get("is_active"))

asyncio.run(test_promo_flow())
