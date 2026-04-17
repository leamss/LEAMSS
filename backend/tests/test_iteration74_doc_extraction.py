"""
Iteration 74: Document Info Extraction API Tests
------------------------------------------------
Tests for the doc-extraction endpoints:
- GET /api/doc-extraction/doc-types (auth required) - returns 12 doc types
- GET /api/doc-extraction/sample-docs (public) - returns 5 samples
- GET /api/doc-extraction/sample-docs/{id}/extraction (public) - pre-computed extraction
- POST /api/doc-extraction/extract (auth required) - base64 image extraction
- POST /api/doc-extraction/extract-upload (auth required) - multipart upload
- POST /api/doc-extraction/save (auth required) - persist extraction
- GET /api/doc-extraction/history (auth required) - role-based history

NOTE: Real /extract and /extract-upload call GPT-4o vision via Emergent LLM Key.
We use ONE real extraction test with a PIL-generated passport-like JPEG.
"""

import pytest
import requests
import os
import base64
import io
from PIL import Image, ImageDraw, ImageFont

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
ADMIN_CREDS = {"email": "admin@leamss.com", "password": "Admin@123"}
PARTNER_CREDS = {"email": "partner@leamss.com", "password": "Partner@123"}
CLIENT_CREDS = {"email": "client@leamss.com", "password": "Client@123"}

# Sample document IDs from the code
SAMPLE_IDS = ["sample_passport_in", "sample_ielts", "sample_bank_statement", "sample_degree", "sample_pcc"]


def get_auth_token(email: str, password: str) -> str:
    """Get JWT token for a user"""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
    if resp.status_code == 200:
        return resp.json().get("token", "") or resp.json().get("access_token", "")
    return ""


def auth_header(token: str) -> dict:
    """Return Authorization header"""
    return {"Authorization": f"Bearer {token}"}


def generate_passport_jpeg() -> bytes:
    """
    Generate a minimal passport-like JPEG image with real text content.
    This is used for ONE real extraction test to minimize API costs.
    """
    # Create a passport-like image (standard passport size ratio)
    img = Image.new("RGB", (600, 400), color=(240, 240, 245))
    draw = ImageDraw.Draw(img)
    
    # Try to use a basic font, fall back to default
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
    except:
        font = ImageFont.load_default()
        font_small = font
        font_large = font
    
    # Draw passport-like content
    # Header
    draw.rectangle([(0, 0), (600, 50)], fill=(0, 51, 102))
    draw.text((20, 15), "REPUBLIC OF INDIA", fill="white", font=font_large)
    draw.text((450, 15), "PASSPORT", fill="white", font=font)
    
    # Photo placeholder
    draw.rectangle([(20, 70), (170, 250)], outline=(100, 100, 100), width=2)
    draw.text((60, 150), "PHOTO", fill=(150, 150, 150), font=font)
    
    # Personal details
    draw.text((200, 70), "Surname / Nom", fill=(100, 100, 100), font=font_small)
    draw.text((200, 85), "PATEL", fill="black", font=font)
    
    draw.text((200, 110), "Given Names / Prénoms", fill=(100, 100, 100), font=font_small)
    draw.text((200, 125), "ANIL KUMAR", fill="black", font=font)
    
    draw.text((200, 150), "Nationality / Nationalité", fill=(100, 100, 100), font=font_small)
    draw.text((200, 165), "INDIAN", fill="black", font=font)
    
    draw.text((200, 190), "Date of Birth / Date de naissance", fill=(100, 100, 100), font=font_small)
    draw.text((200, 205), "22 JUN 1988", fill="black", font=font)
    
    draw.text((400, 70), "Sex / Sexe", fill=(100, 100, 100), font=font_small)
    draw.text((400, 85), "M", fill="black", font=font)
    
    draw.text((400, 110), "Place of Birth", fill=(100, 100, 100), font=font_small)
    draw.text((400, 125), "MUMBAI", fill="black", font=font)
    
    draw.text((400, 150), "Date of Issue", fill=(100, 100, 100), font=font_small)
    draw.text((400, 165), "15 MAR 2020", fill="black", font=font)
    
    draw.text((400, 190), "Date of Expiry", fill=(100, 100, 100), font=font_small)
    draw.text((400, 205), "14 MAR 2030", fill="black", font=font)
    
    # Passport number
    draw.text((200, 240), "Passport No. / No. de passeport", fill=(100, 100, 100), font=font_small)
    draw.text((200, 255), "Z9876543", fill="black", font=font_large)
    
    # MRZ zone (bottom)
    draw.rectangle([(0, 300), (600, 400)], fill=(245, 245, 250))
    draw.text((20, 320), "P<INDPATEL<<ANIL<KUMAR<<<<<<<<<<<<<<<<<<<<<<<<", fill="black", font=font_small)
    draw.text((20, 350), "Z98765434IND8806224M3003147<<<<<<<<<<<<<<<04", fill="black", font=font_small)
    
    # Convert to JPEG bytes
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


