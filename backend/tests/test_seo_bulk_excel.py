import io
import pytest
import pandas as pd
from httpx import AsyncClient, ASGITransport
from server import app
from core.database import db
from core.auth import get_current_user


@pytest.mark.asyncio
async def test_seo_excel_template_and_bulk_upload():
    """Verify Phase 19.8 SEO Bulk Excel template download, preview and live commit."""
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "admin-1",
        "email": "admin@leamss.com",
        "role": "admin",
        "permissions": ["*"],
    }
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Download Blank SEO Template
        r_tmpl = await client.get("/api/occupation-master/import/seo/template?country=AU&mode=template")
        assert r_tmpl.status_code == 200
        assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in r_tmpl.headers["content-type"]
        assert len(r_tmpl.content) > 1000

        # Read back template with pandas/openpyxl
        df_tmpl = pd.read_excel(io.BytesIO(r_tmpl.content))
        assert "Code" in df_tmpl.columns
        assert "Meta_Title" in df_tmpl.columns
        assert "Meta_Description" in df_tmpl.columns

        # 2. Download Pre-filled Export for AU
        r_exp = await client.get("/api/occupation-master/import/seo/template?country=AU&mode=export")
        assert r_exp.status_code == 200
        assert len(r_exp.content) > 1000

        # 3. Create a test occupation in DB if none exists
        test_occ = await db["occupation_master"].find_one({"country_code": "AU", "status": {"$ne": "superseded"}})
        if not test_occ:
            await db["occupation_master"].insert_one({
                "country_code": "AU",
                "code": "261313",
                "title": "Software Engineer",
                "status": "verified",
                "occupation_id": "test_occ_261313",
            })
            test_code = "261313"
        else:
            test_code = str(test_occ["code"])

        # 4. Prepare upload file in-memory with custom SEO attributes
        upload_rows = [
            {
                "Country": "AU",
                "Code": test_code,
                "Occupation_Title": "Test Role",
                "Meta_Title": f"Custom SEO Title for {test_code} | LEAMSS",
                "Meta_Description": f"Custom SEO Description for code {test_code} with high click rate.",
                "Keywords": "software, developer, migration, 189",
                "Focus_Keyword": "software engineer australia pr",
                "OG_Title": f"Social OG Title {test_code}",
                "OG_Description": f"Social OG Description {test_code}",
                "Meta_Robots": "index, follow",
                "Schema_Type": "Occupation",
            }
        ]
        upload_df = pd.DataFrame(upload_rows)
        upload_buf = io.BytesIO()
        upload_df.to_excel(upload_buf, index=False)
        upload_buf.seek(0)
        upload_bytes = upload_buf.getvalue()

        # 5. Test Preview Endpoint
        files = {"file": ("test_seo.xlsx", upload_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        data = {"country_code": "AU"}
        r_prev = await client.post("/api/occupation-master/import/seo/preview", files=files, data=data)
        assert r_prev.status_code == 200
        res_prev = r_prev.json()
        assert res_prev["ok"] is True
        assert res_prev["matched_count"] >= 1
        assert len(res_prev["sample_rows"]) >= 1
        assert res_prev["sample_rows"][0]["code"] == test_code

        # 6. Test Commit Endpoint (Live update)
        files = {"file": ("test_seo.xlsx", upload_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        data = {"country_code": "AU", "publish_live": "true"}
        r_commit = await client.post("/api/occupation-master/import/seo/commit", files=files, data=data)
        assert r_commit.status_code == 200
        res_commit = r_commit.json()
        assert res_commit["ok"] is True
        assert res_commit["updated_count"] >= 1

        # 7. Verify in MongoDB
        updated_doc = await db["occupation_master"].find_one({"country_code": "AU", "code": test_code})
        assert updated_doc is not None
        assert updated_doc.get("seo_meta") is not None
        assert updated_doc["seo_meta"]["meta_title"] == f"Custom SEO Title for {test_code} | LEAMSS"
        assert updated_doc["seo_meta"]["focus_keyword"] == "software engineer australia pr"
        assert updated_doc["seo_meta"]["og_title"] == f"Social OG Title {test_code}"
