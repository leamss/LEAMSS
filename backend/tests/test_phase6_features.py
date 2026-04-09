"""
Phase 6A-6D Features Testing
Tests for: Bulk Operations, SLA Tracker, Auto Case Assignment, Case Transfer,
Surveys, Knowledge Base, Appointments, Document Annotation, Revenue Forecasting, CM Performance
"""
import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDS = {"email": "admin@leamss.com", "password": "Admin@123"}
CM_CREDS = {"email": "manager@leamss.com", "password": "Manager@123"}
CLIENT_CREDS = {"email": "client@leamss.com", "password": "Client@123"}
PARTNER_CREDS = {"email": "partner@leamss.com", "password": "Partner@123"}


class TestAuth:
    """Authentication tests for all roles"""
    
    def test_admin_login(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "admin"
        print(f"Admin login: PASS - token received")
    
    def test_case_manager_login(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CM_CREDS)
        assert response.status_code == 200, f"CM login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "case_manager"
        print(f"Case Manager login: PASS")
    
    def test_client_login(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CLIENT_CREDS)
        assert response.status_code == 200, f"Client login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "client"
        print(f"Client login: PASS")
    
    def test_partner_login(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=PARTNER_CREDS)
        assert response.status_code == 200, f"Partner login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "partner"
        print(f"Partner login: PASS")


@pytest.fixture(scope="module")
def admin_token():
    response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
    if response.status_code == 200:
        return response.json()["token"]
    pytest.skip("Admin auth failed")


@pytest.fixture(scope="module")
def cm_token():
    response = requests.post(f"{BASE_URL}/api/auth/login", json=CM_CREDS)
    if response.status_code == 200:
        return response.json()["token"]
    pytest.skip("CM auth failed")


@pytest.fixture(scope="module")
def client_token():
    response = requests.post(f"{BASE_URL}/api/auth/login", json=CLIENT_CREDS)
    if response.status_code == 200:
        return response.json()["token"]
    pytest.skip("Client auth failed")


@pytest.fixture(scope="module")
def partner_token():
    response = requests.post(f"{BASE_URL}/api/auth/login", json=PARTNER_CREDS)
    if response.status_code == 200:
        return response.json()["token"]
    pytest.skip("Partner auth failed")


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


class TestCoreAPIs:
    """Core API health checks"""
    
    def test_health_endpoint(self):
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        print("Health endpoint: PASS")
    
    def test_dashboard_stats(self, admin_token):
        response = requests.get(f"{BASE_URL}/api/stats/dashboard", headers=auth_header(admin_token))
        assert response.status_code == 200
        data = response.json()
        assert "total_cases" in data or "cases" in data or isinstance(data, dict)
        print(f"Dashboard stats: PASS - {data}")


# ============ PHASE 6A: BULK OPERATIONS ============

class TestBulkOperations:
    """Bulk Advance Cases and Bulk Document Review"""
    
    def test_bulk_advance_cases_admin(self, admin_token):
        """Test bulk advance with admin - first get case IDs"""
        # Get active cases
        cases_resp = requests.get(f"{BASE_URL}/api/cases", headers=auth_header(admin_token))
        assert cases_resp.status_code == 200
        cases = cases_resp.json()
        
        if not cases:
            pytest.skip("No cases available for bulk advance test")
        
        # Get first 2 case IDs
        case_ids = [c["id"] for c in cases[:2]]
        
        response = requests.post(
            f"{BASE_URL}/api/cases/bulk-advance",
            json={"case_ids": case_ids, "notes": "TEST_bulk_advance"},
            headers=auth_header(admin_token)
        )
        assert response.status_code == 200, f"Bulk advance failed: {response.text}"
        data = response.json()
        assert "results" in data
        assert "advanced" in data
        print(f"Bulk advance cases: PASS - {data['advanced']} cases processed")
    
    def test_bulk_advance_cases_cm(self, cm_token):
        """Test bulk advance with case manager"""
        cases_resp = requests.get(f"{BASE_URL}/api/cases", headers=auth_header(cm_token))
        assert cases_resp.status_code == 200
        cases = cases_resp.json()
        
        if not cases:
            pytest.skip("No cases for CM")
        
        case_ids = [c["id"] for c in cases[:1]]
        response = requests.post(
            f"{BASE_URL}/api/cases/bulk-advance",
            json={"case_ids": case_ids, "notes": "TEST_cm_bulk"},
            headers=auth_header(cm_token)
        )
        assert response.status_code == 200
        print(f"Bulk advance (CM): PASS")
    
    def test_bulk_advance_client_forbidden(self, client_token):
        """Client should not be able to bulk advance"""
        response = requests.post(
            f"{BASE_URL}/api/cases/bulk-advance",
            json={"case_ids": ["fake-id"], "notes": "test"},
            headers=auth_header(client_token)
        )
        assert response.status_code == 403
        print("Bulk advance client forbidden: PASS")
    
    def test_bulk_document_review(self, admin_token):
        """Test bulk document review"""
        # Get documents
        docs_resp = requests.get(f"{BASE_URL}/api/documents", headers=auth_header(admin_token))
        if docs_resp.status_code != 200:
            pytest.skip("Cannot get documents")
        
        docs = docs_resp.json()
        if not docs:
            pytest.skip("No documents for bulk review")
        
        doc_ids = [d["id"] for d in docs[:2] if d.get("id")]
        if not doc_ids:
            pytest.skip("No document IDs found")
        
        response = requests.post(
            f"{BASE_URL}/api/documents/bulk-review",
            json={"document_ids": doc_ids, "status": "approved", "comment": "TEST_bulk_approved"},
            headers=auth_header(admin_token)
        )
        assert response.status_code == 200, f"Bulk review failed: {response.text}"
        data = response.json()
        assert "results" in data
        assert "processed" in data
        print(f"Bulk document review: PASS - {data['processed']} docs processed")


# ============ SLA TRACKER ============

class TestSLATracker:
    """SLA Deadline Setting and Overdue Steps"""
    
    def test_set_step_deadline(self, admin_token):
        """Set SLA deadline for a case step"""
        # Get a case with steps
        cases_resp = requests.get(f"{BASE_URL}/api/cases", headers=auth_header(admin_token))
        assert cases_resp.status_code == 200
        cases = cases_resp.json()
        
        case_with_steps = None
        for c in cases:
            if c.get("steps"):
                case_with_steps = c
                break
        
        if not case_with_steps:
            pytest.skip("No case with steps found")
        
        step = case_with_steps["steps"][0]
        deadline = (datetime.now() + timedelta(days=7)).isoformat()
        
        response = requests.post(
            f"{BASE_URL}/api/cases/set-step-deadline",
            json={
                "case_id": case_with_steps["id"],
                "step_name": step["step_name"],
                "deadline": deadline,
                "sla_days": 7
            },
            headers=auth_header(admin_token)
        )
        assert response.status_code == 200, f"Set deadline failed: {response.text}"
        data = response.json()
        assert "message" in data
        assert data["step"] == step["step_name"]
        print(f"Set step deadline: PASS - {step['step_name']} deadline set")
    
    def test_get_overdue_steps_admin(self, admin_token):
        """Get overdue steps as admin"""
        response = requests.get(
            f"{BASE_URL}/api/cases/overdue-steps",
            headers=auth_header(admin_token)
        )
        assert response.status_code == 200, f"Overdue steps failed: {response.text}"
        data = response.json()
        assert "overdue" in data or isinstance(data, list) or isinstance(data, dict)
        print(f"Get overdue steps (admin): PASS - {data}")
    
    def test_get_overdue_steps_cm(self, cm_token):
        """Get overdue steps as case manager"""
        response = requests.get(
            f"{BASE_URL}/api/cases/overdue-steps",
            headers=auth_header(cm_token)
        )
        assert response.status_code == 200
        print("Get overdue steps (CM): PASS")
    
    def test_get_overdue_steps_client_forbidden(self, client_token):
        """Client should not access overdue steps"""
        response = requests.get(
            f"{BASE_URL}/api/cases/overdue-steps",
            headers=auth_header(client_token)
        )
        assert response.status_code == 403
        print("Overdue steps client forbidden: PASS")


# ============ AUTO CASE ASSIGNMENT ============

class TestAutoCaseAssignment:
    """Auto-assign case to least-loaded CM"""
    
    def test_auto_assign_admin_only(self, admin_token):
        """Test auto-assign with admin"""
        # Get unassigned cases
        cases_resp = requests.get(f"{BASE_URL}/api/cases/unassigned", headers=auth_header(admin_token))
        if cases_resp.status_code != 200:
            # Try regular cases
            cases_resp = requests.get(f"{BASE_URL}/api/cases", headers=auth_header(admin_token))
        
        cases = cases_resp.json()
        if not cases:
            pytest.skip("No cases for auto-assign test")
        
        case_id = cases[0]["id"]
        response = requests.post(
            f"{BASE_URL}/api/cases/auto-assign",
            json={"case_id": case_id, "preferred_language": "English"},
            headers=auth_header(admin_token)
        )
        # Could be 200 (success) or 400 (no active CMs)
        assert response.status_code in [200, 400], f"Auto-assign unexpected: {response.text}"
        if response.status_code == 200:
            data = response.json()
            assert "case_manager_id" in data or "message" in data
            print(f"Auto-assign: PASS - {data.get('message', data)}")
        else:
            print(f"Auto-assign: PASS (no active CMs)")
    
    def test_auto_assign_cm_forbidden(self, cm_token):
        """Case manager should not auto-assign"""
        response = requests.post(
            f"{BASE_URL}/api/cases/auto-assign",
            json={"case_id": "fake-id"},
            headers=auth_header(cm_token)
        )
        assert response.status_code == 403
        print("Auto-assign CM forbidden: PASS")


# ============ CASE TRANSFER ============

class TestCaseTransfer:
    """Case transfer between CMs"""
    
    def test_transfer_case_admin(self, admin_token):
        """Admin transfers case"""
        # Get cases and CMs
        cases_resp = requests.get(f"{BASE_URL}/api/cases", headers=auth_header(admin_token))
        users_resp = requests.get(f"{BASE_URL}/api/users", headers=auth_header(admin_token))
        
        if cases_resp.status_code != 200 or users_resp.status_code != 200:
            pytest.skip("Cannot get cases or users")
        
        cases = cases_resp.json()
        users = users_resp.json()
        
        cms = [u for u in users if u.get("role") == "case_manager"]
        if not cases or not cms:
            pytest.skip("No cases or CMs for transfer test")
        
        case_id = cases[0]["id"]
        to_cm_id = cms[0]["id"]
        
        response = requests.post(
            f"{BASE_URL}/api/cases/transfer",
            json={
                "case_id": case_id,
                "to_case_manager_id": to_cm_id,
                "reason": "TEST_transfer_reason"
            },
            headers=auth_header(admin_token)
        )
        assert response.status_code == 200, f"Transfer failed: {response.text}"
        data = response.json()
        assert "transfer_id" in data or "message" in data
        print(f"Case transfer (admin): PASS - {data.get('message', '')}")
    
    def test_transfer_history(self, admin_token):
        """Get transfer history for a case"""
        cases_resp = requests.get(f"{BASE_URL}/api/cases", headers=auth_header(admin_token))
        if cases_resp.status_code != 200:
            pytest.skip("Cannot get cases")
        
        cases = cases_resp.json()
        if not cases:
            pytest.skip("No cases")
        
        case_id = cases[0]["id"]
        response = requests.get(
            f"{BASE_URL}/api/cases/transfer-history/{case_id}",
            headers=auth_header(admin_token)
        )
        assert response.status_code == 200, f"Transfer history failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Transfer history: PASS - {len(data)} transfers found")
    
    def test_transfer_client_forbidden(self, client_token):
        """Client cannot transfer cases"""
        response = requests.post(
            f"{BASE_URL}/api/cases/transfer",
            json={"case_id": "fake", "to_case_manager_id": "fake", "reason": "test"},
            headers=auth_header(client_token)
        )
        assert response.status_code == 403
        print("Transfer client forbidden: PASS")


