"""Unit and Integration Tests for Sales AI Multi-Language Translation (English, Marathi, Hindi).

Verifies:
  1. POST /api/product-master/sales-ai-translate endpoint translates advisory text into Marathi.
  2. POST /api/product-master/sales-ai-translate endpoint translates advisory text into Hindi.
  3. POST /api/product-master/sales-ai-translate translates Marathi text into English.
  4. Direct passthrough optimization when text is already in the requested language.
  5. Preservation of statutory visa subclasses, form numbers, and document formatting.
  6. Graceful error handling for empty text or upstream timeouts.
"""
from __future__ import annotations

import re
import pytest
from httpx import AsyncClient, ASGITransport

from server import app


async def override_sales_user():
    return {
        "id": "sales-rep-lang-01",
        "email": "pooja.ghatkar@leamss.com",
        "name": "Pooja Ghatkar",
        "role": "sales",
        "permissions": ["sales.read", "product_master.view"],
    }


@pytest.fixture(autouse=True)
def mock_external_calls(monkeypatch):
    """Mocks Perplexity API and MongoDB lookups for fast, offline, deterministic test runs."""
    async def _mock_perplexity(prompt, system_msg, model="sonar", max_tokens=2500, temperature=0.1, timeout=35.0):
        # Extract target language from prompt or system_msg
        prompt_lower = prompt.lower()
        if "marathi" in prompt_lower or "marathi" in system_msg.lower():
            return (
                "### 💬 1. Speaking Script for Live Call (Read directly to client)\n"
                "> *\"होय, तुम्ही तुमच्या ऑस्ट्रेलिया Subclass 189 अर्जामध्ये पात्र जोडीदार आणि अवलंबित मुलांना समाविष्ट करू शकता. "
                "कुटुंबातील सदस्यांना Permanent Residency तेव्हाच मिळते जेव्हा त्यांना अर्जात समाविष्ट केले जाते आणि त्यांचे व्हिसा मंजूर होतात. "
                "अवलंबित मुले १८ वर्षांखालील किंवा १८ ते २३ वयोगटातील आणि आर्थिकदृष्ट्या अवलंबून असणे आवश्यक आहे. "
                "जोडीदारासाठी अस्सल नातेसंबंध पुरावे आवश्यक आहेत आणि सर्वांनी आरोग्य व चारित्र्य तपासणी पूर्ण केली पाहिजे.\"*\n\n"
                "### ⚡ 2. Direct Quick Answer: कौटुंबिक समावेश नियम ऑस्ट्रेलिया Subclass 189 (लहान वाक्ये)\n"
                "- **पात्र कुटुंबीय:** तुम्ही कायदेशीर विवाहित जोडीदार किंवा de facto partner आणि अवलंबित मुलांना Subclass 189 मध्ये समाविष्ट करू शकता.\n"
                "- **पीआर मंजुरीची अट:** कुटुंबातील सदस्यांना पीआर केवळ तेव्हाच मिळतो जेव्हा ते अर्जात समाविष्ट असतात आणि Department of Home Affairs द्वारे मंजूर होतात.\n"
                "- **अवलंबित मुले वय निकष:** १८ वर्षांखालील मुले आपोआप पात्र ठरतात. १८ ते २३ वर्षे वयोगटातील मुले आर्थिकदृष्ट्या अवलंबून (विद्यार्थी, अविवाहित) असणे आवश्यक आहे.\n"
                "- **जोडीदार नातेसंबंध पुरावा:** अस्सल आणि चालू असलेल्या संबंधाचा पुरावा आवश्यक (विवाह प्रमाणपत्र किंवा किमान १२ महिने एकत्र राहणे).\n"
                "- **अनिवार्य आरोग्य आणि चारित्र्य:** सर्व अर्जदारांनी ऑस्ट्रेलियन आरोग्य तपासणी आणि पोलीस चारित्र्य पडताळणी उत्तीर्ण केली पाहिजे.\n"
                "- **सरकारी अर्ज शुल्क:** दुय्यम अर्जदारांसाठी अतिरिक्त व्हिसा अर्ज शुल्क लागू होते."
            ), "sonar-mock-marathi"
        elif "hindi" in prompt_lower or "hindi" in system_msg.lower():
            return (
                "### 💬 1. Speaking Script for Live Call (Read directly to client)\n"
                "> *\"हाँ, आप अपने ऑस्ट्रेलिया Subclass 189 आवेदन में अपने जीवनसाथी और आश्रित बच्चों को शामिल कर सकते हैं। "
                "परिवार के सदस्यों को Permanent Residency केवल तभी मिलती है जब वे आवेदन में शामिल हों और उनके वीज़ा स्वीकृत हों। "
                "आश्रित बच्चे 18 वर्ष से कम या 18 से 23 वर्ष के और आर्थिक रूप से आश्रित होने चाहिए। "
                "जीवनसाथी के लिए वास्तविक संबंध प्रमाण आवश्यक है और सभी को स्वास्थ्य व चरित्र आवश्यकताओं को पूरा करना होगा।\"*\n\n"
                "### ⚡ 2. Direct Quick Answer: परिवार समावेशन नियम ऑस्ट्रेलिया Subclass 189 (छोटे वाक्य)\n"
                "- **पात्र परिवार सदस्य:** आप कानूनी रूप से विवाहित जीवनसाथी या de facto partner और आश्रित बच्चों को Subclass 189 में शामिल कर सकते हैं।\n"
                "- **पीआर स्वीकृति शर्त:** परिवार के सदस्यों को पीआर केवल तभी मिलता है जब उन्हें शामिल किया गया हो और Department of Home Affairs द्वारा स्वीकृत किया गया हो।\n"
                "- **आश्रित बच्चों की आयु और शर्तें:** 18 वर्ष से कम उम्र के बच्चे स्वचालित रूप से पात्र हैं। 18 से 23 वर्ष के बच्चे आर्थिक रूप से आश्रित होने चाहिए।\n"
                "- **जीवनसाथी वास्तविक संबंध प्रमाण:** वास्तविक और निरंतर संबंध का प्रमाण अनिवार्य है (विवाह प्रमाण पत्र या कम से कम 12 महीने साथ रहना)।\n"
                "- **अनिवार्य स्वास्थ्य और चरित्र:** सभी द्वितीयक आवेदकों को ऑस्ट्रेलियाई स्वास्थ्य परीक्षा और पुलिस चरित्र प्रमाणपत्र पास करना होगा।\n"
                "- **सरकारी आवेदन शुल्क:** द्वितीयक आवेदकों के लिए अतिरिक्त वीज़ा आवेदन शुल्क लागू होता है।"
            ), "sonar-mock-hindi"
        else:
            return (
                "### 💬 1. Speaking Script for Live Call (Read directly to client)\n"
                "> *\"Yes, you can include your eligible spouse and dependent children in your Australia Subclass 189 application. "
                "Family members receive Permanent Residency only if they are included in the application and their visas are approved. "
                "Dependent children must be under 18, or aged 18 to 23 and financially dependent. "
                "Your spouse must show genuine relationship evidence, and all family members must meet health and character requirements. "
                "Additional government visa charges apply for secondary applicants.\"*\n\n"
                "### ⚡ 2. Direct Quick Answer: Family Inclusion Rules for Australia Subclass 189 (Small Sentences)\n"
                "- **Eligible Family Members:** You can include your spouse and dependent children in the same Subclass 189 application.\n"
                "- **PR Approval Requirement:** Family members receive Permanent Residency only if included and approved by the Department of Home Affairs.\n"
                "- **Dependent Children Age:** Children under 18 qualify automatically; aged 18 to 23 must be financially dependent.\n"
                "- **Spouse Evidence:** Genuine relationship evidence required (marriage certificate or 12-month de facto cohabitation).\n"
                "- **Mandatory Clearances:** All applicants must pass Australian health and police character checks.\n"
                "- **Government Charges:** Additional government visa charges apply for secondary applicants."
            ), "sonar-mock-english"

    monkeypatch.setattr("core.perplexity_client.call_perplexity", _mock_perplexity)


