import pytest
import requests
from pymongo import MongoClient

def test_select_package():
    # 1. Login as admin
    login_res = requests.post("http://localhost:8001/api/auth/login", json={"email": "admin@leamss.com", "password": "Admin@123"})
    assert login_res.status_code == 200, "Admin login failed"
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    db = MongoClient("mongodb://localhost:27017")["leamss"]
    pa = db["pre_assessments"].find_one({"pa_number": "PA-20260901-E4C215"}, {"_id": 0})
    if not pa:
        pa = db["pre_assessments"].find_one({"client_email": "fff@gmail.com"}, {"_id": 0})
    assert pa is not None, "PA not found in DB"
    pa_id = pa["id"]

    # Reset stage to awaiting_package_selection for clean test
    db["pre_assessments"].update_one(
        {"id": pa_id},
        {"$set": {
            "stage": "awaiting_package_selection",
            "selected_package_id": None,
            "selected_package_snapshot": None,
        }}
    )

    packages = pa.get("available_packages_snapshot") or []
    assert len(packages) > 0, "No available packages in snapshot"
    pkg_id = packages[0]["id"]
    pkg_name = packages[0]["name"]

    # 2. Select package via API (as admin impersonating/client)
    sel_res = requests.post(
        f"http://localhost:8001/api/pre-assess-portal/client/select-package/{pa_id}",
        json={"package_id": pkg_id},
        headers=headers
    )
    assert sel_res.status_code == 200, f"Select package failed: {sel_res.text}"
    data = sel_res.json()
    assert data["ok"] is True
    assert data["stage"] == "package_selected"
    assert data["selected_package"]["id"] == pkg_id
    print(f"PASS: Successfully selected package '{pkg_name}' for PA {pa_id}")

    # 3. Verify in DB
    updated = db["pre_assessments"].find_one({"id": pa_id}, {"_id": 0})
    assert updated["stage"] == "package_selected"
    assert updated["selected_package_id"] == pkg_id
    assert updated["selected_package_snapshot"]["name"] == pkg_name
    print("PASS: Verified in MongoDB that PA is now in stage 'package_selected'")

if __name__ == "__main__":
    test_select_package()