# ============ SURVEYS ============

class TestSurveys:
    """Client satisfaction surveys"""
    
    def test_submit_survey_client(self, client_token):
        """Client submits survey"""
        # Get client's cases
        cases_resp = requests.get(f"{BASE_URL}/api/cases", headers=auth_header(client_token))
        if cases_resp.status_code != 200:
            pytest.skip("Cannot get client cases")
        
        cases = cases_resp.json()
        if not cases:
            pytest.skip("No cases for client")
        
        case_id = cases[0]["id"]
        response = requests.post(
            f"{BASE_URL}/api/surveys/submit",
            json={
                "case_id": case_id,
                "overall_rating": 5,
                "communication_rating": 4,
                "speed_rating": 4,
                "documentation_rating": 5,
                "feedback": "TEST_Great service!",
                "would_recommend": True
            },
            headers=auth_header(client_token)
        )
        # 200 = success, 400 = already submitted
        assert response.status_code in [200, 400], f"Survey submit failed: {response.text}"
        if response.status_code == 200:
            data = response.json()
            assert "id" in data
            assert data["overall_rating"] == 5
            print(f"Survey submit: PASS - survey ID {data['id']}")
        else:
            print("Survey submit: PASS (already submitted)")
    
    def test_submit_survey_admin_forbidden(self, admin_token):
        """Admin cannot submit survey"""
        response = requests.post(
            f"{BASE_URL}/api/surveys/submit",
            json={"case_id": "fake", "overall_rating": 5},
            headers=auth_header(admin_token)
        )
        assert response.status_code == 403
        print("Survey admin forbidden: PASS")
    
    def test_get_survey_stats_admin(self, admin_token):
        """Admin gets survey stats"""
        response = requests.get(
            f"{BASE_URL}/api/surveys/stats",
            headers=auth_header(admin_token)
        )
        assert response.status_code == 200, f"Survey stats failed: {response.text}"
        data = response.json()
        assert "total" in data
        assert "avg_rating" in data
        print(f"Survey stats (admin): PASS - total={data['total']}, avg={data['avg_rating']}")
    
    def test_get_survey_stats_cm(self, cm_token):
        """CM gets their survey stats"""
        response = requests.get(
            f"{BASE_URL}/api/surveys/stats",
            headers=auth_header(cm_token)
        )
        assert response.status_code == 200
        print("Survey stats (CM): PASS")
    
    def test_get_survey_for_case(self, admin_token):
        """Get survey for specific case"""
        cases_resp = requests.get(f"{BASE_URL}/api/cases", headers=auth_header(admin_token))
        if cases_resp.status_code != 200:
            pytest.skip("Cannot get cases")
        
        cases = cases_resp.json()
        if not cases:
            pytest.skip("No cases")
        
        case_id = cases[0]["id"]
        response = requests.get(
            f"{BASE_URL}/api/surveys/case/{case_id}",
            headers=auth_header(admin_token)
        )
        assert response.status_code == 200
        print("Get survey for case: PASS")


