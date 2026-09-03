import pytest
import requests
import uuid
from datetime import datetime, timezone
from pymongo import MongoClient

def test_sales_person_package_selection_flow():
    client_db = MongoClient("mongodb://localhost:27017")["leamss"]

    # 1. Login as Admin
    admin_login = requests.post("http://localhost:8001/api/auth/login", json={"email": "admin@leamss.com", "password": "Admin@123"})
    assert admin_login.status_code == 200, "Admin login failed"
    admin_token = admin_login.json()["token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Get Sales Executive user (rohitp)
    sales_user = client_db["users"].find_one({"email": "rohitp@gmail.com"}, {"_id": 0})
    assert sales_user is not None, "Sales user rohitp@gmail.com not found"
    sales_id = sales_user["id"]

    # Get sample product with packages
    product = client_db["products"].find_one({"packages.0": {"$exists": True}}, {"_id": 0})
    assert product is not None and len(product.get("packages", [])) > 0, "No product with packages found"
    packages = product["packages"]
    chosen_pkg = packages[0]

    # 3. Create a test Pre-Assessment for a test client assigned to rohitp
    test_pa_id = str(uuid.uuid4())
    test_pa_number = f"PA-TEST-{uuid.uuid4().hex[:6].upper()}"
    test_client_email = f"sales_client_{uuid.uuid4().hex[:6]}@example.com"
    test_client_name = "Test Client for Sales Person"

    test_pa = {
        "id": test_pa_id,
        "pa_number": test_pa_number,
        "partner_id": sales_id,
        "created_by_user_id": sales_id,
        "partner_name": sales_user.get("name", "rohitp"),
        "client_name": test_client_name,
        "client_email": test_client_email,
        "client_mobile": "+919876543210",
        "country": "Canada",
        "service_type": "Express Entry PR",
        "product_id": product.get("id"),
        "product_name": product.get("name", "Canada PR"),
        "stage": "awaiting_package_selection",
        "available_packages_snapshot": packages,
        "public_token": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    client_db["pre_assessments"].insert_one(test_pa)
    print(f"Created test PA {test_pa_number} assigned to sales person {sales_user['email']}")

    # 4. Client selects package
    # Test via client endpoint
    sel_res = requests.post(
        f"http://localhost:8001/api/pre-assess-portal/client/select-package/{test_pa_id}",
        json={"package_id": chosen_pkg["id"]},
        headers=admin_headers
    )
    assert sel_res.status_code == 200, f"Client package selection failed: {sel_res.text}"
    sel_data = sel_res.json()
    assert sel_data["ok"] is True
    assert sel_data["stage"] == "package_selected"
    assert sel_data["selected_package"]["id"] == chosen_pkg["id"]
    print(f"PASS: Client successfully selected package '{chosen_pkg['name']}' (Price: ₹{chosen_pkg.get('price', 0):,})")

    # 5. Verify the Sales Person sees the selected package in their assessments API
    sales_pas = client_db["pre_assessments"].find_one({"id": test_pa_id}, {"_id": 0})
    assert sales_pas["stage"] == "package_selected"
    assert sales_pas.get("selected_package_id") == chosen_pkg["id"]
    assert sales_pas.get("selected_package_snapshot") is not None
    assert sales_pas["selected_package_snapshot"]["name"] == chosen_pkg["name"]
    assert sales_pas["selected_package_snapshot"]["price"] == chosen_pkg["price"]
    print(f"PASS: Sales Person assessment record contains selected package snapshot: {sales_pas['selected_package_snapshot']['name']}")

    # 6. Verify Sales Person received notification
    notif = client_db["notifications"].find_one({"user_id": sales_id, "type": "package_selected"}, {"_id": 0})
    assert notif is not None, "Notification not found for sales person"
    print(f"PASS: Notification sent to Sales Person: '{notif.get('title')}' — '{notif.get('message')}'")

    # Clean up test PA
    client_db["pre_assessments"].delete_one({"id": test_pa_id})
    print("Test completed successfully and test data cleaned up.")

if __name__ == "__main__":
    test_sales_person_package_selection_flow()