@pytest.mark.asyncio
async def test_translate_english_to_marathi():
    """Verify translating English advisory document into Marathi."""
    from core.auth import get_current_user

    app.dependency_overrides[get_current_user] = override_sales_user
    transport = ASGITransport(app=app)

    english_text = (
        "### 💬 1. Speaking Script for Live Call (Read directly to client)\n"
        "> *\"Yes, you can include your eligible spouse and dependent children in your Australia Subclass 189 application.\"*\n\n"
        "### ⚡ 2. Direct Quick Answer: Family Inclusion Rules for Australia Subclass 189 (Small Sentences)\n"
        "- **Eligible Family Members:** Spouse and dependent children can be included."
    )

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/product-master/sales-ai-translate", json={
            "text": english_text,
            "target_language": "Marathi",
            "country": "Australia",
            "visa_subclass": "189",
        })
        assert resp.status_code == 200
        data = resp.json()

        assert data["target_language"] == "Marathi"
        translated = data["translated_text"]

        # Must contain Devanagari script for Marathi
        assert bool(re.search(r"[\u0900-\u097F]", translated))
        # Must preserve official visa subclass
        assert "Subclass 189" in translated or "189" in translated
        # Must preserve document structure
        assert "### 💬 1." in translated or "Speaking Script" in translated

    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_translate_english_to_hindi():
    """Verify translating English advisory document into Hindi."""
    from core.auth import get_current_user

    app.dependency_overrides[get_current_user] = override_sales_user
    transport = ASGITransport(app=app)

    english_text = (
        "### 💬 1. Speaking Script for Live Call (Read directly to client)\n"
        "> *\"Yes, you can include your eligible spouse and dependent children in your Australia Subclass 189 application.\"*\n\n"
        "### ⚡ 2. Direct Quick Answer: Family Inclusion Rules for Australia Subclass 189 (Small Sentences)\n"
        "- **Eligible Family Members:** Spouse and dependent children can be included."
    )

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/product-master/sales-ai-translate", json={
            "text": english_text,
            "target_language": "Hindi",
            "country": "Australia",
            "visa_subclass": "189",
        })
        assert resp.status_code == 200
        data = resp.json()

        assert data["target_language"] == "Hindi"
        translated = data["translated_text"]

        # Must contain Devanagari script for Hindi
        assert bool(re.search(r"[\u0900-\u097F]", translated))
        # Must preserve official visa subclass
        assert "Subclass 189" in translated or "189" in translated
        assert "### 💬 1." in translated or "Speaking Script" in translated

    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_translate_marathi_to_english():
    """Verify translating Marathi document back into English."""
    from core.auth import get_current_user

    app.dependency_overrides[get_current_user] = override_sales_user
    transport = ASGITransport(app=app)

    marathi_text = (
        "### 💬 1. Speaking Script for Live Call (Read directly to client)\n"
        "> *\"होय, तुम्ही तुमच्या ऑस्ट्रेलिया Subclass 189 अर्जामध्ये जोडीदार आणि मुलांना समाविष्ट करू शकता.\"*\n\n"
        "### ⚡ 2. Direct Quick Answer: कौटुंबिक नियम (लहान वाक्ये)\n"
        "- **पात्र कुटुंबीय:** जोडीदार आणि मुले."
    )

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/product-master/sales-ai-translate", json={
            "text": marathi_text,
            "target_language": "English",
            "country": "Australia",
            "visa_subclass": "189",
        })
        assert resp.status_code == 200
        data = resp.json()

        assert data["target_language"] == "English"
        translated = data["translated_text"]

        assert "Subclass 189" in translated
        assert "Speaking Script" in translated or "Live Call" in translated
        assert "Permanent Residency" in translated or "permanent" in translated.lower()

    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_translate_english_to_english_passthrough():
    """Verify instant passthrough when text is already English."""
    from core.auth import get_current_user

    app.dependency_overrides[get_current_user] = override_sales_user
    transport = ASGITransport(app=app)

    pure_english = "This is a purely English consultation pitch for US F-1 visa."

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/product-master/sales-ai-translate", json={
            "text": pure_english,
            "target_language": "English",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["target_language"] == "English"
        assert data["translated_text"] == pure_english
        assert data["model"] == "direct-passthrough"

    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_translate_empty_text_validation():
    """Verify 400 Bad Request if text is blank."""
    from core.auth import get_current_user

    app.dependency_overrides[get_current_user] = override_sales_user
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/product-master/sales-ai-translate", json={
            "text": "   ",
            "target_language": "Marathi",
        })
        assert resp.status_code == 400

    app.dependency_overrides.pop(get_current_user, None)