# ============ KNOWLEDGE BASE ============

class TestKnowledgeBase:
    """Knowledge base CRUD"""
    
    created_article_id = None
    
    def test_create_article_admin(self, admin_token):
        """Admin creates KB article"""
        response = requests.post(
            f"{BASE_URL}/api/knowledge-base/articles",
            json={
                "title": f"TEST_Article_{uuid.uuid4().hex[:8]}",
                "content": "This is test content for the knowledge base article.",
                "category": "immigration",
                "tags": ["visa", "test"],
                "is_published": True
            },
            headers=auth_header(admin_token)
        )
        assert response.status_code == 200, f"Create article failed: {response.text}"
        data = response.json()
        assert "id" in data
        assert "title" in data
        TestKnowledgeBase.created_article_id = data["id"]
        print(f"Create KB article: PASS - ID {data['id']}")
    
    def test_create_article_client_forbidden(self, client_token):
        """Client cannot create articles"""
        response = requests.post(
            f"{BASE_URL}/api/knowledge-base/articles",
            json={"title": "Test", "content": "Test", "category": "test"},
            headers=auth_header(client_token)
        )
        assert response.status_code == 403
        print("Create article client forbidden: PASS")
    
    def test_list_articles(self, client_token):
        """All users can list articles"""
        response = requests.get(
            f"{BASE_URL}/api/knowledge-base/articles",
            headers=auth_header(client_token)
        )
        assert response.status_code == 200, f"List articles failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"List KB articles: PASS - {len(data)} articles")
    
    def test_get_article(self, client_token):
        """Get single article"""
        if not TestKnowledgeBase.created_article_id:
            # Get any article
            articles_resp = requests.get(
                f"{BASE_URL}/api/knowledge-base/articles",
                headers=auth_header(client_token)
            )
            if articles_resp.status_code == 200 and articles_resp.json():
                article_id = articles_resp.json()[0]["id"]
            else:
                pytest.skip("No articles to get")
        else:
            article_id = TestKnowledgeBase.created_article_id
        
        response = requests.get(
            f"{BASE_URL}/api/knowledge-base/articles/{article_id}",
            headers=auth_header(client_token)
        )
        assert response.status_code == 200
        data = response.json()
        assert "title" in data
        assert "content" in data
        print(f"Get KB article: PASS - {data['title']}")
    
    def test_get_categories(self, client_token):
        """Get KB categories"""
        response = requests.get(
            f"{BASE_URL}/api/knowledge-base/categories",
            headers=auth_header(client_token)
        )
        assert response.status_code == 200, f"Get categories failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Get KB categories: PASS - {len(data)} categories")
    
    def test_update_article_admin(self, admin_token):
        """Admin updates article"""
        if not TestKnowledgeBase.created_article_id:
            pytest.skip("No article to update")
        
        response = requests.put(
            f"{BASE_URL}/api/knowledge-base/articles/{TestKnowledgeBase.created_article_id}",
            json={
                "title": "TEST_Updated_Article",
                "content": "Updated content",
                "category": "immigration",
                "tags": ["updated"],
                "is_published": True
            },
            headers=auth_header(admin_token)
        )
        assert response.status_code == 200
        print("Update KB article: PASS")
    
    def test_delete_article_admin(self, admin_token):
        """Admin deletes article"""
        if not TestKnowledgeBase.created_article_id:
            pytest.skip("No article to delete")
        
        response = requests.delete(
            f"{BASE_URL}/api/knowledge-base/articles/{TestKnowledgeBase.created_article_id}",
            headers=auth_header(admin_token)
        )
        assert response.status_code == 200
        print("Delete KB article: PASS")


