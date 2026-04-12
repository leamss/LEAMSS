"""Phase 12: Client Experience Enhancement Router
- 12A: Self-Eligibility Checker
- 12B: EMI Payment Plans
- 12C: Family Member Management
- 12D: Smart Document Upload enhancement (bulk upload already exists, adding checklist tracker)
"""
import uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from core.database import (
    db, cases_col, users_col, products_col, sales_col,
    notifications_col, audit_logs_col, documents_col
)
from core.auth import get_current_user

router = APIRouter(prefix="/client-tools", tags=["Client Experience"])

eligibility_checks_col = db["eligibility_checks"]
emi_plans_col = db["emi_plans"]
emi_payments_col = db["emi_payments"]
family_members_col = db["family_members"]


# ===================== 12A: SELF-ELIGIBILITY CHECKER =====================

class EligibilityInput(BaseModel):
    age: int = 0
    education: str = ""  # high_school, bachelors, masters, phd
    work_experience_years: float = 0
    ielts_overall: float = 0
    ielts_listening: float = 0
    ielts_reading: float = 0
    ielts_writing: float = 0
    ielts_speaking: float = 0
    country_preference: str = ""  # canada, australia, uk, usa, germany, nz
    has_job_offer: bool = False
    has_relatives_abroad: bool = False
    marital_status: str = ""  # single, married
    spouse_education: str = ""
    spouse_work_experience: float = 0
    funds_available_inr: float = 0


