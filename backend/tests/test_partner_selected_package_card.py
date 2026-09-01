import pytest
import requests
from pymongo import MongoClient

def test_partner_selected_package():
    # Login
    login_res = requests.post("http://localhost:8001/api/auth/login", json={"email": "admin@leamss.com", "password": "Admin@123"})
    assert login_res.status_code == 200, "Login failed"
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    db = MongoClient("mongodb://localhost:27017")["leamss"]
    pa = db["pre_assessments"].find_one({"client_name": "saanikaa"}, {"_id": 0})
    assert pa is not None, "saanikaa PA not found"
    pa_id = pa["id"]

    prod = db["products"].find_one({"id": pa.get("product_id")}, {"_id": 0})
    assert prod is not None and prod.get("packages"), "Product packages not found"
    selected_pkg = prod["packages"][0]

    # Update PA with selected package
    db["pre_assessments"].update_one(
        {"id": pa_id},
        {"$set": {
            "stage": "package_selected",
            "selected_package_id": selected_pkg["id"],
            "selected_package_snapshot": selected_pkg,
            "package_selected_at": "2026-08-29T11:45:00Z"
        }}
    )

    # Fetch from partner endpoint
    res = requests.get(f"http://localhost:8001/api/pre-assessment/{pa_id}", headers=headers)
    assert res.status_code == 200, "Fetch PA failed"
    data = res.json()

    assert data.get("stage") == "package_selected"
    assert data.get("selected_package_snapshot") is not None
    assert data["selected_package_snapshot"]["name"] == selected_pkg["name"]
    assert data["selected_package_snapshot"]["price"] == selected_pkg["price"]
    print("Test passed: Selected package snapshot is correctly returned to Partner!")

if __name__ == "__main__":
    test_partner_selected_package()