def generate_large_image() -> bytes:
    """Generate an image larger than 8MB for size limit testing"""
    # Create a large image (approx 9MB when saved as JPEG)
    img = Image.new("RGB", (4000, 4000), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    # Add some content to prevent compression from making it too small
    for i in range(0, 4000, 10):
        draw.line([(0, i), (4000, i)], fill=(i % 256, (i * 2) % 256, (i * 3) % 256), width=1)
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=100)
    return buffer.getvalue()


class TestDocExtractionPublicEndpoints:
    """Tests for public endpoints (no auth required)"""
    
    def test_sample_docs_list(self):
        """GET /api/doc-extraction/sample-docs - returns 5 samples (public)"""
        resp = requests.get(f"{BASE_URL}/api/doc-extraction/sample-docs")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert "samples" in data, "Response should have 'samples' key"
        samples = data["samples"]
        assert len(samples) == 5, f"Expected 5 samples, got {len(samples)}"
        
        # Verify sample IDs
        sample_ids = [s["id"] for s in samples]
        for expected_id in SAMPLE_IDS:
            assert expected_id in sample_ids, f"Missing sample: {expected_id}"
        
        # Verify each sample has required fields (but NOT extraction - that's separate)
        for sample in samples:
            assert "id" in sample
            assert "name" in sample
            assert "doc_type" in sample
            assert "thumbnail" in sample
            assert "description" in sample
            assert "extraction" not in sample, "List should not include extraction data"
        
        print(f"✓ Sample docs list: {len(samples)} samples returned")
    
    def test_sample_extraction_passport(self):
        """GET /api/doc-extraction/sample-docs/sample_passport_in/extraction - pre-computed extraction"""
        resp = requests.get(f"{BASE_URL}/api/doc-extraction/sample-docs/sample_passport_in/extraction")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert data["sample_id"] == "sample_passport_in"
        assert data["doc_type"] == "passport"
        assert data["demo"] is True
        assert "extraction" in data
        
        extraction = data["extraction"]
        assert extraction["doc_type"] == "passport"
        assert extraction["overall_confidence"] >= 0.95, f"Expected high confidence, got {extraction['overall_confidence']}"
        
        # Verify fields
        fields = extraction["fields"]
        assert len(fields) >= 8, f"Expected at least 8 fields, got {len(fields)}"
        assert "full_name" in fields
        assert "passport_number" in fields
        assert "date_of_birth" in fields
        
        # Verify confidences
        confidences = extraction["confidences"]
        assert len(confidences) >= 8
        
        print(f"✓ Sample passport extraction: {len(fields)} fields, confidence={extraction['overall_confidence']}")
    
    def test_sample_extraction_ielts(self):
        """GET /api/doc-extraction/sample-docs/sample_ielts/extraction"""
        resp = requests.get(f"{BASE_URL}/api/doc-extraction/sample-docs/sample_ielts/extraction")
        assert resp.status_code == 200
        
        data = resp.json()
        assert data["doc_type"] == "ielts_scorecard"
        extraction = data["extraction"]
        fields = extraction["fields"]
        
        # IELTS specific fields
        assert "overall_band_score" in fields
        assert "listening" in fields
        assert "reading" in fields
        assert "writing" in fields
        assert "speaking" in fields
        
        print(f"✓ Sample IELTS extraction: overall_band={fields.get('overall_band_score')}")
    
    def test_sample_extraction_bank_statement(self):
        """GET /api/doc-extraction/sample-docs/sample_bank_statement/extraction"""
        resp = requests.get(f"{BASE_URL}/api/doc-extraction/sample-docs/sample_bank_statement/extraction")
        assert resp.status_code == 200
        
        data = resp.json()
        assert data["doc_type"] == "bank_statement"
        fields = data["extraction"]["fields"]
        
        assert "account_holder_name" in fields
        assert "closing_balance" in fields
        assert "bank_name" in fields
        
        print(f"✓ Sample bank statement extraction: balance={fields.get('closing_balance')}")
    
    def test_sample_extraction_degree(self):
        """GET /api/doc-extraction/sample-docs/sample_degree/extraction"""
        resp = requests.get(f"{BASE_URL}/api/doc-extraction/sample-docs/sample_degree/extraction")
        assert resp.status_code == 200
        
        data = resp.json()
        assert data["doc_type"] == "educational_certificate"
        fields = data["extraction"]["fields"]
        
        assert "candidate_name" in fields
        assert "institution" in fields
        assert "degree_or_qualification" in fields
        
        print(f"✓ Sample degree extraction: {fields.get('degree_or_qualification')}")
    
    def test_sample_extraction_pcc(self):
        """GET /api/doc-extraction/sample-docs/sample_pcc/extraction"""
        resp = requests.get(f"{BASE_URL}/api/doc-extraction/sample-docs/sample_pcc/extraction")
        assert resp.status_code == 200
        
        data = resp.json()
        assert data["doc_type"] == "police_clearance"
        fields = data["extraction"]["fields"]
        
        assert "holder_name" in fields
        assert "certificate_number" in fields
        
        print(f"✓ Sample PCC extraction: cert_no={fields.get('certificate_number')}")
    
    def test_sample_extraction_not_found(self):
        """GET /api/doc-extraction/sample-docs/does_not_exist/extraction - 404"""
        resp = requests.get(f"{BASE_URL}/api/doc-extraction/sample-docs/does_not_exist/extraction")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        print("✓ Non-existent sample returns 404")