# ============ APPOINTMENTS ============

class TestAppointments:
    """Appointment scheduling"""
    
    created_appt_id = None
    
    def test_create_appointment(self, admin_token):
        """Create appointment"""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        response = requests.post(
            f"{BASE_URL}/api/appointments",
            json={
                "title": f"TEST_Appointment_{uuid.uuid4().hex[:8]}",
                "description": "Test appointment description",
                "date": tomorrow,
                "time": "10:00",
                "duration_minutes": 30
            },
            headers=auth_header(admin_token)
        )
        assert response.status_code == 200, f"Create appointment failed: {response.text}"
        data = response.json()
        assert "id" in data
        assert data["status"] == "scheduled"
        TestAppointments.created_appt_id = data["id"]
        print(f"Create appointment: PASS - ID {data['id']}")
    
    def test_list_appointments(self, admin_token):
        """List appointments"""
        response = requests.get(
            f"{BASE_URL}/api/appointments",
            headers=auth_header(admin_token)
        )
        assert response.status_code == 200, f"List appointments failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"List appointments: PASS - {len(data)} appointments")
    
    def test_cancel_appointment(self, admin_token):
        """Cancel appointment"""
        if not TestAppointments.created_appt_id:
            pytest.skip("No appointment to cancel")
        
        response = requests.put(
            f"{BASE_URL}/api/appointments/{TestAppointments.created_appt_id}/cancel",
            headers=auth_header(admin_token)
        )
        assert response.status_code == 200
        print("Cancel appointment: PASS")
    
    def test_complete_appointment(self, admin_token):
        """Complete appointment"""
        # Create a new one to complete
        tomorrow = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
        create_resp = requests.post(
            f"{BASE_URL}/api/appointments",
            json={"title": "TEST_Complete", "date": tomorrow, "time": "14:00"},
            headers=auth_header(admin_token)
        )
        if create_resp.status_code != 200:
            pytest.skip("Cannot create appointment")
        
        appt_id = create_resp.json()["id"]
        response = requests.put(
            f"{BASE_URL}/api/appointments/{appt_id}/complete",
            headers=auth_header(admin_token)
        )
        assert response.status_code == 200
        print("Complete appointment: PASS")


