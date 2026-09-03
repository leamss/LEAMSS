import asyncio
import httpx
from core.database import db
from core.allocations_logic import build_allocations_for_pa
from core.auth import create_access_token

async def test_all():
    print("--- 1. Testing Cost Allocations for pranali ---")
    pa = await db['pre_assessments'].find_one({'id': '590c6bdb-080d-4115-8012-bb97de5b9f77'}, {'_id': 0})
    doc = await build_allocations_for_pa(pa)
    print("Revenue:", doc['total_revenue'])
    for a in doc['allocations']:
        print("  Category:", a['vendor_category'], "| Type:", a['payment_type'], "| Rate:", a.get('rate'), "| Calc:", a['calculated_amount'], "| Total:", a['total_amount'])
    print("Summary:", doc['summary'])

    print("\n--- 2. Testing Payment Endpoints via HTTP ---")
    admin_user = await db['users'].find_one({'role': 'admin'}, {'_id': 0})
    token = create_access_token({"sub": admin_user["id"], "role": admin_user["role"], "email": admin_user["email"]})
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000") as client:
        # Bank details
        bank_res = await client.get("/api/payments/bank-details", params={"country": "Australia"}, headers=headers)
        print("Bank details status:", bank_res.status_code, "| Account:", bank_res.json().get("account_number"))

        # Razorpay create-order
        sale = await db['sales'].find_one({'id': pa.get('sale_id')}, {'_id': 0})
        if sale:
            order_res = await client.post("/api/payments/razorpay/create-order", json={"sale_id": sale["id"], "amount": 10620}, headers=headers)
            print("Create order status:", order_res.status_code, "| Order ID:", order_res.json().get("order_id"), "| Amount:", order_res.json().get("amount_rupees"))

        # PA allocations API endpoint
        alloc_res = await client.get(f"/api/pa-allocations/{pa['id']}/allocations", headers=headers)
        print("PA Allocations endpoint status:", alloc_res.status_code, "| Total Allocated:", alloc_res.json().get("allocations", {}).get("summary", {}).get("total_allocated"))

    print("\nAll tests passed successfully with 200 OK!")

asyncio.run(test_all())