def _calculate_eligibility(data: EligibilityInput):
    """Calculate eligibility scores for different visa programs"""
    results = []

    # --- Canada PR (Express Entry CRS-like scoring) ---
    canada_score = 0
    # Age (max 12 pts)
    if 20 <= data.age <= 29: canada_score += 12
    elif 30 <= data.age <= 34: canada_score += 11
    elif 35 <= data.age <= 39: canada_score += 9
    elif 40 <= data.age <= 44: canada_score += 7
    elif data.age >= 45: canada_score += 3
    # Education (max 25 pts)
    edu_scores = {"phd": 25, "masters": 23, "bachelors": 20, "diploma": 15, "high_school": 5}
    canada_score += edu_scores.get(data.education, 0)
    # Work experience (max 15 pts)
    if data.work_experience_years >= 6: canada_score += 15
    elif data.work_experience_years >= 4: canada_score += 13
    elif data.work_experience_years >= 2: canada_score += 11
    elif data.work_experience_years >= 1: canada_score += 9
    # IELTS (max 24 pts)
    ielts_avg = data.ielts_overall or ((data.ielts_listening + data.ielts_reading + data.ielts_writing + data.ielts_speaking) / 4 if data.ielts_listening else 0)
    if ielts_avg >= 8: canada_score += 24
    elif ielts_avg >= 7: canada_score += 20
    elif ielts_avg >= 6.5: canada_score += 16
    elif ielts_avg >= 6: canada_score += 12
    elif ielts_avg >= 5.5: canada_score += 8
    # Bonus
    if data.has_job_offer: canada_score += 10
    if data.has_relatives_abroad: canada_score += 5
    if data.marital_status == "married" and data.spouse_education: canada_score += 5
    if data.funds_available_inr >= 1500000: canada_score += 4

    canada_pct = min(100, round(canada_score / 95 * 100))
    canada_tips = []
    if ielts_avg < 7: canada_tips.append("Improve IELTS to 7+ for higher CRS score")
    if data.work_experience_years < 3: canada_tips.append("More work experience will boost your score")
    if not data.has_job_offer: canada_tips.append("A valid job offer adds significant points")
    results.append({
        "program": "Canada PR (Express Entry)",
        "country": "Canada",
        "score": canada_pct,
        "raw_score": canada_score,
        "max_score": 95,
        "status": "highly_eligible" if canada_pct >= 70 else "eligible" if canada_pct >= 50 else "needs_improvement" if canada_pct >= 30 else "low_eligibility",
        "tips": canada_tips,
    })

    # --- Australia PR (Skilled Migration) ---
    aus_score = 0
    if 25 <= data.age <= 32: aus_score += 15
    elif 33 <= data.age <= 39: aus_score += 10
    elif 40 <= data.age <= 44: aus_score += 5
    edu_aus = {"phd": 20, "masters": 15, "bachelors": 15, "diploma": 10, "high_school": 0}
    aus_score += edu_aus.get(data.education, 0)
    if data.work_experience_years >= 8: aus_score += 15
    elif data.work_experience_years >= 5: aus_score += 10
    elif data.work_experience_years >= 3: aus_score += 5
    if ielts_avg >= 8: aus_score += 20
    elif ielts_avg >= 7: aus_score += 10
    if data.has_relatives_abroad: aus_score += 5
    if data.marital_status == "married" and data.spouse_education in ["bachelors", "masters", "phd"]: aus_score += 5

    aus_pct = min(100, round(aus_score / 85 * 100))
    aus_tips = []
    if data.age > 39: aus_tips.append("Age above 39 reduces points significantly")
    if ielts_avg < 7: aus_tips.append("IELTS 7+ (each band) gives 10 bonus points")
    results.append({
        "program": "Australia PR (Skilled Migration)",
        "country": "Australia",
        "score": aus_pct,
        "raw_score": aus_score,
        "max_score": 85,
        "status": "highly_eligible" if aus_pct >= 70 else "eligible" if aus_pct >= 50 else "needs_improvement" if aus_pct >= 30 else "low_eligibility",
        "tips": aus_tips,
    })

    # --- Student Visa (General) ---
    student_score = 0
    if data.age <= 30: student_score += 20
    elif data.age <= 35: student_score += 15
    else: student_score += 8
    if data.education in ["bachelors", "masters", "phd"]: student_score += 25
    elif data.education == "diploma": student_score += 15
    else: student_score += 10
    if ielts_avg >= 6.5: student_score += 25
    elif ielts_avg >= 6: student_score += 20
    elif ielts_avg >= 5.5: student_score += 15
    if data.funds_available_inr >= 2000000: student_score += 15
    elif data.funds_available_inr >= 1000000: student_score += 10
    elif data.funds_available_inr >= 500000: student_score += 5

    student_pct = min(100, round(student_score / 85 * 100))
    student_tips = []
    if ielts_avg < 6: student_tips.append("Most universities require IELTS 6.0+")
    if data.funds_available_inr < 1000000: student_tips.append("Show adequate funds for tuition + living expenses")
    results.append({
        "program": "Student Visa",
        "country": data.country_preference or "Multiple",
        "score": student_pct,
        "raw_score": student_score,
        "max_score": 85,
        "status": "highly_eligible" if student_pct >= 70 else "eligible" if student_pct >= 50 else "needs_improvement" if student_pct >= 30 else "low_eligibility",
        "tips": student_tips,
    })

    # --- Work Permit ---
    work_score = 0
    if data.has_job_offer: work_score += 30
    if data.work_experience_years >= 5: work_score += 20
    elif data.work_experience_years >= 3: work_score += 15
    elif data.work_experience_years >= 1: work_score += 10
    if data.education in ["masters", "phd"]: work_score += 15
    elif data.education == "bachelors": work_score += 10
    if ielts_avg >= 6.5: work_score += 15
    elif ielts_avg >= 5.5: work_score += 10

    work_pct = min(100, round(work_score / 80 * 100))
    work_tips = []
    if not data.has_job_offer: work_tips.append("A valid job offer is usually required for work permits")
    results.append({
        "program": "Work Permit",
        "country": data.country_preference or "Multiple",
        "score": work_pct,
        "raw_score": work_score,
        "max_score": 80,
        "status": "highly_eligible" if work_pct >= 70 else "eligible" if work_pct >= 50 else "needs_improvement" if work_pct >= 30 else "low_eligibility",
        "tips": work_tips,
    })

    return sorted(results, key=lambda x: x["score"], reverse=True)


@router.post("/eligibility-check")
async def check_eligibility(data: EligibilityInput, current_user: dict = Depends(get_current_user)):
    """Run eligibility check for logged-in user"""
    results = _calculate_eligibility(data)

    # Save check
    check = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "input_data": data.dict(),
        "results": results,
        "best_program": results[0]["program"] if results else "",
        "best_score": results[0]["score"] if results else 0,
        "created_at": datetime.now(timezone.utc),
    }
    await eligibility_checks_col.insert_one(check)
    check.pop("_id", None)
    check["created_at"] = check["created_at"].isoformat()

    return {"results": results, "check_id": check["id"]}


@router.post("/eligibility-check/public")
async def check_eligibility_public(data: EligibilityInput):
    """Public eligibility check (no login required)"""
    results = _calculate_eligibility(data)
    return {"results": results}


@router.get("/eligibility-history")
async def get_eligibility_history(current_user: dict = Depends(get_current_user)):
    """Get past eligibility checks"""
    checks = await eligibility_checks_col.find(
        {"user_id": current_user["id"]}, {"_id": 0}
    ).sort("created_at", -1).to_list(20)
    for c in checks:
        if isinstance(c.get("created_at"), datetime):
            c["created_at"] = c["created_at"].isoformat()
    return checks