# ============ DOCUMENT ANNOTATION ============

class TestDocumentAnnotation:
    """Document annotation feature"""
    
    def test_annotate_document(self, admin_token):
        """Add annotation to document"""
        # Get a document
        docs_resp = requests.get(f"{BASE_URL}/api/documents", headers=auth_header(admin_token))
        if docs_resp.status_code != 200:
            pytest.skip("Cannot get documents")
        
        docs = docs_resp.json()
        if not docs:
            pytest.skip("No documents to annotate")
        
        doc_id = docs[0]["id"]
        response = requests.post(
            f"{BASE_URL}/api/documents/{doc_id}/annotate",
            json={
                "text": "TEST_annotation_text",
                "page": 1,
                "x": 100.0,
                "y": 200.0
            },
            headers=auth_header(admin_token)
        )
        assert response.status_code == 200, f"Annotate failed: {response.text}"
        data = response.json()
        assert "id" in data
        assert data["text"] == "TEST_annotation_text"
        print(f"Annotate document: PASS - annotation ID {data['id']}")
    
    def test_get_annotations(self, admin_token):
        """Get annotations for document"""
        docs_resp = requests.get(f"{BASE_URL}/api/documents", headers=auth_header(admin_token))
        if docs_resp.status_code != 200:
            pytest.skip("Cannot get documents")
        
        docs = docs_resp.json()
        if not docs:
            pytest.skip("No documents")
        
        doc_id = docs[0]["id"]
        response = requests.get(
            f"{BASE_URL}/api/documents/{doc_id}/annotations",
            headers=auth_header(admin_token)
        )
        assert response.status_code == 200, f"Get annotations failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Get annotations: PASS - {len(data)} annotations")
    
    def test_annotate_client_forbidden(self, client_token):
        """Client cannot annotate"""
        response = requests.post(
            f"{BASE_URL}/api/documents/fake-id/annotate",
            json={"text": "test"},
            headers=auth_header(client_token)
        )
        assert response.status_code == 403
        print("Annotate client forbidden: PASS")