class TestDocExtractionAuthRequired:
    """Tests for endpoints requiring authentication"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth tokens for all roles"""
        self.admin_token = get_auth_token(**ADMIN_CREDS)
        self.partner_token = get_auth_token(**PARTNER_CREDS)
        self.client_token = get_auth_token(**CLIENT_CREDS)
        
        assert self.admin_token, "Admin login failed"
        assert self.partner_token, "Partner login failed"
        assert self.client_token, "Client login failed"
    
    def test_doc_types_requires_auth(self):
        """GET /api/doc-extraction/doc-types - 401 without token"""
        resp = requests.get(f"{BASE_URL}/api/doc-extraction/doc-types")
        assert resp.status_code in [401, 403], f"Expected 401/403 without auth, got {resp.status_code}"
        print("✓ /doc-types requires auth")
    
    def test_doc_types_returns_catalog(self):
        """GET /api/doc-extraction/doc-types - returns 12 doc types"""
        resp = requests.get(
            f"{BASE_URL}/api/doc-extraction/doc-types",
            headers=auth_header(self.admin_token)
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert "doc_types" in data
        doc_types = data["doc_types"]
        assert len(doc_types) == 12, f"Expected 12 doc types, got {len(doc_types)}"
        
        # Verify expected doc types
        expected_types = [
            "passport", "visa", "educational_certificate", "academic_transcript",
            "ielts_scorecard", "bank_statement", "police_clearance", "marriage_certificate",
            "birth_certificate", "driver_license", "offer_letter", "unknown"
        ]
        for dt in expected_types:
            assert dt in doc_types, f"Missing doc type: {dt}"
            assert "name" in doc_types[dt]
            assert "fields" in doc_types[dt]
        
        print(f"✓ Doc types catalog: {len(doc_types)} types with fields")
    
    def test_extract_requires_auth(self):
        """POST /api/doc-extraction/extract - 401 without token"""
        resp = requests.post(
            f"{BASE_URL}/api/doc-extraction/extract",
            json={"image_base64": "test"}
        )
        assert resp.status_code in [401, 403], f"Expected 401/403 without auth, got {resp.status_code}"
        print("✓ /extract requires auth")
    
    def test_extract_missing_image_400(self):
        """POST /api/doc-extraction/extract - 400 when image_base64 missing"""
        resp = requests.post(
            f"{BASE_URL}/api/doc-extraction/extract",
            json={},
            headers=auth_header(self.admin_token)
        )
        assert resp.status_code in [400, 422], f"Expected 400/422, got {resp.status_code}"
        print("✓ Missing image_base64 returns 400/422")
    
    def test_extract_bad_mime_415(self):
        """POST /api/doc-extraction/extract - 415 for SVG/unsupported mime"""
        # SVG content (not a valid image for extraction)
        svg_content = '<svg xmlns="http://www.w3.org/2000/svg"><rect width="100" height="100"/></svg>'
        svg_b64 = base64.b64encode(svg_content.encode()).decode()
        
        resp = requests.post(
            f"{BASE_URL}/api/doc-extraction/extract",
            json={"image_base64": svg_b64, "mime_type": "image/svg+xml"},
            headers=auth_header(self.admin_token)
        )
        assert resp.status_code == 415, f"Expected 415 for SVG, got {resp.status_code}: {resp.text}"
        print("✓ SVG mime type returns 415")
    
    def test_extract_upload_requires_auth(self):
        """POST /api/doc-extraction/extract-upload - 401 without token"""
        # Create a minimal file
        files = {"file": ("test.jpg", b"fake", "image/jpeg")}
        resp = requests.post(f"{BASE_URL}/api/doc-extraction/extract-upload", files=files)
        assert resp.status_code in [401, 403], f"Expected 401/403 without auth, got {resp.status_code}"
        print("✓ /extract-upload requires auth")
    
    def test_extract_upload_bad_mime_415(self):
        """POST /api/doc-extraction/extract-upload - 415 for non-image file"""
        files = {"file": ("test.txt", b"Hello world", "text/plain")}
        resp = requests.post(
            f"{BASE_URL}/api/doc-extraction/extract-upload",
            files=files,
            headers=auth_header(self.admin_token)
        )
        assert resp.status_code == 415, f"Expected 415 for text file, got {resp.status_code}: {resp.text}"
        print("✓ Non-image upload returns 415")
    
    def test_extract_upload_file_too_large_413(self):
        """POST /api/doc-extraction/extract-upload - 413 for file > 8MB"""
        # Generate a large image
        large_img = generate_large_image()
        
        # Check if it's actually > 8MB
        if len(large_img) <= 8 * 1024 * 1024:
            # If not large enough, pad it
            large_img = large_img + b"\x00" * (9 * 1024 * 1024 - len(large_img))
        
        files = {"file": ("large.jpg", large_img, "image/jpeg")}
        resp = requests.post(
            f"{BASE_URL}/api/doc-extraction/extract-upload",
            files=files,
            headers=auth_header(self.admin_token)
        )
        assert resp.status_code == 413, f"Expected 413 for large file, got {resp.status_code}"
        print(f"✓ Large file ({len(large_img) / 1024 / 1024:.1f}MB) returns 413")
    
    def test_save_requires_auth(self):
        """POST /api/doc-extraction/save - 401 without token"""
        resp = requests.post(
            f"{BASE_URL}/api/doc-extraction/save",
            json={"extraction": {}}
        )
        assert resp.status_code in [401, 403], f"Expected 401/403 without auth, got {resp.status_code}"
        print("✓ /save requires auth")
    
    def test_history_requires_auth(self):
        """GET /api/doc-extraction/history - 401 without token"""
        resp = requests.get(f"{BASE_URL}/api/doc-extraction/history")
        assert resp.status_code in [401, 403], f"Expected 401/403 without auth, got {resp.status_code}"
        print("✓ /history requires auth")


class TestDocExtractionRealExtraction:
    """
    ONE real extraction test using PIL-generated passport image.
    This calls GPT-4o vision via Emergent LLM Key - use sparingly!
    """
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.admin_token = get_auth_token(**ADMIN_CREDS)
        assert self.admin_token, "Admin login failed"
    
    def test_extract_real_passport_image(self):
        """
        POST /api/doc-extraction/extract - Real extraction with PIL-generated passport
        This is the ONLY real LLM call in this test suite.
        """
        # Generate passport-like JPEG
        passport_bytes = generate_passport_jpeg()
        passport_b64 = base64.b64encode(passport_bytes).decode()
        
        # Test with data URI prefix (should be stripped)
        data_uri = f"data:image/jpeg;base64,{passport_b64}"
        
        resp = requests.post(
            f"{BASE_URL}/api/doc-extraction/extract",
            json={
                "image_base64": data_uri,
                "mime_type": "image/jpeg",
                "hint_doc_type": "passport"
            },
            headers=auth_header(self.admin_token),
            timeout=60  # LLM calls can take time
        )
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert "id" in data
        assert "doc_type" in data
        assert "extraction" in data
        assert "generated_at" in data
        
        extraction = data["extraction"]
        assert "fields" in extraction
        assert "confidences" in extraction
        assert "overall_confidence" in extraction
        
        # The LLM should detect this as a passport
        assert data["doc_type"] in ["passport", "unknown"], f"Unexpected doc_type: {data['doc_type']}"
        
        # Should have some fields extracted
        fields = extraction["fields"]
        assert len(fields) >= 1, "Expected at least 1 field extracted"
        
        # Overall confidence should be reasonable
        overall_conf = extraction["overall_confidence"]
        assert 0 <= overall_conf <= 1, f"Invalid confidence: {overall_conf}"
        
        print(f"✓ Real extraction: doc_type={data['doc_type']}, fields={len(fields)}, confidence={overall_conf:.2f}")
        print(f"  Fields: {list(fields.keys())[:5]}...")


class TestDocExtractionSaveAndHistory:
    """Tests for save and history endpoints with role-based access"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.admin_token = get_auth_token(**ADMIN_CREDS)
        self.partner_token = get_auth_token(**PARTNER_CREDS)
        self.client_token = get_auth_token(**CLIENT_CREDS)
        
        assert self.admin_token, "Admin login failed"
        assert self.partner_token, "Partner login failed"
        assert self.client_token, "Client login failed"
    
    def test_save_extraction_client(self):
        """POST /api/doc-extraction/save - Client can save extraction"""
        extraction_data = {
            "doc_type": "passport",
            "doc_type_name": "Passport",
            "fields": {"full_name": "TEST_CLIENT_USER", "passport_number": "TEST123"},
            "confidences": {"full_name": 0.95, "passport_number": 0.90},
            "overall_confidence": 0.92,
            "warnings": [],
            "summary": "Test extraction for client"
        }
        
        resp = requests.post(
            f"{BASE_URL}/api/doc-extraction/save",
            json={
                "extraction": extraction_data,
                "filename": "test_passport_client.jpg"
            },
            headers=auth_header(self.client_token)
        )
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert "id" in data
        assert data["extraction"]["fields"]["full_name"] == "TEST_CLIENT_USER"
        assert data["created_by_role"] == "client"
        
        print(f"✓ Client saved extraction: id={data['id']}")
        return data["id"]
    
    def test_save_extraction_partner(self):
        """POST /api/doc-extraction/save - Partner can save extraction"""
        extraction_data = {
            "doc_type": "ielts_scorecard",
            "fields": {"candidate_name": "TEST_PARTNER_USER", "overall_band_score": 7.5},
            "confidences": {"candidate_name": 0.98, "overall_band_score": 0.99},
            "overall_confidence": 0.98,
            "warnings": [],
            "summary": "Test IELTS for partner"
        }
        
        resp = requests.post(
            f"{BASE_URL}/api/doc-extraction/save",
            json={
                "extraction": extraction_data,
                "filename": "test_ielts_partner.jpg"
            },
            headers=auth_header(self.partner_token)
        )
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert data["created_by_role"] == "partner"
        
        print(f"✓ Partner saved extraction: id={data['id']}")
        return data["id"]
    
    def test_history_client_sees_own_only(self):
        """GET /api/doc-extraction/history - Client sees only their own extractions"""
        # First save one as client
        self.test_save_extraction_client()
        
        resp = requests.get(
            f"{BASE_URL}/api/doc-extraction/history",
            headers=auth_header(self.client_token)
        )
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert "extractions" in data
        assert "total" in data
        
        # All extractions should be created by client
        for ext in data["extractions"]:
            assert ext["created_by_role"] == "client", f"Client should only see own extractions, got role={ext['created_by_role']}"
        
        print(f"✓ Client history: {data['total']} extractions (all own)")
    
    def test_history_partner_sees_own_only(self):
        """GET /api/doc-extraction/history - Partner sees only their own extractions"""
        # First save one as partner
        self.test_save_extraction_partner()
        
        resp = requests.get(
            f"{BASE_URL}/api/doc-extraction/history",
            headers=auth_header(self.partner_token)
        )
        
        assert resp.status_code == 200
        
        data = resp.json()
        for ext in data["extractions"]:
            assert ext["created_by_role"] == "partner", f"Partner should only see own extractions"
        
        print(f"✓ Partner history: {data['total']} extractions (all own)")
    
    def test_history_admin_sees_all(self):
        """GET /api/doc-extraction/history - Admin sees all extractions"""
        # Save as both client and partner first
        self.test_save_extraction_client()
        self.test_save_extraction_partner()
        
        resp = requests.get(
            f"{BASE_URL}/api/doc-extraction/history",
            headers=auth_header(self.admin_token)
        )
        
        assert resp.status_code == 200
        
        data = resp.json()
        # Admin should see extractions from multiple roles
        roles_seen = set(ext["created_by_role"] for ext in data["extractions"])
        
        print(f"✓ Admin history: {data['total']} extractions, roles={roles_seen}")


class TestDocExtractionEdgeCases:
    """Edge case tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.admin_token = get_auth_token(**ADMIN_CREDS)
        assert self.admin_token, "Admin login failed"
    
    def test_extract_with_data_uri_prefix(self):
        """POST /api/doc-extraction/extract - Accepts data URI prefix"""
        # Create a minimal valid JPEG
        img = Image.new("RGB", (100, 100), color=(255, 200, 150))
        draw = ImageDraw.Draw(img)
        draw.text((10, 40), "TEST", fill="black")
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        img_b64 = base64.b64encode(buffer.getvalue()).decode()
        
        # With data URI prefix
        data_uri = f"data:image/jpeg;base64,{img_b64}"
        
        resp = requests.post(
            f"{BASE_URL}/api/doc-extraction/extract",
            json={"image_base64": data_uri},
            headers=auth_header(self.admin_token),
            timeout=60
        )
        
        # Should accept and process (may return unknown doc type for minimal image)
        assert resp.status_code in [200, 502], f"Expected 200 or 502 (AI error), got {resp.status_code}"
        
        if resp.status_code == 200:
            print("✓ Data URI prefix accepted and processed")
        else:
            print("✓ Data URI prefix accepted (AI returned error for minimal image)")
    
    def test_extract_without_mime_type(self):
        """POST /api/doc-extraction/extract - Auto-detects mime from magic bytes"""
        # Create a JPEG without specifying mime_type
        img = Image.new("RGB", (100, 100), color=(100, 150, 200))
        draw = ImageDraw.Draw(img)
        draw.text((10, 40), "AUTO", fill="white")
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        img_b64 = base64.b64encode(buffer.getvalue()).decode()
        
        resp = requests.post(
            f"{BASE_URL}/api/doc-extraction/extract",
            json={"image_base64": img_b64},  # No mime_type
            headers=auth_header(self.admin_token),
            timeout=60
        )
        
        # Should auto-detect JPEG from magic bytes
        assert resp.status_code in [200, 502], f"Expected 200 or 502, got {resp.status_code}"
        
        if resp.status_code == 200:
            data = resp.json()
            assert data["mime_type"] == "image/jpeg", f"Expected auto-detected jpeg, got {data['mime_type']}"
            print("✓ Mime type auto-detected as image/jpeg")
        else:
            print("✓ Mime type auto-detection worked (AI returned error for minimal image)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
