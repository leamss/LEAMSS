"""Test Website Lead Synchronization & Navratri Integration with Cockpit."""
import pytest
from core.website_sync import map_navratri_row_to_lead


def test_map_navratri_row_success_payment():
    """Verify mapping of successful registration with full payment."""
    raw = {
        "id": 31,
        "unique_id": "NN242731",
        "full_name": "pooja prakash ghatkar",
        "email": "pgmodel29@gmail.com",
        "mobile": "+919423391355",
        "country_code": "91",
        "mobile_number": "9423391355",
        "dob": "2026-09-09",
        "qualification": "cs",
        "experience": "2 years",
        "gender": "Female",
        "marital_status": "Single",
        "resume_path": "uploads/resumes/1789021243_SRI GODA TURLAPATI CV.pdf",
        "agree": 1,
        "payment_status": "success",
        "payment_mode": "upi",
        "payment_amount": "1.00",
        "razorpay_payment_id": "pay_TaE0YLf6KnSyTI",
        "razorpay_order_id": "order_TaE00jSZjFgla2",
        "paid_at": "2026-09-10 11:21:29",
        "reference": "Facebook",
        "sales_person_name": "rohit",
        "created_at": "2026-09-10 11:20:41",
        "updated_at": "2026-09-10 11:21:29"
    }

    mapped = map_navratri_row_to_lead(raw)

    assert mapped["name"] == "pooja prakash ghatkar"
    assert mapped["email"] == "pgmodel29@gmail.com"
    assert mapped["phone"] == "+919423391355"
    assert mapped["unique_id"] == "NN242731"
    assert mapped["stage"] == "payment_done"
    assert mapped["priority"] == "high"
    assert mapped["latest_qualification"] == "cs"
    assert mapped["total_work_experience"] == "2 years"
    assert mapped["gender"] == "Female"
    assert mapped["marital_status"] == "Single"
    assert mapped["payment_status"] == "success"
    assert mapped["payment_amount"] == 1.0
    assert mapped["razorpay_payment_id"] == "pay_TaE0YLf6KnSyTI"
    assert mapped["resume_url"] == "https://leamss.com/uploads/resumes/1789021243_SRI GODA TURLAPATI CV.pdf"
    assert "Navratri Offer 2026" in mapped["tags"]
    assert "Payment Success" in mapped["tags"]
    assert mapped["source"] == "Navratri Offer (leamss.com)"
    assert mapped["subsource"] == "Facebook"
    assert mapped["sales_person_name"] == "rohit"


def test_map_navratri_row_pending_payment():
    """Verify mapping of pending registration without payment."""
    raw = {
        "id": 34,
        "unique_id": "NN242734",
        "full_name": "Jyoti Pandey",
        "email": "jyoti@leamss.com",
        "mobile": "+917900152427",
        "country_code": "91",
        "mobile_number": "7900152427",
        "dob": "2026-09-07",
        "qualification": "Msc",
        "experience": "9",
        "gender": "Female",
        "marital_status": "Single",
        "resume_path": None,
        "agree": 1,
        "payment_status": "pending",
        "payment_mode": None,
        "payment_amount": None,
        "razorpay_payment_id": None,
        "razorpay_order_id": None,
        "paid_at": None,
        "reference": None,
        "sales_person_name": None,
        "created_at": "2026-09-10 14:15:54",
        "updated_at": "2026-09-10 14:15:54"
    }

    mapped = map_navratri_row_to_lead(raw)

    assert mapped["name"] == "Jyoti Pandey"
    assert mapped["email"] == "jyoti@leamss.com"
    assert mapped["phone"] == "+917900152427"
    assert mapped["unique_id"] == "NN242734"
    assert mapped["stage"] == "new"
    assert mapped["priority"] == "medium"
    assert mapped["latest_qualification"] == "Msc"
    assert mapped["total_work_experience"] == "9"
    assert mapped["payment_status"] == "pending"
    assert mapped["payment_amount"] is None
    assert mapped["resume_url"] == ""
    assert "Navratri Offer 2026" in mapped["tags"]
    assert mapped["source"] == "Navratri Offer (leamss.com)"


def test_map_navratri_row_failed_payment():
    """Verify mapping of failed payment registration."""
    raw = {
        "id": 32,
        "unique_id": "NN242732",
        "full_name": "Test User",
        "email": "test@leamss.com",
        "mobile": "+917900152427",
        "payment_status": "failed",
        "payment_amount": "1.00",
        "razorpay_payment_id": "pay_failed_123",
        "razorpay_order_id": "order_failed_456"
    }

    mapped = map_navratri_row_to_lead(raw)

    assert mapped["stage"] == "not_connected"
    assert mapped["payment_status"] == "failed"
    assert "Payment Failed" in mapped["tags"]
