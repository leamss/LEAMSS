"""Integration test suite for Complete Resume Upload, Attachment & Forwarding Workflow in CRM."""
import os
import sys
import uuid
import pytest
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from server import app
from core.auth import create_access_token
from core.database import db


@pytest.mark.asyncio
async def test_crm_resume_upload_gridfs_and_streaming():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Setup Salesperson User
        user_id = f"test_sales_rep_{uuid.uuid4().hex[:6]}"
        user_email = f"sales_{uuid.uuid4().hex[:6]}@leamss.com"
        await db["users"].update_one(
            {"id": user_id},
            {"$set": {
                "id": user_id,
                "email": user_email,
                "name": "Sarah Connor",
                "role": "sales_executive",
                "rbac_role": "sales_executive",
                "user_type": "internal",
            }},
            upsert=True
        )
        token = create_access_token({
            "sub": user_id,
            "id": user_id,
            "email": user_email,
            "role": "sales_executive",
            "rbac_role": "sales_executive",
            "name": "Sarah Connor",
            "permissions": ["*"]
        })
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Setup Lead
        lead_id = f"lead_{uuid.uuid4().hex[:6]}"
        client_email = f"candidate_{uuid.uuid4().hex[:6]}@example.com"
        await db["leads"].update_one(
            {"id": lead_id},
            {"$set": {
                "id": lead_id,
                "name": "John Connor",
                "email": client_email,
                "phone": "+91 98765 43210",
                "country_of_interest": "Canada",
                "service_interested": "Express Entry PR",
                "stage": "new",
                "source": "Website",
            }},
            upsert=True
        )

        # 3. Upload Resume via POST /api/leads/{id}/resume
        dummy_pdf_bytes = b"%PDF-1.4 dummy pdf resume content for testing purposes"
        files = {
            "file": ("John_Connor_CV.pdf", dummy_pdf_bytes, "application/pdf")
        }
        upload_res = await client.post(
            f"/api/leads/{lead_id}/resume",
            files=files,
            headers=headers
        )
        assert upload_res.status_code == 200, f"Upload failed: {upload_res.text}"
        data = upload_res.json()
        assert data.get("ok") is True
        file_id = data.get("resume_file_id")
        assert file_id is not None
        assert data.get("resume_filename") == "John_Connor_CV.pdf"

        # 4. Verify Lead document in MongoDB
        lead_doc = await db["leads"].find_one({"id": lead_id})
        assert lead_doc.get("resume_file_id") == file_id
        assert lead_doc.get("resume_uploaded") is True
        assert lead_doc.get("resume_filename") == "John_Connor_CV.pdf"

        # 5. Verify Streaming via /api/cockpit/resume/{file_id}
        stream_res = await client.get(f"/api/cockpit/resume/{file_id}")
        assert stream_res.status_code == 200
        assert stream_res.content == dummy_pdf_bytes

        # 6. Verify Streaming with Lead ID fallback resolution
        fallback_res = await client.get(f"/api/cockpit/resume/{lead_id}")
        assert fallback_res.status_code == 200
        assert fallback_res.content == dummy_pdf_bytes