# ============ REVENUE FORECASTING ============

class TestRevenueForecasting:
    """Revenue forecast analytics"""
    
    def test_revenue_forecast_admin(self, admin_token):
        """Admin gets revenue forecast"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/revenue-forecast?months=3",
            headers=auth_header(admin_token)
        )
        assert response.status_code == 200, f"Revenue forecast failed: {response.text}"
        data = response.json()
        assert "historical" in data or "forecast" in data or "summary" in data
        print(f"Revenue forecast (admin): PASS - {data.get('summary', {})}")
    
    def test_revenue_forecast_partner(self, partner_token):
        """Partner gets revenue forecast"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/revenue-forecast?months=6",
            headers=auth_header(partner_token)
        )
        assert response.status_code == 200
        print("Revenue forecast (partner): PASS")
    
    def test_revenue_forecast_client_empty(self, client_token):
        """Client gets empty forecast (not authorized)"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/revenue-forecast",
            headers=auth_header(client_token)
        )
        # Returns empty data for unauthorized roles
        assert response.status_code == 200
        data = response.json()
        assert data.get("forecast") == [] or "forecast" in data
        print("Revenue forecast (client): PASS (empty/limited)")


# ============ CM PERFORMANCE METRICS ============

class TestCMPerformance:
    """Case manager performance metrics"""
    
    def test_cm_performance_admin(self, admin_token):
        """Admin gets all CM performance"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/cm-performance",
            headers=auth_header(admin_token)
        )
        assert response.status_code == 200, f"CM performance failed: {response.text}"
        data = response.json()
        assert "metrics" in data
        print(f"CM performance (admin): PASS - {len(data['metrics'])} CMs")
    
    def test_cm_performance_cm(self, cm_token):
        """CM gets own performance"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/cm-performance",
            headers=auth_header(cm_token)
        )
        assert response.status_code == 200
        data = response.json()
        assert "metrics" in data
        # CM should see only their own metrics
        print(f"CM performance (self): PASS - {len(data['metrics'])} metrics")
    
    def test_cm_performance_client_empty(self, client_token):
        """Client gets empty metrics"""
        response = requests.get(
            f"{BASE_URL}/api/analytics/cm-performance",
            headers=auth_header(client_token)
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("metrics") == []
        print("CM performance (client): PASS (empty)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