# ===================== 12B: EMI PAYMENT PLANS =====================

class CreateEMIPlan(BaseModel):
    sale_id: str
    total_amount: float
    installments: int = 3  # 3, 6, 12
    notes: str = ""


@router.post("/emi/create")
async def create_emi_plan(data: CreateEMIPlan, current_user: dict = Depends(get_current_user)):
    """Admin creates an EMI plan for a sale"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    sale = await sales_col.find_one({"id": data.sale_id}, {"_id": 0})
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")

    if data.installments not in [3, 6, 12]:
        raise HTTPException(status_code=400, detail="Installments must be 3, 6, or 12")

    emi_amount = round(data.total_amount / data.installments, 2)
    now = datetime.now(timezone.utc)

    schedule = []
    for i in range(data.installments):
        due_date = now + timedelta(days=30 * (i + 1))
        schedule.append({
            "installment_no": i + 1,
            "amount": emi_amount,
            "due_date": due_date.isoformat(),
            "status": "pending",
            "paid_at": None,
        })

    plan = {
        "id": str(uuid.uuid4()),
        "sale_id": data.sale_id,
        "client_id": sale.get("client_id", ""),
        "client_name": sale.get("client_name", ""),
        "client_email": sale.get("client_email", ""),
        "total_amount": data.total_amount,
        "emi_amount": emi_amount,
        "installments": data.installments,
        "schedule": schedule,
        "paid_count": 0,
        "total_paid": 0,
        "status": "active",
        "notes": data.notes,
        "created_by": current_user["id"],
        "created_at": now,
    }
    await emi_plans_col.insert_one(plan)
    plan.pop("_id", None)
    plan["created_at"] = plan["created_at"].isoformat()

    # Notify client
    client = await users_col.find_one({"email": sale.get("client_email")}, {"_id": 0, "id": 1})
    if client:
        await notifications_col.insert_one({
            "id": str(uuid.uuid4()), "user_id": client["id"],
            "title": "EMI Plan Created",
            "message": f"An EMI plan of {data.installments} installments (₹{emi_amount:,.0f}/month) has been created for your case.",
            "type": "emi_plan", "read": False,
            "created_at": now,
        })

    return {"message": f"EMI plan created: {data.installments} x ₹{emi_amount:,.0f}", "plan": plan}


@router.get("/emi/my-plans")
async def get_my_emi_plans(current_user: dict = Depends(get_current_user)):
    """Get EMI plans for current user"""
    if current_user["role"] == "admin":
        plans = await emi_plans_col.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    else:
        # Find by client email or client_id
        plans = await emi_plans_col.find(
            {"$or": [{"client_id": current_user["id"]}, {"client_email": current_user.get("email", "")}]}, {"_id": 0}
        ).sort("created_at", -1).to_list(50)

    for p in plans:
        if isinstance(p.get("created_at"), datetime):
            p["created_at"] = p["created_at"].isoformat()
    return plans


@router.post("/emi/{plan_id}/pay-installment")
async def pay_emi_installment(plan_id: str, installment_no: int = 1, current_user: dict = Depends(get_current_user)):
    """Mark an EMI installment as paid"""
    plan = await emi_plans_col.find_one({"id": plan_id}, {"_id": 0})
    if not plan:
        raise HTTPException(status_code=404, detail="EMI plan not found")

    schedule = plan.get("schedule", [])
    found = False
    for s in schedule:
        if s["installment_no"] == installment_no and s["status"] == "pending":
            s["status"] = "paid"
            s["paid_at"] = datetime.now(timezone.utc).isoformat()
            found = True
            break

    if not found:
        raise HTTPException(status_code=400, detail="Installment not found or already paid")

    paid_count = sum(1 for s in schedule if s["status"] == "paid")
    total_paid = round(paid_count * plan.get("emi_amount", 0), 2)
    plan_status = "completed" if paid_count >= plan["installments"] else "active"

    await emi_plans_col.update_one({"id": plan_id}, {"$set": {
        "schedule": schedule,
        "paid_count": paid_count,
        "total_paid": total_paid,
        "status": plan_status,
    }})

    # Update sale amount received
    await sales_col.update_one({"id": plan["sale_id"]}, {"$inc": {"amount_received": plan.get("emi_amount", 0)}})

    return {"message": f"Installment #{installment_no} paid (₹{plan.get('emi_amount', 0):,.0f})", "paid_count": paid_count, "status": plan_status}


# ===================== 12C: FAMILY MEMBER MANAGEMENT =====================

class FamilyMember(BaseModel):
    name: str
    relationship: str  # spouse, child, parent, sibling
    age: int = 0
    passport_number: str = ""
    date_of_birth: str = ""
    included_in_application: bool = False
    notes: str = ""


@router.post("/family/add")
async def add_family_member(data: FamilyMember, current_user: dict = Depends(get_current_user)):
    """Add a family member"""
    member = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "name": data.name,
        "relationship": data.relationship,
        "age": data.age,
        "passport_number": data.passport_number,
        "date_of_birth": data.date_of_birth,
        "included_in_application": data.included_in_application,
        "notes": data.notes,
        "documents": [],
        "created_at": datetime.now(timezone.utc),
    }
    await family_members_col.insert_one(member)
    member.pop("_id", None)
    member["created_at"] = member["created_at"].isoformat()
    return {"message": f"Family member '{data.name}' added", "member": member}


@router.get("/family/members")
async def get_family_members(current_user: dict = Depends(get_current_user)):
    """Get all family members"""
    members = await family_members_col.find(
        {"user_id": current_user["id"]}, {"_id": 0}
    ).sort("created_at", 1).to_list(20)
    for m in members:
        if isinstance(m.get("created_at"), datetime):
            m["created_at"] = m["created_at"].isoformat()
    return members


@router.put("/family/{member_id}")
async def update_family_member(member_id: str, data: FamilyMember, current_user: dict = Depends(get_current_user)):
    """Update a family member"""
    member = await family_members_col.find_one({"id": member_id, "user_id": current_user["id"]}, {"_id": 0})
    if not member:
        raise HTTPException(status_code=404, detail="Family member not found")

    await family_members_col.update_one({"id": member_id}, {"$set": {
        "name": data.name,
        "relationship": data.relationship,
        "age": data.age,
        "passport_number": data.passport_number,
        "date_of_birth": data.date_of_birth,
        "included_in_application": data.included_in_application,
        "notes": data.notes,
        "updated_at": datetime.now(timezone.utc),
    }})
    return {"message": "Family member updated"}


@router.delete("/family/{member_id}")
async def delete_family_member(member_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a family member"""
    result = await family_members_col.delete_one({"id": member_id, "user_id": current_user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Family member not found")
    return {"message": "Family member removed"}


# ===================== 12D: DOCUMENT COMPLETION TRACKER =====================

@router.get("/document-tracker")
async def get_document_tracker(current_user: dict = Depends(get_current_user)):
    """Get document upload completion status for client's case"""
    # Get client's case
    my_cases = await cases_col.find(
        {"client_id": current_user["id"], "status": {"$in": ["active", "in_progress"]}}, {"_id": 0}
    ).to_list(10)

    if not my_cases:
        return {"cases": [], "overall_completion": 0}

    results = []
    total_required = 0
    total_uploaded = 0

    for case in my_cases:
        case_id = case["id"]
        from core.database import case_steps_col
        steps = await case_steps_col.find({"case_id": case_id}, {"_id": 0}).sort("step_order", 1).to_list(50)
        docs = await documents_col.find({"case_id": case_id}, {"_id": 0}).to_list(200)

        step_results = []
        for step in steps:
            req_docs = step.get("required_documents", [])
            step_total = len(req_docs)
            uploaded_docs = [d for d in docs if d.get("step_name") == step.get("step_name")]
            step_uploaded = len(uploaded_docs)
            verified = sum(1 for d in uploaded_docs if d.get("status") in ["verified", "approved"])

            total_required += step_total
            total_uploaded += min(step_uploaded, step_total)

            step_results.append({
                "step_name": step.get("step_name", ""),
                "step_order": step.get("step_order", 0),
                "required": step_total,
                "uploaded": step_uploaded,
                "verified": verified,
                "completion": round(min(step_uploaded, step_total) / step_total * 100) if step_total > 0 else 100,
                "documents": [{
                    "doc_name": rd.get("doc_name", ""),
                    "is_mandatory": rd.get("is_mandatory", True),
                    "uploaded": any(d.get("document_type") == rd.get("doc_name") or d.get("step_name") == step.get("step_name") for d in uploaded_docs),
                } for rd in req_docs],
            })

        case_completion = round(total_uploaded / total_required * 100) if total_required > 0 else 0
        results.append({
            "case_id": case.get("case_id", ""),
            "product_name": case.get("product_name", ""),
            "steps": step_results,
            "total_required": total_required,
            "total_uploaded": total_uploaded,
            "completion": case_completion,
        })

    overall = round(total_uploaded / total_required * 100) if total_required > 0 else 0

    return {"cases": results, "overall_completion": overall}