@pytest.mark.asyncio
async def test_resume_persistence_across_conversions_and_handover():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Setup Admin / Sales User
        admin_id = f"admin_{uuid.uuid4().hex[:6]}"
        admin_email = f"admin_{uuid.uuid4().hex[:6]}@leamss.com"
        await db["users"].update_one(
            {"id": admin_id},
            {"$set": {
                "id": admin_id,
                "email": admin_email,
                "name": "Super Admin",
                "role": "admin",
                "rbac_role": "admin",
            }},
            upsert=True
        )
        token = create_access_token({
            "sub": admin_id,
            "id": admin_id,
            "email": admin_email,
            "role": "admin",
            "rbac_role": "admin",
            "name": "Super Admin",
            "permissions": ["*"]
        })
        headers = {"Authorization": f"Bearer {token}"}

        # Setup Lead with existing resume attached
        lead_id = f"lead_{uuid.uuid4().hex[:6]}"
        client_email = f"client_{uuid.uuid4().hex[:6]}@example.com"
        fake_file_id = "507f1f77bcf86cd799439011"
        await db["leads"].update_one(
            {"id": lead_id},
            {"$set": {
                "id": lead_id,
                "name": "Alice Wonderland",
                "email": client_email,
                "phone": "+91 91234 56789",
                "country_of_interest": "Australia",
                "service_interested": "General Skilled Migration",
                "resume_file_id": fake_file_id,
                "resume_filename": "Alice_Wonderland_Resume.pdf",
                "resume_url": f"/cockpit/resume/{fake_file_id}",
                "resume_uploaded": True,
                "stage": "qualified",
                "source": "Website",
            }},
            upsert=True
        )

        # 1. Convert Lead to Client via POST /api/leads/{id}/convert-to-client
        conv_client_res = await client.post(
            f"/api/leads/{lead_id}/convert-to-client",
            json={"package_price": 65000, "paid_amount": 65000},
            headers=headers
        )
        assert conv_client_res.status_code == 200, f"Convert to client failed: {conv_client_res.text}"
        conv_client_data = conv_client_res.json()
        client_id = conv_client_data.get("client_id")

        client_user = await db["users"].find_one({"id": client_id})
        assert client_user is not None
        assert client_user.get("resume_file_id") == fake_file_id
        assert client_user.get("resume_filename") == "Alice_Wonderland_Resume.pdf"
        assert client_user.get("resume_uploaded") is True

        # 2. Convert Lead to Pre-Assessment via POST /api/leads/{id}/convert-to-pa
        conv_pa_res = await client.post(
            f"/api/leads/{lead_id}/convert-to-pa",
            json={"service_type": "General Skilled Migration"},
            headers=headers
        )
        assert conv_pa_res.status_code == 200, f"Convert to PA failed: {conv_pa_res.text}"
        pa_id = conv_pa_res.json().get("pa_id")

        pa_doc = await db["pre_assessments"].find_one({"id": pa_id})
        assert pa_doc is not None
        assert pa_doc.get("resume_file_id") == fake_file_id
        assert pa_doc.get("resume_filename") == "Alice_Wonderland_Resume.pdf"
        assert pa_doc.get("resume_uploaded") is True

        pa_doc_record = await db["pre_assessment_documents"].find_one({"pre_assessment_id": pa_id, "doc_type": "resume"})
        assert pa_doc_record is not None
        assert pa_doc_record.get("file_url") == f"/cockpit/resume/{fake_file_id}"

        # 3. Handover to Case Manager via POST /api/leads/{id}/case-manager-handover
        cm_id = f"cm_{uuid.uuid4().hex[:6]}"
        await db["users"].update_one(
            {"id": cm_id},
            {"$set": {"id": cm_id, "name": "David Case Manager", "email": f"cm_{cm_id}@leamss.com", "role": "case_manager"}},
            upsert=True
        )
        handover_res = await client.post(
            f"/api/leads/{lead_id}/case-manager-handover",
            json={"case_manager_id": cm_id, "notes": "Handoff with verified resume"},
            headers=headers
        )
        assert handover_res.status_code == 200, f"Handover failed: {handover_res.text}"
        case_id = handover_res.json().get("case_id")

        case_doc = await db["cases"].find_one({"case_id": case_id})
        assert case_doc is not None
        assert case_doc.get("resume_file_id") == fake_file_id
        assert case_doc.get("resume_filename") == "Alice_Wonderland_Resume.pdf"
        assert case_doc.get("resume_uploaded") is True

        case_doc_record = await db["documents"].find_one({"case_id": case_id, "doc_type": "resume"})
        assert case_doc_record is not None
        assert case_doc_record.get("file_url") == f"/cockpit/resume/{fake_file_id}"


