import asyncio
import httpx
from core.database import db
from core.auth import create_access_token

async def test_order_flow():
    # Find puja24 user
    user = await db['users'].find_one({'email': {'$regex': 'puju24|puja24', '$options': 'i'}}, {'_id': 0})
    if not user:
        user = await db['users'].find_one({'role': 'client'}, {'_id': 0})
    print("Testing with User:", user.get('name'), user.get('email'), user.get('id'))

    token = create_access_token({"sub": user["id"], "role": user.get("role", "client"), "email": user["email"]})
    headers = {"Authorization": f"Bearer {token}"}

    case = await db['cases'].find_one({'client_email': user['email']}, {'_id': 0})
    sale = await db['sales'].find_one({'client_email': user['email']}, {'_id': 0})
    print("Case ID:", case.get('id') if case else None)
    print("Sale ID:", sale.get('id') if sale else None, "| Pending:", sale.get('pending_amount') if sale else None)

    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000") as client:
        # Create Order
        payload = {"sale_id": sale["id"] if sale else None, "amount": 10125}
        res = await client.post("/api/payments/razorpay/create-order", json=payload, headers=headers)
        print("Create Order Response:", res.status_code, res.json())

        if res.status_code == 200:
            order_data = res.json()
            # Verify Payment
            verify_payload = {
                "sale_id": sale["id"],
                "order_id": order_data["order_id"],
                "payment_id": f"pay_test_{order_data['order_id'][:8]}",
                "signature": ""
            }
            v_res = await client.post("/api/payments/razorpay/verify", json=verify_payload, headers=headers)
            print("Verify Payment Response:", v_res.status_code, v_res.json())

            # Check updated sale
            s_after = await db['sales'].find_one({'id': sale['id']}, {'_id': 0})
            print("Sale after pay:", s_after.get('pending_amount'), s_after.get('status'), s_after.get('payment_parts'))

asyncio.run(test_order_flow())
