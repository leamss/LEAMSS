import pytest
import requests
import uuid
from datetime import datetime, timezone
from pymongo import MongoClient

def test_package_refund_policy_flow():
    client_db = MongoClient("mongodb://localhost:27017")["leamss"]

    # 1. Login as Admin
    login_res = requests.post("http://localhost:8001/api/auth/login", json={"email": "admin@leamss.com", "password": "Admin@123"})
    assert login_res.status_code == 200, "Admin login failed"
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create or find product to test packages with refund policy
    test_prod_id = f"prod-test-{uuid.uuid4().hex[:6]}"
    pkg_protection_id = str(uuid.uuid4())
    pkg_standard_id = str(uuid.uuid4())
    pkg_no_refund_id = str(uuid.uuid4())
    pkg_none_id = str(uuid.uuid4())

    packages_data = [
        {
            "id": pkg_protection_id,
            "package_type": "standard",
            "name": "Protection Package",
            "price": 77945.0,
            "description": "Full coverage package",
            "is_active": True,
            "refund_policy": {
                "enabled": True,
                "policy_type": "protection",
                "name": "Protection Policy",
                "label": "Protection Policy Guarantee",
                "is_service_fee_refundable": True,
                "refundable_service_fee_pct": 100,
                "include_govt_fees": True,
                "govt_fees_handling": "subsidized",
                "negative_skills_assessment_guarantee": True,
                "visa_refusal_guarantee": True,
                "voluntary_withdrawal_milestones": True,
                "claim_window_days": 30,
                "payout_time_days": 14,
                "conditions": [
                    "100% genuine documentation provided without omissions",
                    "Client responds within 7 working days"
                ]
            }
        },
        {
            "id": pkg_standard_id,
            "package_type": "smart",
            "name": "Standard Package",
            "price": 90853.0,
            "description": "Standard milestone package",
            "is_active": True,
            "refund_policy": {
                "enabled": True,
                "policy_type": "standard",
                "name": "Standard Policy",
                "label": "Standard Milestone Policy",
                "is_service_fee_refundable": True,
                "refundable_service_fee_pct": 50,
                "include_govt_fees": False,
                "govt_fees_handling": "non_refundable",
                "negative_skills_assessment_guarantee": True,
                "visa_refusal_guarantee": False,
                "voluntary_withdrawal_milestones": True,
                "claim_window_days": 30,
                "payout_time_days": 14,
                "conditions": [
                    "Withdrawal prior to filing: 50% refund less file charges"
                ]
            }
        },
        {
            "id": pkg_no_refund_id,
            "package_type": "premium",
            "name": "Express No Refund Package",
            "price": 50000.0,
            "description": "Fast track appeals",
            "is_active": True,
            "refund_policy": {
                "enabled": True,
                "policy_type": "no_refund",
                "name": "No Refund",
                "is_service_fee_refundable": False,
                "refundable_service_fee_pct": 0,
                "conditions": ["Non-refundable"]
            }
        },
        {
            "id": pkg_none_id,
            "package_type": "custom",
            "name": "Unconfigured Package",
            "price": 25000.0,
            "description": "No refund policy set",
            "is_active": True,
            "refund_policy": None
        }
    ]

    test_product = {
        "id": test_prod_id,
        "name": "Test Canada PR Product",
        "country": "Canada",
        "visa_type": "PR",
        "service_price": 77945.0,
        "packages": packages_data,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    client_db["products"].insert_one(test_product)

    # 3. Create test Pre-Assessment linked to this product
    test_pa_id = str(uuid.uuid4())
    test_pa_num = f"PA-TEST-{uuid.uuid4().hex[:6].upper()}"
    test_pa = {
        "id": test_pa_id,
        "pa_number": test_pa_num,
        "client_name": "Refund Policy Test Client",
        "client_email": f"test_refund_{uuid.uuid4().hex[:6]}@example.com",
        "client_mobile": "+919998887776",
        "country": "Canada",
        "service_type": "PR",
        "product_id": test_prod_id,
        "stage": "awaiting_package_selection",
        "available_packages_snapshot": packages_data,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    client_db["pre_assessments"].insert_one(test_pa)

    # 4. Client selects Protection Package
    sel_res = requests.post(
        f"http://localhost:8001/api/pre-assess-portal/client/select-package/{test_pa_id}",
        json={"package_id": pkg_protection_id},
        headers=headers
    )
    assert sel_res.status_code == 200, f"Client select package failed: {sel_res.text}"
    sel_data = sel_res.json()
    assert sel_data["ok"] is True
    assert sel_data["selected_package"]["id"] == pkg_protection_id
    assert sel_data["selected_package"]["refund_policy"]["policy_type"] == "protection"
    assert sel_data["selected_package"]["refund_policy"]["include_govt_fees"] is True
    assert sel_data["selected_package"]["refund_policy"]["refundable_service_fee_pct"] == 100

    # 5. Verify auto-vars for agreement reflect the package refund policy
    auto_vars_res = requests.get(
        f"http://localhost:8001/api/pa-agreements/auto-vars/{test_pa_id}",
        headers=headers
    )
    assert auto_vars_res.status_code == 200, f"Get auto-vars failed: {auto_vars_res.text}"
    vars_data = auto_vars_res.json().get("variables", {})

    assert vars_data.get("refund_policy_type") == "protection"
    assert vars_data.get("refund_policy_name") == "Protection Policy"
    assert vars_data.get("refund_service_fee_pct") == "100%"
    assert vars_data.get("refundable_amount") == "₹77,945"
    assert vars_data.get("refund_fee_scope") == "Including Govt. & Professional Fees"
    assert "100% genuine documentation provided without omissions" in vars_data.get("refund_conditions", "")

    # 6. Test Standard Package selection and auto-vars
    client_db["pre_assessments"].update_one(
        {"id": test_pa_id},
        {"$set": {"stage": "awaiting_package_selection"}}
    )
    sel_res_std = requests.post(
        f"http://localhost:8001/api/pre-assess-portal/client/select-package/{test_pa_id}",
        json={"package_id": pkg_standard_id},
        headers=headers
    )
    assert sel_res_std.status_code == 200
    std_data = sel_res_std.json()["selected_package"]
    assert std_data["refund_policy"]["policy_type"] == "standard"
    assert std_data["refund_policy"]["refundable_service_fee_pct"] == 50

    auto_vars_std = requests.get(
        f"http://localhost:8001/api/pa-agreements/auto-vars/{test_pa_id}",
        headers=headers
    ).json().get("variables", {})

    assert auto_vars_std.get("refund_policy_type") == "standard"
    assert auto_vars_std.get("refund_service_fee_pct") == "50%"
    assert auto_vars_std.get("refundable_amount") == "₹45,426"  # 50% of 90853 rounded (round(45426.5) == 45426)
    assert auto_vars_std.get("refund_fee_scope") == "Professional Fees Only"

    # 7. Test Package without refund policy (None)
    client_db["pre_assessments"].update_one(
        {"id": test_pa_id},
        {"$set": {"stage": "awaiting_package_selection"}}
    )
    sel_res_none = requests.post(
        f"http://localhost:8001/api/pre-assess-portal/client/select-package/{test_pa_id}",
        json={"package_id": pkg_none_id},
        headers=headers
    )
    assert sel_res_none.status_code == 200
    none_data = sel_res_none.json()["selected_package"]
    assert none_data.get("refund_policy") is None

    auto_vars_none = requests.get(
        f"http://localhost:8001/api/pa-agreements/auto-vars/{test_pa_id}",
        headers=headers
    ).json().get("variables", {})

    assert auto_vars_none.get("refund_policy_type") == ""
    assert auto_vars_none.get("refundable_amount") == ""
    assert auto_vars_none.get("refund_fee_scope") == ""

    # Clean up test data
    client_db["products"].delete_one({"id": test_prod_id})
    client_db["pre_assessments"].delete_one({"id": test_pa_id})
    print("ALL TESTS PASSED: Package refund policy integration verified across creation, client selection, and agreement auto-vars.")

if __name__ == "__main__":
    test_package_refund_policy_flow()