@pytest.mark.asyncio
async def test_pipeline_summary_exposes_resume_fields():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_id = f"admin_{uuid.uuid4().hex[:6]}"
        admin_email = f"admin_{uuid.uuid4().hex[:6]}@leamss.com"
        await db["users"].update_one(
            {"id": admin_id},
            {"$set": {"id": admin_id, "email": admin_email, "role": "admin", "rbac_role": "admin"}},
            upsert=True
        )
        token = create_access_token({
            "sub": admin_id, "id": admin_id, "email": admin_email, "role": "admin", "rbac_role": "admin", "permissions": ["*"]
        })
        headers = {"Authorization": f"Bearer {token}"}

        # Seed lead with resume in converted stage
        lead_id = f"lead_{uuid.uuid4().hex[:6]}"
        resume_fid = "607f1f77bcf86cd799439022"
        await db["leads"].update_one(
            {"id": lead_id},
            {"$set": {
                "id": lead_id,
                "name": "Converted Candidate With Resume",
                "email": f"conv_{uuid.uuid4().hex[:6]}@example.com",
                "stage": "converted",
                "resume_file_id": resume_fid,
                "resume_filename": "Candidate_CV.pdf",
                "resume_uploaded": True,
            }},
            upsert=True
        )

        res = await client.get("/api/partner-analytics/pipeline-summary", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert "converted" in data
        converted_items = data["converted"]["items"]
        target_item = next((i for i in converted_items if i.get("id") == lead_id or i.get("lead_id") == lead_id), None)
        assert target_item is not None, "Target converted lead should be in pipeline summary"
        assert target_item.get("resume_file_id") == resume_fid
        assert target_item.get("resume_uploaded") is True
        assert target_item.get("resume_filename") == "Candidate_CV.pdf"


@pytest.mark.asyncio
async def test_crm_email_auto_attach_resume(monkeypatch):
    from core.resume_service import save_resume_to_gridfs

    dummy_pdf = b"%PDF-1.4 sample content for email auto attachment"
    file_id_str, _ = await save_resume_to_gridfs(
        filename="Attached_Candidate_Resume.pdf",
        file_bytes=dummy_pdf,
        content_type="application/pdf"
    )

    lead_id = f"lead_{uuid.uuid4().hex[:6]}"
    client_email = f"lead_{uuid.uuid4().hex[:6]}@example.com"
    await db["leads"].update_one(
        {"id": lead_id},
        {"$set": {
            "id": lead_id,
            "name": "Bruce Wayne",
            "email": client_email,
            "resume_file_id": file_id_str,
            "resume_filename": "Attached_Candidate_Resume.pdf",
            "resume_uploaded": True,
        }},
        upsert=True
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        user_id = f"user_{uuid.uuid4().hex[:6]}"
        user_email = f"agent_{uuid.uuid4().hex[:6]}@leamss.com"
        await db["users"].update_one(
            {"id": user_id},
            {"$set": {"id": user_id, "email": user_email, "name": "Agent Smith", "role": "sales_executive"}},
            upsert=True
        )
        token = create_access_token({
            "sub": user_id, "id": user_id, "email": user_email, "role": "sales_executive", "permissions": ["*"]
        })
        headers = {"Authorization": f"Bearer {token}"}

        # Mock dispatch_email to capture attachments without real SMTP network call
        captured = {}
        async def mock_dispatch_email(**kwargs):
            captured.update(kwargs)
            return {"status": "delivered", "provider": "mock", "message_id": f"<mock_{uuid.uuid4().hex}@leamss.com>"}

        import routers.crm_communication as crm_comm
        monkeypatch.setattr(crm_comm, "dispatch_email", mock_dispatch_email)

        # Send email with attach_resume: True
        send_res = await client.post(
            "/api/crm/emails/send",
            json={
                "lead_id": lead_id,
                "to_email": "employer@partner.com",
                "subject": "Forwarding Candidate Profile: Bruce Wayne",
                "body_html": "<p>Please see profile and attached resume.</p>",
                "attach_resume": True,
            },
            headers=headers
        )
        assert send_res.status_code == 200, f"Send email failed: {send_res.text}"
        assert captured.get("attachments"), "Attachments should be non-empty"
        attached_resume = next((a for a in captured["attachments"] if a.get("file_id") == file_id_str), None)
        assert attached_resume is not None, "Candidate resume should be attached to email dispatch"
        assert attached_resume.get("filename") == "Attached_Candidate_Resume.pdf"
        assert attached_resume.get("bytes") == dummy_pdf


@pytest.mark.asyncio
async def test_public_resume_upload_updates_lead_and_streaming():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Setup primary lead and duplicate lead (counterpart)
        lead_id = f"lead_{uuid.uuid4().hex[:8]}"
        dup_lead_id = f"lead_{uuid.uuid4().hex[:8]}"
        test_email = f"lead_test_{uuid.uuid4().hex[:8]}@example.com"
        test_phone = f"989{uuid.uuid4().int % 10000000:07d}"

        await db["leads"].insert_many([
            {
                "id": lead_id,
                "lead_number": f"LD{uuid.uuid4().hex[:6].upper()}",
                "name": "Integration Test Lead",
                "email": test_email,
                "phone": test_phone,
                "stage": "contacted",
                "resume_file_id": None,
                "resume_uploaded": False,
                "timeline": [],
            },
            {
                "id": dup_lead_id,
                "lead_number": f"LD{uuid.uuid4().hex[:6].upper()}",
                "name": "Integration Test Duplicate",
                "email": test_email,
                "phone": test_phone,
                "stage": "new",
                "resume_file_id": None,
                "resume_uploaded": False,
                "timeline": [],
            }
        ])

        # 2. Client performs public upload via /api/public/resume-upload/{token}
        import io
        from reportlab.pdfgen import canvas
        buf = io.BytesIO()
        c = canvas.Canvas(buf)
        c.drawString(100, 750, "Valid Test Resume PDF Content")
        c.save()
        pdf_content = buf.getvalue()

        files = {
            "file": ("Integration_Test_Resume.pdf", pdf_content, "application/pdf")
        }
        res = await client.post(f"/api/public/resume-upload/{lead_id}", files=files)
        assert res.status_code == 200, f"Public upload failed: {res.text}"
        data = res.json()
        assert data.get("ok") is True
        file_id = data.get("resume_file_id")
        assert file_id is not None
        assert data.get("resume_filename") == "Integration_Test_Resume.pdf"

        # 3. Check that primary lead has resume attached
        doc1 = await db["leads"].find_one({"id": lead_id})
        assert doc1["resume_file_id"] == file_id
        assert doc1["resume_filename"] == "Integration_Test_Resume.pdf"
        assert doc1["resume_uploaded"] is True
        assert doc1["resume_url"] == f"/cockpit/resume/{file_id}"
        # Timeline should record the upload
        timeline_actions = [t.get("action") for t in (doc1.get("timeline") or [])]
        assert "resume_uploaded" in timeline_actions

        # 4. Check that counterpart duplicate lead also received synced resume
        doc2 = await db["leads"].find_one({"id": dup_lead_id})
        assert doc2["resume_file_id"] == file_id
        assert doc2["resume_filename"] == "Integration_Test_Resume.pdf"
        assert doc2["resume_uploaded"] is True

        # 5. Verify streaming endpoint serves the uploaded resume
        stream_res = await client.get(f"/api/cockpit/resume/{file_id}")
        assert stream_res.status_code == 200
        assert stream_res.content == pdf_content


@pytest.mark.asyncio
async def test_assessment_report_requires_resume():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Setup Admin user
        admin_id = f"admin_{uuid.uuid4().hex[:6]}"
        admin_email = f"admin_{uuid.uuid4().hex[:6]}@leamss.com"
        await db["users"].update_one(
            {"id": admin_id},
            {"$set": {"id": admin_id, "email": admin_email, "role": "admin", "rbac_role": "admin", "name": "Admin Tester"}},
            upsert=True
        )
        token = create_access_token({
            "sub": admin_id, "id": admin_id, "email": admin_email, "role": "admin", "rbac_role": "admin", "permissions": ["*"]
        })
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Setup lead WITHOUT resume
        lead_id = f"lead_{uuid.uuid4().hex[:8]}"
        lead_number = f"LD{uuid.uuid4().hex[:6].upper()}"
        await db["leads"].insert_one({
            "id": lead_id,
            "lead_number": lead_number,
            "name": "Manali Patkar Test",
            "email": f"manali_{uuid.uuid4().hex[:6]}@example.com",
            "phone": f"987{uuid.uuid4().int % 10000000:07d}",
            "country_of_interest": "Australia",
            "service_interested": "PR 189/190",
            "stage": "new",
            "resume_file_id": None,
            "resume_uploaded": False,
        })

        # 3. Attempt generating report without resume -> MUST fail with HTTP 400
        res_no_resume = await client.post(
            f"/api/crm/leads/{lead_id}/generate-assessment-report",
            json={"force_regenerate": True},
            headers=headers
        )
        assert res_no_resume.status_code == 400
        assert "resume" in res_no_resume.json().get("detail", "").lower()

        # 4. Attach valid resume to lead
        import io
        from reportlab.pdfgen import canvas
        buf = io.BytesIO()
        c = canvas.Canvas(buf)
        c.drawString(100, 750, "Valid Candidate Resume for Assessment")
        c.save()
        valid_pdf = buf.getvalue()

        files = {"file": ("Manali_Patkar_Resume.pdf", valid_pdf, "application/pdf")}
        upload_res = await client.post(f"/api/leads/{lead_id}/resume", files=files, headers=headers)
        assert upload_res.status_code == 200

        # 5. Attempt generating report with resume attached -> MUST succeed
        res_with_resume = await client.post(
            f"/api/crm/leads/{lead_id}/generate-assessment-report",
            json={"force_regenerate": True},
            headers=headers
        )
        assert res_with_resume.status_code == 200, f"Report generation failed: {res_with_resume.text}"
        data = res_with_resume.json()
        assert data.get("success") is True
        assert data.get("snapshot_id") is not None


@pytest.mark.asyncio
async def test_crm_resume_status_and_candidate_name_phone_sync():
    """Verify GET /api/crm/leads/{id}/resume-status auto-syncs across duplicate records by name/phone/email."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Setup Sales User
        sales_id = f"sales_{uuid.uuid4().hex[:6]}"
        sales_email = f"sales_{uuid.uuid4().hex[:6]}@leamss.com"
        await db["users"].update_one(
            {"id": sales_id},
            {"$set": {
                "id": sales_id,
                "email": sales_email,
                "name": "Sarah Connor",
                "role": "sales_executive",
                "rbac_role": "sales_executive",
                "user_type": "internal",
            }},
            upsert=True
        )
        token = create_access_token({
            "sub": sales_id, "id": sales_id, "email": sales_email,
            "role": "sales_executive", "rbac_role": "sales_executive", "permissions": ["*"]
        })
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Setup Lead A (No resume, phone with country code & spaces)
        phone_digits = f"982{uuid.uuid4().int % 10000000:07d}"
        cand_name = f"Candidate MultiSync {uuid.uuid4().hex[:4]}"
        lead_a_id = f"lead_a_{uuid.uuid4().hex[:6]}"
        await db["leads"].insert_one({
            "id": lead_a_id,
            "name": cand_name,
            "email": f"cand_a_{uuid.uuid4().hex[:6]}@example.com",
            "phone": f"+91 {phone_digits[:5]} {phone_digits[5:]}",
            "stage": "new",
            "resume_file_id": None,
            "resume_uploaded": False,
        })

        # 3. Setup Lead B (Same candidate, uploaded resume)
        lead_b_id = f"lead_b_{uuid.uuid4().hex[:6]}"
        await db["leads"].insert_one({
            "id": lead_b_id,
            "name": cand_name,
            "email": f"cand_b_{uuid.uuid4().hex[:6]}@example.com",
            "phone": phone_digits,
            "stage": "converted",
            "resume_file_id": None,
            "resume_uploaded": False,
        })

        # Upload resume to Lead B
        import io
        from reportlab.pdfgen import canvas
        buf = io.BytesIO()
        c = canvas.Canvas(buf)
        c.drawString(100, 750, "Resume Content for Candidate MultiSync")
        c.save()
        files = {"file": ("Candidate_Sync_CV.pdf", buf.getvalue(), "application/pdf")}
        upload_res = await client.post(f"/api/leads/{lead_b_id}/resume", files=files, headers=headers)
        assert upload_res.status_code == 200

        # 4. Check resume status on Lead A -> MUST auto-sync and return has_resume = True
        status_res = await client.get(f"/api/crm/leads/{lead_a_id}/resume-status", headers=headers)
        assert status_res.status_code == 200
        data = status_res.json()
        assert data.get("has_resume") is True
        assert data.get("resume_filename") == "Candidate_Sync_CV.pdf"

        # 5. Verify Lead A in MongoDB is now updated
        lead_a_doc = await db["leads"].find_one({"id": lead_a_id})
        assert lead_a_doc.get("resume_uploaded") is True
        assert lead_a_doc.get("resume_filename") == "Candidate_Sync_CV.pdf"
        assert lead_a_doc.get("resume_file_id") is not None


@pytest.mark.asyncio
async def test_generate_assessment_report_returns_assessment_id_and_hydrates():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Setup Admin user
        admin_id = f"admin_{uuid.uuid4().hex[:6]}"
        admin_email = f"admin_{uuid.uuid4().hex[:6]}@leamss.com"
        await db["users"].update_one(
            {"id": admin_id},
            {"$set": {"id": admin_id, "email": admin_email, "role": "admin", "rbac_role": "admin", "name": "Admin Tester"}},
            upsert=True
        )
        token = create_access_token({
            "sub": admin_id, "id": admin_id, "email": admin_email, "role": "admin", "rbac_role": "admin", "permissions": ["*"]
        })
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Setup lead with attached resume
        lead_id = f"lead_{uuid.uuid4().hex[:8]}"
        lead_number = f"LD{uuid.uuid4().hex[:6].upper()}"
        from motor.motor_asyncio import AsyncIOMotorGridFSBucket
        gridfs = AsyncIOMotorGridFSBucket(db)
        import io
        from reportlab.pdfgen import canvas
        buf = io.BytesIO()
        c = canvas.Canvas(buf)
        c.drawString(100, 750, "Resume Content for Assessment Report Test")
        c.save()
        file_id = str(await gridfs.upload_from_stream(
            "Test_Resume.pdf", io.BytesIO(buf.getvalue()), metadata={"lead_id": lead_id}
        ))

        await db["leads"].insert_one({
            "id": lead_id,
            "lead_number": lead_number,
            "name": "Manali Patkar Hydro Test",
            "email": f"manali_hydro_{uuid.uuid4().hex[:6]}@example.com",
            "phone": "9876543210",
            "country_of_interest": "Australia",
            "occupation": "Software Engineer",
            "occupation_code": "261313",
            "education": "Master's Degree",
            "experience_years": 5.0,
            "stage": "attempted",
            "resume_file_id": file_id,
            "resume_filename": "Test_Resume.pdf",
            "resume_url": f"/cockpit/resume/{file_id}",
            "resume_uploaded": True,
        })

        # 3. Call generate-assessment-report
        gen_res = await client.post(
            f"/api/crm/leads/{lead_id}/generate-assessment-report",
            json={"force_regenerate": True},
            headers=headers
        )
        assert gen_res.status_code == 200
        gen_data = gen_res.json()
        assert gen_data.get("success") is True
        assert gen_data.get("snapshot_id") is not None
        assert gen_data.get("assessment_id") is not None
        asm_id = gen_data["assessment_id"]

        # 4. Fetch the assessment via /api/sales/assessments/{id}
        fetch_res = await client.get(f"/api/sales/assessments/{asm_id}", headers=headers)
        assert fetch_res.status_code == 200
        asm_doc = fetch_res.json()
        assert asm_doc.get("id") == asm_id
        assert asm_doc.get("client_name") == "Manali Patkar Hydro Test"
        assert asm_doc.get("resume_file_id") == file_id
        assert asm_doc.get("profile") is not None
        assert asm_doc["profile"]["primary_applicant"]["education"]["highest_qualification"] == "Master's Degree"
        assert asm_doc["profile"]["primary_applicant"]["professional"]["years_experience_total"] == 5.0


@pytest.mark.asyncio
async def test_crm_pre_assessment_report_upload_attachment_and_retrieval():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Setup Admin/Sales user
        user_id = f"test_rep_{uuid.uuid4().hex[:6]}"
        user_email = f"rep_{uuid.uuid4().hex[:6]}@leamss.com"
        await db["users"].update_one(
            {"id": user_id},
            {"$set": {
                "id": user_id,
                "email": user_email,
                "name": "Alex Vance",
                "role": "admin",
                "rbac_role": "admin",
                "user_type": "internal",
            }},
            upsert=True
        )
        token = create_access_token({
            "sub": user_id,
            "id": user_id,
            "email": user_email,
            "role": "admin",
            "rbac_role": "admin",
            "name": "Alex Vance",
            "permissions": ["*"]
        })
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Setup Lead
        lead_id = f"lead_{uuid.uuid4().hex[:6]}"
        client_email = f"client_{uuid.uuid4().hex[:6]}@example.com"
        await db["leads"].update_one(
            {"id": lead_id},
            {"$set": {
                "id": lead_id,
                "name": "Gordon Freeman",
                "email": client_email,
                "phone": "+91 91234 56789",
                "country_of_interest": "Australia",
                "service_interested": "GSM PR Visa",
                "stage": "qualified",
                "source": "Website",
            }},
            upsert=True
        )

        # 3. Upload Pre-Assessment Report via POST /api/leads/{id}/pre-assessment-report
        dummy_pdf_bytes = b"%PDF-1.4 dummy pre-assessment report content"
        files = {
            "file": ("Gordon_Freeman_Pre_Assessment_Report.pdf", dummy_pdf_bytes, "application/pdf")
        }
        upload_res = await client.post(
            f"/api/leads/{lead_id}/pre-assessment-report",
            files=files,
            headers=headers
        )
        assert upload_res.status_code == 200, f"Upload failed: {upload_res.text}"
        data = upload_res.json()
        assert data.get("ok") is True
        file_id = data.get("assessment_report_file_id")
        assert file_id is not None
        assert data.get("assessment_report_filename") == "Gordon_Freeman_Pre_Assessment_Report.pdf"

        # 4. Verify MongoDB Lead Document
        lead_doc = await db["leads"].find_one({"id": lead_id})
        assert lead_doc.get("assessment_report_file_id") == file_id
        assert lead_doc.get("has_pre_assessment_report") is True
        assert lead_doc.get("assessment_report_filename") == "Gordon_Freeman_Pre_Assessment_Report.pdf"
        assert lead_doc.get("report_status") == "attached"

        # 5. Verify direct GET /api/leads/{id}/pre-assessment-report
        lead_report_res = await client.get(f"/api/leads/{lead_id}/pre-assessment-report", headers=headers)
        assert lead_report_res.status_code == 200
        assert lead_report_res.content == dummy_pdf_bytes

        # 6. Verify streaming via /api/cockpit/resume/{file_id}
        cockpit_res = await client.get(f"/api/cockpit/resume/{file_id}")
        assert cockpit_res.status_code == 200
        assert cockpit_res.content == dummy_pdf_bytes


@pytest.mark.asyncio
async def test_website_form_submission_with_attached_resume_multipart():
    """Verify website form capture endpoint accepts multipart form data with resume file attached."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        unique_suffix = uuid.uuid4().hex[:6]
        resume_bytes = b"%PDF-1.4 website applicant resume payload testing binary"
        form_data = {
            "name": f"Alex Johnson {unique_suffix}",
            "email": f"alex.johnson.{unique_suffix}@gmail.com",
            "phone": "+91 98888 77777",
            "country_of_interest": "Canada",
            "service_interested": "Express Entry",
            "source": "Website Form",
        }
        files = {
            "file": (f"Alex_{unique_suffix}_CV.pdf", resume_bytes, "application/pdf")
        }

        # Submit to /api/crm/website-leads/capture
        resp = await client.post("/api/crm/website-leads/capture", data=form_data, files=files)
        assert resp.status_code == 200, f"Capture failed: {resp.text}"
        res_data = resp.json()
        assert res_data.get("ok") is True or "id" in res_data
        lead_id = res_data.get("id") or res_data.get("lead_id")
        assert lead_id is not None

        # Verify MongoDB Lead Document
        lead_doc = await db["leads"].find_one({"id": lead_id})
        assert lead_doc is not None
        assert lead_doc.get("resume_uploaded") is True
        assert lead_doc.get("resume_file_id") is not None
        assert lead_doc.get("resume_filename") == f"Alex_{unique_suffix}_CV.pdf"

        # Verify Resume Streaming via /api/cockpit/resume/{lead_id}
        stream_by_lead = await client.get(f"/api/cockpit/resume/{lead_id}")
        assert stream_by_lead.status_code == 200
        assert stream_by_lead.content == resume_bytes

        # Verify Resume Streaming via /api/cockpit/resume/{file_id}
        stream_by_fid = await client.get(f"/api/cockpit/resume/{lead_doc['resume_file_id']}")
        assert stream_by_fid.status_code == 200
        assert stream_by_fid.content == resume_bytes


@pytest.mark.asyncio
async def test_website_form_submission_with_resume_url():
    """Verify website form capture endpoint accepts JSON payload with resume_url and exposes resume streaming."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        unique_suffix = uuid.uuid4().hex[:6]
        payload = {
            "name": f"Priya Sharma {unique_suffix}",
            "email": f"priya.sharma.{unique_suffix}@gmail.com",
            "phone": "+91 97777 66666",
            "country_of_interest": "Australia",
            "service_interested": "Subclass 189",
            "source": "Website Form",
            "resume_url": f"https://leamss.com/public/uploads/resumes/priya_{unique_suffix}_resume.pdf",
        }

        resp = await client.post("/api/crm/website-leads/capture", json=payload)
        assert resp.status_code == 200, f"JSON capture failed: {resp.text}"
        res_data = resp.json()
        lead_id = res_data.get("id") or res_data.get("lead_id")
        assert lead_id is not None

        # Check lead document has resume metadata
        lead_doc = await db["leads"].find_one({"id": lead_id})
        assert lead_doc is not None
        assert lead_doc.get("resume_url") == payload["resume_url"]
        assert lead_doc.get("resume_uploaded") is True
        assert lead_doc.get("resume_filename") == f"priya_{unique_suffix}_resume.pdf"






